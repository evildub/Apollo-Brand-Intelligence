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
import json
import time
import random
import logging
import threading
import urllib.parse
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

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

    def search(self, store_url: str, include_term: str,
               exclude_terms: list[str] = None,
               condition: str = "all",
               stop_event: threading.Event = None,
               pause_event: threading.Event = None) -> list[dict]:
        """
        Search TikTok Shop or harvest creator showcase.
        Supports single PDP URL direct fetch or search queries.
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

                    # Adaptive deep scroll & "View more" click pagination loop
                    max_scroll_cycles = 16
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

                        # If we have reached a generous amount (100+) or no new items after 3 attempts, finish
                        if current_card_count >= 100 or consecutive_no_change >= 3:
                            if consecutive_no_change >= 3:
                                break

                        # 1. Scroll down
                        page.evaluate("window.scrollBy(0, 1600);")
                        time.sleep(0.6)

                        # 2. Look for and click any "View more" / "Load more" / "See more" / "Show more" button
                        clicked = page.evaluate("""() => {
                            const candidates = Array.from(document.querySelectorAll('button, div[role="button"], a[role="button"], [class*="button"], [class*="btn"], [class*="viewMore"], [class*="loadMore"], [class*="load-more"], [class*="view-more"]'));
                            for (const b of candidates) {
                                const txt = (b.innerText || '').trim().toLowerCase();
                                if (txt === 'view more' || txt === 'see more' || txt === 'load more' || txt === 'show more' ||
                                    txt.includes('view more') || txt.includes('load more') || txt.includes('see more')) {
                                    b.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    b.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")

                        if clicked:
                            time.sleep(1.5)
                        else:
                            time.sleep(0.8)

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
