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
#  REVERSE VISUAL DREDGE RESULTS & THREAT CLONE DISCOVERY MODAL
# ══════════════════════════════════════════════════════════════════════════════
class ReverseVisualModal(tk.Toplevel):
    """
    Dedicated Discovery & Triage Modal for Reverse Visual Search / Visual Threat Catalog Clones.
    Presents the reference photo alongside discovered marketplace listings with side-by-side
    perceptual verification previews, seller intel, match similarity %, and 1-click batch actions.
    """
    def __init__(self, parent, hits: list, target_img, label: str = "Visual Reference", marketplace: str = "eBay", region: Optional[str] = None, target_phash: str = ""):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.hits = hits or []
        self.target_img = target_img
        self.label = label
        self.marketplace = parent._get_current_platform_name(marketplace) if hasattr(parent, "_get_current_platform_name") else (marketplace or "eBay")
        self.region = region
        self.target_phash = target_phash
        self.t = parent.theme
        self.thumb_cache = {}
        self.sort_directions = {}

        loc_str = f" [{region}]" if region else ""
        self.title(f"📸 Reverse Visual Dredge Discovery — {self.marketplace}{loc_str} ({len(self.hits)} Matches)")
        self.geometry("1200x780")
        self.configure(bg=self.t["bg"])
        self.minsize(980, 620)
        self.parent._apply_dark_titlebar(self)

        self._build_ui()
        self._populate_tree()

        # Center modal relative to parent window and reveal
        self.parent._center_window(self, 1200, 780)
        self.lift()
        self.focus_force()

        self.after(200, self._enrich_all_hits)

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

        tag_lbl = tk.Label(badge_row, text="📸 TARGET REFERENCE PHOTO", font=("Segoe UI", 8, "bold"), bg=t["accent"], fg="white", padx=8, pady=2)
        tag_lbl.pack(side="left", padx=(0, 8))

        loc_str = f" [{self.region}]" if self.region else ""
        tk.Label(badge_row, text=f"Marketplace: {self.marketplace}{loc_str}", font=("Segoe UI", 8, "bold"), bg=t["entry_bg"], fg=t["subtext"], padx=8, pady=2).pack(side="left", padx=(0, 8))

        title_lbl = tk.Label(info_box, text=f"Target: {self.label}", font=FONT_HEAD, bg=t["panel"], fg=t["text"], wraplength=820, justify="left")
        title_lbl.pack(anchor="w")

        verified_count = sum(1 for h in self.hits if h.get("is_verified_match", h.get("distance", 99) <= 18))
        sub_text = f"⚡ Total Discovered: {verified_count} verified photo clones | {len(self.hits)} total candidate listings evaluated"
        sub_lbl = tk.Label(info_box, text=sub_text, font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        sub_lbl.pack(anchor="w", pady=(4, 0))

        # ── 2. Filters toolbar ────────────────────────────────────────────────
        f_row = tk.Frame(self, bg=t["panel"], padx=12, pady=5, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        f_row.pack(side="top", fill="x", padx=12, pady=(2, 4))

        tk.Label(f_row, text="Thumbnails:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(0, 4))
        self.thumb_size_var = tk.StringVar(value="Medium (100px)")
        self.thumb_size_combo = ttk.Combobox(f_row, textvariable=self.thumb_size_var, values=list(THUMB_CONFIG.keys()), width=14, state="readonly", font=FONT_SM)
        self.thumb_size_combo.pack(side="left", padx=(0, 10))
        self.thumb_size_combo.bind("<<ComboboxSelected>>", self._on_thumb_size_changed)

        match_filters = [
            "(All Harvested Candidates)",
            "🎯 Verified Clones Only",
            "🎯 Exact Matches (90%+)",
            "🖼 High Similarity (80%+)",
            "🔍 Close Candidates (70%+)",
            "📷 Broad Visual Sweep (50%+)"
        ]
        default_match_filter = "🎯 Verified Clones Only" if verified_count > 0 else "(All Harvested Candidates)"
        self.match_filter_var = tk.StringVar(value=default_match_filter)
        self.match_filter_combo = ttk.Combobox(f_row, textvariable=self.match_filter_var, values=match_filters, width=28, state="readonly", font=FONT_SM)
        self.match_filter_combo.pack(side="left", padx=(0, 10))
        self.match_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_tree())

        self.hide_same_seller_var = tk.BooleanVar(value=False)
        same_seller_cb = tk.Checkbutton(f_row, text="Hide Same Seller", variable=self.hide_same_seller_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t.get("check_select_bg", t["accent"]), activebackground=t["panel"], font=FONT_SM)
        same_seller_cb.pack(side="left", padx=(0, 8))

        self.hide_wl_var = tk.BooleanVar(value=False)
        wl_cb = tk.Checkbutton(f_row, text="🛡 Hide Whitelisted Dealers", variable=self.hide_wl_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t.get("check_select_bg", t["accent"]), activebackground=t["panel"], font=FONT_SM)
        wl_cb.pack(side="left", padx=(0, 8))

        # ── 3. Action Toolbar (Pack bottom first to prevent table overflow clipping) ──
        btn_bar = tk.Frame(self, bg=t["panel"], padx=10, pady=8, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x", padx=12, pady=(4, 8))

        self.count_var = tk.StringVar(value=f"{len(self.hits)} candidate listings discovered")
        count_lbl = tk.Label(btn_bar, textvariable=self.count_var, bg=t["panel"], fg=t["text"], font=FONT_HEAD)
        count_lbl.pack(side="left")

        tk.Button(btn_bar, text="✕ Close", command=self.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="🔄 Enrich Intel", command=self._enrich_all_hits, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📋 Copy Handles", command=self._copy_sellers, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="🏪 To Stores", command=self._add_all_to_stores, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📥 To Table", command=self._add_to_results, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="➕ Queue Sellers", command=self._add_sellers_to_queue, bg=t["accent"], fg="white", relief="flat", padx=10, pady=4, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)

        # ── 4. Discovered Network Table ───────────────────────────────────────
        table_frame = tk.Frame(self, bg=t["bg"])
        table_frame.pack(side="top", fill="both", expand=True, padx=12, pady=4)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("similarity", "seller", "origin", "threat", "price", "title", "item_id")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="tree headings", selectmode="extended", style="ReverseVisual.Treeview")

        style = ttk.Style()
        style.configure("ReverseVisual.Treeview", background=t["entry_bg"], foreground=t["text"], fieldbackground=t["entry_bg"], rowheight=108, font=FONT_SM)
        style.configure("ReverseVisual.Treeview.Heading", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9, "bold"))
        style.map("ReverseVisual.Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["select_fg"])])

        self.tree.tag_configure("whitelisted", foreground=t["success"])
        self.tree.tag_configure("clone", foreground=t.get("danger", "#E63946"))
        self.tree.tag_configure("candidate", foreground=t["subtext"])

        self.tree.heading("#0", text="Photo Preview", anchor="center")
        self.tree.column("#0", width=120, minwidth=100, anchor="center", stretch=False)

        self.col_cfg = {
            "similarity": ("Match Type / Visual Fingerprint", 185),
            "seller": ("Discovered Seller", 140),
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

    def _load_source_image(self):
        img_src = self.target_img
        if not img_src:
            self.src_img_lbl.configure(text="No Photo\nAvailable")
            return

        def _w():
            try:
                if isinstance(img_src, Image.Image):
                    pimg = img_src.copy()
                elif isinstance(img_src, str) and os.path.exists(img_src):
                    pimg = Image.open(img_src).convert("RGBA")
                elif isinstance(img_src, str) and img_src.startswith("http"):
                    data = download_image_bytes(img_src, timeout=8)
                    if not data:
                        raise ValueError("No data")
                    pimg = Image.open(io.BytesIO(data)).convert("RGBA")
                else:
                    self.after(0, lambda: self.src_img_lbl.configure(text="Photo\nUnavailable"))
                    return

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
                self.after(0, lambda: self.src_img_lbl.configure(text="Photo\nUnavailable"))
        threading.Thread(target=_w, daemon=True).start()

    def _on_thumb_size_changed(self, event=None):
        size_key = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_key, THUMB_CONFIG["Medium (100px)"])
        style = ttk.Style()
        style.configure("ReverseVisual.Treeview", rowheight=cfg["rowheight"])
        self.tree.configure(show=cfg["show"], style="ReverseVisual.Treeview")
        self.tree.column("#0", width=cfg["col_width"], minwidth=cfg["col_width"], anchor="center", stretch=False)
        self.tree.heading("#0", text="Photo Preview" if cfg["img_size"] > 0 else "", anchor="center")
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
        total_count = len(self.hits)
        if sel_count > 0:
            self.count_var.set(f"{vis_count} listings shown ({sel_count} selected) | {total_count} total candidates")
        else:
            self.count_var.set(f"{vis_count} listings shown | {total_count} total candidates")

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        hide_wl = self.hide_wl_var.get()
        hide_same_seller = self.hide_same_seller_var.get()
        match_filter = self.match_filter_var.get()

        size_name = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_name, THUMB_CONFIG.get("Medium (100px)", {"rowheight": 110, "img_size": 100, "col_width": 116}))
        img_size = cfg.get("img_size", 0)
        show_images = img_size > 0

        ds = getattr(self.parent, "data_store", None)
        shown_count = 0
        seen_sellers = set()

        for itm in self.hits:
            seller = (itm.get("seller") or "Unknown").strip()
            seller_clean = seller.lower()
            is_wl = ds.is_seller_whitelisted(seller) if ds else False
            is_same = bool(seller_clean in seen_sellers)

            if hide_wl and is_wl:
                continue
            if hide_same_seller and is_same:
                continue

            seen_sellers.add(seller_clean)

            sim_txt = itm.get("match_type") or itm.get("threat_badge") or itm.get("similarity") or "🎯 Exact Photo Match (100%)"
            dist = itm.get("distance", 0)
            is_verified = itm.get("is_verified_match", dist <= 18)

            if match_filter == "🎯 Verified Clones Only" and not is_verified:
                continue
            elif "Exact Matches" in match_filter and dist > 6:
                continue
            elif "High Similarity" in match_filter and dist > 12:
                continue
            elif "Close Candidates" in match_filter and dist > 18:
                continue
            elif "50%+" in match_filter and dist > 32:
                continue

            if is_wl:
                seller_display = f"🛡 {seller} (Authorized)"
            else:
                seller_display = f"⚡ {seller}"

            # Threat Intel from DataStore & Item Location
            cached_intel = ds.get_seller_intel(seller) if ds else {}
            seller_country = cached_intel.get("country", "") if cached_intel else ""
            loc_val = itm.get("location", "")
            assessment = ds.compute_threat_assessment(seller_country or loc_val, loc_val) if ds else {}
            c_name = assessment.get("country", "Unknown")
            orig_txt = f"{assessment.get('flag', '❓')} {c_name}" if c_name not in ("Unknown", "Unresolved", "") else (f"📍 {loc_val}" if loc_val else "❓ Unresolved")
            threat_txt = assessment.get("badge", ("🚨 Rogue Photo Clone" if is_verified else "Candidate"))

            price_txt = str(itm.get("price", "N/A"))
            title_txt = str(itm.get("title", "Unknown Title"))
            item_id_txt = str(itm.get("item_id", "N/A"))

            if is_wl:
                row_tag = "whitelisted"
            elif is_verified:
                row_tag = "clone"
            else:
                row_tag = "candidate"

            iid = self.tree.insert("", "end", text="", values=(
                sim_txt,
                seller_display,
                orig_txt,
                threat_txt,
                price_txt,
                title_txt,
                item_id_txt
            ), tags=(row_tag,))

            shown_count += 1

            if show_images and itm.get("image_url"):
                self._load_row_thumbnail(iid, itm["image_url"], img_size)

        self.count_var.set(f"{shown_count} listings shown across {len(seen_sellers)} seller account(s)")

    def _load_row_thumbnail(self, iid, url, img_size):
        if not url:
            return
        if iid in self.thumb_cache:
            try:
                self.tree.item(iid, image=self.thumb_cache[iid])
            except Exception:
                pass
            return

        def _w():
            try:
                if hasattr(self.parent, "raw_img_cache") and url in self.parent.raw_img_cache:
                    pimg = self.parent.raw_img_cache[url].copy()
                else:
                    data = download_image_bytes(url, timeout=6)
                    if not data:
                        raise ValueError("No data")
                    pimg = Image.open(io.BytesIO(data)).convert("RGBA")

                pimg.thumbnail((img_size, img_size), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
                canvas.paste(pimg, ((img_size - pimg.width)//2, (img_size - pimg.height)//2))

                def _set(c=canvas):
                    try:
                        if self.winfo_exists() and self.tree.exists(iid):
                            photo = ImageTk.PhotoImage(c, master=self)
                            self.thumb_cache[iid] = photo
                            self.tree.item(iid, image=photo)
                    except Exception:
                        pass
                self.after(0, _set)
            except Exception:
                pass
        threading.Thread(target=_w, daemon=True).start()

    def _sort_by_column(self, col):
        if not self.hits:
            return
        descending = self.sort_directions.get(col, False)
        self.sort_directions[col] = not descending
        ds = getattr(self.parent, "data_store", None)

        def get_sort_key(item):
            seller = (item.get("seller") or "").strip()
            if col == "origin":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else ""
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("country", "Unknown").lower()
            elif col == "threat":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else ""
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("score", 0)
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

        self.hits.sort(key=get_sort_key, reverse=descending)
        self._populate_tree()

    def _enrich_all_hits(self):
        """Resolve seller handles and country origin threat intelligence for all visual clone matches."""
        ds = getattr(self.parent, "data_store", None)
        if not self.hits:
            return
        self.count_var.set(f"🏪 Enriching {len(self.hits)} visual clone merchant account(s)...")

        INVALID_HANDLES = {"ebay merchant", "unknown", "resolving...", "", "i.html", "m.html", "sch", "usr", "str", "itm"}

        def _is_bad(name):
            if not name: return True
            n = str(name).strip().lower()
            return n in INVALID_HANDLES or n.endswith(".html") or n.endswith(".htm")

        def _worker():
            for itm in self.hits:
                s = itm.get("seller", "")
                url = itm.get("url") or (f"https://www.ebay.com/itm/{itm.get('item_id', '')}" if itm.get("item_id") else "")
                if url and _is_bad(s):
                    try:
                        import batch_importer
                        res = batch_importer.fetch_single_listing(url, headless=True)
                        if res:
                            cand_s = res.get("seller", "")
                            if cand_s and not _is_bad(cand_s):
                                itm["seller"] = cand_s
                                s = cand_s
                            if res.get("price") and res.get("price") not in ("$0.00", ""):
                                itm["price"] = res["price"]
                            if res.get("location") and res.get("location") not in ("Unknown", ""):
                                itm["location"] = res["location"]
                            if res.get("title") and not res.get("title").startswith("Imported Listing"):
                                itm["title"] = res["title"]
                    except Exception as e:
                        logger.debug(f"Visual clone fetch error on {url}: {e}")

                # Resolve seller threat intel / country if needed
                if s and not _is_bad(s) and ds:
                    intel = ds.get_seller_intel(s)
                    if not intel or not intel.get("country") or intel.get("country") == "Unknown":
                        try:
                            resolved = self.parent.scraper.resolve_seller_country(s)
                            if resolved and resolved.get("country") and resolved["country"] != "Unknown":
                                ds.set_seller_intel(s, resolved["country"], member_since=resolved.get("member_since", ""))
                        except Exception as e:
                            logger.debug(f"Visual clone country resolve error for {s}: {e}")

            def _finish():
                if self.winfo_exists():
                    self._populate_tree()
                    unique_sellers = {r.get("seller", "") for r in self.hits if r.get("seller") and not _is_bad(r.get("seller"))}
                    self.count_var.set(f"{len(self.hits)} photo clone listings discovered across {len(unique_sellers)} verified merchant account(s)")

            self.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _clean_seller_handle(self, raw_str: str) -> str:
        s = str(raw_str).strip()
        for prefix in ("⚡", "🏠", "🛡", "🎯", "🔗", "👤"):
            s = s.replace(prefix, "")
        for suffix in ("(Authorized)", "(Source Seller)", "(Targeted/Harvested)"):
            s = s.replace(suffix, "")
        return s.strip()

    def _append_to_parent_stores(self, seller_handle: str):
        parent = self.parent
        if not hasattr(parent, "store_text") or not seller_handle:
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

    def _add_all_to_stores(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown", ""):
                    sellers.append(s_clean)
        else:
            for r in self.hits:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown", ""):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to add.")
            return

        for s in unique_sellers:
            self._append_to_parent_stores(s)

        if hasattr(self.parent, "store_full_sweep_var"):
            self.parent.store_full_sweep_var.set(True)

        self.count_var.set(f"🏪 Added {len(unique_sellers)} seller(s) to Stores box & enabled Full Store Sweep!")
        self.parent._log(f"🏪 Added {len(unique_sellers)} discovered visual clone sellers to Stores box: {', '.join(unique_sellers)}")

    def _add_to_results(self):
        selected_iids = self.tree.selection()
        target_records = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                for r in self.hits:
                    target_id = str(vals[6]).strip() if len(vals) > 6 else ""
                    if target_id and str(r.get("item_id")) == target_id:
                        target_records.append(r)
                        break
        else:
            target_records = self.hits

        added = 0
        for itm in target_records:
            t = itm.get("title", "")
            detected_b, detected_pt = self.parent._auto_detect_brand_from_title(t) if hasattr(self.parent, "_auto_detect_brand_from_title") else ("Unassigned", "")
            brand_name = detected_b if detected_b != "Unassigned" else (self.label or "Visual Sweep")
            pt_name = detected_pt or "Visual Clone"

            row = {
                "brand": brand_name,
                "product_type": pt_name,
                "title": t,
                "item_id": str(itm.get("item_id", "")),
                "price": normalize_price_string(itm.get("price", "")),
                "seller": itm.get("seller", ""),
                "location": itm.get("location", ""),
                "image_url": itm.get("image_url", ""),
                "threat_badge": itm.get("threat_badge", "🚨 Visual Clone (100%)"),
                "threat_score": max(safe_int_score(itm.get("threat_score")), 95),
                "url": itm.get("url", f"https://www.ebay.com/itm/{itm.get('item_id', '')}"),
                "marketplace": self.marketplace
            }
            if row["item_id"] and row["item_id"] not in self.parent.seen_item_ids:
                self.parent.seen_item_ids.add(row["item_id"])
                self.parent.results.append(row)
                added += 1
            else:
                # Update existing row with threat badge
                for r_item in self.parent.results:
                    if str(r_item.get("item_id")) == row["item_id"]:
                        r_item["threat_badge"] = row["threat_badge"]
                        r_item["threat_score"] = row["threat_score"]
                        break

        if hasattr(self.parent, "_repopulate_results_table"):
            self.parent._repopulate_results_table()
        if hasattr(self.parent, "_log"):
            self.parent._log(f"📸 Added/updated {len(target_records)} visual clone listings in Results table ({added} newly added).")
        self.count_var.set(f"✓ Added/updated {len(target_records)} visual clone listings in Results table!")

    def _add_sellers_to_queue(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown", ""):
                    sellers.append(s_clean)
        else:
            for r in self.hits:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown", ""):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No valid seller handles to queue.")
            return

        parent = self.parent
        ds = getattr(parent, "data_store", None)
        eligible_sellers = [s for s in unique_sellers if not (ds.is_seller_whitelisted(s) if ds else False)]
        skipped_count = len(unique_sellers) - len(eligible_sellers)

        if not eligible_sellers:
            self.count_var.set(f"🛡 All {len(unique_sellers)} sellers are Authorized Dealerships (Skipped).")
            return

        target_brands = [k.split("/")[0] for k, v in parent.brand_states.items() if v == "target"]
        target_brands = list(dict.fromkeys(target_brands))
        if not target_brands:
            target_brands = ["Full Store Sweep"]

        custom_includes = [l.strip() for l in parent.include_text.get("1.0", "end").splitlines() if l.strip()]
        generic_excludes = parent._get_active_exclusions() if hasattr(parent, "_get_active_exclusions") else []
        condition = parent.condition_var.get() if hasattr(parent, "condition_var") else "all"
        platform_name = self.marketplace or "eBay"

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
                if b_name == "Full Store Sweep":
                    includes = ["*"]
                else:
                    includes = b_terms if b_terms else (custom_includes if custom_includes else [b_name.lower()])

                entry = {
                    "store": s,
                    "brand": b_name,
                    "marketplace": platform_name,
                    "includes": list(includes),
                    "excludes": list(generic_excludes),
                    "condition": condition
                }
                parent.queue.append(entry)
                lbl = f"{parent._store_label(s, platform=platform_name)} ▸ {b_name} ({len(includes)} terms | {len(generic_excludes)} excl)" if b_name != "Full Store Sweep" else f"{parent._store_label(s, platform=platform_name)} ▸ 🏪 Full Store Sweep"
                parent.queue_list.insert("end", lbl)
                added_count += 1

        msg = f"Enqueued {added_count} job(s) for {len(eligible_sellers)} seller(s)"
        if skipped_count > 0:
            msg += f" (Shielded {skipped_count} Whitelisted Dealers)"
        if skipped_executed > 0:
            msg += f" (Skipped {skipped_executed} already-completed searches)"
        parent._log(f"🎯 Enqueued {added_count} batch jobs across {len(eligible_sellers)} visual clone sellers on {platform_name}.")
        self.count_var.set(f"🎯 {msg}")

    def _copy_sellers(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown", ""):
                    sellers.append(s_clean)
        else:
            for r in self.hits:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown", ""):
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

    def _open_selected_url(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        item_id = str(vals[6]).strip() if len(vals) > 6 else ""
        for r in self.hits:
            if str(r.get("item_id")) == item_id:
                u = r.get("url")
                if u:
                    webbrowser.open(u)
                return
        if item_id:
            webbrowser.open(f"https://www.ebay.com/itm/{item_id}")

    def _show_row_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        vals = self.tree.item(row_id)["values"]
        seller_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
        item_id = str(vals[6]).strip() if len(vals) > 6 else ""

        menu = tk.Menu(self, tearoff=0, bg=self.t["panel"], fg=self.t["text"], activebackground=self.t["select_bg"], activeforeground=self.t["select_fg"])
        menu.add_command(label="🌐 Open Listing in Browser", command=self._open_selected_url)
        if seller_clean and seller_clean not in ("Resolving...", "Unknown", ""):
            menu.add_command(label=f"🏪 Add '{seller_clean}' to Stores Box", command=lambda: self._append_to_parent_stores(seller_clean))
            menu.add_command(label=f"📋 Copy Seller '{seller_clean}'", command=lambda: [self.clipboard_clear(), self.clipboard_append(seller_clean)])
        menu.add_separator()
        menu.add_command(label="📥 Add This Listing to Results", command=self._add_to_results)
        menu.tk_popup(event.x_root, event.y_root)

