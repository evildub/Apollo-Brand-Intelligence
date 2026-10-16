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


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHORIZED DEALERS & MERCHANT WHITELIST MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class WhitelistManagerModal(tk.Toplevel):
    """
    Authorized Dealer & Client Approved Merchant Whitelist Manager.
    Allows analysts to maintain persistent lists of authorized storefronts,
    bulk import dealership lists from client emails/Excel, and auto-shield
    legitimate distributors from false-positive scraping and enforcement.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.t = parent.theme
        self.data_store = parent.data_store
        
        self.title("🛡 Authorized Dealers & Merchant Whitelist Manager")
        self.geometry("980x640")
        self.configure(bg=self.t["bg"])
        self.minsize(800, 500)
        self.parent._apply_dark_titlebar(self)
        
        self._build_ui()
        self._refresh_table()

        # Center modal relative to parent window and reveal
        self.parent._center_window(self, 980, 640)
        self.lift()
        self.focus_force()

    def _build_ui(self):
        t = self.t

        # ── 1. Top Header Card ────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=t["panel"], padx=16, pady=12, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        hdr.pack(side="top", fill="x", padx=12, pady=(12, 6))

        title_row = tk.Frame(hdr, bg=t["panel"])
        title_row.pack(fill="x")
        tk.Label(title_row, text="🛡", font=("Segoe UI", 12), bg=t["panel"], fg=t["accent"]).pack(side="left")
        tk.Label(title_row, text="AUTHORIZED DEALERS & CLIENT APPROVED WHITELIST", font=("Segoe UI", 11, "bold"), bg=t["panel"], fg=t["accent"]).pack(side="left", padx=(4, 0))
        self.stat_lbl = tk.Label(title_row, text="0 Authorized Dealers Registered", font=("Segoe UI", 9, "bold"), bg=t["entry_bg"], fg=t["success"], padx=8, pady=2)
        self.stat_lbl.pack(side="right")

        desc_lbl = tk.Label(hdr, text="Whitelisted dealers and storefronts are automatically shielded across all scrapers, threat intel modules, and syndicate hunters to prevent false-positive enforcement.", font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        desc_lbl.pack(anchor="w", pady=(4, 0))

        # ── 2. Filter & Search Toolbar ────────────────────────────────────────
        filter_bar = tk.Frame(self, bg=t["bg"], padx=4, pady=4)
        filter_bar.pack(side="top", fill="x", padx=12, pady=(2, 6))

        tk.Label(filter_bar, text="🔍 Search / Filter:", bg=t["bg"], fg=t["text"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_table())
        search_entry = tk.Entry(filter_bar, textvariable=self.search_var, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], width=28, font=FONT_SM)
        search_entry.pack(side="left", padx=(0, 12))

        tk.Label(filter_bar, text="Portfolio Brand:", bg=t["bg"], fg=t["text"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.brand_filter_var = tk.StringVar(value="All Brands")
        brands_list = ["All Brands"] + sorted(list(self.data_store.get_brands().keys()))
        self.brand_combo = ttk.Combobox(filter_bar, textvariable=self.brand_filter_var, values=brands_list, state="readonly", width=18, font=FONT_SM)
        self.brand_combo.pack(side="left", padx=(0, 4))
        self.brand_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_table())

        # ── 3. Whitelist Treeview ─────────────────────────────────────────────
        table_frame = tk.Frame(self, bg=t["bg"])
        table_frame.pack(side="top", fill="both", expand=True, padx=12, pady=4)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("seller", "brand", "dealer_name", "marketplace", "notes", "added_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended", style="Whitelist.Treeview")

        style = ttk.Style()
        style.configure("Whitelist.Treeview", background=t["entry_bg"], foreground=t["text"], fieldbackground=t["entry_bg"], rowheight=28, font=FONT_SM)
        style.configure("Whitelist.Treeview.Heading", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9, "bold"))
        style.map("Whitelist.Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["select_fg"])])

        col_cfg = {
            "seller": ("Seller Handle / Store Slug", 160),
            "brand": ("Brand Portfolio", 130),
            "dealer_name": ("Dealership / Entity Name", 200),
            "marketplace": ("Marketplace Scope", 140),
            "notes": ("Analyst Notes", 220),
            "added_at": ("Date Added", 120)
        }
        for c, (txt, w) in col_cfg.items():
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, minwidth=80)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self._edit_dealer_dialog())

        # ── 4. Bottom Action Toolbar ──────────────────────────────────────────
        btn_bar = tk.Frame(self, bg=t["panel"], padx=16, pady=12, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x", padx=12, pady=(6, 12))

        tk.Button(btn_bar, text="➕ Add Dealer", command=self._add_dealer_dialog, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=6).pack(side="left", padx=(0, 6))
        tk.Button(btn_bar, text="✏ Edit Dealer", command=self._edit_dealer_dialog, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="📋 Bulk Import List", command=self._bulk_import_dialog, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="🗑 Remove Selected", command=self._remove_selected, bg=t["entry_bg"], fg=t["danger"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="💾 Export CSV", command=self._export_csv, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="✕ Close", command=self.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=14, pady=6, font=FONT_SM).pack(side="right")

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        wl = self.data_store.get_whitelist()
        q = self.search_var.get().lower().strip()
        brand_filter = self.brand_filter_var.get()

        total = len(wl)
        shown = 0

        for handle, data in sorted(wl.items()):
            b = data.get("brand", "")
            d_name = data.get("dealer_name", "")
            mp = data.get("marketplace", "All Marketplaces")
            notes = data.get("notes", "")
            date = data.get("date_added") or data.get("added_at") or data.get("date_updated") or ""

            # Filter logic
            if brand_filter != "All Brands" and b.lower() != brand_filter.lower():
                continue
            if q and not any(q in str(x).lower() for x in (handle, b, d_name, mp, notes)):
                continue

            self.tree.insert("", "end", values=(handle, b, d_name, mp, notes, date))
            shown += 1

        self.stat_lbl.config(text=f"{total} Authorized Dealers Registered ({shown} shown)")

    def _show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
        if not self.tree.selection(): return
        
        t = self.t
        menu = tk.Menu(self, tearoff=0, bg=t["panel"], fg=t["text"], activebackground=t["accent"], activeforeground="white")
        menu.add_command(label="✏ Edit Dealer", command=self._edit_dealer_dialog)
        menu.add_command(label="🗑 Remove from Whitelist", command=self._remove_selected)
        menu.add_command(label="📋 Copy Seller Handle", command=self._copy_selected_handle)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_selected_handle(self):
        sel = self.tree.selection()
        if sel:
            handle = self.tree.item(sel[0])["values"][0]
            self.clipboard_clear()
            self.clipboard_append(handle)

    def _edit_dealer_dialog(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Dealer", "Please select an authorized dealer from the table to edit.")
            return
        vals = self.tree.item(sel[0])["values"]
        handle = vals[0]
        self._add_dealer_dialog(edit_handle=handle)

    def _add_dealer_dialog(self, edit_handle=None):
        dlg = tk.Toplevel(self)
        dlg.withdraw()
        is_edit = bool(edit_handle)
        dlg.title("✏ Edit Authorized Dealership" if is_edit else "➕ Add Authorized Dealership")
        dlg.geometry("480x380")
        dlg.configure(bg=self.t["bg"])
        dlg.transient(self)
        dlg.grab_set()
        self.parent._apply_dark_titlebar(dlg)

        t = self.t
        f = tk.Frame(dlg, bg=t["panel"], padx=16, pady=16)
        f.pack(fill="both", expand=True, padx=12, pady=12)

        wl = self.data_store.get_whitelist()
        existing_data = wl.get(edit_handle, {}) if is_edit else {}

        tk.Label(f, text="Seller Handle / Store URL:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        h_entry = tk.Entry(f, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, width=32)
        h_entry.grid(row=0, column=1, sticky="w", pady=4)
        if is_edit:
            h_entry.insert(0, edit_handle)
            h_entry.config(state="disabled")
        else:
            h_entry.focus_set()

        tk.Label(f, text="Brand Portfolio:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        brands = ["General / All Brands"] + sorted(list(self.data_store.get_brands().keys()))
        b_combo = ttk.Combobox(f, values=brands, font=FONT_SM, width=30)
        b_combo.grid(row=1, column=1, sticky="w", pady=4)
        b_combo.set(existing_data.get("brand", "Toyota") if is_edit else "Toyota")

        tk.Label(f, text="Dealership / Entity Name:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=4)
        d_entry = tk.Entry(f, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, width=32)
        d_entry.grid(row=2, column=1, sticky="w", pady=4)
        d_entry.insert(0, existing_data.get("dealer_name", "Authorized Dealership") if is_edit else "Authorized Dealership")

        tk.Label(f, text="Marketplace Scope:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=4)
        mp_options = ["All Marketplaces (Global)", "eBay Only", "ManoMano Only", "TikTok Shop Only", "Mercado Libre Only", "Vinted Only"]
        mp_combo = ttk.Combobox(f, values=mp_options, font=FONT_SM, width=30, state="readonly")
        mp_combo.grid(row=3, column=1, sticky="w", pady=4)
        mp_combo.set(existing_data.get("marketplace", "All Marketplaces (Global)") if is_edit else "All Marketplaces (Global)")

        tk.Label(f, text="Analyst Notes:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=4)
        n_entry = tk.Entry(f, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, width=32)
        n_entry.grid(row=4, column=1, sticky="w", pady=4)
        n_entry.insert(0, existing_data.get("notes", "") if is_edit else "")

        def _close_dlg():
            try: dlg.grab_release()
            except Exception: pass
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", _close_dlg)

        def _save():
            handle = edit_handle if is_edit else h_entry.get().strip()
            if not handle:
                messagebox.showwarning("Missing Handle", "Please enter a seller handle or store URL.", parent=dlg)
                return
            b = b_combo.get().strip()
            d = d_entry.get().strip() or "Authorized Dealership"
            mp = mp_combo.get().strip() or "All Marketplaces (Global)"
            n = n_entry.get().strip()
            self.data_store.add_to_whitelist(handle, brand=b, dealer_name=d, notes=n, marketplace=mp)
            self.parent._log(f"🛡 Whitelist updated for '{handle}' ({b} • {mp}).")
            self._refresh_table()
            _close_dlg()

        btn_box = tk.Frame(f, bg=t["panel"])
        btn_box.grid(row=5, column=0, columnspan=2, pady=(16, 0), sticky="e")
        tk.Button(btn_box, text="Cancel", command=_close_dlg, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=10, pady=4).pack(side="right", padx=4)
        tk.Button(btn_box, text="💾 Save Changes" if is_edit else "💾 Save Dealer", command=_save, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4).pack(side="right")

        self.parent._center_window(dlg, 480, 380)

    def _bulk_import_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.withdraw()
        dlg.title("📋 Bulk Import Authorized Dealerships")
        dlg.geometry("560x480")
        dlg.configure(bg=self.t["bg"])
        dlg.transient(self)
        dlg.grab_set()
        self.parent._apply_dark_titlebar(dlg)

        def _close_bulk():
            try: dlg.grab_release()
            except Exception: pass
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", _close_bulk)

        t = self.t
        f = tk.Frame(dlg, bg=t["panel"], padx=16, pady=14)
        f.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(f, text="Paste List of Store URLs or Seller Usernames (1 per line):", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        txt = tk.Text(f, height=12, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, relief="flat")
        txt.pack(fill="both", expand=True, pady=4)

        opt_frame = tk.Frame(f, bg=t["panel"])
        opt_frame.pack(fill="x", pady=6)
        
        tk.Label(opt_frame, text="Assign Brand:", bg=t["panel"], fg=t["text"], font=FONT_SM).pack(side="left", padx=(0, 4))
        brands = ["General / All Brands"] + sorted(list(self.data_store.get_brands().keys()))
        b_combo = ttk.Combobox(opt_frame, values=brands, font=FONT_SM, width=20)
        b_combo.pack(side="left", padx=(0, 8))
        b_combo.set("Toyota")

        def _do_import():
            raw = txt.get("1.0", "end").strip()
            if not raw:
                messagebox.showwarning("Empty", "Please paste one or more seller handles.", parent=dlg)
                return
            b = b_combo.get().strip()
            added = self.data_store.bulk_add_whitelist(raw, brand=b, notes="Bulk Client Import")
            self.parent._log(f"🛡 Bulk imported {added} authorized dealers for {b}.")
            self._refresh_table()
            messagebox.showinfo("Import Complete", f"Successfully imported {added} authorized dealers into your Whitelist!", parent=dlg)
            dlg.destroy()

        btn_box = tk.Frame(f, bg=t["panel"])
        btn_box.pack(fill="x", pady=(8, 0))
        tk.Button(btn_box, text="Cancel", command=dlg.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=10, pady=4).pack(side="right", padx=4)
        tk.Button(btn_box, text="📥 Import Dealers", command=_do_import, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=4).pack(side="right")

        self.parent._center_window(dlg, 560, 480)

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select one or more dealers to remove.")
            return
        if not messagebox.askyesno("Confirm Removal", f"Remove {len(sel)} dealer(s) from your Authorized Whitelist?"):
            return
        for iid in sel:
            handle = self.tree.item(iid)["values"][0]
            self.data_store.remove_from_whitelist(str(handle))
        self._refresh_table()
        self.parent._log(f"🛡 Removed {len(sel)} dealer(s) from Authorized Whitelist.")

    def _export_csv(self):
        wl = self.data_store.get_whitelist()
        if not wl:
            messagebox.showinfo("Export", "No whitelisted dealers to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile="authorized_dealers_whitelist.csv")
        if not path: return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Seller Handle", "Brand", "Dealership Name", "Notes", "Date Added"])
                for h, d in wl.items():
                    writer.writerow([h, d.get("brand", ""), d.get("dealer_name", ""), d.get("notes", ""), d.get("added_at", "")])
            messagebox.showinfo("Exported", f"Successfully exported {len(wl)} whitelisted dealers to:\n\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

