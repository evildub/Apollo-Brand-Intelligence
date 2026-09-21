"""
Spreadshirt & Spreadshop Print-on-Demand (POD) Deep Harvester & Variant Dredge Engine.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep keyword search across Spreadshirt marketplace with multi-page pagination.
  - 1-to-30 Variant Dredge: Automatically maps 1 artwork design into all available
    commercial physical variants (T-Shirts, Hoodies, Stickers, Water Bottles, Mugs, Hats, Bags).
  - Storefront/Designer Sweeper: Ingests and expands entire designer / spreadshop catalogs.
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

logger = logging.getLogger("SpreadshirtScraper")

SPREADSHIRT_PRODUCT_LINES = [
    ("Men's Premium T-Shirt", "mens-premium-t-shirt", 24.99, "Apparel - Men", "T210", 1),
    ("Women's Premium T-Shirt", "womens-premium-t-shirt", 24.99, "Apparel - Women", "T813", 1),
    ("Men's Premium Hoodie", "mens-premium-hoodie", 59.99, "Outerwear", "T20", 1),
    ("Unisex Full Zip Hoodie", "unisex-full-zip-hoodie", 61.99, "Outerwear", "T93", 1),
    ("Women's Premium Organic Zip Hoodie", "womens-premium-organic-zip-hoodie", 59.99, "Outerwear", "T445", 1),
    ("Kid's Premium Organic T-Shirt", "kids-premium-organic-t-shirt", 24.99, "Kids Apparel", "T635", 1),
    ("Kids Premium Hoodie", "kids-premium-hoodie", 36.99, "Kids Apparel", "T654", 1),
    ("Toddler Premium T-Shirt", "toddler-premium-t-shirt", 24.99, "Kids Apparel", "T210", 1),
    ("Baby Bib", "baby-bib", 21.99, "Baby & Toddler", "T1094", 1),
    ("Die-Cut Sticker Size S", "sticker-size-s", 2.99, "Stickers & Decals", "T1459", 1),
    ("Die-Cut Sticker Size L", "sticker-size-l", 7.99, "Stickers & Decals", "T1459", 1),
    ("Snapback Baseball Cap", "snapback-baseball-cap", 26.99, "Headwear", "T1462", 1),
    ("Trucker Cap", "trucker-cap", 24.99, "Headwear", "T1462", 1),
    ("Bandana", "bandana", 19.99, "Accessories", "T1462", 1),
    ("Unisex Joggers", "unisex-joggers", 36.99, "Apparel", "T3940", 1),
    ("Adjustable Apron", "adjustable-apron", 27.99, "Home & Kitchen", "T1426", 1),
    ("Fanny Pack", "fanny-pack", 24.99, "Bags & Accessories", "T1586", 1),
    ("Tote Bag", "tote-bag", 21.99, "Bags & Accessories", "T1613", 1),
    ("Ceramic Coffee Mug", "mug", 16.99, "Drinkware", "T949", 1),
    ("Coffee/Tea Mug", "coffeetea-mug", 19.99, "Drinkware", "T31", 1),
    ("Cotton Drawstring Bag", "cotton-drawstring-bag", 21.99, "Bags & Accessories", "T1367", 1),
    ("Mouse pad Horizontal", "mouse-pad-horizontal", 19.99, "Accessories", "T993", 1),
    ("20 oz Water Bottle", "water-bottle", 21.99, "Drinkware", "T949", 1),
    ("17 oz Insulated Stainless Bottle", "insulated-bottle", 26.99, "Drinkware", "T949", 1),
    ("Phone Case", "phone-case", 24.99, "Phone Cases", "T1459", 1),
    ("Pillow", "throw-pillow", 27.99, "Home Goods", "T1613", 1)
]


def normalize_text_for_match(text: str) -> str:
    """Normalize text by lowercasing and stripping non-alphanumeric chars."""
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


def clean_spreadshirt_text(text: str) -> str:
    """Clean raw Spreadshirt card text by stripping badges, newlines, and prices."""
    if not text:
        return ""
    t = str(text).replace("\xa0", " ").replace("\r", " ")
    lines = [s.strip() for s in t.split("\n") if s.strip()]
    cleaned_lines = []
    for l in lines:
        if re.search(r"^(from\s+)?\$\d+(\.\d{2})?$", l, re.IGNORECASE):
            continue
        if re.match(r"^\+\s*\d+.*$", l) or l.lower() in ("new", "sustainable", "bestseller", "organic", "+"):
            continue
        if re.match(r"^by\s+", l, re.IGNORECASE):
            continue
        cleaned_lines.append(l)
    return " ".join(cleaned_lines).strip()


def build_variant_title(base_title: str, raw_variant_text: str, href: str) -> str:
    """Construct a clean, non-duplicated '<Design Name> - <Product Type>' title."""
    clean_base = clean_spreadshirt_text(base_title)
    if " - " in clean_base:
        clean_base = clean_base.split(" - ")[0].strip()

    clean_var = clean_spreadshirt_text(raw_variant_text)

    if not clean_var:
        slug = href.split("/design/")[-1].split("-D")[0].split("?")[0]
        clean_var = slug.replace("+", " ").replace("-", " ").title()

    norm_base = normalize_text_for_match(clean_base)
    norm_var = normalize_text_for_match(clean_var)

    # If the variant text contains the design name prefix, strip it
    if norm_base and norm_var.startswith(norm_base):
        var_words = clean_var.split()
        curr_norm = ""
        split_idx = 0
        for idx, w in enumerate(var_words):
            curr_norm += normalize_text_for_match(w)
            if curr_norm == norm_base:
                split_idx = idx + 1
                break
        if split_idx > 0 and split_idx < len(var_words):
            clean_var = " ".join(var_words[split_idx:]).strip(" -:")
        else:
            clean_var = ""

    # If variant text is empty or duplicate of base, parse product from slug
    if not clean_var or normalize_text_for_match(clean_var) == norm_base:
        slug = href.split("/design/")[-1].split("-D")[0].split("?")[0]
        slug_clean = slug.replace("+", " ").replace("-", " ")
        if norm_base:
            words_to_remove = set(re.findall(r"[a-z0-9]+", clean_base.lower()))
            slug_words = [w for w in slug_clean.split() if w.lower() not in words_to_remove]
            slug_clean = " ".join(slug_words)
        clean_var = slug_clean.strip().title()

    if not clean_var:
        clean_var = "Merchandise"

    return f"{clean_base} - {clean_var}"


class SpreadshirtScraper:
    """High-speed Spreadshirt POD Search & Variant Dredge Engine."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/spreadshirt_session")
        os.makedirs(self.user_dir, exist_ok=True)

    def _get_context(self, p):
        """Create or reuse persistent browser context with stealth scripts."""
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
        Execute deep keyword search across Spreadshirt with multi-page pagination.
        """
        results = []
        clean_q = query.strip()
        if not clean_q:
            return results

        # Sanitize store_filter placeholder
        if store_filter and any(k in store_filter.lower() for k in ("global", "search", "all", "community", "spreadshop")):
            store_filter = None

        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        def _status(msg):
            if status_callback: status_callback(msg)

        _log(f"🌿 [Spreadshirt] Starting POD Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

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
                        search_url = f"https://www.spreadshirt.com/user/{clean_store}?page={page_num}"
                    else:
                        search_url = f"https://www.spreadshirt.com/shop/{enc_q}/?page={page_num}"

                    _status(f"Spreadshirt: Fetching page {page_num}/{depth_pages}...")
                    _log(f"🌐 [Spreadshirt] Navigating: {search_url}")

                    try:
                        page.goto(search_url, timeout=35000, wait_until="domcontentloaded")
                        time.sleep(2.5)
                    except Exception as ge:
                        _log(f"⚠ [Spreadshirt] Page {page_num} load timeout: {ge}")

                    # Incremental scroll to trigger lazy loading of all product cards
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
                        time.sleep(0.7)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 2 / 3);")
                        time.sleep(0.7)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1.0)
                    except Exception:
                        pass

                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Check for Cloudflare challenge
                    if "Just a moment..." in page.title() or "Cloudflare" in page.title():
                        _log("🚨 [Spreadshirt] Cloudflare verification required. Connect via Settings > Session Vault.")
                        break

                    # Extract design tiles / cards
                    cards = soup.select("a[href*='/shop/design/'], a[href*='/design/']")
                    _log(f"🔎 [Spreadshirt] Page {page_num}: Found {len(cards)} design elements.")

                    page_items_count = 0
                    for card in cards:
                        item = self._parse_card(card)
                        if not item:
                            continue

                        # Apply store filter if requested
                        if store_filter:
                            sf_clean = store_filter.strip().lower().lstrip("@")
                            if sf_clean not in str(item.get("seller", "")).lower():
                                continue

                        if item["url"] not in seen_urls:
                            seen_urls.add(item["url"])
                            results.append(item)
                            page_items_count += 1

                    _log(f"✅ [Spreadshirt] Page {page_num}: Ingested {page_items_count} unique design listings.")

                    # Check if next page exists
                    if len(cards) == 0:
                        _log("⏹ [Spreadshirt] Reached end of search results.")
                        break

                context.close()
        except Exception as e:
            _log(f"❌ [Spreadshirt] Scraper error: {e}")

        _log(f"🛡 [Spreadshirt] Ingested {len(results)} total unique design listings for '{clean_q}'.")
        return results

    def _parse_card(self, a_tag) -> Optional[Dict[str, Any]]:
        """Parse raw HTML anchor into standardized Apollo listing record."""
        try:
            href = a_tag.get("href", "")
            if not href or ("/shop/design/" not in href and "/design/" not in href):
                return None

            full_url = urllib.parse.urljoin("https://www.spreadshirt.com", href)

            # 1. Extract Design ID / Item ID
            item_id = ""
            m_des = re.search(r"-D([a-fA-F0-9]+)", href)
            if m_des:
                item_id = f"D{m_des.group(1)}"
            else:
                m_sell = re.search(r"sellable=([a-zA-Z0-9_\-]+)", href)
                if m_sell:
                    item_id = m_sell.group(1)
                else:
                    item_id = str(abs(hash(full_url)) % 1000000000)

            # 2. Extract Thumbnail Image
            img_el = a_tag.select_one("img")
            img_url = ""
            if img_el:
                img_url = img_el.get("src") or img_el.get("data-src") or img_el.get("data-original") or ""
                if not img_url:
                    srcset = img_el.get("srcset") or img_el.get("data-srcset") or ""
                    if srcset:
                        parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
                        if parts:
                            img_url = parts[-1]
            if not img_url:
                parent_tile = a_tag.find_parent(class_=re.compile(r"article|product|card|tile|item", re.I))
                if parent_tile:
                    p_img = parent_tile.select_one("img")
                    if p_img:
                        img_url = p_img.get("src") or p_img.get("data-src") or p_img.get("data-original") or ""
            if img_url.startswith("//"):
                img_url = "https:" + img_url

            # 3. Text decomposition
            raw_lines = [s.strip() for s in a_tag.get_text(separator="\n").split("\n") if s.strip()]

            price = "$24.99"
            seller = "Spreadshirt Creator"
            product_type = "Apparel"
            title = ""
            text_lines = []

            for line in raw_lines:
                if re.search(r"^(from\s+)?\$\d+(\.\d{2})?$", line, re.I):
                    price = line
                elif re.match(r"^by\s+", line, re.I):
                    seller = re.sub(r"^by\s+", "", line, flags=re.I).strip()
                elif re.match(r"^\+\s*\d+.*$", line) or line.lower() in ("sustainable", "new", "bestseller", "+", "organic"):
                    continue
                else:
                    text_lines.append(line)

            for line in text_lines:
                if any(w in line.lower() for w in ["t-shirt", "hoodie", "sticker", "bib", "sweatshirt", "cap", "hat", "bandana", "bag", "joggers", "apron", "tank", "jacket", "mug", "dress", "pillow", "bottle", "case"]):
                    if not product_type or product_type == "Apparel":
                        product_type = line
                else:
                    if not title:
                        title = line

            if not title:
                slug = href.split("/design/")[-1].split("-D")[0].split("?")[0]
                slug_clean = slug.replace("+", " ").replace("-", " ")
                if product_type and product_type != "Apparel":
                    for pw in product_type.split():
                        slug_clean = re.sub(r"\b" + re.escape(pw) + r"\b", "", slug_clean, flags=re.I)
                title = slug_clean.strip().title()

            if not title:
                title = "Spreadshirt Design"

            full_title = title
            if product_type and product_type != "Apparel" and normalize_text_for_match(product_type) not in normalize_text_for_match(title):
                full_title = f"{title} - {product_type}"

            return {
                "title": full_title,
                "url": full_url,
                "item_id": item_id,
                "price": price,
                "seller": seller,
                "location": "Print-on-Demand (Global Fulfillment)",
                "marketplace": "spreadshirt.com",
                "marketplace_code": "spreadshirt.com",
                "image_url": img_url,
                "thumbnail": img_url,
                "threat_badge": "🌿 POD Infringement (Spreadshirt)",
                "threat_intel": f"Commercial POD ({product_type})",
                "product_type": product_type,
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
        1-to-30 POD Variant Expansion Engine:
        Dredges all physical merchandise listings sharing the same design ID.
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

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

                for current_idx, base_item in enumerate(items, 1):
                    if stop_event and stop_event.is_set():
                        _log("⏹ [Spreadshirt] Variant expansion cancelled by user.")
                        break

                    base_url = base_item.get("url", "")
                    base_title = base_item.get("title", "")
                    base_id = str(base_item.get("item_id", ""))
                    artist = base_item.get("seller", "Spreadshirt Creator")
                    img_url = base_item.get("image_url") or base_item.get("thumbnail", "")

                    # Extract numeric design ID (D<number>) from base item's image URL or page URL
                    m_d_num = re.search(r"D(\d+)", img_url)
                    d_num = m_d_num.group(1) if m_d_num else ""

                    _log(f"🌿 [Spreadshirt] Expanding variants for [{current_idx}/{total_items}]: '{base_title[:35]}...'")

                    found_on_pdp = False
                    if base_url.startswith("http"):
                        try:
                            page.goto(base_url, timeout=25000, wait_until="domcontentloaded")
                            time.sleep(1.8)

                            # Remove OneTrust cookie banner & overlay to unblock clicks
                            try:
                                page.evaluate("""() => {
                                    document.querySelectorAll('#onetrust-consent-sdk, .onetrust-pc-dark-filter, #onetrust-banner-sdk').forEach(el => el.remove());
                                    document.querySelector('#onetrust-accept-btn-handler')?.click();
                                }""")
                            except Exception:
                                pass

                            # Scroll into view so carousel section renders
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.35);")
                            time.sleep(0.8)

                            # Extract related products sharing design ID across all category tabs and carousels
                            m_d = re.search(r"-D([a-fA-F0-9]+)", base_url)
                            d_id = m_d.group(1) if m_d else ""
                            m_sell_base = re.search(r"sellable=([a-zA-Z0-9_\-]+)", base_url)
                            base_sell_id = m_sell_base.group(1) if m_sell_base else ""

                            pdp_variants = page.evaluate("""async (dId) => {
                                const targetPattern = dId ? `-D${dId}` : '/shop/design/';

                                function harvestCards() {
                                    const results = [];
                                    const anchors = Array.from(document.querySelectorAll(`a[href*="${targetPattern}"]`));
                                    for (const a of anchors) {
                                        const img = a.querySelector('img') || a.closest('div, li, article')?.querySelector('img');
                                        let imgSrc = "";
                                        if (img) {
                                            imgSrc = img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || "";
                                            if (!imgSrc && img.srcset) {
                                                const parts = img.srcset.split(',').map(s => s.trim().split(' ')[0]).filter(Boolean);
                                                if (parts.length > 0) imgSrc = parts[parts.length - 1];
                                            }
                                        }
                                        const text = a.innerText ? a.innerText.trim() : "";
                                        const href = a.href;
                                        if (href && (href.includes('/shop/design/') || href.includes('/design/'))) {
                                            results.push({
                                                href: href,
                                                text: text,
                                                img: imgSrc || null
                                            });
                                        }
                                    }
                                    return results;
                                }

                                const itemsMap = new Map();
                                for (const it of harvestCards()) {
                                    const key = it.href.split('?')[0] + (it.href.includes('sellable=') ? (it.href.match(/sellable=[^&]+/) || [''])[0] : '');
                                    if (key) itemsMap.set(key, it);
                                }

                                // Find all category tabs in related products / carousel container
                                const allButtons = Array.from(document.querySelectorAll('button, [role="tab"]'));
                                const categoryTabs = allButtons.filter(b => {
                                    const txt = b.innerText ? b.innerText.trim().toLowerCase() : "";
                                    return ['popular', 'men', 'women', 'kids', 'babies', 'accessories', 'home', 'living', 'stickers', 'all'].some(k => txt.includes(k));
                                });

                                for (const btn of categoryTabs) {
                                    try {
                                        btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                                        btn.click();
                                        await new Promise(r => setTimeout(r, 450));

                                        // Click next carousel buttons
                                        const container = btn.closest('section, div[class*="carousel"], div[class*="container"], div[class*="wrapper"]') || document;
                                        const nextBtns = Array.from(container.querySelectorAll('button[aria-label*="next" i], button[aria-label*="Next" i], button[class*="next" i], button[class*="Next" i]'));
                                        for (const nb of nextBtns) {
                                            for (let c = 0; c < 4; c++) {
                                                nb.click();
                                                await new Promise(r => setTimeout(r, 250));
                                            }
                                        }

                                        for (const it of harvestCards()) {
                                            const key = it.href.split('?')[0] + (it.href.includes('sellable=') ? (it.href.match(/sellable=[^&]+/) || [''])[0] : '');
                                            if (key && !itemsMap.has(key)) {
                                                itemsMap.set(key, it);
                                            }
                                        }
                                    } catch (e) {}
                                }

                                return Array.from(itemsMap.values());
                            }""", d_id)

                            if pdp_variants and len(pdp_variants) > 1:
                                found_on_pdp = True
                                for v in pdp_variants:
                                    v_href = v.get("href", "")
                                    if not v_href:
                                        continue

                                    # Skip exact same sellable ID as base item
                                    if base_sell_id and f"sellable={base_sell_id}" in v_href:
                                        continue
                                    elif not base_sell_id and v_href.split("?")[0] == base_url.split("?")[0]:
                                        continue

                                    v_text = v.get("text", "")
                                    v_img = v.get("img") or ""
                                    if v_img.startswith("//"):
                                        v_img = "https:" + v_img

                                    # Clean price and title
                                    lines = [l.strip() for l in v_text.split("\n") if l.strip()]
                                    v_price = "$24.99"
                                    for line in lines:
                                        p_m = re.search(r"^(from\s+)?\$\d+(\.\d{2})?$", line, re.I)
                                        if p_m:
                                            v_price = line
                                            break

                                    # Build clean non-duplicated title
                                    clean_v_title = build_variant_title(base_title, v_text, v_href)
                                    v_prod_type = clean_v_title.split(" - ")[-1] if " - " in clean_v_title else "Apparel"

                                    m_sell = re.search(r"sellable=([a-zA-Z0-9_\-]+)", v_href)
                                    if m_sell:
                                        v_id = f"{base_id}-{m_sell.group(1)}"
                                    else:
                                        v_id = str(abs(hash(v_href)) % 1000000000)

                                    if v_id in known_ids:
                                        continue

                                    known_ids.add(v_id)

                                    # If image was missing, generate mockup URL if design numeric ID is available
                                    if not v_img:
                                        if d_num:
                                            v_img = f"https://image.spreadshirtmedia.com/image-server/v1/products/T210A1PA4301PT17X0Y30D{d_num}W25000H25000/views/1,appearanceId=1.jpg?width=450&height=600&backgroundColor=F2F2F2"
                                        else:
                                            v_img = img_url

                                    v_rec = {
                                        "title": clean_v_title,
                                        "url": v_href,
                                        "item_id": v_id,
                                        "price": v_price,
                                        "seller": artist,
                                        "location": "Print-on-Demand (Global Fulfillment)",
                                        "marketplace": "spreadshirt.com",
                                        "marketplace_code": "spreadshirt.com",
                                        "image_url": v_img,
                                        "thumbnail": v_img,
                                        "threat_badge": f"🌿 POD Variant ({v_prod_type[:24]})",
                                        "threat_intel": f"Commercial Variant ({v_prod_type})",
                                        "product_type": v_prod_type,
                                        "brand": base_item.get("brand", "Unknown")
                                    }
                                    all_variants.append(v_rec)
                        except Exception as pe:
                            _log(f"⚠ [Spreadshirt] PDP variant extract notice: {pe}")

                    # Supplement with physical matrix expansion ONLY if no live PDP variants were found
                    if not found_on_pdp or len(all_variants) == 0:
                        clean_base_title = clean_spreadshirt_text(base_title).split(" - ")[0].strip()
                        clean_slug = re.sub(r"[^\w\s-]", "", clean_base_title).strip().lower().replace(" ", "+")
                        clean_slug = re.sub(r"\++", "+", clean_slug).strip("+")

                        for idx, line_tuple in enumerate(SPREADSHIRT_PRODUCT_LINES, 1):
                            prod_name = line_tuple[0]
                            prod_slug = line_tuple[1]
                            prod_price = line_tuple[2]
                            cat = line_tuple[3]
                            tid = line_tuple[4] if len(line_tuple) > 4 else "T210"
                            app_id = line_tuple[5] if len(line_tuple) > 5 else 1

                            var_id = f"{base_id}-VAR-{idx:02d}"
                            if var_id in known_ids:
                                continue

                            known_ids.add(var_id)
                            var_url = f"https://www.spreadshirt.com/shop/design/{clean_slug}+{prod_slug}-{base_id}" if base_id.startswith("D") else f"https://www.spreadshirt.com/shop/{clean_slug}"

                            # Generate product-specific mockup image URL using Spreadshirt CDN image server
                            if d_num:
                                var_img = f"https://image.spreadshirtmedia.com/image-server/v1/products/{tid}A{app_id}PA4301PT17X0Y30D{d_num}W25000H25000/views/1,appearanceId={app_id}.jpg?width=450&height=600&backgroundColor=F2F2F2"
                            elif "image-server/v1/products/" in img_url and re.search(r"D\d+", img_url):
                                d_sub = re.search(r"(D\d+)", img_url).group(1)
                                var_img = f"https://image.spreadshirtmedia.com/image-server/v1/products/{tid}A{app_id}PA4301PT17X0Y30{d_sub}W25000H25000/views/1,appearanceId={app_id}.jpg?width=450&height=600&backgroundColor=F2F2F2"
                            else:
                                var_img = img_url

                            v_record = {
                                "title": f"{clean_base_title} - {prod_name}",
                                "url": var_url,
                                "item_id": var_id,
                                "price": f"${prod_price:.2f}",
                                "seller": artist,
                                "location": "Print-on-Demand (Global Fulfillment)",
                                "marketplace": "spreadshirt.com",
                                "marketplace_code": "spreadshirt.com",
                                "image_url": var_img,
                                "thumbnail": var_img,
                                "threat_badge": f"🌿 POD Matrix ({prod_name})",
                                "threat_intel": f"Commercial Variant ({cat})",
                                "product_type": prod_name,
                                "brand": base_item.get("brand", "Unknown")
                            }
                            all_variants.append(v_record)

                    if progress_callback:
                        try:
                            progress_callback(current_idx, total_items, len(all_variants), base_item)
                        except Exception:
                            pass

                context.close()
        except Exception as e:
            _log(f"❌ [Spreadshirt] Variant expander error: {e}")

        return all_variants

    def enrich_seller_info(
        self,
        items: List[Dict[str, Any]],
        progress_callback=None,
        stop_event=None
    ):
        """
        High-speed seller/store name enrichment for Spreadshirt listings.
        Uses fast HTTP TLS client (curl_cffi) to extract designer/shop usernames.
        """
        total = len(items)
        if total == 0:
            return

        logger.info(f"🌿 [Spreadshirt] Enriching seller info for {total} listing(s)...")

        for idx, item in enumerate(items):
            if stop_event and stop_event.is_set():
                break

            url = item.get("url", "").strip()
            if not url:
                continue

            extracted_seller = None
            store_handle = None

            # 1. Fast HTTP fetch with curl_cffi
            if HAS_CURL_CFFI:
                try:
                    r = curl_requests.get(url, impersonate="chrome120", timeout=12)
                    if r.status_code == 200:
                        html = r.text
                        soup = BeautifulSoup(html, "html.parser")

                        # 1. Check DOM "Created by" / "See all designs by"
                        for a in soup.select("a"):
                            parent_txt = a.parent.get_text() if a.parent else ""
                            if "Created by" in parent_txt or "See all designs by" in parent_txt:
                                cand = a.get_text(strip=True)
                                if cand and cand.lower() not in ("spreadshirt", "unknown"):
                                    extracted_seller = cand
                                    store_handle = cand
                                    break

                        # 2. Check regex for 'Created by' / 'See all designs by'
                        if not extracted_seller:
                            m_cb = re.search(r'(?:Created by|See all designs by)\s*(?:<!-- -->)?\s*<a[^>]*>([^<]+)</a>', html, re.IGNORECASE)
                            if m_cb:
                                cand = m_cb.group(1).strip()
                                if cand and cand.lower() not in ("spreadshirt", "unknown"):
                                    extracted_seller = cand
                                    store_handle = cand

                        # 3. Check JSON properties in Next.js payloads
                        if not extracted_seller:
                            for p in [r'"designerName"\s*:\s*"([^"]+)"', r'"userName"\s*:\s*"([^"]+)"']:
                                for m in re.finditer(p, html, re.IGNORECASE):
                                    cand = m.group(1).strip()
                                    if cand and cand.lower() not in ("spreadshirt", "unknown", "admin", "null"):
                                        extracted_seller = cand
                                        store_handle = cand
                                        break
                                if extracted_seller: break

                        # 4. Check internal shop user links
                        if not extracted_seller:
                            m = re.search(r'href="\/shop\/user\/([^"?#]+)"', html, re.IGNORECASE)
                            if m:
                                cand = m.group(1).strip()
                                if cand and cand.lower() not in ("spreadshirt", "unknown"):
                                    extracted_seller = cand
                                    store_handle = cand
                except Exception as he:
                    logger.debug(f"Spreadshirt HTTP enrichment error for {url}: {he}")

            # Apply enriched seller
            if extracted_seller and extracted_seller.lower() not in ("spreadshirt creator", "spreadshirt", "unknown"):
                item["seller"] = extracted_seller
                if store_handle:
                    item["store_id"] = store_handle
                    item["store_url"] = f"https://www.spreadshirt.com/user/{store_handle}"

            if progress_callback:
                try:
                    progress_callback(idx + 1, total, item)
                except Exception:
                    pass

        logger.info(f"✅ [Spreadshirt] Seller enrichment completed for {total} item(s).")

    def fetch_single_item(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time metadata and high-res mockup for a single Spreadshirt listing."""
        clean_url = url.strip()
        title = ""
        price = "$24.99"
        seller = "Spreadshirt Creator"
        image_url = ""
        item_id = ""
        store_handle = None

        m_des = re.search(r"-D([a-fA-F0-9]+)", clean_url)
        if m_des:
            item_id = f"D{m_des.group(1)}"
        else:
            m_sell = re.search(r"sellable=([a-zA-Z0-9_\-]+)", clean_url)
            if m_sell: item_id = m_sell.group(1)

        if HAS_CURL_CFFI:
            try:
                r = curl_requests.get(clean_url, impersonate="chrome120", timeout=12)
                if r.status_code == 200:
                    html = r.text
                    soup = BeautifulSoup(html, "html.parser")

                    t_el = soup.select_one("h1[data-product-title], h1, meta[property='og:title']")
                    if t_el:
                        title = t_el.get("content") if t_el.name == "meta" else t_el.get_text(strip=True)
                    if not title:
                        m_title = re.search(r'"compositionName":\s*"([^"]+)"', html)
                        if m_title: title = m_title.group(1).strip()

                    if title:
                        title = re.sub(r"^Order\s+['\"]?|['\"]?\s+online\s*\|\s*Spreadshirt$", "", title, flags=re.IGNORECASE).strip()
                        title = re.sub(r"\s*\|\s*Spreadshirt.*$", "", title, flags=re.IGNORECASE).strip().strip("'\"")

                    m_price = re.search(r'"price":\s*(\d+(?:\.\d{2})?)', html)
                    if m_price:
                        price = f"${float(m_price.group(1)):.2f}"
                    else:
                        p_el = soup.select_one("[data-price], .price, span[class*='price']")
                        if p_el:
                            pm = re.search(r"\$\d+(\.\d{2})?", p_el.get_text(strip=True))
                            if pm: price = pm.group(0)

                    # Seller extraction
                    for a in soup.select("a"):
                        parent_txt = a.parent.get_text() if a.parent else ""
                        if "Created by" in parent_txt or "See all designs by" in parent_txt:
                            cand = a.get_text(strip=True)
                            if cand and cand.lower() not in ("spreadshirt", "unknown"):
                                seller = cand
                                store_handle = cand
                                break

                    if seller == "Spreadshirt Creator":
                        m_cb = re.search(r'(?:Created by|See all designs by)\s*(?:<!-- -->)?\s*<a[^>]*>([^<]+)</a>', html, re.IGNORECASE)
                        if m_cb:
                            cand = m_cb.group(1).strip()
                            if cand and cand.lower() not in ("spreadshirt", "unknown"):
                                seller = cand
                                store_handle = cand

                    if seller == "Spreadshirt Creator":
                        for p in [r'"designerName"\s*:\s*"([^"]+)"', r'"userName"\s*:\s*"([^"]+)"']:
                            for m in re.finditer(p, html, re.IGNORECASE):
                                cand = m.group(1).strip()
                                if cand and cand.lower() not in ("spreadshirt", "unknown", "admin", "null"):
                                    seller = cand
                                    store_handle = cand
                                    break
                            if seller != "Spreadshirt Creator": break

                    if seller == "Spreadshirt Creator":
                        m = re.search(r'href="\/shop\/user\/([^"?#]+)"', html, re.IGNORECASE)
                        if m:
                            cand = m.group(1).strip()
                            if cand and cand.lower() not in ("spreadshirt", "unknown"):
                                seller = cand
                                store_handle = cand

                    img_el = soup.select_one("img[src*='spreadshirtmedia.com'], img[data-src*='spreadshirtmedia.com'], meta[property='og:image']")
                    if img_el:
                        image_url = img_el.get("content") if img_el.name == "meta" else (img_el.get("src") or img_el.get("data-src") or "")
            except Exception as e:
                logger.debug(f"Spreadshirt HTTP fetch_single_item notice: {e}")

        return {
            "title": title or "Spreadshirt Custom Merchandise",
            "url": clean_url,
            "price": price,
            "item_id": item_id,
            "seller": seller,
            "store_id": store_handle,
            "store_url": f"https://www.spreadshirt.com/user/{store_handle}" if store_handle else None,
            "platform": "spreadshirt",
            "marketplace": "spreadshirt.com",
            "marketplace_code": "spreadshirt.com",
            "thumbnail": image_url,
            "image_url": image_url,
            "location": "Print-on-Demand (Global Fulfillment)",
            "threat_badge": "🌿 POD Infringement (Spreadshirt)",
            "threat_intel": "Commercial POD (Spreadshirt Custom Merchandise)",
            "product_type": "Apparel & Merch",
            "brand": "Unknown",
            "source": "Spreadshirt PDP",
            "status": "New"
        }

