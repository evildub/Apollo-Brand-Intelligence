import re
import json
import logging
import urllib.parse
import urllib.request
import threading
from typing import List, Dict, Optional

logger = logging.getLogger("Apollo.ShopifyScraper")

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    import requests as curl_requests


class ShopifyScraper:
    """
    High-performance scraper for Shopify storefronts and global Shopify brand discovery.
    Supports:
      1. Direct Store Dredging (/products.json & /search/suggest.json)
      2. Global Shopify Brand Discovery (site:myshopify.com ecosystem sweeps)
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.name = "Shopify"
        self.session = curl_requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _log(self, msg: str, callback=None):
        if callback:
            try:
                callback(msg)
            except Exception:
                pass
        logger.info(msg)

    def resolve_store_info(self, raw_input: str) -> dict:
        """Resolve store input into canonical domain and display label."""
        if not raw_input:
            return {"store_name": "Shopify Ecosystem", "domain": "myshopify.com", "url": "https://myshopify.com"}

        clean = raw_input.strip()
        if any(w in clean.lower() for w in ("global", "full search", "all products", "shopify brand search", "shopify search")):
            return {"store_name": "Shopify Ecosystem", "domain": "myshopify.com", "url": "https://myshopify.com"}

        # Extract domain from URL or raw text
        domain_match = re.search(r'(?:https?://)?([^/\s:]+)', clean)
        domain = domain_match.group(1).lower() if domain_match else clean.lower()
        domain = re.sub(r'^www\.', '', domain)

        return {
            "store_name": domain,
            "domain": domain,
            "url": f"https://{domain}" if not clean.startswith("http") else clean
        }

    def _fetch_store_products(self, domain: str, term: str = "", limit: int = 50, stop_event=None) -> List[Dict]:
        """Fetch products directly from a Shopify storefront via /products.json or /search/suggest.json."""
        items = []
        clean_domain = re.sub(r'^https?://', '', domain).split('/')[0]

        # 1. First attempt: /search/suggest.json if a search term is specified
        if term and term.strip() and term != "*":
            q_enc = urllib.parse.quote(term.strip())
            suggest_url = f"https://{clean_domain}/search/suggest.json?q={q_enc}&resources[type]=product&resources[limit]={limit}"
            try:
                if HAS_CURL_CFFI:
                    resp = self.session.get(suggest_url, headers=self.headers, impersonate="chrome110", timeout=8)
                else:
                    resp = self.session.get(suggest_url, headers=self.headers, timeout=8)

                if resp.status_code == 200:
                    data = resp.json()
                    prods = data.get("resources", {}).get("results", {}).get("products", [])
                    for p in prods:
                        if stop_event and stop_event.is_set():
                            break
                        pid = str(p.get("id") or "")
                        title = p.get("title") or ""
                        price_raw = p.get("price") or ""
                        price = f"${float(price_raw):.2f}" if price_raw else ""
                        img = p.get("image") or p.get("featured_image", {}).get("url", "")
                        p_url = p.get("url") or f"/products/{p.get('handle', '')}"
                        if p_url.startswith("/"):
                            p_url = f"https://{clean_domain}{p_url}"

                        vendor = p.get("vendor") or clean_domain

                        items.append({
                            "item_id": pid or re.sub(r'[^a-zA-Z0-9]', '', p_url)[-12:],
                            "title": title,
                            "price": price,
                            "image_url": img,
                            "seller": vendor,
                            "url": p_url,
                            "marketplace": "Shopify",
                            "store": clean_domain
                        })
                    if items:
                        return items
            except Exception as e:
                logger.debug(f"Shopify suggest.json error on {clean_domain}: {e}")

        # 2. Second attempt: /products.json catalog sweep
        p_json_url = f"https://{clean_domain}/products.json?limit=250"
        try:
            if HAS_CURL_CFFI:
                resp = self.session.get(p_json_url, headers=self.headers, impersonate="chrome110", timeout=8)
            else:
                resp = self.session.get(p_json_url, headers=self.headers, timeout=8)

            if resp.status_code == 200:
                data = resp.json()
                raw_prods = data.get("products", [])
                t_low = term.lower().strip() if term and term != "*" else ""

                for p in raw_prods:
                    if stop_event and stop_event.is_set():
                        break
                    title = p.get("title", "")
                    vendor = p.get("vendor", "") or clean_domain
                    body = p.get("body_html", "") or ""
                    tags = p.get("tags", [])
                    if isinstance(tags, str):
                        tags = [tags]
                    tag_str = " ".join(str(tg) for tg in tags).lower()

                    # Filter by term if provided
                    if t_low:
                        combined_text = f"{title} {vendor} {tag_str}".lower()
                        if t_low not in combined_text:
                            continue

                    pid = str(p.get("id", ""))
                    handle = p.get("handle", "")
                    p_url = f"https://{clean_domain}/products/{handle}"

                    # Extract price from variants
                    price = ""
                    variants = p.get("variants", [])
                    if variants:
                        v_prices = []
                        for v in variants:
                            try:
                                v_prices.append(float(v.get("price", 0)))
                            except (ValueError, TypeError):
                                pass
                        if v_prices:
                            price = f"${min(v_prices):.2f}"

                    # Extract image
                    img = ""
                    images = p.get("images", [])
                    if images:
                        img = images[0].get("src", "")

                    items.append({
                        "item_id": pid or re.sub(r'[^a-zA-Z0-9]', '', p_url)[-12:],
                        "title": title,
                        "price": price,
                        "image_url": img,
                        "seller": vendor,
                        "url": p_url,
                        "marketplace": "Shopify",
                        "store": clean_domain
                    })
                    if len(items) >= limit:
                        break
        except Exception as e:
            logger.debug(f"Shopify products.json error on {clean_domain}: {e}")

        return items

    def _discover_shopify_stores(self, term: str, max_stores: int = 15, stop_event=None) -> List[str]:
        """Discover active myshopify.com stores selling the target brand keyword via Brave Search index."""
        discovered_stores = set()
        query = f"site:myshopify.com {term}"
        url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"

        try:
            if HAS_CURL_CFFI:
                resp = self.session.get(url, headers=self.headers, impersonate="chrome110", timeout=10)
            else:
                resp = self.session.get(url, headers=self.headers, timeout=10)

            if resp.status_code == 200:
                matches = re.findall(r'https?://([a-zA-Z0-9.-]+\.myshopify\.com)', resp.text)
                for m in matches:
                    dom = m.lower()
                    if "cdn" not in dom and "help" not in dom and "community" not in dom:
                        discovered_stores.add(dom)
                        if len(discovered_stores) >= max_stores:
                            break
        except Exception as e:
            logger.debug(f"Brave search error discovering Shopify stores: {e}")

        return list(discovered_stores)

    def search(self, store_raw: str, term: str, excludes: list = None,
               condition: str = "all", stop_event=None, pause_event=None,
               log_callback=None, max_items: int = 50) -> List[Dict]:
        """
        Execute Shopify search.
        Handles both individual storefront dredging and global brand sweeps across Shopify stores.
        """
        excludes = excludes or []
        items = []
        seen_keys = set()
        store_info = self.resolve_store_info(store_raw)
        is_global = store_info["store_name"] == "Shopify Ecosystem" or any(g in str(store_raw).lower() for g in ("global", "full search", "ecosystem"))

        if is_global:
            self._log(f"🌐 [Shopify Ecosystem Discovery] Sweeping Shopify network for '{term}'...", log_callback)
            stores = self._discover_shopify_stores(term, max_stores=10, stop_event=stop_event)
            if not stores:
                self._log(f"  ℹ No active Shopify storefronts discovered matching '{term}'.", log_callback)
                return []

            self._log(f"  🎯 Identified {len(stores)} active Shopify storefront(s) carrying '{term}'. Dredging catalogs...", log_callback)
            for s_dom in stores:
                if stop_event and stop_event.is_set():
                    break
                if pause_event:
                    pause_event.wait()

                s_items = self._fetch_store_products(s_dom, term=term, limit=10, stop_event=stop_event)
                for itm in s_items:
                    k = itm.get("url") or itm.get("item_id")
                    if k and k not in seen_keys:
                        seen_keys.add(k)
                        items.append(itm)
                if len(items) >= max_items:
                    break
        else:
            domain = store_info["domain"]
            self._log(f"🛍️ [Shopify Store Dredge] Sweeping catalog for {domain} (Term: '{term}')...", log_callback)
            items = self._fetch_store_products(domain, term=term, limit=max_items, stop_event=stop_event)

        # Apply user exclusions
        final_items = []
        for itm in items:
            t_low = itm.get("title", "").lower()
            if any(ex.lower() in t_low for ex in excludes if ex.strip()):
                continue
            final_items.append(itm)

        return final_items
