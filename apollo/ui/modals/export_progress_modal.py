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
#  EXCEL EXPORT & REGISTRY PROGRESS MODAL
# ══════════════════════════════════════════════════════════════════════════════
class ExportProgressModal(tk.Toplevel):
    """
    Dedicated non-blocking progress modal for high-volume Excel exports and registry updates.
    Displays live percentage, current operation phase, and prevents accidental window termination during disk I/O.
    """
    def __init__(self, parent, total_items: int, title="Exporting Enforcement Dossier"):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        active_tool = _get_active_tool()
        root_theme = getattr(active_tool, "theme", None)
        self.t = getattr(parent, "theme", root_theme or {
            "bg": "#0D1117", "panel": "#161B22", "border": "#30363D",
            "text": "#E6EDF3", "subtext": "#8B949E", "accent": "#238636", "entry_bg": "#0D1117"
        })
        self.total_items = max(1, total_items)
        self.title(f"💾 {title}")
        self.geometry("520x220")
        self.resizable(False, False)
        self.configure(bg=self.t.get("bg", "#0D1117"))
        
        if hasattr(parent, "_apply_dark_titlebar"):
            parent._apply_dark_titlebar(self)
        elif active_tool and hasattr(active_tool, "_apply_dark_titlebar"):
            active_tool._apply_dark_titlebar(self)
            
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt)
        self.allow_close = False
        
        self._build_ui(title)
        center_window_on_parent(self, parent, 520, 220)
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self, title_text):
        t = self.t
        pad = tk.Frame(self, bg=t.get("bg", "#0D1117"), padx=24, pady=20)
        pad.pack(fill="both", expand=True)

        self.lbl_header = tk.Label(
            pad, text=f"💾 {title_text}",
            font=("Segoe UI", 12, "bold"),
            fg=t.get("text", "#E6EDF3"), bg=t.get("bg", "#0D1117")
        )
        self.lbl_header.pack(anchor="w", pady=(0, 4))

        self.lbl_status = tk.Label(
            pad, text="Preparing data...",
            font=("Segoe UI", 9),
            fg=t.get("subtext", "#8B949E"), bg=t.get("bg", "#0D1117")
        )
        self.lbl_status.pack(anchor="w", pady=(0, 14))

        # Themed Progressbar styling matching active Apollo theme (no native white bar)
        prog_style_name = "ExportModal.Horizontal.TProgressbar"
        try:
            p_style = ttk.Style(self)
            p_style.configure(
                prog_style_name,
                troughcolor=t.get("entry_bg", t.get("panel", "#0D1117")),
                background=t.get("accent", "#38bdf8"),
                bordercolor=t.get("border", t.get("entry_bg", "#30363D")),
                lightcolor=t.get("accent2", t.get("accent", "#38bdf8")),
                darkcolor=t.get("accent", "#38bdf8")
            )
        except Exception:
            pass

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            pad, variable=self.progress_var, maximum=100.0, mode="determinate",
            style=prog_style_name
        )
        self.progress_bar.pack(fill="x", pady=(0, 8))


        sub_row = tk.Frame(pad, bg=t.get("bg", "#0D1117"))
        sub_row.pack(fill="x", pady=(0, 10))
        
        self.lbl_percent = tk.Label(
            sub_row, text="0.0%",
            font=("Segoe UI", 9, "bold"),
            fg=t.get("accent", "#58A6FF"), bg=t.get("bg", "#0D1117")
        )
        self.lbl_percent.pack(side="left")

        self.lbl_count = tk.Label(
            sub_row, text=f"0 / {self.total_items:,} items",
            font=("Segoe UI", 9),
            fg=t.get("subtext", "#8B949E"), bg=t.get("bg", "#0D1117")
        )
        self.lbl_count.pack(side="right")

        self.lbl_note = tk.Label(
            pad, text="⚡ Background worker active. Do not close to ensure file integrity.",
            font=("Segoe UI", 8, "italic"),
            fg=t.get("subtext", "#8B949E"), bg=t.get("bg", "#0D1117")
        )
        self.lbl_note.pack(anchor="w")

    def update_progress(self, current: int, total: int, status_text: str = ""):
        try:
            if total > 0:
                pct = min(100.0, (current / total) * 100.0)
                self.progress_var.set(pct)
                self.lbl_percent.config(text=f"{pct:.1f}%")
                self.lbl_count.config(text=f"{current:,} / {total:,} items")
            if status_text:
                self.lbl_status.config(text=status_text)
            self.update_idletasks()
        except Exception:
            pass

    def set_indeterminate(self, status_text: str = ""):
        try:
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start(15)
            if status_text:
                self.lbl_status.config(text=status_text)
            self.lbl_percent.config(text="Processing...")
            self.lbl_count.config(text="")
            self.update_idletasks()
        except Exception:
            pass

    def _on_close_attempt(self):
        if self.allow_close:
            self.destroy()

    def finish(self):
        self.allow_close = True
        try:
            self.destroy()
        except Exception:
            pass

