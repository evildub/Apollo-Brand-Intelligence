"""
Apollo Brand Intelligence - Product Type & Industry Taxonomy Manager
Allows analysts to inspect, edit, add, and test product taxonomy categories and keyword triggers
organized by industry sectors (Automotive, Apparel, Tools, Home/Living, Pharma/Vet, Electronics).
"""

import copy
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_HEADING = ("Segoe UI", 10, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_CODE = ("Consolas", 9)
FONT_SM = ("Segoe UI", 8)


class ProductTypeModal(tk.Toplevel):
    """Interactive modal for managing Industry & Product Type taxonomy rules."""

    def __init__(self, master, theme: dict, data_store=None, on_save_callback=None):
        super().__init__(master)
        self.theme = theme or {}
        self.data_store = data_store or getattr(master, "data_store", None)
        self.on_save_callback = on_save_callback

        self.title("🏷 Product Type & Industry Taxonomy Manager")
        self.geometry("1020x720")
        self.minsize(860, 600)
        self.configure(bg=self._t("bg", "#121212"))
        self.transient(master)

        if hasattr(master, "_apply_dark_titlebar"):
            master._apply_dark_titlebar(self)
        if hasattr(master, "_load_app_icon"):
            master._load_app_icon(self)

        # In-memory working copy of taxonomy
        raw_tax = None
        if self.data_store and hasattr(self.data_store, "get_product_taxonomy"):
            raw_tax = self.data_store.get_product_taxonomy()
        if not raw_tax:
            from data_store import DEFAULT_PRODUCT_TAXONOMY
            raw_tax = DEFAULT_PRODUCT_TAXONOMY
        self.taxonomy = copy.deepcopy(raw_tax)

        self._selected_industry = None
        self._selected_type = None

        self._setup_tree_styles()
        self._build_header()
        self._build_body()
        self._build_sandbox()
        self._build_footer()

        self._populate_industries()

        if hasattr(master, "_center_window"):
            master._center_window(self, 1020, 720)
        else:
            self.deiconify()
        self.lift()
        self.focus_force()

    def _t(self, key, default):
        return self.theme.get(key, default)

    def _setup_tree_styles(self):
        """Configure theme-adaptive TTK Treeview styles to prevent white-on-white text issues."""
        style = ttk.Style()
        style.configure(
            "Taxonomy.Treeview",
            background=self._t("entry_bg", "#0f172a"),
            foreground=self._t("text", "#f8fafc"),
            fieldbackground=self._t("entry_bg", "#0f172a"),
            font=FONT_NORM,
            rowheight=26
        )
        style.configure(
            "Taxonomy.Treeview.Heading",
            background=self._t("panel", "#1e1e1e"),
            foreground=self._t("text", "#f8fafc"),
            font=FONT_BOLD
        )
        style.map(
            "Taxonomy.Treeview",
            background=[("selected", self._t("select_bg", "#0284c7"))],
            foreground=[("selected", self._t("select_fg", "#ffffff"))]
        )

    def _build_header(self):
        hdr = tk.Frame(self, bg=self._t("panel", "#1e1e1e"), padx=16, pady=12)
        hdr.pack(fill="x", side="top")

        left = tk.Frame(hdr, bg=self._t("panel", "#1e1e1e"))
        left.pack(side="left", fill="y")

        tk.Label(
            left,
            text="🏷 Product Type & Industry Taxonomy Manager",
            font=FONT_TITLE,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("accent", "#38bdf8")
        ).pack(anchor="w")

        tk.Label(
            left,
            text="Organize product categories and keyword auto-tagging rules across industry sectors (Automotive, Apparel, Tools, etc.).",
            font=FONT_NORM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        ).pack(anchor="w", pady=(2, 0))

    def _build_body(self):
        body = tk.Frame(self, bg=self._t("bg", "#121212"), padx=12, pady=8)
        body.pack(fill="both", expand=True)

        paned = tk.PanedWindow(
            body,
            orient="horizontal",
            bg=self._t("border", "#334155"),
            sashwidth=4,
            sashrelief="flat"
        )
        paned.pack(fill="both", expand=True)

        # ── Left Column: Industries ──
        left_frame = tk.Frame(paned, bg=self._t("panel", "#1e1e1e"), padx=8, pady=8)
        paned.add(left_frame, minsize=260, width=300)

        lbl_ind = tk.Label(
            left_frame,
            text="🏢 Industry Sectors",
            font=FONT_HEADING,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("text", "#f8fafc")
        )
        lbl_ind.pack(anchor="w", pady=(0, 6))

        ind_tree_frame = tk.Frame(left_frame, bg=self._t("panel", "#1e1e1e"))
        ind_tree_frame.pack(fill="both", expand=True)

        self.ind_tree = ttk.Treeview(
            ind_tree_frame,
            columns=("types_count",),
            show="tree headings",
            selectmode="browse",
            style="Taxonomy.Treeview"
        )
        self.ind_tree.heading("#0", text="Industry Sector")
        self.ind_tree.heading("types_count", text="Types")
        self.ind_tree.column("#0", width=190, stretch=True)
        self.ind_tree.column("types_count", width=55, anchor="center")

        ind_scroll = ttk.Scrollbar(ind_tree_frame, orient="vertical", command=self.ind_tree.yview)
        self.ind_tree.configure(yscrollcommand=ind_scroll.set)
        self.ind_tree.pack(side="left", fill="both", expand=True)
        ind_scroll.pack(side="right", fill="y")
        self.ind_tree.bind("<<TreeviewSelect>>", self._on_industry_selected)

        # Industry buttons
        ind_btn_bar = tk.Frame(left_frame, bg=self._t("panel", "#1e1e1e"), pady=6)
        ind_btn_bar.pack(fill="x")

        tk.Button(
            ind_btn_bar,
            text="➕ Add",
            font=FONT_SM,
            bg=self._t("btn_bg", "#334155"),
            fg=self._t("text", "#f8fafc"),
            relief="flat",
            padx=6,
            pady=2,
            command=self._add_industry_dialog
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            ind_btn_bar,
            text="✏️ Rename",
            font=FONT_SM,
            bg=self._t("btn_bg", "#334155"),
            fg=self._t("text", "#f8fafc"),
            relief="flat",
            padx=6,
            pady=2,
            command=self._rename_industry_dialog
        ).pack(side="left", padx=4)

        tk.Button(
            ind_btn_bar,
            text="🗑 Delete",
            font=FONT_SM,
            bg=self._t("btn_bg", "#334155"),
            fg="#f87171",
            relief="flat",
            padx=6,
            pady=2,
            command=self._delete_industry_dialog
        ).pack(side="right")

        # ── Right Column: Product Types & Keyword Rules ──
        right_frame = tk.Frame(paned, bg=self._t("panel", "#1e1e1e"), padx=8, pady=8)
        paned.add(right_frame, minsize=460, stretch="always")

        lbl_types = tk.Label(
            right_frame,
            text="🏷 Product Types in Selected Industry",
            font=FONT_HEADING,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("text", "#f8fafc")
        )
        lbl_types.pack(anchor="w", pady=(0, 6))

        type_tree_frame = tk.Frame(right_frame, bg=self._t("panel", "#1e1e1e"))
        type_tree_frame.pack(fill="both", expand=True)

        self.type_tree = ttk.Treeview(
            type_tree_frame,
            columns=("kws_count", "kws_preview"),
            show="tree headings",
            selectmode="browse",
            height=6,
            style="Taxonomy.Treeview"
        )
        self.type_tree.heading("#0", text="Product Type Tag")
        self.type_tree.heading("kws_count", text="Triggers")
        self.type_tree.heading("kws_preview", text="Keyword Rule Sample")
        self.type_tree.column("#0", width=180, stretch=False)
        self.type_tree.column("kws_count", width=65, anchor="center")
        self.type_tree.column("kws_preview", width=260, stretch=True)

        type_scroll = ttk.Scrollbar(type_tree_frame, orient="vertical", command=self.type_tree.yview)
        self.type_tree.configure(yscrollcommand=type_scroll.set)
        self.type_tree.pack(side="left", fill="both", expand=True)
        type_scroll.pack(side="right", fill="y")
        self.type_tree.bind("<<TreeviewSelect>>", self._on_type_selected)

        # Type buttons
        type_btn_bar = tk.Frame(right_frame, bg=self._t("panel", "#1e1e1e"), pady=6)
        type_btn_bar.pack(fill="x")

        tk.Button(
            type_btn_bar,
            text="➕ Add Product Type",
            font=FONT_SM,
            bg=self._t("btn_bg", "#334155"),
            fg=self._t("text", "#f8fafc"),
            relief="flat",
            padx=6,
            pady=2,
            command=self._add_type_dialog
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            type_btn_bar,
            text="✏️ Rename",
            font=FONT_SM,
            bg=self._t("btn_bg", "#334155"),
            fg=self._t("text", "#f8fafc"),
            relief="flat",
            padx=6,
            pady=2,
            command=self._rename_type_dialog
        ).pack(side="left", padx=4)

        tk.Button(
            type_btn_bar,
            text="🗑 Delete",
            font=FONT_SM,
            bg=self._t("btn_bg", "#334155"),
            fg="#f87171",
            relief="flat",
            padx=6,
            pady=2,
            command=self._delete_type_dialog
        ).pack(side="right")

        # ── Keyword Editor for selected type ──
        kw_hdr_bar = tk.Frame(right_frame, bg=self._t("panel", "#1e1e1e"))
        kw_hdr_bar.pack(fill="x", pady=(8, 2))

        self.lbl_kw_title = tk.Label(
            kw_hdr_bar,
            text="🔑 Trigger Keywords for Selected Type",
            font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("accent", "#38bdf8")
        )
        self.lbl_kw_title.pack(side="left")

        tk.Label(
            kw_hdr_bar,
            text="(Separated by commas or newlines)",
            font=FONT_SM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        ).pack(side="left", padx=6)

        self.kw_text = tk.Text(
            right_frame,
            height=4,
            font=FONT_CODE,
            bg=self._t("input_bg", "#0f172a"),
            fg=self._t("text", "#f8fafc"),
            insertbackground=self._t("accent", "#38bdf8"),
            relief="solid",
            bd=1,
            padx=6,
            pady=6
        )
        self.kw_text.pack(fill="x", pady=4)
        self.kw_text.bind("<KeyRelease>", lambda e: self._on_keywords_edited())

        kw_action_bar = tk.Frame(right_frame, bg=self._t("panel", "#1e1e1e"))
        kw_action_bar.pack(fill="x")

        self.lbl_kw_status = tk.Label(
            kw_action_bar,
            text="",
            font=FONT_SM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        )
        self.lbl_kw_status.pack(side="left")

        tk.Button(
            kw_action_bar,
            text="💾 Save Keywords",
            font=FONT_SM,
            bg=self._t("btn_bg", "#334155"),
            fg=self._t("accent", "#38bdf8"),
            relief="flat",
            padx=8,
            pady=2,
            command=self._save_active_keywords
        ).pack(side="right")

    def _build_sandbox(self):
        """Interactive real-time title detection testing sandbox."""
        sb_frame = tk.LabelFrame(
            self,
            text=" 🧪 Live Title Auto-Tagging Sandbox (Test Detection Rules) ",
            font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("accent", "#38bdf8"),
            padx=12,
            pady=8
        )
        sb_frame.pack(fill="x", padx=12, pady=(0, 8))

        row1 = tk.Frame(sb_frame, bg=self._t("panel", "#1e1e1e"))
        row1.pack(fill="x")

        tk.Label(
            row1,
            text="Listing Title:",
            font=FONT_NORM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("text", "#f8fafc")
        ).pack(side="left", padx=(0, 6))

        self.test_title_var = tk.StringVar(value="4Pcs Laser Iridium Spark Plugs for Toyota Camry 2.5L 2018-2022")
        self.test_title_var.trace_add("write", lambda *_: self._run_sandbox_detection())

        self.test_entry = tk.Entry(
            row1,
            textvariable=self.test_title_var,
            font=FONT_NORM,
            bg=self._t("input_bg", "#0f172a"),
            fg=self._t("text", "#f8fafc"),
            insertbackground=self._t("accent", "#38bdf8"),
            relief="solid",
            bd=1
        )
        self.test_entry.pack(side="left", fill="x", expand=True, padx=4)

        row2 = tk.Frame(sb_frame, bg=self._t("panel", "#1e1e1e"), pady=4)
        row2.pack(fill="x")

        self.lbl_detect_result = tk.Label(
            row2,
            text="",
            font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"),
            fg="#4ade80",
            anchor="w"
        )
        self.lbl_detect_result.pack(fill="x")

    def _build_footer(self):
        footer = tk.Frame(self, bg=self._t("panel", "#1e1e1e"), padx=16, pady=10)
        footer.pack(fill="x", side="bottom")

        self.lbl_footer_status = tk.Label(
            footer,
            text="",
            font=FONT_NORM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        )
        self.lbl_footer_status.pack(side="left")

        tk.Button(
            footer,
            text="✕ Close",
            font=FONT_NORM,
            bg=self._t("btn_bg", "#334155"),
            fg=self._t("text", "#f8fafc"),
            relief="flat",
            padx=12,
            pady=4,
            command=self.destroy
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            footer,
            text="💾 Save & Apply Taxonomy",
            font=FONT_BOLD,
            bg=self._t("accent_btn", "#0284c7"),
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=4,
            command=self._save_all_and_apply
        ).pack(side="right", padx=6)

        tk.Button(
            footer,
            text="🔄 Reset to Defaults",
            font=FONT_NORM,
            bg=self._t("btn_bg", "#334155"),
            fg="#f87171",
            relief="flat",
            padx=10,
            pady=4,
            command=self._reset_to_defaults_dialog
        ).pack(side="right", padx=6)

    # ── Logic & Populating ──

    def _populate_industries(self, select_industry=None):
        """Populate the industry sectors tree."""
        self.ind_tree.delete(*self.ind_tree.get_children())
        first_item = None
        target_item = None

        total_types = 0
        for ind_name, types_dict in self.taxonomy.items():
            count = len(types_dict)
            total_types += count
            iid = self.ind_tree.insert("", "end", text=ind_name, values=(str(count),))
            if first_item is None:
                first_item = iid
            if select_industry and ind_name == select_industry:
                target_item = iid

        sel_to_pick = target_item or first_item
        if sel_to_pick:
            self.ind_tree.selection_set(sel_to_pick)
            self.ind_tree.focus(sel_to_pick)
            self._on_industry_selected(None)

        self._update_footer_status(len(self.taxonomy), total_types)
        self._run_sandbox_detection()

    def _on_industry_selected(self, _event):
        sel = self.ind_tree.selection()
        if not sel:
            return
        item_text = self.ind_tree.item(sel[0], "text")
        self._selected_industry = item_text
        self._populate_types_for_industry(item_text)

    def _populate_types_for_industry(self, ind_name, select_type=None):
        self.type_tree.delete(*self.type_tree.get_children())
        self.kw_text.delete("1.0", "end")
        self._selected_type = None

        types_dict = self.taxonomy.get(ind_name, {})
        first_type_iid = None
        target_type_iid = None

        for pt_name, kws in types_dict.items():
            kw_count_str = str(len(kws))
            kw_preview = ", ".join(kws[:3])
            if len(kws) > 3:
                kw_preview += f" (+{len(kws)-3} more)"

            iid = self.type_tree.insert("", "end", text=pt_name, values=(kw_count_str, kw_preview))
            if first_type_iid is None:
                first_type_iid = iid
            if select_type and pt_name == select_type:
                target_type_iid = iid

        sel_pick = target_type_iid or first_type_iid
        if sel_pick:
            self.type_tree.selection_set(sel_pick)
            self.type_tree.focus(sel_pick)
            self._on_type_selected(None)

    def _on_type_selected(self, _event):
        sel = self.type_tree.selection()
        if not sel or not self._selected_industry:
            return
        pt_name = self.type_tree.item(sel[0], "text")
        self._selected_type = pt_name

        self.lbl_kw_title.config(text=f"🔑 Trigger Keywords for [{pt_name}]:")
        kws = self.taxonomy.get(self._selected_industry, {}).get(pt_name, [])
        self.kw_text.delete("1.0", "end")
        self.kw_text.insert("1.0", ", ".join(kws))
        self.lbl_kw_status.config(text=f"{len(kws)} keyword triggers loaded.")

    def _on_keywords_edited(self):
        self._save_active_keywords(silent=True)
        self._run_sandbox_detection()

    def _save_active_keywords(self, silent=False):
        if not self._selected_industry or not self._selected_type:
            return

        raw_text = self.kw_text.get("1.0", "end").strip()
        # Parse commas and newlines
        items = []
        for line in raw_text.split("\n"):
            for chunk in line.split(","):
                c = chunk.strip().lower()
                if c and c not in items:
                    items.append(c)

        if self._selected_industry in self.taxonomy:
            self.taxonomy[self._selected_industry][self._selected_type] = items

        # Update Treeview preview
        sel = self.type_tree.selection()
        if sel:
            kw_preview = ", ".join(items[:3])
            if len(items) > 3:
                kw_preview += f" (+{len(items)-3} more)"
            self.type_tree.item(sel[0], values=(str(len(items)), kw_preview))

        self.lbl_kw_status.config(text=f"✓ {len(items)} keywords saved.")
        if not silent:
            self._run_sandbox_detection()

    def _add_industry_dialog(self):
        name = simpledialog.askstring(
            "Add Industry Sector",
            "Enter name for new Industry Sector (e.g. '🎮 Gaming & Collectibles'):",
            parent=self
        )
        if not name:
            return
        name = name.strip()
        if name in self.taxonomy:
            messagebox.showwarning("Exists", f"Industry '{name}' already exists.", parent=self)
            return
        self.taxonomy[name] = {}
        self._populate_industries(select_industry=name)

    def _rename_industry_dialog(self):
        if not self._selected_industry:
            return
        old_name = self._selected_industry
        new_name = simpledialog.askstring(
            "Rename Industry",
            f"Enter new name for '{old_name}':",
            initialvalue=old_name,
            parent=self
        )
        if not new_name or new_name.strip() == old_name:
            return
        new_name = new_name.strip()
        data = self.taxonomy.pop(old_name)
        self.taxonomy[new_name] = data
        self._populate_industries(select_industry=new_name)

    def _show_themed_info(self, title: str, message: str, icon: str = "ℹ"):
        """Display an Apollo theme-adaptive info dialog."""
        t = self.theme
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=self._t("bg", "#121212"))
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        if hasattr(self.master, "_apply_dark_titlebar"):
            self.master._apply_dark_titlebar(win)
        if hasattr(self.master, "_load_app_icon"):
            self.master._load_app_icon(win)

        card = tk.Frame(win, bg=self._t("panel", "#1e1e1e"), padx=20, pady=16, highlightbackground=self._t("border", "#334155"), highlightthickness=1)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        hdr = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
        hdr.pack(fill="x", pady=(0, 8))

        tk.Label(hdr, text=icon, font=("Segoe UI", 16), bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text=title, font=FONT_HEADING, bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#f8fafc")).pack(side="left")

        div = tk.Frame(card, bg=self._t("border", "#334155"), height=1)
        div.pack(fill="x", pady=(0, 10))

        tk.Label(card, text=message, font=FONT_NORM, bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#f8fafc"), justify="left", wraplength=400).pack(anchor="w", pady=(0, 14))

        btn_row = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
        btn_row.pack(fill="x")
        btn = tk.Button(
            btn_row,
            text="OK",
            font=FONT_BOLD,
            bg=self._t("accent_btn", "#0284c7"),
            fg="#ffffff",
            relief="flat",
            padx=18,
            pady=3,
            cursor="hand2",
            command=win.destroy
        )
        btn.pack(side="right")
        btn.focus_set()
        win.bind("<Return>", lambda e: win.destroy())
        win.bind("<Escape>", lambda e: win.destroy())

        if hasattr(self.master, "_center_window"):
            self.master._center_window(win, 460, 210)

    def _show_themed_confirm(self, title: str, message: str, icon: str = "❓", yes_text: str = "Yes", no_text: str = "No") -> bool:
        """Display an Apollo theme-adaptive confirmation dialog returning True for Yes, False for No."""
        t = self.theme
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=self._t("bg", "#121212"))
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        if hasattr(self.master, "_apply_dark_titlebar"):
            self.master._apply_dark_titlebar(win)
        if hasattr(self.master, "_load_app_icon"):
            self.master._load_app_icon(win)

        result = {"confirmed": False}

        card = tk.Frame(win, bg=self._t("panel", "#1e1e1e"), padx=20, pady=16, highlightbackground=self._t("border", "#334155"), highlightthickness=1)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        hdr = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
        hdr.pack(fill="x", pady=(0, 8))

        tk.Label(hdr, text=icon, font=("Segoe UI", 16), bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text=title, font=FONT_HEADING, bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#f8fafc")).pack(side="left")

        div = tk.Frame(card, bg=self._t("border", "#334155"), height=1)
        div.pack(fill="x", pady=(0, 10))

        tk.Label(card, text=message, font=FONT_NORM, bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#f8fafc"), justify="left", wraplength=400).pack(anchor="w", pady=(0, 14))

        btn_row = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
        btn_row.pack(fill="x")

        def _on_yes():
            result["confirmed"] = True
            win.destroy()

        def _on_no():
            result["confirmed"] = False
            win.destroy()

        no_btn = tk.Button(
            btn_row,
            text=no_text,
            font=FONT_NORM,
            bg=self._t("btn_bg", "#334155"),
            fg=self._t("text", "#f8fafc"),
            relief="flat",
            padx=16,
            pady=3,
            cursor="hand2",
            command=_on_no
        )
        no_btn.pack(side="right", padx=(6, 0))

        yes_btn = tk.Button(
            btn_row,
            text=yes_text,
            font=FONT_BOLD,
            bg=self._t("accent_btn", "#0284c7"),
            fg="#ffffff",
            relief="flat",
            padx=18,
            pady=3,
            cursor="hand2",
            command=_on_yes
        )
        yes_btn.pack(side="right")
        yes_btn.focus_set()

        win.bind("<Return>", lambda e: _on_yes())
        win.bind("<Escape>", lambda e: _on_no())

        if hasattr(self.master, "_center_window"):
            self.master._center_window(win, 460, 210)
        win.wait_window()
        return result["confirmed"]

    def _delete_industry_dialog(self):
        if not self._selected_industry:
            return
        ind = self._selected_industry
        confirm = self._show_themed_confirm(
            "Delete Industry",
            f"Are you sure you want to delete '{ind}' and all its product types?"
        )
        if confirm:
            self.taxonomy.pop(ind, None)
            self._populate_industries()

    def _add_type_dialog(self):
        if not self._selected_industry:
            self._show_themed_info("Select Industry", "Please select an Industry Sector first.", icon="ℹ")
            return
        name = simpledialog.askstring(
            "Add Product Type",
            f"Enter Product Type name for '{self._selected_industry}' (e.g. 'Air Filters'):",
            parent=self
        )
        if not name:
            return
        name = name.strip()
        ind_dict = self.taxonomy.setdefault(self._selected_industry, {})
        if name in ind_dict:
            self._show_themed_info("Exists", f"Product Type '{name}' already exists in this industry.", icon="⚠")
            return
        ind_dict[name] = []
        self._populate_types_for_industry(self._selected_industry, select_type=name)
        sel = self.ind_tree.selection()
        if sel:
            self.ind_tree.item(sel[0], values=(str(len(ind_dict)),))

    def _rename_type_dialog(self):
        if not self._selected_industry or not self._selected_type:
            return
        old_type = self._selected_type
        new_type = simpledialog.askstring(
            "Rename Product Type",
            f"Enter new name for '{old_type}':",
            initialvalue=old_type,
            parent=self
        )
        if not new_type or new_type.strip() == old_type:
            return
        new_type = new_type.strip()
        ind_dict = self.taxonomy[self._selected_industry]
        kws = ind_dict.pop(old_type)
        ind_dict[new_type] = kws
        self._populate_types_for_industry(self._selected_industry, select_type=new_type)

    def _delete_type_dialog(self):
        if not self._selected_industry or not self._selected_type:
            return
        pt = self._selected_type
        confirm = self._show_themed_confirm(
            "Delete Product Type",
            f"Delete product type '{pt}' from '{self._selected_industry}'?"
        )
        if confirm:
            ind_dict = self.taxonomy[self._selected_industry]
            ind_dict.pop(pt, None)
            self._populate_types_for_industry(self._selected_industry)
            sel = self.ind_tree.selection()
            if sel:
                self.ind_tree.item(sel[0], values=(str(len(ind_dict)),))

    def _detect_type_from_taxonomy(self, title: str):
        """Run classification against in-memory taxonomy."""
        t_low = title.lower()
        for ind_name, types_dict in self.taxonomy.items():
            for pt_name, kws in types_dict.items():
                for kw in kws:
                    kw_clean = kw.lower().strip()
                    if kw_clean and kw_clean in t_low:
                        return ind_name, pt_name, kw_clean
        return None, None, None

    def _run_sandbox_detection(self):
        """Test the current title against active taxonomy rules."""
        title = self.test_title_var.get().strip()
        if not title:
            self.lbl_detect_result.config(text="Enter a listing title to test classification.", fg=self._t("subtext", "#94a3b8"))
            return

        ind, pt, matched_kw = self._detect_type_from_taxonomy(title)
        if pt:
            self.lbl_detect_result.config(
                text=f"🎯 MATCH DETECTED: [{ind}] ➔ Tag: '{pt}' (Matched Keyword: '{matched_kw}')",
                fg="#4ade80"
            )
        else:
            self.lbl_detect_result.config(
                text="⚪ No match detected (Will be categorized as 'Unassigned' or fallback to brand without product type).",
                fg=self._t("subtext", "#94a3b8")
            )

    def _update_footer_status(self, ind_count, type_count):
        self.lbl_footer_status.config(
            text=f"📊 Active Taxonomy: {ind_count} Industries, {type_count} Total Product Types."
        )

    def _save_all_and_apply(self):
        """Save the updated taxonomy to persistent data_store and notify callbacks."""
        self._save_active_keywords(silent=True)
        if self.data_store and hasattr(self.data_store, "set_product_taxonomy"):
            self.data_store.set_product_taxonomy(self.taxonomy)

        if callable(self.on_save_callback):
            try:
                self.on_save_callback(self.taxonomy)
            except Exception:
                pass
        elif hasattr(self.master, "_on_taxonomy_saved_and_applied"):
            try:
                self.master._on_taxonomy_saved_and_applied(self.taxonomy)
            except Exception:
                pass

        self._show_themed_info(
            "Saved",
            "Product Type & Industry Taxonomy successfully saved and applied to live auto-tagging engine and active results table!",
            icon="💾"
        )

    def _reset_to_defaults_dialog(self):
        confirm = self._show_themed_confirm(
            "Reset Taxonomy to Factory Defaults",
            "Are you sure you want to reset all Industry & Product Type rules back to Apollo factory defaults?\n\nAny custom tags or keyword additions will be replaced."
        )
        if not confirm:
            return

        if self.data_store and hasattr(self.data_store, "reset_product_taxonomy"):
            self.taxonomy = copy.deepcopy(self.data_store.reset_product_taxonomy())
        self._populate_industries()

        if callable(self.on_save_callback):
            try:
                self.on_save_callback(self.taxonomy)
            except Exception:
                pass
        elif hasattr(self.master, "_on_taxonomy_saved_and_applied"):
            try:
                self.master._on_taxonomy_saved_and_applied(self.taxonomy)
            except Exception:
                pass

        self._show_themed_info("Reset Complete", "Taxonomy reset to factory defaults and applied to active results table.", icon="🔄")
