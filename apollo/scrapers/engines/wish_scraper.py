import re
import os
import time
import random
import tempfile
import threading
from urllib.parse import urlencode, quote_plus, urlparse
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as curl_requests
    HAS_CURL_CFFI = False


MAX_PAGES = 5


class WishScraper:
    def __init__(self, headless=False):
        """
        Stealth Scraper for Wish.com search and merchant stores with
        session persistence, smooth scroll harvesting, and client-side exclusion filtering.
        """
        self.headless = headless
        self.max_items = 50
        self.profile_dir = os.path.join(tempfile.gettempdir(), "wish_harvester_profile")

    def resolve_store_info(self, raw_input: str) -> dict:
        """Parse Wish merchant URL, Merchant ID, or Global Search."""
        raw = raw_input.strip() if raw_input else ""

        # Check for Merchant ID in URL (e.g., wish.com/merchant/5b8f... or wish.com/store/...)
        m = re.search(r"/(?:merchant|store)/([a-zA-Z0-9_\-]+)", raw)
        if m:
            store_id = m.group(1)
            return {
                "store_id": store_id,
                "store_name": f"Wish Merchant {store_id[:8]}",
                "original": raw
            }

        low = raw.lower()
        if not raw or any(g in low for g in ("global", "marketplace", "all", "wish", "full search", "catalog")):
            return {
                "store_id": "GLOBAL",
                "store_name": "Wish Global Search",
                "original": "https://www.wish.com"
            }

        # If pure alphanumeric merchant ID
        if re.match(r"^[a-zA-Z0-9_\-]+$", raw) and len(raw) > 10:
            return {
                "store_id": raw,
                "store_name": f"Wish Merchant {raw[:8]}",
                "original": f"https://www.wish.com/merchant/{raw}"
            }

        clean_name = raw.split("/")[-1].replace(".html", "")
        return {
            "store_id": clean_name,
            "store_name": clean_name or "Wish Merchant",
            "original": raw if raw.startswith("http") else f"https://www.wish.com/merchant/{raw}"
        }

    def search(self, store_url: str, include_term: str,
               exclude_terms: list[str] = None,
               condition: str = "all",
               stop_event: threading.Event = None,
               pause_event: threading.Event = None,
               max_items: int = None) -> list[dict]:
        """
        Search Wish.com catalog or merchant store for include_term, client-filtering exclude_terms.
        Supports real-time pause and cancel events and configurable item depth.
        """
        store_info = self.resolve_store_info(store_url)
        exclude_terms = [e.strip().lower() for e in (exclude_terms or []) if e.strip()]

        items = []
        seen_ids = set()

        if HAS_PLAYWRIGHT:
            try:
                items = self._search_via_playwright(
                    store_info, include_term, exclude_terms, condition, seen_ids,
                    stop_event=stop_event, pause_event=pause_event,
                    max_items=max_items
                )
                if items or (stop_event and stop_event.is_set()):
                    return items
            except Exception:
                pass

        # Fallback to requests if playwright fails
        url = self._build_search_url(store_info, include_term, 1)
        html = self._fetch_via_requests(url)
        if html:
            items = self._parse_html(html, store_info.get("store_name", "Wish Merchant"), include_term, exclude_terms)

        return items

    def _build_search_url(self, store_info: dict, keyword: str, page: int = 1) -> str:
        """Construct the search URL on Wish.com."""
        store_id = store_info.get("store_id", "")
        enc_kw = quote_plus(keyword)

        if not store_id or store_id == "GLOBAL" or "global" in str(store_id).lower():
            # Standard Wish search query
            return f"https://www.wish.com/search/{enc_kw}"

        orig = store_info.get("original", "")
        if "wish.com" in orig and "/merchant/" in orig:
            sep = "&" if "?" in orig else "?"
            return f"{orig}{sep}q={enc_kw}"

        return f"https://www.wish.com/merchant/{store_id}?q={enc_kw}"

    def _launch_browser_context(self, p, launch_args: list, ua: str):
        """Safely launch persistent Edge context with automatic stale lock cleanup and fallback temp profiles."""
        for lk in ("SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile", "LOCK"):
            fp = os.path.join(self.profile_dir, lk)
            try:
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass

        try:
            return p.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                channel="msedge",
                headless=self.headless,
                args=launch_args,
                user_agent=ua,
                viewport={"width": 1440, "height": 900},
                locale="en-US"
            )
        except Exception:
            temp_profile = tempfile.mkdtemp(prefix="wish_edge_session_")
            try:
                return p.chromium.launch_persistent_context(
                    user_data_dir=temp_profile,
                    channel="msedge",
                    headless=self.headless,
                    args=launch_args,
                    user_agent=ua,
                    viewport={"width": 1440, "height": 900},
                    locale="en-US"
                )
            except Exception:
                return p.chromium.launch_persistent_context(
                    user_data_dir=temp_profile,
                    headless=self.headless,
                    args=launch_args,
                    user_agent=ua,
                    viewport={"width": 1440, "height": 900},
                    locale="en-US"
                )

    def _search_via_playwright(self, store_info: dict,
                               include_term: str, excludes: list[str],
                               condition: str, seen_ids: set,
                               stop_event: threading.Event = None,
                               pause_event: threading.Event = None,
                               max_items: int = None) -> list[dict]:
        """Execute stealth Playwright browser scraping for Wish.com with configurable scroll depth."""
        items = []
        seller_label = store_info.get("store_name", "Wish Merchant")
        target_count = max_items or getattr(self, "max_items", 50)

        with sync_playwright() as p:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"

            browser_context = self._launch_browser_context(p, launch_args, ua)
            page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()

            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """)

            try:
                if stop_event and stop_event.is_set():
                    return items
                if pause_event:
                    pause_event.wait()

                url = self._build_search_url(store_info, include_term, 1)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                except Exception:
                    pass

                # Auto-dismiss Wish popups / cookie consents / overlay modals
                try:
                    page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('button, [role="button"], [class*="close"], [class*="Close"], [aria-label*="close"], [aria-label*="Close"]'));
                        for (const b of buttons) {
                            const txt = (b.innerText || '').trim().toLowerCase();
                            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                            if (txt === 'accept' || txt === 'accept all' || txt === 'opt-out' || txt === 'got it' || txt === 'close' || aria.includes('close')) {
                                try { b.click(); } catch(e) {}
                                break;
                            }
                        }
                        document.querySelectorAll('[class*="ModalContainer"], [class*="modal-root"], [class*="Backdrop"], [class*="Overlay"]').forEach(el => {
                            const low = el.innerText.toLowerCase();
                            if (low.includes('accept') || low.includes('cookie') || low.includes('terms') || low.includes('welcome') || low.includes('sign in') || low.includes('log in')) {
                                try { el.remove(); } catch(e) {}
                            }
                        });
                    }""")
                except Exception:
                    pass

                # Adaptive progressive scrolling based on target max_items
                max_scroll_cycles = max(5, min(40, int(target_count / 4)))
                consecutive_no_change = 0
                last_count = 0

                for _ in range(max_scroll_cycles):
                    if stop_event and stop_event.is_set():
                        break
                    if pause_event:
                        pause_event.wait()

                    current_count = page.evaluate("""() => {
                        const seen = new Set();
                        document.querySelectorAll('a[href*="/product/"], a[href*="/c/"]').forEach(a => {
                            const m = (a.href || '').match(/\\/(?:product|c)\\/([a-zA-Z0-9]+)/);
                            if (m) seen.add(m[1]);
                        });
                        return seen.size;
                    }""")

                    if current_count >= target_count:
                        break

                    if current_count > 0 and current_count == last_count:
                        consecutive_no_change += 1
                        if consecutive_no_change >= 3:
                            break
                    else:
                        consecutive_no_change = 0
                    last_count = current_count

                    try:
                        page.evaluate("window.scrollBy(0, 1200)")
                    except Exception:
                        pass
                    time.sleep(0.7)

                time.sleep(0.8)

                html = page.content()
                page_items = self._parse_html(html, seller_label, include_term, excludes)

                if not page_items:
                    page_items = self._extract_dom_items(page, seller_label, include_term, excludes)

                for it in page_items:
                    iid = it.get("item_id")
                    dedup_key = iid if iid else it.get("url")
                    if dedup_key and dedup_key not in seen_ids:
                        seen_ids.add(dedup_key)
                        items.append(it)
                        if len(items) >= target_count:
                            break

            finally:
                try:
                    browser_context.close()
                except Exception:
                    pass

        return items

    def _extract_dom_items(self, page, seller_label: str, include_term: str, excludes: list[str]) -> list[dict]:
        """Extract product cards directly via Playwright JS evaluation."""
        try:
            raw_cards = page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href*="/product/"], a[href*="/c/"]');
                    const seen = new Set();

                    links.forEach(a => {
                        const href = a.href || '';
                        const m = href.match(/\\/(?:product|c)\\/([a-zA-Z0-9]+)/);
                        if (!m) return;
                        const itemId = m[1];
                        if (seen.has(itemId)) return;
                        seen.add(itemId);

                        const card = a.closest('div[class*="ProductGridItem"], div[class*="ProductCard"], div[class*="FeedItem"], [data-testid*="product-card"]') || a.parentElement;
                        
                        let title = a.innerText.trim() || a.getAttribute('title') || '';
                        let img = '';
                        let price = '';
                        let seller = '';

                        if (card) {
                            const imgEl = card.querySelector('img');
                            if (imgEl) {
                                img = imgEl.currentSrc || imgEl.src || imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '';
                                if (!img && imgEl.srcset) {
                                    const parts = imgEl.srcset.split(',');
                                    if (parts.length > 0) img = parts[parts.length - 1].trim().split(' ')[0];
                                }
                            }
                            if (!title) {
                                const titleEl = card.querySelector('h1, h2, h3, div[class*="Title"], span[class*="Title"], [class*="product-title"]');
                                if (titleEl) title = titleEl.innerText.trim();
                            }
                            const priceEl = card.querySelector('div[class*="Price"], span[class*="Price"], div[class*="price"], [class*="product-price"]');
                            if (priceEl) price = priceEl.innerText.trim();

                            const storeEl = card.querySelector('a[href*="/merchant/"], span[class*="merchant"], [class*="store-name"]');
                            if (storeEl) seller = storeEl.innerText.trim();
                        }

                        if (img && img.startsWith('//')) img = 'https:' + img;

                        results.push({
                            title: title || `Wish Product ${itemId}`,
                            url: href.split('?')[0],
                            item_id: itemId,
                            image_url: img,
                            price: price || "$0.00",
                            seller: seller
                        });
                    });
                    return results;
                }
            """)

            parsed = []
            for c in raw_cards:
                title = c.get("title", "").strip()
                if not title:
                    continue

                title_lower = title.lower()
                if any(ex in title_lower for ex in excludes):
                    continue

                parsed.append({
                    "title": title,
                    "url": c.get("url", ""),
                    "image_url": c.get("image_url", ""),
                    "item_id": c.get("item_id", ""),
                    "price": c.get("price", "N/A"),
                    "seller": c.get("seller") or seller_label,
                    "location": "Global",
                    "marketplace": "wish.com",
                    "keyword": include_term,
                    "product_type": "",
                    "brand": ""
                })
            return parsed
        except Exception:
            return []

    def _parse_html(self, html: str, seller_label: str, include_term: str, excludes: list[str]) -> list[dict]:
        """Parse raw HTML for Wish.com product listings and apply exclusion filters."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        items = []
        seen_ids = set()

        item_links = soup.find_all("a", href=re.compile(r"/(?:product|c)/([a-zA-Z0-9]+)"))

        for link in item_links:
            href = link.get("href", "")
            if not href.startswith("http"):
                href = "https:" + href if href.startswith("//") else f"https://www.wish.com{href}"

            clean_url = href.split("?")[0]
            m = re.search(r"/(?:product|c)/([a-zA-Z0-9]+)", clean_url)
            if not m:
                continue

            item_id = m.group(1)
            if item_id in seen_ids:
                continue

            card = link.parent

            # 1. Price extraction
            raw_text = link.get_text(separator=" ", strip=True)
            m_p = re.search(r"(?:US\s*\$|\$|€|£)\s*[\d,]+(?:\.\d+)?", raw_text)
            price = m_p.group(0) if m_p else "N/A"

            # 2. Title extraction
            title = link.get("title", "").strip()
            if not title and card:
                title_el = card.find(["h1", "h3", "h2", "div"])
                if title_el and len(title_el.get_text(strip=True)) > 5:
                    title = title_el.get_text(strip=True)

            if not title:
                t_clean = re.split(r"(?:US\s*\$|\$|€|£)\s*\d", raw_text)[0].strip()
                t_clean = re.sub(r"(?:colors|sizes|verified|sold).*$", "", t_clean, flags=re.I).strip()
                if len(t_clean) > 4:
                    title = t_clean

            if not title and card:
                img_el = card.find("img")
                if img_el and img_el.get("alt"):
                    title = img_el.get("alt").strip()

            if not title or len(title) < 4:
                continue

            title_lower = title.lower()
            if any(ex in title_lower for ex in excludes):
                continue

            # 3. Image extraction
            img_url = ""
            if card:
                img_tag = card.find("img")
                if img_tag:
                    img_url = img_tag.get("src") or img_tag.get("data-src") or ""
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url

            # 4. Merchant extraction
            card_seller = seller_label
            if card:
                m_link = card.find("a", href=re.compile(r"/merchant/"))
                if m_link:
                    card_seller = m_link.get_text(strip=True) or card_seller

            seen_ids.add(item_id)
            items.append({
                "title": title,
                "url": clean_url,
                "image_url": img_url,
                "item_id": item_id,
                "price": price,
                "seller": card_seller,
                "location": "Global",
                "marketplace": "wish.com",
                "keyword": include_term,
                "product_type": "",
                "brand": ""
            })

        return items

    def _fetch_via_requests(self, url: str) -> str:
        """Fetch Wish.com HTML using curl_cffi impersonation."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.wish.com/"
        }
        try:
            if HAS_CURL_CFFI:
                resp = curl_requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
            else:
                resp = curl_requests.get(url, headers=headers, timeout=15)

            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return ""

    # ── Local Disk Store Cache ───────────────────────────────────────────────
    def _get_cache_path(self) -> str:
        return os.path.join(tempfile.gettempdir(), "wish_store_cache.json")

    def _load_cache(self) -> dict:
        p = self._get_cache_path()
        if os.path.exists(p):
            try:
                import json
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self, cache: dict):
        p = self._get_cache_path()
        try:
            import json
            with open(p, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

    # ── High-Reliability Paced Seller Enrichment Engine ─────────────────────
    def enrich_seller_info(self, items: list[dict],
                           progress_callback=None,
                           stop_event: threading.Event = None,
                           chunk_size: int = 15) -> list[dict]:
        """
        Adaptive Batch Resolver for Wish.com item merchant names and store IDs with:
        1. Persistent local disk cache (instantly resolves previously seen items in 0ms)
        2. Human micro-jitter pacing (1.5s - 2.8s) to prevent velocity flags
        3. Cool-down breathing intervals every chunk (15 items)
        """
        if not HAS_PLAYWRIGHT or not items:
            return items

        cache = self._load_cache()
        items_to_fetch = []

        # Pass 1: Resolve from local cache first (0ms latency, zero network hits)
        for idx, it in enumerate(items):
            item_id = it.get("item_id")
            if item_id and item_id in cache:
                cached_info = cache[item_id]
                it["seller"] = cached_info.get("seller", it.get("seller"))
                if cached_info.get("store_id"):
                    it["store_id"] = cached_info.get("store_id")
                if progress_callback:
                    progress_callback(idx + 1, len(items), it)
            else:
                current_seller = it.get("seller", "")
                if not current_seller or any(g in current_seller.lower() for g in ("global", "seller", "wish")):
                    items_to_fetch.append((idx, it))

        if not items_to_fetch:
            return items

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars"
        ]
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"

        with sync_playwright() as p:
            browser_context = self._launch_browser_context(p, launch_args, ua)
            page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()

            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            try:
                processed_in_chunk = 0
                for fetch_idx, (orig_idx, it) in enumerate(items_to_fetch):
                    if stop_event and stop_event.is_set():
                        break

                    if processed_in_chunk >= chunk_size:
                        time.sleep(random.uniform(3.5, 5.0))
                        processed_in_chunk = 0

                    item_id = it.get("item_id")
                    if not item_id:
                        continue

                    url = it.get("url") if it.get("url") and it.get("url").startswith("http") else f"https://www.wish.com/product/{item_id}"
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        try:
                            page.wait_for_selector('a[href*="/merchant/"]', timeout=4000)
                        except Exception:
                            time.sleep(1.5)
                    except Exception:
                        pass

                    merchant_res = page.evaluate("""
                        () => {
                            const storeNameLink = document.querySelector('a[class*="StoreNameLink"], a[class*="storeName"]');
                            if (storeNameLink && storeNameLink.innerText.trim()) {
                                const m = storeNameLink.href.match(/\\/(?:merchant|store)\\/([a-zA-Z0-9_\\-]+)/);
                                return {
                                    store_id: m ? m[1] : '',
                                    seller_name: storeNameLink.innerText.trim()
                                };
                            }

                            const links = Array.from(document.querySelectorAll('a[href*="/merchant/"], a[href*="/store/"]'));
                            let foundId = '';
                            let foundName = '';

                            for (const a of links) {
                                const m = a.href.match(/\\/(?:merchant|store)\\/([a-zA-Z0-9_\\-]+)/);
                                if (m) {
                                    foundId = m[1];
                                    const txt = a.innerText.trim();
                                    if (txt && !txt.toLowerCase().includes('view store') && txt.length > 1) {
                                        foundName = txt;
                                        break;
                                    }
                                }
                            }

                            return {
                                store_id: foundId,
                                seller_name: foundName || (foundId ? `Wish Merchant ${foundId.slice(0,8)}` : '')
                            };
                        }
                    """)

                    s_name = merchant_res.get("seller_name")
                    s_id = merchant_res.get("store_id")

                    if s_name:
                        it["seller"] = s_name
                        if s_id:
                            it["store_id"] = s_id
                        cache[item_id] = {"seller": s_name, "store_id": s_id}

                    processed_in_chunk += 1
                    if progress_callback:
                        progress_callback(orig_idx + 1, len(items), it)

                    # Micro-jitter delay
                    time.sleep(random.uniform(1.2, 2.2))

            finally:
                try:
                    self._save_cache(cache)
                    browser_context.close()
                except Exception:
                    pass

        return items
