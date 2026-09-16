import re
import os
import time
import random
import tempfile
import threading
import io
import urllib.request
import urllib.parse
from urllib.parse import urlencode, urlparse, parse_qs, quote
from typing import Optional, List, Dict, Union, Tuple
import concurrent.futures
from bs4 import BeautifulSoup
from PIL import Image

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


EBAY_LOCALES = [
    {"code": "US", "name": "United States", "domain": "ebay.com", "region": "North America", "flag": "🇺🇸"},
    {"code": "UK", "name": "United Kingdom", "domain": "ebay.co.uk", "region": "Europe", "flag": "🇬🇧"},
    {"code": "DE", "name": "Germany", "domain": "ebay.de", "region": "Europe", "flag": "🇩🇪"},
    {"code": "CA", "name": "Canada", "domain": "ebay.ca", "region": "North America", "flag": "🇨🇦"},
    {"code": "AU", "name": "Australia", "domain": "ebay.com.au", "region": "APAC", "flag": "🇦🇺"},
    {"code": "FR", "name": "France", "domain": "ebay.fr", "region": "Europe", "flag": "🇫🇷"},
    {"code": "IT", "name": "Italy", "domain": "ebay.it", "region": "Europe", "flag": "🇮🇹"},
    {"code": "ES", "name": "Spain", "domain": "ebay.es", "region": "Europe", "flag": "🇪🇸"},
    {"code": "NL", "name": "Netherlands", "domain": "ebay.nl", "region": "Europe", "flag": "🇳🇱"},
    {"code": "PL", "name": "Poland", "domain": "ebay.pl", "region": "Europe", "flag": "🇵🇱"},
    {"code": "CH", "name": "Switzerland", "domain": "ebay.ch", "region": "Europe", "flag": "🇨🇭"},
    {"code": "AT", "name": "Austria", "domain": "ebay.at", "region": "Europe", "flag": "🇦🇹"},
    {"code": "IE", "name": "Ireland", "domain": "ebay.ie", "region": "Europe", "flag": "🇮🇪"},
]

MAX_PAGES = 15
PAGE_SIZE = 60        # eBay standard items per page


class EbayScraper:
    def __init__(self, headless=False):
        """
        Scraper for eBay store and seller listings with anti-bot bypass and multi-locale support.
        """
        self.headless = headless
        self.last_scrape_warning = ""
        self.is_bot_challenge = False
        self.blocked_store_name = ""
        self.blocked_store_url = ""
        self.profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Apollo_eBay_Session"
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    def _find_edge_path(self):
        browser_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        ]
        return next((p for p in browser_paths if os.path.exists(p)), None)

    def _clean_ebay_domain(self, domain_str: str) -> str:
        """Resolve standard eBay domain string (e.g., 'ebay.co.uk') from country name, code, or URL."""
        if not domain_str:
            return "ebay.com"
        d = str(domain_str).strip().lower()
        if d in ("all", "auto", "reverse", "sweep") or "all locales" in d or "reverse sweep" in d:
            return "ebay.com"
        m = re.search(r'(?:https?://)?(?:www\.)?(ebay\.[a-z0-9.]+)', d)
        if m:
            return m.group(1).rstrip("/")
        for loc in EBAY_LOCALES:
            if loc["code"].lower() == d or loc["name"].lower() in d or loc["domain"] in d:
                return loc["domain"]
        clean = d.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        return clean if clean.startswith("ebay.") else "ebay.com"

    def probe_seller_active_locale(self, target_handle: str) -> Optional[str]:
        """
        Fast probe across major international eBay domains to find where an international seller
        is actively listing or has a registered store.
        Returns the domain string (e.g. 'ebay.co.uk', 'ebay.de') or None.
        """
        if not target_handle or target_handle.lower() in ("global", "marketplace", "all products", "catalog", "full search"):
            return None
        
        probe_domains = ["ebay.co.uk", "ebay.de", "ebay.ca", "ebay.com.au", "ebay.fr", "ebay.it", "ebay.es", "ebay.nl", "ebay.pl", "ebay.ch", "ebay.at", "ebay.ie"]
        clean_handle = target_handle.strip()
        
        for dom in probe_domains:
            try:
                test_url = f"https://www.{dom}/sch/i.html?_ssn={urllib.parse.quote(clean_handle)}&_ipg=25"
                html = self._fetch_via_requests(test_url)
                if html:
                    cards = self._parse_html(html, fallback_seller=clean_handle, domain=dom)
                    if cards:
                        return dom
                    if f"/str/{clean_handle.lower()}" in html.lower() or f"/usr/{clean_handle.lower()}" in html.lower():
                        return dom
            except Exception:
                pass
        return None

    def search_multi_locale(self, store_url: str, include_term: str,
                            exclude_terms: list[str] = None,
                            condition: str = "all",
                            locales: list[str] = None,
                            stop_event: threading.Event = None,
                            pause_event: threading.Event = None,
                            log_callback = None) -> list[dict]:
        """
        Cross-border multi-locale sweep across all specified or major eBay regional domains.
        """
        target_domains = locales or ["ebay.com", "ebay.co.uk", "ebay.de", "ebay.ca", "ebay.com.au", "ebay.fr", "ebay.it", "ebay.es", "ebay.nl", "ebay.pl"]
        all_items = []
        seen_ids = set()

        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass

        _log(f"🌍 [eBay Multi-Locale Sweep] Searching across {len(target_domains)} regional domains for '{include_term}'...")

        for dom in target_domains:
            if stop_event and stop_event.is_set():
                break
            if pause_event:
                pause_event.wait()

            clean_dom = self._clean_ebay_domain(dom)
            _log(f"🌍 [{clean_dom}] Scanning store/seller on {clean_dom}...")
            
            try:
                dom_items = self.search(
                    store_url,
                    include_term,
                    exclude_terms=exclude_terms,
                    condition=condition,
                    domain=clean_dom,
                    reverse_locale_probe=False,
                    stop_event=stop_event,
                    pause_event=pause_event,
                    log_callback=log_callback
                )
                new_in_dom = 0
                for it in dom_items:
                    iid = it.get("item_id")
                    dedup_key = iid if iid else it.get("url")
                    if dedup_key and dedup_key not in seen_ids:
                        seen_ids.add(dedup_key)
                        all_items.append(it)
                        new_in_dom += 1
                if new_in_dom > 0:
                    _log(f"  ✓ Found {new_in_dom} listings on {clean_dom}.")
            except Exception as e:
                _log(f"  ⚠ Error scanning {clean_dom}: {e}")

        return all_items

    def search(self, store_url: str, include_term: str,
               exclude_terms: list[str] = None,
               condition: str = "all",
               domain: str = "",
               reverse_locale_probe: bool = False,
               stop_event: threading.Event = None,
               pause_event: threading.Event = None,
               log_callback = None) -> list[dict]:
        """
        Search an eBay store/seller for include_term on a specific locale domain or with reverse locale auto-detection.
        Supports stop_event and pause_event for real-time user control.
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass

        # Check if full multi-locale sweep requested
        if domain and any(k in str(domain).lower() for k in ("all", "reverse", "sweep")):
            return self.search_multi_locale(
                store_url, include_term,
                exclude_terms=exclude_terms,
                condition=condition,
                stop_event=stop_event,
                pause_event=pause_event,
                log_callback=log_callback
            )

        self.is_bot_challenge = False
        self.blocked_store_name = ""
        self.blocked_store_url = ""
        store_info = self.resolve_store_info(store_url)
        
        # Override domain if explicitly passed, otherwise use domain detected from store URL
        active_dom = self._clean_ebay_domain(domain or store_info.get("domain", "ebay.com"))
        store_info["domain"] = active_dom

        exclude_terms = exclude_terms or []
        cleaned_excludes = self._sanitize_exclusions(include_term, exclude_terms)

        items = []
        seen_ids = set()

        if HAS_PLAYWRIGHT:
            try:
                items = self._search_via_playwright(
                    store_info, include_term, cleaned_excludes, condition, seen_ids,
                    domain=active_dom,
                    stop_event=stop_event, pause_event=pause_event
                )
                if items or (stop_event and stop_event.is_set()):
                    return items
            except Exception:
                pass

        # Fallback to requests search
        page = 1
        seller_label = store_info.get("store_name") or store_info.get("seller") or ""
        target_slug = store_info.get("seller") or store_info.get("store_name") or ""
        candidates = self._generate_seller_candidates(target_slug) if target_slug else [""]
        active_info = dict(store_info)

        # Try candidate handles on page 1
        for cand in candidates:
            if stop_event and stop_event.is_set():
                break
            if pause_event:
                pause_event.wait()

            cand_info = dict(store_info)
            if cand:
                if store_info.get("is_store") and not store_info.get("seller"):
                    cand_info["store_name"] = cand
                    cand_info["seller"] = ""
                else:
                    cand_info["seller"] = cand
                    cand_info["store_name"] = cand

            url = self._build_url(cand_info, include_term, cleaned_excludes, 1, condition, domain=active_dom)
            html = self._fetch_via_requests(url)
            if not html:
                continue
            page_items = self._parse_html(html, fallback_seller=cand or seller_label, domain=active_dom)
            if page_items:
                active_info = cand_info
                seller_label = cand or seller_label
                for item in page_items:
                    item_id = item.get("item_id")
                    dedup_key = item_id if item_id else item.get("url")
                    if dedup_key and dedup_key not in seen_ids:
                        seen_ids.add(dedup_key)
                        items.append(item)
                break

        if items:
            page = 2
            while page <= MAX_PAGES:
                if stop_event and stop_event.is_set():
                    break
                if pause_event:
                    pause_event.wait()

                url = self._build_url(active_info, include_term, cleaned_excludes, page, condition, domain=active_dom)
                html = self._fetch_via_requests(url)
                if not html:
                    break
                page_items = self._parse_html(html, fallback_seller=seller_label, domain=active_dom)
                if not page_items:
                    break

                new_found = 0
                for item in page_items:
                    item_id = item.get("item_id")
                    dedup_key = item_id if item_id else item.get("url")
                    if dedup_key and dedup_key not in seen_ids:
                        seen_ids.add(dedup_key)
                        items.append(item)
                        new_found += 1

                if new_found == 0 or len(page_items) < 10:
                    break
                page += 1
                time.sleep(random.uniform(1.0, 2.0))

        # Reverse Locale Auto-Detection fallback: If 0 results found on requested locale, probe international locales
        if not items and reverse_locale_probe and target_slug and target_slug.lower() not in ("global", "marketplace", "all products", "catalog", "full search"):
            _log(f"🔍 [Reverse Locale Probe] Checking international eBay locales for seller '{target_slug}'...")
            found_locale_dom = self.probe_seller_active_locale(target_slug)
            if found_locale_dom and found_locale_dom != active_dom:
                _log(f"🌍 [Reverse Locale Match] Seller '{target_slug}' found active on eBay {found_locale_dom}! Harvesting listings...")
                return self.search(
                    store_url,
                    include_term,
                    exclude_terms=exclude_terms,
                    condition=condition,
                    domain=found_locale_dom,
                    reverse_locale_probe=False,
                    stop_event=stop_event,
                    pause_event=pause_event,
                    log_callback=log_callback
                )

        return items

    def _get_user_data_dir(self) -> str:
        """Return dedicated persistent user data directory for Playwright."""
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "browser_session")
        os.makedirs(base, exist_ok=True)
        return base

    def open_interactive_solve_window(self, url: str, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """Launch a visible browser window using the persistent profile to let analyst solve CAPTCHA."""
        if not HAS_PLAYWRIGHT:
            import webbrowser
            webbrowser.open(url)
            return

        user_data_dir = self._get_user_data_dir()
        edge_path = self._find_edge_path()
        try:
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": False,
                    "viewport": {"width": window_size[0], "height": window_size[1]},
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        f"--window-position={window_pos[0]},{window_pos[1]}",
                        f"--window-size={window_size[0]},{window_size[1]}"
                    ]
                }
                if edge_path:
                    launch_kwargs["executable_path"] = edge_path
                else:
                    launch_kwargs["channel"] = "msedge"

                context = p.chromium.launch_persistent_context(user_data_dir, **launch_kwargs)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait for user to interact / solve challenge (up to 25 seconds or until closed)
                for _ in range(25):
                    if page.is_closed():
                        break
                    time.sleep(1)
                try:
                    context.close()
                except Exception:
                    pass
        except Exception:
            import webbrowser
            webbrowser.open(url)

    def _search_via_playwright(self, store_info: dict,
                               include_term: str, excludes: list[str],
                               condition: str, seen_ids: set,
                               domain: str = "ebay.com",
                               stop_event: threading.Event = None,
                               pause_event: threading.Event = None) -> list[dict]:
        """Search across pages using a single browser session with stop/pause support."""
        items = []
        seller_label = store_info.get("store_name") or store_info.get("seller") or ""
        active_dom = self._clean_ebay_domain(domain or store_info.get("domain", "ebay.com"))
        host = f"www.{active_dom}" if not active_dom.startswith("www.") and "cafr." not in active_dom else active_dom

        user_data_dir = self._get_user_data_dir()
        try:
            with sync_playwright() as p:
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
                ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
                edge_path = self._find_edge_path()
                launch_kwargs = {
                    "headless": self.headless,
                    "user_agent": ua,
                    "viewport": {"width": 1440, "height": 900},
                    "args": launch_args
                }
                if edge_path:
                    launch_kwargs["executable_path"] = edge_path
                else:
                    launch_kwargs["channel"] = "msedge"

                try:
                    context = p.chromium.launch_persistent_context(user_data_dir, **launch_kwargs)
                except Exception:
                    try:
                        launch_kwargs.pop("executable_path", None)
                        launch_kwargs["channel"] = "msedge"
                        context = p.chromium.launch_persistent_context(user_data_dir, **launch_kwargs)
                    except Exception:
                        launch_kwargs["channel"] = "chrome"
                        context = p.chromium.launch_persistent_context(user_data_dir, **launch_kwargs)

                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.navigator.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                """)

                page = context.pages[0] if context.pages else context.new_page()

                # Warm up session with authentic eBay cookies on active domain
                try:
                    page.goto(f"https://{host}", wait_until="domcontentloaded", timeout=12000)
                    time.sleep(0.6)
                except Exception:
                    pass

                # If item URL was passed, resolve the actual seller username from the listing
                if store_info.get("is_item") and store_info.get("item_id"):
                    item_id = store_info["item_id"]
                    try:
                        page.goto(f"https://{host}/itm/{item_id}", wait_until="domcontentloaded", timeout=15000)
                        time.sleep(0.8)
                        item_html = page.content()
                        resolved = ""
                        # Prioritize Store Link, then JSON sellerName, then /usr/ profile link
                        m_str = re.search(r"/str/([a-zA-Z0-9_.-]+)", item_html)
                        if m_str and not any(k in m_str.group(1).lower() for k in ("help", "about", "contact")):
                            resolved = m_str.group(1).strip()
                        else:
                            m_j = re.search(r'"sellerName":\s*"([a-zA-Z0-9_.-]+)"', item_html)
                            if m_j:
                                resolved = m_j.group(1).strip()
                            else:
                                m_usr = re.search(r"/usr/([a-zA-Z0-9_.-]+)", item_html)
                                resolved = m_usr.group(1).strip() if m_usr else ""

                        if resolved:
                            store_info["seller"] = resolved
                            store_info["store_name"] = resolved
                            seller_label = resolved
                    except Exception:
                        pass

                # If store URL was passed without a resolved seller username, resolve it directly in browser
                if store_info.get("is_store") and store_info.get("store_name") and not store_info.get("seller"):
                    try:
                        page.goto(f"https://{host}/str/{store_info['store_name']}", wait_until="domcontentloaded", timeout=15000)
                        time.sleep(0.8)
                        store_html = page.content()
                        m_ssn = re.search(r'"_ssn":\s*"([a-zA-Z0-9_.-]+)"', store_html)
                        m_seller = re.search(r'"(?:sellerId|ownerUsername|username)":\s*"([a-zA-Z0-9_.-]+)"', store_html)
                        m_usr = re.search(r'/usr/([a-zA-Z0-9_.-]+)', store_html)
                        resolved = ""
                        if m_ssn and not any(k in m_ssn.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                            resolved = m_ssn.group(1).strip()
                        elif m_seller and not any(k in m_seller.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                            resolved = m_seller.group(1).strip()
                        elif m_usr and not any(k in m_usr.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                            resolved = m_usr.group(1).strip()
                        if resolved:
                            store_info["seller"] = resolved
                            seller_label = resolved
                    except Exception:
                        pass

                target_slug = store_info.get("seller") or store_info.get("store_name") or ""
                candidates = self._generate_seller_candidates(target_slug) if target_slug else [""]
                active_info = dict(store_info)

                # Try candidate variations on Page 1 until a matching handle is found
                for cand in candidates:
                    if stop_event and stop_event.is_set():
                        break
                    if pause_event:
                        pause_event.wait()

                    cand_info = dict(store_info)
                    if cand:
                        if store_info.get("is_store") and not store_info.get("seller"):
                            cand_info["store_name"] = cand
                            cand_info["seller"] = ""
                        else:
                            cand_info["seller"] = cand
                            cand_info["store_name"] = cand

                    url = self._build_url(cand_info, include_term, excludes, 1, condition, domain=active_dom)
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        try:
                            page.wait_for_selector(".s-card, .s-item, .str-item-card, .srp-results, .srp-save-null-search", timeout=6000)
                        except Exception:
                            pass
                        time.sleep(0.6)
                        # Trigger lazy-loaded items (eBay virtualized stream)
                        for _ in range(2):
                            page.evaluate("window.scrollBy(0, 1200)")
                            time.sleep(0.2)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(0.4)
                        html = page.content()
                    except Exception:
                        try: html = page.content()
                        except Exception: html = ""
                        if not html:
                            continue

                    page_items = self._parse_html(html, fallback_seller=cand or seller_label, domain=active_dom)
                    if page_items:
                        active_info = cand_info
                        seller_label = cand or seller_label
                        for item in page_items:
                            item_id = item.get("item_id")
                            dedup_key = item_id if item_id else item.get("url")
                            if dedup_key and dedup_key not in seen_ids:
                                seen_ids.add(dedup_key)
                                items.append(item)
                        break

                # If items found on Page 1, paginate remaining pages with the confirmed handle
                if items:
                    page_num = 2
                    max_crawl_limit = MAX_PAGES if target_slug else 2
                    while page_num <= max_crawl_limit:
                        if stop_event and stop_event.is_set():
                            break
                        if pause_event:
                            pause_event.wait()

                        url = self._build_url(active_info, include_term, excludes, page_num, condition, domain=active_dom)
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=20000)
                            try:
                                page.wait_for_selector(".s-card, .s-item, .str-item-card, .srp-results, .srp-save-null-search", timeout=5000)
                            except Exception:
                                pass
                            time.sleep(0.6)
                            # Trigger lazy-loaded items for paginated pages
                            for _ in range(2):
                                page.evaluate("window.scrollBy(0, 1200)")
                                time.sleep(0.2)
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(0.4)
                            html = page.content()
                        except Exception:
                            try: html = page.content()
                            except Exception: html = ""
                            if not html:
                                break

                        page_items = self._parse_html(html, fallback_seller=seller_label, domain=active_dom)
                        if not page_items:
                            break

                        new_found = 0
                        for item in page_items:
                            item_id = item.get("item_id")
                            dedup_key = item_id if item_id else item.get("url")
                            if dedup_key and dedup_key not in seen_ids:
                                seen_ids.add(dedup_key)
                                items.append(item)
                                new_found += 1

                        if new_found == 0 or len(page_items) < 10:
                            break

                        page_num += 1
                        time.sleep(random.uniform(0.8, 1.5))

                if not items and html:
                    html_low = html.lower()
                    if any(t in html_low for t in ("pardon our interruption", "security measure", "please verify you are a human", "access denied")):
                        self.is_bot_challenge = True
                        self.blocked_store_name = seller_label
                        self.blocked_store_url = url
                        self.last_scrape_warning = f"⚠ [IP THROTTLE / BOT CHALLENGE] eBay returned a security rate-limit / CAPTCHA challenge on '{seller_label}' — zero results returned due to IP block, not empty inventory."
                    elif any(t in html_low for t in ("error page | ebay", "does not exist", "store not found", "seller not found", "we looked everywhere")):
                        self.last_scrape_warning = f"ℹ Store/Seller '{seller_label}' returned 0 results or store was not found on eBay ({active_dom})."
                    else:
                        self.last_scrape_warning = ""
                else:
                    self.last_scrape_warning = ""

                try:
                    context.close()
                except Exception:
                    pass
        finally:
            pass
        return items

    # ── Store / Seller Info Resolver ──────────────────────────────────────────
    def resolve_store_info(self, url: str) -> dict:
        """
        Extract store_name, seller username, domain, and store flag.
        Returns dict: {'store_name': str, 'seller': str, 'is_store': bool, 'domain': str}
        """
        info = {
            "store_name": "",
            "seller": "",
            "is_store": False,
            "domain": "ebay.com"
        }
        if not url:
            return info
            
        url_str = url.strip().rstrip("/")
        m_dom = re.search(r'(?:https?://)?(?:www\.)?(ebay\.[a-z0-9.]+)', url_str, re.IGNORECASE)
        if m_dom:
            info["domain"] = m_dom.group(1).lower()

        if any(g in url_str.lower() for g in ("global", "marketplace", "all products", "catalog", "full search")) or url_str.lower() in (
            "https://www.ebay.com", "http://www.ebay.com", "https://ebay.com", "http://ebay.com",
            "www.ebay.com", "ebay.com", "https://www.ebay.com/sch", "https://www.ebay.com/sch/i.html"
        ):
            return info

        # Check for query parameters first (e.g. pasted eBay search URL)
        if "?" in url_str:
            parsed = urlparse(url_str)
            qs = parse_qs(parsed.query)
            if "store_name" in qs:
                info["store_name"] = qs["store_name"][0].strip()
                info["is_store"] = True
            if "_ssn" in qs:
                info["seller"] = qs["_ssn"][0].strip()
            if info["store_name"] or info["seller"]:
                return info

        # Check for item URL pattern /itm/
        m_itm = re.search(r"/itm/(?:[^/]+/)?(\d+)", url_str)
        if m_itm:
            item_id = m_itm.group(1)
            info["item_id"] = item_id
            info["is_item"] = True
            info["is_store"] = True
            return info

        # Check for bare 12-digit eBay Item ID
        if url_str.isdigit() and len(url_str) >= 10:
            info["item_id"] = url_str
            info["is_item"] = True
            info["is_store"] = True
            return info

        # Check for store URL pattern /str/
        elif "/str/" in url_str.lower():
            part = url_str.lower().split("/str/")[-1]
            store_name = part.split("/")[0].split("?")[0].strip()
            info["store_name"] = store_name
            info["is_store"] = True

        # Check for user / seller URL pattern /usr/ or /seller/
        elif "/usr/" in url_str.lower() or "/seller/" in url_str.lower():
            for pattern in ["/usr/", "/seller/"]:
                if pattern in url_str.lower():
                    part = url_str.lower().split(pattern)[-1]
                    user_name = part.split("/")[0].split("?")[0].strip()
                    info["seller"] = user_name
                    info["is_store"] = False
                    break

        # Check /sch/username/m.html pattern
        elif re.search(r"/sch/([^/?&#]+)/m\.html", url_str, re.IGNORECASE):
            m = re.search(r"/sch/([^/?&#]+)/m\.html", url_str, re.IGNORECASE)
            info["seller"] = m.group(1).strip()
            info["is_store"] = False

        # Plain text input
        elif not url_str.startswith("http://") and not url_str.startswith("https://"):
            clean_name = url_str.split("/")[0].split("?")[0].strip()
            info["store_name"] = clean_name
            info["is_store"] = True
        else:
            # Check if root domain with no store path
            parsed = urlparse(url_str)
            path_segs = [p for p in parsed.path.split("/") if p]
            if not path_segs:
                info["store_name"] = ""
                info["seller"] = ""
                info["is_store"] = False
            else:
                last_seg = path_segs[-1].split("?")[0].strip()
                info["store_name"] = last_seg
                info["is_store"] = True

        # Automatic Store-to-Seller Bridge: Resolve underlying legal seller ID if store_name is present
        if info.get("store_name") and not info.get("seller"):
            s_name = info["store_name"].lower()
            if not hasattr(self, "_store_seller_cache"):
                self._store_seller_cache = {}
            if s_name in self._store_seller_cache:
                info["seller"] = self._store_seller_cache[s_name]
            else:
                try:
                    host = f"www.{info['domain']}" if not info['domain'].startswith("www.") and "cafr." not in info['domain'] else info['domain']
                    store_html = self._fetch_via_requests(f"https://{host}/str/{info['store_name']}")
                    if store_html:
                        m_ssn = re.search(r'"_ssn":\s*"([a-zA-Z0-9_.-]+)"', store_html)
                        m_seller = re.search(r'"(?:sellerId|ownerUsername|username)":\s*"([a-zA-Z0-9_.-]+)"', store_html)
                        m_usr = re.search(r'/usr/([a-zA-Z0-9_.-]+)', store_html)
                        
                        resolved_user = ""
                        if m_ssn and not any(k in m_ssn.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                            resolved_user = m_ssn.group(1).strip()
                        elif m_seller and not any(k in m_seller.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                            resolved_user = m_seller.group(1).strip()
                        elif m_usr and not any(k in m_usr.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                            resolved_user = m_usr.group(1).strip()
                            
                        if resolved_user:
                            self._store_seller_cache[s_name] = resolved_user
                            info["seller"] = resolved_user
                except Exception:
                    pass

        return info

    def _generate_seller_candidates(self, slug: str) -> list[str]:
        """Return the exact target handle without mangling underscores or hyphens."""
        if not slug:
            return [""]
        clean = slug.strip()
        return [clean]

    def resolve_seller(self, url: str) -> str:
        """Backwards compatibility for main.py."""
        if not url or any(g in url.lower() for g in ("global", "marketplace", "all products", "catalog", "full search")):
            return "eBay Global Search"
        info = self.resolve_store_info(url)
        return info.get("store_name") or info.get("seller") or "eBay Global Search"

    # ── Exclusion Sanitizer ───────────────────────────────────────────────────
    def _sanitize_exclusions(self, include_term: str, exclude_terms: list[str]) -> list[str]:
        """
        Ensure no exclusion term contradicts or cancels out the search term.
        """
        inc_lower = include_term.lower()
        inc_tokens = set(re.findall(r"\w+", inc_lower))

        safe_excludes = []
        for ex in exclude_terms:
            ex_clean = ex.strip().strip('"')
            if not ex_clean:
                continue
            ex_lower = ex_clean.lower()
            ex_tokens = set(re.findall(r"\w+", ex_lower))
            if ex_lower == inc_lower or (ex_tokens and ex_tokens.issubset(inc_tokens)):
                continue
            safe_excludes.append(ex_clean)

        return safe_excludes

    # ── URL Builder ───────────────────────────────────────────────────────────
    def _build_url(self, store_info: dict, include: str, excludes: list[str],
                   page: int, condition: str = "all", domain: str = "") -> str:
        """
        Build eBay search URL matching native store or seller search on specified or default locale domain.
        Handles multi-word exclusions properly by wrapping them in quotes (e.g. -"General Motors").
        """
        nkw_parts = []
        if include and include.strip():
            nkw_parts.append(include.strip())
        for ex in excludes:
            ex_str = ex.strip().strip('"')
            if ex_str:
                if " " in ex_str:
                    nkw_parts.append(f'-"{ex_str}"')
                else:
                    nkw_parts.append(f"-{ex_str}")
        nkw = " ".join(nkw_parts).strip()

        if isinstance(store_info, str):
            store_name = store_info
            seller = store_info
            target_dom = domain or "ebay.com"
        elif isinstance(store_info, dict):
            store_name = store_info.get("store_name", "")
            seller = store_info.get("seller", "")
            target_dom = domain or store_info.get("domain", "ebay.com")
        else:
            store_name = ""
            seller = ""
            target_dom = domain or "ebay.com"

        clean_dom = self._clean_ebay_domain(target_dom)
        host = f"www.{clean_dom}" if not clean_dom.startswith("www.") and "cafr." not in clean_dom else clean_dom

        params = {
            "_from": "R40",
            "_sacat": "0",
            "_ipg": PAGE_SIZE
        }

        target_handle = seller or store_name
        if target_handle:
            params["_ssn"] = target_handle
            if nkw:
                params["_nkw"] = nkw
            else:
                params["_armrs"] = "1"
        else:
            params["_nkw"] = nkw if nkw else ""

        if page > 1:
            params["_pgn"] = page

        if condition == "new":
            params["LH_ItemCondition"] = "1000"
        elif condition == "used":
            params["LH_ItemCondition"] = "3000"

        return f"https://{host}/sch/i.html?" + urlencode(params)

    def _fetch_via_requests(self, url: str) -> str:
        """Fallback fetch using session."""
        try:
            if HAS_CURL_CFFI:
                session = curl_requests.Session(impersonate="chrome124")
            else:
                session = curl_requests.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            resp = session.get(url, timeout=15)
            return resp.text if resp.status_code == 200 else ""
        except Exception:
            return ""

    def _parse_html(self, html: str, fallback_seller: str = "", include_term: str = "", domain: str = "ebay.com") -> list[dict]:
        """
        Parse listing items from modern .s-card, classic .s-item, and store layouts.
        Extracts robust high-resolution thumbnail URLs.
        Filters out rewritten/sponsored overflow items (e.g. 'Results matching fewer words').
        """
        soup = BeautifulSoup(html, "html.parser")
        items = []

        all_cards = soup.select(
            "li.s-card, li.s-item, div.s-item__wrapper, li.srp-results__item, .str-item-card, div.str-item-card__wrapper"
        )

        # Locate rewrite or recommendation divider if present on page
        rewrite_banner = soup.find(class_=re.compile(r'REWRITE_START|AUTO_CORRECT_START|s-item--section-title|srp-river-answer--REWRITE', re.I))
        if not rewrite_banner:
            for h in soup.find_all(["h2", "h3", "div", "span"], string=re.compile(r'results matching fewer words|more items related to|items matching your search keywords|explore more options', re.I)):
                rewrite_banner = h
                break

        for card in all_cards:
            # If this card comes AFTER an eBay recommendation / rewrite banner: HARD BREAK!
            if rewrite_banner and card in rewrite_banner.find_all_next():
                break

            card_text = card.get_text(" ", strip=True).lower()
            if any(k in card_text for k in ("results matching fewer words", "more items related to", "items matching your search keywords", "explore more options")):
                break

            if card.select_one(".s-item__placeholder") or card.select_one(".srp-river-answer"):
                continue
            if card.find_parent(class_=re.compile(r'carousel|sponsored|rewritten|recommendation', re.I)):
                continue

            # Check if item is located inside or after an eBay rewrite divider (e.g. 'Results matching fewer words')
            is_rewritten = False
            for prev in card.find_all_previous(class_=True, limit=8):
                classes = " ".join(prev.get("class", []))
                if any(k in classes for k in ("REWRITE_START", "AUTO_CORRECT_START", "SPONSORED_CONTAINER")):
                    is_rewritten = True
                    break
            if is_rewritten:
                break

            # 1. URL & Item ID
            link_el = (
                card.select_one('a[href*="/itm/"]') or
                card.select_one("a.s-item__link, a.s-card__link, a.str-item-card__link")
            )
            if not link_el or not link_el.get("href"):
                continue

            raw_url = link_el["href"]
            if not raw_url.startswith("http"):
                clean_dom = self._clean_ebay_domain(domain)
                host = f"www.{clean_dom}" if not clean_dom.startswith("www.") and "cafr." not in clean_dom else clean_dom
                raw_url = f"https://{host}{raw_url}"
            item_url = raw_url.split("?")[0]
            item_id = self._extract_item_id(raw_url)

            # 2. Title
            title_el = (
                card.select_one(".s-card__title") or
                card.select_one(".s-item__title") or
                card.select_one(".str-item-card__title") or
                card.select_one('[role="heading"]') or
                card.select_one("h3")
            )
            if title_el:
                for sub_el in title_el.select(".s-item__dynamic-subtitle, .s-card__subtitle, .s-item__subtitle, .s-item__title--tag"):
                    sub_el.decompose()
                title = title_el.get_text(strip=True)
            else:
                title = link_el.get_text(strip=True) if link_el else ""

            if not title or title.lower() == "shop on ebay":
                continue
            if "Opens in a new window or tab" in title:
                title = title.replace("Opens in a new window or tab", "").strip()
            if title.startswith("New Listing"):
                title = title.replace("New Listing", "", 1).strip()
            # Clean surgical eBay inline vehicle compatibility tags ONLY at the very end in parentheses
            title = re.sub(r'\s*\((?:For|Fits|Compatible with|Fits for):\s*[^)]+\)\s*$', '', title, flags=re.IGNORECASE).strip()

            # 3. Price
            price_el = (
                card.select_one(".s-card__price") or
                card.select_one(".s-item__price") or
                card.select_one(".str-item-card__price") or
                card.select_one(".text-display-2")
            )
            price = price_el.get_text(strip=True) if price_el else ""

            # 4. Thumbnail Image URL & Authoritative Title Extraction
            img_url = ""
            img_el = (
                card.select_one('img[src*="ebayimg.com"]') or
                card.select_one('img[data-src*="ebayimg.com"]') or
                card.select_one("img.s-card__image") or
                card.select_one("img.s-item__image-img") or
                card.select_one(".str-item-card__image img") or
                card.select_one("img")
            )
            if img_el:
                # If img_el has a clean, original seller title in alt, prefer it over eBay's modified card span
                alt_txt = (img_el.get("alt") or "").strip()
                if len(alt_txt) >= 8 and not alt_txt.lower().startswith(("opens in", "item", "product", "image", "thumbnail")):
                    if title.startswith(alt_txt) or "(for:" in title.lower() or "(fits:" in title.lower():
                        title = alt_txt

                candidates = [
                    img_el.get("data-src"),
                    img_el.get("data-lazy"),
                    img_el.get("src"),
                ]
                srcset = img_el.get("srcset", "")
                if srcset:
                    candidates.insert(0, srcset.split()[0].strip())
                for cand in candidates:
                    if cand and "ebayimg.com" in cand and not cand.endswith(".gif") and not cand.startswith("data:"):
                        img_url = cand
                        break
                if not img_url:
                    for cand in candidates:
                        if cand and not cand.startswith("data:") and not cand.endswith(".gif"):
                            img_url = cand
                            break

            # 5. Seller Extraction (URL-First Architecture)
            INVALID_SELLER_WORDS = {
                "new", "used", "pre-owned", "refurbished", "remanufactured", "returns", "delivery", "located", "sponsored", 
                "brand new", "buy it now", "opens in", "new listing", "save", "free", "seller", "top rated", 
                "top-rated", "open box", "parts only", "other", "watch", "authenticity", "guarantee", "feedback",
                "star", "stars", "seller info", "shop on ebay", "save this seller", "sold", "shipping", "free shipping",
                "free returns", "warranty", "watchers", "watcher", "viewed", "trending", "deals", "coupon", "discount",
                "compatibility", "compatible", "vehicle", "fitment", "details", "contact", "about", "united states",
                "bids", "bidding", "bid", "rating"
            }

            def _is_valid_seller_handle(cand_str: str) -> bool:
                if not cand_str:
                    return False
                c = cand_str.strip().strip("():;,")
                c_low = c.lower()
                if len(c) < 2 or len(c) > 40:
                    return False
                if c_low in INVALID_SELLER_WORDS or c_low in ("i.html", "m.html", "sch", "usr", "str", "itm", "ebay", "null", "undefined", "unknown", "ebay merchant"):
                    return False
                if c_low.endswith(".html") or c_low.endswith(".htm") or c_low.endswith(".php"):
                    return False
                if any(w in c_low for w in ("sold", "save up", "% off", "shipping", "returns", "sponsored", "brand:", "brand new", "was:", "now:", "watcher", "watchers", "bids", "feedback", "rating")):
                    return False
                if re.search(r'\b\d+\s*(?:sold|watchers?|bids?)\b', c_low) or re.match(r'^\d+[\d,.]*$', c_low):
                    return False
                return True

            # Rule 1: Store Sweeps — strictly use the store/seller handle from the target URL
            if fallback_seller and fallback_seller not in ("eBay Merchant", "Unknown", "", "Global Search"):
                seller = fallback_seller
            else:
                # Rule 2: General Searches — only accept direct /usr/ or /str/ profile links
                seller = ""
                for a in card.select("a[href*='/usr/'], a[href*='/str/']"):
                    href = a.get("href", "")
                    m_usr = re.search(r'/usr/([^/?&#]+)', href)
                    if m_usr and not any(k in m_usr.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                        cand_user = m_usr.group(1).strip()
                        if _is_valid_seller_handle(cand_user):
                            seller = cand_user
                            break
                    m_str = re.search(r'/str/([^/?&#]+)', href)
                    if m_str and not any(k in m_str.group(1).lower() for k in ("help", "about", "contact", "signin", "register")):
                        cand_str = m_str.group(1).strip()
                        if _is_valid_seller_handle(cand_str):
                            seller = cand_str
                            break

                # Check explicit seller container link
                if not seller:
                    seller_el = (
                        card.select_one(".s-item__seller-info-text") or
                        card.select_one(".s-item__seller-info") or
                        card.select_one(".s-card__seller-info") or
                        card.select_one(".str-seller-info")
                    )
                    if seller_el:
                        usr_a = seller_el.select_one("a[href*='/usr/'], a[href*='/str/']")
                        if usr_a:
                            href = usr_a.get("href", "")
                            m_u = re.search(r'/(?:usr|str)/([^/?&#]+)', href)
                            if m_u and not any(k in m_u.group(1).lower() for k in ("help", "about", "contact")):
                                cand_user = m_u.group(1).strip()
                                if _is_valid_seller_handle(cand_user):
                                    seller = cand_user

                if not seller or not _is_valid_seller_handle(seller):
                    seller = fallback_seller if (fallback_seller and _is_valid_seller_handle(fallback_seller)) else "eBay Merchant"

            # 6. Item Location / Origin
            loc_el = (
                card.select_one(".s-item__location") or
                card.select_one(".s-card__location") or
                card.select_one(".s-item__location--text") or
                card.select_one(".s-item__itemLocation") or
                card.select_one(".str-item-card__location") or
                card.select_one("span[class*='location']") or
                card.select_one(".s-item__detail--secondary")
            )
            item_location = loc_el.get_text(strip=True) if loc_el else ""
            if not item_location:
                for span in card.select("span, div.s-item__detail, div.s-card__detail"):
                    txt = span.get_text(strip=True)
                    if (txt.lower().startswith("from ") or "located in" in txt.lower()) and len(txt) < 50:
                        item_location = txt
                        break

            if item_location.lower().startswith("from "):
                item_location = item_location[5:].strip()
            elif "located in" in item_location.lower():
                item_location = item_location.split(":")[-1].strip()

            items.append({
                "title":       title,
                "url":         item_url,
                "item_id":     item_id,
                "price":       price,
                "image_url":   img_url,
                "seller":      seller if seller else fallback_seller,
                "location":    item_location,
                "marketplace": f"eBay ({domain})" if domain and domain != "ebay.com" else "eBay",
                "domain":      domain or "ebay.com"
            })

        return items

    def _extract_item_id(self, url: str) -> str:
        """Extract eBay 12-digit item ID from URL."""
        m = re.search(r"/itm/(?:[^/]+/)?(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"[?&]item=(\d+)", url)
        if m:
            return m.group(1)
        return ""

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

    def find_connected_network(self, item_id: str, item_url: str = "", target_img_url: str = "") -> list[dict]:
        """
        Scan eBay listing page carousels to discover competing / syndicate sellers.
        Performs perceptual image matching against target_img_url.
        """
        if not item_url and item_id:
            item_url = f"https://www.ebay.com/itm/{item_id}"
        if not item_id and item_url:
            item_id = self._extract_item_id(item_url)

        discovered = []
        seen_ids = set([str(item_id)] if item_id else [])

        target_hash = None
        if target_img_url and str(target_img_url).startswith("http"):
            try:
                req = urllib.request.Request(str(target_img_url), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                    target_hash = self.compute_dhash(t_img)
            except Exception:
                pass

        if not HAS_PLAYWRIGHT:
            return discovered

        edge_path = self._find_edge_path()
        launch_kwargs = {
            "headless": self.headless,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "viewport": {"width": 1440, "height": 900},
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            "ignore_default_args": ["--enable-automation"]
        }
        if edge_path:
            launch_kwargs["executable_path"] = edge_path
        else:
            launch_kwargs["channel"] = "msedge"

        temp_worker_dir = tempfile.mkdtemp(prefix="apollo_network_")
        try:
            with sync_playwright() as p:
                try:
                    context = p.chromium.launch_persistent_context(temp_worker_dir, **launch_kwargs)
                except Exception:
                    try:
                        launch_kwargs.pop("executable_path", None)
                        launch_kwargs["channel"] = "msedge"
                        context = p.chromium.launch_persistent_context(temp_worker_dir, **launch_kwargs)
                    except Exception:
                        launch_kwargs["channel"] = "chrome"
                        context = p.chromium.launch_persistent_context(temp_worker_dir, **launch_kwargs)

                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                try:
                    page.goto("https://www.ebay.com", wait_until="domcontentloaded", timeout=12000)
                    time.sleep(0.5)
                except Exception:
                    pass
                try:
                    page.goto(item_url, wait_until="domcontentloaded", timeout=20000)
                except Exception as e:
                    logger.debug(f"Initial goto notice for {item_url}: {e}")
                
                time.sleep(1.5)

                # Scroll in stages to trigger lazy-loaded carousels (Similar items, Explore related, Compare)
                for _ in range(5):
                    try:
                        page.evaluate("window.scrollBy(0, 800);")
                    except Exception:
                        pass
                    time.sleep(0.4)
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                except Exception:
                    pass
                time.sleep(0.6)

                # Auto-recover target image hash if not provided initially
                if not target_hash:
                    try:
                        target_img_src = page.evaluate("""() => {
                            const meta = document.querySelector('meta[property="og:image"]');
                            if (meta && meta.content) return meta.content;
                            const img = document.querySelector('#icImg, .ux-image-magnify img, .ux-image-filmstrip img, .filmstrip img, img[class*="picture"]');
                            return img ? (img.src || img.getAttribute('data-src') || '') : '';
                        }""")
                        if target_img_src and str(target_img_src).startswith("http"):
                            req = urllib.request.Request(str(target_img_src), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                            with urllib.request.urlopen(req, timeout=5) as r:
                                t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                                target_hash = self.compute_dhash(t_img)
                    except Exception:
                        pass

                raw_data = page.evaluate("""() => {
                    const res = [];
                    const seen = new Set();
                    document.querySelectorAll('a[href*="/itm/"]').forEach(a => {
                        const m = a.href.match(/\\/itm\\/(\\d+)/);
                        if (m && !seen.has(m[1])) {
                            seen.add(m[1]);
                            const card = a.closest('li, div[class*="item"], div[class*="card"], div[class*="merch"], div[class*="carousel"], div[class*="slider"]') || a.parentElement;
                            const imgEl = card ? card.querySelector('img') : a.querySelector('img');
                            const imgAlt = imgEl ? (imgEl.getAttribute('alt') || '').trim() : '';

                            let title = '';
                            if (imgAlt && imgAlt.length >= 8 && !imgAlt.toLowerCase().startsWith('opens in') && !imgAlt.toLowerCase().startsWith('item') && !imgAlt.toLowerCase().startsWith('image')) {
                                title = imgAlt;
                            } else if (a.innerText && a.innerText.trim().length > 5) {
                                title = a.innerText.trim();
                            } else if (a.getAttribute('title')) {
                                title = a.getAttribute('title').trim();
                            } else if (a.getAttribute('aria-label')) {
                                title = a.getAttribute('aria-label').trim();
                            } else if (card) {
                                const tEl = card.querySelector('h3, [class*="title"], [class*="desc"], [class*="text"], span');
                                if (tEl) title = tEl.innerText.trim();
                            }
                            if (title.startsWith("New Listing")) title = title.replace("New Listing", "").trim();
                            if (title.includes("Opens in a new window")) title = title.replace(/Opens in a new window.*/i, "").trim();
                            // Surgically strip ONLY parenthetical compatibility suffixes at the very end
                            title = title.replace(/\\s*\\((?:For|Fits|Fits for|Compatible with|Replacement for):\\s*[^)]+\\)\\s*$/i, '').trim();

                            if (!title) title = 'Discovered Listing ' + m[1];
                            
                            let img = '';
                            if (imgEl) {
                                img = imgEl.getAttribute('data-defer-src') || 
                                      imgEl.getAttribute('data-highres-src') || 
                                      imgEl.getAttribute('data-retina-src') || 
                                      imgEl.getAttribute('data-src') || 
                                      imgEl.getAttribute('data-lazy-src') || 
                                      imgEl.src || '';
                                if (img.includes(' ')) img = img.split(' ')[0];
                            }
                            
                            let price = '';
                            if (card) {
                                const pEl = card.querySelector('[class*="price"], [class*="Price"], span[class*="bold"]');
                                if (pEl) price = pEl.innerText.trim();
                            }
                            
                            let seller = '';
                            if (card) {
                                const sEl = card.querySelector('span[class*="seller"], a[href*="/usr/"], [class*="subtitle"]');
                                if (sEl) seller = sEl.innerText.trim();
                            }
                            
                            res.push({
                                id: m[1],
                                url: 'https://www.ebay.com/itm/' + m[1],
                                title: title,
                                img: img,
                                price: price,
                                seller: seller
                            });
                        }
                    });
                    return res;
                }""")

                # In-page parallel seller handle resolution for all discovered candidate IDs
                candidate_ids = list(dict.fromkeys([itm['id'] for itm in raw_data if itm.get('id') and itm['id'] not in seen_ids]))
                seller_map = {}
                if candidate_ids:
                    try:
                        seller_map = page.evaluate("""async (ids) => {
                            const out = {};
                            const batch = ids.slice(0, 40);
                            await Promise.all(batch.map(async (id) => {
                                try {
                                    const resp = await fetch('https://www.ebay.com/itm/' + id);
                                    const txt = await resp.text();
                                    
                                    // 1. Check JSON sellerName attribute
                                    const m_json = txt.match(/"sellerName":\\s*"([a-zA-Z0-9_.-]+)"/);
                                    if (m_json && !['help', 'about', 'contact', 'signin', 'register'].includes(m_json[1].toLowerCase())) {
                                        out[id] = m_json[1];
                                        return;
                                    }
                                    
                                    // 2. Check Seller Profile /usr/ Link
                                    const m_usr = txt.match(/\\/usr\\/([a-zA-Z0-9_.-]+)/);
                                    if (m_usr && !['help', 'about', 'contact', 'signin', 'register'].includes(m_usr[1].toLowerCase())) {
                                        out[id] = m_usr[1];
                                        return;
                                    }

                                    // 3. Check Store Link in Header
                                    const m_str = txt.match(/\\/str\\/([a-zA-Z0-9_.-]+)/);
                                    if (m_str && !m_str[1].includes('help') && !m_str[1].includes('about') && !m_str[1].includes('contact')) {
                                        out[id] = m_str[1];
                                        return;
                                    }
                                } catch(e) {}
                            }));
                            return out;
                        }""", candidate_ids)
                    except Exception:
                        pass

                for itm in raw_data:
                    iid = itm['id']
                    if iid in seen_ids:
                        continue
                    seen_ids.add(iid)

                    sim_label = "Related Listing"
                    dist_val = 99
                    if target_hash and itm['img'] and str(itm['img']).startswith("http"):
                        try:
                            img_hi = str(itm['img']).replace("s-l96.jpg", "s-l500.jpg").replace("s-l140.jpg", "s-l500.jpg").replace("s-l225.jpg", "s-l500.jpg")
                            req = urllib.request.Request(img_hi, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                            with urllib.request.urlopen(req, timeout=4) as r:
                                c_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                                c_hash = self.compute_dhash(c_img)
                                dist_val = self.hamming_distance(target_hash, c_hash)
                                if dist_val <= 4:
                                    sim_label = "🎯 Exact Photo Match (100%)"
                                elif dist_val <= 8:
                                    sim_label = "🔍 Near-Exact Photo (~90%)"
                                elif dist_val <= 14:
                                    sim_label = "🖼 High Visual Similarity (~75%)"
                                elif dist_val <= 20:
                                    sim_label = "📷 Similar Photo Theme"
                        except Exception:
                            pass

                    resolved_seller = seller_map.get(iid) or itm.get('seller', '')

                    discovered.append({
                        "item_id": iid,
                        "title": itm['title'],
                        "price": itm['price'],
                        "image_url": itm['img'],
                        "seller": resolved_seller,
                        "similarity": sim_label,
                        "distance": dist_val,
                        "url": f"https://www.ebay.com/itm/{iid}"
                    })
                try:
                    context.close()
                except Exception:
                    pass
        finally:
            try:
                shutil.rmtree(temp_worker_dir, ignore_errors=True)
            except Exception:
                pass

        # Sort: Exact photo matches first, then near-exact, then related
        discovered.sort(key=lambda x: x.get("distance", 99))
        return discovered

    def probe_item_locales(self, item_id: str, candidate_locales: list = None) -> list:
        """
        Probe sample item ID across international eBay locales using in-browser fetch.
        Returns list of active, verified locale objects.
        """
        if not item_id:
            return []
        if not candidate_locales:
            from main import EBAY_LOCALES
            candidate_locales = EBAY_LOCALES

        verified = []
        try:
            with sync_playwright() as p:
                edge_path = self._find_edge_path()
                context = p.chromium.launch_persistent_context(
                    self.profile_dir,
                    executable_path=edge_path if edge_path else None,
                    channel="msedge" if not edge_path else None,
                    headless=self.headless,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={"width": 1440, "height": 900},
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.pages[0] if context.pages else context.new_page()
                
                # Navigate to US item page first to establish session
                page.goto(f"https://www.ebay.com/itm/{item_id}", wait_until="domcontentloaded", timeout=15000)
                
                # In-browser parallel fetch across locales
                domain_list = [loc.get("domain") for loc in candidate_locales]
                results = page.evaluate("""async (domains, id) => {
                    const out = {};
                    await Promise.all(domains.map(async (dom) => {
                        try {
                            const u = (dom.startsWith('cafr') || dom.startsWith('befr') || dom.startsWith('benl')) 
                                ? 'https://' + dom + '/itm/' + id 
                                : 'https://www.' + dom + '/itm/' + id;
                            const resp = await fetch(u, { method: 'GET' });
                            const txt = await resp.text();
                            const is_dead = txt.includes('Page not found') || txt.includes('This listing was ended') || txt.includes('item is not available on this site');
                            out[dom] = (resp.status === 200 && !is_dead);
                        } catch(e) {
                            out[dom] = false;
                        }
                    }));
                    return out;
                }""", domain_list, item_id)
                
                for loc in candidate_locales:
                    dom = loc.get("domain")
                    if results.get(dom, False):
                        verified.append(loc)
                context.close()
        except Exception:
            # Fallback: if browser probe fails, return candidate locales as default
            verified = list(candidate_locales)

        return verified if verified else candidate_locales

    def resolve_seller_country(self, seller_handle: str) -> dict:
        """
        Extract seller registered country & member info from eBay feedback profile.
        Uses a 2-Tier Cascaded Resolution Engine:
          Tier 1: Direct Feedback Profile check (fastest).
          Tier 2: Storefront & User Bridge Fallback (resolves Store Name -> Underlying User ID).
        Returns dict: {"seller": seller_handle, "country": "China", "member_since": "Jul-04-26"}
        """
        if not seller_handle or seller_handle in ("Unknown", "Resolving..."):
            return {"seller": seller_handle, "country": "Unknown", "member_since": ""}

        clean = str(seller_handle).replace("🛡", "").replace("(Authorized)", "").strip()
        if "/str/" in clean or "/usr/" in clean:
            clean = clean.split("/str/")[-1].split("/usr/")[-1].split("?")[0].split("/")[0].strip()

        candidates = [clean, clean.replace("-", ""), clean.replace("_", "-"), clean.replace("-", "_")]
        candidates = list(dict.fromkeys(candidates))

        # ── Tier 1: Direct Feedback Profile Query ─────────────────────────────
        for cand in candidates:
            url = f"https://www.ebay.com/fdbk/feedback_profile/{cand}"
            try:
                if HAS_CURL_CFFI:
                    r = curl_requests.get(url, impersonate="chrome110", timeout=6)
                else:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    r = curl_requests.get(url, headers=headers, timeout=6)

                if r.status_code == 200 and len(r.text) > 1000 and "User ID you entered was not found" not in r.text:
                    m = re.search(r"Member since:[^<\n]*?\bin\s+([A-Za-z\s]+?)(?:<|\n|\t|&|$)", r.text, re.I)
                    if m:
                        country = m.group(1).strip()
                        m_date = re.search(r"Member since:\s*([A-Za-z0-9-]+)", r.text, re.I)
                        return {
                            "seller": clean,
                            "country": country,
                            "member_since": m_date.group(1).strip() if m_date else ""
                        }
                    m2 = re.search(r"(?:Based in|Located in)\s+([A-Za-z\s]+?)(?:<|\n|\t|&|$)", r.text, re.I)
                    if m2:
                        return {
                            "seller": clean,
                            "country": m2.group(1).strip(),
                            "member_since": ""
                        }
            except Exception:
                continue

        # ── Tier 2: Storefront & User Profile Bridge Fallback ──────────────────
        for cand in candidates:
            store_urls = [
                f"https://www.ebay.com/str/{cand}/about",
                f"https://www.ebay.com/str/{cand}",
                f"https://www.ebay.com/usr/{cand}"
            ]
            for s_url in store_urls:
                try:
                    if HAS_CURL_CFFI:
                        r_store = curl_requests.get(s_url, impersonate="chrome110", timeout=6)
                    else:
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                        r_store = curl_requests.get(s_url, headers=headers, timeout=6)

                    if r_store.status_code == 200 and len(r_store.text) > 1000:
                        # Check JSON country metadata in store page
                        m_cjson = re.search(r'"country":\s*"([A-Za-z\s]+?)"', r_store.text, re.I)
                        if m_cjson and m_cjson.group(1).strip().lower() not in ("the", "this", "our", "all", "unknown", "null"):
                            return {"seller": clean, "country": m_cjson.group(1).strip(), "member_since": ""}

                        # Check DOM location nodes
                        m_dom = re.search(r'(?:str-about-description__location|seller-location)[^>]*>([^<]+)<', r_store.text, re.I)
                        if m_dom and len(m_dom.group(1).strip()) >= 2:
                            return {"seller": clean, "country": m_dom.group(1).strip(), "member_since": ""}

                        # Check direct "Based in <Country>" or "Located in <Country>" on store/user page
                        m_based = re.search(r"(?:Based in|Located in|Registered in)\s+([A-Za-z\s]+?)(?:<|\n|\t|&|\.|,|$)", r_store.text, re.I)
                        if m_based and m_based.group(1).strip().lower() not in ("the", "this", "our", "all"):
                            c_name = m_based.group(1).strip()
                            return {
                                "seller": clean,
                                "country": c_name,
                                "member_since": ""
                            }

                        # Scan for underlying true User IDs
                        found_user_ids = []
                        for m_usr in re.finditer(r"/usr/([a-zA-Z0-9_.-]+)", r_store.text):
                            u = m_usr.group(1).strip()
                            if u.lower() not in (cand.lower(), "help", "about", "contact", "signin", "register"):
                                found_user_ids.append(u)
                        for m_json in re.finditer(r'"(?:sellerName|username|userId)":\s*"([a-zA-Z0-9_.-]+)"', r_store.text):
                            u = m_json.group(1).strip()
                            if u.lower() not in (cand.lower(), "help", "about", "contact"):
                                found_user_ids.append(u)

                        # Query feedback profile for discovered underlying User IDs
                        for true_id in list(dict.fromkeys(found_user_ids)):
                            if HAS_CURL_CFFI:
                                r_fdbk = curl_requests.get(f"https://www.ebay.com/fdbk/feedback_profile/{true_id}", impersonate="chrome110", timeout=6)
                            else:
                                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                                r_fdbk = curl_requests.get(f"https://www.ebay.com/fdbk/feedback_profile/{true_id}", headers=headers, timeout=6)

                            if r_fdbk.status_code == 200 and "User ID you entered was not found" not in r_fdbk.text:
                                m_f = re.search(r"Member since:[^<\n]*?\bin\s+([A-Za-z\s]+?)(?:<|\n|\t|&|$)", r_fdbk.text, re.I)
                                if m_f:
                                    m_d = re.search(r"Member since:\s*([A-Za-z0-9-]+)", r_fdbk.text, re.I)
                                    return {
                                        "seller": clean,
                                        "true_user_id": true_id,
                                        "country": m_f.group(1).strip(),
                                        "member_since": m_d.group(1).strip() if m_d else ""
                                    }
                except Exception:
                    continue

        return {"seller": clean, "country": "Unknown", "member_since": ""}

    def batch_resolve_seller_countries(self, seller_list: list) -> dict:
        """
        Resolve multiple sellers in parallel using ThreadPoolExecutor.
        Returns dict: {seller_handle: {"seller": str, "country": str, "member_since": str}}
        """
        if not seller_list:
            return {}
        unique_sellers = list(dict.fromkeys([s for s in seller_list if s and str(s) not in ("Unknown", "Resolving...")]))
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(unique_sellers) or 1)) as executor:
            future_to_seller = {executor.submit(self.resolve_seller_country, s): s for s in unique_sellers}
            for future in concurrent.futures.as_completed(future_to_seller):
                s = future_to_seller[future]
                try:
                    res = future.result()
                    results[s] = res
                except Exception:
                    results[s] = {"seller": s, "country": "Unknown", "member_since": ""}
        return results

    def enrich_ebay_seller_info(self, items: list, progress_callback=None, stop_event=None) -> list:
        """
        Enrich real seller usernames for eBay listings that were imported with generic or missing handles.
        Uses fast HTTP and Playwright fallback with instant store/seller deduplication caching.
        """
        import batch_importer
        total = len(items)
        seller_country_cache = {}
        store_cache = {}

        for i, item in enumerate(items):
            if stop_event and stop_event.is_set():
                break

            orig_seller = str(item.get("seller", "")).strip()
            store_id = str(item.get("store_id", "")).strip()
            store_url = str(item.get("store_url", "")).strip()

            # 1. Check if store / seller signature is already resolved in memory
            cached_seller_data = None
            if orig_seller and orig_seller not in ("eBay Seller", "Unknown", "Resolving...", "Global Search") and orig_seller in store_cache:
                cached_seller_data = store_cache[orig_seller]
            elif store_id and store_id in store_cache:
                cached_seller_data = store_cache[store_id]
            elif store_url and store_url in store_cache:
                cached_seller_data = store_cache[store_url]

            if cached_seller_data:
                item["seller"] = cached_seller_data.get("seller", item.get("seller"))
                if cached_seller_data.get("seller_origin") and not item.get("seller_origin"):
                    item["seller_origin"] = cached_seller_data["seller_origin"]
                if cached_seller_data.get("location") and not item.get("location"):
                    item["location"] = cached_seller_data["location"]
                if progress_callback:
                    progress_callback(i + 1, total, item)
                continue

            url = item.get("url", "")
            item_id = str(item.get("item_id", "")).strip()
            if not url and item_id:
                url = f"https://www.ebay.com/itm/{item_id}"
            if not url:
                if progress_callback:
                    progress_callback(i + 1, total, item)
                continue

            try:
                res = batch_importer._fetch_ebay_item(url, headless=self.headless)
                s = res.get("seller", "")
                if s and s != "eBay Seller":
                    item["seller"] = s
                    if s in seller_country_cache:
                        c_info = seller_country_cache[s]
                    else:
                        c_info = self.resolve_seller_country(s)
                        seller_country_cache[s] = c_info
                    if c_info and c_info.get("country") and c_info["country"] != "Unknown":
                        item["seller_origin"] = c_info["country"]

                    # Populate deduplication cache so all identical sellers resolve in 0ms
                    resolved_payload = {
                        "seller": s,
                        "seller_origin": item.get("seller_origin"),
                        "location": res.get("location") or item.get("location")
                    }
                    store_cache[s] = resolved_payload
                    if orig_seller and orig_seller not in ("eBay Seller", "Unknown", "Resolving...", "Global Search"):
                        store_cache[orig_seller] = resolved_payload
                    if store_id:
                        store_cache[store_id] = resolved_payload
                    if store_url:
                        store_cache[store_url] = resolved_payload

                if res.get("price") and item.get("price") in ("$0.00", "", None):
                    item["price"] = res["price"]
                if res.get("location") and not item.get("location"):
                    item["location"] = res["location"]
                if res.get("image_url") and not item.get("image_url"):
                    item["image_url"] = res["image_url"]
                if res.get("title") and (not item.get("title") or item.get("title").startswith("Imported Listing") or item.get("title").startswith("eBay Item #")):
                    item["title"] = res["title"]
                    if item.get("brand") in ("Unknown", "Automotive & Consumer Brands", "", None):
                        b = batch_importer.detect_brand(res["title"])
                        if b and b != "Automotive & Consumer Brands":
                            item["brand"] = b
                    if item.get("product_type") in ("Accessories", "", None):
                        pt = batch_importer.detect_product_type(res["title"])
                        if pt:
                            item["product_type"] = pt
            except Exception as e:
                logger.debug(f"Error enriching eBay item {item_id}: {e}")

            if progress_callback:
                progress_callback(i + 1, total, item)

        return items
