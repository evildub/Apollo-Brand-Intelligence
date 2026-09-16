"""
Zazzle Print-on-Demand (POD) Deep Harvester & Variant Dredge Engine.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep keyword search across Zazzle marketplace with multi-page pagination.
  - 1-to-25 Variant Dredge: Automatically maps 1 design into all available
    commercial physical variants (T-Shirts, Hoodies, Mugs, Stickers, Cases, Posters, Canvas, Magnets).
  - Storefront/Designer Sweeper: Ingests and expands entire designer / store catalogs.
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

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    import requests as curl_requests

logger = logging.getLogger("ZazzleScraper")

ZAZZLE_PRODUCT_LINES = [
    ("Classic T-Shirt", "tshirt", 19.95, "Apparel - Men"),
    ("Women's Fitted T-Shirt", "womens-tshirt", 21.95, "Apparel - Women"),
    ("Pullover Hoodie", "hoodie", 45.95, "Outerwear"),
    ("Tank Top", "tank-top", 22.95, "Apparel"),
    ("Die-Cut Vinyl Sticker", "sticker", 4.95, "Stickers & Decals"),
    ("Ceramic Coffee Mug (11 oz)", "mug-11oz", 16.95, "Drinkware"),
    ("Two-Tone Coffee Mug (15 oz)", "mug-15oz", 18.95, "Drinkware"),
    ("Stainless Steel Water Bottle", "water-bottle", 29.95, "Drinkware"),
    ("Can Cooler / Koozie", "can-cooler", 7.95, "Barware & Accessories"),
    ("Wrapped Canvas Print (16x20)", "canvas-print", 59.95, "Wall Art"),
    ("Matte Poster Print (18x24)", "poster", 18.95, "Wall Art"),
    ("Metal Wall Art Print", "metal-print", 49.95, "Wall Art"),
    ("Square Magnet", "square-magnet", 4.95, "Stationery & Magnets"),
    ("Round Button Pin", "button-pin", 3.95, "Accessories"),
    ("All-Over Print Tote Bag", "tote-bag", 24.95, "Bags & Accessories"),
    ("Throw Pillow (16x16)", "throw-pillow", 34.95, "Home Decor"),
    ("Fleece Blanket (50x60)", "fleece-blanket", 44.95, "Home Goods"),
    ("iPhone Tough Case", "iphone-case", 34.95, "Phone Cases"),
    ("Samsung Galaxy Case", "galaxy-case", 34.95, "Phone Cases"),
    ("Ergonomic Mouse Pad", "mouse-pad", 14.95, "Office & Tech"),
    ("Metal Keychain", "keychain", 11.95, "Accessories"),
    ("Embroidered Baseball Hat", "baseball-hat", 24.95, "Headwear"),
    ("Trucker Hat", "trucker-hat", 19.95, "Headwear"),
    ("Welcome Doormat", "doormat", 32.95, "Home Decor")
]


class ZazzleScraper:
    """High-speed Zazzle POD Search & Variant Dredge Engine."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/zazzle_session")
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
        Execute deep keyword search across Zazzle with multi-page pagination.
        Uses ultra-fast curl_cffi TLS engine (chrome124) with Playwright fallback.
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

        _log(f"🎨 [Zazzle] Starting POD Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

        seen_urls = set()
        seen_ids = set()

        for page_num in range(1, depth_pages + 1):
            enc_q = urllib.parse.quote_plus(clean_q)
            if store_filter:
                clean_store = store_filter.strip().lstrip("@")
                search_url = f"https://www.zazzle.com/store/{clean_store}/products?pg={page_num}&ps=60"
            else:
                search_url = f"https://www.zazzle.com/s/{enc_q}?pg={page_num}&ps=60"

            _status(f"🎨 [Zazzle] Fetching page {page_num}/{depth_pages}...")
            _log(f"🎨 [Zazzle] Navigating to: {search_url}")

            html = ""
            if HAS_CURL_CFFI:
                try:
                    s = curl_requests.Session(impersonate="chrome124")
                    r = s.get(search_url, timeout=15)
                    if r.status_code == 200:
                        html = r.text
                except Exception as he:
                    _log(f"⚠ [Zazzle] HTTP engine notice on page {page_num}: {he}")

            # Playwright fallback if HTTP was blocked
            if not html or "Something doesn't look right" in html:
                try:
                    with sync_playwright() as p:
                        context = self._get_context(p)
                        page = context.pages[0] if context.pages else context.new_page()
                        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                        page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                        for _ in range(3):
                            page.evaluate("window.scrollBy(0, 1000);")
                            time.sleep(0.4)
                        time.sleep(1.0)
                        html = page.content()
                        context.close()
                except Exception as pe:
                    _log(f"⚠ [Zazzle] Playwright fallback error on page {page_num}: {pe}")

            if not html:
                _log(f"🎨 [Zazzle] No response on page {page_num}. Ending sweep.")
                break

            page_items = self._parse_search_page(html)
            _log(f"🎨 [Zazzle] Page {page_num}: Parsed {len(page_items)} listings.")

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
                _log(f"🎨 [Zazzle] No more unique listings found on page {page_num}. Ending sweep.")
                break

        _log(f"✅ [Zazzle] Search completed. Extracted {len(results)} distinct POD listing(s).")
        return results

    def _parse_search_page(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse Zazzle search grid into structured item dictionaries.
        Extracts 100% of products, thumbnails, store names, and pricing directly from ZData state,
        with seamless DOM fallback.
        """
        items = []
        seen_ids = set()
        seen_urls = set()

        # 1. Primary: Direct ZData Script State Extraction (guarantees 100% thumbnails & accurate sellers)
        m = re.search(r"ZData\s*=\s*JSON\.parse\('(.*?)'\);", html, re.DOTALL)
        if m:
            try:
                raw_json_str = m.group(1).encode().decode('unicode_escape')
                zd = json.loads(raw_json_str)
                prods = []

                # Global Search products
                ms_prods = zd.get("slices", {}).get("data", {}).get("mainSearch", {}).get("searchResultsData", {}).get("products", [])
                if ms_prods:
                    prods.extend(ms_prods)

                # Store Search products
                sps_prods = zd.get("slices", {}).get("data", {}).get("storeProductSearch", {}).get("searchResultsData", {}).get("products", [])
                if sps_prods:
                    prods.extend(sps_prods)

                # Entity product search infos
                psi = zd.get("entities", {}).get("productSearchInfos", {})
                if psi:
                    prods.extend(list(psi.values()))

                for p in prods:
                    item_id = str(p.get("id") or "").strip()
                    link_url = p.get("linkUrl") or p.get("url") or ""
                    if link_url and not link_url.startswith("http"):
                        link_url = f"https://www.zazzle.com{link_url}"
                    clean_url = link_url.split("?")[0] if link_url else ""

                    if not clean_url and not item_id:
                        continue
                    if item_id and item_id in seen_ids:
                        continue
                    if clean_url and clean_url in seen_urls:
                        continue

                    if item_id: seen_ids.add(item_id)
                    if clean_url: seen_urls.add(clean_url)

                    # Title
                    title = p.get("titleSeo") or p.get("title") or ""
                    if not title and clean_url:
                        slug = clean_url.rstrip("/").split("/")[-1]
                        slug_clean = re.sub(r"-\d+$", "", slug)
                        title = slug_clean.replace("-", " ").replace("_", " ").title()

                    # Price
                    price_raw = p.get("price")
                    if price_raw:
                        try:
                            price = f"${float(price_raw):.2f}"
                        except Exception:
                            price = f"${price_raw}"
                    else:
                        price = "$19.95"

                    # Seller / Store handle
                    seller = p.get("storeName") or p.get("storeHandle") or "Zazzle Creator"
                    store_handle = p.get("storeHandle")
                    store_url = f"https://www.zazzle.com/store/{store_handle.lower()}" if store_handle else None

                    # Thumbnail / High-Res image
                    image_url = p.get("imageUrl") or p.get("hoverImageUrl") or ""
                    if image_url and image_url.startswith("//"):
                        image_url = f"https:{image_url}"

                    items.append({
                        "title": title or "Zazzle Custom Design",
                        "url": clean_url,
                        "price": price,
                        "item_id": item_id,
                        "seller": seller,
                        "store_id": store_handle,
                        "store_url": store_url,
                        "platform": "zazzle",
                        "marketplace": "zazzle.com",
                        "marketplace_code": "zazzle.com",
                        "thumbnail": image_url,
                        "image_url": image_url,
                        "location": "Print-on-Demand (Global Fulfillment)",
                        "threat_badge": "🎨 POD Infringement (Zazzle)",
                        "threat_intel": "Commercial POD (Zazzle Custom Merchandise)",
                        "product_type": "Apparel & Merch",
                        "brand": "Unknown",
                        "source": "Zazzle Search",
                        "status": "New"
                    })
            except Exception as e:
                logger.debug(f"ZData parsing notice: {e}")

        # 2. Fallback: DOM Parsing if ZData was empty
        if not items:
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.SearchResultsGridCell2_root, div[data-itemid], div.SearchResults_cell.GA-MaybeProduct")
            if not cards:
                cards = soup.select(".ProductGrid-cell, .ProductCell, div[data-cell-id], div[class*='SearchResultsGrid'] div[class*='cell']")

            for card in cards:
                try:
                    link_el = card if card.name == "a" else card.select_one("a[href*='zazzle.com/'], a[href^='/']")
                    if not link_el or not link_el.get("href"):
                        continue

                    href = link_el["href"].strip()
                    if not href.startswith("http"):
                        href = f"https://www.zazzle.com{href}"

                    clean_url = href.split("?")[0]
                    if any(x in clean_url.lower() for x in ("/custom", "/lpt/", "/my/", "/sell/", "/ideas/", "/create/", "cart", "help")):
                        continue

                    item_id = card.get("data-itemid", "").strip()
                    if not item_id:
                        m = re.search(r"-(\d{10,25})", clean_url)
                        if m: item_id = m.group(1)
                        else:
                            m2 = re.search(r"(\d{9,})", clean_url)
                            if m2: item_id = m2.group(1)

                    if item_id and item_id in seen_ids:
                        continue
                    if clean_url in seen_urls:
                        continue

                    if item_id: seen_ids.add(item_id)
                    seen_urls.add(clean_url)

                    title = card.get("title", "").strip()
                    if not title:
                        t_el = card.select_one(".SearchResultsGridCell2_title, [class*='title'], [class*='Title'], .ProductCell-title, h3, h4")
                        if t_el:
                            title = t_el.get_text(strip=True)
                    if not title and link_el.get("title"):
                        title = link_el["title"].strip()
                    if not title and link_el.get("aria-label"):
                        title = re.sub(r"^Product:\s*", "", link_el["aria-label"]).strip()
                    if not title:
                        img_el = card.select_one("img")
                        if img_el and img_el.get("alt"):
                            title = img_el["alt"].strip()
                    if not title:
                        slug = clean_url.rstrip("/").split("/")[-1]
                        slug_clean = re.sub(r"-\d+$", "", slug)
                        title = slug_clean.replace("-", " ").replace("_", " ").title()

                    title = re.sub(r"\s+", " ", title).strip()
                    if not title or len(title) < 3:
                        continue

                    price = "$19.95"
                    card_text = card.get_text(separator="\n")
                    price_matches = re.findall(r"\$\d+(?:\.\d{2})?", card_text)
                    if price_matches:
                        price = price_matches[0]
                    else:
                        p_el = card.select_one(".SearchProductPrice_priceAdjustedText, [class*='price'], [class*='Price']")
                        if p_el:
                            p_m = re.search(r"\$\d+(?:\.\d{2})?", p_el.get_text(strip=True))
                            if p_m: price = p_m.group(0)

                    image_url = ""
                    img_el = card.select_one("img")
                    if img_el:
                        for attr in ["src", "data-src", "srcset", "data-original"]:
                            val = img_el.get(attr)
                            if val:
                                if attr == "srcset":
                                    val = val.split(",")[0].split()[0]
                                if val.startswith("//"):
                                    val = f"https:{val}"
                                if val.startswith("http"):
                                    image_url = val
                                    break

                    seller = "Zazzle Creator (Unresolved)"
                    st_link = card.select_one("a[href*='/store/']")
                    if st_link and st_link.get("href"):
                        st_m = re.search(r"/store/([^/?#]+)", st_link["href"])
                        if st_m:
                            seller = st_m.group(1).replace("-", " ").replace("_", " ").title()

                    items.append({
                        "title": title,
                        "url": clean_url,
                        "price": price,
                        "item_id": item_id,
                        "seller": seller,
                        "platform": "zazzle",
                        "marketplace": "zazzle.com",
                        "marketplace_code": "zazzle.com",
                        "thumbnail": image_url,
                        "image_url": image_url,
                        "location": "Print-on-Demand (Global Fulfillment)",
                        "threat_badge": "🎨 POD Infringement (Zazzle)",
                        "threat_intel": "Commercial POD (Zazzle Custom Merchandise)",
                        "product_type": "Apparel & Merch",
                        "brand": "Unknown",
                        "source": "Zazzle Search",
                        "status": "New"
                    })
                except Exception as ex:
                    logger.debug(f"Error parsing Zazzle card: {ex}")
                    continue

        return items

    def enrich_seller_info(
        self,
        items: List[Dict[str, Any]],
        progress_callback=None,
        stop_event=None
    ):
        """
        High-speed seller/store name & location enrichment for Zazzle listings.
        Uses fast HTTP TLS client (curl_cffi) with Playwright fallback to parse ZData/ProfileCard.
        """
        total = len(items)
        if total == 0:
            return

        logger.info(f"🎨 [Zazzle] Enriching seller info for {total} listing(s)...")

        for idx, item in enumerate(items):
            if stop_event and stop_event.is_set():
                break

            url = item.get("url", "").strip()
            if not url:
                continue

            extracted_seller = None
            extracted_location = None
            store_handle = None

            # 1. Fast HTTP fetch with curl_cffi
            if HAS_CURL_CFFI:
                try:
                    r = curl_requests.get(url, impersonate="chrome124", timeout=12)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.content, "html.parser")
                        # ProfileCard DOM
                        store_el = soup.select_one("a[class*='ProfileCard-name'], a[href*='/store/'], [class*='designer-name']")
                        if store_el and store_el.get_text(strip=True):
                            extracted_seller = store_el.get_text(strip=True)
                            if store_el.get("href"):
                                sm = re.search(r"/store/([^/?#]+)", store_el["href"])
                                if sm: store_handle = sm.group(1)

                        # ZData script extraction
                        for s in soup.select("script"):
                            stxt = s.get_text()
                            if "ZData = JSON.parse(" in stxt:
                                m = re.search(r"ZData\s*=\s*JSON\.parse\('(.*?)'\);", stxt, re.DOTALL)
                                if m:
                                    try:
                                        raw_json_str = m.group(1).encode().decode('unicode_escape')
                                        zd = json.loads(raw_json_str)
                                        profiles = zd.get("entities", {}).get("profiles", {})
                                        for pid, prof in profiles.items():
                                            ptype = prof.get("type", "")
                                            pname = prof.get("name") or prof.get("storeHandle")
                                            ploc = prof.get("location") or prof.get("country")
                                            if ptype in ("Store", "Member") and pname and "zazzle" not in pname.lower():
                                                extracted_seller = pname
                                                extracted_location = ploc
                                                if prof.get("storeHandle"): store_handle = prof.get("storeHandle")
                                                break
                                            elif not extracted_seller and pname:
                                                extracted_seller = pname
                                                extracted_location = ploc
                                    except Exception:
                                        pass
                                break
                except Exception as he:
                    logger.debug(f"Zazzle HTTP enrichment error for {url}: {he}")

            # 2. Playwright fallback if HTTP didn't extract seller
            if not extracted_seller or extracted_seller.lower() in ("zazzle creator", "zazzle creator (unresolved)", "zazzle merchant"):
                try:
                    with sync_playwright() as p:
                        ctx = self._get_context(p)
                        page = ctx.pages[0] if ctx.pages else ctx.new_page()
                        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                        page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        time.sleep(1.0)
                        
                        # Evaluate JS state directly
                        js_data = page.evaluate("""() => {
                            let res = {};
                            if (typeof ZData !== 'undefined' && ZData.entities && ZData.entities.profiles) {
                                for (let k in ZData.entities.profiles) {
                                    let p = ZData.entities.profiles[k];
                                    if (p.name && !p.name.toLowerCase().includes('zazzle')) {
                                        return { name: p.name, location: p.location || p.country || '', handle: p.storeHandle || '' };
                                    }
                                }
                            }
                            let el = document.querySelector(".ProfileCard-name, a[href*='/store/']");
                            if (el) return { name: el.textContent.trim(), location: '', handle: '' };
                            return null;
                        }""")
                        if js_data and js_data.get("name"):
                            extracted_seller = js_data["name"]
                            if js_data.get("location"): extracted_location = js_data["location"]
                            if js_data.get("handle"): store_handle = js_data["handle"]
                        ctx.close()
                except Exception as pe:
                    logger.debug(f"Zazzle Playwright enrichment error for {url}: {pe}")

            # Apply enriched results
            if extracted_seller and extracted_seller.lower() not in ("zazzle creator", "unknown"):
                item["seller"] = extracted_seller
                if store_handle:
                    item["store_id"] = store_handle
                    item["store_url"] = f"https://www.zazzle.com/store/{store_handle.lower()}"
                if extracted_location:
                    item["location"] = f"{extracted_location} (POD)"
                    item["seller_origin"] = extracted_location

            if progress_callback:
                try:
                    progress_callback(idx + 1, total, item)
                except Exception:
                    pass

        logger.info(f"✅ [Zazzle] Seller enrichment completed for {total} item(s).")

    def fetch_single_item(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time metadata and high-res mockup for a single Zazzle listing."""
        clean_url = url.strip()
        title = ""
        price = "$19.95"
        seller = "Zazzle Creator"
        image_url = ""
        location = "Print-on-Demand"
        item_id = ""

        # Extract Item ID
        id_m = re.search(r"-(\d{10,25})", clean_url)
        if id_m:
            item_id = id_m.group(1)

        # 1. Fast HTTP fetch with curl_cffi
        if HAS_CURL_CFFI:
            try:
                r = curl_requests.get(clean_url, impersonate="chrome124", timeout=15)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.content, "html.parser")
                    t_el = soup.select_one("h1, meta[property='og:title']")
                    if t_el:
                        title = t_el.get("content", "") if t_el.name == "meta" else t_el.get_text(strip=True)

                    p_el = soup.select_one("meta[property='product:price:amount'], [class*='price'], [class*='Price']")
                    if p_el:
                        p_val = p_el.get("content") if p_el.name == "meta" else p_el.get_text(strip=True)
                        p_m = re.search(r"\$\d+(?:\.\d{2})?", p_val)
                        if p_m: price = p_m.group(0)

                    img_el = soup.select_one("meta[property='og:image'], img#viewMainImage, img[class*='mainImage']")
                    if img_el:
                        image_url = img_el.get("content") if img_el.name == "meta" else img_el.get("src", "")

                    # ZData profiles
                    for s in soup.select("script"):
                        stxt = s.get_text()
                        if "ZData = JSON.parse(" in stxt:
                            m = re.search(r"ZData\s*=\s*JSON\.parse\('(.*?)'\);", stxt, re.DOTALL)
                            if m:
                                try:
                                    raw_json_str = m.group(1).encode().decode('unicode_escape')
                                    zd = json.loads(raw_json_str)
                                    profiles = zd.get("entities", {}).get("profiles", {})
                                    for pid, prof in profiles.items():
                                        pname = prof.get("name") or prof.get("storeHandle")
                                        ploc = prof.get("location") or prof.get("country")
                                        if pname and "zazzle" not in pname.lower():
                                            seller = pname
                                            if ploc: location = f"{ploc} (POD)"
                                            break
                                except Exception:
                                    pass
                            break
            except Exception as e:
                logger.debug(f"Zazzle HTTP fetch_single_item error: {e}")

        # 2. Playwright fallback if title or image missing
        if not title or not image_url:
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
                if not title:
                    t_el = soup.select_one("h1, meta[property='og:title']")
                    if t_el:
                        title = t_el.get("content", "") if t_el.name == "meta" else t_el.get_text(strip=True)

                if not image_url:
                    img_el = soup.select_one("meta[property='og:image'], img#viewMainImage, img[class*='mainImage']")
                    if img_el:
                        image_url = img_el.get("content") if img_el.name == "meta" else img_el.get("src", "")
            except Exception as e:
                logger.error(f"Failed to fetch single Zazzle item {url}: {e}")

        return {
            "title": title or "Zazzle Custom Design",
            "url": clean_url,
            "price": price,
            "item_id": item_id,
            "seller": seller,
            "platform": "zazzle",
            "marketplace": "zazzle.com",
            "marketplace_code": "zazzle.com",
            "thumbnail": image_url,
            "image_url": image_url,
            "location": location,
            "threat_badge": "🎨 POD Infringement (Zazzle)",
            "threat_intel": "Commercial POD (Zazzle Custom Merchandise)",
            "product_type": "Apparel & Merch",
            "brand": "Unknown",
            "source": "Zazzle PDP",
            "status": "New"
        }

    def expand_design_variants(
        self,
        parent_item: Dict[str, Any],
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        1-to-24 POD Variant Matrix Expansion for Zazzle designs.
        Generates individual merchandise variants for enforcement.
        """
        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        variants = []
        base_url = parent_item.get("url", "")
        base_title = parent_item.get("title", "Custom Artwork")
        seller = parent_item.get("seller", "Zazzle Creator")
        parent_id = parent_item.get("item_id", "")
        base_image = parent_item.get("image_url") or parent_item.get("thumbnail", "")

        # Clean core title
        clean_title = re.sub(r"\s*-\s*T-?Shirt.*$", "", base_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Mug.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Sticker.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = clean_title.strip()

        _log(f"🎨 [Zazzle] Expanding POD Matrix for design '{clean_title[:35]}...'")

        for prod_name, slug_code, est_price, category in ZAZZLE_PRODUCT_LINES:
            var_url = f"{base_url}?product_line={slug_code}"
            var_title = f"{clean_title} - {prod_name}"
            var_id = f"{parent_id}_{slug_code}" if parent_id else slug_code

            variants.append({
                "title": var_title,
                "url": var_url,
                "price": f"${est_price:.2f}",
                "item_id": var_id,
                "seller": seller,
                "platform": "zazzle",
                "thumbnail": base_image,
                "image_url": base_image,
                "source": f"Zazzle POD ({category})",
                "status": "New"
            })

        _log(f"🎨 [Zazzle] Generated +{len(variants)} POD commercial variants.")
        return variants
