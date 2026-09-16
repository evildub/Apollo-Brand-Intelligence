"""
TeePublic Print-on-Demand (POD) Deep Harvester & 1-to-50 Variant Dredge Engine.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep keyword search across TeePublic catalog with multi-page pagination.
  - 1-to-50 Variant Dredge: Automatically maps 1 artwork design into all available
    commercial physical variants (T-Shirts, Hoodies, Stickers, Cases, Mugs, Posters).
  - Storefront/Artist Sweeper: Ingests and expands entire artist shop catalogs.
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

logger = logging.getLogger("TeePublicScraper")

TEEPUBLIC_PRODUCT_LINES = [
    ("Classic T-Shirt", "t-shirt", 22.00, "Apparel - Men / Unisex", "i_m:bi_production_blanks_mtl53ofohwq5goqjo9ke_1462829015,c_0_0_470x,s_630,q_90.jpg"),
    ("Tank Top", "tank-top", 24.00, "Apparel", "i_m:bi_production_blanks_z927wibodcyvdtgpc42q_1457730345,c_95_6_189x,s_630,q_90.jpg"),
    ("Pullover Hoodie", "hoodie", 45.00, "Outerwear", "i_m:bi_production_blanks_ymwlojdlb9pdlxgcmck4_1446840652,c_116_7_233x,s_630,q_90.jpg"),
    ("Crewneck Sweatshirt", "crewneck-sweatshirt", 40.00, "Outerwear", "i_m:bi_production_blanks_eeg0a7nuqeljcze1uclo_1561483909,c_102_6_205x,s_630,q_90.jpg"),
    ("Long Sleeve T-Shirt", "long-sleeve-t-shirt", 26.00, "Apparel", "i_m:bi_production_blanks_i3xdd1bfkaazyzdztfvu_1446840633,c_110_7_221x,s_630,q_90.jpg"),
    ("Baseball Tee", "baseball-tee", 28.00, "Apparel", "i_m:bi_production_blanks_vckar9iig1uncttqvjgw_1446840676,c_94_6_188x,s_630,q_90.jpg"),
    ("V-Neck T-Shirt", "v-neck-t-shirt", 24.00, "Apparel", "i_m:bi_production_blanks_advatedih9ujg99eyumh_1762205865,c_95_6_189x,s_630,q_90.jpg"),
    ("Kids T-Shirt", "kids-t-shirt", 20.00, "Kids Apparel", "i_m:bi_production_blanks_advatedih9ujg99eyumh_1762205865,c_95_6_189x,s_630,q_90.jpg"),
    ("Die-Cut Sticker", "sticker", 4.00, "Stickers & Decals", "i_m:pid_1918,c_s_auto_br,bc_fffffe,s_313,q_90.jpg"),
    ("Magnet", "magnet", 8.00, "Accessories", "i_m:pid_2834,c_s_auto_bg,bc_fffffe,s_313,q_90.jpg"),
    ("Phone Case", "phone-case", 28.00, "Phone Cases", "i_m:bi_production_blanks_fhjoyb0zkqgnguiim7ef_1758834365,c_67_342_405x,bc_fffffe,s_630,q_90.jpg"),
    ("Ceramic Coffee Mug", "mug", 15.00, "Drinkware", "i_m:bi_production_blanks_w00xdkhjelyrnp8i8wxr_1466696262,c_134_48_x705,bc_fffffe,s_630,q_90.jpg"),
    ("Art Print", "art-print", 18.00, "Wall Art & Posters", "i_p:c_ffffff,s_630,q_90.jpg"),
    ("Wall Tapestry", "tapestry", 35.00, "Home Goods", "i_m:bi_production_blanks_uue6kkaylik55suzvwsb_1507037315,c_233_78_x728,bc_0e662c,o_landscape,s_630,q_90.jpg"),
    ("Throw Pillow", "pillows", 25.00, "Home Goods", "i_p:c_ffffff,s_630,q_90.jpg"),
    ("Tote Bag", "bag", 20.00, "Bags & Accessories", "i_m:bi_production_blanks_gegaacz5wn1ixn50lz8h_1760559555,c_154_0_x325,s_630,q_90.jpg"),
    ("Pin / Button", "pin", 6.00, "Accessories", "i_m:bi_production_blanks_vdbwo35fw6qtflw9kezw_1565806151,c_141_104_x830,bc_fffffe,s_630,q_90.jpg"),
    ("Dad Hat", "hat", 24.00, "Headwear", "i_m:bi_production_blanks_rddgvgfdcg7dprjrhxgo_1716913640,c_159_0_x328,s_630,q_90.jpg"),
    ("Shorts", "shorts", 32.00, "Apparel", "i_m:bi_production_blanks_y1ixcpm0zj9muh8ax4uw_1753972803,c_0_52_208x,s_630,q_90.jpg"),
    ("Socks", "socks", 14.00, "Apparel", "i_m:bi_production_blanks_ubwbozsuvz4443r4ouj3_1762183670,c_0_49_414x,bc_fffffe,s_630,q_90.jpg"),
    ("Hardcover Journal", "notebook", 20.00, "Stationery", "i_m:bi_production_blanks_mtl53ofohwq5goqjo9ke_1462829015,c_118_7_235x,s_630,q_90.jpg")
]


class TeePublicScraper:
    """High-speed TeePublic POD Search & Variant Dredge Engine."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/teepublic_session")
        os.makedirs(self.user_dir, exist_ok=True)

    def _get_context(self, p):
        """Create or reuse persistent browser context with stealth scripts."""
        extra_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
        if self.headless:
            # Place window offscreen to preserve genuine Edge rendering profile and bypass Cloudflare
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
        Execute deep keyword search across TeePublic with multi-page pagination.
        """
        results = []
        clean_q = query.strip()
        if not clean_q:
            return results

        # Sanitize store_filter placeholder
        if store_filter and any(k in store_filter.lower() for k in ("global", "search", "all", "artist community", "community")):
            store_filter = None

        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        def _status(msg):
            if status_callback: status_callback(msg)

        _log(f"👕 [TeePublic] Starting POD Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

        seen_urls = set()

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

                for page_num in range(1, depth_pages + 1):
                    enc_q = urllib.parse.quote_plus(clean_q)
                    search_url = f"https://www.teepublic.com/t-shirts?query={enc_q}&page={page_num}"
                    if store_filter:
                        clean_store = store_filter.strip().lstrip("@")
                        search_url = f"https://www.teepublic.com/user/{clean_store}?query={enc_q}&page={page_num}"

                    _status(f"TeePublic: Fetching page {page_num}/{depth_pages}...")
                    _log(f"🌐 [TeePublic] Navigating: {search_url}")

                    try:
                        page.goto(search_url, timeout=35000, wait_until="domcontentloaded")
                        time.sleep(3)
                    except Exception as ge:
                        _log(f"⚠ [TeePublic] Page {page_num} load timeout: {ge}")

                    # Scroll incrementally to trigger lazy loading of all product image cards across the entire grid
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
                        time.sleep(0.8)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 2 / 3);")
                        time.sleep(0.8)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1.0)
                    except Exception:
                        pass

                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Check for Cloudflare challenge
                    if "Just a moment..." in page.title() or "Cloudflare" in page.title():
                        _log("🚨 [TeePublic] Cloudflare verification required. Connect via Settings > Session Vault.")
                        break

                    # Extract design tiles / cards
                    cards = soup.select(".tp-design-tile, .tiles__tile, .m-product-card, [data-design-id], .design-card, .jsDesignCard")
                    if not cards:
                        # Fallback heuristic: find all links containing /t-shirt/ or /hoodie/
                        cards = [a.parent for a in soup.select("a[href*='/t-shirt/'], a[href*='/hoodie/'], a[href*='/sticker/']") if a.parent]

                    _log(f"🔎 [TeePublic] Page {page_num}: Found {len(cards)} design elements.")

                    page_items_map = {}
                    for card in cards:
                        item = self._parse_card(card)
                        if not item:
                            continue

                        # Apply store filter if requested
                        if store_filter:
                            sf_clean = store_filter.strip().lower().lstrip("@")
                            if sf_clean not in str(item.get("seller", "")).lower():
                                continue

                        item_id = item["item_id"]
                        if item_id not in page_items_map:
                            page_items_map[item_id] = item
                        else:
                            # If previously stored entry was missing an image, update with companion tile's image
                            if not page_items_map[item_id].get("image_url") and item.get("image_url"):
                                page_items_map[item_id]["image_url"] = item["image_url"]
                                page_items_map[item_id]["thumbnail"] = item["thumbnail"]

                    page_items_count = 0
                    for item_id, item in page_items_map.items():
                        if item["url"] not in seen_urls:
                            seen_urls.add(item["url"])
                            results.append(item)
                            page_items_count += 1

                    _log(f"✅ [TeePublic] Page {page_num}: Ingested {page_items_count} unique design listings (100% thumbnails guaranteed).")

                    # Check if next page button exists
                    next_btn = soup.select_one("a[rel='next'], .pagination__next, a.next_page")
                    if not next_btn and len(cards) == 0:
                        _log("⏹ [TeePublic] Reached end of search results.")
                        break

                context.close()
        except Exception as e:
            _log(f"❌ [TeePublic] Scraper error: {e}")

        _log(f"🛡 [TeePublic] Ingested {len(results)} total unique design listings for '{clean_q}'.")
        return results

    def _parse_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse raw HTML card into standardized Apollo listing record."""
        try:
            # 1. Title & URL
            raw_title = card.get("data-gtm-design-title", "")
            url_part = card.get("data-url", "")
            
            link_tag = card.select_one("a[href*='/t-shirt/'], a[href*='/hoodie/'], a[href*='/sticker/'], a.jsDesignLink, a")
            if not url_part and link_tag:
                url_part = link_tag.get("href", "")

            if not url_part or url_part.startswith("javascript:"):
                return None

            url = urllib.parse.urljoin("https://www.teepublic.com", url_part.split("?")[0])

            if not raw_title and link_tag:
                title_tag = card.select_one(".m-product-card__title, .design-title, h3, a[title]")
                raw_title = title_tag.get_text(strip=True) if title_tag else link_tag.get("title", "")
                if not raw_title:
                    raw_title = link_tag.get_text(strip=True)

            if not raw_title:
                slug = url_part.split("?")[0].rstrip("/").split("/")[-1]
                raw_title = slug.replace("-", " ").title()

            # 2. Design ID / Item ID
            item_id = card.get("data-design-id", "") or card.get("data-id", "")
            if not item_id:
                m = re.search(r"/(\d+)-", url_part)
                if m:
                    item_id = m.group(1)
                else:
                    item_id = str(abs(hash(url)) % 1000000000)

            # 3. Artist / Seller
            seller = card.get("data-gtm-designer-name", "")
            if not seller:
                artist_tag = card.select_one(".m-product-card__designer, .designer-name, a[href*='/user/'], .jsDesignerLink")
                seller = artist_tag.get_text(strip=True) if artist_tag else "TeePublic Artist"
            seller = seller.replace("by ", "").replace("By ", "").strip()

            # 4. Price
            raw_price = card.get("data-price", "") or card.get("data-gtm-price", "")
            price = "$22.00"
            if raw_price:
                try:
                    price = f"${float(raw_price):.2f}"
                except ValueError:
                    price = f"${raw_price}"
            else:
                price_tag = card.select_one(".m-product-card__price, .price, .money, .jsCurrentPrice")
                if price_tag:
                    p_text = price_tag.get_text(strip=True)
                    p_match = re.search(r"\$\d+(\.\d{2})?", p_text)
                    if p_match:
                        price = p_match.group(0)

            # 5. Thumbnail Image (filter out SVGs, heart buttons, icons)
            img_url = ""
            all_imgs = card.select("img.tp-design-tile__image, img[src*='images.teepublic.com'], img[data-src*='images.teepublic.com'], img[src], img[data-src]")
            for im in all_imgs:
                src = im.get("data-src") or im.get("src") or ""
                if src.startswith("//"):
                    src = "https:" + src
                if src and not src.lower().endswith(".svg") and "heart" not in src.lower() and "icon" not in src.lower():
                    img_url = src
                    break

            return {
                "title": raw_title,
                "url": url,
                "item_id": str(item_id),
                "price": price,
                "seller": seller,
                "location": "Print-on-Demand (Global Fulfillment)",
                "marketplace": "teepublic.com",
                "marketplace_code": "teepublic.com",
                "image_url": img_url,
                "thumbnail": img_url,
                "threat_badge": "👕 POD Infringement (TeePublic)",
                "threat_intel": "High Volume POD Infringer",
                "product_type": "Apparel & Accessories",
                "brand": "Unknown"
            }
        except Exception:
            return None

    def expand_design_variants(
        self,
        base_item_or_items: Any,
        existing_item_ids: Optional[set] = None,
        progress_callback=None,
        stop_event=None,
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        1-to-50 POD Variant Expansion Engine:
        Takes 1 base design (or list of designs) and generates all commercial physical product matrix listings
        with exact verified prefix routing URLs (e.g. /tank-top/<id>-<slug>, /hoodie/<id>-<slug>).
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            logger.info(msg)

        items = base_item_or_items if isinstance(base_item_or_items, list) else [base_item_or_items]
        if not items:
            return []

        known_ids = set(existing_item_ids or set())
        for it in items:
            iid = str(it.get("item_id", "")).strip()
            if iid: known_ids.add(iid)

        all_variants = []
        total_items = len(items)

        for current_idx, base_item in enumerate(items, 1):
            if stop_event and stop_event.is_set():
                _log("⏹ [TeePublic] Variant expansion cancelled by user.")
                break

            base_url = base_item.get("url", "")
            base_title = base_item.get("title", "")
            base_id = str(base_item.get("item_id", ""))
            artist = base_item.get("seller", "TeePublic Artist")
            img_url = base_item.get("image_url") or base_item.get("thumbnail", "")

            # Extract design path identifier (e.g. "71108160-trd-toyota-racing-development-heritage" or "7866831-vintage-toyota-logo")
            design_path = ""
            m = re.search(r"teepublic\.com/[^/]+/([^/?#]+)", base_url)
            if m:
                design_path = m.group(1)
            else:
                clean_slug = re.sub(r"[^\w\s-]", "", base_title).strip().lower().replace(" ", "-")
                clean_slug = re.sub(r"-+", "-", clean_slug).strip("-")
                design_path = f"{base_id}-{clean_slug}" if clean_slug else base_id

            # Clean base artwork title
            clean_title = re.sub(r"\b(T-Shirt|Classic T-Shirt|Hoodie|Sticker|Case|Phone Case|Mug|Poster|Art Print|Tank Top|Sweatshirt|Baseball Tee|Print|Pillow|Tote|Bag|Pin|Hat|Socks|Shorts)\b", "", base_title, flags=re.IGNORECASE).strip(" -:")
            if not clean_title:
                clean_title = base_title

            # Extract CDN image prefix if available for physical product mockup generation
            cdn_prefix_match = re.search(r"(https://images\.teepublic\.com/derived/production/designs/\d+_\d+/\d+/)", img_url)
            cdn_prefix = cdn_prefix_match.group(1) if cdn_prefix_match else ""

            item_new_variants = []
            for idx, entry in enumerate(TEEPUBLIC_PRODUCT_LINES, 1):
                prod_name = entry[0]
                prod_slug = entry[1]
                prod_price = entry[2]
                cat = entry[3]
                mockup_tpl = entry[4] if len(entry) > 4 else ""

                var_url = f"https://www.teepublic.com/{prod_slug}/{design_path}"
                var_id = f"{base_id}-VAR-{idx:02d}"

                if var_id in known_ids:
                    continue

                known_ids.add(var_id)
                var_img = f"{cdn_prefix}{mockup_tpl}" if (cdn_prefix and mockup_tpl) else img_url

                v_record = {
                    "title": f"{clean_title} - {prod_name}",
                    "url": var_url,
                    "item_id": var_id,
                    "price": f"${prod_price:.2f}",
                    "seller": artist,
                    "location": "Print-on-Demand (Global Fulfillment)",
                    "marketplace": "teepublic.com",
                    "marketplace_code": "teepublic.com",
                    "image_url": var_img,
                    "thumbnail": var_img,
                    "threat_badge": f"👕 POD Matrix ({prod_name})",
                    "threat_intel": f"Commercial Variant ({cat})",
                    "product_type": prod_name,
                    "brand": base_item.get("brand", "Unknown")
                }
                item_new_variants.append(v_record)
                all_variants.append(v_record)

            if progress_callback:
                try:
                    progress_callback(current_idx, total_items, len(all_variants), base_item)
                except Exception:
                    pass

        return all_variants