"""
Fine Art America & Pixels Print-on-Demand (POD) Deep Harvester & Variant Dredge Engine.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep keyword search across Fine Art America and Pixels marketplace with multi-page pagination.
  - 1-to-20 Variant Dredge: Automatically maps 1 artwork into all available
    commercial physical variants (Canvas Prints, Framed Art, Metal Prints, Acrylic Prints, Tapestries, Pillows, Mugs, Apparel).
  - Artist Store Sweeper: Ingests and expands independent Fine Art America / Pixels artist profiles.
  - Full stealth Playwright & direct HTTP resilient automation with Session Vault integration.
"""

import os
import re
import time
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logger = logging.getLogger("FineArtAmericaScraper")

FAA_PRODUCT_LINES = [
    ("Stretched Canvas Print", "canvas-print", 85.00, "Wall Art"),
    ("Custom Framed Print", "framed-print", 110.00, "Wall Art"),
    ("Fine Art Print", "art-print", 35.00, "Wall Art"),
    ("High Gloss Metal Print", "metal-print", 95.00, "Wall Art"),
    ("Acrylic Print", "acrylic-print", 105.00, "Wall Art"),
    ("Wood Print", "wood-print", 75.00, "Wall Art"),
    ("Woven Wall Tapestry", "tapestry", 45.00, "Home Decor"),
    ("Decorative Throw Pillow", "throw-pillow", 35.00, "Home Decor"),
    ("Plush Fleece Blanket", "fleece-blanket", 50.00, "Home Goods"),
    ("Duvet Cover", "duvet-cover", 95.00, "Home Goods"),
    ("Shower Curtain", "shower-curtain", 65.00, "Home Goods"),
    ("Cotton Tote Bag", "tote-bag", 25.00, "Bags & Accessories"),
    ("iPhone Tough Case", "iphone-case", 35.00, "Phone Cases"),
    ("Samsung Galaxy Case", "galaxy-case", 35.00, "Phone Cases"),
    ("Men's Graphic T-Shirt", "t-shirt", 25.00, "Apparel"),
    ("Women's Graphic T-Shirt", "womens-t-shirt", 25.00, "Apparel"),
    ("Ceramic Coffee Mug (11 oz)", "coffee-mug", 16.00, "Drinkware"),
    ("Premium Yoga Mat", "yoga-mat", 55.00, "Lifestyle & Fitness"),
    ("Spiral Bound Notebook", "spiral-notebook", 16.00, "Stationery"),
    ("Die-Cut Vinyl Sticker", "sticker", 5.00, "Stickers & Decals"),
    ("500-Piece Jigsaw Puzzle", "jigsaw-puzzle", 35.00, "Puzzles & Games")
]


class FineArtAmericaScraper:
    """High-speed Fine Art America / Pixels POD Search & Variant Dredge Engine."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/fineartamerica_session")
        os.makedirs(self.user_dir, exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _get_context(self, p):
        """Create persistent browser context with stealth scripts."""
        extra_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
        if self.headless:
            extra_args.append("--window-position=-2400,-2400")

        context = p.chromium.launch_persistent_context(
            self.user_dir,
            headless=False if self.headless else False,
            channel="msedge",
            args=extra_args,
            viewport={"width": 1366, "height": 768}
        )
        return context

    def search(
        self,
        query: str,
        depth_pages: int = 2,
        store_filter: Optional[str] = None,
        condition: str = "all",
        status_callback=None,
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Execute deep keyword search across Fine Art America / Pixels with multi-page pagination.
        """
        results = []
        clean_q = query.strip()
        if not clean_q:
            return results

        if store_filter and any(k in store_filter.lower() for k in ("global", "search", "all", "community", "artist")):
            store_filter = None

        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        def _status(msg):
            if status_callback: status_callback(msg)

        _log(f"🖼 [Fine Art America] Starting POD Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

        seen_urls = set()

        for page_num in range(1, depth_pages + 1):
            enc_q = urllib.parse.quote_plus(clean_q)
            if store_filter:
                clean_store = store_filter.strip().lstrip("@")
                if "." in clean_store:
                    search_url = f"https://{clean_store}/shop/all?page={page_num}"
                else:
                    search_url = f"https://fineartamerica.com/profiles/{clean_store}?page={page_num}"
            else:
                search_url = f"https://fineartamerica.com/art/{enc_q}?page={page_num}"

            _status(f"🖼 [Fine Art America] Fetching page {page_num}/{depth_pages}...")
            _log(f"🖼 [Fine Art America] Navigating to: {search_url}")

            # Try direct fast HTTP request first (FAA permits direct HTTP)
            html = None
            try:
                r = requests.get(search_url, headers=self.headers, timeout=12)
                if r.status_code == 200 and len(r.text) > 10000:
                    html = r.text
            except Exception as req_e:
                _log(f"⚠ [Fine Art America] HTTP fallback triggered: {req_e}")

            # Fallback to Playwright if needed
            if not html:
                try:
                    with sync_playwright() as p:
                        context = self._get_context(p)
                        page = context.pages[0] if context.pages else context.new_page()
                        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                        page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                        time.sleep(1.0)
                        html = page.content()
                        context.close()
                except Exception as pw_e:
                    _log(f"❌ [Fine Art America] Playwright fallback error on page {page_num}: {pw_e}")

            if not html:
                continue

            page_items = self._parse_search_page(html)
            _log(f"🖼 [Fine Art America] Page {page_num}: Parsed {len(page_items)} listings.")

            for it in page_items:
                u = it.get("url")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    results.append(it)

            if len(page_items) == 0:
                _log(f"🖼 [Fine Art America] No more listings found on page {page_num}. Ending sweep.")
                break

        _log(f"✅ [Fine Art America] Search completed. Extracted {len(results)} distinct POD listing(s).")
        return results

    def _parse_search_page(self, html: str) -> List[Dict[str, Any]]:
        """Parse Fine Art America search grid into structured item dictionaries."""
        items = []
        soup = BeautifulSoup(html, "html.parser")

        seen_on_page = set()

        # Find all featured links that are actual artwork cards
        featured_links = soup.select("a[href*='/featured/']")

        for link_el in featured_links:
            try:
                href = link_el["href"].strip()
                if not href.startswith("http"):
                    href = f"https://fineartamerica.com{href}"

                clean_url = href.split("?")[0] if "?" in href else href
                # Exclude static/header collections links
                if any(x in clean_url for x in ("/collectiongroups", "/rooms", "/artistdirectory", "/subjects", "/overview")):
                    continue

                if clean_url in seen_on_page:
                    continue

                # Locate card container
                parent_div = link_el.find_parent("div")
                if not parent_div:
                    continue

                # Check ancestor text for metadata
                ancestor = parent_div.find_parent("div")
                if not ancestor:
                    continue

                full_card_text = ancestor.get_text(separator=" | ", strip=True)

                # Look for artwork image
                img_el = link_el.select_one("img") or ancestor.select_one("img[src*='images.fineartamerica.com'], img[src*='render.fineartamerica.com']")
                image_url = ""
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src") or ""

                if not image_url or "LogoFineArtAmerica" in image_url:
                    continue

                seen_on_page.add(clean_url)

                # Parse Title & Artist from text parts:
                # Format: "Blue Dragon Fly | Print | $86 | $69 | By Rodrigo Herweg | 3 Designs"
                parts = [p.strip() for p in full_card_text.split("|") if p.strip()]
                
                title = ""
                price = "$35.00"
                seller = "Fine Art America Artist"

                if parts:
                    title = parts[0]

                if not title or len(title) < 2:
                    slug = clean_url.rstrip("/").split("/")[-1].replace(".html", "")
                    title = slug.replace("-", " ").title()

                # Extract price
                p_match = re.search(r"\$\d+(?:\.\d{2})?", full_card_text)
                if p_match:
                    price = p_match.group(0)

                # Extract artist
                for part in parts[1:]:
                    if part.startswith("By ") or part.startswith("by "):
                        seller = part[3:].strip()
                        break
                    elif "Photography" in part or "Art" in part or "Images" in part or "Designs" in part:
                        if not re.search(r"\$\d+", part) and not part.endswith("Designs"):
                            seller = part
                            break
                if seller == "Fine Art America Artist" and len(parts) >= 4:
                    # Often the 4th or 5th part is the artist name
                    candidate = parts[-2] if "Designs" in parts[-1] else parts[-1]
                    if not re.search(r"\$\d+", candidate) and candidate not in ("Print", "Canvas", "Framed"):
                        seller = candidate

                # Item ID from slug
                item_id = clean_url.rstrip("/").split("/")[-1].replace(".html", "")

                items.append({
                    "title": title,
                    "url": clean_url,
                    "price": price,
                    "item_id": item_id,
                    "seller": seller,
                    "platform": "fineartamerica",
                    "thumbnail": image_url,
                    "image_url": image_url,
                    "source": "Fine Art America Search",
                    "status": "New"
                })
            except Exception as ex:
                logger.debug(f"Error parsing FAA card: {ex}")
                continue

        return items

    def fetch_single_item(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time metadata and high-res image for a single Fine Art America / Pixels listing."""
        clean_url = url.strip()
        try:
            r = requests.get(clean_url, headers=self.headers, timeout=12)
            html = r.text if r.status_code == 200 else None

            if not html:
                with sync_playwright() as p:
                    context = self._get_context(p)
                    page = context.pages[0] if context.pages else context.new_page()
                    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                    page.goto(clean_url, wait_until="domcontentloaded", timeout=25000)
                    time.sleep(1.0)
                    html = page.content()
                    context.close()

            soup = BeautifulSoup(html, "html.parser")

            title = ""
            t_el = soup.select_one("h1, meta[property='og:title']")
            if t_el:
                title = t_el.get("content", "") if t_el.name == "meta" else t_el.get_text(strip=True)

            price = "$35.00"
            p_el = soup.select_one("meta[property='product:price:amount'], [class*='price'], [class*='Price']")
            if p_el:
                p_val = p_el.get("content") if p_el.name == "meta" else p_el.get_text(strip=True)
                p_m = re.search(r"\$\d+(?:\.\d{2})?", p_val)
                if p_m:
                    price = p_m.group(0)

            seller = "Fine Art America Artist"
            s_el = soup.select_one("a[href*='/profiles/'], [class*='artistname'], [class*='artist-name']")
            if s_el:
                s_txt = s_el.get_text(strip=True)
                if s_txt:
                    seller = re.sub(r"^(?:by|By|from|From)\s*", "", s_txt, flags=re.IGNORECASE).strip()

            image_url = ""
            img_el = soup.select_one("meta[property='og:image'], img#mainImage, img[class*='mainImage']")
            if img_el:
                image_url = img_el.get("content") if img_el.name == "meta" else img_el.get("src", "")

            item_id = clean_url.rstrip("/").split("/")[-1].replace(".html", "")

            return {
                "title": title or "Fine Art America Artwork",
                "url": clean_url,
                "price": price,
                "item_id": item_id,
                "seller": seller,
                "platform": "fineartamerica",
                "thumbnail": image_url,
                "image_url": image_url,
                "source": "Fine Art America PDP",
                "status": "New"
            }
        except Exception as e:
            logger.error(f"Failed to fetch single Fine Art America item {url}: {e}")
            return None

    def expand_design_variants(
        self,
        parent_item: Dict[str, Any],
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        1-to-21 POD Variant Matrix Expansion for Fine Art America / Pixels designs.
        Generates individual merchandise variants for enforcement.
        """
        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        variants = []
        base_url = parent_item.get("url", "")
        base_title = parent_item.get("title", "Custom Artwork")
        seller = parent_item.get("seller", "Fine Art America Artist")
        parent_id = parent_item.get("item_id", "")
        base_image = parent_item.get("image_url") or parent_item.get("thumbnail", "")

        clean_title = re.sub(r"\s*-\s*Canvas.*$", "", base_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Print.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Framed.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = clean_title.strip()

        _log(f"🖼 [Fine Art America] Expanding POD Matrix for artwork '{clean_title[:35]}...'")

        for prod_name, slug_code, est_price, category in FAA_PRODUCT_LINES:
            var_url = f"{base_url}?product={slug_code}" if "?" not in base_url else f"{base_url}&product={slug_code}"
            var_title = f"{clean_title} - {prod_name}"
            var_id = f"{parent_id}_{slug_code}" if parent_id else slug_code

            variants.append({
                "title": var_title,
                "url": var_url,
                "price": f"${est_price:.2f}",
                "item_id": var_id,
                "seller": seller,
                "platform": "fineartamerica",
                "thumbnail": base_image,
                "image_url": base_image,
                "source": f"Fine Art America POD ({category})",
                "status": "New"
            })

        _log(f"🖼 [Fine Art America] Generated +{len(variants)} POD commercial variants.")
        return variants
