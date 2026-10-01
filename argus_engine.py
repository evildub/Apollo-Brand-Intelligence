"""
argus_engine.py - Argus Compliance Sentinel Engine
Multi-Marketplace Bulk Availability, Takedown & Compliance Verification Engine.
Designed for high-volume automated verification across eBay, Mercado Libre, Amazon,
Redbubble, TeePublic, Vinted, Etsy, AliExpress, Shopify, and independent storefronts.
"""

import os
import re
import csv
import time
import socket
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Callable
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger("argus_engine")

# Check for curl_cffi for anti-fingerprint SSL impersonation
try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

import requests

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# Compliance Status Constants
STATUS_REMOVED = "REMOVED / 404"
STATUS_ENDED = "ENDED / INACTIVE"
STATUS_ACTIVE = "ACTIVE / LIVE"
STATUS_BLOCKED = "BLOCKED / CAPTCHA"
STATUS_ERROR = "ERROR / UNREACHABLE"

STATUS_BADGES = {
    STATUS_REMOVED: "🔴 Removed / 404",
    STATUS_ENDED:   "🟡 Ended / Inactive",
    STATUS_ACTIVE:  "🟢 Active / Live",
    STATUS_BLOCKED: "⚪ Blocked / Captcha",
    STATUS_ERROR:   "⚠ Connection Error"
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class ComplianceResult:
    """Represents the verification outcome of a single marketplace URL."""

    def __init__(
        self,
        url: str,
        marketplace: str,
        status: str,
        status_code: int,
        details: str,
        latency_ms: float = 0.0,
        original_data: Optional[Dict[str, Any]] = None
    ):
        self.url = url
        self.marketplace = marketplace
        self.status = status
        self.status_code = status_code
        self.details = details
        self.latency_ms = round(latency_ms, 1)
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.original_data = original_data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "marketplace": self.marketplace,
            "status": self.status,
            "status_badge": STATUS_BADGES.get(self.status, self.status),
            "status_code": self.status_code,
            "details": self.details,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            **self.original_data
        }


class ArgusEngine:
    """Multi-marketplace concurrent compliance probe and takedown verification engine."""

    def __init__(self, max_workers: int = 8, timeout: int = 12):
        self.max_workers = max_workers
        self.timeout = timeout
        self.abort_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Unpaused by default
        self._session_cache: Dict[str, Any] = {}

    @staticmethod
    def identify_marketplace(url: str) -> str:
        """Derive standard marketplace identification from domain structure."""
        if not url:
            return "Unknown"
        raw = url.lower()
        if "ebay." in raw:
            return "eBay"
        if "mercadolibre." in raw or "mercadolivre." in raw:
            return "Mercado Libre"
        if "amazon." in raw:
            return "Amazon"
        if "redbubble.com" in raw:
            return "Redbubble"
        if "teepublic.com" in raw:
            return "TeePublic"
        if "vinted." in raw:
            return "Vinted"
        if "etsy.com" in raw:
            return "Etsy"
        if "aliexpress.com" in raw:
            return "AliExpress"
        if "printblur.com" in raw:
            return "Printblur"
        if "printerval.com" in raw:
            return "Printerval"
        if "spreadshirt." in raw:
            return "Spreadshirt"
        if "zazzle.com" in raw:
            return "Zazzle"
        if "teespring.com" in raw or "spring.com" in raw:
            return "Teespring"
        if "threadless.com" in raw:
            return "Threadless"
        if "cafepress.com" in raw:
            return "CafePress"
        if "wish.com" in raw:
            return "Wish"
        if "temu.com" in raw:
            return "Temu"
        if "tiktok.com" in raw:
            return "TikTok Shop"
        if "myshopify.com" in raw:
            return "Shopify"
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "") if parsed.netloc else "Independent Web"

    def probe_url(self, url: str, original_data: Optional[Dict[str, Any]] = None) -> ComplianceResult:
        """
        Probe a single URL with domain-tuned heuristics to detect if the product
        is active, ended, or completely removed / 404'd.
        """
        clean_url = str(url).strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url

        mkt = self.identify_marketplace(clean_url)
        t_start = time.time()

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        resp_code = 0
        html = ""

        try:
            # Prefer curl_cffi with Chrome 120 TLS fingerprint when available
            if HAS_CURL_CFFI:
                r = curl_requests.get(
                    clean_url,
                    headers=headers,
                    impersonate="chrome120",
                    timeout=self.timeout,
                    allow_redirects=True
                )
                resp_code = r.status_code
                html = r.text or ""
            else:
                r = requests.get(
                    clean_url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                resp_code = r.status_code
                html = r.text or ""
        except requests.exceptions.Timeout:
            latency = (time.time() - t_start) * 1000
            return ComplianceResult(clean_url, mkt, STATUS_ERROR, 408, "Gateway Connection Timeout (>12s)", latency, original_data)
        except requests.exceptions.SSLError as e:
            latency = (time.time() - t_start) * 1000
            return ComplianceResult(clean_url, mkt, STATUS_ERROR, 0, f"SSL Handshake Error: {e}", latency, original_data)
        except Exception as e:
            latency = (time.time() - t_start) * 1000
            return ComplianceResult(clean_url, mkt, STATUS_ERROR, 0, f"Network Unreachable: {e}", latency, original_data)

        latency = (time.time() - t_start) * 1000

        # ── 1. HTTP 404 / 410 Fast Path ──────────────────────────────────────
        if resp_code in (404, 410):
            return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, f"HTTP {resp_code} (Item / Page Removed)", latency, original_data)

        # ── 2. HTTP 403 / 429 Captcha / Block Path ───────────────────────────
        if resp_code in (403, 429) or ("captcha" in html.lower() and len(html) < 6000):
            return ComplianceResult(clean_url, mkt, STATUS_BLOCKED, resp_code, "Security Challenge / Rate-Limited (Verify Manually)", latency, original_data)

        # ── 3. Marketplace-Specific Semantic Heuristics ──────────────────────
        html_l = html.lower()

        # ── eBay ──
        if mkt == "eBay":
            if "this listing was ended by the seller" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "eBay: Listing ended by seller", latency, original_data)
            if "this item is out of stock" in html_l or "out of stock" in html_l and "buy it now" not in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "eBay: Out of stock / inactive", latency, original_data)
            if "we looked everywhere" in html_l or "looks like this page is missing" in html_l or "this item is no longer available" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "eBay: Item removed from marketplace", latency, original_data)
            if "binBtn_btn" in html or "isCartBtn_btn" in html or "buy it now" in html_l or "add to cart" in html_l or "add to watchlist" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "eBay: Live active listing with purchase options", latency, original_data)

        # ── Mercado Libre ──
        elif mkt == "Mercado Libre":
            if "publicación finalizada" in html_l or "publicación pausada" in html_l or "anúncio pausado" in html_l or "anúncio finalizado" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "Mercado Libre: Publicación finalizada / pausada", latency, original_data)
            if "parece que no hay nada por aquí" in html_l or "esta página no existe" in html_l or "página não encontrada" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "Mercado Libre: Página eliminada (Removed)", latency, original_data)
            if "comprar ahora" in html_l or "agregar al carrito" in html_l or "comprar agora" in html_l or "adicionar ao carrinho" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "Mercado Libre: Live active publication", latency, original_data)

        # ── Amazon ──
        elif mkt == "Amazon":
            if "currently unavailable" in html_l or "we don't know when or if this item will be back in stock" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "Amazon: Currently unavailable / Out of stock", latency, original_data)
            if "looking for something?" in html_l and "functioning page on our site" in html_l or "dogs of amazon" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "Amazon: ASIN page deleted / dog page (Removed)", latency, original_data)
            if "add to cart" in html_l or "buy now" in html_l or "add-to-cart-button" in html:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "Amazon: Active Buy Box / In Stock", latency, original_data)

        # ── Redbubble ──
        elif mkt == "Redbubble":
            if "whoops! we couldn't find that page" in html_l or "this work has been removed" in html_l or "content removed" in html_l or "page not found" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "Redbubble: Design taken down / deleted (Removed)", latency, original_data)
            if "add to cart" in html_l or "add-to-cart" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "Redbubble: Active design available for purchase", latency, original_data)

        # ── TeePublic ──
        elif mkt == "TeePublic":
            if "product not found" in html_l or "that design doesn't exist" in html_l or "oops! something went wrong" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "TeePublic: Design removed / 404", latency, original_data)
            if "add to cart" in html_l or "add_to_cart" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "TeePublic: Active design live", latency, original_data)

        # ── Vinted ──
        elif mkt == "Vinted":
            if "member's item is no longer available" in html_l or "item was removed" in html_l or "cet article n'est plus disponible" in html_l or "article introuvable" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "Vinted: Listing removed or item unavailable", latency, original_data)
            if "item-sold" in html_l or "sold" in html_l and "buy" not in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "Vinted: Item marked as sold", latency, original_data)
            if "buy" in html_l or "acheter" in html_l or "comprar" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "Vinted: Active live article", latency, original_data)

        # ── Etsy ──
        elif mkt == "Etsy":
            if "sorry, this item is unavailable" in html_l or "this item is sold out" in html_l or "listing has ended" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "Etsy: Listing sold out / inactive", latency, original_data)
            if "listing has been removed" in html_l or "page not found" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "Etsy: Listing removed by platform / seller", latency, original_data)
            if "add to cart" in html_l or "buy it now" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "Etsy: Active listing live in shop", latency, original_data)

        # ── AliExpress ──
        elif mkt == "AliExpress":
            if "item is no longer available" in html_l or "this product can't be shipped" in html_l or "under review" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "AliExpress: Product offline / inactive", latency, original_data)
            if "page not found" in html_l or "not found" in html_l and len(html) < 8000:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "AliExpress: Item removed", latency, original_data)
            if "buy now" in html_l or "add to cart" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "AliExpress: Live store listing", latency, original_data)

        # ── Printerval / Printblur ──
        elif mkt in ("Printerval", "Printblur"):
            if "product not found" in html_l or "design not found" in html_l or "404" in html_l and len(html) < 10000:
                return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, f"{mkt}: Product deleted (Removed)", latency, original_data)
            if "add to cart" in html_l or "buy now" in html_l:
                return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, f"{mkt}: Live active design", latency, original_data)

        # ── 4. Generic Intelligent Fallback Heuristics ──
        if "out of stock" in html_l or "sold out" in html_l or "no longer available for purchase" in html_l:
            return ComplianceResult(clean_url, mkt, STATUS_ENDED, resp_code, "Generic: Out of stock / Sold out", latency, original_data)

        if "item removed" in html_l or "product not found" in html_l or "page not found" in html_l or "has been deleted" in html_l:
            return ComplianceResult(clean_url, mkt, STATUS_REMOVED, resp_code, "Generic: Page indicates item removed", latency, original_data)

        if resp_code == 200 and len(html) > 5000:
            return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, "HTTP 200 (Active Content Payload)", latency, original_data)

        return ComplianceResult(clean_url, mkt, STATUS_ACTIVE, resp_code, f"HTTP {resp_code} (Assumed Live)", latency, original_data)

    def audit_batch(
        self,
        items: List[Dict[str, Any]],
        url_field: str = "url",
        progress_callback: Optional[Callable[[int, int, ComplianceResult], None]] = None,
        completion_callback: Optional[Callable[[List[ComplianceResult]], None]] = None
    ) -> List[ComplianceResult]:
        """
        Execute concurrent compliance audit over a batch of items.
        Calls progress_callback(completed_count, total_count, latest_result) in real time.
        """
        if self.abort_event.is_set():
            return []
        results: List[ComplianceResult] = []
        total = len(items)
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {
                executor.submit(self.probe_url, it.get(url_field, ""), it): it
                for it in items
            }

            for future in as_completed(future_to_item):
                if self.abort_event.is_set():
                    break

                # Support pause/resume
                self.pause_event.wait()

                try:
                    res = future.result()
                except Exception as e:
                    orig = future_to_item[future]
                    res = ComplianceResult(
                        orig.get(url_field, ""),
                        "Unknown",
                        STATUS_ERROR,
                        0,
                        f"Thread Failure: {e}",
                        original_data=orig
                    )

                results.append(res)
                completed += 1
                if progress_callback:
                    try:
                        progress_callback(completed, total, res)
                    except Exception:
                        pass

        if completion_callback:
            try:
                completion_callback(results)
            except Exception:
                pass

        return results

    def abort(self):
        """Immediately abort active compliance audit."""
        self.abort_event.set()
        self.pause_event.set()

    def pause(self):
        """Pause active compliance audit."""
        self.pause_event.clear()

    def resume(self):
        """Resume paused compliance audit."""
        self.pause_event.set()

    @staticmethod
    def parse_import_file(filepath: str) -> Tuple[List[Dict[str, Any]], str, List[str]]:
        """
        Parse an Excel (.xlsx, .xls) or CSV (.csv) file.
        Automatically isolates the URL column and preserves all original data.
        Returns (rows, detected_url_column, all_columns).
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()
        rows: List[Dict[str, Any]] = []
        all_cols: List[str] = []

        if ext in (".xlsx", ".xls") and HAS_OPENPYXL:
            wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
            ws = wb.active
            iter_rows = ws.iter_rows(values_only=True)
            headers = None
            for row_idx, row_vals in enumerate(iter_rows):
                if not headers:
                    # Take first row with non-empty strings as headers
                    if any(row_vals):
                        headers = [str(v).strip() if v is not None else f"Column_{i+1}" for i, v in enumerate(row_vals)]
                        all_cols = headers
                    continue
                if not any(row_vals):
                    continue
                row_dict = {}
                for idx, col_name in enumerate(headers):
                    val = row_vals[idx] if idx < len(row_vals) else ""
                    row_dict[col_name] = str(val).strip() if val is not None else ""
                rows.append(row_dict)
            wb.close()
        else:
            # Fallback to CSV parser
            with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                all_cols = list(reader.fieldnames or [])
                for r in reader:
                    rows.append({k: str(v).strip() if v is not None else "" for k, v in r.items()})

        # Heuristically detect URL column
        detected_col = ""
        url_keywords = ["url", "link", "listing url", "item url", "listing_url", "item_url", "web url", "product url"]
        for c in all_cols:
            if c.lower().strip() in url_keywords:
                detected_col = c
                break
        if not detected_col:
            # Inspect first 10 rows for http
            for c in all_cols:
                for r in rows[:10]:
                    v = str(r.get(c, "")).lower()
                    if v.startswith("http://") or v.startswith("https://") or "ebay." in v or "amazon." in v:
                        detected_col = c
                        break
                if detected_col:
                    break

        if not detected_col and all_cols:
            # If standard 18-column format, Column B is typically URL (index 1)
            if len(all_cols) >= 2 and ("http" in str(rows[0].get(all_cols[1], "")) if rows else False):
                detected_col = all_cols[1]
            else:
                detected_col = all_cols[0]

        return rows, detected_col, all_cols

    @staticmethod
    def export_compliance_report(
        filepath: str,
        results: List[ComplianceResult],
        original_cols: Optional[List[str]] = None
    ) -> str:
        """
        Export verified compliance findings to an Excel (.xlsx) file with
        status badges, HTTP codes, reasons, and conditional formatting.
        """
        if not HAS_OPENPYXL:
            raise RuntimeError("openpyxl is required to generate Excel compliance reports.")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Argus Compliance Audit"
        ws.views.sheetView[0].showGridLines = True

        # Styles
        header_fill = PatternFill(start_color="0A0E36", end_color="0A0E36", fill_type="solid")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

        fill_removed = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        font_removed = Font(name="Segoe UI", size=9, bold=True, color="991B1B")

        fill_ended = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        font_ended = Font(name="Segoe UI", size=9, bold=True, color="92400E")

        fill_active = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        font_active = Font(name="Segoe UI", size=9, bold=True, color="166534")

        fill_blocked = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        font_blocked = Font(name="Segoe UI", size=9, bold=False, color="475569")

        font_norm = Font(name="Segoe UI", size=9)
        border_thin = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )

        # Assemble columns: Compliance audit columns first, then original data columns
        compliance_headers = [
            "Compliance Status",
            "Marketplace",
            "Verification Detail",
            "HTTP Code",
            "Latency (ms)",
            "Audited Timestamp",
            "Verified URL"
        ]

        orig_fields = original_cols or []
        if not orig_fields and results:
            orig_fields = [k for k in results[0].original_data.keys() if k != "url"]

        all_headers = compliance_headers + [c for c in orig_fields if c.lower() != "url"]

        # Write header row
        for col_idx, h in enumerate(all_headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center" if col_idx in (1, 2, 4, 5, 6) else "left", vertical="center")
        ws.row_dimensions[1].height = 28

        # Write data rows
        for row_idx, res in enumerate(results, 2):
            status_text = STATUS_BADGES.get(res.status, res.status)
            row_vals = [
                status_text,
                res.marketplace,
                res.details,
                res.status_code if res.status_code else "ERR",
                res.latency_ms,
                res.timestamp,
                res.url
            ]

            # Append preserved original fields
            for orig_col in orig_fields:
                if orig_col.lower() != "url":
                    row_vals.append(res.original_data.get(orig_col, ""))

            ws.row_dimensions[row_idx].height = 20
            for col_idx, val in enumerate(row_vals, 1):
                c = ws.cell(row=row_idx, column=col_idx, value=val)
                c.font = font_norm
                c.border = border_thin
                c.alignment = Alignment(
                    horizontal="center" if col_idx in (1, 2, 4, 5, 6) else "left",
                    vertical="center"
                )

                # Format Compliance Status cell with colored badge
                if col_idx == 1:
                    if res.status == STATUS_REMOVED:
                        c.fill = fill_removed
                        c.font = font_removed
                    elif res.status == STATUS_ENDED:
                        c.fill = fill_ended
                        c.font = font_ended
                    elif res.status == STATUS_ACTIVE:
                        c.fill = fill_active
                        c.font = font_active
                    else:
                        c.fill = fill_blocked
                        c.font = font_blocked

                # Make URL clickable hyperlink
                if col_idx == 7 and str(val).startswith("http"):
                    c.hyperlink = val
                    c.font = Font(name="Segoe UI", size=9, color="0284C7", underline="single")

        # Auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col[:100]:  # sample first 100 rows for speed
                val_s = str(cell.value or "")
                if len(val_s) > max_len:
                    max_len = len(val_s)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 48)

        ws.freeze_panes = "A2"
        wb.save(filepath)
        return filepath
