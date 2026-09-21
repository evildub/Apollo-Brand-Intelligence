"""
Threadless Print-on-Demand (POD) Deep Harvester & Variant Dredge Engine.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep keyword search across Threadless marketplace and Artist Shops with multi-page pagination.
  - 1-to-20 Variant Dredge: Automatically maps 1 design into all available
    commercial physical variants (T-Shirts, Hoodies, Mugs, Tapestries, Pillows, Prints, Skate Decks).
  - Artist Shop Sweeper: Ingests and expands independent Threadless artist shop catalogs.
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

logger = logging.getLogger("ThreadlessScraper")

THREADLESS_PRODUCT_LINES = [
    ("Classic T-Shirt", "classic-t-shirt", 24.95, "Apparel - Men"),
    ("Extra Soft Graphic Tee", "extra-soft-tee", 27.95, "Apparel"),
    ("French Terry Pullover Hoodie", "pullover-hoodie", 54.95, "Outerwear"),
    ("Zip Hoodie", "zip-hoodie", 56.95, "Outerwear"),
    ("Long Sleeve T-Shirt", "long-sleeve-tee", 29.95, "Apparel"),
    ("Racerback Tank Top", "tank-top", 24.95, "Apparel"),
    ("Die-Cut Vinyl Sticker", "sticker", 4.95, "Stickers & Decals"),
    ("Ceramic Coffee Mug (11 oz)", "mug-11oz", 15.95, "Drinkware"),
    ("Stainless Travel Mug", "travel-mug", 26.95, "Drinkware"),
    ("Woven Wall Tapestry", "wall-tapestry", 39.95, "Home Decor"),
    ("Decorative Throw Pillow", "throw-pillow", 29.95, "Home Decor"),
    ("Cozy Fleece Blanket", "fleece-blanket", 49.95, "Home Goods"),
    ("Framed Fine Art Print", "art-print", 34.95, "Wall Art"),
    ("Stretched Canvas Print", "canvas-print", 64.95, "Wall Art"),
    ("iPhone Slim / Tough Case", "iphone-case", 24.95, "Phone Cases"),
    ("Canvas Tote Bag", "tote-bag", 18.95, "Bags & Accessories"),
    ("Custom Skate Deck", "skate-deck", 65.00, "Lifestyle & Sports"),
    ("Embroidered Dad Hat", "dad-hat", 24.95, "Headwear"),
    ("Bucket Hat", "bucket-hat", 26.95, "Headwear"),
    ("Polyester Bandana", "bandana", 14.95, "Accessories")
]


class ThreadlessScraper:
    """High-speed Threadless POD Search & Variant Dredge Engine."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/threadless_session")
        self.cookie_file = os.path.abspath("data/threadless_cookies.json")
        os.makedirs(self.user_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)

    def _clean_profile_locks(self):
        """Safely remove orphaned browser lockfiles from persistent profile."""
        if not os.path.exists(self.user_dir):
            return
        for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
            fpath = os.path.join(self.user_dir, fname)
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
            except Exception:
                pass

    def _get_context(self, p, force_visible: bool = False, window_pos: Optional[tuple] = None, window_size: Optional[tuple] = None):
        """Create browser context with stealth anti-detection parameters and cookie restoration."""
        self._clean_profile_locks()
        extra_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        if window_pos and len(window_pos) == 2:
            extra_args.append(f"--window-position={window_pos[0]},{window_pos[1]}")
        elif self.headless and not force_visible:
            extra_args.append("--window-position=-2400,-2400")

        w_size = window_size if (window_size and len(window_size) == 2) else (1366, 850)

        # Attempt to launch persistent context; if locked by an active session, fallback to fresh launch
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                self.user_dir,
                headless=False if force_visible else (False if self.headless else False),
                channel="msedge",
                args=extra_args,
                ignore_default_args=["--enable-automation"],
                viewport={"width": w_size[0], "height": w_size[1]}
            )
        except Exception as pe:
            logger.debug(f"Persistent context locked or unavailable ({pe}), falling back to standard launch with cookies...")
            browser = p.chromium.launch(
                headless=False if force_visible else (False if self.headless else False),
                channel="msedge",
                args=extra_args,
                ignore_default_args=["--enable-automation"]
            )
            context = browser.new_context(viewport={"width": w_size[0], "height": w_size[1]})

        # Load saved cookies if available
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    if isinstance(cookies, list) and cookies:
                        valid_cookies = [c for c in cookies if isinstance(c, dict) and "threadless" in c.get("domain", "")]
                        if valid_cookies:
                            context.add_cookies(valid_cookies)
            except Exception as ce:
                logger.debug(f"Could not restore Threadless cookies: {ce}")

        return context

    def launch_interactive_auth(self, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """
        Open a single visible browser session for the analyst to solve Cloudflare Turnstile verification
        or log in, persisting clearance tokens permanently for subsequent scans.
        """
        self._clean_profile_locks()
        time.sleep(0.3)

        try:
            with sync_playwright() as p:
                context = self._get_context(p, force_visible=True, window_pos=window_pos, window_size=window_size)
                page = context.pages[0] if context.pages else context.new_page()

                page.add_init_script("""
                    delete navigator.__proto__.webdriver;
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
                    window.chrome = { runtime: {}, app: {}, csi: () => {}, loadTimes: () => {} };
                """)

                try:
                    # Navigate directly to apparel search/shop endpoint where Turnstile clearance is established
                    page.goto("https://www.threadless.com/shop/+apparel", wait_until="domcontentloaded", timeout=45000)
                    logger.info("Threadless interactive authentication window opened.")
                except Exception as e:
                    logger.warning(f"Threadless interactive auth navigation note: {e}")

                # Keep browser alive until user completes verification and manually closes the window
                while True:
                    try:
                        if not context.pages or all(pg.is_closed() for pg in context.pages):
                            break
                        # Periodically save cookies as user navigates
                        try:
                            cks = context.cookies()
                            if cks:
                                with open(self.cookie_file, "w", encoding="utf-8") as cf:
                                    json.dump(cks, cf, indent=2)
                        except Exception:
                            pass
                        time.sleep(1.0)
                    except Exception:
                        break

                try:
                    cookies = context.cookies()
                    if cookies:
                        with open(self.cookie_file, "w", encoding="utf-8") as cf:
                            json.dump(cookies, cf, indent=2)
                        logger.info(f"Saved {len(cookies)} Threadless cookies from interactive auth.")
                except Exception as ce:
                    logger.warning(f"Failed to dump Threadless cookies: {ce}")

                try:
                    context.close()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Threadless interactive auth session error: {e}")

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
        Execute deep keyword search across Threadless with multi-page pagination.
        """
        results = []
        clean_q = query.strip()
        if not clean_q:
            return results

        if store_filter and any(k in store_filter.lower() for k in ("global", "search", "all", "community", "shop")):
            store_filter = None

        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        def _status(msg):
            if status_callback: status_callback(msg)

        _log(f"🧵 [Threadless] Starting POD Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

        seen_urls = set()

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("""
                    delete navigator.__proto__.webdriver;
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
                    window.chrome = { runtime: {}, app: {}, csi: () => {}, loadTimes: () => {} };
                """)

                for page_num in range(1, depth_pages + 1):
                    enc_q = urllib.parse.quote_plus(clean_q)
                    if store_filter:
                        clean_store = store_filter.strip().lstrip("@")
                        search_url = f"https://{clean_store}.threadless.com/?page={page_num}"
                    else:
                        search_url = f"https://www.threadless.com/shop/+{enc_q}/?page={page_num}"

                    _status(f"🧵 [Threadless] Fetching page {page_num}/{depth_pages}...")
                    _log(f"🧵 [Threadless] Navigating to: {search_url}")

                    try:
                        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    except Exception as nav_e:
                        _log(f"⚠ [Threadless] Navigation note on page {page_num}: {nav_e}")

                    # Check for Cloudflare challenge
                    curr_title = page.title()
                    if "Just a moment..." in curr_title or "Attention Required!" in curr_title or "Cloudflare" in curr_title:
                        _log("🛡️ [Threadless] Cloudflare challenge detected. Waiting for clearance...")
                        for _ in range(25):
                            page.wait_for_timeout(1000)
                            curr_title = page.title()
                            if "Just a moment..." not in curr_title and "Attention Required!" not in curr_title and "Cloudflare" not in curr_title and "Loading" not in curr_title:
                                _log("✅ [Threadless] Cloudflare challenge passed!")
                                break

                        curr_title = page.title()
                        if "Just a moment..." in curr_title or "Attention Required!" in curr_title or "Cloudflare" in curr_title:
                            _log("🛡️ [Threadless] Cloudflare security challenge active.")
                            _log("💡 [Threadless] Please click the '🧵 Threadless Connect' button in the toolbar to solve the verification once, then restart your scan.")
                            break

                    # Wait for Algolia InstantSearch / Hydrogen hydration
                    try:
                        page.wait_for_selector(".search-result-card, .ais-Hits-item, a[href*='/design/']", timeout=8000)
                    except Exception:
                        pass

                    time.sleep(1.5)
                    # Scroll down smoothly to trigger lazy-loaded images and cards
                    for _ in range(4):
                        try:
                            page.evaluate("window.scrollBy(0, 900);")
                        except Exception:
                            pass
                        time.sleep(0.4)
                    time.sleep(1.0)

                    html = page.content()
                    page_items = self._parse_search_page(html)
                    _log(f"🧵 [Threadless] Page {page_num}: Parsed {len(page_items)} listings.")

                    for it in page_items:
                        u = it.get("url")
                        if u and u not in seen_urls:
                            seen_urls.add(u)
                            results.append(it)

                    # Save active cookies
                    try:
                        active_cookies = context.cookies()
                        if active_cookies:
                            with open(self.cookie_file, "w", encoding="utf-8") as cf:
                                json.dump(active_cookies, cf, indent=2)
                    except Exception:
                        pass

                    if len(page_items) == 0:
                        _log(f"🧵 [Threadless] No more listings found on page {page_num}. Ending sweep.")
                        break

                try:
                    context.close()
                except Exception:
                    pass

        except Exception as e:
            _log(f"❌ [Threadless] Engine error: {e}")
            logger.exception("Threadless scraping failed")

        _log(f"✅ [Threadless] Search completed. Extracted {len(results)} distinct POD listing(s).")
        return results

    def _parse_search_page(self, html: str) -> List[Dict[str, Any]]:
        """Parse Threadless modern Hydrogen / Algolia search grid and classic cards into structured item dictionaries."""
        items = []
        soup = BeautifulSoup(html, "html.parser")

        # Decompose header, footer, and navigation menus so header artist links never contaminate search results
        for el in soup.select("header, nav, footer, .sub-menu, .threadless-header-menu-artists, .threadless-header"):
            el.decompose()

        # Match modern Algolia InstantSearch cards or classic search containers
        cards = soup.select(".search-result-card, .ais-Hits-item, .catalog-item, .product-card, div[data-product]")
        if not cards:
            # Fallback to direct design link anchors
            cards = soup.select("a[href*='/design/'], a[href*='/designs/'], a[href*='/product/']")

        seen_on_page = set()

        for card in cards:
            try:
                link_el = card if card.name == "a" else card.select_one(".search-result-link, a[href*='/design/'], a[href*='/designs/'], a[href*='/product/'], a[href^='/shop/']")
                if not link_el or not link_el.get("href"):
                    continue

                href = link_el["href"].strip()
                if not href.startswith("http"):
                    href = f"https://www.threadless.com{href}"

                if any(x in href for x in ("/cart", "/checkout", "/help", "/artist-shops", "/login", "/signup", "/privacy", "/terms", "/about", "/designs/submit")):
                    continue

                clean_url = href.split("?")[0].split("#")[0]
                if clean_url in seen_on_page:
                    continue

                # Must be a design or product page
                if not any(k in clean_url for k in ["/design/", "/designs/", "/product/"]) and "/shop/@" not in clean_url:
                    continue

                seen_on_page.add(clean_url)
                container = card if card.name != "a" else (card.find_parent("div", class_=lambda c: c and "search-result" in c) or card.find_parent("li") or card)

                # 1. Extract Item ID / Design Slug
                item_id = ""
                id_m = re.search(r'/design/([^/?#]+)', clean_url) or re.search(r'/designs/([^/?#]+)', clean_url) or re.search(r'/product/([^/?#]+)', clean_url)
                if id_m:
                    item_id = id_m.group(1)

                # 2. Extract Seller / Artist Name
                seller = "Threadless Artist"
                artist_slug = ""
                seller_m = re.search(r'/@([^/?#]+)', clean_url)
                if seller_m:
                    artist_slug = seller_m.group(1)
                    seller = artist_slug.replace("_", " ").title()

                # Check title container for explicit "by <Artist>"
                title_container = container.select_one(".search-result-title, .product-title, [class*='title']")
                if title_container:
                    t_full = title_container.get_text(separator=" ", strip=True)
                    by_m = re.search(r'\bby\s+([A-Za-z0-9_\-\s]+)$', t_full, flags=re.IGNORECASE)
                    if by_m:
                        seller = by_m.group(1).strip()

                # 3. Extract Title
                title = ""
                if title_container:
                    strong_el = title_container.find("strong")
                    if strong_el:
                        title = strong_el.get_text(strip=True)
                    else:
                        t_txt = title_container.get_text(strip=True)
                        t_txt = re.sub(r'\s+by\s+.*$', '', t_txt, flags=re.IGNORECASE)
                        title = t_txt.strip()

                if not title and link_el.get("aria-label"):
                    title = link_el["aria-label"].strip()

                img_el = container.find("img")
                if not title and img_el and img_el.get("alt"):
                    title = img_el["alt"].strip()

                if not title and item_id:
                    title = item_id.replace("-", " ").replace("_", " ").title()

                title = re.sub(r'\s+', ' ', title).strip()
                if not title or len(title) < 2 or title.lower() in ("cart", "search", "menu", "products", "designs"):
                    continue

                # 4. Extract Image URL
                image_url = ""
                if img_el:
                    src = img_el.get("src", "").strip()
                    if src and (src.startswith("http") or src.startswith("/")):
                        if not src.startswith("http"):
                            src = f"https://www.threadless.com{src}"
                        image_url = src
                    elif img_el.get("srcset"):
                        srcset = img_el.get("srcset", "").strip()
                        parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
                        if parts:
                            cand = parts[-1]
                            if not cand.startswith("http"):
                                cand = f"https://www.threadless.com{cand}"
                            image_url = cand
                    elif img_el.get("data-src"):
                        dsrc = img_el.get("data-src", "").strip()
                        if dsrc:
                            if not dsrc.startswith("http"):
                                dsrc = f"https://www.threadless.com{dsrc}"
                            image_url = dsrc

                # If image_url has maestro.threadless.com, ensure it has a valid width parameter
                if "maestro.threadless.com" in image_url:
                    if "preset=" in image_url:
                        image_url = re.sub(r'\?preset=[^&]*', '?width=600', image_url)
                    elif "?" not in image_url:
                        image_url = f"{image_url}?width=600"
                elif not image_url and artist_slug and item_id:
                    image_url = f"https://maestro.threadless.com/api/v1/image/artist/{artist_slug}/design/{item_id}?width=600"

                # 5. Extract Price
                price = "$24.95"
                p_match = re.search(r'\$\s*(\d+(?:\.\d{2})?)', container.get_text())
                if p_match:
                    price = f"${p_match.group(1)}"

                items.append({
                    "title": title,
                    "url": clean_url,
                    "price": price,
                    "item_id": item_id or "threadless_item",
                    "seller": seller,
                    "platform": "threadless",
                    "thumbnail": image_url,
                    "image_url": image_url,
                    "source": "Threadless Search",
                    "status": "New"
                })
            except Exception as ex:
                logger.debug(f"Error parsing Threadless card: {ex}")
                continue

        return items

    def fetch_single_item(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time metadata and high-res mockup for a single Threadless listing."""
        clean_url = url.strip()
        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                page.goto(clean_url, wait_until="domcontentloaded", timeout=25000)
                time.sleep(1.0)
                html = page.content()
                context.close()

            soup = BeautifulSoup(html, "html.parser")

            title = ""
            t_el = soup.select_one("h1, meta[property='og:title']")
            if t_el:
                title = t_el.get("content", "") if t_el.name == "meta" else t_el.get_text(strip=True)

            price = "$24.95"
            p_el = soup.select_one("meta[property='product:price:amount'], [class*='price'], [class*='Price']")
            if p_el:
                p_val = p_el.get("content") if p_el.name == "meta" else p_el.get_text(strip=True)
                p_m = re.search(r"\$\d+(?:\.\d{2})?", p_val)
                if p_m:
                    price = p_m.group(0)

            seller = "Threadless Artist"
            s_el = soup.select_one("a[href*='/@'], [class*='artist-name'], [class*='creator-name']")
            if s_el:
                s_txt = s_el.get_text(strip=True)
                if s_txt:
                    seller = re.sub(r"^(?:by|By|from|From)\s*", "", s_txt, flags=re.IGNORECASE).strip()

            image_url = ""
            img_el = soup.select_one("meta[property='og:image'], img.product-image, img[class*='mainImage']")
            if img_el:
                image_url = img_el.get("content") if img_el.name == "meta" else img_el.get("src", "")

            item_id = ""
            id_m = re.search(r"/product/(\d+)", clean_url) or re.search(r"/designs/([^/]+)", clean_url)
            if id_m:
                item_id = id_m.group(1)

            return {
                "title": title or "Threadless Artist Design",
                "url": clean_url,
                "price": price,
                "item_id": item_id,
                "seller": seller,
                "platform": "threadless",
                "thumbnail": image_url,
                "image_url": image_url,
                "source": "Threadless PDP",
                "status": "New"
            }
        except Exception as e:
            logger.error(f"Failed to fetch single Threadless item {url}: {e}")
            return None

    def expand_design_variants(
        self,
        parent_item: Dict[str, Any],
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        1-to-20 POD Variant Matrix Expansion for Threadless designs.
        Generates individual merchandise variants for enforcement.
        """
        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        variants = []
        base_url = parent_item.get("url", "")
        base_title = parent_item.get("title", "Custom Artwork")
        seller = parent_item.get("seller", "Threadless Artist")
        parent_id = parent_item.get("item_id", "")
        base_image = parent_item.get("image_url") or parent_item.get("thumbnail", "")

        clean_title = re.sub(r"\s*-\s*T-?Shirt.*$", "", base_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Mug.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*-\s*Sticker.*$", "", clean_title, flags=re.IGNORECASE)
        clean_title = clean_title.strip()

        _log(f"🧵 [Threadless] Expanding POD Matrix for design '{clean_title[:35]}...'")

        for prod_name, slug_code, est_price, category in THREADLESS_PRODUCT_LINES:
            var_url = f"{base_url}?style={slug_code}"
            var_title = f"{clean_title} - {prod_name}"
            var_id = f"{parent_id}_{slug_code}" if parent_id else slug_code

            variants.append({
                "title": var_title,
                "url": var_url,
                "price": f"${est_price:.2f}",
                "item_id": var_id,
                "seller": seller,
                "platform": "threadless",
                "thumbnail": base_image,
                "image_url": base_image,
                "source": f"Threadless POD ({category})",
                "status": "New"
            })

        _log(f"🧵 [Threadless] Generated +{len(variants)} POD commercial variants.")
        return variants
