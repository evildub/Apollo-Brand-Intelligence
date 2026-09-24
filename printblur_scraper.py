"""
Printblur Scraper Module for Apollo Brand Intelligence Suite.
Specialized in automated retrieval of Print-on-Demand (POD) merchandise,
apparel, and custom creator products on Printblur (printblur.com).

Features:
- Playwright + Native Microsoft Edge Stealth automation.
- Cloudflare WAF evasion with persistent authenticated session cookies.
- Structured product card extraction (Title, Price, Creator, Product ID, Image).
- Full POD Variant Expansion (harvesting 50-90+ real product variants per artwork).
- High-reliability Seller/Artist Enrichment engine with persistent local disk caching.
- Per-item fault isolation preventing single-item failures from interrupting batch runs.
"""

import os
import re
import io
import json
import time
import random
import logging
import threading
import urllib.parse
import urllib.request
from typing import List, Dict, Optional
from PIL import Image

logger = logging.getLogger("Apollo.PrintblurScraper")

POD_GENERIC_STOPWORDS = {
    "the", "and", "for", "with", "shirt", "hoodie", "gift", "gifts", "tshirt", "t-shirt",
    "tank", "top", "tops", "tee", "sweatshirt", "sweater", "mug", "mugs", "sticker", "stickers",
    "poster", "canvas", "bag", "bags", "backpack", "hat", "hats", "cap", "caps", "blanket",
    "flag", "flags", "pillow", "case", "phone", "onesie", "apron", "men", "mens", "women",
    "womens", "unisex", "kids", "youth", "baby", "size", "sizes", "plus", "luxury", "brand",
    "custom", "customized", "name", "2d", "3d", "half", "zipper", "zip", "retro", "vintage",
    "classic", "graphic", "printed", "print", "funny", "cool", "cute", "best", "style", "fashion",
    "apparel", "merch", "merchandise", "product", "item", "items"
}


class PrintblurScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self.profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Apollo_Printblur_Session"
        )
        os.makedirs(self.profile_dir, exist_ok=True)
        self.cache_file = os.path.join(self.profile_dir, "printblur_seller_cache.json")

    def _is_valid_pod_variant(self, parent_title: str, variant_title: str, variant_slug: str, brand: str = "", keyword: str = "") -> bool:
        """Validate that candidate variant represents the same underlying POD artwork/design."""
        raw_tokens = re.findall(r'[a-zA-Z0-9]{3,}', parent_title.lower())
        core_parent_tokens = [t for t in raw_tokens if t not in POD_GENERIC_STOPWORDS]

        var_text = f"{variant_title.lower()} {variant_slug.lower()}"

        target_b = (brand or keyword or "").lower().strip()
        if target_b and target_b not in ("adhoc request", "full store sweep", ""):
            if target_b in parent_title.lower() and target_b not in var_text:
                return False

        if not core_parent_tokens:
            core_parent_tokens = [t for t in raw_tokens if t not in ("the", "and", "for", "with")]

        if not core_parent_tokens:
            return True

        matched = [t for t in core_parent_tokens if t in var_text]
        match_ratio = len(matched) / len(core_parent_tokens)

        if len(core_parent_tokens) == 1:
            return match_ratio >= 1.0
        elif len(core_parent_tokens) == 2:
            return match_ratio >= 0.50
        else:
            return match_ratio >= 0.40

    def _synthesize_variant_title(self, parent_title: str, slug: str, card_title: str = "") -> str:
        """Format variant title preserving parent casing and design name."""
        if card_title and len(card_title.split()) >= 4:
            p_toks = set(re.findall(r'[a-zA-Z0-9]{3,}', parent_title.lower())) if parent_title else set()
            c_toks = set(re.findall(r'[a-zA-Z0-9]{3,}', card_title.lower()))
            if len(p_toks & c_toks) >= 2 or not p_toks:
                return card_title

        if not slug:
            return parent_title or card_title or "Merchandise"

        slug_words = [w for w in slug.split("-") if w]
        parent_tokens = re.findall(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', parent_title) if parent_title else []
        parent_map = {t.lower(): t for t in parent_tokens}

        formatted_words = []
        i = 0
        while i < len(slug_words):
            if i + 1 < len(slug_words):
                two_pair = f"{slug_words[i]}-{slug_words[i+1]}".lower()
                if two_pair in parent_map:
                    formatted_words.append(parent_map[two_pair])
                    i += 2
                    continue
            w = slug_words[i]
            w_lower = w.lower()
            if w_lower == "t" and i + 1 < len(slug_words) and slug_words[i+1].lower().startswith("shirt"):
                formatted_words.append("T-" + slug_words[i+1].title())
                i += 2
                continue
            if w_lower in parent_map:
                formatted_words.append(parent_map[w_lower])
            elif w.upper() in ("SS", "Z28", "RS", "GT", "ZL1", "2D", "3D", "4D", "USA", "V8", "V6", "SKU", "POD"):
                formatted_words.append(w.upper())
            else:
                formatted_words.append(w.title())
            i += 1

        raw_res = " ".join(formatted_words)
        if parent_title and " - " in parent_title:
            prefix = parent_title.split(" - ")[0].strip()
            pref_tokens = re.findall(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', prefix)
            pref_len = len(pref_tokens)
            if pref_len > 0 and [w.lower() for w in formatted_words[:pref_len]] == [p.lower() for p in pref_tokens]:
                rem_words = formatted_words[pref_len:]
                raw_res = prefix + " - " + " ".join(rem_words)

        return raw_res

    def _load_cache(self) -> dict:
        """Load persistent item_id -> {seller, title, price} cache."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self, cache: dict):
        """Save persistent cache atomically."""
        try:
            temp_file = self.cache_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
            os.replace(temp_file, self.cache_file)
        except Exception as e:
            logger.warning(f"Could not save Printblur cache: {e}")

    def _find_edge_path(self) -> Optional[str]:
        """Locate native Microsoft Edge binary on Windows."""
        for path in [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
        ]:
            if os.path.isfile(path):
                return path
        return None

    def _clean_profile_locks(self):
        """Clean singleton lock files from persistent profile."""
        lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]
        for lf in lock_files:
            fp = os.path.join(self.profile_dir, lf)
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass

    def _get_context(self, p=None, force_visible: bool = False, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """Initialize and return a persistent Playwright context with stealth evasions."""
        from playwright.sync_api import sync_playwright
        if p is None:
            p = sync_playwright().start()

        self._clean_profile_locks()
        edge_path = self._find_edge_path()

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ]

        is_headless = False
        if self.headless and not force_visible:
            args.extend(["--window-position=-2400,-2400", "--window-size=1366,850"])
        elif force_visible:
            args.extend([f"--window-position={window_pos[0]},{window_pos[1]}", f"--window-size={window_size[0]},{window_size[1]}"])

        kwargs = {
            "user_data_dir": self.profile_dir,
            "headless": is_headless,
            "args": args,
            "viewport": {"width": window_size[0] if force_visible else 1366, "height": window_size[1] if force_visible else 850},
            "locale": "en-US",
            "ignore_default_args": ["--enable-automation"],
        }
        if edge_path:
            kwargs["executable_path"] = edge_path
        else:
            kwargs["channel"] = "msedge"

        try:
            context = p.chromium.launch_persistent_context(**kwargs)
        except Exception as e:
            logger.warning(f"Persistent context launch retry after process cleanup: {e}")
            self._clean_profile_locks()
            time.sleep(0.6)
            try:
                context = p.chromium.launch_persistent_context(**kwargs)
            except Exception:
                import tempfile
                temp_profile = tempfile.mkdtemp(prefix="pb_edge_session_")
                kwargs["user_data_dir"] = temp_profile
                context = p.chromium.launch_persistent_context(**kwargs)

        return context

    def launch_interactive_auth(self, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """
        Open a visible browser session for the analyst to solve the initial
        Cloudflare security check or accept cookies, persisting clearance tokens permanently.
        """
        from playwright.sync_api import sync_playwright
        self._clean_profile_locks()
        time.sleep(0.3)

        try:
            with sync_playwright() as p:
                context = self._get_context(p, force_visible=True, window_pos=window_pos, window_size=window_size)
                page = context.pages[0] if context.pages else context.new_page()

                logger.info("Opening interactive Printblur session for Cloudflare clearance...")
                page.goto("https://printblur.com", wait_until="domcontentloaded", timeout=45000)

                # Keep window alive until analyst closes it
                while True:
                    try:
                        if page.is_closed() or not context.pages:
                            break
                        time.sleep(1.0)
                    except Exception:
                        break

                try:
                    context.close()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error during interactive Printblur auth session: {e}")
        finally:
            self._clean_profile_locks()

    def search(self, query: str,
               max_items: int = 50,
               max_pages: int = 5,
               progress_callback=None,
               stop_event: threading.Event = None,
               log_callback=None) -> List[Dict]:
        """
        Execute automated keyword search across Printblur.com with stealth pagination.
        Harvests all matching listing cards (title, price, image, item_id, url, marketplace).
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            logger.info(msg)

        results = []
        seen_ids = set()
        clean_query = query.strip()
        encoded_query = urllib.parse.quote_plus(clean_query)

        _log(f"👕 [Printblur] Initializing search for '{clean_query}' (up to {max_items} items, max {max_pages} pages)...")

        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()

                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """)

                try:
                    page_num = 1
                    while page_num <= max_pages and len(results) < max_items:
                        if stop_event and stop_event.is_set():
                            _log("⏹ [Printblur] Search stopped by user.")
                            break

                        # Printblur supports &interest= and &page_id=
                        search_url = f"https://printblur.com/search?interest={encoded_query}&page_id={page_num}"
                        _log(f"🔍 [Printblur] Fetching page {page_num}: {search_url}")

                        try:
                            resp = page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                            page.wait_for_timeout(2500)
                        except Exception as nav_err:
                            _log(f"⚠ [Printblur] Page load warning (page {page_num}): {nav_err}")

                        # Extract product cards
                        page_items = page.evaluate("""() => {
                            const items = [];
                            const seenHrefs = new Set();

                            const cards = document.querySelectorAll(
                                '.product-item-box, .product-item, .item-product, div.item, [class*="product-item"]'
                            );

                            for (const card of cards) {
                                const linkEl = card.querySelector('a.product-link, a[href*="-p"]');
                                if (!linkEl) continue;

                                const href = linkEl.href || '';
                                if (!href || seenHrefs.has(href)) continue;
                                seenHrefs.add(href);

                                const cleanUrl = href.split('?')[0];
                                const mId = cleanUrl.match(/-p(\\d+)/);
                                const pId = mId ? mId[1] : '';

                                // Title
                                let title = (linkEl.getAttribute('title') || '').trim();
                                if (!title) {
                                    const titleEl = card.querySelector('[class*="title"], h3, h2, h4, span.title, p');
                                    if (titleEl) title = (titleEl.innerText || '').trim();
                                }
                                if (!title && pId) {
                                    const slug = cleanUrl.split('/').pop().split('-p')[0].replace(/-/g, ' ').trim();
                                    title = slug ? slug.charAt(0).toUpperCase() + slug.slice(1) : `Printblur Product #${pId}`;
                                }

                                // Price
                                let price = '';
                                const priceEl = card.querySelector('[class*="price"], .product-price-current, span');
                                if (priceEl) {
                                    const mP = (priceEl.innerText || '').match(/\\$\\s*[\\d,]+(?:\\.\\d+)?/);
                                    if (mP) price = mP[0];
                                }

                                // Image
                                let img = '';
                                const imgEl = card.querySelector('img.product-item-image, img');
                                if (imgEl) {
                                    img = imgEl.currentSrc || imgEl.src || imgEl.getAttribute('data-src') || '';
                                }

                                items.push({
                                    title: title,
                                    url: cleanUrl,
                                    price: price || '$24.95',
                                    seller: 'Printblur Creator',
                                    image_url: img
                                });
                            }
                            return items;
                        }""")

                        if not page_items:
                            curr_title = page.title()
                            if "403" in curr_title or "blocked" in curr_title.lower() or "just a moment" in curr_title.lower():
                                _log("🛡️ [Printblur] Cloudflare challenge detected.")
                                _log("💡 [Printblur] Please click '👕 Printblur Connect' in toolbar to authenticate once.")
                            else:
                                _log(f"ℹ [Printblur] No product cards found on page {page_num}.")
                            break

                        new_count = 0
                        for raw_it in page_items:
                            u = raw_it.get("url", "").split("?")[0]
                            m_id = re.search(r'-p(\d+)', u)
                            if not m_id:
                                continue
                            item_id = m_id.group(1)

                            if not item_id or item_id in seen_ids:
                                continue
                            seen_ids.add(item_id)

                            title = raw_it.get("title", "")
                            if not title or title.startswith("$") or len(title) < 3:
                                slug_part = u.split("/")[-1].split("-p")[0].replace("-", " ").title()
                                title = slug_part if slug_part else f"Printblur Product #{item_id}"

                            price = raw_it.get("price", "") or "$24.95"

                            results.append({
                                "brand": "",
                                "product_type": "Merchandise",
                                "title": title,
                                "item_id": item_id,
                                "price": price,
                                "seller": raw_it.get("seller") or "Printblur Creator",
                                "location": "United States",
                                "image_url": raw_it.get("image_url", ""),
                                "url": u,
                                "marketplace": "printblur.com",
                                "condition": "New",
                                "keyword": query
                            })
                            new_count += 1

                            if len(results) >= max_items:
                                break

                        _log(f"📦 [Printblur] Harvested {new_count} listings from page {page_num} ({len(results)}/{max_items} total).")

                        if len(results) >= max_items or new_count == 0:
                            break

                        page_num += 1
                        time.sleep(1.5)

                finally:
                    try: context.close()
                    except Exception: pass

        except Exception as e:
            _log(f"❌ Error during Printblur scraping: {e}")
            logger.exception("Printblur search failure")
        finally:
            self._clean_profile_locks()

        _log(f"✅ [Printblur] Search complete: Retrieved {len(results)} listings.")
        return results

    def enrich_seller_info(self, items: List[Dict],
                           progress_callback=None,
                           stop_event: threading.Event = None,
                           chunk_size: int = 15) -> List[Dict]:
        """
        Enrich real creator / artist / shop names and exact pricing for Printblur items.
        Uses persistent disk cache to resolve previously seen items in 0ms.
        """
        if not items:
            return items

        cache = self._load_cache()
        items_to_fetch = []
        generic_placeholders = ("creator", "unknown", "printblur creator", "printblur")

        # Pass 1: Resolve from local cache
        for idx, it in enumerate(items):
            item_id = str(it.get("item_id", "")).strip()
            cached = cache.get(item_id) if item_id else None
            cached_seller = cached.get("seller", "") if cached else ""
            is_valid_cached_seller = bool(cached_seller and not any(g in str(cached_seller).lower() for g in generic_placeholders))
            if item_id and cached and is_valid_cached_seller and cached.get("image_url"):
                it["seller"] = cached_seller
                if cached.get("price"):
                    it["price"] = cached.get("price")
                if cached.get("title") and (not it.get("title") or it.get("title").startswith("Printblur")):
                    it["title"] = cached.get("title")
                if cached.get("image_url") and not it.get("image_url"):
                    it["image_url"] = cached.get("image_url")
                if progress_callback:
                    progress_callback(idx + 1, len(items), it)
            else:
                items_to_fetch.append((idx, it))

        if not items_to_fetch:
            return items

        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()

                try:
                    # Abort heavy static assets for rapid metadata extraction
                    page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,eot,css,mp4,webm,avi,mov}", lambda route: route.abort())
                except Exception:
                    pass

                try:
                    processed_in_chunk = 0
                    for fetch_idx, (orig_idx, it) in enumerate(items_to_fetch):
                        if stop_event and stop_event.is_set():
                            break

                        if processed_in_chunk >= chunk_size:
                            time.sleep(random.uniform(0.6, 1.2))
                            processed_in_chunk = 0

                        item_id = str(it.get("item_id", "")).strip()
                        raw_url = it.get("url", "")
                        url = raw_url if raw_url.startswith("http") else f"https://printblur.com/product-p{item_id}"

                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(400)

                            res = page.evaluate("""() => {
                                let seller = '';
                                let price = '';
                                let title = '';

                                // 0. Direct JS variables (window.product.seller_name)
                                try {
                                    if (window.product && window.product.seller_name) {
                                        const cand = String(window.product.seller_name).trim();
                                        if (cand && !cand.toLowerCase().includes('printblur')) seller = cand;
                                    }
                                    if (window.product && window.product.price) {
                                        price = '$' + String(window.product.price).replace('$', '').trim();
                                    }
                                } catch(e) {}

                                // 1. Document title
                                if (!seller && document.title) {
                                    const tm = document.title.match(/sold\\s+by\\s+([^|\\n]+)/i);
                                    if (tm && tm[1]) {
                                        const cand = tm[1].trim();
                                        if (cand && !cand.toLowerCase().includes('printblur') && cand.length > 1) {
                                            seller = cand;
                                        }
                                    }
                                }

                                // 2. Body text match
                                if (!seller && document.body) {
                                    const fullText = document.body.innerText || '';
                                    const m = fullText.match(/(?:sold|designed|created)\\s+by\\s*\\n?\\s*([^\\n\\r]+)/i);
                                    if (m && m[1]) {
                                        const cand = m[1].trim();
                                        if (cand && !cand.toLowerCase().includes('printblur')) {
                                            seller = cand;
                                        }
                                    }
                                }

                                // 3. H1 Title
                                const h1 = document.querySelector('h1');
                                if (h1 && h1.innerText) title = h1.innerText.trim();

                                // 4. Price fallback
                                if (!price) {
                                    const priceEl = document.querySelector('.product-price-current, .price, [class*="product-price"]');
                                    if (priceEl && priceEl.innerText) {
                                        const mP = priceEl.innerText.match(/\\$\\s*[\\d,]+(?:\\.\\d+)?/);
                                        if (mP) price = mP[0];
                                    }
                                }

                                // 5. Image
                                let img = '';
                                const og = document.querySelector('meta[property="og:image"], meta[name="og:image"]');
                                if (og && og.content && og.content.startsWith('http')) {
                                    img = og.content;
                                }

                                return { seller: seller, price: price, title: title, image_url: img };
                            }""")

                            if res.get("seller"):
                                it["seller"] = res["seller"]
                            if res.get("price"):
                                it["price"] = res["price"]
                            if res.get("title") and (not it.get("title") or it.get("title").startswith("Printblur") or len(it.get("title", "")) < len(res.get("title", ""))):
                                it["title"] = res["title"]
                            if res.get("image_url") and not it.get("image_url"):
                                it["image_url"] = res["image_url"]

                            if item_id and it.get("seller") and not any(g in str(it.get("seller")).lower() for g in generic_placeholders):
                                cache[item_id] = {
                                    "seller": it.get("seller"),
                                    "price": it.get("price"),
                                    "title": it.get("title"),
                                    "image_url": it.get("image_url")
                                }

                        except Exception as item_err:
                            logger.debug(f"Error enriching Printblur item {item_id}: {item_err}")

                        processed_in_chunk += 1
                        if progress_callback:
                            progress_callback(orig_idx + 1, len(items), it)

                        time.sleep(random.uniform(0.1, 0.25))

                finally:
                    try: context.close()
                    except Exception: pass

        except Exception as e:
            logger.error(f"Error during Printblur seller enrichment: {e}")
        finally:
            self._save_cache(cache)
            self._clean_profile_locks()

        return items

    def expand_design_variants(self, items: List[Dict],
                               existing_item_ids: Optional[set] = None,
                               progress_callback=None,
                               stop_event: threading.Event = None,
                               log_callback=None) -> List[Dict]:
        """
        Dredge and harvest all Print-on-Demand (POD) design variants for given Printblur listings.
        Each parent design listing can expand into 50-90+ real product listings
        (Hoodies, Mugs, Blankets, Pillows, Posters, Bags, 3D Apparel, etc.).
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            logger.info(msg)

        if not items:
            return []

        known_ids = set(existing_item_ids or set())
        for it in items:
            iid = str(it.get("item_id", "")).strip()
            if iid: known_ids.add(iid)

        cache = self._load_cache()
        handled_parent_ids = set()
        expanded_results = []
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()

                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """)

                try:
                    total_parents = len(items)
                    for idx, parent in enumerate(items):
                        if stop_event and stop_event.is_set():
                            _log("⏹ [Printblur] Variant expansion cancelled by user.")
                            break

                        parent_id = str(parent.get("item_id", "")).strip()
                        parent_title = parent.get("title", "")
                        if parent_id and parent_id in handled_parent_ids:
                            _log(f"⚡ [Printblur] Skipping [{idx+1}/{total_parents}]: '{parent_title[:35]}...' (already enriched & expanded).")
                            continue

                        raw_url = parent.get("url", "")
                        url = raw_url if raw_url.startswith("http") else f"https://printblur.com/product-p{parent_id}"
                        seller = parent.get("seller") or "Printblur Creator"
                        brand = parent.get("brand", "")
                        keyword = parent.get("keyword", "")

                        _log(f"👕 [Printblur] Expanding variants for [{idx+1}/{total_parents}]: '{parent_title[:35]}...'")

                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=25000)
                            page.wait_for_timeout(2000)

                            # Live creator/seller extraction directly from page
                            live_seller = page.evaluate("""() => {
                                let s = '';
                                try {
                                    if (window.product && window.product.seller_name) {
                                        const cand = String(window.product.seller_name).trim();
                                        if (cand && !cand.toLowerCase().includes('printblur')) s = cand;
                                    }
                                } catch(e) {}

                                if (!s && document.title) {
                                    const tm = document.title.match(/sold\\s+by\\s+([^|\\n]+)/i);
                                    if (tm && tm[1]) {
                                        const cand = tm[1].trim();
                                        if (cand && !cand.toLowerCase().includes('printblur') && cand.length > 1) s = cand;
                                    }
                                }

                                if (!s && document.body) {
                                    const fullText = document.body.innerText || '';
                                    const m = fullText.match(/(?:sold|designed|created)\\s+by\\s*\\n?\\s*([^\\n\\r]+)/i);
                                    if (m && m[1]) {
                                        const cand = m[1].trim();
                                        if (cand && !cand.toLowerCase().includes('printblur')) s = cand;
                                    }
                                }
                                return s;
                            }""")

                            if isinstance(live_seller, str) and live_seller.strip() and not live_seller.strip().lower().startswith("printblur"):
                                seller = live_seller.strip()
                                parent["seller"] = seller
                                if parent_id:
                                    cache[parent_id] = {
                                        "seller": seller,
                                        "price": parent.get("price"),
                                        "title": parent.get("title"),
                                        "image_url": parent.get("image_url")
                                    }

                            # Click 'See all items' if present to expand full catalog modal/drawer
                            page.evaluate("""() => {
                                const btn = document.querySelector('.show-more-also-available, .component-seemore');
                                if (btn) {
                                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    btn.click();
                                }
                            }""")
                            page.wait_for_timeout(2000)

                            # Extract variant products from drawer
                            extracted_variants = page.evaluate("""(parentId) => {
                                const items = [];
                                const seen = new Set();
                                const selectors = [
                                    'a[data-source-box="also-available"]',
                                    '.js-also-available-product a',
                                    '#modal-also-available a[href*="-p"]',
                                    '.modal-also-available a[href*="-p"]',
                                    '.tab-more-also-available-product a[href*="-p"]',
                                    '.box-also-available a[href*="-p"]',
                                    'a.js-also-available-product'
                                ];

                                const allElements = document.querySelectorAll(selectors.join(', '));
                                for (let a of allElements) {
                                    const rawHref = a.href || '';
                                    const m = rawHref.match(/-p(\\d+)/);
                                    if (!m) continue;

                                    const vId = m[1];
                                    if (vId === parentId || seen.has(vId)) continue;
                                    seen.add(vId);

                                    const cleanUrl = rawHref.split('?')[0];
                                    const parentEl = a.closest('div.item, div.product-item, div.available-product-item, div.js-also-available-product, div') || a;

                                    let title = '';
                                    const titleEl = a.querySelector('[class*="title"], h3, h2, h4, span.title, p') || a;
                                    if (titleEl) {
                                        title = (titleEl.innerText || titleEl.getAttribute('title') || '').trim();
                                    }

                                    let price = '';
                                    const priceEl = parentEl.querySelector('[class*="price"], .product-price-current, span');
                                    if (priceEl) {
                                        const mP = (priceEl.innerText || '').match(/\\$\\s*[\\d,]+(?:\\.\\d+)?/);
                                        if (mP) price = mP[0];
                                    }

                                    let img = '';
                                    const imgEl = a.querySelector('img') || (parentEl ? parentEl.querySelector('img') : null);
                                    if (imgEl) {
                                        img = imgEl.currentSrc || imgEl.src || imgEl.getAttribute('data-src') || '';
                                    }

                                    items.push({
                                        item_id: vId,
                                        url: cleanUrl,
                                        title: title,
                                        price: price,
                                        image_url: img
                                    });
                                }
                                return items;
                            }""", parent_id)

                            is_valid_seller = bool(seller and not any(g in str(seller).lower() for g in ("creator", "unknown", "printblur creator", "printblur")))

                            # Cross-link matching parent items in queue
                            for v in extracted_variants:
                                v_id = str(v.get("item_id", "")).strip()
                                if not v_id: continue
                                if is_valid_seller and v_id not in cache:
                                    cache[v_id] = {
                                        "seller": seller,
                                        "price": v.get("price") or parent.get("price"),
                                        "title": v.get("title"),
                                        "image_url": v.get("image_url")
                                    }
                                if is_valid_seller:
                                    for other_idx in range(idx + 1, total_parents):
                                        other = items[other_idx]
                                        other_id = str(other.get("item_id", "")).strip()
                                        if other_id and other_id == v_id:
                                            other["seller"] = seller
                                            handled_parent_ids.add(other_id)
                                            _log(f"⚡ [Printblur] Parent [{other_idx+1}/{total_parents}] '{other.get('title', '')[:30]}' matches variant. Auto-enriched as '{seller}'.")

                            # Add new variants
                            for v in extracted_variants:
                                v_id = str(v.get("item_id", "")).strip()
                                if not v_id or v_id in known_ids:
                                    continue

                                u = v.get("url", "")
                                slug = u.split("/")[-1].split("-p")[0]
                                card_raw = v.get("title", "").replace("\n", " ").strip()
                                card_clean = re.sub(r'\$\s*[\d,]+(?:\.\d+)?', '', card_raw).strip()

                                type_part = slug.split("-")[-1].title() if "-" in slug else "Merchandise"
                                if len(type_part) <= 2: type_part = "Merchandise"

                                v_title = self._synthesize_variant_title(parent_title, slug, card_clean)
                                if not self._is_valid_pod_variant(parent_title, v_title, slug, brand=brand, keyword=keyword):
                                    continue

                                known_ids.add(v_id)
                                price = v.get("price") or parent.get("price") or "$24.95"
                                v_img = v.get("image_url", "") or parent.get("image_url", "")

                                variant_item = {
                                    "brand": brand,
                                    "product_type": type_part,
                                    "title": v_title,
                                    "item_id": v_id,
                                    "price": price,
                                    "seller": seller,
                                    "location": "United States",
                                    "image_url": v_img,
                                    "thumbnail": v_img,
                                    "url": u,
                                    "marketplace": "printblur.com",
                                    "condition": "New",
                                    "keyword": keyword
                                }
                                expanded_results.append(variant_item)

                            if progress_callback:
                                progress_callback(idx + 1, total_parents, len(expanded_results), parent)

                        except Exception as parent_err:
                            _log(f"⚠ [Printblur] Error expanding [{idx+1}/{total_parents}]: {parent_err}")

                finally:
                    try: context.close()
                    except Exception: pass

        except Exception as e:
            _log(f"❌ Error during Printblur variant expansion: {e}")
        finally:
            self._save_cache(cache)
            self._clean_profile_locks()

        _log(f"✅ [Printblur] Variant expansion complete: Created +{len(expanded_results)} product variant listings.")
        return expanded_results

    def resolve_store_info(self, store_input: str) -> Dict[str, str]:
        """Resolve store slug or link into clean store metadata."""
        clean = store_input.strip()
        m = re.search(r'printblur\.com/shops/([^/?#]+)', clean, re.IGNORECASE)
        if m:
            slug = m.group(1).replace("-", " ").title()
            return {"store_name": slug, "store_url": clean}
        return {"store_name": clean, "store_url": f"https://printblur.com/shops/{urllib.parse.quote(clean.lower().replace(' ', '-'))}"}

    # ── Perceptual Hash (dHash) & Connected Network Discovery ────────────────
    def compute_dhash(self, pil_img) -> int:
        """Compute 64-bit difference hash (dHash) for fast perceptual image matching."""
        small = pil_img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        try:
            pixels = list(small.get_flattened_data())
        except AttributeError:
            pixels = list(small.getdata())
        diff = []
        for row in range(8):
            for col in range(8):
                diff.append(pixels[row * 9 + col] > pixels[row * 9 + col + 1])
        return sum([1 << i for i, b in enumerate(diff) if b])

    def hamming_distance(self, h1: int, h2: int) -> int:
        """Hamming distance between two 64-bit hashes (0 = exact match, <=8 = near-identical)."""
        return bin(h1 ^ h2).count("1")

    def find_connected_network(self, item_id: str, item_url: str = "", target_img_url: str = "") -> List[Dict]:
        """
        On-Demand Visual Syndicate & Connected Seller Hunter for Printblur.
        Scans product page recommendation carousels:
        - "You may also like" / "Similar Products"
        - "Frequently bought together"
        - "Customers also viewed" / Viewed products
        - "Related merchandise"
        - "Creator's other designs" / Storefront recommendations
        Performs perceptual image matching (dHash) against target_img_url.
        Uses active inactivity polling (closes as soon as no new items appear for 1.5s)
        and concurrent multithreaded image dHash calculation.
        """
        if not item_url and item_id:
            item_url = f"https://printblur.com/product-p{item_id}"
        if not item_id and item_url:
            m = re.search(r'-p(\d+)', item_url)
            if m:
                item_id = m.group(1)

        results = []
        if not item_url:
            return results

        target_hash = None
        if target_img_url and str(target_img_url).startswith("http"):
            try:
                req = urllib.request.Request(str(target_img_url), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=3) as r:
                    t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                    target_hash = self.compute_dhash(t_img)
            except Exception:
                pass

        from playwright.sync_api import sync_playwright

        carousels_data = []
        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """)

                try:
                    try:
                        page.goto(item_url, wait_until="domcontentloaded", timeout=12000)
                    except Exception:
                        pass

                    # Extract target image if not already hashed
                    if not target_hash:
                        try:
                            t_src = page.evaluate("""() => {
                                const og = document.querySelector('meta[property="og:image"], meta[name="og:image"]');
                                if (og && og.content) return og.content;
                                const src = document.querySelector('picture source[srcset]');
                                if (src && src.srcset) {
                                    const urls = src.srcset.match(/https?:\\/\\/[^\\s"']+/g);
                                    if (urls && urls.length > 0) return urls[urls.length - 1].replace(/\\s+\\d+[wx]$/, '').trim();
                                }
                                const img = document.querySelector('img[src*="printblur.com"], img[src*="cdn"]');
                                return img ? (img.currentSrc || img.src || '') : '';
                            }""")
                            if t_src and str(t_src).startswith("http"):
                                req = urllib.request.Request(str(t_src), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                                with urllib.request.urlopen(req, timeout=3) as r:
                                    t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                                    target_hash = self.compute_dhash(t_img)
                        except Exception:
                            pass

                    # Active Carousel Harvester with Inactivity/Idle Early Exit
                    start_time = time.time()
                    last_new_time = time.time()
                    last_count = 0
                    idle_threshold = 1.5
                    max_scan_duration = 5.0

                    extract_js = """() => {
                        const discovered = [];
                        const seen = new Set();

                        const sectionSelectors = [
                            '.you-may-also-like-list',
                            '.md-product-viewed-list',
                            '.bought-together-other-product',
                            '.related-items-wrapper',
                            'div[class*="recommend"]',
                            'div[class*="carousel"]',
                            'div[class*="swiper"]',
                            'div[class*="similar"]',
                            'div[class*="related"]',
                            'section'
                        ];

                        for (let sel of sectionSelectors) {
                            const sections = document.querySelectorAll(sel);
                            for (let sec of sections) {
                                const hEl = sec.querySelector('h1, h2, h3, h4, h5, [class*="heading"], [class*="title"], .title');
                                let secTitle = hEl ? hEl.innerText.trim() : '';
                                let secType = '👥 You Might Also Like';

                                const secClass = sec.className || '';
                                if (secTitle.toLowerCase().includes('bought together') || secClass.includes('bought-together')) {
                                    secType = '🛒 Frequently Bought Together';
                                } else if (secTitle.toLowerCase().includes('viewed') || secClass.includes('product-viewed')) {
                                    secType = '👥 Customers Also Viewed';
                                } else if (secTitle.toLowerCase().includes('related') || secClass.includes('related-items')) {
                                    secType = '🔗 Related Merchandise';
                                } else if (secTitle.toLowerCase().includes('more') && secTitle.toLowerCase().includes('products')) {
                                    secType = '🏪 Creator\\'s Other Products';
                                }

                                const cards = sec.querySelectorAll('.product-item, .item, [class*="product-card"], a[href*="-p"], .swiper-slide');
                                for (let card of cards) {
                                    const link = card.tagName === 'A' ? card : card.querySelector('a[href*="-p"]');
                                    if (!link) continue;
                                    const href = link.href || '';
                                    if (!href.includes('-p')) continue;

                                    const cleanHref = href.split('?')[0].split('#')[0];
                                    if (seen.has(cleanHref)) continue;
                                    seen.add(cleanHref);

                                    const tEl = card.querySelector('[class*="title"], h3, h2, span.title') || link;
                                    const pEl = card.querySelector('[class*="price"], .product-price, span[class*="price"]');
                                    const sEl = card.querySelector('[class*="author"], [class*="artist"], [class*="store"], [class*="seller"], [class*="shop"], [class*="creator"]');

                                    let title = tEl ? (tEl.innerText || '').trim() : '';
                                    let price = pEl ? (pEl.innerText || '').trim() : '';
                                    let seller = sEl ? (sEl.innerText || '').trim() : '';

                                    let img = '';
                                    const sourceEls = card.querySelectorAll('picture source, source');
                                    for (let s of sourceEls) {
                                        const rawSet = s.srcset || s.getAttribute('data-srcset') || '';
                                        if (rawSet) {
                                            const urls = rawSet.match(/https?:\\/\\/[^\\s"']+/g);
                                            if (urls && urls.length > 0) {
                                                img = urls[urls.length - 1].replace(/\\s+\\d+[wx]$/, '').trim();
                                                break;
                                            }
                                        }
                                    }

                                    if (!img || img.startsWith('data:') || img.includes('1x1.png')) {
                                        const imgEls = card.querySelectorAll('img');
                                        for (let im of imgEls) {
                                            const cand = im.getAttribute('data-original') ||
                                                         im.getAttribute('data-src') ||
                                                         im.getAttribute('data-srcset') ||
                                                         im.getAttribute('data-lazy-src') ||
                                                         im.getAttribute('data-thumb') ||
                                                         (im.currentSrc && !im.currentSrc.startsWith('data:') && !im.currentSrc.includes('1x1.png') ? im.currentSrc : '') ||
                                                         (im.src && !im.src.startsWith('data:') && !im.src.includes('1x1.png') ? im.src : '');
                                            if (cand) {
                                                const urls = cand.match(/https?:\\/\\/[^\\s"']+/g);
                                                if (urls && urls.length > 0) {
                                                    img = urls[urls.length - 1].replace(/\\s+\\d+[wx]$/, '').trim();
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    discovered.push({
                                        title: title,
                                        url: cleanHref,
                                        price_raw: price,
                                        seller: seller,
                                        image_url: img,
                                        network_type: secType
                                    });
                                }
                            }
                        }

                        return discovered;
                    }"""

                    scroll_count = 0
                    while (time.time() - start_time) < max_scan_duration:
                        try:
                            page.evaluate("window.scrollBy(0, 800);")
                        except Exception:
                            pass
                        time.sleep(0.25)

                        current_items = page.evaluate(extract_js)
                        if len(current_items) > last_count:
                            last_count = len(current_items)
                            last_new_time = time.time()
                            carousels_data = current_items
                        elif last_count > 0 and (time.time() - last_new_time) >= idle_threshold:
                            break

                        scroll_count += 1
                        if scroll_count >= 10:
                            break

                    if not carousels_data:
                        carousels_data = page.evaluate(extract_js)

                finally:
                    try:
                        context.close()
                    except Exception:
                        pass

        except Exception as e:
            logger.debug(f"Error finding connected network for Printblur item {item_url}: {e}")
        finally:
            self._clean_profile_locks()

        # Fast parallel perceptual image hashing (dHash) after browser window is closed
        hash_results = {}
        if target_hash and carousels_data:
            from concurrent.futures import ThreadPoolExecutor
            def _calc_dist(itm):
                u_img = itm.get("image_url", "")
                if u_img and str(u_img).startswith("http"):
                    try:
                        req = urllib.request.Request(u_img, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                        with urllib.request.urlopen(req, timeout=1.8) as r:
                            c_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                            c_hash = self.compute_dhash(c_img)
                            d = self.hamming_distance(target_hash, c_hash)
                            if d <= 6:
                                return (itm.get("url"), f"🎯 Exact Photo Match (dHash: {d})")
                            elif d <= 14:
                                return (itm.get("url"), f"🖼 Visual Match (dHash: {d})")
                    except Exception:
                        pass
                return (itm.get("url"), None)

            try:
                with ThreadPoolExecutor(max_workers=10) as pool:
                    for u, label in pool.map(_calc_dist, carousels_data):
                        if label:
                            hash_results[u] = label
            except Exception:
                pass

        cache = self._load_cache()
        seen_ids = set([str(item_id)] if item_id else [])

        for itm in carousels_data:
            u = itm.get("url", "")
            m = re.search(r'-p(\d+)', u)
            if not m:
                continue
            c_id = m.group(1)
            if c_id in seen_ids:
                continue
            seen_ids.add(c_id)

            raw_price = itm.get("price_raw", "")
            m_price = re.search(r'\$\s*[\d,]+(?:\.\d+)?', raw_price)
            price_disp = m_price.group(0) if m_price else "$24.95"

            seller_name = itm.get("seller") or ""
            if not seller_name and c_id in cache:
                seller_name = cache[c_id].get("seller", "")
            if not seller_name:
                seller_name = "Printblur Creator"

            title = itm.get("title", "")
            if not title or title.startswith("$") or len(title) < 3:
                slug_part = u.split("/")[-1].split("-p")[0].replace("-", " ").title()
                title = slug_part if slug_part else f"Printblur Product #{c_id}"

            img_url = itm.get("image_url", "")
            sim_label = hash_results.get(u) or itm.get("network_type", "👥 You Might Also Like")

            results.append({
                "brand": "",
                "product_type": "Merchandise",
                "title": title,
                "item_id": c_id,
                "price": price_disp,
                "seller": seller_name,
                "location": "United States",
                "seller_origin": "United States",
                "image_url": img_url,
                "url": u,
                "marketplace": "printblur.com",
                "condition": itm.get("network_type", "You Might Also Like"),
                "similarity": sim_label,
                "match_type": itm.get("network_type", "You Might Also Like")
            })

        return results
