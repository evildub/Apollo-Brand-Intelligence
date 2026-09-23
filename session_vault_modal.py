"""
Universal Marketplace Session & Account Vault Modal for Apollo Brand Intelligence Suite.
Presents a centralized management console to monitor and refresh authentication
and anti-bot session state across all gated marketplaces.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import threading
from session_vault import SessionVault, VAULT_PLATFORMS

FONT_BOLD  = ("Segoe UI", 9, "bold")
FONT_NORM  = ("Segoe UI", 9)
FONT_SM    = ("Segoe UI", 8)
FONT_HEAD  = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")


class SessionVaultModal(tk.Toplevel):
    """Modern 2-tab modal dialog displaying live session status, stored logins, and API configurations."""

    def __init__(self, parent, theme: dict, session_vault: SessionVault):
        super().__init__(parent)
        self.parent = parent
        self.theme = theme
        self.vault = session_vault

        self.title("🔐 Marketplace Session Vault & Enterprise API Console")
        self.geometry("980x720")
        self.minsize(880, 560)
        self.configure(bg=self.theme["bg"])
        self.transient(parent)
        self.grab_set()

        if hasattr(parent, "_apply_dark_titlebar"):
            parent._apply_dark_titlebar(self)
        if hasattr(parent, "_load_app_icon"):
            parent._load_app_icon(self)
        if hasattr(parent, "_center_window"):
            parent._center_window(self, 980, 720)

        self.card_widgets = {}
        self._build_ui()
        self._refresh_all_statuses()
        self._load_api_keys()

    def _t(self, key, fallback="#1e1e1e"):
        return self.theme.get(key, fallback)

    def _build_ui(self):
        t = self.theme

        # ── Tabbed Notebook Setup ──
        style = ttk.Style()
        style.configure(
            "Vault.TNotebook",
            background=t["bg"],
            borderwidth=0
        )
        style.configure(
            "Vault.TNotebook.Tab",
            background=t["panel"],
            foreground=t["text"],
            padding=[18, 9],
            font=FONT_BOLD
        )
        style.map(
            "Vault.TNotebook.Tab",
            background=[("selected", t["accent"]), ("active", t.get("border", "#333333"))],
            foreground=[("selected", "black" if str(t.get("name", "")).startswith("⚡") else "white"),
                        ("active", t["text"])]
        )

        self.notebook = ttk.Notebook(self, style="Vault.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(12, 4))

        # Tab 1: Marketplace Sessions & Logins
        self.tab_sessions = tk.Frame(self.notebook, bg=t["bg"])
        self.notebook.add(self.tab_sessions, text="🔐 Marketplace Browser Sessions & Stored Logins")
        self._build_sessions_tab(self.tab_sessions)

        # Tab 2: Enterprise & Platform API Keys
        self.tab_api = tk.Frame(self.notebook, bg=t["bg"])
        self.notebook.add(self.tab_api, text="🔑 Enterprise & Platform API Keys")
        self._build_api_tab(self.tab_api)

        def _on_tab_changed(event):
            try:
                cur_tab = self.notebook.index(self.notebook.select())
                if cur_tab == 1 and hasattr(self, "api_canvas"):
                    self.api_canvas.update_idletasks()
                    self.api_canvas.configure(scrollregion=self.api_canvas.bbox("all"))
                elif cur_tab == 0 and hasattr(self, "sessions_canvas"):
                    self.sessions_canvas.update_idletasks()
                    self.sessions_canvas.configure(scrollregion=self.sessions_canvas.bbox("all"))
            except Exception:
                pass

        self.notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)

        def _on_global_mousewheel(event):
            try:
                cur_tab = self.notebook.index(self.notebook.select())
                target_canvas = self.sessions_canvas if cur_tab == 0 else getattr(self, "api_canvas", None)
                if target_canvas:
                    target_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        self.bind("<MouseWheel>", _on_global_mousewheel)

        # ── Bottom Common Control Row ──
        bot_row = tk.Frame(self, bg=t["bg"], padx=16, pady=10)
        bot_row.pack(fill="x", side="bottom")

        tk.Label(
            bot_row,
            text="💡 All session cookies, credentials, and API tokens are encrypted and stored locally in your Apollo profile directory.",
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
            padx=18,
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

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1: Marketplace Browser Sessions & Stored Logins
    # ──────────────────────────────────────────────────────────────────────────
    def _build_sessions_tab(self, parent):
        t = self.theme

        # Sub-header banner
        subhead = tk.Frame(
            parent,
            bg=t["panel"],
            padx=16,
            pady=10,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        subhead.pack(fill="x", padx=4, pady=(6, 8))

        tk.Label(
            subhead,
            text="🔐 Persistent Marketplace Authentication & Stored Logins",
            font=FONT_HEAD,
            bg=t["panel"],
            fg=t["accent"]
        ).pack(anchor="w")

        tk.Label(
            subhead,
            text="Bypass Cloudflare Turnstile, DataDome, and bot challenges. Store login credentials to automatically authenticate on storefronts.",
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["subtext"]
        ).pack(anchor="w", pady=(2, 0))

        # Scrollable container
        body_container = tk.Frame(parent, bg=t["bg"])
        body_container.pack(fill="both", expand=True, padx=4, pady=2)

        canvas = tk.Canvas(body_container, bg=t["bg"], highlightthickness=0)
        self.sessions_canvas = canvas
        scrollbar = ttk.Scrollbar(body_container, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=t["bg"])

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_win = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set, yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            inner_w = max(event.width - 10, 780)
            canvas.itemconfig(canvas_win, width=inner_w)

        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(4, 0))

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

        # Build cards for each platform
        for p_key, p_cfg in VAULT_PLATFORMS.items():
            self._create_platform_card(self.scroll_frame, p_key, p_cfg)

        _bind_mousewheel_recursive(self.scroll_frame)

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

        # ── Top Row: Header & Connect Button ──
        top_row = tk.Frame(card, bg=t["panel"])
        top_row.pack(fill="x")

        # Right-aligned Connect Button
        btn_connect = tk.Button(
            top_row,
            text="🔑 Connect Profile",
            font=FONT_BOLD,
            bg=t["accent"],
            fg="black" if str(t.get("name", "")).startswith("⚡") else "white",
            relief="flat",
            padx=16,
            pady=5,
            command=lambda k=p_key: self._on_connect_clicked(k),
            cursor="hand2"
        )
        btn_connect.pack(side="right", padx=(10, 0))

        # Left-aligned Icon, Name, and Status Label
        title_box = tk.Frame(top_row, bg=t["panel"])
        title_box.pack(side="left", fill="x", expand=True)

        tk.Label(
            title_box,
            text=f"{p_cfg['icon']}  {p_cfg['name']}",
            font=FONT_HEAD,
            bg=t["panel"],
            fg=t["text"]
        ).pack(side="left")

        status_lbl = tk.Label(
            title_box,
            text="Checking...",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["subtext"]
        )
        status_lbl.pack(side="left", padx=14)

        # ── Middle Row: Security Type & Last Activity ──
        mid_row = tk.Frame(card, bg=t["panel"])
        mid_row.pack(fill="x", pady=(4, 6))

        desc_lbl = tk.Label(
            mid_row,
            text=f"Security: {p_cfg['auth_type']}  •  {p_cfg['help']}",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"]
        )
        desc_lbl.pack(anchor="w")

        meta_lbl = tk.Label(
            mid_row,
            text="",
            font=FONT_SM,
            bg=t["panel"],
            fg=t.get("accent2", t["accent"])
        )
        meta_lbl.pack(anchor="w", pady=(1, 0))

        # ── Bottom Row: Stored Login Credentials Row ──
        cred_frame = tk.Frame(
            card,
            bg=t["bg"],
            padx=10,
            pady=6,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        cred_frame.pack(fill="x", pady=(4, 0))

        tk.Label(
            cred_frame,
            text="👤 Stored Login:",
            font=FONT_BOLD,
            bg=t["bg"],
            fg=t["text"]
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            cred_frame,
            text="Email/User:",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["subtext"]
        ).pack(side="left", padx=(0, 4))

        ent_user = tk.Entry(
            cred_frame,
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["text"],
            insertbackground=t["text"],
            relief="flat",
            width=22
        )
        ent_user.pack(side="left", padx=(0, 10))

        tk.Label(
            cred_frame,
            text="Password:",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["subtext"]
        ).pack(side="left", padx=(0, 4))

        ent_pwd = tk.Entry(
            cred_frame,
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["text"],
            insertbackground=t["text"],
            show="*",
            relief="flat",
            width=16
        )
        ent_pwd.pack(side="left", padx=(0, 4))

        # Show/Hide Toggle Button
        btn_eye = tk.Button(
            cred_frame,
            text="👁",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["text"],
            relief="flat",
            width=3,
            pady=1,
            command=lambda e=ent_pwd: self._toggle_pwd_visibility(e),
            cursor="hand2"
        )
        btn_eye.pack(side="left", padx=(0, 10))

        # Save Login Button
        save_status_lbl = tk.Label(
            cred_frame,
            text="",
            font=FONT_SM,
            bg=t["bg"],
            fg=t.get("success", "#10b981")
        )

        btn_save_cred = tk.Button(
            cred_frame,
            text="💾 Save Login",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["text"],
            relief="flat",
            padx=8,
            pady=1,
            command=lambda k=p_key, u=ent_user, p=ent_pwd, s=save_status_lbl: self._save_platform_cred(k, u, p, s),
            cursor="hand2"
        )
        btn_save_cred.pack(side="left", padx=(0, 8))
        save_status_lbl.pack(side="left")

        # Pre-fill stored credentials if existing
        stored_c = self.vault.get_credential(p_key)
        if stored_c.get("username"):
            ent_user.insert(0, stored_c["username"])
        if stored_c.get("password"):
            ent_pwd.insert(0, stored_c["password"])
            save_status_lbl.config(text="✓ Saved", fg=t.get("success", "#10b981"))

        self.card_widgets[p_key] = {
            "status_lbl": status_lbl,
            "meta_lbl": meta_lbl,
            "btn_connect": btn_connect,
            "ent_user": ent_user,
            "ent_pwd": ent_pwd,
            "save_status_lbl": save_status_lbl
        }

    def _toggle_pwd_visibility(self, entry_widget):
        if entry_widget.cget("show") == "*":
            entry_widget.config(show="")
        else:
            entry_widget.config(show="*")

    def _save_platform_cred(self, p_key: str, ent_user: tk.Entry, ent_pwd: tk.Entry, status_lbl: tk.Label):
        u = ent_user.get().strip()
        p = ent_pwd.get().strip()
        ok = self.vault.save_credential(p_key, u, p)
        t = self.theme
        if ok:
            if u or p:
                status_lbl.config(text="✓ Credentials Saved", fg=t.get("success", "#10b981"))
            else:
                status_lbl.config(text="✓ Cleared", fg=t["subtext"])
            self.after(2500, lambda: status_lbl.config(text="✓ Saved" if (u or p) else ""))
        else:
            status_lbl.config(text="❌ Save Failed", fg=t.get("danger", "#ef4444"))

    def _refresh_all_statuses(self):
        statuses = self.vault.get_all_statuses()
        t = self.theme
        for p_key, st in statuses.items():
            if p_key in self.card_widgets:
                w = self.card_widgets[p_key]
                if self.vault.is_session_active(p_key):
                    w["status_lbl"].config(text="🟡 Browser Session Active...", fg=t.get("warning", "#f59e0b"))
                    w["btn_connect"].config(
                        text="💾 Save & Finish",
                        bg=t.get("warning", "#f59e0b"),
                        fg="black",
                        relief="flat",
                        bd=0,
                        highlightthickness=0,
                        state="normal",
                        command=lambda k=p_key: self._on_finish_session_clicked(k)
                    )
                elif st["connected"]:
                    w["status_lbl"].config(text=st["summary"], fg=t["success"])
                    w["btn_connect"].config(
                        text="🔄 Refresh Session",
                        bg=t.get("entry_bg", "#2a2a2a"),
                        fg=t.get("text", "#ffffff"),
                        relief="solid",
                        bd=1,
                        state="normal",
                        command=lambda k=p_key: self._on_connect_clicked(k)
                    )
                else:
                    w["status_lbl"].config(text=st["summary"], fg=t.get("danger", "#ff5555"))
                    w["btn_connect"].config(
                        text="🔑 Connect Profile",
                        bg=t["accent"],
                        fg="black" if str(t.get("name", "")).startswith("⚡") else "white",
                        relief="flat",
                        bd=0,
                        state="normal",
                        command=lambda k=p_key: self._on_connect_clicked(k)
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
            w["status_lbl"].config(text="🟡 Launching Edge...", fg=self.theme.get("warning", "#f59e0b"))
            w["btn_connect"].config(
                text="💾 Save & Finish",
                bg=self.theme.get("warning", "#f59e0b"),
                fg="black",
                relief="flat",
                bd=0,
                state="normal",
                command=lambda k=p_key: self._on_finish_session_clicked(k)
            )

        def _on_done(k):
            self.after(0, lambda: self._on_connect_finished(k))

        self.vault.launch_connect_browser(p_key, on_complete=_on_done)
        self._schedule_active_session_poll()

    def _on_finish_session_clicked(self, p_key: str):
        w = self.card_widgets.get(p_key)
        if w:
            w["btn_connect"].config(text="Saving...", state="disabled")
            w["status_lbl"].config(text="🟡 Saving Session & Cookies...", fg=self.theme.get("warning", "#f59e0b"))
        self.vault.close_session(p_key)

    def _schedule_active_session_poll(self):
        any_active = any(self.vault.is_session_active(k) for k in VAULT_PLATFORMS)
        self._refresh_all_statuses()
        if any_active:
            self.after(1200, self._schedule_active_session_poll)

    def _on_connect_finished(self, p_key: str):
        self._refresh_all_statuses()

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2: Enterprise & Platform API Keys
    # ──────────────────────────────────────────────────────────────────────────
    def _build_api_tab(self, parent):
        t = self.theme

        # Sub-header banner
        subhead = tk.Frame(
            parent,
            bg=t["panel"],
            padx=16,
            pady=10,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        subhead.pack(fill="x", padx=4, pady=(6, 8))

        tk.Label(
            subhead,
            text="🔑 Enterprise API Gateways & Direct Developer Keys",
            font=FONT_HEAD,
            bg=t["panel"],
            fg=t["accent"]
        ).pack(anchor="w")

        tk.Label(
            subhead,
            text="Configure automated enterprise case ingestion endpoints and direct platform developer REST APIs.",
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["subtext"]
        ).pack(anchor="w", pady=(2, 0))

        # Scrollable container for API sections
        body_container = tk.Frame(parent, bg=t["bg"])
        body_container.pack(fill="both", expand=True, padx=4, pady=2)

        canvas = tk.Canvas(body_container, bg=t["bg"], highlightthickness=0)
        self.api_canvas = canvas
        scrollbar = ttk.Scrollbar(body_container, orient="vertical", command=canvas.yview)
        api_scroll = tk.Frame(canvas, bg=t["bg"])

        api_scroll.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        c_win = canvas.create_window((0, 0), window=api_scroll, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set, yscrollcommand=scrollbar.set)

        def _on_api_canvas_configure(event):
            inner_w = max(event.width - 10, 780)
            canvas.itemconfig(c_win, width=inner_w)

        canvas.bind("<Configure>", _on_api_canvas_configure)
        scrollbar.pack(side="right", fill="y", padx=(4, 0))
        canvas.pack(side="left", fill="both", expand=True)

        def _on_api_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _bind_api_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", _on_api_mousewheel, add="+")
            for child in widget.winfo_children():
                _bind_api_mousewheel_recursive(child)

        canvas.bind("<MouseWheel>", _on_api_mousewheel)
        api_scroll.bind("<MouseWheel>", _on_api_mousewheel)

        # ── Card 1: Enterprise Enforcement API Gateway ──
        ent_card = tk.Frame(
            api_scroll,
            bg=t["panel"],
            padx=20,
            pady=16,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        ent_card.pack(fill="x", pady=6, padx=2)

        tk.Label(
            ent_card,
            text="🏢 Enterprise Enforcement API (Direct Intake Gateway)",
            font=FONT_HEAD,
            bg=t["panel"],
            fg=t["text"]
        ).pack(anchor="w")

        tk.Label(
            ent_card,
            text="Bi-directional enterprise gateway for automated case ingestion, repeat offender validation, and live takedown status tracking.",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"]
        ).pack(anchor="w", pady=(2, 12))

        # Grid form for Enterprise API
        f_grid = tk.Frame(ent_card, bg=t["panel"])
        f_grid.pack(fill="x")

        # Row 0: Base Endpoint URL
        tk.Label(
            f_grid,
            text="Gateway Endpoint URL:",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=0, column=0, pady=5, sticky="w")

        self.ent_url = tk.Entry(
            f_grid,
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["text"],
            insertbackground=t["text"],
            relief="flat",
            width=45
        )
        self.ent_url.grid(row=0, column=1, columnspan=2, pady=5, sticky="ew")

        # Row 1: Environment
        tk.Label(
            f_grid,
            text="Environment:",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=1, column=0, pady=5, sticky="w")

        self.env_var = tk.StringVar(value="production")
        env_box = tk.Frame(f_grid, bg=t["panel"])
        env_box.grid(row=1, column=1, columnspan=2, sticky="w", pady=5)

        tk.Radiobutton(
            env_box,
            text="🟢 Production Gateway",
            variable=self.env_var,
            value="production",
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["text"],
            selectcolor=t["bg"],
            activebackground=t["panel"],
            activeforeground=t["text"]
        ).pack(side="left", padx=(0, 14))

        tk.Radiobutton(
            env_box,
            text="🟡 Staging / Sandbox",
            variable=self.env_var,
            value="sandbox",
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["text"],
            selectcolor=t["bg"],
            activebackground=t["panel"],
            activeforeground=t["text"]
        ).pack(side="left")

        # Row 2: Client ID
        tk.Label(
            f_grid,
            text="Client / App ID:",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=2, column=0, pady=5, sticky="w")

        self.ent_client_id = tk.Entry(
            f_grid,
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["text"],
            insertbackground=t["text"],
            relief="flat",
            width=45
        )
        self.ent_client_id.grid(row=2, column=1, columnspan=2, pady=5, sticky="ew")

        # Row 3: Secret Token / Bearer Key
        tk.Label(
            f_grid,
            text="Secret Token / Bearer Key:",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=3, column=0, pady=5, sticky="w")

        self.ent_secret = tk.Entry(
            f_grid,
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["text"],
            insertbackground=t["text"],
            show="*",
            relief="flat",
            width=40
        )
        self.ent_secret.grid(row=3, column=1, pady=5, sticky="ew")

        btn_eye_ent = tk.Button(
            f_grid,
            text="👁",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["text"],
            relief="flat",
            width=3,
            command=lambda e=self.ent_secret: self._toggle_pwd_visibility(e),
            cursor="hand2"
        )
        btn_eye_ent.grid(row=3, column=2, padx=(6, 0), sticky="w")

        f_grid.columnconfigure(1, weight=1)

        # Action row for Enterprise API
        act_row = tk.Frame(ent_card, bg=t["panel"])
        act_row.pack(fill="x", pady=(12, 4))

        self.btn_test_ent = tk.Button(
            act_row,
            text="⚡ Test Connection",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            relief="flat",
            padx=14,
            pady=6,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1,
            command=self._on_test_enterprise_clicked,
            cursor="hand2"
        )
        self.btn_test_ent.pack(side="left")

        self.btn_save_ent = tk.Button(
            act_row,
            text="💾 Save Enterprise Configuration",
            font=FONT_BOLD,
            bg=t["accent"],
            fg="black" if str(t.get("name", "")).startswith("⚡") else "white",
            relief="flat",
            padx=14,
            pady=6,
            command=self._save_enterprise_keys,
            cursor="hand2"
        )
        self.btn_save_ent.pack(side="left", padx=10)

        self.lbl_ent_status = tk.Label(
            act_row,
            text="⚪ Not Configured",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"]
        )
        self.lbl_ent_status.pack(side="left", padx=10)

        # ── Card 2: eBay Developer REST API Keys ──
        ebay_card = tk.Frame(
            api_scroll,
            bg=t["panel"],
            padx=20,
            pady=16,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        ebay_card.pack(fill="x", pady=6, padx=2)

        tk.Label(
            ebay_card,
            text="🛒 eBay Developer REST API Keys (Finding & Buy Feed)",
            font=FONT_HEAD,
            bg=t["panel"],
            fg=t["text"]
        ).pack(anchor="w")

        tk.Label(
            ebay_card,
            text="Direct developer keys for high-volume eBay Finding, Buy Feed, and Taxonomy APIs with rate-limit expansion.",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"]
        ).pack(anchor="w", pady=(2, 12))

        # Grid form for eBay Keys
        e_grid = tk.Frame(ebay_card, bg=t["panel"])
        e_grid.pack(fill="x")

        # Row 0: App ID
        tk.Label(
            e_grid,
            text="App ID (Client ID):",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=0, column=0, pady=5, sticky="w")

        self.ebay_app_id = tk.Entry(
            e_grid,
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["text"],
            insertbackground=t["text"],
            relief="flat",
            width=45
        )
        self.ebay_app_id.grid(row=0, column=1, columnspan=2, pady=5, sticky="ew")

        # Row 1: Cert ID
        tk.Label(
            e_grid,
            text="Cert ID (Client Secret):",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=1, column=0, pady=5, sticky="w")

        self.ebay_cert_id = tk.Entry(
            e_grid,
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["text"],
            insertbackground=t["text"],
            show="*",
            relief="flat",
            width=40
        )
        self.ebay_cert_id.grid(row=1, column=1, pady=5, sticky="ew")

        btn_eye_cert = tk.Button(
            e_grid,
            text="👁",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["text"],
            relief="flat",
            width=3,
            command=lambda e=self.ebay_cert_id: self._toggle_pwd_visibility(e),
            cursor="hand2"
        )
        btn_eye_cert.grid(row=1, column=2, padx=(6, 0), sticky="w")

        # Row 2: Dev ID
        tk.Label(
            e_grid,
            text="Dev ID:",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=2, column=0, pady=5, sticky="w")

        self.ebay_dev_id = tk.Entry(
            e_grid,
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["text"],
            insertbackground=t["text"],
            relief="flat",
            width=45
        )
        self.ebay_dev_id.grid(row=2, column=1, columnspan=2, pady=5, sticky="ew")

        # Row 3: User Token / OAuth Refresh Token
        tk.Label(
            e_grid,
            text="OAuth Refresh Token:",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            width=22,
            anchor="w"
        ).grid(row=3, column=0, pady=5, sticky="w")

        self.ebay_user_token = tk.Entry(
            e_grid,
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["text"],
            insertbackground=t["text"],
            show="*",
            relief="flat",
            width=40
        )
        self.ebay_user_token.grid(row=3, column=1, pady=5, sticky="ew")

        btn_eye_token = tk.Button(
            e_grid,
            text="👁",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["text"],
            relief="flat",
            width=3,
            command=lambda e=self.ebay_user_token: self._toggle_pwd_visibility(e),
            cursor="hand2"
        )
        btn_eye_token.grid(row=3, column=2, padx=(6, 0), sticky="w")

        e_grid.columnconfigure(1, weight=1)

        # Action row for eBay Keys
        ebay_act = tk.Frame(ebay_card, bg=t["panel"])
        ebay_act.pack(fill="x", pady=(12, 4))

        self.btn_save_ebay = tk.Button(
            ebay_act,
            text="💾 Save eBay Developer Keys",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["text"],
            relief="flat",
            padx=14,
            pady=6,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1,
            command=self._save_ebay_keys,
            cursor="hand2"
        )
        self.btn_save_ebay.pack(side="left")

        self.lbl_ebay_status = tk.Label(
            ebay_act,
            text="",
            font=FONT_SM,
            bg=t["panel"],
            fg=t.get("success", "#10b981")
        )
        self.lbl_ebay_status.pack(side="left", padx=10)

        _bind_api_mousewheel_recursive(parent)

    def _load_api_keys(self):
        api_data = self.vault.get_api_credentials()
        ent = api_data.get("enterprise", {})
        if ent.get("endpoint_url"):
            self.ent_url.delete(0, "end")
            self.ent_url.insert(0, ent["endpoint_url"])
        if ent.get("client_id"):
            self.ent_client_id.delete(0, "end")
            self.ent_client_id.insert(0, ent["client_id"])
        if ent.get("secret_token"):
            self.ent_secret.delete(0, "end")
            self.ent_secret.insert(0, ent["secret_token"])
        if ent.get("environment"):
            self.env_var.set(ent["environment"])
        if ent.get("status"):
            self.lbl_ent_status.config(text=ent["status"])

        ebay = api_data.get("ebay_rest", {})
        if ebay.get("app_id"):
            self.ebay_app_id.delete(0, "end")
            self.ebay_app_id.insert(0, ebay["app_id"])
        if ebay.get("cert_id"):
            self.ebay_cert_id.delete(0, "end")
            self.ebay_cert_id.insert(0, ebay["cert_id"])
        if ebay.get("dev_id"):
            self.ebay_dev_id.delete(0, "end")
            self.ebay_dev_id.insert(0, ebay["dev_id"])
        if ebay.get("user_token"):
            self.ebay_user_token.delete(0, "end")
            self.ebay_user_token.insert(0, ebay["user_token"])

    def _save_enterprise_keys(self):
        data = self.vault.get_api_credentials()
        data["enterprise"] = {
            "endpoint_url": self.ent_url.get().strip(),
            "client_id": self.ent_client_id.get().strip(),
            "secret_token": self.ent_secret.get().strip(),
            "environment": self.env_var.get(),
            "status": self.lbl_ent_status.cget("text"),
            "last_checked": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        ok = self.vault.save_api_credentials(data)
        if ok:
            messagebox.showinfo("Enterprise API Saved", "Enterprise API Gateway configuration successfully updated.", parent=self)
        else:
            messagebox.showerror("Save Error", "Failed to write API configuration file.", parent=self)

    def _save_ebay_keys(self):
        data = self.vault.get_api_credentials()
        data["ebay_rest"] = {
            "app_id": self.ebay_app_id.get().strip(),
            "cert_id": self.ebay_cert_id.get().strip(),
            "dev_id": self.ebay_dev_id.get().strip(),
            "user_token": self.ebay_user_token.get().strip()
        }
        ok = self.vault.save_api_credentials(data)
        t = self.theme
        if ok:
            self.lbl_ebay_status.config(text="✓ eBay Developer Keys Saved", fg=t.get("success", "#10b981"))
            self.after(3000, lambda: self.lbl_ebay_status.config(text=""))
        else:
            self.lbl_ebay_status.config(text="❌ Save Failed", fg=t.get("danger", "#ef4444"))

    def _on_test_enterprise_clicked(self):
        url = self.ent_url.get().strip()
        client_id = self.ent_client_id.get().strip()
        secret = self.ent_secret.get().strip()

        if not url:
            messagebox.showwarning("Missing URL", "Please enter an Endpoint URL before testing the connection.", parent=self)
            return

        self.btn_test_ent.config(state="disabled", text="Testing...")
        self.lbl_ent_status.config(text="🟡 Testing Gateway Connection...", fg=self.theme.get("warning", "#f59e0b"))

        def _worker():
            success, msg = self.vault.test_enterprise_connection(url, client_id, secret)
            self.after(0, lambda: self._on_test_finished(success, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_test_finished(self, success: bool, msg: str):
        t = self.theme
        self.btn_test_ent.config(state="normal", text="⚡ Test Connection")
        fg_color = t.get("success", "#10b981") if success else t.get("danger", "#ef4444")
        self.lbl_ent_status.config(text=msg, fg=fg_color)