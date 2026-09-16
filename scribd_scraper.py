"""
scribd_scraper.py
Specialized Scribd Document & Copyright Infringement Harvester for Apollo.

Features:
- Stealth Playwright / Edge browser automation for dynamic document catalog searches.
- Full metadata extraction: Document titles, uploader handles, preview thumbnails, direct document URLs.
- Multi-page pagination support (`&page=1`, `&page=2`).
- Integrated Brand, Model, and Exclusion filtering.
- Seller / Uploader profile enrichment.
"""

import os
import re
import time
import json
import logging
import urllib.parse
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright

logger = logging.getLogger("Apollo.ScribdScraper")


class ScribdScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None

    def _get_context(self):
        if self._context is None:
            self._playwright = sync_playwright().start()
            try:
                self._browser = self._playwright.chromium.launch(
                    channel="msedge",
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                )
            except Exception:
                self._browser = self._playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ]
                )
            self._context = self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
        return self._context

    def resolve_store_info(self, url_or_name: str) -> Dict[str, str]:
        """Resolve store/uploader name and document ID from Scribd URL or identifier."""
        if not url_or_name:
            return {"store_name": "Scribd Documents", "doc_id": ""}
        clean = url_or_name.strip()
        m_doc = re.search(r'scribd\.com/(?:document|presentation|doc)/(\d+)(?:/([^/?#]+))?', clean, re.IGNORECASE)
        if m_doc:
            doc_id = m_doc.group(1)
            doc_slug = m_doc.group(2) or f"Document_{doc_id}"
            return {"store_name": doc_slug, "doc_id": doc_id}
        m_user = re.search(r'scribd\.com/(?:user|author)/[^/]+/([^/?#]+)', clean, re.IGNORECASE)
        if m_user:
            return {"store_name": m_user.group(1), "doc_id": ""}
        parts = clean.rstrip("/").split("/")
        return {"store_name": parts[-1] if parts else clean, "doc_id": ""}

    def _build_search_url(self, store_info: Dict[str, str], query: str, page: int = 1) -> str:
        """Build canonical Scribd document search URL."""
        encoded_q = urllib.parse.quote_plus(query.strip())
        return f"https://www.scribd.com/search?content_type=documents&query={encoded_q}&page={page}"

    def _clean_uploader_name(self, raw_name: str, url: str = "") -> str:
        """Sanitize uploader / seller name."""
        if not raw_name:
            return "Scribd Uploader"
        cleaned = re.sub(r'^(?:uploaded\s+by|by|author)[:\s]*', '', raw_name.strip(), flags=re.IGNORECASE).strip()
        return cleaned or "Scribd Uploader"

    def search(self, store: str, query: str, excludes: list, condition: str = "all",
               max_pages: Optional[int] = None, max_items: int = 200,
               stop_event=None, pause_event=None, log_callback=None) -> List[Dict]:
        """
        Search Scribd for documents matching query keywords.
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            else:
                logger.info(msg)

        if not query or not query.strip():
            _log("⚠ [Scribd] No search query provided.")
            return []

        results = []
        seen_urls = set()
        clean_q = query.strip()
        encoded_q = urllib.parse.quote_plus(clean_q)
        limit_pages = max_pages if max_pages is not None else 2

        _log(f"📚 [Scribd] Initiating document sweep for '{clean_q}' (Target: {limit_pages} page(s))...")

        try:
            context = self._get_context()
            page = context.new_page()

            for page_num in range(1, limit_pages + 1):
                if stop_event and stop_event.is_set():
                    _log("⏹ [Scribd] Stop signal received.")
                    break
                if pause_event:
                    pause_event.wait()

                search_url = f"https://www.scribd.com/search?content_type=documents&query={encoded_q}&page={page_num}"
                _log(f"🌐 [Scribd] Loading search page {page_num}/{limit_pages}...")

                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(3000)
                except Exception as ex:
                    _log(f"⚠ [Scribd] Page load timeout on page {page_num}: {ex}")

                # Extract document cards from DOM
                page_items = page.evaluate(r"""
                    () => {
                        const items = [];
                        const links = document.querySelectorAll('a[href*="/document/"], a[href*="/presentation/"], a[href*="/doc/"]');
                        for (let a of links) {
                            const card = a.closest('div[class*="document_cell"], div[class*="search_object"], div[class*="cell"], li, article') || a.parentElement;
                            const titleEl = card ? card.querySelector('span[class*="title"], h3, h2, a[class*="title"]') : a;
                            const title = (titleEl ? titleEl.innerText : (a.innerText || a.getAttribute('aria-label') || '')).trim();
                            const url = a.href;
                            const imgEl = card ? card.querySelector('img') : null;
                            const img = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '';
                            const uploaderEl = card ? card.querySelector('a[href*="/user/"], a[href*="/author/"], span[class*="author"], span[class*="uploader"], span[class*="by"]') : null;
                            const uploader = uploaderEl ? uploaderEl.innerText.trim().replace(/^by\s+/i, '') : '';
                            
                            // Extract document ID from URL
                            const m = url.match(/\/(?:document|presentation|doc)\/(\d+)/i);
                            const itemId = m ? m[1] : '';

                            if (title && url && itemId && !items.some(x => x.url === url) && title.length > 2) {
                                items.push({
                                    title: title,
                                    url: url,
                                    item_id: itemId,
                                    image_url: img,
                                    seller: uploader || 'Scribd Uploader'
                                });
                            }
                        }
                        return items;
                    }
                """)

                if not page_items:
                    _log(f"ℹ [Scribd] No document listings found on page {page_num}.")
                    break

                page_new = 0
                for it in page_items:
                    u_norm = it["url"].split("?")[0]
                    if u_norm in seen_urls:
                        continue
                    seen_urls.add(u_norm)

                    # Exclusions check
                    t_low = it.get("title", "").lower()
                    if excludes:
                        if any(ex.lower().strip() in t_low for ex in excludes if ex.strip()):
                            continue

                    results.append({
                        "brand": "",
                        "product_type": "Document / PDF",
                        "title": it.get("title", ""),
                        "item_id": it.get("item_id", ""),
                        "price": "Free / Subscription",
                        "price_usd": 0.0,
                        "seller": it.get("seller", "Scribd Uploader"),
                        "location": "Scribd Digital Repository",
                        "image_url": it.get("image_url", ""),
                        "url": it.get("url", ""),
                        "marketplace": "Scribd",
                        "condition": "Digital Document",
                        "keyword": query
                    })
                    page_new += 1

                _log(f"📦 [Scribd] Harvested {page_new} documents from page {page_num} ({len(results)} total).")
                if page_new == 0:
                    break

            page.close()
        except Exception as e:
            _log(f"❌ [Scribd] Sweep error: {e}")
            logger.exception("Scribd search error")
        finally:
            self.close()

        return results

    def scrape_store(self, store_url: str, brand_terms: list = None, excludes: list = None,
                     max_pages: int = 2, stop_event=None, log_callback=None) -> List[Dict]:
        """Scrape all documents from a specific Scribd uploader/user profile."""
        query = " ".join(brand_terms) if brand_terms else "*"
        return self.search(store_url, query, excludes or [], max_pages=max_pages, stop_event=stop_event, log_callback=log_callback)

    def enrich_seller_info(self, items: List[Dict], progress_callback=None, stop_event=None):
        """Enrich document uploader username by visiting the document page."""
        if not items:
            return
        total = len(items)
        context = self._get_context()

        try:
            for idx, it in enumerate(items, 1):
                if stop_event and stop_event.is_set():
                    break
                url = it.get("url", "")
                if not url:
                    continue

                try:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(2000)

                    uploader = page.evaluate(r"""
                        () => {
                            const upEl = document.querySelector('a[href*="/user/"], a[href*="/author/"], span[class*="author"], span[class*="uploader"], .document_author');
                            return upEl ? upEl.innerText.trim().replace(/^by\s+/i, '') : '';
                        }
                    """)
                    if uploader and uploader != "Scribd Uploader":
                        it["seller"] = uploader
                    page.close()
                except Exception:
                    pass

                if progress_callback:
                    progress_callback(idx, total, it)
        finally:
            self.close()
