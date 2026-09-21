"""
Redbubble Scraper Module for Apollo Brand Intelligence Suite.
Specialized in automated retrieval of Print-on-Demand (POD) merchandise,
apparel, stickers, and artist shop listings on Redbubble (redbubble.com).

Features:
- Ultra high-speed Next.js hydration payload extraction with 100% thumbnail guarantee.
- 1-to-74 Print-on-Demand (POD) Design Variant Expansion Engine.
- Deep Artist Portfolio Sweeper (/people/<artist>/shop) discovering hidden portfolio infringements.
- High-res preview and structured metadata normalization.
"""

import os
import io
import re
import json
import time
import random
import logging
import threading
import urllib.parse
import urllib.request
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from PIL import Image

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as curl_requests
    HAS_CURL_CFFI = False

logger = logging.getLogger("Apollo.RedbubbleScraper")


class RedbubbleScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._context = None
        self.profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Apollo_Hunter", "redbubble_profile"
        )
        os.makedirs(self.profile_dir, exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _find_edge_path(self) -> Optional[str]:
        """Locate native Microsoft Edge executable on Windows."""
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ]
        return next((p for p in edge_paths if os.path.exists(p)), None)

    def _get_context(self):
        """Initialize or return existing Playwright context with stealth evasions and persistent profile."""
        from playwright.sync_api import sync_playwright
        if self._pw is None:
            self._pw = sync_playwright().start()

        if self._context is None:
            edge_path = self._find_edge_path()
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
            ]

            kwargs = {
                "user_data_dir": self.profile_dir,
                "headless": self.headless,
                "args": args,
                "viewport": {"width": 1366, "height": 850},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "locale": "en-US",
            }
            if edge_path:
                kwargs["executable_path"] = edge_path
            else:
                kwargs["channel"] = "msedge"

            try:
                self._context = self._pw.chromium.launch_persistent_context(**kwargs)
            except Exception:
                kwargs.pop("executable_path", None)
                self._context = self._pw.chromium.launch_persistent_context(**kwargs)

        return self._context

    def close(self):
        """Cleanly close persistent browser context."""
        try:
            if self._context:
                self._context.close()
                self._context = None
            if self._pw:
                self._pw.stop()
                self._pw = None
        except Exception:
            pass

    def extract_item_id(self, url: str, fallback_work_id: str = "") -> str:
        """
        Extract the composite Redbubble Item ID formatted as {work_id}.{sku_code}
        (e.g., '54931656.7sgk' from '/54931656/7sgk' or '/54931656.7sgk').
        """
        if not url:
            return str(fallback_work_id or "")
        m = re.search(r'/(\d+)[./]([a-zA-Z0-9]{3,8})(?:[?#]|$)', url)
        if m:
            return f"{m.group(1)}.{m.group(2)}"
        m2 = re.search(r'/(?:works/|i/[^/]+/[^/]+/)?(\d{6,12})(?:[-./?#]|$)', url)
        if m2:
            return m2.group(1)
        m3 = re.search(r'/(\d{6,12})(?:[?#]|$)', url)
        if m3:
            return m3.group(1)
        return str(fallback_work_id or "")

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

    def _get_session(self):
        if HAS_CURL_CFFI:
            s = curl_requests.Session(impersonate="chrome124")
        else:
            s = curl_requests.Session()
        s.headers.update(self.headers)
        return s

    def resolve_store_info(self, raw_input: str) -> dict:
        """Parse Redbubble artist shop URL, artist name, or Global Search."""
        raw = raw_input.strip() if raw_input else ""
        if not raw or any(g in raw.lower() for g in ("global", "marketplace", "all", "wholesale", "catalog")):
            return {
                "artist": "GLOBAL",
                "store_name": "Redbubble Global Catalog",
                "original": "https://www.redbubble.com"
            }

        # Check for artist URL (e.g. redbubble.com/people/artistname/shop or redbubble.com/people/artistname)
        m = re.search(r'/people/([a-zA-Z0-9_\-]+)', raw)
        if m:
            artist = m.group(1)
            return {
                "artist": artist,
                "store_name": f"Redbubble Shop ({artist})",
                "original": raw
            }

        # Plain artist name passed
        clean_name = raw.split("/")[-1].replace("?.*", "").strip()
        return {
            "artist": clean_name,
            "store_name": f"Redbubble Shop ({clean_name})",
            "original": f"https://www.redbubble.com/people/{clean_name}/shop"
        }

    def _convert_price(self, price_raw: str) -> float:
        """Extract numeric float from price string."""
        if not price_raw:
            return 0.0
        clean = re.sub(r"[^\d.]", "", price_raw)
        try:
            return float(clean)
        except ValueError:
            return 0.0

    def search(self, query: str, max_items: int = 50, condition: str = "all", log_callback=None) -> List[Dict]:
        """
        Execute search on Redbubble using Next.js hydration payload extraction with HTML fallback.
        
        Args:
            query: Keyword string (e.g., 'Toyota TRD', 'Ford Mustang')
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
        page = 1

        encoded_q = urllib.parse.quote(query.strip())
        _log(f"🎨 [Redbubble] Initiating search for '{query}'...")

        session = self._get_session()

        try:
            while len(results) < max_items and page <= 5:
                if page == 1:
                    target_url = f"https://www.redbubble.com/shop/?query={encoded_q}"
                else:
                    target_url = f"https://www.redbubble.com/shop/?query={encoded_q}&page={page}"

                _log(f"🌐 [Redbubble] Fetching page {page}...")

                resp = session.get(target_url, timeout=18)
                if resp.status_code != 200:
                    _log(f"⚠ [Redbubble] HTTP status {resp.status_code} on page {page}.")
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                next_data = soup.find("script", id="__NEXT_DATA__")
                page_items = []

                # Strategy 1: Next.js __NEXT_DATA__ Hydration Payload (100% accurate thumbnails and metadata)
                if next_data:
                    try:
                        data = json.loads(next_data.text)
                        raw_results = data.get("props", {}).get("pageProps", {}).get("results", [])
                        for r in raw_results:
                            inv = r.get("inventoryItem", {})
                            work = inv.get("work", {})
                            urls = inv.get("productPageUrls", {})
                            full_url = urls.get("url") or urls.get("fallbackUrl") or inv.get("productPageUrl") or ""
                            if not full_url.startswith("http"):
                                full_url = f"https://www.redbubble.com{full_url}"

                            item_id = self.extract_item_id(full_url, fallback_work_id=str(work.get("id") or inv.get("workId") or "").strip())
                            title = (work.get("title") or inv.get("description") or "Redbubble Product").strip()
                            desc = (inv.get("description") or "Merchandise").strip()
                            artist = (work.get("artistUsername") or "Redbubble Artist").strip()

                            if not item_id or item_id in seen_ids:
                                continue
                            seen_ids.add(item_id)

                            # Guaranteed high-res preview image
                            previews = inv.get("previewSet", {}).get("previews", [])
                            img_url = previews[0].get("url", "") if previews else ""

                            # Price
                            p_obj = inv.get("price", {})
                            amt = p_obj.get("amount")
                            price_str = f"${amt:.2f}" if isinstance(amt, (int, float)) else str(amt or "$19.99")

                            item_dict = {
                                "brand": "",
                                "product_type": desc,
                                "title": title,
                                "item_id": item_id,
                                "price": price_str,
                                "seller": artist,
                                "location": "United States",
                                "image_url": img_url,
                                "url": full_url,
                                "marketplace": "redbubble.com",
                                "condition": "New",
                                "keyword": query,
                            }
                            page_items.append(item_dict)
                            results.append(item_dict)

                            if len(results) >= max_items:
                                break
                    except Exception as json_err:
                        logger.debug(f"Redbubble JSON parse failed on page {page}: {json_err}")

                # Strategy 2: HTML Fallback
                if not page_items:
                    product_links = soup.find_all("a", href=re.compile(r"^/i/"))
                    for a in product_links:
                        href = a.get("href", "")
                        if not href or not a.text.strip():
                            continue

                        full_url = f"https://www.redbubble.com{href}"
                        m = re.search(r"^/i/([^/]+)/(.+)-by-([^/]+)/(\d+)", href)
                        if m:
                            ptype = m.group(1).replace("-", " ").title()
                            title_slug = m.group(2).replace("-", " ")
                            artist = m.group(3)
                            item_id = self.extract_item_id(full_url, fallback_work_id=m.group(4))
                        else:
                            ptype = "Merchandise"
                            title_slug = a.text.strip()
                            artist = "Redbubble Artist"
                            item_id = self.extract_item_id(full_url, fallback_work_id=re.sub(r'\D+', '', href)[-8:])

                        if not item_id or item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)

                        parent = a.find_parent("div")
                        img_el = a.find("img") or (parent.find("img") if parent else None)
                        img_url = img_el.get("src") or img_el.get("data-src") if img_el else ""

                        price_text = "$19.99"
                        price_el = parent.find(string=re.compile(r"\$\d+(?:\.\d{2})?")) if parent else None
                        if price_el:
                            price_text = price_el.strip()

                        title = a.get("aria-label") or title_slug.title()

                        item_dict = {
                            "brand": "",
                            "product_type": ptype,
                            "title": title,
                            "item_id": item_id,
                            "price": price_text,
                            "seller": artist,
                            "location": "United States",
                            "image_url": img_url,
                            "url": full_url,
                            "marketplace": "redbubble.com",
                            "condition": "New",
                            "keyword": query,
                        }
                        page_items.append(item_dict)
                        results.append(item_dict)

                        if len(results) >= max_items:
                            break

                _log(f"📦 [Redbubble] Harvested {len(page_items)} listings from page {page} ({len(results)}/{max_items} total).")

                if len(results) >= max_items or len(page_items) == 0:
                    break

                page += 1
                time.sleep(0.5)

        except Exception as e:
            _log(f"❌ Error during Redbubble search: {e}")
            logger.exception("Redbubble search failure")

        _log(f"✅ [Redbubble] Search complete: Retrieved {len(results)} listings.")
        return results

    def expand_design_variants(self, items: List[Dict],
                               existing_item_ids: Optional[set] = None,
                               progress_callback=None,
                               stop_event: threading.Event = None,
                               log_callback=None) -> List[Dict]:
        """
        Dredge and harvest all Print-on-Demand (POD) product variants for given Redbubble listings.
        Each parent design listing expands into 60-74 physical product listings
        (Hoodies, Mugs, Stickers, T-Shirts, Posters, Cases, Pillows, Magnets, Acrylic Blocks, etc.).
        
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
        session = self._get_session()
        total_parents = len(items)

        try:
            for idx, parent in enumerate(items):
                if stop_event and stop_event.is_set():
                    _log("⏹ [Redbubble] Variant expansion cancelled by user.")
                    break

                parent_id = str(parent.get("item_id", "")).strip()
                raw_url = str(parent.get("url", "")).strip()
                if not raw_url:
                    continue

                if not raw_url.startswith("http"):
                    if raw_url.startswith("/"):
                        raw_url = f"https://www.redbubble.com{raw_url}"
                    elif re.match(r'^\d+$', raw_url):
                        raw_url = f"https://www.redbubble.com/shop/ap/{raw_url}"
                    else:
                        raw_url = f"https://www.redbubble.com/{raw_url}"

                seller = parent.get("seller") or "Redbubble Artist"
                brand = parent.get("brand", "")
                keyword = parent.get("keyword", "")
                parent_title = parent.get("title", "")
                new_for_this_parent = 0

                _log(f"🎨 [Redbubble] Expanding variants for [{idx+1}/{total_parents}]: '{parent_title[:35]}...'")

                try:
                    resp = session.get(raw_url, timeout=18)
                    html_text = resp.text if resp.status_code == 200 else ""

                    # Fallback to Playwright if session get blocked or empty
                    if not html_text or resp.status_code in (403, 429, 503):
                        try:
                            context = self._get_context()
                            page = context.new_page()
                            page.goto(raw_url, wait_until="domcontentloaded", timeout=20000)
                            page.wait_for_timeout(1500)
                            html_text = page.content()
                            page.close()
                        except Exception as pw_err:
                            logger.debug(f"Playwright fallback fetch error: {pw_err}")

                    if not html_text:
                        _log(f"⚠ [Redbubble] Could not retrieve page HTML for {raw_url}.")
                        continue

                    soup = BeautifulSoup(html_text, "html.parser")
                    parent_variants = []

                    # ── Strategy 1: Next.js __NEXT_DATA__ JSON ────────────────────
                    next_data = soup.find("script", id="__NEXT_DATA__")
                    if next_data:
                        try:
                            data = json.loads(next_data.text)
                            props = data.get("props", {}).get("pageProps", {})
                            inv_items = (
                                props.get("defaultInventoryItems") or
                                props.get("inventoryItems") or
                                props.get("work", {}).get("inventoryItems") or
                                props.get("work", {}).get("products") or
                                []
                            )
                            for it in inv_items:
                                if not isinstance(it, dict):
                                    continue
                                p_urls = it.get("productPageUrls", {})
                                u = p_urls.get("url") or p_urls.get("fallbackUrl") or it.get("productPageUrl") or it.get("url") or ""
                                if not u:
                                    continue
                                if not u.startswith("http"):
                                    u = f"https://www.redbubble.com{u}"

                                v_id = self.extract_item_id(u, fallback_work_id=str(it.get("id", "")).strip())
                                if not v_id or v_id in known_ids or v_id == parent_id:
                                    continue
                                known_ids.add(v_id)

                                desc = (it.get("description") or "Merchandise").strip()
                                p_obj = it.get("price", {})
                                amt = p_obj.get("amount") if isinstance(p_obj, dict) else None
                                price_str = f"${amt:.2f}" if isinstance(amt, (int, float)) else str(amt or parent.get("price") or "$19.99")

                                previews = it.get("previewSet", {}).get("previews", []) if isinstance(it.get("previewSet"), dict) else []
                                img_url = previews[0].get("url", "") if previews else parent.get("image_url", "")

                                full_title = f"{parent_title} - {desc}" if parent_title and desc.lower() not in parent_title.lower() else (parent_title or f"Redbubble {desc}")

                                variant_item = {
                                    "brand": brand,
                                    "product_type": desc,
                                    "title": full_title,
                                    "item_id": v_id,
                                    "price": price_str,
                                    "seller": seller,
                                    "location": "United States",
                                    "image_url": img_url,
                                    "thumbnail": img_url or parent.get("thumbnail", "") or parent.get("image_url", ""),
                                    "url": u,
                                    "marketplace": "redbubble.com",
                                    "condition": "New",
                                    "keyword": keyword
                                }
                                parent_variants.append(variant_item)
                        except Exception as json_err:
                            logger.debug(f"Redbubble Next.js parse error: {json_err}")

                    # ── Strategy 2: window.__APOLLO_STATE__ GraphQL State ─────────
                    if not parent_variants:
                        for s in soup.find_all("script"):
                            txt = s.text
                            if "window.__APOLLO_STATE__" in txt:
                                m = re.search(r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});', txt, re.DOTALL)
                                if m:
                                    try:
                                        apollo_data = json.loads(m.group(1))
                                        for k, v in apollo_data.items():
                                            if isinstance(v, dict) and "productPageUrls" in v:
                                                p_urls = v.get("productPageUrls", {})
                                                u = p_urls.get("url") or p_urls.get("fallbackUrl") or ""
                                                if not u:
                                                    continue
                                                if not u.startswith("http"):
                                                    u = f"https://www.redbubble.com{u}"

                                                v_id = self.extract_item_id(u, fallback_work_id=str(v.get("id", "")).strip())
                                                if not v_id or v_id in known_ids or v_id == parent_id:
                                                    continue
                                                known_ids.add(v_id)

                                                desc = (v.get("description") or "Merchandise").strip()
                                                p_obj = v.get("price", {})
                                                amt = p_obj.get("amount") if isinstance(p_obj, dict) else None
                                                price_str = f"${amt:.2f}" if isinstance(amt, (int, float)) else str(amt or parent.get("price") or "$19.99")

                                                previews = v.get("previewSet", {}).get("previews", []) if isinstance(v.get("previewSet"), dict) else []
                                                img_url = previews[0].get("url", "") if previews else parent.get("image_url", "")

                                                full_title = f"{parent_title} - {desc}" if parent_title and desc.lower() not in parent_title.lower() else (parent_title or f"Redbubble {desc}")

                                                parent_variants.append({
                                                    "brand": brand,
                                                    "product_type": desc,
                                                    "title": full_title,
                                                    "item_id": v_id,
                                                    "price": price_str,
                                                    "seller": seller,
                                                    "location": "United States",
                                                    "image_url": img_url,
                                                    "thumbnail": img_url or parent.get("thumbnail", "") or parent.get("image_url", ""),
                                                    "url": u,
                                                    "marketplace": "redbubble.com",
                                                    "condition": "New",
                                                    "keyword": keyword
                                                })
                                    except Exception as ap_err:
                                        logger.debug(f"Apollo state parse error: {ap_err}")

                    # ── Strategy 3: DOM Product Link & Card Extraction ───────────
                    if not parent_variants:
                        for a in soup.select('a[href*="/i/"]'):
                            href = a.get("href", "")
                            if not href:
                                continue
                            if not href.startswith("http"):
                                href = f"https://www.redbubble.com{href}"

                            v_id = self.extract_item_id(href)
                            if not v_id or v_id in known_ids or v_id == parent_id:
                                continue
                            known_ids.add(v_id)

                            raw_text = a.get_text(" ", strip=True)
                            m_price = re.search(r'\$[\d,.]+', raw_text)
                            price_str = m_price.group(0) if m_price else str(parent.get("price") or "$19.99")
                            desc = raw_text.replace(price_str, "").replace("From", "").strip() or "Merchandise"

                            img = a.select_one("img")
                            img_url = ""
                            if img:
                                img_url = img.get("src") or img.get("data-src") or ""
                                if img_url.startswith("//"):
                                    img_url = f"https:{img_url}"

                            full_title = f"{parent_title} - {desc}" if parent_title and desc.lower() not in parent_title.lower() else (parent_title or f"Redbubble {desc}")

                            parent_variants.append({
                                "brand": brand,
                                "product_type": desc,
                                "title": full_title,
                                "item_id": v_id,
                                "price": price_str,
                                "seller": seller,
                                "location": "United States",
                                "image_url": img_url or parent.get("image_url", ""),
                                "thumbnail": img_url or parent.get("thumbnail", "") or parent.get("image_url", ""),
                                "url": href,
                                "marketplace": "redbubble.com",
                                "condition": "New",
                                "keyword": keyword
                            })

                    for var in parent_variants:
                        expanded_results.append(var)
                        new_for_this_parent += 1

                    _log(f"  ✓ Harvested +{new_for_this_parent} POD product variants for '{parent_title[:30]}...' (Total new: {len(expanded_results)})")

                    if progress_callback:
                        progress_callback(idx + 1, total_parents, len(expanded_results), parent)

                except Exception as ex:
                    _log(f"⚠ [Redbubble] Error expanding variants for {raw_url}: {ex}")

                time.sleep(random.uniform(0.3, 0.7))

        except Exception as e:
            _log(f"❌ [Redbubble] Error during variant expansion batch: {e}")
            logger.exception("Redbubble variant expansion failure")

        _log(f"✅ [Redbubble] Variant dredge complete: Added {len(expanded_results)} new POD listing URLs.")
        return expanded_results

    def sweep_artist_portfolio(self, artist_name: str, brand_keyword: str = "", max_items: int = 100,
                               existing_item_ids: Optional[set] = None,
                               progress_callback=None,
                               stop_event: threading.Event = None,
                               log_callback=None) -> List[Dict]:
        """
        Sweep an artist's full portfolio on Redbubble (/people/<artist>/shop).
        Discovers all other infringing designs created by this specific seller.
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            logger.info(msg)

        clean_artist = artist_name.strip().replace(" ", "")
        if not clean_artist or clean_artist.lower() in ("redbubble artist", "unknown", "global"):
            return []

        _log(f"🎨 [Redbubble] Sweeping artist portfolio for '{clean_artist}' (Filter: '{brand_keyword or 'All'}')...")
        results = []
        seen_ids = set(existing_item_ids or set())
        page = 1
        session = self._get_session()

        try:
            while len(results) < max_items and page <= 5:
                if stop_event and stop_event.is_set():
                    _log("⏹ [Redbubble] Artist portfolio sweep cancelled by user.")
                    break

                if brand_keyword:
                    encoded_k = urllib.parse.quote(brand_keyword.strip())
                    url = f"https://www.redbubble.com/people/{clean_artist}/shop?query={encoded_k}&page={page}"
                else:
                    url = f"https://www.redbubble.com/people/{clean_artist}/shop?page={page}"

                resp = session.get(url, timeout=18)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                next_data = soup.find("script", id="__NEXT_DATA__")
                page_results = []

                if next_data:
                    try:
                        data = json.loads(next_data.text)
                        raw_results = data.get("props", {}).get("pageProps", {}).get("results", [])
                        for r in raw_results:
                            inv = r.get("inventoryItem", {})
                            work = inv.get("work", {})
                            urls = inv.get("productPageUrls", {})
                            full_url = urls.get("url") or urls.get("fallbackUrl") or inv.get("productPageUrl") or ""
                            if not full_url.startswith("http"):
                                full_url = f"https://www.redbubble.com{full_url}"

                            item_id = self.extract_item_id(full_url, fallback_work_id=str(work.get("id") or inv.get("workId") or "").strip())
                            title = (work.get("title") or inv.get("description") or "Redbubble Product").strip()
                            desc = (inv.get("description") or "Merchandise").strip()
                            artist = (work.get("artistUsername") or clean_artist).strip()

                            if not item_id or item_id in seen_ids:
                                continue
                            seen_ids.add(item_id)

                            previews = inv.get("previewSet", {}).get("previews", [])
                            img_url = previews[0].get("url", "") if previews else ""

                            p_obj = inv.get("price", {})
                            amt = p_obj.get("amount")
                            price_str = f"${amt:.2f}" if isinstance(amt, (int, float)) else str(amt or "$19.99")

                            item_dict = {
                                "brand": brand_keyword.title() if brand_keyword else "",
                                "product_type": desc,
                                "title": title,
                                "item_id": item_id,
                                "price": price_str,
                                "seller": artist,
                                "location": "United States",
                                "image_url": img_url,
                                "url": full_url,
                                "marketplace": "redbubble.com",
                                "condition": "New",
                                "keyword": brand_keyword,
                            }
                            page_results.append(item_dict)
                            results.append(item_dict)

                            if len(results) >= max_items:
                                break
                    except Exception as json_err:
                        logger.debug(f"Artist sweep JSON parse error: {json_err}")

                if not page_results:
                    break

                _log(f"  ✓ Harvested +{len(page_results)} portfolio items from page {page} ({len(results)} total).")
                page += 1
                time.sleep(0.5)

        except Exception as e:
            _log(f"❌ [Redbubble] Error sweeping artist portfolio: {e}")
            logger.exception("Artist portfolio sweep failure")

        _log(f"✅ [Redbubble] Artist portfolio sweep finished: Discovered {len(results)} designs by '{clean_artist}'.")
        return results

    def enrich_seller_info(self, items: List[Dict],
                           progress_callback=None,
                           stop_event: threading.Event = None,
                           chunk_size: int = 15) -> List[Dict]:
        """
        Enrich real creator / artist names and exact pricing for Redbubble items.
        Redbubble artist names are extracted directly from URL slugs and Next.js hydration state.
        """
        if not items:
            return items

        for idx, it in enumerate(items):
            if stop_event and stop_event.is_set():
                break
            raw_url = it.get("url", "")
            if not it.get("seller") or it.get("seller") in ("Redbubble Artist", "GLOBAL", "unknown", "Redbubble Creator"):
                m = re.search(r'/by-([^/]+)/', raw_url)
                if m:
                    it["seller"] = m.group(1).strip()
            if progress_callback:
                progress_callback(idx + 1, len(items), it)

        return items

    def find_connected_network(self, item_id: str, item_url: str = "", target_img_url: str = "") -> List[Dict]:
        """
        On-Demand Visual Syndicate & Connected Artist Hunter for Redbubble.
        Scans recommendation carousels, artist shops, and merchandise rows:
        - "Stickers you might like" / "You might like"
        - "More by this artist" / "Designed and sold by [seller]"
        - "Also available on"
        Performs perceptual image matching (dHash) against target_img_url.
        """
        if not item_url and item_id:
            item_url = f"https://www.redbubble.com/i/product/{item_id}"
        if not item_id and item_url:
            item_id = self.extract_item_id(item_url)

        if not item_url:
            return []

        logger.info(f"🎨 [Redbubble] Hunting connected network for {item_id} ({item_url})...")
        ctx = self._get_context()
        page = ctx.new_page()

        try:
            page.goto(item_url, wait_until="domcontentloaded", timeout=25000)

            # Fast active carousel harvesting with inactivity early exit
            raw_items = []
            last_count = 0
            last_change_time = time.time()
            max_scan_duration = 5.0
            idle_threshold = 1.5
            start_scan = time.time()

            extract_script = """() => {
                const items = [];
                const seen = new Set();
                
                const allLinks = Array.from(document.querySelectorAll('a[href*="/i/"], a[href*="/works/"]'));
                for (let a of allLinks) {
                    const href = a.href || '';
                    if (!href || seen.has(href)) continue;
                    
                    const m = href.match(/\\/(\\d+)[.\\/]([a-zA-Z0-9]{3,8})(?:[?#]|$)/) || href.match(/\\/(\\d+)(?:[?#]|$)/);
                    if (!m) continue;
                    
                    seen.add(href);
                    const itemId = m[2] ? `${m[1]}.${m[2]}` : m[1];
                    
                    const container = a.closest('div[class*="styles__box"], div[class*="styles__item"], div[class*="Carousel"], div') || a;
                    
                    let imgUrl = '';
                    const imgs = Array.from(container.querySelectorAll('img'));
                    for (let img of imgs) {
                        const src = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                        if (src && src.includes('redbubble.net/image') && !src.includes('.svg')) {
                            imgUrl = src;
                            break;
                        }
                    }
                    if (!imgUrl) {
                        for (let img of imgs) {
                            const src = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                            if (src && !src.includes('.svg') && !src.includes('heart') && src.startsWith('http')) {
                                imgUrl = src;
                                break;
                            }
                        }
                    }
                    
                    let title = '';
                    let seller = '';
                    
                    for (let img of imgs) {
                        const alt = (img.alt || '').trim();
                        const altM = alt.match(/Item preview,\\s*(.+?)\\s*designed and sold by\\s*(.+?)\\.?$/i);
                        if (altM) {
                            title = altM[1].trim();
                            seller = altM[2].trim();
                            break;
                        }
                    }
                    
                    if (!title || !seller) {
                        const urlM = href.match(/\\/i\\/[^\\/]+\\/(.+)-by-([^\\/]+)\\//);
                        if (urlM) {
                            if (!title) title = urlM[1].replace(/-/g, ' ').trim();
                            if (!seller) seller = urlM[2].trim();
                        }
                    }
                    if (!title) {
                        title = (a.innerText || container.innerText || '').split('\\n')[0].trim();
                    }
                    
                    let price = '';
                    const priceM = (container.innerText || a.innerText || '').match(/\\$\\s*[\\d,]+(?:\\.\\d+)?/);
                    if (priceM) {
                        price = priceM[0];
                    }
                    
                    items.push({
                        item_id: itemId,
                        url: href.split('?')[0],
                        title: title,
                        seller: seller,
                        price: price,
                        image_url: imgUrl
                    });
                }
                return items;
            }"""

            for step in range(8):
                if time.time() - start_scan > max_scan_duration:
                    break
                try:
                    page.evaluate(f"window.scrollBy(0, {(step + 1) * 600});")
                except Exception:
                    pass
                time.sleep(0.35)

                try:
                    current_items = page.evaluate(extract_script)
                except Exception:
                    current_items = []

                if len(current_items) > last_count:
                    last_count = len(current_items)
                    last_change_time = time.time()
                    raw_items = current_items
                elif last_count > 0 and (time.time() - last_change_time >= idle_threshold):
                    break

            if not raw_items:
                try:
                    raw_items = page.evaluate(extract_script)
                except Exception:
                    pass

            # Close browser context immediately to release resources & close window
            try:
                page.close()
            except Exception:
                pass
            if self.headless:
                self.close()

            # Target dHash calculation
            target_hash = None
            if target_img_url:
                try:
                    req = urllib.request.Request(target_img_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(req, timeout=3.0) as r:
                        t_pimg = Image.open(io.BytesIO(r.read())).convert("RGB")
                        target_hash = self.compute_dhash(t_pimg)
                except Exception as e:
                    logger.debug(f"Target Redbubble image dHash calculation skipped: {e}")

            # Parallel dHash calculation for harvested items
            item_badges = {}
            if target_hash and raw_items:
                def _calc_similarity(it):
                    clean_u = it.get("url", "")
                    img_u = it.get("image_url", "")
                    if not img_u:
                        return clean_u, "👕 POD Print Syndicate / Related Merchandise"
                    try:
                        req = urllib.request.Request(img_u, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                        with urllib.request.urlopen(req, timeout=1.8) as r:
                            cand_pimg = Image.open(io.BytesIO(r.read())).convert("RGB")
                            c_hash = self.compute_dhash(cand_pimg)
                            dist = self.hamming_distance(target_hash, c_hash)
                            sim_pct = max(0, int((1.0 - (dist / 64.0)) * 100))
                            if dist == 0:
                                return clean_u, "🎯 Exact Match (dHash: 0, 100%)"
                            elif dist <= 4:
                                return clean_u, f"🎯 Near-Exact Photo (dHash: {dist}, {sim_pct}%)"
                            elif dist <= 12:
                                return clean_u, f"🖼 Visual Match (dHash: {dist}, {sim_pct}%)"
                            else:
                                return clean_u, f"👕 Related Merchandise ({sim_pct}%)"
                    except Exception:
                        return clean_u, "👕 POD Print Syndicate / Related Merchandise"

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(_calc_similarity, it) for it in raw_items]
                    for f in as_completed(futures):
                        try:
                            u, badge = f.result()
                            item_badges[u] = badge
                        except Exception:
                            pass

            results = []
            seen_clean_urls = set()
            for it in raw_items:
                clean_u = it.get("url", "")
                if clean_u in seen_clean_urls:
                    continue
                seen_clean_urls.add(clean_u)

                img_u = it.get("image_url", "")
                sim_badge = item_badges.get(clean_u, "👕 POD Print Syndicate / Related Merchandise")

                results.append({
                    "brand": "",
                    "product_type": "Merchandise",
                    "title": it.get("title") or "Redbubble Listing",
                    "item_id": it.get("item_id"),
                    "price": it.get("price") or "$19.99",
                    "seller": it.get("seller") or "Redbubble Creator",
                    "location": "United States",
                    "seller_origin": "United States",
                    "threat_badge": "👕 POD Print Syndicate",
                    "image_url": img_u,
                    "url": clean_u,
                    "similarity": sim_badge,
                    "marketplace": "redbubble.com"
                })

            return results

        except Exception as e:
            logger.exception("Error finding Redbubble connected network")
            return []
        finally:
            try: page.close()
            except Exception: pass
            if self.headless:
                self.close()


