"""
Etsy Commercial Scale Dredge & High-Volume Infringement Scraper.
Author: Apollo Brand Intelligence Suite 2.1
Features:
  - Deep search with automated DataDome / Playwright stealth context.
  - Commercial Scale Filter: Automatically suppresses single-item / 1-of-1 / handpicked
    vintage closet items, routing them to the suppressed fluff tier so the main
    queue strictly targets commercial counterfeiters (multi-quantity stock, vinyl decals,
    CNC badges, and high-volume POD apparel).
  - Extracts listing ID, shop name, sales badges, review volume, and image assets.
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

logger = logging.getLogger("EtsyScraper")

# Keywords indicating commercial reproduction / mass manufacturing
COMMERCIAL_KEYWORDS = [
    "decal", "decals", "sticker", "stickers", "badge", "badges", "emblem", "emblems",
    "vinyl", "t-shirt", "tee", "hoodie", "apparel", "reproduction", "custom fit",
    "laser cut", "cnc", "3d print", "3d printed", "replacement", "wholesale"
]


class EtsyScraper:
    """Etsy Search & Commercial Scale Enforcement Dredge."""

    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self.user_dir = os.path.abspath("data/etsy_session")
        os.makedirs(self.user_dir, exist_ok=True)

    def _get_context(self, p):
        """Create or reuse persistent browser context with stealth scripts."""
        extra_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
        if self.headless:
            extra_args.append("--window-position=-2400,-2400")

        context = p.chromium.launch_persistent_context(
            self.user_dir,
            headless=False if self.headless else False,
            channel="msedge",
            args=extra_args,
            viewport={"width": 1366, "height": 768}
        )
        return context

    def search(
        self,
        query: str,
        depth_pages: int = 2,
        commercial_only: bool = True,
        store_filter: Optional[str] = None,
        condition: str = "all",
        status_callback=None,
        log_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Execute deep keyword search across Etsy with commercial scale filtering.
        """
        results = []
        clean_q = query.strip()
        if not clean_q:
            return results

        # Sanitize store_filter placeholder
        if store_filter and any(k in store_filter.lower() for k in ("global", "search", "all", "commercial makers", "makers")):
            store_filter = None

        def _log(msg):
            logger.info(msg)
            if log_callback: log_callback(msg)

        def _status(msg):
            if status_callback: status_callback(msg)

        _log(f"🧶 [Etsy] Starting Commercial Scale Dredge for '{clean_q}' (Depth: {depth_pages} page(s))...")

        seen_urls = set()

        try:
            with sync_playwright() as p:
                context = self._get_context(p)
                page = context.pages[0] if context.pages else context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

                for page_num in range(1, depth_pages + 1):
                    enc_q = urllib.parse.quote_plus(clean_q)
                    search_url = f"https://www.etsy.com/search?q={enc_q}&page={page_num}&ref=pagination"
                    if store_filter:
                        clean_store = store_filter.strip().lstrip("@")
                        search_url = f"https://www.etsy.com/shop/{clean_store}?search_query={enc_q}&page={page_num}"

                    _status(f"Etsy: Fetching page {page_num}/{depth_pages}...")
                    _log(f"🌐 [Etsy] Navigating: {search_url}")

                    try:
                        page.goto(search_url, timeout=35000, wait_until="domcontentloaded")
                        time.sleep(3)
                    except Exception as ge:
                        _log(f"⚠ [Etsy] Page {page_num} load timeout: {ge}")

                    # Scroll to trigger lazy loading of search results
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                        time.sleep(1.2)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1.2)
                    except Exception:
                        pass

                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Check for DataDome or Cloudflare block
                    if "Just a moment..." in page.title() or "datadome" in html.lower()[:500]:
                        _log("🚨 [Etsy] DataDome verification challenge encountered. Connect via Settings > Session Vault.")
                        break

                    cards = soup.select(".v2-listing-card, .wt-grid__item-xs-6, [data-search-results-container] li, .listing-link")
                    if not cards:
                        cards = soup.select("a[href*='/listing/']")

                    _log(f"🔎 [Etsy] Page {page_num}: Found {len(cards)} card elements.")

                    page_items = 0
                    for card in cards:
                        item = self._parse_card(card)
                        if item and item["url"] not in seen_urls:
                            if store_filter:
                                sf_clean = store_filter.strip().lower().lstrip("@")
                                if sf_clean not in str(item.get("seller", "")).lower():
                                    continue

                            # Apply Commercial Scale Filter
                            is_commercial = self._is_commercial_scale(item)
                            if commercial_only and not is_commercial:
                                # Suppress 1-of-1 / handpicked items to benign/fluff tier
                                item["visual_benign"] = True
                                item["threat_badge"] = "⚪ Handpicked / Single Item (Suppressed)"
                                item["threat_intel"] = "Suppressed 1-of-1 Closet Listing"

                            seen_urls.add(item["url"])
                            results.append(item)
                            page_items += 1

                    _log(f"✅ [Etsy] Page {page_num}: Ingested {page_items} listings.")

                    if len(cards) == 0:
                        break

                context.close()
        except Exception as e:
            _log(f"❌ [Etsy] Scraper error: {e}")

        _log(f"🛡 [Etsy] Ingested {len(results)} total listings for '{clean_q}'.")
        return results

    def _parse_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse Etsy listing card into normalized Apollo listing dict."""
        try:
            link_tag = card.select_one("a[href*='/listing/']") if card.name != "a" else card
            if not link_tag:
                return None

            href = link_tag.get("href", "")
            if not href or "/listing/" not in href:
                return None

            url = urllib.parse.urljoin("https://www.etsy.com", href.split("?")[0])

            # Extract Listing ID
            item_id = ""
            m = re.search(r"/listing/(\d+)", href)
            if m:
                item_id = m.group(1)
            else:
                item_id = str(abs(hash(url)) % 1000000000)

            # Title Extraction & Deep Cleanup
            title_tag = card.select_one(".v2-listing-card__title, h3, .wt-text-caption, a[title]")
            raw_title = ""
            if title_tag:
                t_copy = BeautifulSoup(str(title_tag), "html.parser")
                for sr in t_copy.select(".wt-screen-reader-only"):
                    sr.decompose()
                raw_title = t_copy.get_text(strip=True)
            elif link_tag and link_tag.get("title"):
                raw_title = link_tag.get("title", "").strip()

            if not raw_title and link_tag:
                l_copy = BeautifulSoup(str(link_tag), "html.parser")
                for sr in l_copy.select(".wt-screen-reader-only, .wt-badge, .currency-value, .money, .v2-listing-card__shop, [class*='shop'], [class*='price']"):
                    sr.decompose()
                raw_title = l_copy.get_text(strip=True)

            if not raw_title or raw_title.lower() in ("bestseller", "popular now", "free shipping", "in demand", "ad", "sale", "in high demand", "more like this"):
                slug = url.rstrip("/").split("/")[-1]
                raw_title = slug.replace("-", " ").title()

            # Clean trailing seller, ad, or shop noise if concatenated in title
            if raw_title:
                if "·" in raw_title:
                    raw_title = raw_title.split("·")[0].strip()
                raw_title = re.sub(r"from\s+shop[\s:-]+.*$", "", raw_title, flags=re.IGNORECASE).strip()
                raw_title = re.sub(r"\bAd\s*[-–—:]?\s*(by\s+Etsy\s+seller|from\s+Etsy\s+seller|by|from)?\b.*$", "", raw_title, flags=re.IGNORECASE).strip()
                raw_title = re.sub(r"^[·\s\-_:,\(\)\[\]]+|[·\s\-_:,\(\)\[\]]+$", "", raw_title).strip()

            # Shop Name / Seller Extraction & Deep Cleanup
            shop_tag = card.select_one(".v2-listing-card__shop, [data-seller-name-container], .streamline-seller-shop-name__line-height, p[class*='shop'], a[href*='/shop/']")
            shop_id = card.get("data-shop-id", "")
            seller = ""

            shop_link = card.select_one("a[href*='/shop/']")
            if shop_link:
                m_shop = re.search(r"/shop/([^/?#]+)", shop_link.get("href", ""))
                if m_shop:
                    seller = m_shop.group(1).strip()

            if not seller and shop_tag:
                s_copy = BeautifulSoup(str(shop_tag), "html.parser")
                for sr in s_copy.select(".wt-screen-reader-only"):
                    sr.decompose()
                seller = s_copy.get_text(strip=True)

            if seller:
                seller = re.sub(r"from\s+shop[\s:-]+.*$", "", seller, flags=re.IGNORECASE)
                seller = re.sub(r"\bAd\s*[-–—:]?\s*(by\s+Etsy\s+seller|from\s+Etsy\s+seller|by|from)?\b", "", seller, flags=re.IGNORECASE)
                seller = re.sub(r"\bEtsy\s+seller\b", "", seller, flags=re.IGNORECASE)
                seller = re.sub(r"^by\s*[\(:\[]?", "", seller, flags=re.IGNORECASE)
                seller = re.sub(r"^[·\s\-_:,\(\)\[\]]+|[·\s\-_:,\(\)\[\]]+$", "", seller).strip()
                
                # Deduplicate if concatenated (e.g. "VroomKeysVroomKeys" -> "VroomKeys")
                if len(seller) >= 4 and len(seller) % 2 == 0:
                    half = len(seller) // 2
                    if seller[:half].lower() == seller[half:].lower():
                        seller = seller[:half]

            if not seller or len(seller) < 2 or "shipping" in seller.lower() or seller.lower() in ("ad by", "ad", "by"):
                if shop_id:
                    seller = f"Etsy Shop #{shop_id}"
                else:
                    seller = "Etsy Merchant"

            # Price
            price_tag = card.select_one(".currency-value, .wt-text-title-01, .money")
            price = "$15.00"
            if price_tag:
                p_text = price_tag.get_text(strip=True)
                p_match = re.search(r"\d+(\.\d{2})?", p_text)
                if p_match:
                    price = f"${p_match.group(0)}"

            # Badges (Bestseller, Star Seller, In Demand)
            badges = []
            if card.select(".wt-badge--status-02, .wt-badge"):
                for b in card.select(".wt-badge"):
                    badges.append(b.get_text(strip=True))

            badge_str = " | ".join(badges) if badges else ""

            # Thumbnail Image
            img_url = ""
            all_imgs = card.select("img[src], img[data-src], img[data-preload-lp-src], img[data-src-delay]")
            for im in all_imgs:
                src = im.get("data-preload-lp-src") or im.get("data-src") or im.get("data-src-delay") or im.get("src") or ""
                if src.startswith("//"):
                    src = "https:" + src
                if src and not src.lower().endswith(".svg") and "icon" not in src.lower():
                    img_url = src
                    break

            threat_badge = "🧶 Commercial Scale (Etsy)"
            if "Bestseller" in badge_str or "Popular" in badge_str:
                threat_badge = "🔥 Bestseller Scale (Etsy)"

            return {
                "title": raw_title,
                "url": url,
                "item_id": str(item_id),
                "price": price,
                "seller": seller,
                "location": "United States / Global Maker",
                "marketplace": "etsy.com",
                "marketplace_code": "etsy.com",
                "image_url": img_url,
                "thumbnail": img_url,
                "threat_badge": threat_badge,
                "threat_intel": f"Commercial Merchant ({badge_str})" if badge_str else "Commercial Merchant",
                "product_type": "Custom Goods & Repro",
                "brand": "Unknown"
            }
        except Exception:
            return None

    def _is_commercial_scale(self, item: Dict[str, Any]) -> bool:
        """
        Determines whether listing is commercial manufacturing vs handpicked single-item.
        """
        title_lower = str(item.get("title", "")).lower()
        intel_lower = str(item.get("threat_intel", "")).lower()

        # Check for commercial keywords
        for kw in COMMERCIAL_KEYWORDS:
            if kw in title_lower:
                return True

        # Check for volume sales badges
        if any(b in intel_lower for b in ["bestseller", "popular", "star seller", "in demand", "sales"]):
            return True

        # If title contains explicit "1 of 1", "vintage single", "one-of-a-kind" -> classify non-commercial
        if any(w in title_lower for w in ["one of a kind", "1 of 1", "handpicked used", "pre-owned single"]):
            return False

        # Default assumption on e-commerce search is commercial reproduction
        return True