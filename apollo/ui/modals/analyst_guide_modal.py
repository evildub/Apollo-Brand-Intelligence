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



class AnalystGuideModal(tk.Toplevel):
    """Interactive Analyst Operations Guide, Feature Comparison & Workflow Reference."""
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.theme = parent.theme
        t = self.theme

        self.title("💡 Apollo Brand Intelligence — Analyst Operations Guide & Reference")
        self.geometry("860x700")
        self.minsize(740, 560)
        self.configure(bg=t["bg"])
        self.transient(parent)
        
        if hasattr(parent, "_apply_dark_titlebar"):
            parent._apply_dark_titlebar(self)
        if hasattr(parent, "_load_app_icon"):
            parent._load_app_icon(self)

        # Header Frame
        header = tk.Frame(self, bg=t["panel"], padx=18, pady=14, relief="solid", bd=1)
        header.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(header, text="💡 Analyst Operations & Feature Reference", font=("Segoe UI", 13, "bold"),
                 bg=t["panel"], fg=t["accent"]).pack(anchor="w")
        tk.Label(header, text="Operational guide for high-velocity investigations, cross-border sweeps, and Enterprise data contracts.",
                 font=FONT_NORM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w", pady=(2, 0))

        # Scrollable Body Container
        container = tk.Frame(self, bg=t["bg"])
        container.pack(fill="both", expand=True, padx=12, pady=6)

        canvas = tk.Canvas(container, bg=t["bg"], highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=t["bg"])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind("<MouseWheel>", _on_mousewheel)

        def _add_section(title, icon, items):
            card = tk.Frame(scrollable_frame, bg=t["panel"], padx=16, pady=12, relief="solid", bd=1)
            card.pack(fill="x", pady=6)

            h_box = tk.Frame(card, bg=t["panel"])
            h_box.pack(fill="x", pady=(0, 8))
            tk.Label(h_box, text=f"{icon} {title}", font=("Segoe UI", 11, "bold"),
                     bg=t["panel"], fg=t["accent"]).pack(side="left")

            for item_title, desc, badge in items:
                row = tk.Frame(card, bg=t["panel"], pady=4)
                row.pack(fill="x")

                t_row = tk.Frame(row, bg=t["panel"])
                t_row.pack(fill="x")
                tk.Label(t_row, text=item_title, font=("Segoe UI", 9, "bold"),
                         bg=t["panel"], fg=t["text"]).pack(side="left")
                if badge:
                    tk.Label(t_row, text=f" {badge} ", font=("Segoe UI", 8, "bold"),
                             bg=t["entry_bg"], fg=t["accent"], relief="solid", bd=1).pack(side="left", padx=6)

                tk.Label(row, text=desc, font=FONT_NORM, bg=t["panel"], fg=t["subtext"],
                         wraplength=760, justify="left").pack(anchor="w", pady=(2, 0))

        # 1. Rescrape vs. Enrich
        _add_section("Listing Refresh vs. Merchant Discovery", "🔄", [
            ("🔄 Rescrape / Refresh Selected",
             "Live listing fetch directly from the marketplace page (eBay, Vinted, AliExpress, Mercado Libre). Re-pulls high-res photo thumbnails, live prices, exact active titles, and availability. Use this when rows have missing thumbnails, after importing URLs, or to verify if a listing was taken down.",
             "HotKey: F5"),
            ("🏪 Enrich Sellers",
             "Batch background resolver across e-commerce feeds (AliExpress, Temu, Wish, Mercado Libre, eBay) to populate missing merchant storefront IDs. Preserves all other manually edited listing attributes.",
             "Batch Resolver"),
            ("✏ In-Table Cell Editing",
             "Directly edit Brand, Category, Seller Name, Price, or Title in place without navigating away or losing table selection. Automatically recalculates threat intel and updates the Enterprise export dataset.",
             "HotKey: F2 / Double-Click")
        ])

        # 2. Threat Intel vs Connected Network Hunter
        _add_section("Syndicate Investigation & Threat Intel", "🕵", [
            ("🔗 Connected Seller Network Hunter",
             "Performs cross-store syndicate correlation to uncover multi-store networks sharing identical telephone numbers, customer service emails, business licenses, or physical 3PL warehouse addresses across platforms.",
             "Syndicate Hunter"),
            ("🌍 Threat Intel & Origin Resolution",
             "Computes seller risk scores, unmasks foreign drop-shippers (e.g. China-based merchants using domestic California/New Jersey 3PL forwarding hubs), and tracks lifetime brand infringement strikes.",
             "Drop-Ship Detection"),
            ("🛡 Enforcement Registry",
             "Centralized ledger aggregating recidivist seller dossiers, captured infringing listings, historical enforcement notices, and total cumulative counterfeit market value ($ MSRP).",
             "Legal Dossier")
        ])

        # 3. Export & Multi-Locale Expander
        _add_section("Standard Upload & Cross-Border Projections", "💾", [
            ("💾 Standard 18-Column Export",
             "Generates an Excel (.xlsx) file matching the exact 18-column Standard Upload Specification (Columns A–R). Column C contains the live image thumbnail URL, Column B provides active listing hyperlinks, and Column J records verified seller names.",
             "HotKey: Ctrl+E"),
            ("🌐 Multi-Locale International Expander",
             "Projects selected listings across international marketplaces (eBay UK/DE/AU, Mercado Libre Latin America, Vinted Europe). Preserves Columns A–R intact while appending extended regional metadata (domain, local currency, translated query) starting at Column S+.",
             "Multi-Marketplace")
        ])

        # 4. Visual Threat Catalog
        _add_section("Visual Packaging Catalog & Reverse Search", "🖼", [
            ("🟢 Benign Packaging Catalog",
             "Stores perceptual hash (pHash) fingerprints of verified genuine OEM packaging. Automatically shields legitimate authorized listings from accidental enforcement.",
             "Shielding"),
            ("🔴 Known Counterfeit Catalog",
             "Stores fingerprints of confirmed counterfeit packaging. Automatically flags matching visual clone listings in real time with high threat badges (🚨 Visual Counterfeit).",
             "High Threat"),
            ("📸 Reverse Visual Sweep",
             "Performs a visual reverse lookup to scan active marketplace feeds for duplicate packaging photos used across different seller storefronts.",
             "Visual Sweep")
        ])

        # 5. Hotkeys & Shortcuts
        _add_section("Analyst Hotkeys & Fast Actions", "⌨", [
            ("F2 / Double-Click", "Edit Brand, Category, Seller, Price, or Title in place in the Results Table.", "Quick Edit"),
            ("F5", "Trigger targeted live rescrape on highlighted listings.", "Live Rescrape"),
            ("Ctrl + E", "Instantly export current session results to Standard Excel (.xlsx).", "Export"),
            ("Ctrl + A", "Select all visible listings in the Results Table.", "Select All"),
            ("Delete", "Remove selected listings from current session.", "Remove"),
            ("Right-Click Context Menu", "Access Reverse Visual Search, WHOIS Lookup, Threat Badges, and Dealership Whitelisting.", "Context Menu")
        ])

        # Bottom Close Button
        btn_bar = tk.Frame(self, bg=t["bg"])
        btn_bar.pack(fill="x", padx=12, pady=(4, 12))
        tk.Button(btn_bar, text="✕ Close Guide", command=self.destroy,
                  font=("Segoe UI", 9, "bold"), bg=t["accent"], fg="white",
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="right")

        # Center modal relative to parent window and reveal
        if hasattr(parent, "_center_window"):
            parent._center_window(self, 860, 700)
        else:
            self.deiconify()
        self.lift()
        self.focus_force()

