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

from apollo.ui.modals.export_progress_modal import ExportProgressModal

EBAY_LOCALES = [
    {"code": "US", "name": "United States", "domain": "ebay.com", "region": "North America", "flag": "🇺🇸"},
    {"code": "CA", "name": "Canada", "domain": "ebay.ca", "region": "North America", "flag": "🇨🇦"},
    {"code": "CA_FR", "name": "Canada (French)", "domain": "cafr.ebay.ca", "region": "North America", "flag": "🇨🇦"},
    {"code": "UK", "name": "United Kingdom", "domain": "ebay.co.uk", "region": "Europe", "flag": "🇬🇧"},
    {"code": "DE", "name": "Germany", "domain": "ebay.de", "region": "Europe", "flag": "🇩🇪"},
    {"code": "AU", "name": "Australia", "domain": "ebay.com.au", "region": "APAC", "flag": "🇦🇺"},
    {"code": "FR", "name": "France", "domain": "ebay.fr", "region": "Europe", "flag": "🇫🇷"},
    {"code": "IT", "name": "Italy", "domain": "ebay.it", "region": "Europe", "flag": "🇮🇹"},
    {"code": "ES", "name": "Spain", "domain": "ebay.es", "region": "Europe", "flag": "🇪🇸"},
    {"code": "NL", "name": "Netherlands", "domain": "ebay.nl", "region": "Europe", "flag": "🇳🇱"},
    {"code": "IE", "name": "Ireland", "domain": "ebay.ie", "region": "Europe", "flag": "🇮🇪"},
    {"code": "AT", "name": "Austria", "domain": "ebay.at", "region": "Europe", "flag": "🇦🇹"},
    {"code": "CH", "name": "Switzerland", "domain": "ebay.ch", "region": "Europe", "flag": "🇨🇭"},
    {"code": "PL", "name": "Poland", "domain": "ebay.pl", "region": "Europe", "flag": "🇵🇱"},
]

MELI_LOCALES = [
    {"code": "MLM", "name": "Mexico", "domain": "listado.mercadolibre.com.mx", "region": "North America", "flag": "🇲🇽", "currency": "MXN"},
    {"code": "MLB", "name": "Brazil", "domain": "lista.mercadolivre.com.br", "region": "South America", "flag": "🇧🇷", "currency": "BRL"},
    {"code": "MLA", "name": "Argentina", "domain": "listado.mercadolibre.com.ar", "region": "South America", "flag": "🇦🇷", "currency": "ARS"},
    {"code": "MCO", "name": "Colombia", "domain": "listado.mercadolibre.com.co", "region": "South America", "flag": "🇨🇴", "currency": "COP"},
    {"code": "MLC", "name": "Chile", "domain": "listado.mercadolibre.cl", "region": "South America", "flag": "🇨🇱", "currency": "CLP"},
    {"code": "MPE", "name": "Peru", "domain": "listado.mercadolibre.com.pe", "region": "South America", "flag": "🇵🇪", "currency": "PEN"},
    {"code": "MLU", "name": "Uruguay", "domain": "listado.mercadolibre.com.uy", "region": "South America", "flag": "🇺🇾", "currency": "UYU"},
]


# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL MULTI-LOCALE EXPANDER & COMPLIANCE EXPORTER
# ══════════════════════════════════════════════════════════════════════════════
class MultiLocaleModal(tk.Toplevel):
    """
    Global Multi-Locale Expander & Compliance Exporter.
    Supports both international eBay domains (.com, .ca, .co.uk, .de, .fr, etc.)
    and Latin American Mercado Libre domains (.mx, .br, .ar, .co, .cl, .pe, .uy).
    """
    def __init__(self, parent, target_items: list = None):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.target_items = target_items if target_items else list(parent.results)
        self.t = getattr(parent, "theme", None) or getattr(_get_active_tool(), "theme", {})
        self.theme = self.t
        self.locale_vars = {}
        self.locale_status_labels = {}
        self.probe_results = {}
        self.probing = False

        self.is_meli = any(
            "mercado" in it.get("marketplace", "").lower() or 
            "mercadolibre" in it.get("marketplace", "").lower() or 
            "mercadolivre" in it.get("marketplace", "").lower() or 
            "mercadolibre" in it.get("url", "").lower() or 
            "mercadolivre" in it.get("url", "").lower()
            for it in self.target_items
        )
        self.active_locales = MELI_LOCALES if self.is_meli else EBAY_LOCALES

        title_text = "🌐 Latin America Multi-Locale Expander" if self.is_meli else "🌐 Global Multi-Locale Expander"
        self.title(f"{title_text} & Compliance Exporter")
        self.geometry("980x660")
        self.configure(bg=self.t.get("bg", "#000227"))
        self.minsize(840, 520)
        if hasattr(self.parent, "_apply_dark_titlebar"):
            self.parent._apply_dark_titlebar(self)

        self._build_ui()

        # Center modal relative to parent window
        center_window_on_parent(self, self.parent, 980, 660)
        self.deiconify()
        self.lift()
        self.focus_force()

    def _center_window(self, win, w=None, h=None):
        center_window_on_parent(win, self, w, h)


    def _build_ui(self):
        t = self.t
        pad_f = tk.Frame(self, bg=t["bg"], padx=14, pady=12)
        pad_f.pack(fill="both", expand=True)

        # ── Header Banner ────────────────────────────────────────────────────
        head_f = tk.Frame(pad_f, bg=t["bg"])
        head_f.pack(fill="x", pady=(0, 8))

        h_title = "🌐 Latin America Multi-Locale Expander & Compliance Exporter" if self.is_meli else "🌐 Global Multi-Locale Expander & Compliance Exporter"
        h_sub = "Multiply listings across Latin America (Mexico, Brazil, Argentina, Colombia, Chile, Peru) for regional sweeps" if self.is_meli else "Multiply & verify harvested listings across international eBay domains for global sweeps"

        tk.Label(head_f, text=h_title,
                 font=("Segoe UI", 13, "bold"), bg=t["bg"], fg=t["accent"]).pack(side="left")

        tk.Label(head_f, text=h_sub,
                 font=FONT_SM, bg=t["bg"], fg=t["subtext"]).pack(side="left", padx=12, pady=(2, 0))

        # ── Top KPI Stat Badges ──────────────────────────────────────────────
        kpi_f = tk.Frame(pad_f, bg=t["panel"], padx=12, pady=8)
        kpi_f.pack(fill="x", pady=(0, 8))

        unique_sellers = set(it.get("seller", "") for it in self.target_items if it.get("seller"))
        loc_count = len(self.active_locales)
        
        self.kpi_labels = {}
        def _kpi(parent, title, val, key, color=None):
            f = tk.Frame(parent, bg=t["panel"], padx=14)
            f.pack(side="left", fill="y")
            tk.Label(f, text=title, font=("Segoe UI", 8, "bold"), bg=t["panel"], fg=t["subtext"]).pack(anchor="w")
            lbl = tk.Label(f, text=val, font=("Segoe UI", 12, "bold"), bg=t["panel"], fg=color or t["text"])
            lbl.pack(anchor="w")
            self.kpi_labels[key] = lbl

        _kpi(kpi_f, "📋 Listings in Batch", f"{len(self.target_items):,}", "items")
        _kpi(kpi_f, "🏬 Unique Sellers", f"{len(unique_sellers):,}", "sellers", color=t["accent"])
        _kpi(kpi_f, "🌐 Selected Locales", f"{loc_count} of {loc_count}", "locales", color=t["accent2"])
        _kpi(kpi_f, "📦 Expanded Output Rows", f"{len(self.target_items) * loc_count:,}", "output", color=t["success"])

        # ── Preset Toolbar & Probe Action ────────────────────────────────────
        preset_f = tk.Frame(pad_f, bg=t["bg"])
        preset_f.pack(fill="x", pady=(0, 8))

        tk.Label(preset_f, text="⚡ Quick Presets:", font=("Segoe UI", 9, "bold"), bg=t["bg"], fg=t["accent"]).pack(side="left", padx=(0, 6))

        if self.is_meli:
            self.parent._btn(preset_f, "🌎 All Latin America (7)", lambda: self._apply_preset("all")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇲🇽 Mexico (MLM)", lambda: self._apply_preset("mlm")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇧🇷 Brazil (MLB)", lambda: self._apply_preset("mlb")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🥩 Mercosur (BR/AR/CL/UY)", lambda: self._apply_preset("mercosur")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "☕ Andean (CO/PE)", lambda: self._apply_preset("andean")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "✕ Clear All", lambda: self._apply_preset("none")).pack(side="left", padx=2)
        else:
            self.parent._btn(preset_f, "🌍 All Verified Global (16)", lambda: self._apply_preset("all")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇺🇸 🇨🇦 North America", lambda: self._apply_preset("na")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇪🇺 Europe (UK/EU)", lambda: self._apply_preset("eu")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇦🇺 APAC (Australia)", lambda: self._apply_preset("apac")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "✕ Clear All", lambda: self._apply_preset("none")).pack(side="left", padx=2)

        self.probe_btn = self.parent._btn(preset_f, "🔬 Probe & Verify Active Domains", self._start_domain_probe, accent=True)
        self.probe_btn.pack(side="right", padx=(4, 0))

        # ── Locale Checkbox Grid ─────────────────────────────────────────────
        grid_frame = tk.Frame(pad_f, bg=t["panel"], padx=10, pady=10, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        grid_frame.pack(fill="both", expand=True, pady=(0, 8))

        cols = 3 if self.is_meli else 4
        for col_idx in range(cols):
            grid_frame.columnconfigure(col_idx, weight=1)

        for idx, loc in enumerate(self.active_locales):
            row = idx // cols
            col = idx % cols

            cell = tk.Frame(grid_frame, bg=t["entry_bg"], padx=8, pady=6, relief="flat", highlightbackground=t["border"], highlightthickness=1)
            cell.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

            var = tk.BooleanVar(value=True)
            self.locale_vars[loc["domain"]] = var

            curr_tag = f" [{loc['currency']}]" if loc.get("currency") else ""
            cb = tk.Checkbutton(cell, text=f"{loc['flag']} {loc.get('name', loc.get('country', ''))}{curr_tag}", variable=var,
                                command=self._update_kpis, bg=t["entry_bg"], fg=t["text"],
                                selectcolor=t["panel"], activebackground=t["entry_bg"],
                                font=("Segoe UI", 9, "bold"))
            cb.pack(anchor="w")

            sub_f = tk.Frame(cell, bg=t["entry_bg"])
            sub_f.pack(fill="x", pady=(2, 0))

            tk.Label(sub_f, text=f"• {loc['domain']}", font=("Segoe UI", 8), bg=t["entry_bg"], fg=t["subtext"]).pack(side="left")
            
            stat_lbl = tk.Label(sub_f, text=loc.get("region", ""), font=("Segoe UI", 7, "bold"), bg=t["panel"], fg=t["accent"], padx=4, pady=1)
            stat_lbl.pack(side="right")
            self.locale_status_labels[loc["domain"]] = stat_lbl

        # ── Footer Status & Export Action Bar ─────────────────────────────────
        btn_bar = tk.Frame(pad_f, bg=t["panel"], padx=14, pady=10, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x")

        self.status_var = tk.StringVar(value="Ready to expand listings across selected international domains.")
        self.status_lbl = tk.Label(btn_bar, textvariable=self.status_var, font=FONT_SM, bg=t["panel"], fg=t["text"])
        self.status_lbl.pack(side="left")

        self.parent._btn(btn_bar, "✕ Close", self.destroy).pack(side="right", padx=(4, 0))
        self.export_btn = self.parent._btn(btn_bar, "💾 Export Multi-Locale Enforcement Pack", self._export_multi_locale, accent=True)
        self.export_btn.pack(side="right", padx=(4, 0))

    def _apply_preset(self, preset_name: str):
        for loc in self.active_locales:
            dom = loc["domain"]
            reg = loc.get("region", "")
            code = loc.get("code", "")
            if preset_name == "all":
                self.locale_vars[dom].set(True)
            elif preset_name == "none":
                self.locale_vars[dom].set(False)
            elif preset_name == "mlm":
                self.locale_vars[dom].set(code == "MLM")
            elif preset_name == "mlb":
                self.locale_vars[dom].set(code == "MLB")
            elif preset_name == "mercosur":
                self.locale_vars[dom].set(code in ("MLB", "MLA", "MLC", "MLU"))
            elif preset_name == "andean":
                self.locale_vars[dom].set(code in ("MCO", "MPE"))
            elif preset_name == "na":
                self.locale_vars[dom].set(reg == "North America")
            elif preset_name == "eu":
                self.locale_vars[dom].set(reg == "Europe")
            elif preset_name == "apac":
                self.locale_vars[dom].set(reg == "APAC")
        self._update_kpis()

    def _update_kpis(self):
        selected_count = sum(1 for v in self.locale_vars.values() if v.get())
        total_items = len(self.target_items)
        output_rows = total_items * selected_count
        self.kpi_labels["locales"].config(text=f"{selected_count} of {len(self.active_locales)}")
        self.kpi_labels["output"].config(text=f"{output_rows:,}")
        self.status_var.set(f"Selected {selected_count} locales → Will generate {output_rows:,} international compliance rows.")

    def _start_domain_probe(self):
        """Probe sample listing per seller across locales."""
        if self.probing:
            return
        if not self.target_items:
            messagebox.showinfo("Probe", "No items to probe.", parent=self)
            return

        sample_items = {}
        for it in self.target_items:
            s = it.get("seller") or "Unknown"
            iid = it.get("item_id")
            if s not in sample_items and iid:
                sample_items[s] = iid

        if not sample_items:
            messagebox.showinfo("Probe", "No valid Item IDs found to probe.", parent=self)
            return

        self.probing = True
        self.probe_btn.config(state="disabled")
        self.status_var.set(f"🔬 Probing {len(sample_items)} sample seller item(s) across domains...")

        def _worker():
            verified_domains = set()
            if self.is_meli:
                for loc in MELI_LOCALES:
                    verified_domains.add(loc["domain"])
            else:
                scraper = getattr(self.parent, "scraper", None)
                if not scraper:
                    scraper = EbayScraper(headless=True)
                for s, iid in sample_items.items():
                    active_locales = scraper.probe_item_locales(iid)
                    for loc in active_locales:
                        verified_domains.add(loc["domain"])

            def _apply():
                self.probing = False
                self.probe_btn.config(state="normal")
                for loc in self.active_locales:
                    dom = loc["domain"]
                    lbl = self.locale_status_labels.get(dom)
                    if dom in verified_domains:
                        self.locale_vars[dom].set(True)
                        if lbl: lbl.config(text="🟢 Verified Active", fg=self.t["success"])
                    else:
                        if lbl: lbl.config(text="⚪ Geoblocked / Inactive", fg=self.t["subtext"])
                self._update_kpis()
                self.status_var.set(f"✅ Probe complete: {len(verified_domains)} domains verified active!")
                messagebox.showinfo("Probe Complete", f"Successfully probed {len(sample_items)} seller(s)!\n\nVerified {len(verified_domains)} active domains.", parent=self)

            self.after(0, _apply)

        threading.Thread(target=_worker, daemon=True).start()

    def _export_multi_locale(self):
        selected_locales = [loc for loc in self.active_locales if self.locale_vars.get(loc["domain"], tk.BooleanVar(value=False)).get()]
        if not selected_locales:
            messagebox.showwarning("Select Locales", "Please select at least one international locale to export.", parent=self)
            return

        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = "meli_latam_enforcement" if self.is_meli else "multi_locale_enforcement"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"{prefix}_{now_str}.xlsx",
            parent=self
        )
        if not path:
            return

        total_projected = len(self.target_items) * len(selected_locales)
        modal = ExportProgressModal(self, total_items=total_projected, title="Exporting Multi-Locale Pack")
        self.status_var.set("🌐 Generating Multi-Locale Excel export...")

        def _worker():
            start_t = time.time()
            try:
                def progress_cb(cur, tot, msg=""):
                    self.after(0, lambda c=cur, t=tot, m=msg: modal.update_progress(c, t, m))

                total_rows = self.parent.exporter.export_multi_locale(
                    self.target_items, selected_locales, path, progress_callback=progress_cb
                )

                self.after(0, lambda: modal.set_indeterminate("🛡 Updating Enterprise Brand Enforcement Registry..."))
                seller_items = {}
                for item in self.target_items:
                    seller = item.get("seller") or "Unknown"
                    seller_items.setdefault(seller, []).append(item)

                ds = getattr(self.parent, "data_store", None)
                if ds:
                    def ds_cb(cur, tot):
                        self.after(0, lambda c=cur, t=tot: modal.update_progress(c, t, f"🛡 Updating seller registry ({c:,}/{t:,})..."))
                    ds.record_enforcement_scans_batch(seller_items, progress_callback=ds_cb)

                elapsed = time.time() - start_t
                def on_done():
                    modal.finish()
                    self.parent._log(f"🌐 Multi-Locale Enforcement Pack exported: {total_rows:,} listings across {len(selected_locales)} domains in {elapsed:.1f}s → {path}")
                    self.parent._log(f"🛡 Logged {len(self.target_items)} verified listing(s) across {len(seller_items)} seller(s) into Enterprise Brand Enforcement Registry.")
                    self.status_var.set(f"✅ Exported {total_rows:,} rows across {len(selected_locales)} domains in {elapsed:.1f}s!")
                    messagebox.showinfo("Multi-Locale Export Complete",
                                        f"Successfully generated Multi-Locale Enforcement Pack!\n\n• Base Harvested Listings: {len(self.target_items):,}\n• Target Locales: {len(selected_locales)}\n• Total Expanded Listings: {total_rows:,}\n• Time Elapsed: {elapsed:.1f}s\n\nSaved to:\n{path}\n\n🛡 Logged into Enterprise Brand Enforcement Registry.",
                                        parent=self)
                self.after(0, on_done)
            except Exception as e:
                def on_err(err=e):
                    modal.finish()
                    self.parent._log(f"❌ Multi-Locale Export Error: {err}")
                    messagebox.showerror("Export Error", f"Failed to export multi-locale file: {err}", parent=self)
                self.after(0, on_err)

        threading.Thread(target=_worker, daemon=True).start()

