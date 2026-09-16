"""
CafePress Print-on-Demand (POD) Deep Harvester & Variant Dredge Engine.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep keyword search across CafePress marketplace with multi-page pagination.
  - 1-to-20 Variant Dredge: Automatically maps 1 design into all available
    commercial physical variants (T-Shirts, Hoodies, Mugs, Decals, Magnets, Tote Bags, Hats).
  - Storefront Sweeper: Ingests and expands CafePress profile and store catalogs.
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

logger = logging.getLogger("CafePressScraper")

CAFEPRESS_PRODUCT_LINES = [
    ("Classic T-Shirt", "classic-t-shirt", 19.99, "Apparel - Men"),
    ("Women's Value T-Shirt", "womens-t-shirt", 19.99, "Apparel - Women"),
    ("Pullover Hoodie", "pullover-hoodie", 44.99, "Outerwear"),
    ("Full Zip Hoodie", "zip-hoodie", 49.99, "Outerwear"),
    ("Ceramic Coffee Mug (11 oz)", "mug-11oz", 15.99, "Drinkware"),
    ("Large Coffee Mug (15 oz)", "mug-15oz", 18.99, "Drinkware"),
    ("Stainless Steel Travel Mug", "travel-mug", 24.99, "Drinkware"),
    ("Oval / Bumper Sticker", "sticker", 4.99, "Stickers & Decals"),
    ("Rectangle Magnet", "magnet", 4.99, "Stationery & Magnets"),
    ("Canvas Tote Bag", "tote-bag", 19.99, "Bags & Accessories"),
    ("Trucker Hat", "trucker-hat", 19.99, "Headwear"),
    ("Baseball Cap", "baseball-cap", 21.99, "Headwear"),
    ("Decorative Throw Pillow", "throw-pillow", 29.99, "Home Decor"),
    ("Drinking Pint Glass", "pint-glass", 16.99, "Drinkware & Barware"),
    ("Shot Glass", "shot-glass", 9.99, "Drinkware & Barware"),
    ("Stainless Water Bottle", "water-bottle", 22.99, "Drinkware"),
    ("Adjustable Kitchen Apron", "apron", 24.99, "Home & Kitchen"),
    ("Ergonomic Mouse Pad", "mouse-pad", 14.99, "Office & Tech"),
    ("Baby Bodysuit / Creeper", "baby-bodysuit", 18.99, "Baby & Toddler"),
    ("Metal License Plate Frame", "license-plate-frame", 19.99, "Automotive & Decals")
]


class CafePressScraper:
    """High-speed CafePress POD Search & Variant Dredge Engine."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/cafepress_session")
        os.makedirs(self.user_dir, exist_ok=True)

    def _get_context(self, p):
        """Create persistent browser context with realistic browser headers and stealth scripts."""
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
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
        Execute deep keyword search across CafePress with multi-page pagination.
        Handles AWS WAF challenges automatically via persistent stealth browser.
        """
        results = []
        clean_q = query.strip()
        if not clean_q:
            return results

        if store_filter and any(k in store_filter.lower() for k in ("global", "search", "all", "community", "shop", "designer")):
            store_filter = None

        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        def _status(msg):
            if status_callback: status_callback(msg)

        _log(f"☕ [CafePress] Starting POD Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

        seen_urls = set()
        seen_ids = set()

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

                for page_num in range(1, depth_pages + 1):
                    enc_q = clean_q.replace(" ", "+")
                    if store_filter:
                        clean_store = store_filter.strip().lstrip("@")
                        search_url = f"https://www.cafepress.com/profile/{clean_store}?page={page_num}"
                    else:
                        search_url = f"https://www.cafepress.com/+{enc_q}?page={page_num}"

                    _status(f"☕ [CafePress] Fetching page {page_num}/{depth_pages}...")
                    _log(f"☕ [CafePress] Navigating to: {search_url}")

                    try:
                        resp = page.goto(search_url, wait_until="networkidle", timeout=30000)
                        time.sleep(1.0)
                    except Exception as nav_e:
                        _log(f"⚠ [CafePress] Navigation warning on page {page_num}: {nav_e}")

                    html = page.content()
                    page_items = self._parse_search_page(html)
                    _log(f"☕ [CafePress] Page {page_num}: Parsed {len(page_items)} listings.")

                    new_count = 0
                    for it in page_items:
                        u = it.get("url")
                        iid = it.get("item_id")
                        if (u and u not in seen_urls) and (not iid or iid not in seen_ids):
                            if u: seen_urls.add(u)
                            if iid: seen_ids.add(iid)
                            results.append(it)
                            new_count += 1

                    if len(page_items) == 0 or new_count == 0:
                        _log(f"☕ [CafePress] No more unique listings found on page {page_num}. Ending sweep.")
                        break

                try:
                    context.close()
                except Exception:
                    pass

        except Exception as e:
            _log(f"❌ [CafePress] Engine error: {e}")
            logger.exception("CafePress scraping failed")

        _log(f"✅ [CafePress] Search completed. Extracted {len(results)} distinct POD listing(s).")
        return results

    def _parse_search_page(self, html: str) -> List[Dict[str, Any]]:
        """Parse CafePress search grid into structured item dictionaries."""
        items = []
        seen_ids = set()
        seen_urls = set()

        # 1. Primary: Extract var PRODUCT_ITEMS from page script
        m = re.search(r"var\s+PRODUCT_ITEMS\s*=\s*(\[.*?\]);", html, re.DOTALL)
        if m:
            try:
                prods = json.loads(m.group(1))
                for p_obj in prods:
                    title = p_obj.get("caption", "").strip()
                    detail_url = p_obj.get("detail_url", "").strip()
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = f"https://www.cafepress.com{detail_url}"
                    clean_url = detail_url.split("?")[0] if detail_url else ""

                    item_id = str(p_obj.get("design_id") or p_obj.get("product_id") or "").strip()
                    if not item_id and clean_url:
                        id_m = re.search(r",(\d{6,15})", clean_url) or re.search(r"[-_](\d{6,15})", clean_url)
                        if id_m: item_id = id_m.group(1)

                    if clean_url in seen_urls or (item_id and item_id in seen_ids):
                        continue
                    if clean_url: seen_urls.add(clean_url)
                    if item_id: seen_ids.add(item_id)

                    price_val = p_obj.get("sale_price") or p_obj.get("retail_price") or 19.99
                    try:
                        price = f"${float(price_val):.2f}"
                    except Exception:
                        price = f"${price_val}"

                    img_raw = p_obj.get("image_url", "").strip()
                    if img_raw and not img_raw.startswith("http"):
                        img_raw = f"https://www.cafepress.com{img_raw}"

                    items.append({
                        "title": title or "CafePress Custom Merchandise",
                        "url": clean_url,
                        "price": price,
                        "item_id": item_id,
                        "seller": "CafePress Designer",
                        "platform": "cafepress",
                        "marketplace": "cafepress.com",
                        "marketplace_code": "cafepress.com",
                        "thumbnail": img_raw,
                        "image_url": img_raw,
                        "location": "Print-on-Demand (Global Fulfillment)",
                        "threat_badge": "☕ POD Infringement (CafePress)",
                        "threat_intel": "Commercial POD (CafePress Custom Merchandise)",
                        "product_type": "Apparel & Merch",
                        "brand": "Unknown",
                        "source": "CafePress Search",
                        "status": "New"
                    })
            except Exception as je:
                logger.debug(f"CafePress JSON parsing notice: {je}")

        # 2. Fallback: DOM card parsing if script missing
        if not items:
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".product-item-card, .design-item-wrapper, div[data-id], .gallery-item, .product-box, .product-tile")
            if not cards:
                cards = soup.select("div[class*='product-item'], div[class*='design-item']")

            for card in cards:
                try:
                    link_el = card if card.name == "a" else card.select_one("a[href]")
                    if not link_el or not link_el.get("href"):
                        continue

                    href = link_el["href"].strip()
                    if not href.startswith("http"):
                        href = f"https://www.cafepress.com{href}"

                    if any(x in href for x in ("/cp/customer/", "/help/", "/cart", "/account", "/sell", "login")):
                        continue

                    clean_url = href.split("?")[0]
                    if clean_url in seen_urls:
                        continue

                    item_id = card.get("data-id", "").strip()
                    if not item_id:
                        id_m = re.search(r",(\d{6,15})", clean_url) or re.search(r"[-_](\d{6,15})", clean_url)
                        if id_m: item_id = id_m.group(1)

                    if item_id and item_id in seen_ids:
                        continue

                    if clean_url: seen_urls.add(clean_url)
                    if item_id: seen_ids.add(item_id)

                    title_el = card.select_one(".design-title, [class*='title'], [class*='Title'], .product-name, h3, h4")
                    title = title_el.get_text(strip=True) if title_el else link_el.get("title", "")
                    if not title and link_el.get("aria-label"):
                        title = link_el["aria-label"].strip()
                    if not title:
                        slug = clean_url.rstrip("/").split("/")[-1]
                        slug_clean = re.sub(r"[,_-]\d+$", "", slug)
                        title = slug_clean.replace("-", " ").replace("+", " ").replace("_", " ").title()

                    title = re.sub(r"\s+", " ", title).strip()
                    if not title or len(title) < 3:
                        continue

                    price = "$19.99"
                    price_el = card.select_one(".design-price, .component-price, [class*='price'], .retail-price, .sale-price")
                    if price_el:
                        pm = re.search(r"\$\d+(?:\.\d{2})?", price_el.get_text(strip=True))
                        if pm: price = pm.group(0)

                    seller = "CafePress Designer"
                    seller_el = card.select_one("a[href*='/profile/'], a[href*='/shop/'], [class*='designer'], [class*='seller'], [class*='by-line']")
                    if seller_el:
                        s_txt = seller_el.get_text(strip=True)
                        if s_txt:
                            seller = re.sub(r"^(?:by|By|from|From|Shop:?)\s*", "", s_txt, flags=re.IGNORECASE).strip()

                    image_url = ""
                    img_el = card.select_one("img[data-zoom-src], img[src*='/rest/pub/designs/'], img")
                    if img_el:
                        for attr in ["data-zoom-src", "src", "data-src", "data-original", "data-lazy-src"]:
                            val = img_el.get(attr)
                            if val and not val.startswith("data:"):
                                if not val.startswith("http"):
                                    val = f"https://www.cafepress.com{val}"
                                image_url = val
                                break

                    items.append({
                        "title": title,
                        "url": clean_url,
                        "price": price,
                        "item_id": item_id,
                        "seller": seller,
                        "platform": "cafepress",
                        "marketplace": "cafepress.com",
                        "marketplace_code": "cafepress.com",
                        "thumbnail": image_url,
                        "image_url": image_url,
                        "location": "Print-on-Demand (Global Fulfillment)",
                        "threat_badge": "☕ POD Infringement (CafePress)",
                        "threat_intel": "Commercial POD (CafePress Custom Merchandise)",
                        "product_type": "Apparel & Merch",
                        "brand": "Unknown",
                        "source": "CafePress Search",
                        "status": "New"
                    })
                except Exception as ex:
                    logger.debug(f"Error parsing CafePress card: {ex}")
                    continue

        return items

    def enrich_seller_info(
        self,
        items: List[Dict[str, Any]],
        progress_callback=None,
        stop_event=None
    ):
        """
        High-speed seller/designer name & store link enrichment for CafePress listings.
        Visits the PDP to extract .designer-card-wrapper / .designer-info / profile links.
        """
        total = len(items)
        if total == 0:
            return

        logger.info(f"☕ [CafePress] Enriching seller info for {total} listing(s)...")

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

                for idx, item in enumerate(items):
                    if stop_event and stop_event.is_set():
                        break

                    url = item.get("url", "").strip()
                    if not url:
                        continue

                    extracted_seller = None
                    store_handle = None

                    try:
                        page.goto(url, wait_until="networkidle", timeout=20000)
                        html = page.content()
                        soup = BeautifulSoup(html, "html.parser")

                        des_el = soup.select_one(".designer-card-wrapper a[href*='/profile/'], .designer-info a[href*='/profile/'], a[href*='/profile/'], [class*='designer-name']")
                        if des_el and des_el.get_text(strip=True):
                            cand = des_el.get_text(strip=True)
                            href = des_el.get("href", "")
                            sm = re.search(r'/profile/([^/?#]+)', href)
                            store_handle = sm.group(1) if sm else cand
                            extracted_seller = cand
                        else:
                            s_el = soup.select_one("a[href*='/shop/'], [class*='by-line']")
                            if s_el and s_el.get_text(strip=True):
                                cand = re.sub(r"^(?:by|By|from|From|Shop:?)\s*", "", s_el.get_text(strip=True), flags=re.IGNORECASE).strip()
                                extracted_seller = cand
                                store_handle = cand
                    except Exception as pe:
                        logger.debug(f"CafePress seller enrichment error for {url}: {pe}")

                    if extracted_seller and extracted_seller.lower() not in ("cafepress designer", "unknown"):
                        item["seller"] = extracted_seller
                        if store_handle:
                            item["store_id"] = store_handle
                            item["store_url"] = f"https://www.cafepress.com/profile/{store_handle}"
                        item["location"] = "Print-on-Demand (Global Fulfillment)"

                    if progress_callback:
                        try:
                            progress_callback(idx + 1, total, item)
                        except Exception:
                            pass

                try:
                    context.close()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"CafePress seller enrichment engine error: {e}")

        logger.info(f"✅ [CafePress] Seller enrichment completed for {total} item(s).")

    def fetch_single_item(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time metadata and high-res mockup for a single CafePress listing."""
        clean_url = url.strip()
        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                page.goto(clean_url, wait_until="networkidle", timeout=25000)
                time.sleep(1.0)
                html = page.content()
                context.close()

            soup = BeautifulSoup(html, "html.parser")

            # Title
            title = ""
            t_el = soup.select_one("h1, meta[property='og:title']")
            if t_el:
                title = t_el.get("content", "") if t_el.name == "meta" else t_el.get_text(strip=True)

            # Price
            price = "$19.99"
            p_el = soup.select_one("meta[property='product:price:amount'], [class*='price'], [class*='Price']")
            if p_el:
                p_val = p_el.get("content") if p_el.name == "meta" else p_el.get_text(strip=True)
                p_m = re.search(r"\$\d+(?:\.\d{2})?", p_val)
                if p_m:
                    price = p_m.group(0)

            # Seller / Store
            seller = "CafePress Designer"
            store_handle = None
            des_el = soup.select_one(".designer-card-wrapper a[href*='/profile/'], .designer-info a[href*='/profile/'], a[href*='/profile/']")
            if des_el and des_el.get_text(strip=True):
                seller = des_el.get_text(strip=True)
                sm = re.search(r'/profile/([^/?#]+)', des_el.get("href", ""))
                if sm: store_handle = sm.group(1)
            else:
                s_el = soup.select_one("a[href*='/shop/'], [class*='by-line'], [class*='designer-name']")
                if s_el and s_el.get_text(strip=True):
                    seller = re.sub(r"^(?:by|By|from|From)\s*", "", s_el.get_text(strip=True), flags=re.IGNORECASE).strip()

            # Image
            image_url = ""
            img_el = soup.select_one("meta[property='og:image'], img#mainImage, img[class*='product-image'], img[src*='/rest/pub/designs/']")
            if img_el:
                image_url = img_el.get("content") if img_el.name == "meta" else img_el.get("src", "")
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://www.cafepress.com{image_url}"

            # Item ID
            item_id = ""
            id_m = re.search(r",(\d{6,15})", clean_url) or re.search(r"[-_](\d{6,15})", clean_url)
            if id_m:
                item_id = id_m.group(1)

            return {
                "title": title or "CafePress Custom Design",
                "url": clean_url,
                "price": price,
                "item_id": item_id,
                "seller": seller,
                "store_id": store_handle,
                "store_url": f"https://www.cafepress.com/profile/{store_handle}" if store_handle else None,
                "platform": "cafepress",
                "marketplace": "cafepress.com",
                "marketplace_code": "cafepress.com",
                "thumbnail": image_url,
                "image_url": image_url,
                "location": "Print-on-Demand (Global Fulfillment)",
                "threat_badge": "☕ POD Infringement (CafePress)",
                "threat_intel": "Commercial POD (CafePress Custom Merchandise)",
                "product_type": "Apparel & Merch",
                "brand": "Unknown",
                "source": "CafePress PDP",
                "status": "New"
            }
        except Exception as e:
            logger.error(f"Failed to fetch single CafePress item {url}: {e}")
            return None

    def expand_design_variants(
        self,
        parent_item: Dict[str, Any],
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        1-to-20 POD Variant Matrix Expansion for CafePress designs.
        Generates individual merchandise variants for enforcement.
        """
        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        variants = []
        base_url = parent_item.get("url", "")
        base_title = parent_item.get("title", "Custom Artwork")
        seller = parent_item.get("seller", "CafePress Designer")
        parent_id = parent_item.get("item_id", "")
        base_image = parent_item.get("image_url") or parent_item.get("thumbnail", "")

        clean_title = re.sub(r"\s*-\s*T-?Shirt.*$", "", base_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Mug.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Sticker.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = clean_title.strip()

        _log(f"☕ [CafePress] Expanding POD Matrix for design '{clean_title[:35]}...'")

        for prod_name, slug_code, est_price, category in CAFEPRESS_PRODUCT_LINES:
            var_url = f"{base_url}?product_line={slug_code}"
            var_title = f"{clean_title} - {prod_name}"
            var_id = f"{parent_id}_{slug_code}" if parent_id else slug_code

            variants.append({
                "title": var_title,
                "url": var_url,
                "price": f"${est_price:.2f}",
                "item_id": var_id,
                "seller": seller,
                "platform": "cafepress",
                "marketplace": "cafepress.com",
                "marketplace_code": "cafepress.com",
                "thumbnail": base_image,
                "image_url": base_image,
                "location": "Print-on-Demand (Global Fulfillment)",
                "threat_badge": "☕ POD Infringement (CafePress)",
                "threat_intel": "Commercial POD (CafePress Custom Merchandise)",
                "product_type": "Apparel & Merch",
                "brand": "Unknown",
                "source": f"CafePress POD ({category})",
                "status": "New"
            })

        _log(f"☕ [CafePress] Generated +{len(variants)} POD commercial variants.")
        return variants
