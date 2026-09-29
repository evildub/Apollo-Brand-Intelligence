"""
Artemis Rights Engine — Autonomous Platform Enforcement, LOA Registry & Legal Notice Hub.
Companion application to Apollo Brand Intelligence.
"""

import os
import sys
import copy
import shutil
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime
from typing import Dict, List, Any, Optional

# Set explicit Windows AppUserModelID so Artemis has its own distinct taskbar icon and group
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Apollo.Artemis.RightsEngine.1.0")
    except Exception:
        pass

from artemis_bridge import (
    get_artemis_base_dir,
    get_pending_artemis_batches,
    mark_batch_as_ingested
)
from artemis_data_store import ArtemisDataStore
from artemis_engine import ArtemisEngine
from theme_definitions import THEMES as ARTEMIS_THEMES

FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_HEAD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_SM   = ("Segoe UI", 8)
FONT_CODE = ("Consolas", 9)


class ArtemisApp(tk.Tk):
    def __init__(self, initial_theme_key: Optional[str] = None):
        super().__init__()
        # Preemptively withdraw to prevent startup white flashbang
        self.withdraw()

        self.title("🏹 Artemis Rights Engine — Autonomous Platform Enforcement")
        self.geometry("1240x800")
        self.minsize(1020, 680)

        self.data_store = ArtemisDataStore()
        self.engine = ArtemisEngine(self.data_store)

        # Theme resolution
        theme_k = initial_theme_key or self.data_store.get_setting("theme", "artemis_emerald")
        if theme_k not in ARTEMIS_THEMES:
            theme_k = "artemis_emerald"
        self.current_theme_key = theme_k
        self.theme = ARTEMIS_THEMES[self.current_theme_key]

        self.configure(bg=self.theme["bg"])
        self.selected_queue_ids = set()

        self._load_app_icon()
        self._apply_dark_titlebar()
        self._configure_ttk_styles()
        self._build_ui()
        self._check_pending_intake(silent=True)
        self._refresh_queue_table()

        self.bind("<F1>", lambda e: self._open_field_guide())

        # Reveal window smoothly once all widgets and dark styles are applied
        self.after(10, self.deiconify)

    def _load_app_icon(self, window=None):
        target = window or self
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            for ico_name in ("artemis.ico", "artemis.png", "apollo.ico"):
                p = os.path.join(base_dir, ico_name)
                if os.path.exists(p):
                    if p.endswith(".ico"):
                        target.iconbitmap(p)
                    return
        except Exception:
            pass

    def _apply_dark_titlebar(self, win=None):
        """Enable immersive dark mode title bar and caption color on Windows."""
        if sys.platform != "win32":
            return
        target = win or self
        try:
            if not target.winfo_exists():
                return
            target.update_idletasks()
            w_id = target.winfo_id()
            import ctypes
            hwnd = ctypes.windll.user32.GetAncestor(w_id, 2)  # GA_ROOT = 2
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(w_id)
            if not hwnd:
                hwnd = w_id

            v_dark = ctypes.c_int(1)
            for attr in (20, 19):
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v_dark), ctypes.sizeof(v_dark))
                except Exception:
                    pass

            t = getattr(self, "theme", ARTEMIS_THEMES["artemis_emerald"])
            bg_hex = t.get("panel", t.get("bg", "#070D0A"))
            fg_hex = t.get("text", "#ECFDF5")
            border_hex = t.get("border", "#164E33")

            # 35: DWMWA_CAPTION_COLOR (keeps titlebar dark even when window is deselected/unfocused)
            if bg_hex and len(bg_hex) == 7:
                try:
                    r, g, b = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
                    c_color = ctypes.c_int((b << 16) | (g << 8) | r)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c_color), ctypes.sizeof(c_color))
                except Exception:
                    pass

            # 36: DWMWA_TEXT_COLOR
            if fg_hex and len(fg_hex) == 7:
                try:
                    r, g, b = int(fg_hex[1:3], 16), int(fg_hex[3:5], 16), int(fg_hex[5:7], 16)
                    t_color = ctypes.c_int((b << 16) | (g << 8) | r)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(t_color), ctypes.sizeof(t_color))
                except Exception:
                    pass

            # 34: DWMWA_BORDER_COLOR
            if border_hex and len(border_hex) == 7:
                try:
                    r, g, b = int(border_hex[1:3], 16), int(border_hex[3:5], 16), int(border_hex[5:7], 16)
                    br_color = ctypes.c_int((b << 16) | (g << 8) | r)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(br_color), ctypes.sizeof(br_color))
                except Exception:
                    pass

            try:
                ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0037)
            except Exception:
                pass

            if not getattr(target, "_dwm_bound", False):
                target._dwm_bound = True
                def _reassert(e=None):
                    try:
                        if target.winfo_exists():
                            self.after(50, lambda: self._apply_dark_titlebar(target))
                    except Exception:
                        pass
                target.bind("<Map>", _reassert, add="+")
        except Exception:
            pass

    def _configure_ttk_styles(self):
        """Configure ttk widgets (Notebook, Treeview, Combobox) so they strictly match the active dark theme."""
        t = self.theme
        style = ttk.Style(self)
        try:
            style.theme_use("default")
        except Exception:
            pass

        # Notebook tabs
        style.configure("Artemis.TNotebook", background=t["bg"], borderwidth=0)
        style.configure("Artemis.TNotebook.Tab", background=t["panel"], foreground=t["text"], padding=[16, 7], font=FONT_BOLD)
        style.map("Artemis.TNotebook.Tab",
                  background=[("selected", t["accent"]), ("active", t["border"])],
                  foreground=[("selected", t.get("btn_accent_fg", "#070D0A")), ("active", t["text"])])

        # Treeview background, fieldbackground, borders
        style.configure("Treeview",
                        background=t["entry_bg"],
                        foreground=t["text"],
                        fieldbackground=t["entry_bg"],
                        bordercolor=t["border"],
                        darkcolor=t["border"],
                        lightcolor=t["border"],
                        rowheight=26,
                        font=FONT_NORM)
        style.configure("Treeview.Heading",
                        background=t["panel"],
                        foreground=t["text"],
                        bordercolor=t["border"],
                        font=FONT_BOLD,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", t.get("select_bg", t["accent"]))],
                  foreground=[("selected", t.get("select_fg", "#FFFFFF"))])
        style.map("Treeview.Heading",
                  background=[("active", t["border"])],
                  foreground=[("active", t["text"])])

        # Combobox styling (both entry & dropdown listbox)
        sel_fg = t.get("select_fg", t.get("btn_accent_fg", "#FFFFFF"))
        style.configure("TCombobox",
                        fieldbackground=t["entry_bg"],
                        background=t["panel"],
                        foreground=t["text"],
                        selectbackground=t["accent"],
                        selectforeground=sel_fg,
                        bordercolor=t["border"],
                        darkcolor=t["border"],
                        lightcolor=t["border"],
                        arrowcolor=t["accent"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", t["entry_bg"]), ("active", t["entry_bg"]), ("focus", t["entry_bg"])],
                  selectbackground=[("readonly", t["accent"]), ("active", t["accent"]), ("focus", t["accent"])],
                  selectforeground=[("readonly", sel_fg), ("active", sel_fg)],
                  background=[("readonly", t["panel"]), ("active", t["panel"]), ("focus", t["panel"])],
                  foreground=[("readonly", t["text"]), ("active", t["text"]), ("focus", t["text"])],
                  bordercolor=[("readonly", t["border"]), ("active", t["accent"]), ("focus", t["accent"])],
                  arrowcolor=[("readonly", t["accent"]), ("active", t.get("accent2", t["accent"])), ("focus", t["accent"])])

        self._update_combobox_popdowns()

    def _update_combobox_popdowns(self):
        """Theme the popup listboxes of all Comboboxes in the Tk database."""
        t = self.theme
        sel_fg = t.get("select_fg", t.get("btn_accent_fg", "#FFFFFF"))
        try:
            self.option_add("*TCombobox*Listbox.background", t["entry_bg"])
            self.option_add("*TCombobox*Listbox.foreground", t["text"])
            self.option_add("*TCombobox*Listbox.selectBackground", t["accent"])
            self.option_add("*TCombobox*Listbox.selectForeground", sel_fg)
            self.option_add("*TCombobox*Listbox.font", FONT_SM)
            self.option_add("*ComboboxPopdown*Listbox.background", t["entry_bg"])
            self.option_add("*ComboboxPopdown*Listbox.foreground", t["text"])
            self.option_add("*ComboboxPopdown*Listbox.selectBackground", t["accent"])
            self.option_add("*ComboboxPopdown*Listbox.selectForeground", sel_fg)
            self.option_add("*ComboboxPopdown*Listbox.font", FONT_SM)
        except Exception:
            pass

    def _center_window(self, win: tk.Toplevel, width: int = 560, height: int = 400):
        """Center a modal accurately over the Artemis main window."""
        self.update_idletasks()
        rx = self.winfo_rootx()
        ry = self.winfo_rooty()
        rw = self.winfo_width()
        rh = self.winfo_height()
        if rw > 100 and rh > 100:
            x = max(20, rx + (rw - width) // 2)
            y = max(20, ry + (rh - height) // 2)
        else:
            x = (self.winfo_screenwidth() - width) // 2
            y = (self.winfo_screenheight() - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")

    # ══════════════════════════════════════════════════════════════════════════
    #  THEMED DIALOGS (Zero Native Stark-White Popups)
    # ══════════════════════════════════════════════════════════════════════════
    def _show_themed_info(self, title: str, message: str, icon: str = "ℹ", parent=None):
        t = self.theme
        win = tk.Toplevel(parent or self)
        win.title(title)
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        win.transient(parent or self)
        win.grab_set()
        self._load_app_icon(win)
        self._apply_dark_titlebar(win)

        calc_w = 540
        calc_h = max(240, 180 + (message.count("\n") * 18))
        self._center_window(win, calc_w, calc_h)

        card = tk.Frame(win, bg=t["panel"], padx=20, pady=16, highlightbackground=t["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        hdr = tk.Frame(card, bg=t["panel"])
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text=icon, font=("Segoe UI", 16), bg=t["panel"], fg=t["accent"]).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text=title, font=FONT_HEAD, bg=t["panel"], fg=t["text"]).pack(side="left")

        tk.Frame(card, bg=t["border"], height=1).pack(fill="x", pady=(0, 10))
        tk.Label(card, text=message, font=FONT_NORM, bg=t["panel"], fg=t["text"], justify="left", wraplength=calc_w - 60).pack(anchor="w", fill="both", expand=True, pady=(0, 12))

        b_row = tk.Frame(card, bg=t["panel"])
        b_row.pack(fill="x", side="bottom")
        btn = self._btn(b_row, "OK", win.destroy, accent=True, padx=18, pady=6)
        btn.pack(side="right")
        btn.focus_set()

        win.bind("<Return>", lambda e: win.destroy())
        win.bind("<Escape>", lambda e: win.destroy())
        win.wait_window()

    def _show_themed_warning(self, title: str, message: str, icon: str = "⚠", parent=None):
        self._show_themed_info(title, message, icon=icon, parent=parent)

    def _show_themed_error(self, title: str, message: str, icon: str = "❌", parent=None):
        self._show_themed_info(title, message, icon=icon, parent=parent)

    def _show_themed_confirm(self, title: str, message: str, confirm_text: str = "Yes", cancel_text: str = "No", icon: str = "❓", parent=None) -> bool:
        t = self.theme
        win = tk.Toplevel(parent or self)
        win.title(title)
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        win.transient(parent or self)
        win.grab_set()
        self._load_app_icon(win)
        self._apply_dark_titlebar(win)

        result = [False]
        calc_w = 540
        calc_h = max(250, 190 + (message.count("\n") * 18))
        self._center_window(win, calc_w, calc_h)

        card = tk.Frame(win, bg=t["panel"], padx=20, pady=16, highlightbackground=t["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        hdr = tk.Frame(card, bg=t["panel"])
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text=icon, font=("Segoe UI", 16), bg=t["panel"], fg=t["accent"]).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text=title, font=FONT_HEAD, bg=t["panel"], fg=t["text"]).pack(side="left")

        tk.Frame(card, bg=t["border"], height=1).pack(fill="x", pady=(0, 10))
        tk.Label(card, text=message, font=FONT_NORM, bg=t["panel"], fg=t["text"], justify="left", wraplength=calc_w - 60).pack(anchor="w", fill="both", expand=True, pady=(0, 12))

        b_row = tk.Frame(card, bg=t["panel"])
        b_row.pack(fill="x", side="bottom")

        def _on_yes():
            result[0] = True
            win.destroy()

        def _on_no():
            result[0] = False
            win.destroy()

        self._btn(b_row, cancel_text, _on_no, padx=14, pady=6).pack(side="right", padx=(6, 0))
        y_btn = self._btn(b_row, confirm_text, _on_yes, accent=True, padx=18, pady=6)
        y_btn.pack(side="right")
        y_btn.focus_set()

        win.bind("<Return>", lambda e: _on_yes())
        win.bind("<Escape>", lambda e: _on_no())
        win.wait_window()
        return result[0]

    def _btn(self, parent, text, cmd, accent=False, danger=False, **kwargs):
        t = self.theme
        if accent:
            bg = t.get("accent", "#10B981")
            fg = t.get("btn_accent_fg", "#070D0A")
            active_bg = t.get("accent2", bg)
        elif danger:
            bg = t.get("danger", "#EF4444")
            fg = "#FFFFFF"
            active_bg = "#DC2626"
        else:
            bg = t.get("btn_normal_bg", t.get("panel", "#13251D"))
            fg = t.get("btn_normal_fg", t.get("text", "#ECFDF5"))
            active_bg = t.get("border", "#164E33")

        font = kwargs.pop("font", FONT_BOLD if accent else FONT_NORM)
        padx = kwargs.pop("padx", 10)
        pady = kwargs.pop("pady", 4)

        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief="flat",
                         font=font, padx=padx, pady=pady, activebackground=active_bg,
                         activeforeground=fg, cursor="hand2", **kwargs)

    # ══════════════════════════════════════════════════════════════════════════
    #  UI LAYOUT
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        t = self.theme

        # ── 1. Top Header Bar ────────────────────────────────────────────────
        self.top_bar = tk.Frame(self, bg=t["panel"], padx=14, pady=8, highlightbackground=t["border"], highlightthickness=1)
        self.top_bar.pack(fill="x", side="top")

        # Left Branding
        brand_f = tk.Frame(self.top_bar, bg=t["panel"])
        brand_f.pack(side="left")
        tk.Label(brand_f, text="🏹", font=("Segoe UI", 16), bg=t["panel"], fg=t.get("accent_gold", t["accent"])).pack(side="left", padx=(0, 6))

        title_box = tk.Frame(brand_f, bg=t["panel"])
        title_box.pack(side="left")
        tk.Label(title_box, text="ARTEMIS RIGHTS ENGINE", font=FONT_HEAD, bg=t["panel"], fg=t["text"]).pack(anchor="w")
        tk.Label(title_box, text="Autonomous Platform Enforcement, LOA Registry & Legal Notice Hub", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w")

        # Right Controls
        right_f = tk.Frame(self.top_bar, bg=t["panel"])
        right_f.pack(side="right")

        self.intake_btn = self._btn(right_f, "📥 Ingest Apollo Batches (0)", self._ingest_pending_batches, accent=True)
        self.intake_btn.pack(side="left", padx=(0, 6))

        self._btn(right_f, "🔄 Refresh", self._refresh_all).pack(side="left", padx=(0, 6))

        # ── Settings ▾ Menubutton ──
        self.settings_mb = tk.Menubutton(
            right_f,
            text="⚙ Settings ▾",
            font=FONT_NORM,
            bg=t.get("btn_normal_bg", t["panel"]),
            fg=t.get("btn_normal_fg", t["text"]),
            activebackground=t.get("accent", "#10B981"),
            activeforeground=t.get("btn_accent_fg", "#070D0A"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        self.settings_mb.pack(side="left")

        self.settings_menu = tk.Menu(
            self.settings_mb,
            tearoff=0,
            bg=t["panel"],
            fg=t["text"],
            activebackground=t["accent"],
            activeforeground=t.get("btn_accent_fg", "#070D0A"),
            bd=1,
            relief="solid",
            selectcolor=t["accent"]
        )
        self.settings_mb.config(menu=self.settings_menu)

        # 1. Themes Submenu
        self.theme_menu = tk.Menu(
            self.settings_menu,
            tearoff=0,
            bg=t["panel"],
            fg=t["text"],
            activebackground=t["accent"],
            activeforeground=t.get("btn_accent_fg", "#070D0A"),
            bd=1,
            relief="solid",
            selectcolor=t["accent"]
        )
        self.theme_var = tk.StringVar(value=self.current_theme_key)
        for th_k, th_d in ARTEMIS_THEMES.items():
            self.theme_menu.add_radiobutton(
                label=th_d.get("name", th_k),
                variable=self.theme_var,
                value=th_k,
                command=lambda k=th_k: self._on_theme_changed(k)
            )
        self.settings_menu.add_cascade(label="🎨 Themes ▾", menu=self.theme_menu)

        # 2. Brand Rights Modal
        self.settings_menu.add_separator()
        self.settings_menu.add_command(
            label="⚖ Brand Rights & LOA Registry...",
            command=self._open_add_brand_dialog
        )

        # 3. Field Guide
        self.settings_menu.add_command(
            label="📚 Artemis Field Guide (F1)...",
            command=self._open_field_guide
        )

        # 4. Open Storage Folder
        self.settings_menu.add_command(
            label="📁 Open Artemis Storage Folder...",
            command=self._open_artemis_appdata_dir
        )

        # 5. Pre-Flight Diagnostics
        self.settings_menu.add_separator()
        self.settings_menu.add_command(
            label="🩺 Pre-Flight System Diagnostics...",
            command=self._open_system_diagnostics
        )

        # 6. About Artemis
        self.settings_menu.add_separator()
        self.settings_menu.add_command(
            label="ℹ About Artemis Rights Engine...",
            command=self._show_about_dialog
        )

        # ── 2. Notebook Tabs ─────────────────────────────────────────────────
        self.nb = ttk.Notebook(self, style="Artemis.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        # Tab 1: Active Enforcement Queue
        self.tab_queue = tk.Frame(self.nb, bg=t["bg"], padx=10, pady=8)
        self.nb.add(self.tab_queue, text="🎯 Active Enforcement Queue")
        self._build_queue_tab(self.tab_queue)

        # Tab 2: Portals & Sessions
        self.tab_portals = tk.Frame(self.nb, bg=t["bg"], padx=14, pady=12)
        self.nb.add(self.tab_portals, text="🔐 Platform Portals")
        self._build_portals_tab(self.tab_portals)

        # Tab 3: Rights Owners & LOA Registry
        self.tab_rights = tk.Frame(self.nb, bg=t["bg"], padx=14, pady=12)
        self.nb.add(self.tab_rights, text="📜 Rights Registry & LOA")
        self._build_rights_tab(self.tab_rights)

        # Tab 4: Submission Audit Log
        self.tab_history = tk.Frame(self.nb, bg=t["bg"], padx=10, pady=8)
        self.nb.add(self.tab_history, text="📊 Submission History")
        self._build_history_tab(self.tab_history)

        # ── 3. Bottom Status Bar ─────────────────────────────────────────────
        self.status_bar = tk.Frame(self, bg=t["panel"], padx=10, pady=4)
        self.status_bar.pack(fill="x", side="bottom")

        self.status_lbl = tk.Label(self.status_bar, text="Ready.", font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        self.status_lbl.pack(side="left")

        self.stats_lbl = tk.Label(self.status_bar, text="Queue: 0 | History: 0", font=FONT_SM, bg=t["panel"], fg=t["text"])
        self.stats_lbl.pack(side="right")

    def _set_status(self, text: str):
        self.status_lbl.config(text=text)

    def _on_theme_changed(self, theme_key: Optional[str] = None):
        new_k = theme_key or self.theme_var.get()
        if new_k in ARTEMIS_THEMES and new_k != self.current_theme_key:
            self.current_theme_key = new_k
            self.theme = ARTEMIS_THEMES[new_k]
            self.data_store.set_setting("theme", new_k)
            self.configure(bg=self.theme["bg"])
            self._apply_dark_titlebar()
            self._configure_ttk_styles()
            self._rebuild_all_tabs()
            self._set_status(f"Theme switched to {self.theme.get('name', new_k)}.")

    def _open_field_guide(self):
        ArtemisFieldGuideModal(self)

    def _open_artemis_appdata_dir(self):
        base_dir = get_artemis_base_dir()
        os.makedirs(base_dir, exist_ok=True)
        try:
            os.startfile(base_dir)
            self._set_status(f"Opened storage directory: {base_dir}")
        except Exception as e:
            self._show_themed_error("Open Directory Error", f"Could not open storage directory:\n{e}")

    def _open_system_diagnostics(self):
        """Launch the Pre-Flight System Diagnostics & Telemetry modal."""
        try:
            from system_diagnostics import open_diagnostics_modal
            open_diagnostics_modal(self, self.theme)
        except Exception as e:
            self._show_themed_error("Diagnostics Error", f"Unable to launch diagnostics:\n{e}")

    def _show_about_dialog(self):
        msg = (
            "🏹 Artemis Rights Engine — Version 1.0.0\n"
            "Autonomous Platform Enforcement & LOA Registry Hub\n\n"
            "The Apollo & Artemis Initiative:\n"
            "• Apollo Brand Intelligence: The Eyes — Multi-Sector Discovery & Forensic Reconnaissance.\n"
            "• Artemis Rights Engine: The Hands — Sovereign Form Automation, Legal Assertion & LOA Vault.\n\n"
            "Persistent Storage:\n"
            f"{get_artemis_base_dir()}\n\n"
            "Architecture: Decoupled Multi-Process IPC Protocol."
        )
        self._show_themed_info("About Artemis Rights Engine", msg, icon="🏹")

    def _rebuild_all_tabs(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()
        self._check_pending_intake(silent=True)
        self._refresh_queue_table()

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 1: ENFORCEMENT QUEUE (With Listing URL Column & Context Menu)
    # ══════════════════════════════════════════════════════════════════════════
    def _build_queue_tab(self, parent):
        t = self.theme

        # Filters Bar
        f_bar = tk.Frame(parent, bg=t["panel"], padx=10, pady=6, highlightbackground=t["border"], highlightthickness=1)
        f_bar.pack(fill="x", pady=(0, 6))

        tk.Label(f_bar, text="Filter Platform:", font=FONT_NORM, bg=t["panel"], fg=t["text"]).pack(side="left", padx=(0, 4))
        self.filter_platform_var = tk.StringVar(value="All Platforms")
        self.filter_platform_cb = ttk.Combobox(f_bar, textvariable=self.filter_platform_var, values=["All Platforms", "Amazon", "Walmart", "eBay", "Redbubble", "Printerval"], state="readonly", width=16, font=FONT_SM)
        self.filter_platform_cb.pack(side="left", padx=(0, 12))
        self.filter_platform_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_queue_table())

        tk.Label(f_bar, text="Filter Brand:", font=FONT_NORM, bg=t["panel"], fg=t["text"]).pack(side="left", padx=(0, 4))
        self.filter_brand_var = tk.StringVar(value="All Brands")
        self.filter_brand_cb = ttk.Combobox(f_bar, textvariable=self.filter_brand_var, values=["All Brands"], state="readonly", width=16, font=FONT_SM)
        self.filter_brand_cb.pack(side="left", padx=(0, 12))
        self.filter_brand_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_queue_table())

        # Select all / Deselect
        self._btn(f_bar, "Select All", self._select_all_queue).pack(side="right", padx=(4, 0))
        self._btn(f_bar, "Deselect All", self._deselect_all_queue).pack(side="right")

        # Treeview Container
        tree_f = tk.Frame(parent, bg=t["bg"])
        tree_f.pack(fill="both", expand=True)

        cols = ("select", "status", "platform", "item_id", "brand", "seller", "price", "title", "url")
        self.queue_tree = ttk.Treeview(tree_f, columns=cols, show="headings", selectmode="extended")

        self.queue_tree.heading("select", text="✓")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.heading("platform", text="Platform")
        self.queue_tree.heading("item_id", text="Item ID")
        self.queue_tree.heading("brand", text="Brand")
        self.queue_tree.heading("seller", text="Seller / Merchant")
        self.queue_tree.heading("price", text="Price")
        self.queue_tree.heading("title", text="Listing Title")
        self.queue_tree.heading("url", text="Listing URL")

        self.queue_tree.column("select", width=35, anchor="center")
        self.queue_tree.column("status", width=85, anchor="center")
        self.queue_tree.column("platform", width=95, anchor="center")
        self.queue_tree.column("item_id", width=120, anchor="w")
        self.queue_tree.column("brand", width=110, anchor="w")
        self.queue_tree.column("seller", width=140, anchor="w")
        self.queue_tree.column("price", width=70, anchor="center")
        self.queue_tree.column("title", width=340, anchor="w")
        self.queue_tree.column("url", width=280, anchor="w")

        scroll_y = ttk.Scrollbar(tree_f, orient="vertical", command=self.queue_tree.yview)
        scroll_x = ttk.Scrollbar(tree_f, orient="horizontal", command=self.queue_tree.xview)
        self.queue_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.queue_tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.queue_tree.bind("<Button-1>", self._on_queue_tree_click)
        self.queue_tree.bind("<Button-3>", self._show_queue_context_menu)
        self.queue_tree.bind("<Double-Button-1>", self._on_queue_double_click)

        # Bottom Action Bar
        act_bar = tk.Frame(parent, bg=t["panel"], padx=10, pady=8, highlightbackground=t["border"], highlightthickness=1)
        act_bar.pack(fill="x", pady=(6, 0))

        self._btn(act_bar, "🚀 Engage Portal Automation", self._engage_portal_automation, accent=True).pack(side="left", padx=(0, 6))
        self._btn(act_bar, "📄 Draft Formal Notice", self._draft_notice_dialog).pack(side="left", padx=(0, 6))
        self._btn(act_bar, "📊 Export Batch CSV", self._export_batch_csv_dialog).pack(side="left", padx=(0, 6))
        self._btn(act_bar, "✓ Mark as Filed", self._mark_selected_filed).pack(side="left", padx=(0, 6))
        self._btn(act_bar, "🗑 Remove Selected", self._remove_selected_queue, danger=True).pack(side="right")

    def _show_queue_context_menu(self, event):
        row_id = self.queue_tree.identify_row(event.y)
        if row_id:
            self.queue_tree.selection_set(row_id)
        selected_iids = self.queue_tree.selection()
        if not selected_iids:
            return

        t = self.theme
        menu = tk.Menu(self, tearoff=0, bg=t["panel"], fg=t["text"],
                       activebackground=t["accent"], activeforeground=t.get("btn_accent_fg", "#070D0A"))

        menu.add_command(label="🌐 Open URL in Browser", command=self._open_selected_listing_url)
        menu.add_command(label="📋 Copy Listing URL", command=self._copy_selected_listing_url)
        menu.add_command(label="📋 Copy Item ID", command=self._copy_selected_item_id)
        menu.add_separator()
        menu.add_command(label="🚀 Engage Portal for Selected", command=self._engage_portal_automation)
        menu.add_command(label="📄 Draft Notice for Selected", command=self._draft_notice_dialog)
        menu.add_separator()
        menu.add_command(label="✓ Mark as Filed", command=self._mark_selected_filed)
        menu.add_command(label="🗑 Remove Selected", command=self._remove_selected_queue)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_queue_double_click(self, event):
        self._open_selected_listing_url()

    def _open_selected_listing_url(self):
        items = self._get_selected_items()
        if items and items[0].get("url"):
            webbrowser.open_new_tab(items[0]["url"])

    def _copy_selected_listing_url(self):
        items = self._get_selected_items()
        if items and items[0].get("url"):
            self.clipboard_clear()
            self.clipboard_append(items[0]["url"])
            self._set_status(f"Copied listing URL: {items[0]['url']}")

    def _copy_selected_item_id(self):
        items = self._get_selected_items()
        if items and items[0].get("item_id"):
            self.clipboard_clear()
            self.clipboard_append(items[0]["item_id"])
            self._set_status(f"Copied item ID: {items[0]['item_id']}")

    def _on_queue_tree_click(self, event):
        region = self.queue_tree.identify_region(event.x, event.y)
        if region == "cell":
            col = self.queue_tree.identify_column(event.x)
            item_iid = self.queue_tree.identify_row(event.y)
            if col == "#1" and item_iid:
                qid = item_iid
                if qid in self.selected_queue_ids:
                    self.selected_queue_ids.remove(qid)
                    self.queue_tree.set(item_iid, "select", "○")
                else:
                    self.selected_queue_ids.add(qid)
                    self.queue_tree.set(item_iid, "select", "✓")

    def _select_all_queue(self):
        for iid in self.queue_tree.get_children():
            self.selected_queue_ids.add(iid)
            self.queue_tree.set(iid, "select", "✓")

    def _deselect_all_queue(self):
        for iid in self.queue_tree.get_children():
            self.queue_tree.set(iid, "select", "○")
        self.selected_queue_ids.clear()

    def _get_selected_items(self) -> List[Dict[str, Any]]:
        queue = self.data_store.get_enforcement_queue()
        q_map = {it.get("queue_id"): it for it in queue}
        # First check explicitly checked boxes
        checked = [q_map[qid] for qid in self.selected_queue_ids if qid in q_map]
        if checked:
            return checked
        # Fallback to selected Treeview row
        tree_sel = self.queue_tree.selection()
        if tree_sel:
            return [q_map[iid] for iid in tree_sel if iid in q_map]
        return []

    def _refresh_queue_table(self):
        self.queue_tree.delete(*self.queue_tree.get_children())
        queue = self.data_store.get_enforcement_queue()

        p_filter = self.filter_platform_var.get()
        b_filter = self.filter_brand_var.get()

        brands_found = sorted({it.get("brand") for it in queue if it.get("brand")})
        self.filter_brand_cb["values"] = ["All Brands"] + brands_found

        visible_count = 0
        for it in queue:
            qid = it.get("queue_id", "")
            platform = it.get("platform", "Unknown")
            brand = it.get("brand", "Unassigned")

            if p_filter != "All Platforms" and p_filter.lower() not in platform.lower():
                continue
            if b_filter != "All Brands" and b_filter != brand:
                continue

            sel_char = "✓" if qid in self.selected_queue_ids else "○"
            self.queue_tree.insert(
                "", "end", iid=qid,
                values=(
                    sel_char,
                    it.get("status", "Pending"),
                    platform,
                    it.get("item_id", ""),
                    brand,
                    it.get("seller", ""),
                    it.get("price", ""),
                    it.get("title", ""),
                    it.get("url", "")
                )
            )
            visible_count += 1

        self.stats_lbl.config(text=f"Queue: {len(queue)} items ({visible_count} visible) | History: {len(self.data_store.get_submission_history())}")

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 2: PORTALS & PERSISTENT SESSIONS
    # ══════════════════════════════════════════════════════════════════════════
    def _build_portals_tab(self, parent):
        t = self.theme
        tk.Label(parent, text="🔐 CONFIGURED ENFORCEMENT PORTALS", font=FONT_HEAD, bg=t["bg"], fg=t.get("accent_gold", t["accent"])).pack(anchor="w", pady=(0, 4))
        tk.Label(parent, text="Launch interactive browser portals to authenticate once or inspect active takedown accounts.", font=FONT_SM, bg=t["bg"], fg=t["subtext"]).pack(anchor="w", pady=(0, 12))

        portals = self.data_store.get_portal_configs()
        for p_name, cfg in portals.items():
            card = tk.Frame(parent, bg=t["panel"], padx=14, pady=10, highlightbackground=t["border"], highlightthickness=1)
            card.pack(fill="x", pady=4)

            row = tk.Frame(card, bg=t["panel"])
            row.pack(fill="x")

            tk.Label(row, text=f"🏛 {cfg.get('name', p_name)}", font=FONT_BOLD, bg=t["panel"], fg=t["text"]).pack(side="left")
            p_url = cfg.get("portal_url", "")

            btn_launch = self._btn(row, "🚀 Open Portal in Browser", lambda u=p_url: self._open_url(u), accent=True)
            btn_launch.pack(side="right")

            info_row = tk.Frame(card, bg=t["panel"])
            info_row.pack(fill="x", pady=(4, 0))
            tk.Label(info_row, text=f"• Intake Identifier: {cfg.get('id_type', 'N/A')}  |  Batch Limit: {cfg.get('batch_limit', 'Unlimited')}", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left")

    def _open_url(self, url: str):
        if url:
            webbrowser.open_new_tab(url)

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 3: RIGHTS OWNERS & LOA REGISTRY
    # ══════════════════════════════════════════════════════════════════════════
    def _build_rights_tab(self, parent):
        t = self.theme

        # Top Action Toolbar
        t_bar = tk.Frame(parent, bg=t["panel"], padx=12, pady=8, highlightbackground=t["border"], highlightthickness=1)
        t_bar.pack(fill="x", pady=(0, 10))

        tk.Label(t_bar, text="📜 BRAND RIGHTS OWNERS & LETTERS OF AUTHORIZATION (LOA)", font=FONT_HEAD, bg=t["panel"], fg=t.get("accent_gold", t["accent"])).pack(side="left")

        self._btn(t_bar, "➕ Add Brand Rights", self._open_add_brand_dialog, accent=True).pack(side="right", padx=(6, 0))

        # Scrollable container for brand cards
        container = tk.Frame(parent, bg=t["bg"])
        container.pack(fill="both", expand=True)

        self.rights_canvas = tk.Canvas(container, bg=t["bg"], highlightthickness=0)
        self.rights_scroll = ttk.Scrollbar(container, orient="vertical", command=self.rights_canvas.yview)
        self.rights_frame = tk.Frame(self.rights_canvas, bg=t["bg"])

        self.rights_frame.bind("<Configure>", lambda e: self.rights_canvas.configure(scrollregion=self.rights_canvas.bbox("all")))
        self.rights_canvas.create_window((0, 0), window=self.rights_frame, anchor="nw", width=1180)
        self.rights_canvas.configure(yscrollcommand=self.rights_scroll.set)

        self.rights_canvas.pack(side="left", fill="both", expand=True)
        self.rights_scroll.pack(side="right", fill="y")

        # Mousewheel binding
        self._bind_mousewheel(self.rights_canvas)
        self._refresh_rights_cards()

    def _bind_mousewheel(self, widget):
        def _on_mw(event):
            delta = int(-1 * (event.delta / 120)) if event.delta else 1
            self.rights_canvas.yview_scroll(delta, "units")
        widget.bind("<MouseWheel>", _on_mw)
        self.rights_frame.bind("<MouseWheel>", _on_mw)

    def _refresh_rights_cards(self):
        t = self.theme
        for child in self.rights_frame.winfo_children():
            child.destroy()

        brands = self.data_store.get_all_brands()
        if not brands:
            empty_box = tk.Frame(self.rights_frame, bg=t["panel"], padx=20, pady=20, highlightbackground=t["border"], highlightthickness=1)
            empty_box.pack(fill="x", pady=10)
            tk.Label(empty_box, text="No Brand Rights on Record", font=FONT_HEAD, bg=t["panel"], fg=t["text"]).pack(anchor="w")
            tk.Label(empty_box, text="Click '➕ Add Brand Rights' above to register authorized legal entities and attach LOAs.", font=FONT_NORM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w", pady=(4, 0))
            return

        for b_name, b_info in sorted(brands.items()):
            card = tk.Frame(self.rights_frame, bg=t["panel"], padx=16, pady=12, highlightbackground=t["border"], highlightthickness=1)
            card.pack(fill="x", pady=6)

            # Top Header Row
            hdr = tk.Frame(card, bg=t["panel"])
            hdr.pack(fill="x")

            title_txt = f"🛡 {b_name} — {b_info.get('rights_holder', 'Legal Entity')}"
            tk.Label(hdr, text=title_txt, font=FONT_HEAD, bg=t["panel"], fg=t["text"]).pack(side="left")

            btn_del = self._btn(hdr, "🗑 Remove", lambda bn=b_name: self._remove_brand_rights(bn), danger=True, padx=8, pady=2)
            btn_del.pack(side="right", padx=(6, 0))

            btn_edit = self._btn(hdr, "✏ Edit Profile", lambda bn=b_name: self._open_edit_brand_dialog(bn), padx=8, pady=2)
            btn_edit.pack(side="right")

            # Address & Phone Row
            addr = b_info.get("company_address", "Corporate Address on Record")
            phone = b_info.get("phone_number", "Phone on Record")
            agent = b_info.get("authorized_agent", "Designated Agent")
            email = b_info.get("contact_email", "ip.protection@brand.com")

            r1 = tk.Frame(card, bg=t["panel"])
            r1.pack(fill="x", pady=(4, 0))
            tk.Label(r1, text=f"📍 Corporate Address: {addr}  |  📞 {phone}", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w")

            r2 = tk.Frame(card, bg=t["panel"])
            r2.pack(fill="x", pady=(2, 0))
            tk.Label(r2, text=f"👤 Authorized Signatory: {agent}  |  ✉ {email}", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w")

            # Trademarks & Copyrights
            tm_regs = ", ".join(b_info.get("trademark_regs", [])) or "None listed"
            cr_regs = ", ".join(b_info.get("copyright_regs", [])) or "None listed"
            r3 = tk.Frame(card, bg=t["panel"])
            r3.pack(fill="x", pady=(2, 0))
            tk.Label(r3, text=f"🔖 Trademarks: {tm_regs}  |  © Copyrights: {cr_regs}", font=FONT_SM, bg=t["panel"], fg=t["accent"]).pack(anchor="w")

            # LOA Attachment Row
            loa_path = b_info.get("loa_path", "")
            r4 = tk.Frame(card, bg=t["panel"])
            r4.pack(fill="x", pady=(6, 0))

            if loa_path and os.path.exists(loa_path):
                tk.Label(r4, text=f"📎 Letter of Authorization (LOA): {os.path.basename(loa_path)}", font=FONT_BOLD, bg=t["panel"], fg=t["success"]).pack(side="left")
                self._btn(r4, "👁 Open LOA", lambda lp=loa_path: self._open_loa_file(lp), padx=8, pady=2).pack(side="left", padx=(10, 0))
            else:
                tk.Label(r4, text="⚠️ No LOA Document Attached", font=FONT_SM, bg=t["panel"], fg=t["warning"]).pack(side="left")
                self._btn(r4, "📎 Attach LOA Document", lambda bn=b_name: self._attach_loa_quick(bn), padx=8, pady=2).pack(side="left", padx=(10, 0))

    def _open_loa_file(self, loa_path: str):
        if not loa_path or not os.path.exists(loa_path):
            self._show_themed_warning("File Not Found", f"The LOA file could not be found at:\n{loa_path}", icon="⚠")
            return
        try:
            os.startfile(loa_path)
        except Exception as e:
            self._show_themed_error("Open File Error", f"Could not open LOA document:\n{e}", icon="❌")

    def _attach_loa_quick(self, brand_name: str):
        init_dir = get_artemis_base_dir()
        path = filedialog.askopenfilename(
            parent=self,
            initialdir=init_dir,
            title=f"Attach Letter of Authorization (LOA) for {brand_name}",
            filetypes=[("Legal & Image Documents", "*.pdf;*.png;*.jpg;*.jpeg;*.docx"), ("All Files", "*.*")]
        )
        if path:
            try:
                dest = self.data_store.store_loa_document(brand_name, path)
                self._refresh_rights_cards()
                self._show_themed_info("LOA Attached", f"Successfully attached LOA for {brand_name}!\n\nStored to:\n{dest}", icon="📎")
            except Exception as e:
                self._show_themed_error("Attachment Error", f"Failed to attach LOA document:\n{e}", icon="❌")

    def _open_add_brand_dialog(self):
        BrandRightsModal(self, brand_name=None, on_save=self._refresh_rights_cards)

    def _open_edit_brand_dialog(self, brand_name: str):
        BrandRightsModal(self, brand_name=brand_name, on_save=self._refresh_rights_cards)

    def _remove_brand_rights(self, brand_name: str):
        if self._show_themed_confirm("Remove Brand Rights", f"Remove legal brand rights for '{brand_name}' from the registry?", icon="🗑"):
            self.data_store.remove_brand_rights(brand_name)
            self._refresh_rights_cards()
            self._set_status(f"Removed brand rights for '{brand_name}'.")

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 4: SUBMISSION AUDIT LOG
    # ══════════════════════════════════════════════════════════════════════════
    def _build_history_tab(self, parent):
        t = self.theme
        cols = ("time", "platform", "brand", "count", "type", "ref")
        self.hist_tree = ttk.Treeview(parent, columns=cols, show="headings")
        self.hist_tree.heading("time", text="Timestamp")
        self.hist_tree.heading("platform", text="Platform")
        self.hist_tree.heading("brand", text="Brand")
        self.hist_tree.heading("count", text="Items Filed")
        self.hist_tree.heading("type", text="Method")
        self.hist_tree.heading("ref", text="Reference / Notice ID")

        self.hist_tree.column("time", width=140, anchor="center")
        self.hist_tree.column("platform", width=100, anchor="center")
        self.hist_tree.column("brand", width=130, anchor="w")
        self.hist_tree.column("count", width=80, anchor="center")
        self.hist_tree.column("type", width=140, anchor="center")
        self.hist_tree.column("ref", width=340, anchor="w")

        self.hist_tree.pack(fill="both", expand=True)
        self._refresh_history_table()

    def _refresh_history_table(self):
        self.hist_tree.delete(*self.hist_tree.get_children())
        hist = self.data_store.get_submission_history()
        for h in hist:
            self.hist_tree.insert(
                "", "end",
                values=(
                    h.get("submitted_at", ""),
                    h.get("platform", ""),
                    h.get("brand", ""),
                    h.get("total_items", 0),
                    h.get("submission_type", "Manual"),
                    h.get("notice_reference", "")
                )
            )

    # ══════════════════════════════════════════════════════════════════════════
    #  INTAKE & ACTIONS
    # ══════════════════════════════════════════════════════════════════════════
    def _check_pending_intake(self, silent=False):
        batches = get_pending_artemis_batches()
        count = len(batches)
        total_items = sum(b.get("total_items", 0) for b in batches)
        self.intake_btn.config(text=f"📥 Ingest Apollo Batches ({count})")
        if count > 0 and not silent:
            self._set_status(f"Found {count} incoming Apollo batch(es) with {total_items} items.")

    def _ingest_pending_batches(self):
        batches = get_pending_artemis_batches()
        if not batches:
            self._show_themed_info("No Pending Batches", "There are currently no new intake batches from Apollo.", icon="ℹ")
            return

        total_added = 0
        for b in batches:
            listings = b.get("listings", [])
            added = self.data_store.enqueue_listings(listings, source_batch=b.get("batch_name", "Apollo Batch"))
            mark_batch_as_ingested(b["_filepath"])
            total_added += added

        self._check_pending_intake(silent=True)
        self._refresh_queue_table()
        self._set_status(f"Successfully ingested {total_added} new items from {len(batches)} Apollo batch(es).")
        self._show_themed_info("Intake Complete", f"Successfully ingested {total_added} items from {len(batches)} Apollo recon batch(es) into the Artemis enforcement queue!", icon="📥")

    def _engage_portal_automation(self):
        items = self._get_selected_items()
        if not items:
            self._show_themed_warning("No Items Selected", "Please select at least one item using the [✓] checkboxes to launch portal automation.", icon="⚠")
            return

        platforms = {it.get("platform", "Unknown") for it in items}
        if len(platforms) > 1:
            self._show_themed_warning("Multi-Platform Selection", f"You have selected items spanning multiple platforms: {', '.join(platforms)}.\nPlease filter and select items for one platform at a time.", icon="⚠")
            return

        target_platform = list(platforms)[0]
        self.engine.launch_assisted_portal_session(target_platform, items, on_status=self._set_status)

    def _draft_notice_dialog(self):
        items = self._get_selected_items()
        if not items:
            self._show_themed_warning("No Items Selected", "Please select at least one item using the [✓] checkboxes to draft a formal legal notice.", icon="⚠")
            return

        brands = {it.get("brand", "Unassigned") for it in items}
        primary_brand = list(brands)[0] if brands else "Protected Brand"
        primary_platform = items[0].get("platform", "E-Commerce Platform")

        notice_text = self.engine.generate_notice_text(primary_platform, primary_brand, items)

        win = tk.Toplevel(self)
        win.title("📄 Draft Formal Infringement Notice")
        win.geometry("820x660")
        win.configure(bg=self.theme["bg"])
        win.transient(self)
        self._load_app_icon(win)
        self._apply_dark_titlebar(win)
        self._center_window(win, 820, 660)

        txt = tk.Text(win, bg=self.theme["entry_bg"], fg=self.theme["text"], font=FONT_CODE, padx=10, pady=10, insertbackground=self.theme["text"])
        txt.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        txt.insert("1.0", notice_text)

        b_bar = tk.Frame(win, bg=self.theme["panel"], padx=10, pady=6)
        b_bar.pack(fill="x")

        def _copy():
            self.clipboard_clear()
            self.clipboard_append(notice_text)
            self._show_themed_info("Copied", "Notice copied to clipboard!", icon="📋", parent=win)

        self._btn(b_bar, "📋 Copy Notice Text", _copy, accent=True).pack(side="left", padx=(0, 6))
        self._btn(b_bar, "Close", win.destroy).pack(side="right")

    def _export_batch_csv_dialog(self):
        items = self._get_selected_items()
        if not items:
            self._show_themed_warning("No Items Selected", "Please select at least one item using the [✓] checkboxes to export.", icon="⚠")
            return

        init_dir = get_artemis_base_dir()
        path = filedialog.asksaveasfilename(
            parent=self,
            initialdir=init_dir,
            title="Export Artemis Batch CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if path:
            self.engine.export_batch_csv(items, path)
            self._set_status(f"Exported {len(items)} items to {os.path.basename(path)}")
            self._show_themed_info("Export Successful", f"Exported {len(items)} items to:\n{path}", icon="📊")

    def _mark_selected_filed(self):
        items = self._get_selected_items()
        if not items:
            self._show_themed_warning("No Items Selected", "Please select items to mark as filed.", icon="⚠")
            return

        primary_platform = items[0].get("platform", "Platform")
        primary_brand = items[0].get("brand", "Brand")

        entry_id = self.data_store.log_submission(primary_platform, primary_brand, items, notice_reference="Manual Batch Filing")
        for it in items:
            self.data_store.update_queue_item_status(it["queue_id"], "Filed")

        self.selected_queue_ids.clear()
        self._refresh_queue_table()
        self._refresh_history_table()
        self._set_status(f"Logged submission {entry_id} for {len(items)} items.")
        self._show_themed_info("Submission Recorded", f"Marked {len(items)} items as Filed and recorded in Submission Audit Log (Ref: {entry_id}).", icon="✓")

    def _remove_selected_queue(self):
        items = self._get_selected_items()
        if not items:
            return
        if not self._show_themed_confirm("Confirm Removal", f"Remove {len(items)} selected items from the active queue?", icon="🗑"):
            return

        qids = [it["queue_id"] for it in items]
        removed = self.data_store.remove_queue_items(qids)
        self.selected_queue_ids.clear()
        self._refresh_queue_table()
        self._set_status(f"Removed {removed} items from queue.")

    def _refresh_all(self):
        self._check_pending_intake(silent=False)
        self._refresh_queue_table()
        self._refresh_history_table()
        self._refresh_rights_cards()
        self._set_status("Refreshed queue, intake, history, and brand rights.")


# ══════════════════════════════════════════════════════════════════════════════
#  BRAND RIGHTS & LOA MODAL (Full Add / Edit Dialog)
# ══════════════════════════════════════════════════════════════════════════════
class BrandRightsModal(tk.Toplevel):
    def __init__(self, parent: ArtemisApp, brand_name: Optional[str] = None, on_save=None):
        super().__init__(parent)
        self.artemis_app = parent
        self.data_store = parent.data_store
        self.theme = parent.theme
        self.editing_brand_name = brand_name
        self.on_save_callback = on_save

        is_edit = bool(brand_name)
        title_str = f"✏ Edit Brand Rights: {brand_name}" if is_edit else "➕ Add New Brand Rights & LOA"
        self.title(title_str)
        
        # Responsive sizing with resizability enabled
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(780, int(sw * 0.85))
        h = min(820, int(sh * 0.90))
        self.geometry(f"{w}x{h}")
        self.minsize(680, 620)
        self.resizable(True, True)

        self.configure(bg=self.theme["bg"])
        self.transient(parent)
        self.grab_set()

        parent._load_app_icon(self)
        parent._apply_dark_titlebar(self)
        parent._center_window(self, w, h)

        # Existing record values if editing
        rec = self.data_store.get_brand_rights(brand_name) if is_edit else {}
        self.initial_rec = rec or {}
        self.loa_file_path = rec.get("loa_path", "")

        self._build_modal_ui()

    def _build_modal_ui(self):
        t = self.theme

        # Top Header
        top_f = tk.Frame(self, bg=t["panel"], padx=18, pady=12, highlightbackground=t["border"], highlightthickness=1)
        top_f.pack(fill="x")

        tk.Label(top_f, text="⚖ BRAND RIGHTS & LEGAL AUTHORIZATION REGISTRY", font=FONT_HEAD, bg=t["panel"], fg=t.get("accent_gold", t["accent"])).pack(anchor="w")
        tk.Label(top_f, text="Complete corporate details, registration numbers, and LOA file required for verified portal submissions.", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w", pady=(2, 0))

        # Bottom Buttons Bar (packed first to bottom so it never gets clipped)
        btn_bar = tk.Frame(self, bg=t["panel"], padx=18, pady=10, highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(fill="x", side="bottom")

        self.artemis_app._btn(btn_bar, "Cancel", self.destroy).pack(side="right", padx=(6, 0))
        self.artemis_app._btn(btn_bar, "💾 Save Rights Profile", self._save_profile, accent=True, padx=16).pack(side="right")

        # Scrollable form container
        form_canvas = tk.Canvas(self, bg=t["bg"], highlightthickness=0)
        form_scroll = ttk.Scrollbar(self, orient="vertical", command=form_canvas.yview)
        form_frame = tk.Frame(form_canvas, bg=t["bg"], padx=18, pady=10)

        def _on_canvas_configure(e):
            form_canvas.itemconfig(win_id, width=e.width)

        win_id = form_canvas.create_window((0, 0), window=form_frame, anchor="nw")
        form_canvas.bind("<Configure>", _on_canvas_configure)
        form_frame.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.configure(yscrollcommand=form_scroll.set)

        form_canvas.pack(side="left", fill="both", expand=True)
        form_scroll.pack(side="right", fill="y")

        # Mousewheel
        def _on_mw(e):
            delta = int(-1 * (e.delta / 120)) if e.delta else 1
            form_canvas.yview_scroll(delta, "units")
        form_canvas.bind("<MouseWheel>", _on_mw)
        form_frame.bind("<MouseWheel>", _on_mw)

        # 1. Brand Identifier
        self.b_name_var = tk.StringVar(value=self.editing_brand_name or "")
        self._add_field(form_frame, "Brand Name / Trademark Reference *", self.b_name_var, "e.g. Toyota, Harley-Davidson, Chevrolet")

        # 2. Rights Holder Legal Entity
        self.holder_var = tk.StringVar(value=self.initial_rec.get("rights_holder", ""))
        self._add_field(form_frame, "Full Legal Ownership Name / Entity *", self.holder_var, "e.g. Toyota Motor Sales, U.S.A., Inc.")

        # 3. Corporate Address
        self.address_var = tk.StringVar(value=self.initial_rec.get("company_address", ""))
        self._add_field(form_frame, "Company Corporate Headquarters Address *", self.address_var, "e.g. 6565 Headquarters Dr, Plano, TX 75024, USA")

        # 4. Contact Phone & Email
        row_pe = tk.Frame(form_frame, bg=t["bg"])
        row_pe.pack(fill="x", pady=4)

        col_p = tk.Frame(row_pe, bg=t["bg"])
        col_p.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.phone_var = tk.StringVar(value=self.initial_rec.get("phone_number", ""))
        self._add_field(col_p, "Legal Phone Number *", self.phone_var, "e.g. +1-800-331-4331")

        col_e = tk.Frame(row_pe, bg=t["bg"])
        col_e.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.email_var = tk.StringVar(value=self.initial_rec.get("contact_email", ""))
        self._add_field(col_e, "Official Notice Email *", self.email_var, "e.g. ip.protection@toyota.com")

        # 5. Authorized Signatory / Agent
        self.agent_var = tk.StringVar(value=self.initial_rec.get("authorized_agent", ""))
        self._add_field(form_frame, "Authorized Signatory / Agent Representative *", self.agent_var, "e.g. Brand Protection & Legal Compliance Division")

        # 6. Trademark Numbers
        tm_initial = ", ".join(self.initial_rec.get("trademark_regs", []))
        self.tm_var = tk.StringVar(value=tm_initial)
        self._add_field(form_frame, "Registered Trademark Numbers (comma separated)", self.tm_var, "e.g. 1,234,567, 2,345,678, 3,456,789")

        # 7. Copyright Numbers
        cr_initial = ", ".join(self.initial_rec.get("copyright_regs", []))
        self.cr_var = tk.StringVar(value=cr_initial)
        self._add_field(form_frame, "Registered Copyright Numbers (optional)", self.cr_var, "e.g. VA 1-234-567, TX 9-876-543")

        # 8. Letter of Authorization (LOA) Attachment
        loa_box = tk.Frame(form_frame, bg=t["panel"], padx=14, pady=12, highlightbackground=t["border"], highlightthickness=1)
        loa_box.pack(fill="x", pady=10)

        tk.Label(loa_box, text="📎 LETTER OF AUTHORIZATION (LOA) ATTACHMENT", font=FONT_BOLD, bg=t["panel"], fg=t.get("accent_gold", t["accent"])).pack(anchor="w")
        tk.Label(loa_box, text="Attach authorization letters signed by the rights owner for automated marketplace upload.", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w", pady=(2, 6))

        # Full-width filename / path entry
        self.loa_disp_var = tk.StringVar(value=self.loa_file_path if self.loa_file_path else "No LOA document attached.")
        loa_entry = tk.Entry(loa_box, textvariable=self.loa_disp_var, state="readonly", font=FONT_SM, bg=t["entry_bg"], fg=t["text"], readonlybackground=t["entry_bg"], relief="flat", highlightbackground=t["border"], highlightthickness=1)
        loa_entry.pack(fill="x", pady=(0, 6), ipady=3)

        # Dedicated action buttons row directly underneath
        btn_loa_row = tk.Frame(loa_box, bg=t["panel"])
        btn_loa_row.pack(fill="x")
        self.artemis_app._btn(btn_loa_row, "📎 Browse & Attach LOA Document...", self._browse_loa_file, accent=True).pack(side="left", padx=(0, 6))
        self.artemis_app._btn(btn_loa_row, "👁 Open Attached Document", self._open_attached_loa).pack(side="left")

        # 9. Default Claim Type & Statement
        self.claim_var = tk.StringVar(value=self.initial_rec.get("default_claim", "Counterfeit Product / Unauthorized Trademark Reproduction"))
        self._add_field(form_frame, "Default Violation Claim", self.claim_var, "e.g. Counterfeit Product / Unauthorized Trademark Reproduction")

        tk.Label(form_frame, text="Legal Affirmation Statement", font=FONT_BOLD, bg=t["bg"], fg=t["text"]).pack(anchor="w", pady=(6, 2))
        self.stmt_txt = tk.Text(form_frame, height=4, font=FONT_NORM, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], relief="flat", highlightbackground=t["border"], highlightthickness=1)
        self.stmt_txt.pack(fill="x", pady=(0, 8))
        def_stmt = self.initial_rec.get("statement", "The seller is offering products bearing unauthorized reproductions of registered trademarks, likely to cause consumer confusion.")
        self.stmt_txt.insert("1.0", def_stmt)

    def _add_field(self, parent, label_text: str, var: tk.StringVar, placeholder: str = ""):
        t = self.theme
        f = tk.Frame(parent, bg=t["bg"])
        f.pack(fill="x", pady=4)
        tk.Label(f, text=label_text, font=FONT_BOLD, bg=t["bg"], fg=t["text"]).pack(anchor="w")
        ent = tk.Entry(f, textvariable=var, font=FONT_NORM, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], relief="flat", highlightbackground=t["border"], highlightthickness=1)
        ent.pack(fill="x", pady=(2, 0), ipady=3)
        return ent

    def _browse_loa_file(self):
        # Open in local user directory to prevent Windows shell freeze on disconnected network shares
        init_dir = get_artemis_base_dir()
        path = filedialog.askopenfilename(
            parent=self,
            initialdir=init_dir,
            title="Select Letter of Authorization (LOA) Document",
            filetypes=[("Legal & Image Documents", "*.pdf;*.png;*.jpg;*.jpeg;*.docx"), ("All Files", "*.*")]
        )
        if path:
            self.loa_file_path = path
            self.loa_disp_var.set(path)

    def _open_attached_loa(self):
        if self.loa_file_path and os.path.exists(self.loa_file_path):
            try:
                os.startfile(self.loa_file_path)
            except Exception as e:
                self.artemis_app._show_themed_error("Open Error", f"Could not open LOA:\n{e}", parent=self)
        else:
            self.artemis_app._show_themed_warning("No File", "No LOA document currently exists or is selected.", parent=self)

    def _save_profile(self):
        b_name = self.b_name_var.get().strip()
        holder = self.holder_var.get().strip()
        addr = self.address_var.get().strip()
        phone = self.phone_var.get().strip()
        email = self.email_var.get().strip()
        agent = self.agent_var.get().strip()

        if not b_name or not holder:
            self.artemis_app._show_themed_warning("Required Fields", "Please specify both the Brand Name and Full Legal Ownership Name.", parent=self)
            return

        tm_list = [x.strip() for x in self.tm_var.get().split(",") if x.strip()]
        cr_list = [x.strip() for x in self.cr_var.get().split(",") if x.strip()]
        claim = self.claim_var.get().strip()
        statement = self.stmt_txt.get("1.0", "end-1c").strip()

        # Handle LOA copying if path was changed to an external file
        final_loa_path = self.loa_file_path
        if self.loa_file_path and os.path.exists(self.loa_file_path):
            loa_dir = os.path.join(get_artemis_base_dir(), "loa_documents")
            if not self.loa_file_path.startswith(loa_dir):
                try:
                    final_loa_path = self.data_store.store_loa_document(b_name, self.loa_file_path)
                except Exception:
                    final_loa_path = self.loa_file_path

        payload = {
            "rights_holder": holder,
            "company_address": addr,
            "phone_number": phone,
            "contact_email": email,
            "authorized_agent": agent,
            "trademark_regs": tm_list,
            "copyright_regs": cr_list,
            "loa_path": final_loa_path,
            "default_claim": claim,
            "statement": statement
        }

        self.data_store.set_brand_rights(b_name, payload)

        if self.on_save_callback:
            self.on_save_callback()

        self.artemis_app._set_status(f"Saved brand rights profile for '{b_name}'.")
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  ARTEMIS FIELD GUIDE MODAL
# ══════════════════════════════════════════════════════════════════════════════
class ArtemisFieldGuideModal(tk.Toplevel):
    def __init__(self, parent: ArtemisApp):
        super().__init__(parent)
        self.artemis_app = parent
        self.theme = parent.theme

        self.title("📚 Artemis Rights Engine — Analyst Field Guide")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(920, int(sw * 0.88))
        h = min(740, int(sh * 0.88))
        self.geometry(f"{w}x{h}")
        self.minsize(780, 580)
        self.resizable(True, True)
        self.configure(bg=self.theme["bg"])
        self.transient(parent)
        self.grab_set()

        parent._load_app_icon(self)
        parent._apply_dark_titlebar(self)
        parent._center_window(self, w, h)

        self._build_ui()

    def _build_ui(self):
        t = self.theme

        # Top Header Banner
        hdr_f = tk.Frame(self, bg=t["panel"], padx=18, pady=12, highlightbackground=t["border"], highlightthickness=1)
        hdr_f.pack(fill="x")

        tk.Label(hdr_f, text="📚 ARTEMIS RIGHTS ENGINE — ANALYST FIELD GUIDE", font=FONT_HEAD, bg=t["panel"], fg=t.get("accent_gold", t["accent"])).pack(anchor="w")
        tk.Label(hdr_f, text="Standard Operating Procedures for Autonomous Platform Enforcement, LOA Registries & Legal Notice Generation.", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w", pady=(2, 0))

        # Bottom Close Button Bar
        b_bar = tk.Frame(self, bg=t["panel"], padx=18, pady=8, highlightbackground=t["border"], highlightthickness=1)
        b_bar.pack(fill="x", side="bottom")

        self.artemis_app._btn(b_bar, "Close Field Guide", self.destroy, accent=True, padx=18, pady=6).pack(side="right")

        # Notebook for Guide Tabs
        style = ttk.Style(self)
        style.configure("Guide.TNotebook", background=t["bg"], borderwidth=0)
        style.configure("Guide.TNotebook.Tab", background=t["panel"], foreground=t["text"], padding=[14, 6], font=FONT_BOLD)
        style.map("Guide.TNotebook.Tab",
                  background=[("selected", t["accent"]), ("active", t["border"])],
                  foreground=[("selected", t.get("btn_accent_fg", "#070D0A")), ("active", t["text"])])

        nb = ttk.Notebook(self, style="Guide.TNotebook")
        nb.pack(fill="both", expand=True, padx=12, pady=(8, 6))

        # Tab 1: Architecture & Lore
        tab_arch = tk.Frame(nb, bg=t["bg"])
        nb.add(tab_arch, text="🏹 Architecture & Lore")
        self._build_tab_content(tab_arch, [
            ("The Apollo & Artemis Initiative",
             "In classical mythology, Apollo and Artemis are divine twins born together on Delos.\n\n"
             "• Apollo brings illumination and prophecy — revealing what lurks in the shadows.\n"
             "• Artemis wields the golden bow — striking confirmed targets with unerring, sovereign precision.\n\n"
             "In brand protection, modern analysts faced a fundamental bottleneck: reconnaissance tools try to do too much, "
             "while form-filling scripts lack forensic context. The Apollo & Artemis Initiative solves this with a twin-engine separation of concerns:\n\n"
             "1. Apollo Brand Intelligence (The Eyes):\n"
             "   Dedicated to multi-sector surveillance, parallel scraping across 19+ marketplaces, visual fingerprinting (pHash), "
             "   cross-border syndicate correlation, and human-in-the-loop reconnaissance triage.\n\n"
             "2. Artemis Rights Engine (The Hands):\n"
             "   Dedicated to autonomous platform enforcement, authenticated portal automation, client Letter of Authorization (LOA) registries, "
             "   and formal legal notice generation."),

            ("The Decoupled Bridge Protocol",
             "Apollo and Artemis are completely independent applications. Artemis maintains zero dependencies on Apollo's scraping code, "
             "and Apollo embeds zero heavy browser automation loops for rights filing.\n\n"
             "Communication occurs strictly via the atomic file bridge in '%LOCALAPPDATA%/Artemis_Rights_Engine/intake_queue/'.\n"
             "• Analysts can right-click any verified listing in Apollo and dispatch it to Artemis in one click.\n"
             "• Artemis ingests batches atomically without risking data corruption or memory leaks.\n"
             "• Artemis can be run completely standalone by enforcement specialists who never open Apollo.")
        ])

        # Tab 2: Queue & Triage Workflow
        tab_queue = tk.Frame(nb, bg=t["bg"])
        nb.add(tab_queue, text="🎯 Queue & Triage Workflow")
        self._build_tab_content(tab_queue, [
            ("The Enforcement Pipeline",
             "1. Ingestion: Click '📥 Ingest Apollo Batches' in the top bar to pull newly dispatched listings into the Active Enforcement Queue.\n\n"
             "2. Deduplication: Artemis automatically checks incoming items against existing queue entries using (Platform, Item ID) signatures, "
             "preventing duplicate enforcement actions.\n\n"
             "3. Multi-Platform Triage: Use the 'Filter Platform' dropdown to isolate specific platforms (Amazon, Walmart, eBay, Redbubble, Printerval) "
             "or filter by protected client Brand.\n\n"
             "4. Selection & Execution: Check individual rows or use 'Select All' to batch-select items for enforcement action."),

            ("Table Controls & Context Menu",
             "• Right-Click Context Menu: Right-click any listing in the table to:\n"
             "  - 🌐 Open URL in Browser (or double-click the row)\n"
             "  - 📋 Copy Listing URL to clipboard\n"
             "  - 📋 Copy Item ID to clipboard\n"
             "  - 🚀 Engage Portal Automation for selected rows\n"
             "  - 📄 Draft Formal Infringement Notice for selected rows\n"
             "  - ✓ Mark Selected as Filed (moves to Submission History audit log)\n\n"
             "• Export Batch CSV: Exports selected items into a formatted CSV ready for bulk upload to marketplace brand portals.")
        ])

        # Tab 3: Brand Rights & LOA Registry
        tab_rights = tk.Frame(nb, bg=t["bg"])
        nb.add(tab_rights, text="📜 Brand Rights & LOA Registry")
        self._build_tab_content(tab_rights, [
            ("Why Informal Reports Fail",
             "Modern e-commerce platforms (Amazon Brand Registry, Walmart Brand Portal, eBay VeRO) enforce strict legal verification standards. "
             "Reports submitted without complete corporate records, active trademark registration numbers, or authorized signatory credentials "
             "are routinely rejected as non-actionable.\n\n"
             "Artemis maintains a persistent, sovereign Brand Rights Registry that guarantees every notice and automated submission carries "
             "unquestionable legal standing."),

            ("The Artemis 8-Point Corporate Schema",
             "Every registered brand profile in Artemis includes:\n"
             "1. Brand / Trademark Reference: The commercial name (e.g. Toyota, Harley-Davidson, Chevrolet).\n"
             "2. Rights Holder Legal Entity: The formal legal corporate ownership name (e.g. Toyota Motor Sales, U.S.A., Inc.).\n"
             "3. Corporate Headquarters Address: Physical corporate legal address required by marketplace intake forms.\n"
             "4. Contact Phone & Official Notice Email: Verified corporate legal compliance channels.\n"
             "5. Authorized Signatory / Agent Representative: The named legal representative declaring authority under penalty of perjury.\n"
             "6. Registered Trademark Numbers: USPTO or WIPO registration numbers proving ownership.\n"
             "7. Registered Copyright Numbers: Copyright Office registrations for catalog artwork, product photography, or logos.\n"
             "8. Letter of Authorization (LOA) Document: Signed authorization file attached directly to the profile."),

            ("Letter of Authorization (LOA) Management",
             "• When you click '📎 Browse LOA...' in the Brand Rights modal, Artemis safely copies the document into its permanent vault:\n"
             "  '%LOCALAPPDATA%/Artemis_Rights_Engine/loa_documents/'.\n"
             "• Supported formats: PDF documents (.pdf) and high-resolution scanned agreements (.png, .jpg, .docx).\n"
             "• Click '👁 Open' at any time to inspect the active authorization document.")
        ])

        # Tab 4: Portals & Legal Notice Engine
        tab_portals = tk.Frame(nb, bg=t["bg"])
        nb.add(tab_portals, text="🔐 Portals & Notice Engine")
        self._build_tab_content(tab_portals, [
            ("Supported Enforcement Portals",
             "• Amazon Brand Registry: Report a Violation tool for counterfeit goods, trademark abuse, and patent infringement using ASINs.\n"
             "• Walmart Brand Portal: Intellectual Property Triage portal for Item IDs and product URLs.\n"
             "• eBay VeRO Portal: Verified Rights Owner notice filing for listing IDs.\n"
             "• Print-on-Demand (POD) Portals: Redbubble and Printerval intellectual property notice centers.\n\n"
             "Click '🚀 Open Portal in Browser' from the Platform Portals tab to authenticate once and manage active takedown accounts."),

            ("The Dynamic Legal Notice Generator",
             "When filing manual notices or communicating directly with marketplace legal teams, click '📄 Draft Formal Notice'.\n\n"
             "Artemis dynamically compiles a court-grade legal notification containing:\n"
             "• Complete legal entity identification, corporate address, phone, and notice email.\n"
             "• Formal declaration under penalty of perjury.\n"
             "• Comprehensive catalog of infringing URLs, item IDs, merchant handles, and prices.\n"
             "• Good faith certification and authorized agent signature block.\n"
             "• Reference to on-file Letter of Authorization (LOA).\n\n"
             "Click '📋 Copy Notice Text' to copy the formatted text directly to your clipboard for instant dispatch.")
        ])

    def _build_tab_content(self, parent, sections):
        t = self.theme
        canvas = tk.Canvas(parent, bg=t["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=t["bg"], padx=16, pady=12)

        def _on_cfg(e):
            canvas.itemconfig(win_id, width=e.width)

        win_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.bind("<Configure>", _on_cfg)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mw(e):
            delta = int(-1 * (e.delta / 120)) if e.delta else 1
            canvas.yview_scroll(delta, "units")
        canvas.bind("<MouseWheel>", _on_mw)
        scroll_frame.bind("<MouseWheel>", _on_mw)

        for sec_title, sec_body in sections:
            card = tk.Frame(scroll_frame, bg=t["panel"], padx=14, pady=10, highlightbackground=t["border"], highlightthickness=1)
            card.pack(fill="x", pady=6)

            tk.Label(card, text=sec_title, font=FONT_HEAD, bg=t["panel"], fg=t.get("accent_gold", t["accent"])).pack(anchor="w")
            tk.Frame(card, bg=t["border"], height=1).pack(fill="x", pady=(4, 8))
            tk.Label(card, text=sec_body, font=FONT_NORM, bg=t["panel"], fg=t["text"], justify="left", wraplength=800).pack(anchor="w")


def main():
    # Inspect CLI arguments for --theme
    theme_arg = None
    for idx, arg in enumerate(sys.argv):
        if arg == "--theme" and idx + 1 < len(sys.argv):
            theme_arg = sys.argv[idx + 1]
            break

    app = ArtemisApp(initial_theme_key=theme_arg)
    app.mainloop()


if __name__ == "__main__":
    main()
