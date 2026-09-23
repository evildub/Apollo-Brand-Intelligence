"""
TeeSpring (Spring) Print-on-Demand (POD) Deep Harvester & Variant Dredge Engine.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep keyword search across TeeSpring / Spring creator marketplace with multi-page pagination.
  - 1-to-20 Variant Dredge: Automatically maps 1 design into all available
    commercial physical variants (T-Shirts, Hoodies, Mugs, Stickers, Cases, Posters, Blankets).
  - Creator Store Sweeper: Ingests and expands creator-spring storefront catalogs.
  - Full stealth Playwright automation with Session Vault integration.
"""

import os
import re
import time
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logger = logging.getLogger("TeeSpringScraper")

TEESPRING_PRODUCT_LINES = [
    ("Classic Unisex Tee", "classic-tee", 22.99, "Apparel - Men"),
    ("Comfort Premium Tee", "comfort-tee", 26.99, "Apparel"),
    ("Classic Pullover Hoodie", "pullover-hoodie", 46.99, "Outerwear"),
    ("Zip Hoodie", "zip-hoodie", 49.99, "Outerwear"),
    ("Crewneck Sweatshirt", "crewneck-sweatshirt", 39.99, "Outerwear"),
    ("Classic Tank Top", "tank-top", 23.99, "Apparel"),
    ("Long Sleeve Tee", "long-sleeve-tee", 28.99, "Apparel"),
    ("Die-Cut Vinyl Sticker", "sticker", 5.99, "Stickers & Decals"),
    ("11 oz Ceramic Mug", "mug-11oz", 15.99, "Drinkware"),
    ("15 oz Ceramic Mug", "mug-15oz", 18.99, "Drinkware"),
    ("Stainless Water Bottle", "water-bottle", 25.99, "Drinkware"),
    ("All-Over Print Tote Bag", "tote-bag", 21.99, "Bags & Accessories"),
    ("Embroidered Dad Cap", "dad-cap", 24.99, "Headwear"),
    ("Snapback Hat", "snapback-hat", 26.99, "Headwear"),
    ("Indoor Throw Pillow", "throw-pillow", 29.99, "Home Decor"),
    ("Plush Fleece Blanket", "fleece-blanket", 49.99, "Home Goods"),
    ("iPhone Snap Case", "iphone-case", 24.99, "Phone Cases"),
    ("Samsung Galaxy Case", "galaxy-case", 24.99, "Phone Cases"),
    ("Stretched Canvas Print", "canvas-print", 59.99, "Wall Art"),
    ("Matte Wall Poster", "poster", 19.99, "Wall Art")
]


class TeeSpringScraper:
    """High-speed TeeSpring / Spring POD Search & Variant Dredge Engine."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/teespring_session")
        os.makedirs(self.user_dir, exist_ok=True)

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
        Execute deep keyword search across TeeSpring / Spring with multi-page pagination.
        """
        results = []
        clean_q = query.strip()
        if not clean_q:
            return results

        if store_filter and any(k in store_filter.lower() for k in ("global", "search", "all", "community", "store")):
            store_filter = None

        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        def _status(msg):
            if status_callback: status_callback(msg)

        _log(f"🌱 [TeeSpring] Starting POD Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

        seen_urls = set()

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

                for page_num in range(1, depth_pages + 1):
                    enc_q = urllib.parse.quote_plus(clean_q)
                    if store_filter:
                        clean_store = store_filter.strip().lstrip("@")
                        if "." in clean_store:
                            search_url = f"https://{clean_store}/?page={page_num}"
                        else:
                            search_url = f"https://{clean_store}.creator-spring.com/?page={page_num}"
                    else:
                        search_url = f"https://spring.com/search?q={enc_q}&page={page_num}"

                    _status(f"🌱 [TeeSpring] Fetching page {page_num}/{depth_pages}...")
                    _log(f"🌱 [TeeSpring] Navigating to: {search_url}")

                    try:
                        resp = page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                        for _ in range(3):
                            page.evaluate("window.scrollBy(0, 1000);")
                            time.sleep(0.4)
                        time.sleep(1.0)
                    except Exception as nav_e:
                        _log(f"⚠ [TeeSpring] Navigation warning on page {page_num}: {nav_e}")

                    html = page.content()
                    page_items = self._parse_search_page(html)
                    _log(f"🌱 [TeeSpring] Page {page_num}: Parsed {len(page_items)} listings.")

                    for it in page_items:
                        u = it.get("url")
                        if u and u not in seen_urls:
                            seen_urls.add(u)
                            results.append(it)

                    if len(page_items) == 0:
                        _log(f"🌱 [TeeSpring] No more listings found on page {page_num}. Ending sweep.")
                        break

                try:
                    context.close()
                except Exception:
                    pass

        except Exception as e:
            _log(f"❌ [TeeSpring] Engine error: {e}")
            logger.exception("TeeSpring scraping failed")

        _log(f"✅ [TeeSpring] Search completed. Extracted {len(results)} distinct POD listing(s).")
        return results

    def _parse_search_page(self, html: str) -> List[Dict[str, Any]]:
        """Parse TeeSpring / Spring search grid into structured item dictionaries."""
        items = []
        soup = BeautifulSoup(html, "html.parser")

        # Select product cards
        cards = soup.select("[data-testid='product-card'], div[class*='ProductCard'], div[class*='product-tile'], a[href*='/listing/'], a[href*='/shop/']")
        if not cards:
            cards = soup.select("div[class*='card'], div[class*='item'], a[href*='creator-spring.com/']")

        seen_on_page = set()

        for card in cards:
            try:
                link_el = card if card.name == "a" else card.select_one("a[href*='/listing/'], a[href*='/shop/'], a[href*='creator-spring.com'], a[href^='/']")
                if not link_el or not link_el.get("href"):
                    continue

                href = link_el["href"].strip()
                if not href.startswith("http"):
                    href = f"https://spring.com{href}"

                if any(x in href for x in ("/cart", "/checkout", "/help", "/login", "/signup", "/start-designing")):
                    continue

                clean_url = href.split("?")[0] if "?" in href else href
                if clean_url in seen_on_page:
                    continue
                seen_on_page.add(clean_url)

                # Extract Item ID
                item_id = ""
                id_m = re.search(r"/listing/([^/?#]+)", clean_url) or re.search(r"pid=(\d+)", clean_url)
                if id_m:
                    item_id = id_m.group(1)

                # Extract Title
                title = ""
                title_el = card.select_one("[class*='title'], [class*='Title'], h3, h4, span[class*='name']")
                if title_el:
                    title = title_el.get_text(strip=True)
                if not title and link_el.get("title"):
                    title = link_el["title"].strip()
                if not title and link_el.get("aria-label"):
                    title = link_el["aria-label"].strip()
                if not title:
                    img_el = card.select_one("img")
                    if img_el and img_el.get("alt"):
                        title = img_el["alt"].strip()
                if not title:
                    slug = clean_url.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").replace("_", " ").title()

                title = re.sub(r"\s+", " ", title).strip()
                if not title or len(title) < 3:
                    continue

                # Extract Price
                price = "$22.99"
                price_el = card.select_one("[class*='price'], [class*='Price'], span[class*='price']")
                if price_el:
                    p_txt = price_el.get_text(strip=True)
                    p_m = re.search(r"\$\d+(?:\.\d{2})?", p_txt)
                    if p_m:
                        price = p_m.group(0)

                # Extract Seller / Creator
                seller = "Spring Creator"
                seller_el = card.select_one("a[href*='/@'], [class*='creator'], [class*='store'], [class*='seller']")
                if seller_el:
                    s_txt = seller_el.get_text(strip=True)
                    if s_txt:
                        seller = re.sub(r"^(?:by|By|from|From|Store:?)\s*", "", s_txt, flags=re.IGNORECASE).strip()
                if seller == "Spring Creator" and "creator-spring.com" in clean_url:
                    store_sub = clean_url.split("://")[1].split(".creator-spring.com")[0]
                    if store_sub:
                        seller = store_sub.replace("-", " ").title()

                # Extract Image URL
                image_url = ""
                img_el = card.select_one("img")
                if img_el:
                    for attr in ["src", "data-src", "data-original"]:
                        val = img_el.get(attr)
                        if val and "http" in val:
                            image_url = val
                            break

                items.append({
                    "title": title,
                    "url": clean_url,
                    "price": price,
                    "item_id": item_id,
                    "seller": seller,
                    "platform": "teespring",
                    "thumbnail": image_url,
                    "image_url": image_url,
                    "source": "TeeSpring Search",
                    "status": "New"
                })
            except Exception as ex:
                logger.debug(f"Error parsing TeeSpring card: {ex}")
                continue

        return items

    def fetch_single_item(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time metadata and high-res mockup for a single TeeSpring / Spring listing."""
        clean_url = url.strip()
        try:
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

            price = "$22.99"
            p_el = soup.select_one("meta[property='product:price:amount'], [class*='price'], [class*='Price']")
            if p_el:
                p_val = p_el.get("content") if p_el.name == "meta" else p_el.get_text(strip=True)
                p_m = re.search(r"\$\d+(?:\.\d{2})?", p_val)
                if p_m:
                    price = p_m.group(0)

            seller = "Spring Creator"
            s_el = soup.select_one("a[href*='/@'], [class*='store-name'], [class*='creator-name']")
            if s_el:
                s_txt = s_el.get_text(strip=True)
                if s_txt:
                    seller = re.sub(r"^(?:by|By|from|From)\s*", "", s_txt, flags=re.IGNORECASE).strip()

            image_url = ""
            img_el = soup.select_one("meta[property='og:image'], img.product-image, img[class*='mainImage']")
            if img_el:
                image_url = img_el.get("content") if img_el.name == "meta" else img_el.get("src", "")

            item_id = ""
            id_m = re.search(r"/listing/([^/?#]+)", clean_url)
            if id_m:
                item_id = id_m.group(1)

            return {
                "title": title or "Spring Creator Design",
                "url": clean_url,
                "price": price,
                "item_id": item_id,
                "seller": seller,
                "platform": "teespring",
                "thumbnail": image_url,
                "image_url": image_url,
                "source": "TeeSpring PDP",
                "status": "New"
            }
        except Exception as e:
            logger.error(f"Failed to fetch single TeeSpring item {url}: {e}")
            return None

    def expand_design_variants(
        self,
        parent_item: Dict[str, Any],
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        1-to-20 POD Variant Matrix Expansion for TeeSpring designs.
        Generates individual merchandise variants for enforcement.
        """
        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        variants = []
        base_url = parent_item.get("url", "")
        base_title = parent_item.get("title", "Custom Artwork")
        seller = parent_item.get("seller", "Spring Creator")
        parent_id = parent_item.get("item_id", "")
        base_image = parent_item.get("image_url") or parent_item.get("thumbnail", "")

        clean_title = re.sub(r"\s*-\s*T-?Shirt.*$", "", base_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Mug.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Sticker.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = clean_title.strip()

        _log(f"🌱 [TeeSpring] Expanding POD Matrix for design '{clean_title[:35]}...'")

        for prod_name, slug_code, est_price, category in TEESPRING_PRODUCT_LINES:
            var_url = f"{base_url}?prop={slug_code}"
            var_title = f"{clean_title} - {prod_name}"
            var_id = f"{parent_id}_{slug_code}" if parent_id else slug_code

            variants.append({
                "title": var_title,
                "url": var_url,
                "price": f"${est_price:.2f}",
                "item_id": var_id,
                "seller": seller,
                "platform": "teespring",
                "thumbnail": base_image,
                "image_url": base_image,
                "source": f"TeeSpring POD ({category})",
                "status": "New"
            })

        _log(f"🌱 [TeeSpring] Generated +{len(variants)} POD commercial variants.")
        return variants

    def enrich_seller_info(
        self,
        items: List[Dict[str, Any]],
        progress_callback=None,
        stop_event=None
    ) -> List[Dict[str, Any]]:
        """
        Enrich real creator/store names for TeeSpring / Spring listings.
        Extracts creator handle from URL slug /@handle or stores path.
        """
        if not items:
            return items

        total = len(items)
        for idx, it in enumerate(items, 1):
            if stop_event and stop_event.is_set():
                break

            current_seller = str(it.get("seller", "")).strip()
            if not current_seller or any(g in current_seller.lower() for g in ("spring creator", "teespring creator", "unknown", "resolving...")):
                url = it.get("url", "")
                m = re.search(r"/(?:@|stores/)([a-zA-Z0-9_-]+)", url)
                if m:
                    it["seller"] = m.group(1).strip()
                elif url:
                    # Fallback to fetching single item if possible
                    try:
                        detail = self.fetch_single_item(url)
                        if detail and detail.get("seller") and detail["seller"] not in ("Spring Creator", "Unknown"):
                            it["seller"] = detail["seller"]
                            if detail.get("price") and not it.get("price"):
                                it["price"] = detail["price"]
                    except Exception:
                        pass

            if progress_callback:
                progress_callback(idx, total, it)

        return items

