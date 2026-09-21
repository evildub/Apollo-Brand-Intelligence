"""
Printerval Scraper Module for Apollo Brand Intelligence Suite.
Specialized in automated retrieval of Print-on-Demand (POD) merchandise,
apparel, stickers, and custom creator products on Printerval (printerval.com).

Features:
- Playwright + Native Microsoft Edge Stealth automation.
- Structured product card extraction (Title, Price, Creator, Product ID, Image).
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

logger = logging.getLogger("Apollo.PrintervalScraper")

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


class PrintervalScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self.profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Apollo_Printerval_Session"
        )
        os.makedirs(self.profile_dir, exist_ok=True)
        self.cache_file = os.path.join(self.profile_dir, "printerval_seller_cache.json")

    def _is_valid_pod_variant(self, parent_title: str, variant_title: str, variant_slug: str, brand: str = "", keyword: str = "") -> bool:
        """Validate that candidate variant represents the same underlying POD artwork/design."""
        raw_tokens = re.findall(r'[a-zA-Z0-9]{3,}', parent_title.lower())
        core_parent_tokens = [t for t in raw_tokens if t not in POD_GENERIC_STOPWORDS]

        var_text = f"{variant_title.lower()} {variant_slug.lower()}"

        # If brand was searched for or exists in parent title, variant must not omit or conflict with it
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
            return len(matched) >= 1
        elif len(core_parent_tokens) == 2:
            return len(matched) >= 1
        else:
            return len(matched) >= 2 or match_ratio >= 0.5

    def _synthesize_variant_title(self, parent_title: str, slug: str, card_title: str = "") -> str:
        """
        Synthesize the full, accurate listing title for a Printerval variant using the URL slug,
        parent title, and card text, preventing partial/truncated category-only titles like 'Baby Blankets'.
        """
        # If card_title is already a full product title with design name (e.g. >= 4 words and contains parent tokens)
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
                pass
        return {}

    def _save_cache(self, cache: dict):
        """Save persistent seller cache."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

    def _find_edge_path(self) -> Optional[str]:
        """Locate native Microsoft Edge executable on Windows."""
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ]
        return next((p for p in edge_paths if os.path.exists(p)), None)

    def _clean_profile_locks(self):
        """Clean any stale Chromium singleton lock files and terminate orphaned Edge processes to avoid ProcessSingleton errors."""
        lock_files = [os.path.join(self.profile_dir, lk) for lk in ("SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile")]
        has_locks = any(os.path.exists(lf) for lf in lock_files)
        if has_locks:
            try:
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            except Exception:
                pass
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except Exception:
                        pass

    def _get_context(self, force_visible: bool = False, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """Initialize or return existing persistent Playwright context with stealth evasions."""
        from playwright.sync_api import sync_playwright
        if self._context is None:
            self._clean_profile_locks()
            if self._pw is None:
                self._pw = sync_playwright().start()
            edge_path = self._find_edge_path()

            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
            ]

            # Cloudflare Evasion: Never run headless=True on Cloudflare-protected sites. Position window offscreen when stealth mode is requested.
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
                self._context = self._pw.chromium.launch_persistent_context(**kwargs)
            except Exception as e:
                logger.warning(f"Persistent context launch retry after process cleanup: {e}")
                self._clean_profile_locks()
                time.sleep(0.6)
                self._context = self._pw.chromium.launch_persistent_context(**kwargs)

        return self._context

    def launch_interactive_auth(self, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """
        Open a visible browser session for the analyst to solve the initial
        Cloudflare security check or accept cookies, persisting clearance tokens permanently.
        """
        self.close()
        self._clean_profile_locks()
        time.sleep(0.5)

        context = self._get_context(force_visible=True, window_pos=window_pos, window_size=window_size)
        page = context.pages[0] if context.pages else context.new_page()

        page.add_init_script("""
            delete navigator.__proto__.webdriver;
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
            window.chrome = { runtime: {}, app: {}, csi: () => {}, loadTimes: () => {} };
        """)

        try:
            page.goto("https://printerval.com", wait_until="domcontentloaded", timeout=30000)
            logger.info("Printerval interactive authentication window opened.")
        except Exception as e:
            logger.warning(f"Interactive auth navigation error: {e}")

    def close(self):
        """Safely close browser context and Playwright instance."""
        try:
            if self._context:
                try:
                    self._context.close()
                except Exception:
                    pass
                self._context = None
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._pw:
                try:
                    self._pw.stop()
                except Exception:
                    pass
                self._pw = None
        except Exception as e:
            logger.debug(f"Error closing Printerval browser context: {e}")
        finally:
            self._clean_profile_locks()

    def resolve_store_info(self, raw_input: str) -> dict:
        """Parse Printerval shop URL, creator name, or Global Search."""
        raw = raw_input.strip() if raw_input else ""
        if not raw or any(g in raw.lower() for g in ("global", "marketplace", "all", "wholesale", "catalog")):
            return {
                "store_name": "Printerval Global Catalog",
                "original": "https://printerval.com"
            }

        # Check for shop URL (e.g. printerval.com/shop/creatorname)
        m = re.search(r'/shop/([a-zA-Z0-9_\-]+)', raw)
        if m:
            creator = m.group(1)
            return {
                "store_name": f"Printerval Shop ({creator})",
                "original": raw
            }

        clean_name = raw.split("/")[-1].replace("?.*", "").strip()
        return {
            "store_name": f"Printerval Shop ({clean_name})",
            "original": f"https://printerval.com/shop/{clean_name}"
        }

    def search(self, query: str, max_items: int = 50, condition: str = "all", log_callback=None) -> List[Dict]:
        """
        Execute search on Printerval using stealth automation.
        
        Args:
            query: Keyword string (e.g., 'Toyota TRD')
            max_items: Maximum listings to return
            condition: 'all', 'new', or 'used'
            log_callback: Optional callable for live UI logging
            
        Returns:
            List of normalized listing dicts.
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            logger.info(msg)

        results = []
        seen_ids = set()
        page_num = 1

        encoded_q = urllib.parse.quote(query.strip())
        _log(f"👕 [Printerval] Initiating stealth search for '{query}'...")

        context = self._get_context()
        page = context.pages[0] if context.pages else context.new_page()

        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        try:
            max_pages = max(4, min(15, (max_items + 29) // 30))
            while len(results) < max_items and page_num <= max_pages:
                if page_num == 1:
                    target_url = f"https://printerval.com/search?q={encoded_q}"
                else:
                    target_url = f"https://printerval.com/search?q={encoded_q}&page={page_num}"

                _log(f"🌐 [Printerval] Loading page {page_num}...")
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=22000)
                    page.wait_for_timeout(2500)
                except Exception as ex:
                    _log(f"⚠ Page load timeout on Printerval: {ex}")

                # Extract product cards
                page_items = page.evaluate("""
                    () => {
                        const items = [];
                        const cards = document.querySelectorAll(
                            '.product-item, .item, [class*="product-card"], a[href*="-p"], div[data-product-id]'
                        );
                        
                        for (let c of cards) {
                            const link = c.tagName === 'A' ? c : c.querySelector('a');
                            if (!link) continue;
                            const href = link.href || '';
                            if (!href.includes('-p')) continue;

                            const titleEl = c.querySelector('[class*="title"], h3, h2, span.title') || link;
                            const priceEl = c.querySelector('[class*="price"], .product-price, span[class*="price"]');
                            const sellerEl = c.querySelector('[class*="author"], [class*="artist"], [class*="store"], [class*="seller"]');

                            const title = titleEl ? (titleEl.innerText || '').trim() : '';
                            const price = priceEl ? (priceEl.innerText || '').trim() : '';
                            const seller = sellerEl ? (sellerEl.innerText || '').trim() : '';

                            // Find real image (ignoring svgs and heart icons)
                            let img = '';
                            const allImgs = Array.from(c.querySelectorAll('img')).map(i => i.src || i.getAttribute('data-src') || i.getAttribute('data-original') || '');
                            for (let im of allImgs) {
                                if (im && !im.includes('.svg') && !im.includes('heart') && (im.includes('cdn.printerval.com') || im.startsWith('http'))) {
                                    img = im;
                                    break;
                                }
                            }

                            if (href && (title || price || img)) {
                                items.push({
                                    title: title,
                                    url: href,
                                    price: price,
                                    seller: seller || 'Printerval Creator',
                                    image_url: img
                                });
                            }
                        }
                        return items;
                    }
                """)

                if not page_items:
                    _log(f"ℹ [Printerval] No listing cards found on page {page_num}.")
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
                        # Derive title from url slug
                        slug_part = u.split("/")[-1].split("-p")[0].replace("-", " ").title()
                        title = slug_part if slug_part else f"Printerval Product #{item_id}"

                    price = raw_it.get("price", "")
                    if not price or not price.startswith("$"):
                        price = "$19.95"

                    results.append({
                        "brand": "",
                        "product_type": "Merchandise",
                        "title": title,
                        "item_id": item_id,
                        "price": price,
                        "seller": raw_it.get("seller") or "Printerval Creator",
                        "location": "United States",
                        "image_url": raw_it.get("image_url", ""),
                        "url": u,
                        "marketplace": "printerval.com",
                        "condition": "New",
                        "keyword": query
                    })
                    new_count += 1

                    if len(results) >= max_items:
                        break

                _log(f"📦 [Printerval] Harvested {new_count} listings from page {page_num} ({len(results)}/{max_items} total).")

                if len(results) >= max_items or new_count == 0:
                    break

                page_num += 1
                time.sleep(1.5)

        except Exception as e:
            _log(f"❌ Error during Printerval scraping: {e}")
            logger.exception("Printerval search failure")
        finally:
            if self.headless:
                self.close()

        _log(f"✅ [Printerval] Search complete: Retrieved {len(results)} listings.")
        return results

    def enrich_seller_info(self, items: List[Dict],
                           progress_callback=None,
                           stop_event: threading.Event = None,
                           chunk_size: int = 15) -> List[Dict]:
        """
        Enrich real creator / artist / shop names and exact pricing for Printerval items.
        Uses persistent disk cache to resolve previously seen items in 0ms.
        """
        if not items:
            return items

        cache = self._load_cache()
        items_to_fetch = []

        # Pass 1: Resolve from local cache
        for idx, it in enumerate(items):
            item_id = str(it.get("item_id", "")).strip()
            if item_id and item_id in cache and cache[item_id].get("image_url"):
                cached = cache[item_id]
                it["seller"] = cached.get("seller", it.get("seller"))
                if cached.get("price"):
                    it["price"] = cached.get("price")
                if cached.get("title") and (not it.get("title") or it.get("title").startswith("Printerval")):
                    it["title"] = cached.get("title")
                if cached.get("image_url") and not it.get("image_url"):
                    it["image_url"] = cached.get("image_url")
                if progress_callback:
                    progress_callback(idx + 1, len(items), it)
            else:
                items_to_fetch.append((idx, it))

        if not items_to_fetch:
            return items

        context = self._get_context()
        page = context.pages[0] if context.pages else context.new_page()

        try:
            processed_in_chunk = 0
            for fetch_idx, (orig_idx, it) in enumerate(items_to_fetch):
                if stop_event and stop_event.is_set():
                    break

                if processed_in_chunk >= chunk_size:
                    time.sleep(random.uniform(2.0, 3.5))
                    processed_in_chunk = 0

                item_id = str(it.get("item_id", "")).strip()
                raw_url = it.get("url", "")
                url = raw_url if raw_url.startswith("http") else f"https://printerval.com/product-p{item_id}"

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=18000)
                    page.wait_for_timeout(1800)

                    # Extract exact creator, price, and canonical title
                    res = page.evaluate("""() => {
                        let seller = '';
                        let price = '';
                        let title = '';

                        // 0. Direct JS variables (window.product, sellerNameProductDescription, etc.)
                        try {
                            if (window.product && window.product.seller_name) {
                                seller = String(window.product.seller_name).trim();
                            }
                        } catch(e) {}

                        if (!seller) {
                            try {
                                if (typeof sellerNameProductDescription !== 'undefined' && sellerNameProductDescription) {
                                    seller = String(sellerNameProductDescription).trim();
                                }
                            } catch(e) {}
                        }

                        // 1. Script tag parsing for var product or var sellerNameProductDescription
                        if (!seller) {
                            const scripts = document.querySelectorAll('script');
                            for (let s of scripts) {
                                const txt = s.innerText || '';
                                const m = txt.match(/["']seller_name["']\\s*:\\s*["']([^"']+)["']/i) || 
                                          txt.match(/var\\s+sellerNameProductDescription\\s*=\\s*["']([^"']+)["']/i);
                                if (m && m[1]) {
                                    const cand = m[1].trim();
                                    if (cand && !cand.toLowerCase().includes('printerval') && cand.length > 1) {
                                        seller = cand;
                                        break;
                                    }
                                }
                            }
                        }

                        // 2. Author / Creator element
                        if (!seller) {
                            const authorEls = document.querySelectorAll(
                                'span.author, .author, .design-pod-seller, .other-product-heading-author, .other-product-heading-author-info, [class*="shop-name"], a[href*="/shop/"], a[href*="/designer/"]'
                            );
                            for (let el of authorEls) {
                                let raw = el ? (el.innerText || '') : '';
                                let txt = raw.trim()
                                    .replace(/^Designed\\s+(?:and\\s+sold\\s+)?by\\s*/i, '')
                                    .replace(/More\\s+/i, '')
                                    .replace(/'s\\s+products.*/i, '')
                                    .trim();
                                if (txt && txt.length > 1 && !txt.toLowerCase().includes('printerval') && !txt.toLowerCase().includes('designed')) {
                                    seller = txt.split('\\n')[0].trim();
                                    break;
                                }
                            }
                        }

                        // 3. Fallback via regex across full body text
                        if (!seller && document.body) {
                            const fullText = document.body.innerText || '';
                            const m = fullText.match(/(?:Designed|Sold|Created)\\s+(?:and\\s+sold\\s+)?by\\s*\\n?\\s*([^\\n\\r]+)/i);
                            if (m && m[1]) {
                                let candidate = m[1].trim();
                                if (candidate && !candidate.toLowerCase().includes('printerval')) {
                                    seller = candidate;
                                }
                            }
                        }

                        // 4. Fallback for "More <Artist>'s products"
                        if (!seller && document.body) {
                            const fullText = document.body.innerText || '';
                            const m2 = fullText.match(/More\\s+([^\\n\\r']+)'s\\s+products/i);
                            if (m2 && m2[1]) {
                                seller = m2[1].trim();
                            }
                        }

                        // Canonical Title from H1
                        const h1 = document.querySelector('h1');
                        if (h1 && h1.innerText) title = h1.innerText.trim();

                        // Price from JSON-LD or DOM
                        const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                        for (let s of scripts) {
                            try {
                                const j = JSON.parse(s.innerText || '{}');
                                if (j['@type'] === 'Product' && j.offers && j.offers.price) {
                                    price = '$' + j.offers.price;
                                    break;
                                }
                            } catch(e) {}
                        }

                        if (!price) {
                            const priceEl = document.querySelector('.product-price-current, .pdp-price, .price, [class*="product-price"]');
                            if (priceEl && priceEl.innerText) {
                                const mP = priceEl.innerText.match(/\\$\\s*[\\d,]+(?:\\.\\d+)?/);
                                if (mP) price = mP[0];
                            }
                        }

                        // 4. Extract High-Resolution Product Image
                        let img = '';
                        const og = document.querySelector('meta[property="og:image"], meta[name="og:image"]');
                        if (og && og.content && og.content.startsWith('http')) {
                            img = og.content;
                        }
                        if (!img) {
                            for (let s of scripts) {
                                try {
                                    const j = JSON.parse(s.innerText || '{}');
                                    if (j['image']) {
                                        if (Array.isArray(j['image']) && j['image'].length > 0) {
                                            img = j['image'][0];
                                        } else if (typeof j['image'] === 'string') {
                                            img = j['image'];
                                        }
                                        if (img) break;
                                    }
                                } catch(e) {}
                            }
                        }
                        if (!img) {
                            const domImgs = Array.from(document.querySelectorAll('img')).map(i => i.src || i.getAttribute('data-src') || '');
                            for (let di of domImgs) {
                                if (di && di.includes('cdn.printerval.com') && !di.includes('.svg')) {
                                    img = di;
                                    break;
                                }
                            }
                        }

                        return { seller: seller, price: price, title: title, image_url: img };
                    }""")

                    if res.get("seller"):
                        it["seller"] = res["seller"]
                    if res.get("price"):
                        it["price"] = res["price"]
                    if res.get("title") and (not it.get("title") or it.get("title").startswith("Printerval") or len(it.get("title", "")) < len(res.get("title", ""))):
                        it["title"] = res["title"]
                    if res.get("image_url") and (not it.get("image_url") or "unsafe/540" in it.get("image_url", "")):
                        it["image_url"] = res["image_url"]

                    # Cache result
                    if item_id:
                        cache[item_id] = {
                            "seller": it.get("seller"),
                            "price": it.get("price"),
                            "title": it.get("title"),
                            "image_url": it.get("image_url")
                        }

                except Exception as item_err:
                    logger.debug(f"Error enriching item {item_id} ({url}): {item_err}")

                processed_in_chunk += 1
                if progress_callback:
                    progress_callback(orig_idx + 1, len(items), it)

                time.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            logger.error(f"Error during Printerval seller enrichment batch: {e}")
        finally:
            self._save_cache(cache)
            if self.headless:
                self.close()

        return items

    def expand_design_variants(self, items: List[Dict],
                               existing_item_ids: Optional[set] = None,
                               progress_callback=None,
                               stop_event: threading.Event = None,
                               log_callback=None) -> List[Dict]:
        """
        Dredge and harvest all Print-on-Demand (POD) design variants for given Printerval listings.
        Each parent design listing can expand into 40-50+ real product listings
        (Hoodies, Mugs, Stickers, Onesies, Tank Tops, House Flags, Baseball Caps, Blankets, Bags, etc.).
        
        Args:
            items: List of parent design listing dicts to expand.
            existing_item_ids: Optional set of already known item IDs to prevent duplicates.
            progress_callback: Optional callable(current, total, new_variants_found, item)
            stop_event: Optional threading.Event to abort early.
            log_callback: Optional live logger callable.
            
        Returns:
            List of newly discovered variant listing dicts.
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
            if iid:
                known_ids.add(iid)

        expanded_results = []
        context = self._get_context()
        page = context.pages[0] if context.pages else context.new_page()

        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        try:
            total_parents = len(items)
            for idx, parent in enumerate(items):
                if stop_event and stop_event.is_set():
                    _log("⏹ [Printerval] Variant expansion cancelled by user.")
                    break

                parent_id = str(parent.get("item_id", "")).strip()
                raw_url = parent.get("url", "")
                url = raw_url if raw_url.startswith("http") else f"https://printerval.com/product-p{parent_id}"
                seller = parent.get("seller") or "Printerval Creator"
                brand = parent.get("brand", "")
                keyword = parent.get("keyword", "")
                parent_title = parent.get("title", "")

                _log(f"👕 [Printerval] Expanding variants for [{idx+1}/{total_parents}]: '{parent_title[:35]}...'")

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(2500)

                    # Click 'See all items' if present to expand full catalog modal/drawer
                    page.evaluate("""() => {
                        const btn = document.querySelector('.show-more-also-available, .component-seemore');
                        if (btn) {
                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                            btn.click();
                        } else {
                            const spans = Array.from(document.querySelectorAll('a, span, button, div'));
                            for (let s of spans) {
                                if ((s.innerText || '').trim().toLowerCase() === 'see all items') {
                                    s.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    s.click();
                                    break;
                                }
                            }
                        }
                    }""")
                    page.wait_for_timeout(2000)

                    # Extract all variant links and metadata strictly from variant containers
                    extracted_variants = page.evaluate("""(parentId) => {
                        const items = [];
                        const seen = new Set();
                        
                        const selectors = [
                            'a[data-source-box="also-available"]',
                            '.js-also-available-product a',
                            '#modal-also-available a[href*="-p"]',
                            '.modal-also-available a[href*="-p"]',
                            '.tab-more-also-available-product a[href*="-p"]',
                            '.tab-more-also-available-product-wrapper a[href*="-p"]',
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
                            
                            // Text / Title
                            let title = '';
                            const titleEl = a.querySelector('[class*="title"], h3, h2, h4, span.title, p') || a;
                            if (titleEl) {
                                title = (titleEl.innerText || titleEl.getAttribute('title') || '').trim();
                            }
                            
                            // Price
                            let price = '';
                            const priceEl = parentEl.querySelector('[class*="price"], .product-price-current, span');
                            if (priceEl) {
                                const mP = (priceEl.innerText || '').match(/\\$\\s*[\\d,]+(?:\\.\\d+)?/);
                                if (mP) price = mP[0];
                            }
                            
                            // High-Res Image Extraction (prioritize picture > source to avoid 1x1 placeholder pngs)
                            let img = '';
                            const picture = a.querySelector('picture') || (parentEl ? parentEl.querySelector('picture') : null);
                            if (picture) {
                                const source = picture.querySelector('source');
                                if (source && source.srcset) {
                                    const urls = source.srcset.match(/https?:\\/\\/[^\\s"']+/g);
                                    if (urls && urls.length > 0) {
                                        img = urls[urls.length - 1].replace(/\\s+\\d+[wx]$/, '').trim();
                                    }
                                }
                            }
                            if (!img) {
                                const imgEl = a.querySelector('img') || (parentEl ? parentEl.querySelector('img') : null);
                                if (imgEl) {
                                    if (imgEl.currentSrc && imgEl.currentSrc.startsWith('http') && !imgEl.currentSrc.includes('1x1.png') && !imgEl.currentSrc.includes('data:')) {
                                        img = imgEl.currentSrc;
                                    } else if (imgEl.src && imgEl.src.startsWith('http') && !imgEl.src.includes('1x1.png') && !imgEl.src.includes('data:')) {
                                        img = imgEl.src;
                                    } else if (imgEl.getAttribute('data-src') && imgEl.getAttribute('data-src').startsWith('http')) {
                                        img = imgEl.getAttribute('data-src');
                                    } else if (imgEl.getAttribute('data-original') && imgEl.getAttribute('data-original').startsWith('http')) {
                                        img = imgEl.getAttribute('data-original');
                                    }
                                }
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

                    new_for_this_parent = 0

                    for v in extracted_variants:
                        v_id = str(v.get("item_id", "")).strip()
                        if not v_id or v_id in known_ids:
                            continue

                        u = v.get("url", "")
                        slug = u.split("/")[-1].split("-p")[0]

                        card_raw = v.get("title", "").replace("\n", " ").strip()
                        card_clean = re.sub(r'\$\s*[\d,]+(?:\.\d+)?', '', card_raw).strip()

                        # Derive clean product type from slug
                        type_part = slug.split("-")[-1].title() if "-" in slug else "Merchandise"
                        if len(type_part) <= 2:
                            type_part = "Merchandise"

                        # Synthesize full, clean listing title preserving parent design casing and full name
                        v_title = self._synthesize_variant_title(parent_title, slug, card_clean)

                        # Token & Brand relevance validation: ensure variant matches the specific POD artwork/design
                        if not self._is_valid_pod_variant(parent_title, v_title, slug, brand=brand, keyword=keyword):
                            continue

                        known_ids.add(v_id)

                        price = v.get("price") or parent.get("price") or "$19.95"
                        variant_id = v_id if v_id else (re.search(r'-p(\d+)', u).group(1) if re.search(r'-p(\d+)', u) else f"{parent_id}_{slug}")
                        v_img = v.get("image_url", "") or parent.get("image_url", "")
                        variant_item = {
                            "brand": brand,
                            "product_type": type_part,
                            "title": v_title,
                            "item_id": variant_id,
                            "price": price,
                            "seller": seller,
                            "location": "United States",
                            "image_url": v_img,
                            "thumbnail": v_img,
                            "url": u,
                            "marketplace": "printerval.com",
                            "condition": "New",
                            "keyword": keyword
                        }
                        expanded_results.append(variant_item)
                        new_for_this_parent += 1

                    _log(f"  ✓ Harvested +{new_for_this_parent} POD product variants for '{parent.get('title', '')[:30]}...' (Total new: {len(expanded_results)})")

                    if progress_callback:
                        progress_callback(idx + 1, total_parents, len(expanded_results), parent)

                except Exception as ex:
                    _log(f"⚠ [Printerval] Error expanding variants for {url}: {ex}")

                time.sleep(random.uniform(0.8, 1.5))

        except Exception as e:
            _log(f"❌ [Printerval] Error during variant expansion batch: {e}")
            logger.exception("Printerval variant expansion failure")
        finally:
            if self.headless:
                self.close()

        _log(f"✅ [Printerval] Variant dredge complete: Added {len(expanded_results)} new POD listing URLs.")
        return expanded_results

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
        On-Demand Visual Syndicate & Connected Seller Hunter for Printerval.
        Scans product page recommendation carousels:
        - "You may also like" / "You might love these"
        - "Frequently bought together"
        - "Customers also viewed" / Viewed products list
        - "Related merchandise"
        - "Seller's other products"
        Performs perceptual image matching (dHash) against target_img_url.
        """
        if not item_url and item_id:
            item_url = f"https://printerval.com/product-p{item_id}"
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
                with urllib.request.urlopen(req, timeout=5) as r:
                    t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                    target_hash = self.compute_dhash(t_img)
            except Exception:
                pass

        try:
            context = self._get_context()
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            page.goto(item_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)

            # Scroll in stages to trigger lazy-loaded carousels
            for _ in range(4):
                try:
                    page.evaluate("window.scrollBy(0, 1000);")
                except Exception:
                    pass
                page.wait_for_timeout(400)

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
                        const img = document.querySelector('img[src*="cdn.printerval.com"]');
                        return img ? (img.currentSrc || img.src || '') : '';
                    }""")
                    if t_src and str(t_src).startswith("http"):
                        req = urllib.request.Request(str(t_src), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                        with urllib.request.urlopen(req, timeout=5) as r:
                            t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                            target_hash = self.compute_dhash(t_img)
                except Exception:
                    pass

            carousels_data = page.evaluate("""() => {
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
                            secType = '🏪 Seller\\'s Other Products';
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
                            const sEl = card.querySelector('[class*="author"], [class*="artist"], [class*="store"], [class*="seller"], [class*="shop"]');

                            let title = tEl ? (tEl.innerText || '').trim() : '';
                            let price = pEl ? (pEl.innerText || '').trim() : '';
                            let seller = sEl ? (sEl.innerText || '').trim() : '';

                            // Extract image with complete data-srcset / data-original / lazy-load support
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
            }""")

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
                price_disp = m_price.group(0) if m_price else "$19.95"

                seller_name = itm.get("seller") or ""
                if not seller_name and c_id in cache:
                    seller_name = cache[c_id].get("seller", "")
                if not seller_name:
                    seller_name = "Printerval Creator"

                title = itm.get("title", "")
                if not title or title.startswith("$") or len(title) < 3:
                    slug_part = u.split("/")[-1].split("-p")[0].replace("-", " ").title()
                    title = slug_part if slug_part else f"Printerval Product #{c_id}"

                img_url = itm.get("image_url", "")
                sim_label = itm.get("network_type", "👥 You Might Also Like")

                if target_hash and img_url and str(img_url).startswith("http"):
                    try:
                        req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                        with urllib.request.urlopen(req, timeout=3) as r:
                            cand_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                            cand_hash = self.compute_dhash(cand_img)
                            dist = self.hamming_distance(target_hash, cand_hash)
                            if dist <= 6:
                                sim_label = f"🎯 Exact Photo Match (dHash: {dist})"
                            elif dist <= 14:
                                sim_label = f"🖼 Visual Match (dHash: {dist})"
                    except Exception:
                        pass

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
                    "marketplace": "printerval.com",
                    "condition": itm.get("network_type", "You Might Also Like"),
                    "similarity": sim_label,
                    "match_type": itm.get("network_type", "You Might Also Like")
                })

        except Exception as e:
            logger.debug(f"Error finding connected network for Printerval item {item_url}: {e}")
        finally:
            if self.headless:
                self.close()

        return results

