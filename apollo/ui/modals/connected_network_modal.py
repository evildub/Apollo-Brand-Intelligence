"""
Extracted Apollo Enterprise UI Modal.
"""

import sys
import os
import re
import io
import time
import threading
import logging
import webbrowser
from datetime import datetime
from typing import Optional, List, Dict, Any
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox as _raw_messagebox
from PIL import Image, ImageTk

from apollo.ui.dialogs import center_window_on_parent, ThemedMessageBoxProxy
from apollo.export.exporter import normalize_price_string
from apollo.scrapers.engines.scraper import EbayScraper

messagebox = ThemedMessageBoxProxy(_raw_messagebox)
logger = logging.getLogger("Apollo")

FONT      = ("Segoe UI", 10)
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SM   = ("Segoe UI", 9)
FONT_XS   = ("Segoe UI", 8)
FONT_LG   = ("Segoe UI", 12, "bold")
FONT_HEAD = ("Segoe UI", 11, "bold")
FONT_TITLE= ("Segoe UI", 13, "bold")
FONT_CODE = ("Consolas", 9)


def _get_app_attr(attr_name, default=None):
    for mod_name in ("apollo.app", "app", "main"):
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, attr_name):
            return getattr(mod, attr_name)
    return default


def _get_active_tool():
    cls = _get_app_attr("EbayTool")
    return getattr(cls, "active_instance", None) if cls else None

THUMB_CONFIG = {
    "Off (Text Only)":     {"rowheight": 24,  "img_size": 0,   "col_width": 0,   "show": "headings"},
    "Small (50px)":        {"rowheight": 56,  "img_size": 50,  "col_width": 64,  "show": "tree headings"},
    "Medium (100px)":      {"rowheight": 110, "img_size": 100, "col_width": 116, "show": "tree headings"},
    "Large (180px)":       {"rowheight": 194, "img_size": 180, "col_width": 196, "show": "tree headings"},
    "Extra Large (250px)": {"rowheight": 266, "img_size": 250, "col_width": 268, "show": "tree headings"},
}


def safe_int_score(val: Any, default: int = 0) -> int:
    """Safely convert any raw threat score (int, float, string 'UNKNOWN', '', None) to an integer."""
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def download_image_bytes(url: str, timeout: float = 10.0, session=None) -> Optional[bytes]:
    """
    Robust image byte downloader with TLS fingerprint impersonation for protected CDNs (Spreadshirt, Threadless, etc.).
    """
    if not url or not str(url).startswith("http"):
        return None
    
    url_str = str(url).strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    }
    
    url_low = url_str.lower()
    if "spreadshirt" in url_low or "spreadshirtmedia" in url_low:
        headers["Referer"] = "https://www.spreadshirt.com/"
        headers["Origin"] = "https://www.spreadshirt.com"
    elif "threadless" in url_low or "maestro." in url_low:
        headers["Referer"] = "https://www.threadless.com/"
        headers["Origin"] = "https://www.threadless.com"
    elif "redbubble" in url_low or "rbxcdn" in url_low:
        headers["Referer"] = "https://www.redbubble.com/"
    elif "printerval" in url_low:
        headers["Referer"] = "https://printerval.com/"
    elif "printblur" in url_low:
        headers["Referer"] = "https://printblur.com/"
    elif "zazzle" in url_low or "zcache" in url_low:
        headers["Referer"] = "https://www.zazzle.com/"
    elif "teepublic" in url_low:
        headers["Referer"] = "https://www.teepublic.com/"

    # If it's a known protected CDN (e.g. Spreadshirt Fastly/Varnish WAF), try curl_cffi first
    is_protected = any(k in url_low for k in ("spreadshirtmedia", "spreadshirt.com", "spreadshirtmedia.net"))
    if is_protected:
        try:
            from curl_cffi import requests as cffi_requests
            r = cffi_requests.get(url_str, headers=headers, impersonate="edge101", timeout=timeout)
            if r.status_code == 200 and r.content:
                return r.content
        except Exception:
            pass

    # Standard fast HTTP request using active session or requests
    try:
        req_lib = session if session is not None else requests
        r = req_lib.get(url_str, headers=headers, timeout=timeout)
        if r.status_code == 200 and r.content:
            return r.content
        elif r.status_code in (403, 401, 429, 503):
            # Retry with curl_cffi on WAF blockage
            try:
                from curl_cffi import requests as cffi_requests
                r_cffi = cffi_requests.get(url_str, headers=headers, impersonate="edge101", timeout=timeout)
                if r_cffi.status_code == 200 and r_cffi.content:
                    return r_cffi.content
            except Exception:
                pass
    except Exception:
        pass

    # Fallback to urllib
    try:
        req = urllib.request.Request(url_str, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if data:
                return data
    except Exception:
        try:
            from curl_cffi import requests as cffi_requests
            r_cffi = cffi_requests.get(url_str, headers=headers, impersonate="edge101", timeout=timeout)
            if r_cffi.status_code == 200 and r_cffi.content:
                return r_cffi.content
        except Exception:
            pass

    return None



# ══════════════════════════════════════════════════════════════════════════════
#  CONNECTED SELLER NETWORK & PHOTO SYNDICATE HUNTER MODAL
# ══════════════════════════════════════════════════════════════════════════════
class ConnectedNetworkModal(tk.Toplevel):
    """
    On-Demand Visual Syndicate & Connected Seller Hunter.
    Scans merchandising carousels on eBay listing pages and runs perceptual image hashing (dHash)
    to discover burner storefronts, competing listings, and connected counterfeit networks.
    """
    def __init__(self, parent, target_item: dict):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.target_item = target_item
        self.t = parent.theme
        self.discovered_items = []
        self.thumb_cache = {}
        self._sort_directions = {}
        
        self.title("🔗 Connected Seller Network & Photo Syndicate Hunter")
        self.geometry("1200x780")
        self.configure(bg=self.t["bg"])
        self.minsize(980, 620)
        self.parent._apply_dark_titlebar(self)
        
        self._build_ui()
        self.parent._center_window(self, 1200, 780)
        self.deiconify()
        self.lift()
        self.focus_force()
        
        self._start_network_scan()

    def _build_ui(self):
        t = self.t

        # ── 1. Top Target Reference Listing Card ──────────────────────────────
        hdr_frame = tk.Frame(self, bg=t["panel"], padx=16, pady=12, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        hdr_frame.pack(side="top", fill="x", padx=12, pady=(12, 6))

        # Big Thumbnail preview container
        img_box = tk.Frame(hdr_frame, bg=t["entry_bg"], width=104, height=104, highlightbackground=t["border"], highlightthickness=1)
        img_box.pack_propagate(False)
        img_box.pack(side="left", padx=(0, 16))

        self.src_img_lbl = tk.Label(img_box, text="Loading\nPhoto...", bg=t["entry_bg"], fg=t["subtext"], font=FONT_SM)
        self.src_img_lbl.pack(fill="both", expand=True)
        self._load_source_image()

        info_box = tk.Frame(hdr_frame, bg=t["panel"])
        info_box.pack(side="left", fill="both", expand=True)

        badge_row = tk.Frame(info_box, bg=t["panel"])
        badge_row.pack(anchor="w", pady=(0, 4))
        
        tag_lbl = tk.Label(badge_row, text="🎯 TARGET REFERENCE LISTING", font=("Segoe UI", 8, "bold"), bg=t["accent"], fg="white", padx=8, pady=2)
        tag_lbl.pack(side="left", padx=(0, 8))

        brand_val = self.target_item.get("brand") or "General Brand"
        tk.Label(badge_row, text=f"Brand: {brand_val}", font=("Segoe UI", 8, "bold"), bg=t["entry_bg"], fg=t["subtext"], padx=8, pady=2).pack(side="left")

        title_lbl = tk.Label(info_box, text=self.target_item.get("title", "Unknown Title"), font=FONT_HEAD, bg=t["panel"], fg=t["text"], wraplength=820, justify="left")
        title_lbl.pack(anchor="w")

        seller_name = self.target_item.get("seller") or "Unknown Seller"
        price_val = self.target_item.get("price") or "N/A"
        item_id_val = self.target_item.get("item_id") or "N/A"
        sub_text = f"👤 Seller: {seller_name}    💰 Price: {price_val}    🆔 Item ID: {item_id_val}"
        sub_lbl = tk.Label(info_box, text=sub_text, font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        sub_lbl.pack(anchor="w", pady=(4, 0))

        # ── 2. Status & Filter Bar ────────────────────────────────────────────
        self.status_frame = tk.Frame(self, bg=t["bg"], padx=14, pady=4)
        self.status_frame.pack(side="top", fill="x", padx=12)

        self.status_lbl = tk.Label(self.status_frame, text="🔍 Scanning eBay merchandising carousels and matching perceptual image hashes...", font=("Segoe UI", 9, "italic"), bg=t["bg"], fg=t["accent"])
        self.status_lbl.pack(side="left")

        self.pbar = ttk.Progressbar(self.status_frame, mode="indeterminate", length=180)
        self.pbar.pack(side="right", padx=(8, 0))
        self.pbar.start(12)

        # Filters toolbar
        f_row = tk.Frame(self, bg=t["panel"], padx=12, pady=5, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        f_row.pack(side="top", fill="x", padx=12, pady=(2, 4))

        tk.Label(f_row, text="Thumbnails:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(0, 4))
        self.thumb_size_var = tk.StringVar(value="Medium (100px)")
        self.thumb_size_combo = ttk.Combobox(f_row, textvariable=self.thumb_size_var, values=list(THUMB_CONFIG.keys()), width=14, state="readonly", font=FONT_SM)
        self.thumb_size_combo.pack(side="left", padx=(0, 10))
        self.thumb_size_combo.bind("<<ComboboxSelected>>", self._on_thumb_size_changed)

        tk.Label(f_row, text="Match Filter:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(0, 4))
        self.match_filter_var = tk.StringVar(value="(All Discovered)")
        match_filters = ["(All Discovered)", "🎯 Exact & Near-Exact Photos Only", "🖼 Visual Matches Only"]
        self.match_filter_combo = ttk.Combobox(f_row, textvariable=self.match_filter_var, values=match_filters, width=24, state="readonly", font=FONT_SM)
        self.match_filter_combo.pack(side="left", padx=(0, 10))
        self.match_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_tree())

        self.hide_same_seller_var = tk.BooleanVar(value=False)
        same_seller_cb = tk.Checkbutton(f_row, text="Hide Same Seller", variable=self.hide_same_seller_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t.get("check_select_bg", t["accent"]), activebackground=t["panel"], font=FONT_SM)
        same_seller_cb.pack(side="left", padx=(0, 8))

        self.hide_wl_var = tk.BooleanVar(value=False)
        wl_cb = tk.Checkbutton(f_row, text="🛡 Hide Whitelisted Dealers", variable=self.hide_wl_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t.get("check_select_bg", t["accent"]), activebackground=t["panel"], font=FONT_SM)
        wl_cb.pack(side="left", padx=(0, 8))

        self.hide_targeted_var = tk.BooleanVar(value=False)
        targeted_cb = tk.Checkbutton(f_row, text="🎯 Hide Targeted / Harvested", variable=self.hide_targeted_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t.get("check_select_bg", t["accent"]), activebackground=t["panel"], font=FONT_SM)
        targeted_cb.pack(side="left", padx=(0, 8))

        # ── 4. Action Toolbar (Docked to Bottom First) ────────────────────────
        btn_bar = tk.Frame(self, bg=t["panel"], padx=10, pady=8, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x", padx=12, pady=(4, 8))

        self.count_var = tk.StringVar(value="0 connected listings discovered")
        count_lbl = tk.Label(btn_bar, textvariable=self.count_var, bg=t["panel"], fg=t["text"], font=FONT_HEAD)
        count_lbl.pack(side="left")

        tk.Button(btn_bar, text="✕ Close", command=self.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="⚡ Enrich", command=self._enrich_selected_sellers, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📥 To Table", command=self._add_to_results, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📋 Copy Handles", command=self._copy_sellers, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="🏪 To Stores", command=self._add_all_to_stores, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="➕ Queue Sellers", command=self._add_sellers_to_queue, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4).pack(side="right", padx=4)

        # ── 3. Discovered Network Table (Fills Remaining Space) ───────────────
        table_frame = tk.Frame(self, bg=t["bg"])
        table_frame.pack(side="top", fill="both", expand=True, padx=12, pady=4)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("similarity", "seller", "origin", "threat", "price", "title", "item_id")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="tree headings", selectmode="extended", style="Network.Treeview")

        style = ttk.Style()
        style.configure("Network.Treeview", background=t["entry_bg"], foreground=t["text"], fieldbackground=t["entry_bg"], rowheight=108, font=FONT_SM)
        style.configure("Network.Treeview.Heading", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9, "bold"))
        style.map("Network.Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["select_fg"])])

        self.tree.tag_configure("whitelisted", foreground=t["success"])
        self.tree.tag_configure("same_seller", foreground=t["accent2"])
        self.tree.tag_configure("targeted", foreground=t["subtext"])

        self.tree.heading("#0", text="Photo Preview", anchor="center")
        self.tree.column("#0", width=120, minwidth=100, anchor="center", stretch=False)

        self.col_cfg = {
            "similarity": ("Match Type / Visual Fingerprint", 185),
            "seller": ("Connected Seller", 140),
            "origin": ("Origin", 85),
            "threat": ("Threat Assessment", 175),
            "price": ("Price", 75),
            "title": ("Discovered Listing Title", 360),
            "item_id": ("Item ID", 105)
        }
        for c, (txt, w) in self.col_cfg.items():
            self.tree.heading(c, text=txt, command=lambda _c=c: self._sort_by_column(_c))
            self.tree.column(c, width=w, minwidth=50, stretch=False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._open_selected_url)
        self.tree.bind("<Button-3>", self._show_row_context_menu)
        self.tree.bind("<Control-a>", self._select_all_rows)
        self.tree.bind("<Control-A>", self._select_all_rows)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _on_thumb_size_changed(self, event=None):
        size_name = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_name, THUMB_CONFIG.get("Medium (100px)", {"rowheight": 110, "img_size": 100, "col_width": 116}))
        style = ttk.Style()
        style.configure("Network.Treeview", rowheight=cfg["rowheight"])
        img_size = cfg.get("img_size", 0)
        col_w = max(50, cfg.get("col_width", 116) + 10) if img_size > 0 else 50
        self.tree.column("#0", width=col_w, minwidth=40)
        self.thumb_cache.clear()
        self._populate_tree()

    def _select_all_rows(self, event=None):
        ch = self.tree.get_children()
        if ch:
            self.tree.selection_set(ch)
            self._on_tree_select()
        return "break"

    def _on_tree_select(self, event=None):
        sel_count = len(self.tree.selection())
        vis_count = len(self.tree.get_children())
        total_count = len(self.discovered_items)
        if sel_count > 0:
            self.count_var.set(f"{vis_count} listings shown ({sel_count} selected) | {total_count} discovered")
        else:
            self.count_var.set(f"{vis_count} listings shown | {total_count} discovered")

    def _load_source_image(self):
        url = self.target_item.get("image_url", "")
        if not url:
            tid = str(self.target_item.get("item_id", "")).strip()
            if tid and hasattr(self.parent, "results"):
                for r in self.parent.results:
                    if str(r.get("item_id", "")).strip() == tid and r.get("image_url"):
                        url = r.get("image_url")
                        break
        if not url:
            self.src_img_lbl.configure(text="No Photo\nAvailable")
            return

        def _w():
            try:
                if hasattr(self.parent, "raw_img_cache") and url in self.parent.raw_img_cache:
                    pimg = self.parent.raw_img_cache[url].copy()
                else:
                    data = download_image_bytes(url, timeout=8)
                    if not data:
                        raise ValueError("No data")
                    pimg = Image.open(io.BytesIO(data)).convert("RGBA")
                
                pimg.thumbnail((96, 96), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
                canvas.paste(pimg, ((96 - pimg.width)//2, (96 - pimg.height)//2))

                def _set(c=canvas):
                    try:
                        if self.winfo_exists():
                            photo = ImageTk.PhotoImage(c, master=self)
                            self.thumb_cache["source"] = photo
                            self.src_img_lbl.configure(image=photo, text="")
                            self.src_img_lbl.image = photo
                    except Exception:
                        self.src_img_lbl.configure(text="Photo\nUnavailable")
                self.after(0, _set)
            except Exception:
                try:
                    self.after(0, lambda: self.src_img_lbl.configure(text="Photo\nUnavailable"))
                except Exception:
                    pass
        threading.Thread(target=_w, daemon=True).start()

    def _start_network_scan(self):
        item_id = self.target_item.get("item_id", "")
        item_url = self.target_item.get("url", "")
        target_img = self.target_item.get("image_url", "")
        is_meli = "mercadolibre" in item_url.lower() or "mercadolivre" in item_url.lower() or "mercado" in str(self.target_item.get("marketplace", "")).lower()
        is_printerval = "printerval" in item_url.lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
        is_pb = "printblur" in item_url.lower() or "printblur" in str(self.target_item.get("marketplace", "")).lower()
        is_rb = "redbubble" in item_url.lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
        is_tiktok = "tiktok" in item_url.lower() or "tiktok" in str(self.target_item.get("marketplace", "")).lower()

        if is_printerval:
            platform_name = "Printerval"
        elif is_pb:
            platform_name = "Printblur"
        elif is_rb:
            platform_name = "Redbubble"
        elif is_meli:
            platform_name = "Mercado Libre"
        elif is_tiktok:
            platform_name = "TikTok Shop"
        else:
            platform_name = "eBay"
        self.status_lbl.configure(text=f"🔍 Scanning {platform_name} merchandising carousels, competitor recommendations, and storefront syndicates...")

        def _worker():
            try:
                if is_printerval:
                    scraper = getattr(self.parent, "printerval_scraper", None)
                    if not scraper:
                        from printerval_scraper import PrintervalScraper
                        scraper = PrintervalScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                elif is_pb:
                    scraper = getattr(self.parent, "printblur_scraper", None)
                    if not scraper:
                        from printblur_scraper import PrintblurScraper
                        scraper = PrintblurScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                elif is_rb:
                    scraper = getattr(self.parent, "redbubble_scraper", None)
                    if not scraper:
                        from redbubble_scraper import RedbubbleScraper
                        scraper = RedbubbleScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                elif is_meli:
                    scraper = getattr(self.parent, "mercadolibre_scraper", None)
                    if not scraper:
                        from mercadolibre_scraper import MercadoLibreScraper
                        scraper = MercadoLibreScraper(headless=False)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                elif is_tiktok:
                    scraper = getattr(self.parent, "tiktok_scraper", None)
                    if not scraper:
                        from tiktok_scraper import TikTokScraper
                        scraper = TikTokScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                else:
                    scraper = getattr(self.parent, "scraper", None)
                    if not scraper:
                        scraper = EbayScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)

                self.discovered_items = results
                scan_err = None
            except Exception as e:
                logger.exception("Error in ConnectedNetworkModal scan")
                results = []
                self.discovered_items = []
                scan_err = str(e)

            def _apply():
                self.pbar.stop()
                self.pbar.pack_forget()

                if scan_err:
                    self.status_lbl.configure(text=f"⚠ Carousel Scan Error: {scan_err}", fg=self.t["danger"])
                    self._populate_tree()
                    return

                ds = getattr(self.parent, "data_store", None)
                unique_sellers = set(r["seller"] for r in self.discovered_items if r.get("seller"))
                exact_matches = sum(1 for r in self.discovered_items if "Exact" in r.get("similarity", ""))
                wl_count = sum(1 for r in self.discovered_items if (ds.is_seller_whitelisted(r.get("seller", "")) if ds else False))

                status_txt = f"✅ Scan Complete: {len(self.discovered_items)} connected listings found ({exact_matches} exact photo matches, {len(unique_sellers)} resolved sellers)"
                if wl_count > 0:
                    status_txt += f" | 🛡 {wl_count} Whitelisted Dealer listings"
                self.status_lbl.configure(text=status_txt, fg=self.t["success"])

                self._populate_tree()

                # Asynchronously resolve seller country intelligence in background
                def _bg_intel():
                    try:
                        unique_sellers = list(dict.fromkeys(r["seller"] for r in results if r.get("seller") and r.get("seller") not in ("Resolving...", "Unknown")))
                        ds = getattr(self.parent, "data_store", None)
                        if unique_sellers and ds:
                            uncached = [s for s in unique_sellers if not ds.get_seller_intel(s).get("country")]
                            if uncached and hasattr(scraper, "batch_resolve_seller_countries"):
                                resolved_intel = scraper.batch_resolve_seller_countries(uncached)
                                for s, data in resolved_intel.items():
                                    c_val = data.get("country", "Unknown")
                                    if c_val and c_val != "Unknown":
                                        ds.set_seller_intel(s, c_val, member_since=data.get("member_since", ""))
                                if self.winfo_exists():
                                    self.after(0, self._populate_tree)
                    except Exception:
                        pass
                threading.Thread(target=_bg_intel, daemon=True).start()

            self.after(0, _apply)
        threading.Thread(target=_worker, daemon=True).start()

    def _sort_by_column(self, col):
        """Sort discovered items by column and re-render tree."""
        if not self.discovered_items:
            return
        if not hasattr(self, "sort_directions"):
            self.sort_directions = {}
        descending = self.sort_directions.get(col, False)
        self.sort_directions[col] = not descending
        ds = getattr(self.parent, "data_store", None)

        def get_sort_key(item):
            seller = (item.get("seller") or "").strip()
            is_pod = any(p in item.get("marketplace", "").lower() or p in item.get("url", "").lower() for p in ("printerval", "printblur", "redbubble", "teepublic", "zazzle", "spreadshirt", "threadless", "teespring"))
            if col == "origin":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else (item.get("seller_origin") or ("United States" if is_pod else ""))
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("country", "United States" if is_pod else "Unknown").lower()
            elif col == "threat":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else (item.get("seller_origin") or ("United States" if is_pod else ""))
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("score", 65 if is_pod else 0)
            elif col == "price":
                m = re.search(r"[\d,]+(?:\.\d+)?", str(item.get("price", "")))
                if m:
                    try: return float(m.group(0).replace(",", ""))
                    except ValueError: return 0.0
                return 0.0
            elif col == "item_id":
                try: return int(item.get("item_id", 0))
                except ValueError: return 0
            elif col == "similarity":
                return str(item.get("similarity", "")).lower()
            elif col == "seller":
                return seller.lower()
            elif col == "title":
                return str(item.get("title", "")).lower()
            return str(item.get(col, "")).lower()

        self.discovered_items.sort(key=get_sort_key, reverse=descending)
        self._populate_tree()

        # Update headings with sort arrows
        for c, (txt, w) in self.col_cfg.items():
            if c == col:
                arrow = " ▼" if descending else " ▲"
                self.tree.heading(c, text=f"{txt}{arrow}", command=lambda _c=c: self._sort_by_column(_c))
            else:
                self.tree.heading(c, text=txt, command=lambda _c=c: self._sort_by_column(_c))

    def _populate_tree(self):
        """Render discovered items honoring current whitelist/same seller/match filters."""
        self.tree.delete(*self.tree.get_children())
        hide_wl = self.hide_wl_var.get()
        hide_same_seller = self.hide_same_seller_var.get()
        hide_targeted = self.hide_targeted_var.get()
        match_filter = self.match_filter_var.get()
        src_raw = (self.target_item.get("seller") or "").strip()
        src_seller = self._clean_seller_handle(src_raw).lower() if hasattr(self, "_clean_seller_handle") else src_raw.lower()

        # Collect active targeted / queued / harvested store handles
        stores_in_input = set()
        if hasattr(self.parent, "store_text"):
            raw_text = self.parent.store_text.get("1.0", "end")
            placeholder = getattr(self.parent, "store_placeholder", "").strip()
            for line in raw_text.splitlines():
                l = line.strip().lower()
                if l and l != placeholder.lower():
                    clean_l = self._clean_seller_handle(l).lower() if hasattr(self, "_clean_seller_handle") else l
                    lbl = self.parent._store_label(l).lower() if hasattr(self.parent, "_store_label") else l
                    stores_in_input.add(l)
                    stores_in_input.add(clean_l)
                    stores_in_input.add(lbl)

        queued_stores = set()
        if hasattr(self.parent, "queue"):
            for q in self.parent.queue:
                s = q.get("store", "").strip().lower()
                if s:
                    clean_s = self._clean_seller_handle(s).lower() if hasattr(self, "_clean_seller_handle") else s
                    lbl = self.parent._store_label(s).lower() if hasattr(self.parent, "_store_label") else s
                    queued_stores.add(s)
                    queued_stores.add(clean_s)
                    queued_stores.add(lbl)

        executed_stores = set()
        if hasattr(self.parent, "executed_jobs"):
            for ex in self.parent.executed_jobs:
                s = ex.get("store", "").strip().lower()
                if s:
                    clean_s = self._clean_seller_handle(s).lower() if hasattr(self, "_clean_seller_handle") else s
                    lbl = self.parent._store_label(s).lower() if hasattr(self.parent, "_store_label") else s
                    executed_stores.add(s)
                    executed_stores.add(clean_s)
                    executed_stores.add(lbl)

        results_stores = set()
        harvested_item_ids = set()
        harvested_urls = set()
        if hasattr(self.parent, "results"):
            for it in self.parent.results:
                s = str(it.get("seller", "")).replace("🛡", "").replace("(Authorized)", "").strip().lower()
                clean_s = self._clean_seller_handle(s).lower() if hasattr(self, "_clean_seller_handle") else s
                if s and s not in ("unknown", "resolving..."):
                    results_stores.add(s)
                    results_stores.add(clean_s)
                iid = str(it.get("item_id", "")).strip()
                if iid:
                    harvested_item_ids.add(iid)
                u = str(it.get("url", "")).strip().lower()
                if u:
                    harvested_urls.add(u)

        targeted_or_harvested = stores_in_input | queued_stores | executed_stores | results_stores
        if src_seller:
            targeted_or_harvested.add(src_seller)
        if src_raw:
            targeted_or_harvested.add(src_raw.lower())

        size_name = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_name, THUMB_CONFIG.get("Medium (100px)", {"rowheight": 110, "img_size": 100, "col_width": 116}))
        img_size = cfg.get("img_size", 0)
        show_images = img_size > 0

        ds = getattr(self.parent, "data_store", None)
        shown_count = 0
        for itm in self.discovered_items:
            raw_seller = (itm.get("seller") or "Unknown").strip()
            seller = self._clean_seller_handle(raw_seller) if hasattr(self, "_clean_seller_handle") else raw_seller
            seller_clean = seller.lower()
            itm_id = str(itm.get("item_id", "")).strip()
            itm_url = str(itm.get("url", "")).strip().lower()

            is_wl = ds.is_seller_whitelisted(seller) if ds else False
            is_same = bool(src_seller and (seller_clean == src_seller or raw_seller.lower() == src_seller))
            is_targeted_or_harvested = bool(
                is_same or
                seller_clean in targeted_or_harvested or 
                raw_seller.lower() in targeted_or_harvested or
                (itm_id and itm_id in harvested_item_ids) or 
                (itm_url and itm_url in harvested_urls)
            )

            if hide_wl and is_wl:
                continue
            if hide_same_seller and is_same:
                continue
            if hide_targeted and is_targeted_or_harvested:
                continue

            sim_txt = itm.get("similarity", "Related Listing")
            if "Exact" in match_filter and "Exact" not in sim_txt:
                continue
            if "Visual" in match_filter and not any(k in sim_txt for k in ("Exact", "Visual", "Near-Exact")):
                continue

            if is_wl:
                seller_display = f"🛡 {seller} (Authorized)"
            elif is_same:
                seller_display = f"🏠 {seller} (Source Seller)"
            elif is_targeted_or_harvested:
                seller_display = f"🎯 {seller} (Targeted/Harvested)"
            else:
                seller_display = f"⚡ {seller}"

            # Evaluate Threat Intel from DataStore
            is_pod = any(p in itm.get("marketplace", "").lower() or p in itm.get("url", "").lower() for p in ("printerval", "printblur", "redbubble", "teepublic", "zazzle", "spreadshirt", "threadless", "teespring"))
            cached_intel = ds.get_seller_intel(seller) if ds else {}
            seller_country = cached_intel.get("country", "") if cached_intel else ""
            if not seller_country and is_pod:
                seller_country = itm.get("seller_origin") or itm.get("location") or "United States"
            loc_val = itm.get("location") or ("United States" if is_pod else "")

            assessment = ds.compute_threat_assessment(seller_country, loc_val) if ds else {}
            if is_pod:
                orig_country = assessment.get("country", "United States")
                if orig_country == "Unknown": orig_country = "United States"
                orig_txt = f"{assessment.get('flag', '🇺🇸')} {orig_country}"
                threat_txt = "👕 POD Print Syndicate"
            else:
                orig_txt = f"{assessment.get('flag', '❓')} {assessment.get('country', 'Unknown')}" if assessment.get('country') != 'Unknown' else "❓ Unresolved"
                threat_txt = assessment.get("badge", "Unresolved")

            img_url = itm.get("image_url", "")
            img_to_use = self.thumb_cache.get(img_url) if show_images else None

            tags = []
            if is_wl: tags.append("whitelisted")
            elif is_same: tags.append("same_seller")
            elif is_targeted_or_harvested: tags.append("targeted")

            iid = self.tree.insert("", "end", text="", image=img_to_use if img_to_use else "", values=(
                sim_txt,
                seller_display,
                orig_txt,
                threat_txt,
                itm.get("price", ""),
                itm.get("title", ""),
                itm.get("item_id", "")
            ), tags=tuple(tags))

            if show_images and img_url:
                if img_url in self.thumb_cache:
                    self.tree.item(iid, image=self.thumb_cache[img_url])
                else:
                    self._fetch_thumb(iid, img_url, img_size)

            shown_count += 1

        self.count_var.set(f"{shown_count} listings shown | {len(self.discovered_items)} discovered")

    def _fetch_thumb(self, iid, url, size):
        """Asynchronously download and scale thumbnail with multi-row listener tracking."""
        if not hasattr(self, "_pending_thumb_iids"):
            self._pending_thumb_iids = {}
        if url in self._pending_thumb_iids:
            if iid not in self._pending_thumb_iids[url]:
                self._pending_thumb_iids[url].append(iid)
            return
        self._pending_thumb_iids[url] = [iid]

        def _w():
            for attempt in range(2):
                try:
                    data = download_image_bytes(url, timeout=10.0)
                    if not data:
                        raise ValueError("No data")
                    pimg = Image.open(io.BytesIO(data)).convert("RGBA")
                    pimg.thumbnail((size, size), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                    canvas.paste(pimg, ((size - pimg.width)//2, (size - pimg.height)//2))
                    
                    def _update_ui(c=canvas):
                        try:
                            if self.winfo_exists():
                                photo = ImageTk.PhotoImage(c, master=self)
                                self.thumb_cache[url] = photo
                                waiting = self._pending_thumb_iids.pop(url, [iid])
                                for wid in waiting:
                                    if self.tree.exists(wid):
                                        self.tree.item(wid, image=photo)
                        except Exception:
                            pass
                    self.after(0, _update_ui)
                    break
                except Exception:
                    if attempt == 0:
                        time.sleep(0.3)
                    else:
                        self._pending_thumb_iids.pop(url, None)
        threading.Thread(target=_w, daemon=True).start()

    def _open_selected_url(self, event=None):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            item_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
            
            target_url = ""
            for itm in self.discovered_items:
                if str(itm.get("item_id", "")).strip() == item_id:
                    target_url = itm.get("url", "")
                    break
            
            if target_url:
                webbrowser.open(target_url)
                return

            is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
            is_pb = "printblur" in self.target_item.get("url", "").lower() or "printblur" in str(self.target_item.get("marketplace", "")).lower()
            is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
            is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()

            if is_printerval:
                webbrowser.open(f"https://printerval.com/product-p{item_id}")
            elif is_pb:
                webbrowser.open(f"https://printblur.com/product-p{item_id}")
            elif is_rb:
                webbrowser.open(f"https://www.redbubble.com/i/product/{item_id}")
            elif is_meli:
                webbrowser.open(f"https://articulo.mercadolibre.com.mx/MLM-{item_id}" if not item_id.startswith("http") else item_id)
            elif item_id:
                webbrowser.open(f"https://www.ebay.com/itm/{item_id}")

    def _show_row_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            if row_id not in self.tree.selection():
                self.tree.selection_set(row_id)
            self.tree.focus(row_id)
        if not self.tree.selection(): return
        
        t = self.t
        menu = tk.Menu(self, tearoff=0, bg=t["panel"], fg=t["text"], activebackground=t["accent"], activeforeground="white")
        menu.add_command(label="📥 Add Selected to Results Table", command=self._add_to_results)
        menu.add_command(label="🏪 Enrich Seller Name(s)", command=self._enrich_selected_sellers)
        menu.add_command(label="➕ Add This Seller to Target Queue", command=self._add_single_seller_to_queue)
        menu.add_command(label="🏪 Add This Seller to Stores Box", command=self._add_single_seller_to_stores)
        menu.add_command(label="🛡 Whitelist This Seller (Authorized Dealer)", command=self._whitelist_selected_row_seller)
        menu.add_command(label="🌍 🚨 Resolve Origin & Threat Intel", command=self._resolve_selected_row_threat_intel)
        menu.add_separator()
        menu.add_command(label="☑ Select All (Ctrl+A)", command=self._select_all_rows)
        menu.add_command(label="🌐 Open in Browser", command=self._open_selected_url)
        menu.add_command(label="📋 Copy Listing URL", command=self._copy_selected_row_url)
        menu.add_command(label="👤 Copy Seller Username", command=self._copy_selected_row_seller)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _clean_seller_handle(self, text: str) -> str:
        """Strip badges, emojis, and status suffixes to extract pure seller username."""
        if not text:
            return ""
        s = str(text)
        for prefix in ("🛡", "🏠", "🎯", "⚡", "❓", "🚨", "👤", "🏪"):
            s = s.replace(prefix, "")
        for suffix in ("(Authorized)", "(Source Seller)", "(Targeted/Harvested)", "(Targeted)", "(Harvested)"):
            s = s.replace(suffix, "")
        return s.strip()

    def _resolve_selected_row_threat_intel(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if not sel: return
        vals = self.tree.item(sel)["values"]
        seller_raw = vals[1] if len(vals) > 1 else ""
        seller_handle = self._clean_seller_handle(seller_raw)
        if not seller_handle or seller_handle in ("Resolving...", "Unknown"):
            return

        def _w():
            scraper = getattr(self.parent, "scraper", None)
            if scraper:
                res = scraper.batch_resolve_seller_countries([seller_handle])
                if seller_handle in res:
                    c_val = res[seller_handle].get("country", "Unknown")
                    m_since = res[seller_handle].get("member_since", "")
                    ds = getattr(self.parent, "data_store", None)
                    if ds:
                        ds.set_seller_intel(seller_handle, c_val, member_since=m_since)
            self.after(0, self._populate_tree)
        threading.Thread(target=_w, daemon=True).start()

    def _copy_selected_row_url(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            item_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
            
            url = ""
            for itm in self.discovered_items:
                if str(itm.get("item_id", "")).strip() == item_id:
                    url = itm.get("url", "")
                    break
            
            if not url and item_id:
                is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
                is_pb = "printblur" in self.target_item.get("url", "").lower() or "printblur" in str(self.target_item.get("marketplace", "")).lower()
                is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
                is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()
                if is_printerval:
                    url = f"https://printerval.com/product-p{item_id}"
                elif is_pb:
                    url = f"https://printblur.com/product-p{item_id}"
                elif is_rb:
                    url = f"https://www.redbubble.com/i/product/{item_id}"
                elif is_meli:
                    url = f"https://articulo.mercadolibre.com.mx/MLM-{item_id}" if not item_id.startswith("http") else item_id
                else:
                    url = f"https://www.ebay.com/itm/{item_id}"

            if url:
                self.clipboard_clear()
                self.clipboard_append(url)
                self.count_var.set(f"📋 Copied listing URL: {url}")
                self.parent._log(f"📋 Copied URL to clipboard: {url}")

    def _copy_selected_row_seller(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if seller_handle and seller_handle not in ("Resolving...", "Unknown"):
                self.clipboard_clear()
                self.clipboard_append(seller_handle)
                self.count_var.set(f"👤 Copied seller handle: '{seller_handle}'")
                self.parent._log(f"👤 Copied seller handle to clipboard: {seller_handle}")
            else:
                self.count_var.set("⚠ No valid seller username on this listing.")

    def _whitelist_selected_row_seller(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if not seller_handle or seller_handle in ("Resolving...", "Unknown"):
                self.count_var.set("⚠ No valid seller handle to whitelist.")
                return
            ds = getattr(self.parent, "data_store", None)
            if ds and ds.is_seller_whitelisted(seller_handle):
                self.count_var.set(f"🛡 '{seller_handle}' is already Whitelisted.")
                return
            d_name = simpledialog.askstring("Authorized Dealership", f"Enter Dealership Name for '{seller_handle}' (optional):", initialvalue="Authorized Dealership", parent=self)
            if d_name is None:
                self.lift()
                return
            notes = simpledialog.askstring("Analyst Notes", f"Notes for '{seller_handle}' (optional):", initialvalue="Client Approved Whitelist", parent=self) or ""
            b_val = self.target_item.get("brand") or "General / All Brands"
            if ds:
                ds.add_to_whitelist(seller_handle, brand=b_val, dealer_name=d_name, notes=notes)
            self.parent._log(f"🛡 Added '{seller_handle}' to Authorized Whitelist ({b_val}).")
            self.count_var.set(f"🛡 Whitelisted '{seller_handle}' ({b_val})!")
            self._populate_tree()
            self.lift()

    def _append_to_parent_stores(self, seller_handle: str):
        """Append seller handle to the main Stores/Sellers input box without fusion or duplicates."""
        parent = self.parent
        if not hasattr(parent, "store_text"):
            return
        curr = parent.store_text.get("1.0", "end").strip()
        ph = getattr(parent, "store_placeholder", "").strip()
        if not curr or curr == ph:
            parent.store_text.delete("1.0", "end")
            parent.store_text.insert("1.0", seller_handle + "\n")
            parent.store_text.config(fg=parent.theme["text"])
        else:
            lines = [l.strip() for l in curr.splitlines() if l.strip()]
            existing_lowers = [l.lower() for l in lines]
            if seller_handle.lower() not in existing_lowers:
                lines.append(seller_handle)
                parent.store_text.delete("1.0", "end")
                parent.store_text.insert("1.0", "\n".join(lines) + "\n")
                parent.store_text.config(fg=parent.theme["text"])

    def _add_single_seller_to_stores(self):
        """Add highlighted seller(s) in tree directly to Stores text box (supports multi-select)."""
        selected_iids = self.tree.selection()
        if not selected_iids:
            sel = self.tree.focus()
            if sel:
                selected_iids = [sel]
        if not selected_iids:
            self.count_var.set("⚠ No listing selected.")
            return

        sellers = []
        for iid in selected_iids:
            vals = self.tree.item(iid)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if seller_handle and seller_handle not in ("Resolving...", "Unknown"):
                sellers.append(seller_handle)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No valid seller handles to add.")
            return

        for s in unique_sellers:
            self._append_to_parent_stores(s)

        if len(unique_sellers) == 1:
            self.count_var.set(f"🏪 Added '{unique_sellers[0]}' to Stores box!")
            self.parent._log(f"🏪 Added connected seller '{unique_sellers[0]}' to Stores box.")
        else:
            self.count_var.set(f"🏪 Added {len(unique_sellers)} selected seller(s) to Stores box!")
            self.parent._log(f"🏪 Added {len(unique_sellers)} connected seller(s) to Stores box: {', '.join(unique_sellers)}")

    def _add_all_to_stores(self):
        """Append all discovered / selected seller handles directly to main Stores/Sellers input."""
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown"):
                    sellers.append(s_clean)
        else:
            for r in self.discovered_items:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown"):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to add.")
            return

        for s in unique_sellers:
            self._append_to_parent_stores(s)

        self.count_var.set(f"🏪 Added {len(unique_sellers)} seller(s) to Stores box!")
        self.parent._log(f"🏪 Added {len(unique_sellers)} connected seller(s) to Stores box: {', '.join(unique_sellers)}")

    def _add_single_seller_to_queue(self):
        """Add highlighted seller(s) in tree to the Target Queue (supports multi-select)."""
        selected_iids = self.tree.selection()
        if not selected_iids:
            sel = self.tree.focus()
            if sel:
                selected_iids = [sel]
        if not selected_iids:
            self.count_var.set("⚠ No listing selected.")
            return

        sellers = []
        for iid in selected_iids:
            vals = self.tree.item(iid)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if seller_handle and seller_handle not in ("Resolving...", "Unknown"):
                sellers.append(seller_handle)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No valid seller handle to enqueue.")
            return

        parent = self.parent
        ds = getattr(parent, "data_store", None)
        whitelisted = [s for s in unique_sellers if (ds.is_seller_whitelisted(s) if ds else False)]
        if whitelisted:
            wl_msg = f"{len(whitelisted)} selected seller(s) are on your Authorized Whitelist:\n{', '.join(whitelisted)}\n\nDo you really want to target them?"
            if not messagebox.askyesno("Whitelisted Seller", wl_msg, parent=self):
                unique_sellers = [s for s in unique_sellers if s not in whitelisted]
                self.lift()
                if not unique_sellers:
                    return

        # 1. Check targeted brands in Brand Library / Presets
        target_brands = [k.split("/")[0] for k, v in parent.brand_states.items() if v == "target"]
        target_brands = list(dict.fromkeys(target_brands))
        if not target_brands:
            target_brands = [self.target_item.get("brand") or "General Brand"]

        custom_includes = [l.strip() for l in parent.include_text.get("1.0", "end").splitlines() if l.strip()]
        generic_excludes = parent._get_active_exclusions() if hasattr(parent, "_get_active_exclusions") else []
        condition = parent.condition_var.get() if hasattr(parent, "condition_var") else "all"
        platform_name = parent._get_current_platform_name() if hasattr(parent, "_get_current_platform_name") else "eBay"

        added_count = 0
        skipped_executed = 0
        for s in unique_sellers:
            self._append_to_parent_stores(s)
            for b_name in target_brands:
                if any(q.get("store", "").strip().lower() == s.strip().lower() and 
                       q.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       q.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for q in parent.queue):
                    continue
                if any(ex.get("store", "").strip().lower() == s.strip().lower() and 
                       ex.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       ex.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for ex in parent.executed_jobs):
                    skipped_executed += 1
                    parent._log(f"ℹ Skipped already-completed search on {platform_name}: [{parent._store_label(s, platform=platform_name)} ▸ {b_name}]")
                    continue

                b_terms = [k.split("/")[-1] for k, v in parent.brand_states.items() if v == "target" and k.split("/")[0] == b_name]
                includes = b_terms if b_terms else (custom_includes if custom_includes else [self.target_item.get("product_type") or b_name.lower()])

                entry = {
                    "store": s,
                    "brand": b_name,
                    "marketplace": platform_name,
                    "includes": list(includes),
                    "excludes": list(generic_excludes),
                    "condition": condition
                }
                parent.queue.append(entry)
                lbl = f"{parent._store_label(s, platform=platform_name)} ▸ {b_name} ({len(includes)} terms | {len(generic_excludes)} excl)"
                parent.queue_list.insert("end", lbl)
                added_count += 1

        if added_count > 0:
            if len(unique_sellers) == 1:
                parent._log(f"🎯 Queued connected seller '{unique_sellers[0]}' for {added_count} brand job(s) on {platform_name}.")
                self.count_var.set(f"🎯 Enqueued '{unique_sellers[0]}' for {added_count} brand(s) [{platform_name}]!")
            else:
                parent._log(f"🎯 Enqueued {added_count} batch jobs across {len(unique_sellers)} selected sellers on {platform_name}.")
                self.count_var.set(f"🎯 Enqueued {added_count} job(s) for {len(unique_sellers)} selected seller(s) [{platform_name}]!")
        else:
            self.count_var.set(f"ℹ Selected seller(s) already queued or previously executed.")

    def _copy_sellers(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown"):
                    sellers.append(s_clean)
        else:
            for r in self.discovered_items:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown"):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to copy.")
            return
        text = ", ".join(unique_sellers)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.count_var.set(f"📋 Copied {len(unique_sellers)} seller handles to clipboard!")
        self.parent._log(f"📋 Copied {len(unique_sellers)} seller handles to clipboard: {text}")

    def _add_to_results(self):
        """Add highlighted or all discovered network listings to the main Results table."""
        selected_iids = self.tree.selection()
        target_records = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                target_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
                for r in self.discovered_items:
                    if target_id and str(r.get("item_id", "")).strip() == target_id:
                        target_records.append(r)
                        break
        else:
            target_records = list(self.discovered_items)

        if not target_records:
            self.count_var.set("⚠ No discovered listings to add.")
            return

        added = 0
        detected_brand = self.target_item.get("brand") or "General Brand"
        ptype = self.target_item.get("product_type", "")
        is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
        is_pb = "printblur" in self.target_item.get("url", "").lower() or "printblur" in str(self.target_item.get("marketplace", "")).lower()
        is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
        is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()

        default_marketplace = "Printerval" if is_printerval else ("Printblur" if is_pb else ("Redbubble" if is_rb else ("Mercado Libre" if is_meli else "eBay")))

        for itm in target_records:
            t = itm.get("title", "")
            if hasattr(self.parent, "_auto_detect_brand_from_title"):
                detected_b, detected_pt = self.parent._auto_detect_brand_from_title(t)
                brand_name = detected_b if detected_b != "Unassigned" else detected_brand
                pt_name = detected_pt or ptype
            else:
                brand_name = detected_brand
                pt_name = ptype

            itm_id = str(itm.get("item_id", "")).strip()
            itm_url = itm.get("url", "")
            if not itm_url:
                if is_printerval and itm_id:
                    itm_url = f"https://printerval.com/product-p{itm_id}"
                elif is_pb and itm_id:
                    itm_url = f"https://printblur.com/product-p{itm_id}"
                elif is_rb and itm_id:
                    itm_url = f"https://www.redbubble.com/i/product/{itm_id}"
                elif is_meli and itm_id:
                    itm_url = f"https://articulo.mercadolibre.com.mx/MLM-{itm_id}"
                elif itm_id:
                    itm_url = f"https://www.ebay.com/itm/{itm_id}"

            mkt = itm.get("marketplace") or default_marketplace

            is_pod_itm = is_printerval or is_pb or is_rb or any(p in str(mkt).lower() or p in str(itm_url).lower() for p in ("printerval", "printblur", "redbubble", "teepublic", "zazzle", "spreadshirt", "threadless", "teespring"))
            row = {
                "brand": brand_name,
                "product_type": pt_name,
                "title": t,
                "item_id": itm_id,
                "price": normalize_price_string(itm.get("price", "")),
                "seller": itm.get("seller", "") or "Unknown",
                "location": itm.get("location", "") or ("United States" if is_pod_itm else ""),
                "image_url": itm.get("image_url", ""),
                "url": itm_url,
                "marketplace": mkt,
                "similarity": itm.get("similarity", "Connected Network Match"),
                "threat_badge": "👕 POD Print Syndicate" if is_pod_itm else itm.get("threat_badge", ""),
                "threat_score": 65 if is_pod_itm else safe_int_score(itm.get("threat_score", 0))
            }

            # Dedup check
            dedup_key = itm_url.lower().split("?")[0] if itm_url else itm_id
            if dedup_key and dedup_key not in self.parent.seen_item_ids:
                if itm_id:
                    self.parent.seen_item_ids.add(itm_id)
                    self.parent.seen_item_ids.add(f"{mkt}_{itm_id}")
                if itm_url:
                    self.parent.seen_item_ids.add(dedup_key)
                self.parent.results.append(row)
                try:
                    if hasattr(self.parent, "data_store"):
                        self.parent.data_store.add_or_update_listing(row)
                except Exception:
                    pass
                added += 1

        if hasattr(self.parent, "_repopulate_results_table"):
            self.parent._repopulate_results_table()
        if hasattr(self.parent, "_log"):
            self.parent._log(f"📥 Added {added} discovered network listings to Results table ({default_marketplace}).")
        self.count_var.set(f"✓ Added {added} discovered listings to Results!")

    def _add_sellers_to_queue(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown"):
                    sellers.append(s_clean)
        else:
            for r in self.discovered_items:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown"):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to enqueue.")
            return

        parent = self.parent
        ds = getattr(parent, "data_store", None)
        eligible_sellers = [s for s in unique_sellers if not (ds.is_seller_whitelisted(s) if ds else False)]
        skipped_count = len(unique_sellers) - len(eligible_sellers)

        if not eligible_sellers:
            self.count_var.set(f"🛡 All {len(unique_sellers)} sellers are Authorized Dealerships (Skipped).")
            return

        # Check targeted brands in Brand Library
        target_brands = [k.split("/")[0] for k, v in parent.brand_states.items() if v == "target"]
        target_brands = list(dict.fromkeys(target_brands))
        if not target_brands:
            target_brands = [self.target_item.get("brand") or "General Brand"]

        custom_includes = [l.strip() for l in parent.include_text.get("1.0", "end").splitlines() if l.strip()]
        generic_excludes = parent._get_active_exclusions() if hasattr(parent, "_get_active_exclusions") else []
        condition = parent.condition_var.get() if hasattr(parent, "condition_var") else "all"
        platform_name = parent._get_current_platform_name() if hasattr(parent, "_get_current_platform_name") else "eBay"

        added_count = 0
        skipped_executed = 0
        for s in eligible_sellers:
            self._append_to_parent_stores(s)
            for b_name in target_brands:
                if any(q.get("store", "").strip().lower() == s.strip().lower() and 
                       q.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       q.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for q in parent.queue):
                    continue
                if any(ex.get("store", "").strip().lower() == s.strip().lower() and 
                       ex.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       ex.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for ex in parent.executed_jobs):
                    skipped_executed += 1
                    continue
                b_terms = [k.split("/")[-1] for k, v in parent.brand_states.items() if v == "target" and k.split("/")[0] == b_name]
                includes = b_terms if b_terms else (custom_includes if custom_includes else [self.target_item.get("product_type") or b_name.lower()])

                entry = {
                    "store": s,
                    "brand": b_name,
                    "marketplace": platform_name,
                    "includes": list(includes),
                    "excludes": list(generic_excludes),
                    "condition": condition
                }
                parent.queue.append(entry)
                lbl = f"{parent._store_label(s, platform=platform_name)} ▸ {b_name} ({len(includes)} terms | {len(generic_excludes)} excl)"
                parent.queue_list.insert("end", lbl)
                added_count += 1

        msg = f"Enqueued {added_count} job(s) for {len(eligible_sellers)} seller(s)"
        if skipped_count > 0:
            msg += f" (Shielded {skipped_count} Whitelisted Dealers)"
        if skipped_executed > 0:
            msg += f" (Skipped {skipped_executed} already-completed searches)"
        parent._log(f"🎯 Enqueued {added_count} batch jobs across {len(eligible_sellers)} sellers on {platform_name} (Shielded {skipped_count} whitelisted dealers, skipped {skipped_executed} already run).")
        self.count_var.set(f"🎯 {msg}")

    def _enrich_selected_sellers(self):
        """Enrich real merchant/artist names across discovered items in the Hunter Modal."""
        selected_iids = self.tree.selection()
        target_items = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                item_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
                for it in self.discovered_items:
                    if str(it.get("item_id", "")).strip() == item_id:
                        target_items.append(it)
                        break
        else:
            target_items = list(self.discovered_items)

        if not target_items:
            messagebox.showinfo("Enrich Sellers", "No discovered listings to enrich.", parent=self)
            return

        items_to_enrich = [
            it for it in target_items 
            if not it.get("seller") or it.get("seller") in ("Printerval Creator", "Printblur Creator", "Printblur Seller", "Redbubble Creator", "Unknown", "Resolving...") or selected_iids
        ]
        if not items_to_enrich:
            items_to_enrich = list(target_items)

        is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
        is_pb = "printblur" in self.target_item.get("url", "").lower() or "printblur" in str(self.target_item.get("marketplace", "")).lower()
        is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
        is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()

        self.status_lbl.configure(text=f"🏪 Enriching real merchant/artist names for {len(items_to_enrich)} listing(s)...", fg=self.t["accent"])
        self.pbar.pack(side="right", padx=(8, 0))
        self.pbar.start(12)

        def _w():
            try:
                if is_printerval:
                    scraper = getattr(self.parent, "printerval_scraper", None)
                    if not scraper:
                        from printerval_scraper import PrintervalScraper
                        scraper = PrintervalScraper(headless=True)
                    
                    def _prog(cur, tot, it):
                        s_name = it.get("seller", "")
                        if s_name and hasattr(self.parent, "_propagate_enriched_seller"):
                            self.parent._propagate_enriched_seller(it, s_name)
                        sibs = set(str(s).strip() for s in it.get("sibling_ids", []) if s)
                        sib_urls = set(str(u).split("?")[0].strip().lower() for u in it.get("sibling_urls", []) if u)
                        if sibs or sib_urls:
                            for other in self.discovered_items:
                                if other is it: continue
                                oid = str(other.get("item_id", "")).strip()
                                ourl = str(other.get("url", "")).split("?")[0].strip().lower()
                                if (oid and oid in sibs) or (ourl and ourl in sib_urls) or any(s in ourl for s in sibs):
                                    other["seller"] = s_name
                        self.after(0, lambda: self.status_lbl.configure(text=f"🏪 Enriching Sellers [{cur}/{tot}] -> '{s_name}'"))
                        self.after(0, self._populate_tree)

                    scraper.enrich_seller_info(items_to_enrich, progress_callback=_prog)
                elif is_pb:
                    scraper = getattr(self.parent, "printblur_scraper", None)
                    if not scraper:
                        from printblur_scraper import PrintblurScraper
                        scraper = PrintblurScraper(headless=True)
                    
                    def _prog(cur, tot, it):
                        s_name = it.get("seller", "")
                        if s_name and hasattr(self.parent, "_propagate_enriched_seller"):
                            self.parent._propagate_enriched_seller(it, s_name)
                        sibs = set(str(s).strip() for s in it.get("sibling_ids", []) if s)
                        sib_urls = set(str(u).split("?")[0].strip().lower() for u in it.get("sibling_urls", []) if u)
                        if sibs or sib_urls:
                            for other in self.discovered_items:
                                if other is it: continue
                                oid = str(other.get("item_id", "")).strip()
                                ourl = str(other.get("url", "")).split("?")[0].strip().lower()
                                if (oid and oid in sibs) or (ourl and ourl in sib_urls) or any(s in ourl for s in sibs):
                                    other["seller"] = s_name
                        self.after(0, lambda: self.status_lbl.configure(text=f"🏪 Enriching Creators [{cur}/{tot}] -> '{s_name}'"))
                        self.after(0, self._populate_tree)

                    scraper.enrich_seller_info(items_to_enrich, progress_callback=_prog)
                elif is_rb:
                    scraper = getattr(self.parent, "redbubble_scraper", None)
                    if not scraper:
                        from redbubble_scraper import RedbubbleScraper
                        scraper = RedbubbleScraper(headless=True)
                    
                    def _prog(cur, tot, it):
                        s_name = it.get("seller", "")
                        self.after(0, lambda: self.status_lbl.configure(text=f"🏪 Enriching Artists [{cur}/{tot}] -> '{s_name}'"))
                        self.after(0, self._populate_tree)

                    scraper.enrich_seller_info(items_to_enrich, progress_callback=_prog)
                elif is_meli:
                    scraper = getattr(self.parent, "mercadolibre_scraper", None)
                    if not scraper:
                        from mercadolibre_scraper import MercadoLibreScraper
                        scraper = MercadoLibreScraper(headless=False)
                    
                    def _prog(cur, tot, it):
                        s_name = it.get("seller", "")
                        self.after(0, lambda: self.status_lbl.configure(text=f"🏪 Enriching Merchants [{cur}/{tot}] -> '{s_name}'"))
                        self.after(0, self._populate_tree)

                    scraper.enrich_seller_info(items_to_enrich, progress_callback=_prog)
                else:
                    scraper = getattr(self.parent, "scraper", None)
                    if scraper and hasattr(scraper, "enrich_ebay_seller_info"):
                        scraper.enrich_ebay_seller_info(items_to_enrich)

            except Exception as e:
                logger.exception("Error enriching sellers in ConnectedNetworkModal")
            
            def _done():
                self.pbar.stop()
                self.pbar.pack_forget()
                self._populate_tree()
                unique_sellers = set(r["seller"] for r in self.discovered_items if r.get("seller") and r.get("seller") not in ("Printerval Creator", "Printblur Creator", "Printblur Seller", "Redbubble Creator", "Unknown", "Resolving..."))
                self.status_lbl.configure(text=f"✅ Enrichment Complete: {len(unique_sellers)} unique creators/merchants identified across discovered network.", fg=self.t["success"])
            
            self.after(0, _done)

        threading.Thread(target=_w, daemon=True).start()


