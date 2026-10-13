import re
import os
import time
import random
import tempfile
import threading
from urllib.parse import urlencode, quote_plus
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


class TemuScraper:
    def __init__(self, headless=False):
        """
        Stealth Scraper for Temu.com search with session persistence,
        popup bypass, smooth scrolling, and client-side exclusion filtering.
        """
        self.headless = headless
        self.profile_dir = os.path.join(tempfile.gettempdir(), "temu_harvester_profile")

    def resolve_store_info(self, raw_input: str) -> dict:
        """Parse Temu store URL, Mall ID, or Global Search."""
        raw = raw_input.strip() if raw_input else ""

        if not raw or any(g in raw.lower() for g in ("global", "marketplace", "all", "temu")):
            return {
                "store_id": "GLOBAL",
                "store_name": "Temu Global Search",
                "original": "https://www.temu.com"
            }

        # Check for Mall ID in URL (e.g., temu.com/mall/12345 or temu.com/store/...)
        m = re.search(r"/(?:mall|store)/([a-zA-Z0-9_\-]+)", raw)
        if m:
            store_id = m.group(1)
            return {
                "store_id": store_id,
                "store_name": f"Temu Mall {store_id[:8]}",
                "original": raw
            }

        clean_name = raw.split("/")[-1].replace(".html", "")
        return {
            "store_id": clean_name,
            "store_name": clean_name or "Temu Mall",
            "original": raw if raw.startswith("http") else f"https://www.temu.com/{raw}"
        }

    def search(self, store_url: str, include_term: str,
               exclude_terms: list[str] = None,
               condition: str = "all",
               stop_event: threading.Event = None,
               pause_event: threading.Event = None) -> list[dict]:
        """
        Search Temu for include_term, client-filtering exclude_terms.
        Supports real-time pause and cancel events.
        """
        store_info = self.resolve_store_info(store_url)
        exclude_terms = [e.strip().lower() for e in (exclude_terms or []) if e.strip()]

        items = []
        seen_ids = set()

        if HAS_PLAYWRIGHT:
            try:
                items = self._search_via_playwright(
                    store_info, include_term, exclude_terms, condition, seen_ids,
                    stop_event=stop_event, pause_event=pause_event
                )
                if items or (stop_event and stop_event.is_set()):
                    return items
            except Exception:
                pass

        return items

    def _build_search_url(self, store_info: dict, keyword: str, page: int = 1) -> str:
        """Construct the organic search URL on Temu.com."""
        enc_kw = quote_plus(keyword)
        return f"https://www.temu.com/search_result.html?search_key={enc_kw}&search_method=user&refer_page_el_sn=200010"

    def _launch_browser_context(self, p, launch_args: list, ua: str, headless: bool = None):
        """Safely launch persistent Edge context with automatic stale lock cleanup and fallback temp profiles."""
        for lk in ("SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile", "LOCK"):
            fp = os.path.join(self.profile_dir, lk)
            try:
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass

        is_hl = self.headless if headless is None else headless
        try:
            return p.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                channel="msedge",
                headless=is_hl,
                args=launch_args,
                user_agent=ua,
                viewport={"width": 1440, "height": 900} if is_hl else None,
                locale="en-US"
            )
        except Exception:
            temp_profile = tempfile.mkdtemp(prefix="temu_edge_session_")
            try:
                return p.chromium.launch_persistent_context(
                    user_data_dir=temp_profile,
                    channel="msedge",
                    headless=is_hl,
                    args=launch_args,
                    user_agent=ua,
                    viewport={"width": 1440, "height": 900} if is_hl else None,
                    locale="en-US"
                )
            except Exception:
                return p.chromium.launch_persistent_context(
                    user_data_dir=temp_profile,
                    headless=is_hl,
                    args=launch_args,
                    user_agent=ua,
                    viewport={"width": 1440, "height": 900} if is_hl else None,
                    locale="en-US"
                )

    def _search_via_playwright(self, store_info: dict,
                               include_term: str, excludes: list[str],
                               condition: str, seen_ids: set,
                               stop_event: threading.Event = None,
                               pause_event: threading.Event = None) -> list[dict]:
        """Execute stealth Playwright browser scraping for Temu.com."""
        items = []
        seller_label = store_info.get("store_name", "Temu Seller")

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

                time.sleep(1.5)

                # Attempt automatic dismissal of guest dialogs/coupons
                try:
                    page.evaluate("""
                        () => {
                            const closeSelectors = [
                                'div[aria-label="close"]',
                                'div[class*="close"]',
                                'button[class*="close"]',
                                'svg[class*="close"]',
                                'div[class*="dialog"] button',
                                'div[class*="modal"] button'
                            ];
                            for (const s of closeSelectors) {
                                const el = document.querySelector(s);
                                if (el) { el.click(); }
                            }
                        }
                    """)
                except Exception:
                    pass

                # Check if redirected to login.html or blocked by login modal
                is_login_wall = ("login" in page.url.lower()) or ("login" in (page.title() or "").lower())
                if is_login_wall:
                    if not self.headless:
                        # In visible mode: Give user up to 90 seconds to log in or solve captcha
                        for wait_i in range(90):
                            if stop_event and stop_event.is_set():
                                break
                            time.sleep(1.0)
                            c_url = page.url.lower()
                            c_title = (page.title() or "").lower()
                            # Once user logs in or closes login modal
                            if "login" not in c_url and "login" not in c_title:
                                time.sleep(1.5)
                                # If needed, re-navigate to the search URL now that user is logged in
                                if "search" not in c_url:
                                    try:
                                        page.goto(url, wait_until="domcontentloaded", timeout=20000)
                                        time.sleep(2.0)
                                    except Exception:
                                        pass
                                break
                    else:
                        time.sleep(2.0)

                # Progressive scrolling to load product cards
                for _ in range(5):
                    if stop_event and stop_event.is_set():
                        break
                    time.sleep(0.6)
                    try:
                        page.evaluate("window.scrollBy(0, 900)")
                    except Exception:
                        pass
                time.sleep(1.2)

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
                    const links = document.querySelectorAll('a[href*="-g-"], a[href*="goods_id"], div[data-tooltip*="goodName-"] a');
                    const seen = new Set();

                    links.forEach(a => {
                        const href = a.href || '';
                        let itemId = '';

                        const m1 = href.match(/-g-(\\d+)\\.html/);
                        const m2 = href.match(/goods_id=(\\d+)/);
                        const tooltipEl = a.closest('[data-tooltip*="goodName-"]');
                        const m3 = tooltipEl ? tooltipEl.getAttribute('data-tooltip').match(/goodName-(\\d+)/) : null;

                        if (m1) itemId = m1[1];
                        else if (m2) itemId = m2[1];
                        else if (m3) itemId = m3[1];

                        if (!itemId || seen.has(itemId)) return;
                        seen.add(itemId);

                        const card = a.closest('div[class*="goodsContainer"], div[class*="productCard"], div[class*="goodsItem"]') || a.parentElement.parentElement || a.parentElement;
                        
                        let title = (tooltipEl ? tooltipEl.getAttribute('data-tooltip-title') : '') || a.innerText.trim() || '';
                        title = title.replace(/Open in new tab\\.?/gi, '').replace(/^(Top pick|Local Warehouse|Best seller)\\s*/gi, '').trim();

                        let img = '';
                        let price = '';
                        let seller = '';

                        if (card) {
                            const imgEl = card.querySelector('img');
                            if (imgEl) img = imgEl.src || imgEl.getAttribute('data-src') || '';
                            
                            const text = card.innerText || '';
                            const priceMatch = text.match(/(?:US\\s*\\$|\\$|€|£)\\s*[\\d,]+(?:\\.\\d+)?/);
                            if (priceMatch) price = priceMatch[0];

                            const mallEl = card.querySelector('a[href*="/mall/"], span[class*="mall"]');
                            if (mallEl) seller = mallEl.innerText.trim();
                        }

                        results.push({
                            title: title,
                            url: href.split('?')[0],
                            item_id: itemId,
                            image_url: img,
                            price: price || 'N/A',
                            seller: seller
                        });
                    });
                    return results;
                }
            """)

            parsed = []
            for c in raw_cards:
                title = c.get("title", "").strip()
                if not title or len(title) < 4:
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
                    "location": "CN / Global",
                    "marketplace": "temu.com",
                    "keyword": include_term,
                    "product_type": "",
                    "brand": ""
                })
            return parsed
        except Exception:
            return []

    def _parse_html(self, html: str, seller_label: str, include_term: str, excludes: list[str]) -> list[dict]:
        """Parse raw HTML for Temu product listings and apply exclusion filters."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        items = []
        seen_ids = set()

        item_links = soup.find_all("a", href=re.compile(r"(?:-g-(\d+)\.html|goods_id=(\d+))"))
        if not item_links:
            # Fallback to tooltip containers
            tooltips = soup.find_all("div", attrs={"data-tooltip": re.compile(r"goodName-(\d+)")})
            for t_el in tooltips:
                a_tag = t_el.find("a")
                if a_tag:
                    item_links.append(a_tag)

        for link in item_links:
            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"https://www.temu.com{href}"

            clean_url = href.split("?")[0]
            m = re.search(r"-g-(\d+)\.html", href) or re.search(r"goods_id=(\d+)", href)
            
            tooltip_el = link.find_parent(attrs={"data-tooltip": re.compile(r"goodName-(\d+)")})
            if not m and tooltip_el:
                m_t = re.search(r"goodName-(\d+)", tooltip_el.get("data-tooltip", ""))
                if m_t:
                    item_id = m_t.group(1)
                else:
                    continue
            elif m:
                item_id = m.group(1) or (m.group(2) if len(m.groups()) > 1 else "")
            else:
                continue

            if not item_id or item_id in seen_ids:
                continue

            card = link.find_parent("div", class_=re.compile(r"goodsContainer|productCard|goodsItem")) or link.parent.parent or link.parent

            # 1. Price extraction
            card_text = card.get_text(separator=" ", strip=True) if card else link.get_text(separator=" ", strip=True)
            m_p = re.search(r"(?:US\s*\$|\$|€|£)\s*[\d,]+(?:\.\d+)?", card_text)
            price = m_p.group(0) if m_p else "N/A"

            # 2. Title extraction
            title = ""
            if tooltip_el and tooltip_el.get("data-tooltip-title"):
                title = tooltip_el.get("data-tooltip-title").strip()
            
            if not title:
                h2 = link.find(["h2", "h1", "h3"])
                if h2:
                    title = h2.get_text(separator=" ", strip=True)

            if not title:
                title = link.get_text(separator=" ", strip=True)

            title = re.sub(r"Open in new tab\.?", "", title, flags=re.I)
            title = re.sub(r"^(?:Top pick|Local Warehouse|Best seller)\s*", "", title, flags=re.I).strip()

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

            # 4. Mall / Seller extraction
            card_seller = seller_label
            if card:
                mall_tag = card.find("a", href=re.compile(r"/mall/"))
                if mall_tag:
                    card_seller = mall_tag.get_text(strip=True) or card_seller

            seen_ids.add(item_id)
            items.append({
                "title": title,
                "url": clean_url,
                "image_url": img_url,
                "item_id": item_id,
                "price": price,
                "seller": card_seller,
                "location": "CN / Global",
                "marketplace": "temu.com",
                "keyword": include_term,
                "product_type": "",
                "brand": ""
            })

        return items

    # ── Local Disk Store Cache ───────────────────────────────────────────────
    def _get_cache_path(self) -> str:
        return os.path.join(tempfile.gettempdir(), "temu_store_cache.json")

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

    def enrich_seller_info(self, items: list[dict],
                           progress_callback=None,
                           stop_event: threading.Event = None,
                           chunk_size: int = 15) -> list[dict]:
        """Adaptive Batch Resolver for Temu mall names with caching and jitter."""
        if not HAS_PLAYWRIGHT or not items:
            return items

        cache = self._load_cache()
        items_to_fetch = []

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
                if not current_seller or any(g in current_seller.lower() for g in ("global", "seller", "temu")):
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

            try:
                for fetch_idx, (orig_idx, it) in enumerate(items_to_fetch):
                    if stop_event and stop_event.is_set():
                        break

                    item_id = it.get("item_id")
                    url = it.get("url") or f"https://www.temu.com/goods.html?goods_id={item_id}"
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        time.sleep(1.5)
                    except Exception:
                        pass

                    mall_res = page.evaluate("""
                        () => {
                            // Strategy 1: Find container with 'Store joined Temu' or 'Follow'
                            const allDivs = Array.from(document.querySelectorAll('div, span, p'));
                            const storeNode = allDivs.find(el => el.children.length === 0 && (el.innerText || '').includes('Store joined Temu'));
                            
                            if (storeNode) {
                                let curr = storeNode.parentElement;
                                for (let i = 0; i < 7; i++) {
                                    if (curr && (curr.innerText.includes('Follow') || curr.innerText.includes('Chat') || curr.innerText.includes('Sold'))) {
                                        const linkEl = curr.querySelector('div[role="link"][aria-label], a[role="link"][aria-label]');
                                        if (linkEl) {
                                            const name = (linkEl.getAttribute('aria-label') || '').trim();
                                            if (name && !name.toLowerCase().includes('temu') && name.length < 50) {
                                                return { seller_name: name, store_id: '' };
                                            }
                                        }
                                        const directName = curr.querySelector('div[class*="_373T"], div[class*="StoreName"]');
                                        if (directName && directName.innerText.trim()) {
                                            return { seller_name: directName.innerText.trim(), store_id: '' };
                                        }
                                    }
                                    if (curr && curr.parentElement) {
                                        curr = curr.parentElement;
                                    }
                                }
                            }

                            // Strategy 2: Direct aria-label query near store indicators
                            const roleLinks = document.querySelectorAll('div[role="link"][aria-label]');
                            for (const rl of roleLinks) {
                                const lbl = (rl.getAttribute('aria-label') || '').trim();
                                if (lbl && lbl.length > 2 && lbl.length < 40 && !lbl.toLowerCase().includes('temu') && !lbl.toLowerCase().includes('cart') && !lbl.toLowerCase().includes('search')) {
                                    const parent = rl.closest('div');
                                    if (parent && (parent.innerText.includes('Follow') || parent.innerText.includes('Sold') || parent.innerText.includes('Store'))) {
                                        return { seller_name: lbl, store_id: '' };
                                    }
                                }
                            }

                            // Strategy 3: Standard mall/store link
                            const mallEl = document.querySelector('a[href*="/mall/"], span[class*="mall"], div[class*="mallName"]');
                            if (mallEl && mallEl.innerText.trim()) {
                                const m = (mallEl.getAttribute('href') || '').match(/\\/mall\\/([a-zA-Z0-9_\\-]+)/);
                                return {
                                    store_id: m ? m[1] : '',
                                    seller_name: mallEl.innerText.trim()
                                };
                            }

                            return { store_id: '', seller_name: '' };
                        }
                    """)

                    s_name = mall_res.get("seller_name")
                    s_id = mall_res.get("store_id")

                    if s_name:
                        it["seller"] = s_name
                        if s_id:
                            it["store_id"] = s_id
                        cache[item_id] = {"seller": s_name, "store_id": s_id}

                    if progress_callback:
                        progress_callback(orig_idx + 1, len(items), it)

                    time.sleep(random.uniform(1.5, 2.5))

            finally:
                try:
                    self._save_cache(cache)
                    browser_context.close()
                except Exception:
                    pass

        return items

    def launch_interactive_auth(self, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """Launch visible Edge browser session for user to dismiss Temu login/guest wall and save persistent profile."""
        with sync_playwright() as p:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                f"--window-position={window_pos[0]},{window_pos[1]}",
                f"--window-size={window_size[0]},{window_size[1]}",
                "--no-sandbox"
            ]
            context = self._launch_browser_context(p, launch_args, ua="", headless=False)
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)
            page.goto("https://www.temu.com", wait_until="domcontentloaded", timeout=60000)
            
            # Keep browser alive until user manually closes the window
            while True:
                try:
                    if not context.pages or all(pg.is_closed() for pg in context.pages):
                        break
                    time.sleep(1)
                except Exception:
                    break
            try:
                context.close()
            except Exception:
                pass
