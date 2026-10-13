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


OEM_SPEC_PATTERNS = [
    # GMW standards (strictly GMW + 3 to 5 digits, e.g. GMW14872, GMW 3044, GMW-3172)
    (re.compile(r'\bGMW\s*[-_]?\s*(\d{3,5})\b', re.IGNORECASE), "General Motors", "GMW"),
    # GM legacy standards: GM4350M, GME00201, GMP.E/P.001
    (re.compile(r'\b(GM\d{4}M|GME\d{4,5}|GMP\.[A-Z0-9.]+)\b', re.IGNORECASE), "General Motors", "GM Legacy"),
    # Ford: WSS-M2C913-C, WSK-M2G379-A, WSB-M1P83-A
    (re.compile(r'\b(WSS|WSK|WSB|WSD|WSE)\s*[-_]?\s*M\d+[A-Z0-9-]*\b', re.IGNORECASE), "Ford", "WSS"),
    # Chrysler / Stellantis: MS-6395, MS-90032, PS-8555
    (re.compile(r'\b(MS|PS)\s*[-_.]?\s*([A-Z]?\d{3,6}[A-Z0-9-]*)\b', re.IGNORECASE), "Chrysler / Stellantis", "MS"),
    # Toyota: TSM5500G, TSK5705G
    (re.compile(r'\bTS[MKFG]\s*[-_]?\s*\d{4,5}[A-Z]?\b', re.IGNORECASE), "Toyota", "TSM"),
    # VW / Audi: TL 52146, PV 1200
    (re.compile(r'\b(TL\s*\d{3,5}|PV\s*\d{3,5})\b', re.IGNORECASE), "Volkswagen Group", "TL"),
    # Mercedes: DBL 5400, MBN 10435
    (re.compile(r'\b(DBL\s*\d{3,5}|MBN\s*\d{3,5})\b', re.IGNORECASE), "Mercedes-Benz", "DBL"),
]

OEM_CORROBORATING_TERMS = {
    "specification", "standard", "test method", "procedure", "material", "coating",
    "corrosion", "fastener", "plating", "engineering", "durability", "oem", "requirement",
    "requirements", "spec", "drawing", "norm", "norma", "vibration", "tensile", "hardness",
    "weld", "welding", "torque", "flammability", "paint", "steel", "aluminum", "resin",
    "general motors", "worldwide", "engineering standard", "material spec", "sheet steel",
    "automotive", "vehicle", "chassis", "powertrain"
}

NON_OEM_FALSE_POSITIVE_TERMS = {
    # Watches, Timepieces & Jewelry (e.g. Casio G-Shock GMW-B5000)
    "casio", "g-shock", "g shock", "watch", "bezel", "strap", "timepiece", "bracelet",
    "glass replacement", "dial", "horology", "chronograph", "quartz", "seiko", "citizen",
    "rolex", "omega", "band replacement", "wrist watch",
    # Gaming, Streaming & Workspace Collision
    "gamer", "gaming", "workspace", "podcast", "music", "radio", "charity", "ministry",
    "west", "global money week", "gameplay", "youtube", "discord", "roblox", "minecraft",
    "twitch", "streamer", "let's play", "esports", "mouse", "keyboard", "headset", "headphone",
    # Apparel & Personal Goods
    "t-shirt", "hoodie", "sweater", "shoes", "sneakers", "dress", "perfume", "fragrance",
    # Literature, Fiction & Media
    "novel", "fiction", "poetry", "poem", "lyrics", "audiobook", "manga", "anime", "comic",
    # Religious & Non-Profit
    "church", "ministry", "charity", "sermon", "global money week", "gospel", "bible"
}

SERVICE_MANUAL_TERMS = {
    "service manual", "workshop manual", "repair manual", "shop manual", "factory manual",
    "owner manual", "owners manual", "engine overhaul", "transmission rebuild",
    "chassis repair", "body repair", "maintenance manual", "technical service manual",
    "factory service manual", "repair guide", "service guide"
}

WIRING_DIAGRAM_TERMS = {
    "wiring diagram", "wiring schematic", "electrical schematic", "electrical diagram",
    "ecu pinout", "pinout", "pin outs", "fuse box diagram", "connector pinout",
    "circuit diagram", "ecm pinout", "bcm pinout", "pcm pinout", "engine harness",
    "schematic diagram", "electrical wiring"
}

TSB_BULLETIN_TERMS = {
    "technical service bulletin", "tsb", "service bulletin", "dealer bulletin",
    "recall bulletin", "special policy bulletin", "campaign bulletin"
}

CORPORATE_BENIGN_TERMS = {
    "10-k", "10-q", "annual report", "investor presentation", "quarterly earnings",
    "proxy statement", "sustainability report", "financial statement", "esg report",
    "shareholder", "press release", "board of directors", "investor day", "form 8-k"
}


def classify_scribd_document(title: str, query: str = "", uploader: str = "") -> Dict:
    """
    Intelligently classify a Scribd document into threat categories with 3-Layer GMW Acronym Disambiguation.
    """
    if not title:
        return {
            "category": "Unknown Document",
            "threat_badge": "📄 Document",
            "threat_score": 10,
            "is_suppressed": False,
            "confidence": "LOW",
            "matched_spec": "",
            "detected_brand": ""
        }

    t_low = title.lower()
    q_low = query.lower() if query else ""
    u_low = uploader.lower() if uploader else ""
    combined = f"{t_low} {q_low} {u_low}"

    # 1. Check for Benign Corporate / Financial Reports first
    if any(b in t_low for b in CORPORATE_BENIGN_TERMS):
        return {
            "category": "Corporate Public Report",
            "threat_badge": "📄 Corporate Report (Benign)",
            "threat_score": 0,
            "is_suppressed": True,
            "confidence": "HIGH",
            "matched_spec": "",
            "detected_brand": ""
        }

    # 2. Check for Non-OEM False Positive Collision Terms (e.g. "Casio GMW-B5000", "Gamer Media Workspace")
    is_non_oem = any(fp in t_low for fp in NON_OEM_FALSE_POSITIVE_TERMS)
    if is_non_oem:
        return {
            "category": "Suppressed False Positive",
            "threat_badge": "🛡️ Suppressed False Positive",
            "threat_score": 0,
            "is_suppressed": True,
            "confidence": "HIGH",
            "matched_spec": "",
            "detected_brand": ""
        }

    # 3. Check for OEM Engineering Standards (GMW, WSS, MS, TSM, TL, DBL)
    matched_any_oem = False
    for pattern, brand_name, code_prefix in OEM_SPEC_PATTERNS:
        match = pattern.search(title)
        if match:
            matched_any_oem = True
            spec_str = match.group(0).strip()
            has_numeric_spec = bool(re.search(r'\d{3,6}', spec_str))
            has_corroborating = any(c in combined for c in OEM_CORROBORATING_TERMS)

            if has_numeric_spec and (has_corroborating or len(spec_str) >= 6 or code_prefix == "GMW"):
                badge_label = f"🚨 Verified {code_prefix} Standard" if code_prefix == "GMW" else f"🚨 Verified OEM Standard ({code_prefix})"
                return {
                    "category": "OEM Engineering Standard",
                    "threat_badge": badge_label,
                    "threat_score": 95,
                    "is_suppressed": False,
                    "confidence": "HIGH",
                    "matched_spec": spec_str,
                    "detected_brand": brand_name
                }
            elif has_numeric_spec:
                return {
                    "category": "OEM Engineering Standard",
                    "threat_badge": f"🔍 Unconfirmed Spec ({code_prefix})",
                    "threat_score": 70,
                    "is_suppressed": False,
                    "confidence": "MEDIUM",
                    "matched_spec": spec_str,
                    "detected_brand": brand_name
                }

    # Standalone unconfirmed "GMW" acronym check without numeric standard code
    if not matched_any_oem and re.search(r'\bgmw\b', t_low):
        has_corroborating = any(c in combined for c in OEM_CORROBORATING_TERMS)
        if has_corroborating:
            return {
                "category": "Ambiguous Document",
                "threat_badge": "⚠️ Ambiguous (Review Required)",
                "threat_score": 25,
                "is_suppressed": False,
                "confidence": "LOW",
                "matched_spec": "GMW",
                "detected_brand": "General Motors"
            }
        else:
            # GMW with zero automotive context is an irrelevant non-OEM collision
            return {
                "category": "Suppressed False Positive",
                "threat_badge": "🛡️ Suppressed False Positive",
                "threat_score": 0,
                "is_suppressed": True,
                "confidence": "HIGH",
                "matched_spec": "",
                "detected_brand": ""
            }

    # 4. Check for Electrical Wiring / Schematic / Pinout
    if any(w in t_low for w in WIRING_DIAGRAM_TERMS):
        return {
            "category": "Electrical / Wiring Diagram",
            "threat_badge": "⚡ Electrical / Wiring Diagram",
            "threat_score": 85,
            "is_suppressed": False,
            "confidence": "HIGH",
            "matched_spec": "",
            "detected_brand": ""
        }

    # 5. Check for Technical Service Bulletins (TSB)
    if any(tb in t_low for tb in TSB_BULLETIN_TERMS):
        return {
            "category": "Dealer Technical Bulletin",
            "threat_badge": "📑 Dealer Service Bulletin (TSB)",
            "threat_score": 80,
            "is_suppressed": False,
            "confidence": "HIGH",
            "matched_spec": "",
            "detected_brand": ""
        }

    # 6. Check for Factory / Workshop Service Manuals
    if any(m in t_low for m in SERVICE_MANUAL_TERMS):
        return {
            "category": "Vehicle Service Manual",
            "threat_badge": "🔧 Vehicle Service Manual",
            "threat_score": 85,
            "is_suppressed": False,
            "confidence": "HIGH",
            "matched_spec": "",
            "detected_brand": ""
        }

    # 7. Generic / Automotive Document Fallback
    return {
        "category": "Automotive / Technical Document",
        "threat_badge": "📄 Technical Document",
        "threat_score": 50,
        "is_suppressed": False,
        "confidence": "MEDIUM",
        "matched_spec": "",
        "detected_brand": ""
    }


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

    def set_headless(self, is_headless: bool, shift_active_window: bool = True):
        """Dynamically update headless mode. If context is open and mode changed, reset context."""
        old = self.headless
        self.headless = is_headless
        if (self._context or self._browser) and old != is_headless:
            try:
                self.close()
            except Exception:
                pass

    def close(self):
        """Safely close browser context, browser instance, and Playwright process."""
        try:
            if self._context:
                try: self._context.close()
                except Exception: pass
                self._context = None
            if self._browser:
                try: self._browser.close()
                except Exception: pass
                self._browser = None
            if self._playwright:
                try: self._playwright.stop()
                except Exception: pass
                self._playwright = None
        except Exception:
            pass

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
               doc_mode: str = "all", suppress_false_positives: bool = True,
               stop_event=None, pause_event=None, log_callback=None) -> List[Dict]:
        """
        Search Scribd for documents matching query keywords with 3-Layer GMW Disambiguation and Smart Classification.
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

        _log(f"📚 [Scribd] Initiating document sweep for '{clean_q}' (Target: {limit_pages} page(s), Mode: {doc_mode})...")

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

                    # Intelligent Document Classification & GMW Disambiguation
                    doc_intel = classify_scribd_document(it.get("title", ""), query=query, uploader=it.get("seller", ""))
                    
                    if suppress_false_positives and doc_intel.get("is_suppressed"):
                        _log(f"  🛡️ [Scribd Filter] Suppressed non-infringing/false positive: '{it.get('title', '')[:50]}' ({doc_intel.get('category')})")
                        continue

                    # Mode filtering if requested
                    if doc_mode == "manuals" and doc_intel.get("category") not in ("Vehicle Service Manual", "Electrical / Wiring Diagram", "Dealer Technical Bulletin"):
                        continue
                    elif doc_mode == "standards" and doc_intel.get("category") != "OEM Engineering Standard":
                        continue

                    results.append({
                        "brand": doc_intel.get("detected_brand", ""),
                        "product_type": doc_intel.get("category", "Document / PDF"),
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
                        "threat_badge": doc_intel.get("threat_badge", "📄 Document"),
                        "threat_score": doc_intel.get("threat_score", 50),
                        "threat_intel": f"{doc_intel.get('category')} ({doc_intel.get('confidence')} Confidence)",
                        "keyword": query
                    })
                    page_new += 1

                _log(f"📦 [Scribd] Harvested {page_new} qualified documents from page {page_num} ({len(results)} total).")
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
