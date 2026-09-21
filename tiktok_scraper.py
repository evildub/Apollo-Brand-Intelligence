"""
TikTok Shop Scraper Module for Apollo Brand Intelligence Suite.
Specialized in automated retrieval of TikTok Shop (shop.tiktok.com) merchandise,
creator storefronts, product detail pages (PDP), and automotive/consumer infringements.

Features:
- High-speed HTTP request engine (curl_cffi impersonate Chrome 124).
- Resilient Playwright + Microsoft Edge Stealth fallback with persistent session profile.
- Exact PDP metadata parsing (Title, Price, Seller Name, Business Entity, Origin Address, Sold Count).
- Automatic Genesis Column H compliance (shop.tiktok.com).
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

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

logger = logging.getLogger("Apollo.TikTokScraper")


class TikTokScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.profile_dir = os.path.join(self.base_dir, "data", "tiktok_session")
        os.makedirs(self.profile_dir, exist_ok=True)
        self.last_scrape_warning = ""
        self.is_bot_challenge = False
        self.blocked_store_name = ""
        self.blocked_store_url = ""

    def _find_edge_path(self) -> Optional[str]:
        """Detect Edge browser path on Windows."""
        for p in (
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ):
            if os.path.exists(p):
                return p
        return None

    def launch_interactive_auth(self, target_url: str = "https://shop.tiktok.com/us", window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """Launch interactive Edge browser with persistent TikTok session for analyst login or CAPTCHA solving."""
        if not HAS_PLAYWRIGHT:
            import webbrowser
            webbrowser.open(target_url)
            return

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

                context = p.chromium.launch_persistent_context(self.profile_dir, **launch_kwargs)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                
                # Keep open for up to 60 seconds or until user closes window
                for _ in range(60):
                    if page.is_closed():
                        break
                    time.sleep(1)
                try:
                    context.close()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"TikTok interactive session error: {e}")
            import webbrowser
            webbrowser.open(target_url)

    def resolve_store_info(self, raw_input: str) -> dict:
        """Parse TikTok Shop store URL, creator handle, or Global Search."""
        raw = raw_input.strip() if raw_input else ""
        if not raw:
            return {
                "store_name": "TikTok Shop Global Search",
                "seller": "",
                "is_store": False,
                "original": "https://shop.tiktok.com/us"
            }

        # 1. Check for product link
        m_pdp = re.search(r'/pdp/(?:[^/]+/)?(\d{15,25})', raw) or re.search(r'(\d{15,25})', raw)
        if m_pdp:
            p_id = m_pdp.group(1)
            return {
                "store_name": f"TikTok Product {p_id}",
                "seller": "",
                "is_store": False,
                "item_id": p_id,
                "original": raw
            }

        # 2. Check for creator handle e.g. @creator or tiktok.com/@creator
        m_at = re.search(r'@([a-zA-Z0-9_\-\.]+)', raw)
        if m_at:
            handle = m_at.group(1).strip()
            return {
                "store_name": f"@{handle}",
                "seller": handle,
                "is_store": True,
                "original": f"https://www.tiktok.com/@{handle}"
            }

        # 3. Check for Global keywords
        if any(g in raw.lower() for g in ("global", "marketplace", "all")) or raw.lower() in ("tiktok", "shop.tiktok.com", "https://shop.tiktok.com", "https://shop.tiktok.com/us"):
            return {
                "store_name": "TikTok Shop Global Search",
                "seller": "",
                "is_store": False,
                "original": "https://shop.tiktok.com/us"
            }

        clean = raw.split("/")[-1].split("?")[0].strip()
        return {
            "store_name": clean or "TikTok Shop",
            "seller": clean,
            "is_store": True,
            "original": raw if raw.startswith("http") else f"https://shop.tiktok.com/us/{clean}"
        }

    def fetch_single_listing(self, url: str) -> dict:
        """
        Fetch and parse a single TikTok Shop PDP URL.
        Extracts Title, Price, Seller, Location, Business Entity, Images, Sold count, and Item ID.
        """
        clean_url = url.strip()
        m_id = re.search(r'/pdp/(?:[^/]+/)?(\d{15,25})', clean_url)
        item_id = m_id.group(1) if m_id else ""
        if not item_id:
            m_alt = re.search(r'(\d{15,25})', clean_url)
            if m_alt: item_id = m_alt.group(1)

        html = ""
        # 1. Attempt fast HTTP via curl_cffi with Chrome impersonation
        try:
            if HAS_CURL_CFFI:
                session = curl_requests.Session(impersonate="chrome124")
            else:
                session = curl_requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            resp = session.get(clean_url, timeout=14)
            if resp.status_code == 200 and len(resp.text) > 1000:
                html = resp.text
        except Exception as e:
            logger.debug(f"TikTok HTTP fetch error: {e}")

        # 2. Fallback to Playwright if HTTP empty or blocked
        if not html and HAS_PLAYWRIGHT:
            try:
                edge_path = self._find_edge_path()
                with sync_playwright() as p:
                    launch_kwargs = {
                        "headless": self.headless,
                        "viewport": {"width": 1440, "height": 900},
                        "args": ["--disable-blink-features=AutomationControlled", "--no-first-run"]
                    }
                    if edge_path: launch_kwargs["executable_path"] = edge_path
                    else: launch_kwargs["channel"] = "msedge"

                    context = p.chromium.launch_persistent_context(self.profile_dir, **launch_kwargs)
                    page = context.pages[0] if context.pages else context.new_page()
                    page.goto(clean_url, wait_until="domcontentloaded", timeout=25000)
                    time.sleep(2.0)
                    html = page.content()
                    context.close()
            except Exception as e:
                logger.debug(f"TikTok Playwright fetch error: {e}")

        title = ""
        price = "$0.00"
        seller = "TikTok Shop Merchant"
        location = "United States"
        image_url = ""
        sold_count = ""
        business_entity = ""

        if html:
            soup = BeautifulSoup(html, "html.parser")

            # Title
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            if not title and soup.title:
                title = soup.title.string.replace(" - TikTok Shop", "").strip()
            if not title:
                h1 = soup.find("h1")
                if h1: title = h1.get_text(strip=True)

            # Price
            og_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
            if og_price and og_price.get("content"):
                try:
                    price = f"${float(og_price['content']):.2f}"
                except Exception:
                    price = f"${og_price['content']}"
            else:
                for el in soup.find_all(["span", "div"]):
                    txt = el.get_text(strip=True)
                    if re.match(r'^\$\d+(\.\d{2})?$', txt):
                        price = txt
                        break

            # Image
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                image_url = og_img["content"].strip()

            # Seller / Shop Name
            m_soldby = re.search(r'Sold by\s+([^<\n\r\t]+?)(?:18 sold|\d+\s*sold|<|\n|\t|$)', html, re.I)
            if m_soldby:
                seller = m_soldby.group(1).strip()
            else:
                for div in soup.find_all("div"):
                    txt = div.get_text(" ", strip=True)
                    if txt.startswith("Sold by "):
                        seller = txt.replace("Sold by ", "").split()[0].strip()
                        break

            # Sold Count
            m_sold = re.search(r'(\d[\d,.]*[kKmM]?\s*sold)', html, re.I)
            if m_sold:
                sold_count = m_sold.group(1).strip()

            # Business entity & address
            m_biz = re.search(r'Business name:\s*(?:<!-- -->)?([^<]+)</span>', html, re.I)
            if m_biz:
                business_entity = m_biz.group(1).strip()
            m_addr = re.search(r'Business address:\s*(?:<!-- -->)?([^<]+)</span>', html, re.I)
            if m_addr:
                b_addr = m_addr.group(1).strip()
                location = b_addr
                if any(c in b_addr.lower() for c in ("china", "guangdong", "guangzhou", "shenzhen", "zhejiang", "anhui", "hefei", "cn")):
                    location = f"China ({b_addr})"
                elif "united states" in b_addr.lower() or "usa" in b_addr.lower():
                    location = f"United States ({b_addr})"

        if not title:
            title = f"TikTok Shop Item #{item_id}" if item_id else f"TikTok Shop Listing ({clean_url[:45]}...)"

        return {
            "title": title,
            "item_id": item_id or re.sub(r'\W+', '', clean_url)[-18:],
            "url": clean_url,
            "price": price,
            "seller": seller,
            "location": location,
            "image_url": image_url,
            "sold_count": sold_count,
            "business_entity": business_entity,
            "marketplace": "shop.tiktok.com",
            "condition": "New"
        }

    def search(self, store_url: str = "", include_term: str = "",
               exclude_terms: list[str] = None,
               condition: str = "all",
               max_pages: int = 2,
               stop_event: threading.Event = None,
               pause_event: threading.Event = None,
               log_callback=None) -> list[dict]:
        """
        Search TikTok Shop or harvest creator showcase.
        Supports single PDP URL direct fetch or search queries across configurable depth pages.
        """
        items = []
        exclude_terms = [e.strip().lower() for e in (exclude_terms or []) if e.strip()]

        # If user passed direct PDP listing URL into store box
        if store_url and ("/pdp/" in store_url or re.search(r'\d{15,25}', store_url)):
            single = self.fetch_single_listing(store_url)
            if single and single.get("title"):
                items.append(single)
            return items

        # For keyword searches on TikTok Shop
        query = include_term.strip() if include_term and include_term != "*" else ""
        if not query and store_url:
            query = self.resolve_store_info(store_url).get("seller", "")

        if not query:
            return items

        # Search via Playwright in persistent profile
        if HAS_PLAYWRIGHT:
            try:
                edge_path = self._find_edge_path()
                with sync_playwright() as p:
                    launch_kwargs = {
                        "headless": self.headless,
                        "viewport": {"width": 1440, "height": 900},
                        "args": ["--disable-blink-features=AutomationControlled", "--no-first-run"]
                    }
                    if edge_path: launch_kwargs["executable_path"] = edge_path
                    else: launch_kwargs["channel"] = "msedge"

                    context = p.chromium.launch_persistent_context(self.profile_dir, **launch_kwargs)
                    page = context.pages[0] if context.pages else context.new_page()
                    
                    target_search_url = f"https://shop.tiktok.com/us/s?q={urllib.parse.quote_plus(query)}&source=ecommerce_mall&enter_method=search"
                    page.goto(target_search_url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3.0)

                    # Dynamic page depth & "View more" button pagination loop
                    target_max_items = max_pages * 50
                    max_scroll_cycles = max(14, max_pages * 8)
                    consecutive_no_change = 0
                    last_card_count = 0

                    for cycle in range(max_scroll_cycles):
                        if stop_event and stop_event.is_set():
                            break
                        if pause_event:
                            pause_event.wait()

                        # Count visible PDP / product cards
                        current_card_count = page.evaluate("""() => {
                            const seen = new Set();
                            document.querySelectorAll('a').forEach(a => {
                                const href = a.href || '';
                                const m = href.match(/\\/pdp\\/(?:[^/]+\\/)?(\\d{15,25})/) || href.match(/\\/product\\/(\\d{15,25})/) || href.match(/(\\d{17,21})/);
                                if (m && !href.includes('campaign') && !href.includes('seller-us') && !href.includes('account')) {
                                    seen.add(m[1]);
                                }
                            });
                            return seen.size;
                        }""")

                        if current_card_count > 0 and current_card_count == last_card_count:
                            consecutive_no_change += 1
                        else:
                            consecutive_no_change = 0
                        last_card_count = current_card_count

                        # Stop if we hit requested max_items depth or exhausted all results (4 consecutive stagnant cycles)
                        if current_card_count >= target_max_items or consecutive_no_change >= 4:
                            if consecutive_no_change >= 4:
                                break
                            if current_card_count >= target_max_items:
                                break

                        # 1. Scroll down towards bottom of page
                        page.evaluate("window.scrollBy(0, 1600);")
                        time.sleep(0.5)

                        # 2. Look for and click any "View more" / "Load more" / "See more" / "Show more" button
                        clicked = page.evaluate("""() => {
                            const candidates = Array.from(document.querySelectorAll('button, div[role="button"], a[role="button"], [class*="button"], [class*="btn"], [class*="viewMore"], [class*="loadMore"], [class*="load-more"], [class*="view-more"], [class*="showMore"], [class*="show-more"]'));
                            for (const b of candidates) {
                                const txt = (b.innerText || '').trim().toLowerCase();
                                if (txt === 'view more' || txt === 'see more' || txt === 'load more' || txt === 'show more' ||
                                    txt.includes('view more') || txt.includes('load more') || txt.includes('see more') || txt.includes('show more')) {
                                    b.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    b.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")

                        if clicked:
                            if log_callback and cycle % 3 == 0:
                                log_callback(f"  📄 [TikTok Shop] Clicked 'View more' pagination ({current_card_count} listings loaded)...")
                            time.sleep(1.5)
                        else:
                            time.sleep(0.7)

                    raw_cards = page.evaluate("""() => {
                        const res = [];
                        const seen = new Set();
                        document.querySelectorAll('a').forEach(a => {
                            const href = a.href || '';
                            const m = href.match(/\\/pdp\\/(?:[^/]+\\/)?(\\d{15,25})/) || href.match(/\\/product\\/(\\d{15,25})/) || href.match(/(\\d{17,21})/);
                            if (m && !seen.has(m[1]) && !href.includes('campaign') && !href.includes('seller-us') && !href.includes('account')) {
                                seen.add(m[1]);
                                let title = a.innerText.trim();
                                if (!title) {
                                    const h = a.querySelector('h1, h2, h3, [class*="title"], [class*="name"]');
                                    if (h) title = h.innerText.trim();
                                }
                                let imgUrl = '';
                                let seller = '';
                                let price = '$0.00';
                                let p = a;
                                for (let i = 0; i < 6; i++) {
                                    if (!p) break;
                                    if (!imgUrl) {
                                        const imgs = Array.from(p.querySelectorAll('img'));
                                        let bestImg = '';
                                        let bestScore = -1;
                                        for (const im of imgs) {
                                            let src = im.currentSrc || im.src || im.getAttribute('src') || im.getAttribute('data-src') || '';
                                            if (!src && im.srcset) {
                                                const parts = im.srcset.split(',');
                                                if (parts.length > 0) {
                                                    src = parts[parts.length - 1].trim().split(' ')[0];
                                                }
                                            }
                                            if (!src || src.startsWith('data:image/svg')) continue;

                                            const lowerSrc = src.toLowerCase();
                                            const alt = (im.alt || '').toLowerCase();
                                            const cls = (im.className || '').toLowerCase();
                                            const parentCls = (im.parentElement?.className || '').toLowerCase();

                                            // Exclude promotional badges, deal tags, icons, avatars, and watermarks
                                            if (lowerSrc.includes('badge') || lowerSrc.includes('avatar') || lowerSrc.includes('icon') ||
                                                lowerSrc.includes('watermark') || lowerSrc.includes('activity_tag') || lowerSrc.includes('promo_tag') ||
                                                cls.includes('badge') || cls.includes('avatar') || cls.includes('icon') || cls.includes('tag') ||
                                                parentCls.includes('badge') || parentCls.includes('avatar') || parentCls.includes('icon') || parentCls.includes('tag') ||
                                                alt.includes('badge') || alt.includes('avatar') || alt.includes('icon') || alt.includes('stock up') || alt.includes('deal')) {
                                                continue;
                                            }

                                            // Exclude tiny icon dimensions if computable
                                            const rect = im.getBoundingClientRect ? im.getBoundingClientRect() : null;
                                            const w = rect ? rect.width : (im.naturalWidth || im.width || 0);
                                            const h = rect ? rect.height : (im.naturalHeight || im.height || 0);
                                            if (w > 0 && w < 60 && h > 0 && h < 60) {
                                                continue;
                                            }

                                            let score = 10;
                                            if (lowerSrc.includes('ttcdn') || lowerSrc.includes('tos-') || lowerSrc.includes('tiktokcdn') || lowerSrc.includes('byteoversea')) score += 50;
                                            if (lowerSrc.includes('resize-webp') || lowerSrc.includes('tplv-')) score += 40;
                                            if (cls.includes('product') || cls.includes('main') || cls.includes('cover') || cls.includes('image')) score += 30;
                                            if (parentCls.includes('product') || parentCls.includes('cover') || parentCls.includes('image')) score += 20;
                                            if (w >= 100 || h >= 100) score += 30;
                                            if (w >= 200 || h >= 200) score += 20;

                                            if (score > bestScore) {
                                                bestScore = score;
                                                bestImg = src;
                                            }
                                        }
                                        if (bestImg) {
                                            imgUrl = bestImg;
                                        }
                                        if (!imgUrl) {
                                            const bgDiv = p.querySelector('[style*="background-image"]');
                                            if (bgDiv) {
                                                const bgMatch = bgDiv.style.backgroundImage.match(/url\\(["']?([^"']+)["']?\\)/);
                                                if (bgMatch && !bgMatch[1].toLowerCase().includes('badge') && !bgMatch[1].toLowerCase().includes('icon')) {
                                                    imgUrl = bgMatch[1];
                                                }
                                            }
                                        }
                                    }
                                    if (!seller) {
                                        const sEl = p.querySelector('[class*="shop-name"], [class*="seller-name"], [class*="store-name"], [class*="shopName"], [class*="sellerName"], a[href*="/@"], a[href*="/store/"], a[href*="/shop/"]');
                                        if (sEl) {
                                            const sTxt = sEl.innerText.trim();
                                            if (sTxt && !sTxt.toLowerCase().includes('sold') && !sTxt.toLowerCase().includes('ratings')) seller = sTxt;
                                        }
                                    }
                                    if (price === '$0.00') {
                                        const pMatch = p.innerText.match(/\\$\\s*\\d+(?:\\.\\d{2})?/);
                                        if (pMatch) price = pMatch[0];
                                    }
                                    p = p.parentElement;
                                }
                                if (!title) {
                                    title = `TikTok Product ${m[1]}`;
                                }
                                res.push({id: m[1], url: href, title: title, image_url: imgUrl, seller: seller, price: price});
                            }
                        });
                        return res;
                    }""")

                    for rc in raw_cards:
                        p_id = rc.get("id")
                        title = rc.get("title") or f"TikTok Product {p_id}"
                        href = rc.get("url")
                        img_url = rc.get("image_url", "")
                        s_name = rc.get("seller") or "TikTok Shop Merchant"
                        pr = rc.get("price") or "$0.00"

                        if exclude_terms and any(ex in title.lower() for ex in exclude_terms):
                            continue

                        items.append({
                            "title": title,
                            "item_id": p_id,
                            "url": href,
                            "price": pr,
                            "seller": s_name,
                            "location": "United States",
                            "image_url": img_url,
                            "marketplace": "shop.tiktok.com",
                            "condition": "New"
                        })
                    context.close()
            except Exception as e:
                logger.debug(f"TikTok search error: {e}")

        return items

    def enrich_seller_info(self, items: list[dict],
                           progress_callback=None,
                           stop_event: threading.Event = None) -> list[dict]:
        """Fetch and enrich exact TikTok Shop merchant names and business entities."""
        if not items:
            return items

        for idx, it in enumerate(items):
            if stop_event and stop_event.is_set():
                break

            url = it.get("url", "")
            if url:
                try:
                    pdp_info = self.fetch_single_listing(url)
                    if pdp_info:
                        if pdp_info.get("seller") and pdp_info.get("seller") != "TikTok Shop Merchant":
                            it["seller"] = pdp_info["seller"]
                        if pdp_info.get("price") and pdp_info.get("price") != "$0.00":
                            it["price"] = pdp_info["price"]
                        if pdp_info.get("business_entity"):
                            it["business_entity"] = pdp_info["business_entity"]
                        if pdp_info.get("location") and pdp_info.get("location") != "United States":
                            it["location"] = pdp_info["location"]
                        if pdp_info.get("sold_count"):
                            it["sold_count"] = pdp_info["sold_count"]
                except Exception as e:
                    logger.debug(f"Error enriching TikTok item {url}: {e}")

            if progress_callback:
                progress_callback(idx + 1, len(items), it)

        return items

    def compute_dhash(self, image: Image.Image) -> int:
        """Compute 64-bit difference hash (dHash) for fast visual clone matching."""
        if not HAS_PIL:
            return 0
        try:
            resized = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(resized.getdata())
            diff = []
            for row in range(8):
                for col in range(8):
                    diff.append(pixels[row * 9 + col] > pixels[row * 9 + col + 1])
            return sum([1 << i for i, b in enumerate(diff) if b])
        except Exception:
            return 0

    def hamming_distance(self, h1: int, h2: int) -> int:
        """Hamming distance between two 64-bit hashes."""
        return bin(h1 ^ h2).count("1")

    def find_connected_network(self, item_id: str, item_url: str = "", target_img_url: str = "") -> list[dict]:
        """
        On-Demand Visual Syndicate & Connected Seller Hunter for TikTok Shop.
        Scans TikTok PDP carousels & recommendations:
        - "Explore more from [seller]" (Seller's other shop listings)
        - "You may also like" (Algorithmically related / competitor products)
        - "Trending / Customers also viewed" (Syndicate & category products)
        Performs perceptual image matching against target_img_url.
        """
        if not item_url and item_id:
            item_url = f"https://shop.tiktok.com/us/pdp/product/{item_id}"
        if not item_id and item_url:
            m = re.search(r'/pdp/(?:[^/]+/)?(\d{15,25})', item_url) or re.search(r'(\d{15,25})', item_url)
            item_id = m.group(1) if m else ""

        discovered = []
        seen_ids = set([str(item_id)] if item_id else [])

        target_hash = None
        if target_img_url and str(target_img_url).startswith("http") and HAS_PIL:
            try:
                req = urllib.request.Request(str(target_img_url), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                    target_hash = self.compute_dhash(t_img)
            except Exception:
                pass

        if not HAS_PLAYWRIGHT or not item_url:
            return discovered

        try:
            edge_path = self._find_edge_path()
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": self.headless,
                    "viewport": {"width": 1440, "height": 900},
                    "args": ["--disable-blink-features=AutomationControlled", "--no-first-run"]
                }
                if edge_path:
                    launch_kwargs["executable_path"] = edge_path
                else:
                    launch_kwargs["channel"] = "msedge"

                context = p.chromium.launch_persistent_context(self.profile_dir, **launch_kwargs)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(item_url, wait_until="domcontentloaded", timeout=30000)

                extract_script = """() => {
                    const res = [];
                    const seen = new Set();

                    // 1. Identify carousel / recommendation sections
                    const sections = Array.from(document.querySelectorAll('section, div[class*="recommend"], div[class*="carousel"], div[class*="more-from"], div[class*="related"], div[class*="similar"], div[class*="container"]'));

                    for (const sec of sections) {
                        const hEl = sec.querySelector('h1, h2, h3, h4, [class*="title"], [class*="header"]');
                        const secTitle = hEl ? hEl.innerText.trim().toLowerCase() : '';
                        let secType = '👥 You May Also Like';

                        if (secTitle.includes('explore more from') || secTitle.includes('more from') || secTitle.includes('shop') || secTitle.includes('store')) {
                            secType = "🏪 Explore More From Seller";
                        } else if (secTitle.includes('you may also like') || secTitle.includes('similar') || secTitle.includes('recommended')) {
                            secType = "👥 You May Also Like";
                        } else if (secTitle.includes('trending') || secTitle.includes('popular') || secTitle.includes('bought')) {
                            secType = "⚔ Trending & Competitors";
                        }

                        const cards = sec.querySelectorAll('a');
                        for (const a of cards) {
                            const href = a.href || '';
                            const m = href.match(/\\/pdp\\/(?:[^/]+\\/)?(\\d{15,25})/) || href.match(/\\/product\\/(\\d{15,25})/) || href.match(/(\\d{17,21})/);
                            if (m && !seen.has(m[1]) && !href.includes('campaign') && !href.includes('seller-us') && !href.includes('account')) {
                                seen.add(m[1]);
                                let title = a.innerText.trim();
                                if (!title) {
                                    const h = a.querySelector('h1, h2, h3, [class*="title"], [class*="name"]');
                                    if (h) title = h.innerText.trim();
                                }
                                let imgUrl = '';
                                let seller = '';
                                let price = '$0.00';
                                let p = a;
                                for (let i = 0; i < 6; i++) {
                                    if (!p) break;
                                    if (!imgUrl) {
                                        const imgs = Array.from(p.querySelectorAll('img'));
                                        let bestImg = '';
                                        let bestScore = -1;
                                        for (const im of imgs) {
                                            let src = im.currentSrc || im.src || im.getAttribute('src') || im.getAttribute('data-src') || '';
                                            if (!src && im.srcset) {
                                                const parts = im.srcset.split(',');
                                                if (parts.length > 0) src = parts[parts.length - 1].trim().split(' ')[0];
                                            }
                                            if (!src || src.startsWith('data:image/svg')) continue;
                                            const lowerSrc = src.toLowerCase();
                                            const alt = (im.alt || '').toLowerCase();
                                            const cls = (im.className || '').toLowerCase();
                                            if (lowerSrc.includes('badge') || lowerSrc.includes('avatar') || lowerSrc.includes('icon') ||
                                                lowerSrc.includes('watermark') || lowerSrc.includes('activity_tag') || cls.includes('badge') ||
                                                cls.includes('avatar') || cls.includes('icon') || alt.includes('badge') || alt.includes('deal')) {
                                                continue;
                                            }
                                            let score = 10;
                                            if (lowerSrc.includes('ttcdn') || lowerSrc.includes('tos-') || lowerSrc.includes('tiktokcdn')) score += 50;
                                            if (lowerSrc.includes('resize-webp') || lowerSrc.includes('tplv-')) score += 40;
                                            if (score > bestScore) {
                                                bestScore = score;
                                                bestImg = src;
                                            }
                                        }
                                        if (bestImg) imgUrl = bestImg;
                                    }
                                    if (!seller) {
                                        const sEl = p.querySelector('[class*="shop-name"], [class*="seller-name"], [class*="store-name"], [class*="shopName"], [class*="sellerName"]');
                                        if (sEl) seller = sEl.innerText.trim();
                                    }
                                    if (price === '$0.00') {
                                        const pMatch = p.innerText.match(/\\$\\s*\\d+(?:\\.\\d{2})?/);
                                        if (pMatch) price = pMatch[0];
                                    }
                                    p = p.parentElement;
                                }
                                res.push({
                                    id: m[1],
                                    url: href,
                                    title: title || `TikTok Product ${m[1]}`,
                                    image_url: imgUrl,
                                    seller: seller,
                                    price: price,
                                    network_type: secType
                                });
                            }
                        }
                    }

                    // 2. Fallback sweep for any remaining uncaptured cards
                    const allLinks = Array.from(document.querySelectorAll('a'));
                    for (const a of allLinks) {
                        const href = a.href || '';
                        const m = href.match(/\\/pdp\\/(?:[^/]+\\/)?(\\d{15,25})/) || href.match(/\\/product\\/(\\d{15,25})/) || href.match(/(\\d{17,21})/);
                        if (m && !seen.has(m[1]) && !href.includes('campaign') && !href.includes('seller-us') && !href.includes('account')) {
                            seen.add(m[1]);
                            let title = a.innerText.trim();
                            let imgUrl = '';
                            let seller = '';
                            let price = '$0.00';
                            let p = a;
                            for (let i = 0; i < 6; i++) {
                                if (!p) break;
                                if (!imgUrl) {
                                    const imgs = Array.from(p.querySelectorAll('img'));
                                    for (const im of imgs) {
                                        let src = im.currentSrc || im.src || im.getAttribute('src') || '';
                                        if (src && !src.includes('badge') && !src.includes('icon') && !src.includes('avatar')) {
                                            imgUrl = src;
                                            break;
                                        }
                                    }
                                }
                                if (!seller) {
                                    const sEl = p.querySelector('[class*="shop-name"], [class*="seller-name"]');
                                    if (sEl) seller = sEl.innerText.trim();
                                }
                                if (price === '$0.00') {
                                    const pMatch = p.innerText.match(/\\$\\s*\\d+(?:\\.\\d{2})?/);
                                    if (pMatch) price = pMatch[0];
                                }
                                p = p.parentElement;
                            }
                            res.push({
                                id: m[1],
                                url: href,
                                title: title || `TikTok Product ${m[1]}`,
                                image_url: imgUrl,
                                seller: seller,
                                price: price,
                                network_type: "👥 You May Also Like"
                            });
                        }
                    }

                    return res;
                }"""

                # Auto-recover target image hash if not provided initially
                if not target_hash and HAS_PIL:
                    try:
                        target_img_src = page.evaluate("""() => {
                            const meta = document.querySelector('meta[property="og:image"]');
                            if (meta && meta.content) return meta.content;
                            return '';
                        }""")
                        if target_img_src and str(target_img_src).startswith("http"):
                            req = urllib.request.Request(str(target_img_src), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                            with urllib.request.urlopen(req, timeout=3) as r:
                                t_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                                target_hash = self.compute_dhash(t_img)
                    except Exception:
                        pass

                # Fast active carousel harvesting with inactivity early exit
                raw_carousels = []
                last_count = 0
                last_change_time = time.time()
                max_scan_duration = 5.0
                idle_threshold = 1.5
                start_scan = time.time()

                for step in range(8):
                    if time.time() - start_scan > max_scan_duration:
                        break
                    try:
                        page.evaluate(f"window.scrollBy(0, {(step + 1) * 600});")
                    except Exception:
                        pass
                    time.sleep(0.35)

                    try:
                        current_cards = page.evaluate(extract_script)
                    except Exception:
                        current_cards = []

                    if len(current_cards) > last_count:
                        last_count = len(current_cards)
                        last_change_time = time.time()
                        raw_carousels = current_cards
                    elif last_count > 0 and (time.time() - last_change_time >= idle_threshold):
                        break

                if not raw_carousels:
                    try:
                        raw_carousels = page.evaluate(extract_script)
                    except Exception:
                        pass

                # Close browser context immediately to release resources & close window
                try:
                    context.close()
                except Exception:
                    pass

                # Parallel dHash calculation for harvested cards
                card_similarities = {}
                if target_hash and raw_carousels and HAS_PIL:
                    def _calc_similarity(card):
                        c_id = str(card.get("id", "")).strip()
                        img_url = card.get("image_url", "")
                        default_lbl = card.get("network_type", "Carousel Asset")
                        if not img_url or not img_url.startswith("http"):
                            return c_id, default_lbl
                        try:
                            req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                            with urllib.request.urlopen(req, timeout=1.8) as r:
                                c_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                                c_hash = self.compute_dhash(c_img)
                                dist = self.hamming_distance(target_hash, c_hash)
                                if dist <= 8:
                                    return c_id, f"🎯 Exact Visual Clone (d={dist})"
                                elif dist <= 16:
                                    return c_id, f"🖼 Visual Match (d={dist})"
                        except Exception:
                            pass
                        return c_id, default_lbl

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [executor.submit(_calc_similarity, c) for c in raw_carousels]
                        for f in as_completed(futures):
                            try:
                                cid, sim = f.result()
                                card_similarities[cid] = sim
                            except Exception:
                                pass

                # Process harvested cards and build results
                for card in raw_carousels:
                    c_id = str(card.get("id", "")).strip()
                    if c_id in seen_ids:
                        continue
                    seen_ids.add(c_id)

                    img_url = card.get("image_url", "")
                    similarity_lbl = card_similarities.get(c_id, card.get("network_type", "Carousel Asset"))
                    s_name = card.get("seller") or "TikTok Shop Merchant"

                    discovered.append({
                        "brand": "",
                        "product_type": "",
                        "title": card.get("title") or f"TikTok Listing #{c_id}",
                        "item_id": c_id,
                        "price": card.get("price") or "$0.00",
                        "seller": s_name,
                        "location": "United States",
                        "seller_origin": "United States",
                        "threat_badge": "🚨 Visual Syndicate" if "Exact" in similarity_lbl else ("🏪 Same Store" if "Seller" in similarity_lbl else ""),
                        "image_url": img_url,
                        "url": card.get("url"),
                        "marketplace": "shop.tiktok.com",
                        "condition": card.get("network_type", "Connected Listing"),
                        "similarity": similarity_lbl,
                        "match_type": card.get("network_type", "Connected Listing")
                    })

        except Exception as e:
            logger.debug(f"Error scanning TikTok carousels for {item_url}: {e}")

        return discovered

    def scan_listing_carousels(self, item_id: str, item_url: str = "", target_img: str = "") -> list[dict]:
        """Alias for find_connected_network for standardized carousel scanner dispatch."""
        return self.find_connected_network(item_id, item_url, target_img)
