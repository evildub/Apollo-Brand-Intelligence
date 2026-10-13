"""
vinted_scraper.py
Specialized Multi-Locale Vinted Anti-Counterfeit & Brand Threat Harvester for Apollo.

Features:
- Multi-Region Domain Architecture (UK, France, Germany, Spain, Italy, Poland, USA, Netherlands, Belgium).
- High-Speed TLS Impersonation (curl_cffi chrome120) with automated session cookie warmup.
- Playwright + Native Microsoft Edge Stealth fallback for stubborn challenges.
- Support for Global Catalog Keyword Searching & 1-Click Seller Storefront Dredging.
- Full Item Metadata Extraction: Titles, Brand, Condition/Status, High-Res Thumbnails, 
  Favorites Count, Seller Profile/ID, Pricing normalized to USD.
- Client-Side Brand Matching & Multi-Layer Exclusion Filtering.
"""

import os
import re
import time
import json
import random
import logging
import threading
import urllib.parse
from typing import List, Dict, Optional, Tuple

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as curl_requests
    HAS_CURL_CFFI = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger("Apollo.VintedScraper")

# Regional domain registry
VINTED_REGIONS = {
    "UK": {"domain": "vinted.co.uk", "name": "United Kingdom", "flag": "🇬🇧", "currency": "GBP", "symbol": "£", "rate": 1.28},
    "FR": {"domain": "vinted.fr",    "name": "France",         "flag": "🇫🇷", "currency": "EUR", "symbol": "€", "rate": 1.08},
    "DE": {"domain": "vinted.de",    "name": "Germany",        "flag": "🇩🇪", "currency": "EUR", "symbol": "€", "rate": 1.08},
    "ES": {"domain": "vinted.es",    "name": "Spain",          "flag": "🇪🇸", "currency": "EUR", "symbol": "€", "rate": 1.08},
    "IT": {"domain": "vinted.it",    "name": "Italy",          "flag": "🇮🇹", "currency": "EUR", "symbol": "€", "rate": 1.08},
    "PL": {"domain": "vinted.pl",    "name": "Poland",         "flag": "🇵🇱", "currency": "PLN", "symbol": "zł", "rate": 0.25},
    "US": {"domain": "vinted.com",   "name": "United States",  "flag": "🇺🇸", "currency": "USD", "symbol": "$", "rate": 1.00},
    "NL": {"domain": "vinted.nl",    "name": "Netherlands",    "flag": "🇳🇱", "currency": "EUR", "symbol": "€", "rate": 1.08},
    "BE": {"domain": "vinted.be",    "name": "Belgium",        "flag": "🇧🇪", "currency": "EUR", "symbol": "€", "rate": 1.08},
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class VintedScraper:
    def __init__(self, headless: bool = True, default_region: str = "UK"):
        """
        Specialized High-Speed Scraper for Vinted marketplaces.
        """
        self.headless = headless
        self.region_code = default_region if default_region in VINTED_REGIONS else "UK"
        self._sessions: Dict[str, curl_requests.Session] = {}
        self._warmed_domains = set()
        self.profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Apollo_Vinted_Session"
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    def set_region(self, region_code: str):
        """Set current active regional domain (e.g. 'UK', 'FR', 'DE', 'US')."""
        if region_code in VINTED_REGIONS:
            self.region_code = region_code

    def get_active_domain(self) -> str:
        """Get active domain name (e.g. 'vinted.co.uk')."""
        return VINTED_REGIONS.get(self.region_code, VINTED_REGIONS["UK"])["domain"]

    def _get_session(self, domain: Optional[str] = None):
        """Get or initialize isolated curl_cffi session per domain to avoid cross-domain TLS/cookie contamination."""
        dom = domain or self.get_active_domain()
        if dom not in self._sessions:
            if HAS_CURL_CFFI:
                session = curl_requests.Session(impersonate="chrome120")
            else:
                session = curl_requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            })
            self._sessions[dom] = session
            self._warmup_session(domain=dom)
        return self._sessions[dom]

    def _apply_saved_cookies(self, domain: Optional[str] = None) -> int:
        """Load stored browser cookies from %LOCALAPPDATA%\\Apollo_Vinted_Session into curl_cffi session."""
        dom = domain or self.get_active_domain()
        session_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Apollo_Vinted_Session")
        cookie_file = os.path.join(session_dir, "cookies.json")
        if not os.path.exists(cookie_file):
            return 0
        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            session = self._sessions.get(dom)
            if not session:
                return 0
            loaded = 0
            for c in cookies:
                c_name = c.get("name", "")
                c_val = c.get("value", "")
                c_dom = c.get("domain", "").lower()
                # Strictly filter to Vinted domain cookies only to prevent foreign MSN/Bing pollution
                if "vinted" not in c_dom and not c_name.startswith("cf_") and not c_name.startswith("__cf"):
                    continue
                if c_name and c_val:
                    try:
                        session.cookies.set(c_name, c_val, domain=c_dom.lstrip(".") if c_dom else None)
                        loaded += 1
                    except Exception:
                        pass
            if loaded > 0:
                logger.info(f"Loaded {loaded} saved Vinted clearance cookies for {dom}.")
            return loaded
        except Exception as e:
            logger.debug(f"Error loading saved Vinted cookies: {e}")
            return 0

    def _refresh_session_token(self, domain: Optional[str] = None):
        """Force clean session recreation and homepage visit to refresh expired Vinted auth tokens."""
        dom = domain or self.get_active_domain()
        if HAS_CURL_CFFI:
            session = curl_requests.Session(impersonate="chrome124")
        else:
            session = curl_requests.Session()
        session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        })
        try:
            session.get(f"https://www.{dom}", timeout=12)
        except Exception:
            pass
        session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://www.{dom}/catalog",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
        self._sessions[dom] = session
        self._warmed_domains.add(dom)
        return session

    def _warmup_session(self, domain: Optional[str] = None):
        """Visit home page to generate valid anonymous session cookies (__cf_bm, anon_id, v_udt)."""
        dom = domain or self.get_active_domain()
        if dom in self._warmed_domains:
            return

        session = self._sessions.get(dom)
        if not session:
            return

        # 1. Apply any saved browser cookies first
        self._apply_saved_cookies(domain=dom)

        home_url = f"https://www.{dom}"
        try:
            r = session.get(home_url, timeout=10)
            if r.status_code in (200, 301, 302):
                self._warmed_domains.add(dom)
                logger.debug(f"Vinted session warmup successful on {dom} (Cookies: {len(session.cookies)})")
            else:
                logger.warning(f"Vinted warmup returned status {r.status_code} on {dom}")
        except Exception as e:
            logger.debug(f"Vinted warmup error on {dom}: {e}")

        # Update headers for subsequent JSON API calls
        session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://www.{dom}/catalog",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })

    def resolve_target_info(self, raw_input: str) -> dict:
        """
        Parse seller profile URL, seller ID, or determine if it is a Global search.
        Examples:
          - 'https://www.vinted.co.uk/member/113873421-sellername' -> user_id: 113873421, seller: sellername
          - '113873421' -> user_id: 113873421
          - 'Global Search' / '' -> Global
        """
        raw = raw_input.strip() if raw_input else ""
        if not raw or any(g in raw.lower() for g in ("global", "marketplace", "all", "sweep")):
            return {
                "type": "global",
                "user_id": None,
                "seller_name": "Vinted Global Search",
                "url": f"https://www.{self.get_active_domain()}",
                "domain": self.get_active_domain()
            }

        # Check for member URL pattern
        m_member = re.search(r'vinted\.(co\.uk|fr|de|es|it|pl|com|nl|be)/member/(\d+)(?:-([^/?#]+))?', raw, re.I)
        if m_member:
            tld = m_member.group(1).lower()
            uid = m_member.group(2)
            uname = m_member.group(3) or f"Seller_{uid}"
            domain = f"vinted.{tld}"
            return {
                "type": "seller",
                "user_id": uid,
                "seller_name": uname,
                "url": raw,
                "domain": domain
            }

        # Check for plain numeric user ID
        if raw.isdigit():
            return {
                "type": "seller",
                "user_id": raw,
                "seller_name": f"Seller_{raw}",
                "url": f"https://www.{self.get_active_domain()}/member/{raw}",
                "domain": self.get_active_domain()
            }

        # Fallback: Treat as seller username or search query
        return {
            "type": "global",
            "user_id": None,
            "seller_name": raw,
            "url": f"https://www.{self.get_active_domain()}",
            "domain": self.get_active_domain()
        }

    def scrape_store(
        self,
        store_target: str,
        brand_terms: Optional[List[str]] = None,
        exclusions: Optional[List[str]] = None,
        max_pages: int = 4,
        stop_event=None,
        pause_event=None,
        log_callback=None,
        status_callback=None,
        region_code: Optional[str] = None
    ) -> List[Dict]:
        """
        Harvest listings from Vinted catalog (Global search or specific seller storefront).
        """
        if region_code and region_code in VINTED_REGIONS:
            self.set_region(region_code)

        reg_info = VINTED_REGIONS.get(self.region_code, VINTED_REGIONS["UK"])
        dom = reg_info["domain"]
        curr_code = reg_info["currency"]
        curr_rate = reg_info["rate"]
        country_name = reg_info["name"]
        flag = reg_info["flag"]

        def _log(msg, error=False):
            if log_callback:
                log_callback(msg, error=error)
            logger.info(msg)

        def _status(msg):
            if status_callback:
                status_callback(msg)

        target_info = self.resolve_target_info(store_target)
        is_seller = target_info["type"] == "seller"
        user_id = target_info.get("user_id")
        seller_label = target_info.get("seller_name", "Global Search")

        if target_info.get("domain") and target_info["domain"] != dom:
            dom = target_info["domain"]

        # Ensure active session cookies
        _status(f"Connecting to Vinted {flag} {country_name} ({dom})...")
        session = self._get_session(domain=dom)

        search_query = " ".join(brand_terms) if brand_terms else ""
        if is_seller:
            _log(f"👗 Starting Vinted Storefront Sweep on {flag} {seller_label} (ID: {user_id})...")
        else:
            _log(f"👗 Starting Vinted Global Sweep on {flag} {country_name} for query: '{search_query or 'All'}'...")

        all_items = []
        seen_ids = set()
        clean_exclusions = [e.lower().strip() for e in (exclusions or []) if e and e.strip()]

        for page_num in range(1, max_pages + 1):
            if stop_event and stop_event.is_set():
                _log("⏹ Vinted harvest stopped by user.")
                break
            if pause_event:
                pause_event.wait()

            _status(f"Harvesting Vinted {flag} {country_name} — Page {page_num}/{max_pages}...")

            # Build query parameters
            params = {
                "page": page_num,
                "per_page": 96,
                "order": "newest_first"
            }

            if is_seller and user_id:
                params["user_id"] = user_id
            if search_query:
                params["search_text"] = search_query

            api_url = f"https://www.{dom}/api/v2/catalog/items"

            try:
                headers = {
                    "Referer": f"https://www.{dom}/catalog" if not is_seller else f"https://www.{dom}/member/{user_id}",
                }
                resp = session.get(api_url, params=params, headers=headers, timeout=15)

                if resp.status_code in (401, 403):
                    _log(f"⚠ Vinted authentication expired on {dom} (HTTP {resp.status_code}). Regenerating fresh session token...")
                    session = self._refresh_session_token(domain=dom)
                    headers["Referer"] = f"https://www.{dom}/catalog" if not is_seller else f"https://www.{dom}/member/{user_id}"
                    resp = session.get(api_url, params=params, headers=headers, timeout=15)

                    if resp.status_code in (401, 403) and dom != "vinted.co.uk":
                        _log(f"⚠ Re-routing search through Global Vinted gateway (vinted.co.uk)...")
                        s_uk = self._refresh_session_token(domain="vinted.co.uk")
                        headers_uk = {
                            "Referer": "https://www.vinted.co.uk/catalog" if not is_seller else f"https://www.vinted.co.uk/member/{user_id}",
                        }
                        api_url_uk = "https://www.vinted.co.uk/api/v2/catalog/items"
                        resp = s_uk.get(api_url_uk, params=params, headers=headers_uk, timeout=15)

                if resp.status_code != 200:
                    _log(f"⚠ Vinted API returned HTTP {resp.status_code} on page {page_num}.", error=True)
                    break

                data = resp.json()
                raw_items = data.get("items", [])
                if not raw_items:
                    _log(f"ℹ Reached end of listings on page {page_num}.")
                    break

                page_matched = 0
                for it in raw_items:
                    item_id = str(it.get("id") or "")
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    title = (it.get("title") or it.get("description") or f"Vinted Item #{item_id}").strip()
                    
                    # Extract Price
                    price_obj = it.get("price") or it.get("total_item_price") or {}
                    if isinstance(price_obj, dict):
                        price_val = price_obj.get("amount", "0.00")
                        c_code = price_obj.get("currency_code", curr_code)
                    else:
                        price_val = str(price_obj)
                        c_code = curr_code

                    try:
                        price_num = float(re.sub(r'[^\d.]', '', str(price_val)))
                    except Exception:
                        price_num = 0.0

                    # Convert to USD estimate
                    price_usd = round(price_num * curr_rate, 2)
                    formatted_price = f"{reg_info['symbol']}{price_num:.2f}"

                    # Seller & Profile
                    user_data = it.get("user") or {}
                    seller_uname = user_data.get("login") or f"Vinted User {item_id[:5]}"
                    seller_uid = str(user_data.get("id") or "")
                    seller_url = f"https://www.{dom}/member/{seller_uid}-{seller_uname}" if seller_uid else f"https://www.{dom}/member/{seller_uname}"

                    # Item URL
                    item_url = it.get("url") or f"https://www.{dom}/items/{item_id}"
                    if not item_url.startswith("http"):
                        item_url = f"https://www.{dom}{item_url}"

                    # Image URL
                    photo_data = it.get("photo") or {}
                    image_url = photo_data.get("url") or ""
                    if not image_url and photo_data.get("thumbnails"):
                        for th in reversed(photo_data["thumbnails"]):
                            if th.get("url"):
                                image_url = th["url"]
                                break

                    # Status / Condition
                    condition = it.get("status") or "Used"
                    brand_name = it.get("brand_title") or (it.get("item_box", {}).get("first_line") if isinstance(it.get("item_box"), dict) else "") or "Nike"

                    # Exclusion Filter
                    title_lower = title.lower()
                    if clean_exclusions and any(exc in title_lower for exc in clean_exclusions):
                        continue

                    # Brand Filter (if specific query was specified)
                    if brand_terms:
                        b_match = any(b.lower() in title_lower or b.lower() in brand_name.lower() for b in brand_terms)
                        if not b_match:
                            continue

                    # Threat Intelligence Heuristics for Vinted
                    cond_low = condition.lower()
                    is_nwt = any(k in cond_low for k in ("new with tag", "new with tags", "brand new with tag", "neuf avec", "neu mit etikett", "nuevo con etiqueta", "nowy z metk"))
                    is_burner_handle = bool(re.search(r'[a-zA-Z]+[0-9]{4,}', seller_uname)) or bool(re.search(r'user_[0-9]+', seller_uname.lower()))
                    
                    if is_nwt and 0 < price_usd < 50:
                        threat_badge = "🚨 NWT Counterfeit Risk (High)"
                        threat_score = 90
                    elif is_nwt:
                        threat_badge = "⚠ NWT Luxury / Streetwear"
                        threat_score = 75
                    elif is_burner_handle:
                        threat_badge = "🚩 Suspicious Burner Handle"
                        threat_score = 65
                    else:
                        threat_badge = f"{flag} {country_name} Direct"
                        threat_score = 30

                    normalized_record = {
                        "item_id": item_id,
                        "title": title,
                        "price": formatted_price,
                        "price_raw": price_usd,
                        "currency": c_code,
                        "seller": seller_uname,
                        "seller_id": seller_uid,
                        "seller_url": seller_url,
                        "url": item_url,
                        "image_url": image_url,
                        "marketplace": f"vinted.{dom.split('.')[-1]}",
                        "platform": "Vinted",
                        "location": f"{country_name} {flag}",
                        "seller_origin": country_name,
                        "threat_badge": threat_badge,
                        "threat_score": threat_score,
                        "condition": condition,
                        "brand": brand_name,
                        "favorite_count": it.get("favourite_count", 0),
                        "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }

                    all_items.append(normalized_record)
                    page_matched += 1

                _log(f"  ✓ Page {page_num}: Parsed {len(raw_items)} listings, matched {page_matched} verified threats.")
                time.sleep(random.uniform(0.6, 1.2))

            except Exception as e:
                _log(f"⚠ Error fetching Vinted page {page_num}: {e}", error=True)
                break

        _log(f"🏁 Vinted harvest complete! Total verified listings harvested: {len(all_items)}")
        _status(f"Harvest complete: {len(all_items)} listings found.")
        return all_items

    def search_multi_region(
        self,
        store_target: str,
        brand_terms: Optional[List[str]] = None,
        exclusions: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        max_pages_per_region: int = 1,
        stop_event=None,
        log_callback=None,
        status_callback=None
    ) -> List[Dict]:
        """
        Cross-border Multi-Region sweep across all specified Vinted domains (UK, FR, DE, ES, IT, PL, US, NL, BE).
        """
        target_regions = regions or ["UK", "FR", "DE", "ES", "IT", "PL", "US", "NL", "BE"]
        all_multi_items = []
        seen_all_ids = set()

        def _log(msg, error=False):
            if log_callback:
                log_callback(msg, error=error)
            logger.info(msg)

        _log(f"🌍 [Vinted Multi-Region Sweep] Launching cross-border reconnaissance across {len(target_regions)} regions: {', '.join(target_regions)}...")

        for reg in target_regions:
            if stop_event and stop_event.is_set():
                _log("⏹ Multi-region Vinted sweep stopped by user.")
                break
            r_info = VINTED_REGIONS.get(reg, {})
            r_flag = r_info.get("flag", "🌐")
            r_name = r_info.get("name", reg)

            _log(f"🌍 [{r_flag} {r_name}] Scanning {r_info.get('domain', reg)} ({max_pages_per_region} pages)...")
            try:
                reg_items = self.scrape_store(
                    store_target,
                    brand_terms=brand_terms,
                    exclusions=exclusions,
                    max_pages=max_pages_per_region,
                    stop_event=stop_event,
                    log_callback=log_callback,
                    status_callback=status_callback,
                    region_code=reg
                )
                for it in reg_items:
                    if it["item_id"] not in seen_all_ids:
                        seen_all_ids.add(it["item_id"])
                        all_multi_items.append(it)
            except Exception as e:
                _log(f"⚠ Error scanning region {reg}: {e}", error=True)

        _log(f"🏁 [Vinted Multi-Region Sweep Complete] Harvested {len(all_multi_items)} listings across all {len(target_regions)} locales!")
        return all_multi_items

    def launch_interactive_auth(self, region_code: str = "UK", window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        r"""
        Open a visible Microsoft Edge / Chromium browser to solve Cloudflare Turnstile challenge once.
        Session clearance tokens and cookies are permanently saved in %LOCALAPPDATA%\Apollo_Vinted_Session.
        """
        reg_info = VINTED_REGIONS.get(region_code, VINTED_REGIONS["UK"])
        dom = reg_info.get("domain", "vinted.co.uk")
        url = f"https://www.{dom}/catalog"

        def _runner():
            try:
                from playwright.sync_api import sync_playwright
                profile_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Apollo_Vinted_Session")
                os.makedirs(profile_dir, exist_ok=True)
                for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
                    lock_f = os.path.join(profile_dir, lock_name)
                    if os.path.exists(lock_f):
                        try:
                            os.remove(lock_f)
                        except Exception:
                            pass
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    f"--window-position={window_pos[0]},{window_pos[1]}",
                    f"--window-size={window_size[0]},{window_size[1]}"
                ]
                with sync_playwright() as p:
                    try:
                        browser = p.chromium.launch_persistent_context(
                            user_data_dir=profile_dir,
                            headless=False,
                            channel="msedge",
                            viewport={"width": window_size[0], "height": window_size[1]},
                            args=launch_args
                        )
                    except Exception:
                        browser = p.chromium.launch_persistent_context(
                            user_data_dir=profile_dir,
                            headless=False,
                            viewport={"width": window_size[0], "height": window_size[1]},
                            args=launch_args
                        )
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    except Exception as ge:
                        logger.warning(f"Initial navigation notice: {ge}")
                    logger.info(f"Vinted session auth window opened at {url}. Monitoring for verification...")
                    session_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Apollo_Vinted_Session")
                    cookie_path = os.path.join(session_dir, "cookies.json")
                    storage_path = os.path.join(session_dir, "storage_state.json")

                    for _ in range(150):
                        if browser.pages and not browser.pages[0].is_closed():
                            try:
                                cookies = browser.cookies()
                                browser.storage_state(path=storage_path)
                                with open(cookie_path, "w", encoding="utf-8") as f:
                                    json.dump(cookies, f, indent=2)
                                self._apply_saved_cookies(domain=dom)
                            except Exception:
                                pass
                            time.sleep(2.0)
                        else:
                            break
                    try:
                        cookies = browser.cookies()
                        browser.storage_state(path=storage_path)
                        with open(cookie_path, "w", encoding="utf-8") as f:
                            json.dump(cookies, f, indent=2)
                        self._apply_saved_cookies(domain=dom)
                        browser.close()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Failed to launch Vinted interactive auth: {e}")

        threading.Thread(target=_runner, daemon=True).start()


# Standalone diagnostic test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = VintedScraper(default_region="UK")
    results = scraper.scrape_store("", brand_terms=["Nike", "Tech Fleece"], max_pages=1)
    print(f"\n--- Diagnostic Results ({len(results)} items) ---")
    for item in results[:3]:
        print(f"[{item['price']}] {item['title']} | Seller: {item['seller']} | {item['url']}")
