import os
import re
import time
import random
import json
import logging
import threading
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("Apollo.ManoMano")

LOCALES = {
    "France": {"domain": "www.manomano.fr", "search_slug": "/recherche/", "default_origin": "France"},
    "Spain": {"domain": "www.manomano.es", "search_slug": "/busqueda/", "default_origin": "Spain"},
    "Germany": {"domain": "www.manomano.de", "search_slug": "/suche/", "default_origin": "Germany"},
    "Italy": {"domain": "www.manomano.it", "search_slug": "/ricerca/", "default_origin": "Italy"},
    "United Kingdom": {"domain": "www.manomano.co.uk", "search_slug": "/search/", "default_origin": "United Kingdom"}
}

# --------------------------------------------------------------------------
# A bet was struck upon a whiskey night,
# The AI boasted all was working right!
# But Jerry found a Frenchman selling gears
# Upon the German storefront, it appears.
# "Sitz in, Frankreich!" the German portal cried,
# The language map had stumbled and had lied!
# So here in rhyme we pay our humble toll:
# Map every tongue across Europa's soul!
# --------------------------------------------------------------------------
COUNTRY_MAP = {
    # Germany
    "allemagne": "Germany",
    "germany": "Germany",
    "deutschland": "Germany",
    "alemania": "Germany",
    "germania": "Germany",
    # France
    "france": "France",
    "frankreich": "France",
    "francia": "France",
    # Spain
    "espagne": "Spain",
    "spain": "Spain",
    "españa": "Spain",
    "espana": "Spain",
    "spanien": "Spain",
    "spagna": "Spain",
    # Italy
    "italie": "Italy",
    "italy": "Italy",
    "italia": "Italy",
    "italien": "Italy",
    # United Kingdom
    "royaume-uni": "United Kingdom",
    "united kingdom": "United Kingdom",
    "grossbritannien": "United Kingdom",
    "großbritannien": "United Kingdom",
    "regno unito": "United Kingdom",
    "reino unido": "United Kingdom",
    # China
    "chine": "China",
    "china": "China",
    # Netherlands & Belgium & Poland
    "pays-bas": "Netherlands",
    "netherlands": "Netherlands",
    "niederlande": "Netherlands",
    "paesi bassi": "Netherlands",
    "países bajos": "Netherlands",
    "belgique": "Belgium",
    "belgium": "Belgium",
    "belgien": "Belgium",
    "bélgica": "Belgium",
    "belgio": "Belgium",
    "pologne": "Poland",
    "poland": "Poland",
    "polen": "Poland",
    "polonia": "Poland"
}


class ManoManoScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.session_dir = os.path.join(appdata, "Apollo", "manomano_session")
        os.makedirs(self.session_dir, exist_ok=True)
        self.merchant_cache = {}
        self.domain_cookies = {}
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    def _sync_cookies_from_browser(self, warm_domain: Optional[str] = None):
        """Extract valid cookies for all ManoMano domains from persistent Playwright session."""
        try:
            with sync_playwright() as p:
                args = ["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check"]
                context = p.chromium.launch_persistent_context(
                    self.session_dir,
                    headless=True,
                    channel="msedge",
                    args=args
                )
                if warm_domain:
                    page = context.pages[0] if context.pages else context.new_page()
                    try:
                        page.goto(f"https://{warm_domain}", timeout=8000)
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass
                for loc_data in LOCALES.values():
                    d = loc_data["domain"]
                    raw_cookies = context.cookies(f"https://{d}")
                    self.domain_cookies[d] = {c["name"]: c["value"] for c in raw_cookies}
                context.close()
        except Exception as e:
            logger.debug(f"Cookie sync error: {e}")

    def launch_interactive_auth(self, locale_key: str = "All", window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """Launch visible Edge to clear Cloudflare Turnstile across European domains."""
        try:
            with sync_playwright() as p:
                args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                    f"--window-position={window_pos[0]},{window_pos[1]}",
                    f"--window-size={window_size[0]},{window_size[1]}"
                ]
                context = p.chromium.launch_persistent_context(
                    self.session_dir,
                    headless=False,
                    channel="msedge",
                    viewport={"width": window_size[0], "height": window_size[1]},
                    args=args
                )
                page = context.pages[0] if context.pages else context.new_page()

                target_locales = list(LOCALES.values()) if ("all" in locale_key.lower() or "europe" in locale_key.lower()) else [LOCALES.get(locale_key, LOCALES["France"])]

                for loc_data in target_locales:
                    d = loc_data["domain"]
                    page.goto(f"https://{d}")
                    for _ in range(10):
                        time.sleep(1)
                        try:
                            if not page.is_visible("body") or "just a moment" not in page.title().lower():
                                time.sleep(1.5)
                                break
                        except Exception:
                            break
                    raw_cookies = context.cookies(f"https://{d}")
                    self.domain_cookies[d] = {c["name"]: c["value"] for c in raw_cookies}

                try:
                    context.close()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Interactive ManoMano session: {e}")

    def search(self,
               store_raw: str,
               include_term: str,
               excludes: list = None,
               condition: str = "all",
               max_pages: int = 4,
               locale_key: str = "France",
               stop_event: threading.Event = None,
               pause_event: threading.Event = None) -> list:
        """
        Search ManoMano for target term, crawling multiple pages and enriching PDP + merchant info concurrently.
        Supports single locale or 'All European Locales'.
        """
        excludes = excludes or []
        if not self.domain_cookies:
            self._sync_cookies_from_browser()

        if "all" in locale_key.lower() or "europe" in locale_key.lower():
            target_keys = ["France", "Spain", "Germany", "Italy", "United Kingdom"]
        else:
            clean_k = "France"
            for k in LOCALES.keys():
                if k.lower() in locale_key.lower():
                    clean_k = k
                    break
            target_keys = [clean_k]

        all_raw_items = []
        seen_ids = set()
        clean_term = include_term.strip()

        for key in target_keys:
            if stop_event and stop_event.is_set():
                break
            loc = LOCALES[key]
            domain = loc["domain"]
            slug = loc["search_slug"]
            default_country = loc["default_origin"]
            cookies = self.domain_cookies.get(domain, {})

            headers = {
                "User-Agent": self.user_agent,
                "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
                "Referer": f"https://{domain}/"
            }

            for page_num in range(1, max_pages + 1):
                if stop_event and stop_event.is_set():
                    break
                if pause_event:
                    pause_event.wait()

                search_url = f"https://{domain}{slug}{clean_term.replace(' ', '+')}?page={page_num}"
                try:
                    r = requests.get(search_url, cookies=cookies, headers=headers, impersonate="chrome124", timeout=12)
                    if r.status_code == 403 or "just a moment" in r.text.lower():
                        self._sync_cookies_from_browser(warm_domain=domain)
                        cookies = self.domain_cookies.get(domain, {})
                        r = requests.get(search_url, cookies=cookies, headers=headers, impersonate="chrome124", timeout=12)
                        if r.status_code != 200:
                            break

                    soup = BeautifulSoup(r.text, "html.parser")
                    page_found = 0
                    for a in soup.find_all("a", href=re.compile(r"/p/")):
                        href = a.get("href", "")
                        if "recherche" in href or "search" in href or "busqueda" in href or "suche" in href or "ricerca" in href:
                            continue
                        title = a.get_text(" ", strip=True)
                        if len(title) > 8 and not title.startswith("Page"):
                            # 1. Search Relevance Guard: eliminate drill bits, rulers, door mats
                            if clean_term and clean_term != "*":
                                term_words = [w.lower() for w in clean_term.split() if len(w) > 2]
                                if term_words and not any(w in title.lower() for w in term_words):
                                    continue

                            m_id = re.search(r"-(\d+)$", href.split("?")[0])
                            item_id = m_id.group(1) if m_id else ""
                            dedup_key = f"{domain}_{item_id}" if item_id else href
                            if dedup_key in seen_ids:
                                continue
                            seen_ids.add(dedup_key)

                            # 2. Extract Immediate Card Thumbnail from Search Results
                            card_img = ""
                            img_tag = a.find("img")
                            if not img_tag and a.parent:
                                img_tag = a.parent.find("img")
                            if not img_tag and a.parent and a.parent.parent:
                                img_tag = a.parent.parent.find("img")
                            if img_tag:
                                card_img = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("srcset", "").split(" ")[0]

                            # 3. Extract Immediate Card Price from Search Results
                            card_price = ""
                            curr = a
                            for _ in range(5):
                                if curr.parent:
                                    curr = curr.parent
                                    pm = re.search(r'([£€$]\s*\d+[\.,]\d{2}|\d+[\.,]\d{2}\s*[£€$])', curr.get_text(" ", strip=True))
                                    if pm:
                                        card_price = pm.group(0).strip()
                                        break

                            full_url = f"https://{domain}{href}" if href.startswith("/") else href
                            all_raw_items.append({
                                "item_id": item_id,
                                "title": title,
                                "url": full_url,
                                "domain": domain,
                                "marketplace": domain,
                                "locale_name": key,
                                "price": card_price,
                                "image_url": card_img,
                                "seller": "",
                                "seller_origin": default_country,
                                "location": default_country,
                                "threat_badge": "",
                                "threat_score": 10,
                                "brand": clean_term.title(),
                                "product_type": "Hardware / Pet / Home"
                            })
                            page_found += 1

                    if page_found == 0:
                        break
                    time.sleep(0.3)
                except Exception as e:
                    logger.debug(f"ManoMano {key} page {page_num} error: {e}")
                    break

        if not all_raw_items:
            return []

        # 2. Enrich PDP & Merchant in Parallel
        def _enrich(item):
            if stop_event and stop_event.is_set():
                return item
            domain = item.get("domain", "www.manomano.fr")
            default_country = LOCALES.get(item.get("locale_name"), LOCALES["France"])["default_origin"]
            cookies = self.domain_cookies.get(domain, {})
            headers = {
                "User-Agent": self.user_agent,
                "Referer": f"https://{domain}/"
            }
            try:
                rp = requests.get(item["url"], cookies=cookies, headers=headers, impersonate="chrome124", timeout=10)
                if rp.status_code == 200:
                    p_soup = BeautifulSoup(rp.text, "html.parser")
                    # 1. Multi-Currency Price (£, €, $)
                    pm = re.search(r'([£€$]\s*\d+[\.,]\d{2}|\d+[\.,]\d{2}\s*[£€$])', rp.text)
                    if pm:
                        item["price"] = pm.group(0).strip()
                    # 2. High-res Image
                    og_img = p_soup.select_one('meta[property="og:image"]')
                    if og_img and og_img.get("content"):
                        item["image_url"] = og_img["content"]

                    # 3. Merchant URL resolution across all European locales (FR, UK, ES, DE, IT)
                    mm = re.search(r'/((?:marchand|seller|haendler|verkaeufer|vendedor|venditore|merchant)-\d+)', rp.text)
                    if mm:
                        m_slug = mm.group(1)
                        cache_key = f"{domain}_{m_slug}"
                        if cache_key in self.merchant_cache:
                            s_name, loc = self.merchant_cache[cache_key]
                            item["seller"] = s_name
                            item["seller_origin"] = loc
                            item["location"] = default_country
                        else:
                            rm = requests.get(f"https://{domain}/{m_slug}", cookies=cookies, headers=headers, impersonate="chrome124", timeout=10)
                            if rm.status_code == 200:
                                m_title = re.search(r'<title[^>]*>(.*?)</title>', rm.text)
                                s_name = m_title.group(1).strip() if m_title else m_slug

                                # Extract physical location across languages (FR, EN, DE, ES, IT)
                                loc_match = re.search(r'(?:situ[ée]s?\s+[àa]|located\s+in|situierten?\s+in|ubicad[oa]s?\s+en|situate?\s+a|sitz\s+in|sede\s+in|sede\s+en|ans[aä]ssig\s+in)\s*,\s*([^\n<]+)', rm.text, re.I)
                                raw_country = loc_match.group(1).split("Parole")[0].split(".")[0].strip() if loc_match else default_country
                                clean_c = COUNTRY_MAP.get(raw_country.lower().strip(), raw_country.title())

                                self.merchant_cache[cache_key] = (s_name, clean_c)
                                item["seller"] = s_name
                                item["seller_origin"] = clean_c
                                item["location"] = default_country
                    else:
                        # Check if first-party retail (sold and shipped directly by ManoMano)
                        if re.search(r'(?:vendu par|sold by|verkauft von|vendido por|venduto da)\s+manomano', rp.text, re.I):
                            item["seller"] = "ManoMano (Direct)"
                            item["seller_origin"] = default_country
                            item["location"] = default_country

                    # Threat Badge: compare True Corporate Origin with Marketplace Country
                    country = item.get("seller_origin", default_country)
                    if country == "China":
                        item["threat_badge"] = f"🇨🇳 Cross-Border Direct (China ➔ {default_country})"
                        item["threat_score"] = 85
                    elif country != default_country:
                        item["threat_badge"] = f"🇪🇺 Cross-Border ({country} ➔ {default_country})"
                        item["threat_score"] = 45
                    else:
                        item["threat_badge"] = f"✅ Domestic ({default_country})"
                        item["threat_score"] = 15
            except Exception as e:
                logger.debug(f"Error enriching ManoMano item {item.get('item_id')}: {e}")
            time.sleep(random.uniform(0.2, 0.35))
            return item

        with ThreadPoolExecutor(max_workers=3) as executor:
            enriched_items = list(executor.map(_enrich, all_raw_items))

        return enriched_items

    def resolve_store_info(self, raw_input: str) -> dict:
        raw = raw_input.strip() if raw_input else ""
        return {
            "store_name": "ManoMano European Search",
            "seller": "",
            "is_store": False,
            "domain": "manomano.fr",
            "url": raw if raw.startswith("http") else f"https://www.manomano.fr/recherche/{raw}"
        }
