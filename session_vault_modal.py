"""
Universal Marketplace Session & Account Vault Modal for Apollo Brand Intelligence Suite.
Presents a centralized management console to monitor and refresh authentication
and anti-bot session state across all gated marketplaces.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from session_vault import SessionVault, VAULT_PLATFORMS

FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_SM   = ("Segoe UI", 8)
FONT_HEAD = ("Segoe UI", 11, "bold")
FONT_TITLE= ("Segoe UI", 12, "bold")


class SessionVaultModal(tk.Toplevel):
    """Modern modal dialog displaying live status and one-click connection for all marketplaces."""

    def __init__(self, parent, theme: dict, session_vault: SessionVault):
        super().__init__(parent)
        self.parent = parent
        self.theme = theme
        self.vault = session_vault

        self.title("🔐 Universal Marketplace Session & Account Vault")
        self.geometry("920x640")
        self.minsize(840, 520)
        self.configure(bg=self.theme["bg"])
        self.transient(parent)
        self.grab_set()

        if hasattr(parent, "_apply_dark_titlebar"):
            parent._apply_dark_titlebar(self)
        if hasattr(parent, "_load_app_icon"):
            parent._load_app_icon(self)
        if hasattr(parent, "_center_window"):
            parent._center_window(self, 920, 640)

        self.card_widgets = {}
        self._build_ui()
        self._refresh_all_statuses()

    def _build_ui(self):
        t = self.theme

        # ── Top Header Banner ──
        head_frame = tk.Frame(
            self,
            bg=t["panel"],
            padx=20,
            pady=14,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        head_frame.pack(fill="x", padx=16, pady=(14, 8))

        tk.Label(
            head_frame,
            text="🔐 Marketplace Session & Account Vault",
            font=FONT_TITLE,
            bg=t["panel"],
            fg=t["accent"]
        ).pack(anchor="w")

        tk.Label(
            head_frame,
            text="Manage persistent authentication cookies & Cloudflare/DataDome bypass sessions for automated background harvesting.",
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["subtext"]
        ).pack(anchor="w", pady=(3, 0))

        # ── Scrollable Platform List Container ──
        body_container = tk.Frame(self, bg=t["bg"])
        body_container.pack(fill="both", expand=True, padx=16, pady=4)

        canvas = tk.Canvas(body_container, bg=t["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_container, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=t["bg"])

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_win = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set, yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            # Reserve space for scrollbar + padding to strictly prevent horizontal clipping
            inner_w = max(event.width - 6, 760)
            canvas.itemconfig(canvas_win, width=inner_w)

        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(4, 0))

        # ── Mousewheel Scrolling Support ──
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", _on_mousewheel, add="+")
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)

        canvas.bind("<MouseWheel>", _on_mousewheel)
        self.scroll_frame.bind("<MouseWheel>", _on_mousewheel)
        self.bind("<MouseWheel>", _on_mousewheel)

        # ── Populate Platform Cards ──
        for p_key, p_cfg in VAULT_PLATFORMS.items():
            self._create_platform_card(self.scroll_frame, p_key, p_cfg)

        _bind_mousewheel_recursive(self.scroll_frame)

        # ── Bottom Control Row ──
        bot_row = tk.Frame(self, bg=t["bg"], padx=16, pady=12)
        bot_row.pack(fill="x", side="bottom")

        tk.Label(
            bot_row,
            text="💡 Clicking 'Connect / Refresh' opens Microsoft Edge in stealth mode to solve verifications or log in once.",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["subtext"]
        ).pack(side="left")

        btn_close = tk.Button(
            bot_row,
            text="✕ Close",
            font=FONT_BOLD,
            bg=t["accent"],
            fg="black" if str(t.get("name", "")).startswith("⚡") else "white",
            relief="flat",
            padx=16,
            pady=6,
            command=self.destroy,
            cursor="hand2"
        )
        btn_close.pack(side="right", padx=(8, 0))

        btn_refresh = tk.Button(
            bot_row,
            text="🔄 Refresh All",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            relief="flat",
            padx=14,
            pady=6,
            command=self._refresh_all_statuses,
            cursor="hand2"
        )
        btn_refresh.pack(side="right")

    def _create_platform_card(self, parent, p_key: str, p_cfg: dict):
        t = self.theme
        card = tk.Frame(
            parent,
            bg=t["panel"],
            padx=16,
            pady=12,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        card.pack(fill="x", pady=5, padx=2)

        # 1. Right Column Packed FIRST to guarantee zero right-edge clipping
        right_box = tk.Frame(card, bg=t["panel"])
        right_box.pack(side="right", padx=(14, 4), anchor="center")

        btn_connect = tk.Button(
            right_box,
            text=f"Connect {p_cfg['name']}",
            font=FONT_BOLD,
            bg=t["btn_normal_bg"],
            fg=t["btn_normal_fg"],
            relief="flat",
            width=20,
            pady=6,
            command=lambda k=p_key: self._on_connect_clicked(k),
            cursor="hand2"
        )
        btn_connect.pack()

        # 2. Left Column: Details & Live Indicators
        left_box = tk.Frame(card, bg=t["panel"])
        left_box.pack(side="left", fill="both", expand=True, padx=(2, 10))

        title_row = tk.Frame(left_box, bg=t["panel"])
        title_row.pack(fill="x")

        tk.Label(
            title_row,
            text=f"{p_cfg['icon']}  {p_cfg['name']}",
            font=FONT_HEAD,
            bg=t["panel"],
            fg=t["text"]
        ).pack(side="left")

        status_lbl = tk.Label(
            title_row,
            text="Checking...",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["subtext"]
        )
        status_lbl.pack(side="left", padx=14)

        desc_lbl = tk.Label(
            left_box,
            text=f"Security: {p_cfg['auth_type']}  •  {p_cfg['help']}",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"]
        )
        desc_lbl.pack(anchor="w", pady=(4, 0))

        meta_lbl = tk.Label(
            left_box,
            text="",
            font=FONT_SM,
            bg=t["panel"],
            fg=t.get("accent2", t["accent"])
        )
        meta_lbl.pack(anchor="w", pady=(2, 0))

        self.card_widgets[p_key] = {
            "status_lbl": status_lbl,
            "meta_lbl": meta_lbl,
            "btn_connect": btn_connect
        }

    def _refresh_all_statuses(self):
        statuses = self.vault.get_all_statuses()
        for p_key, st in statuses.items():
            if p_key in self.card_widgets:
                w = self.card_widgets[p_key]
                if st["connected"]:
                    w["status_lbl"].config(text=st["summary"], fg=self.theme["success"])
                    w["btn_connect"].config(
                        text=f"🔄 Refresh {st['platform_name']}",
                        bg=self.theme["panel"],
                        fg=self.theme["text"]
                    )
                else:
                    w["status_lbl"].config(text=st["summary"], fg=self.theme.get("danger", "#ff5555"))
                    w["btn_connect"].config(
                        text=f"🔑 Connect {st['platform_name']}",
                        bg=self.theme["accent"],
                        fg="black" if str(self.theme.get("name", "")).startswith("⚡") else "white"
                    )

                mod_text = ""
                if st.get("last_modified"):
                    dt = datetime.datetime.fromtimestamp(st["last_modified"])
                    mod_text = f"Last Activity: {dt.strftime('%Y-%m-%d %H:%M')}"
                if st.get("cookie_count", 0) > 0:
                    mod_text += f"  •  ({st['cookie_count']} active session cookies stored)"
                w["meta_lbl"].config(text=mod_text)

    def _on_connect_clicked(self, p_key: str):
        cfg = VAULT_PLATFORMS.get(p_key, {})
        w = self.card_widgets.get(p_key)
        if w:
            w["status_lbl"].config(text="🟡 Browser Session Active...", fg=self.theme["warning"])
            w["btn_connect"].config(state="disabled")

        def _on_done(k):
            self.after(500, lambda: self._on_connect_finished(k))

        self.vault.launch_connect_browser(p_key, on_complete=_on_done)

    def _on_connect_finished(self, p_key: str):
        if p_key in self.card_widgets:
            self.card_widgets[p_key]["btn_connect"].config(state="normal")
        self._refresh_all_statuses()
        cfg = VAULT_PLATFORMS.get(p_key, {})
        messagebox.showinfo(
            "Session Vault Updated",
            f"Active persistent session and cookies captured for {cfg.get('name', p_key)}!\n\nBackground automated searches will now use this authentication profile.",
            parent=self
        )