"""
Apollo Brand Intelligence - Brand Registry & Portfolio Manager Modal
Allows analysts to manage isolated Brand Profiles, configure multi-level brand hierarchies,
sub-brands, model lines, mandatory inclusion keywords, and perform instant bulk imports.
"""

import copy
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_HEADING = ("Segoe UI", 10, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_CODE = ("Consolas", 9)
FONT_SM = ("Segoe UI", 8)


class BrandRegistryModal(tk.Toplevel):
    """Dedicated interactive modal for Brand Intelligence profiles and brand taxonomy management."""

    def __init__(self, master, theme: dict, data_store=None, on_save_callback=None):
        super().__init__(master)
        self.theme = theme or {}
        self.data_store = data_store or getattr(master, "data_store", None)
        self.on_save_callback = on_save_callback

        self.title("🏷 Brand Intelligence Registry & Profile Manager")
        self.geometry("1060x740")
        self.minsize(920, 620)
        self.configure(bg=self._t("bg", "#121212"))
        self.transient(master)

        if hasattr(master, "_apply_dark_titlebar"):
            master._apply_dark_titlebar(self)
        if hasattr(master, "_load_app_icon"):
            master._load_app_icon(self)

        self._selected_tree_item = None
        self._selected_brand = None
        self._selected_sub = None
        self._selected_model = None
        self._filter_query = ""

        self._setup_tree_styles()
        self._build_header()
        self._build_body()
        self._build_bulk_import_section()
        self._build_footer()

        self._refresh_profile_selector()
        self._populate_brand_tree()

        if hasattr(master, "_center_window"):
            master._center_window(self, 1060, 740)
        else:
            self.deiconify()
        self.lift()
        self.focus_force()

    def _t(self, key, default):
        return self.theme.get(key, default)

    def _btn(self, parent, text, command, accent=False, danger=False, **kwargs):
        t = self.theme
        if accent:
            bg = t.get("accent_btn", t.get("accent", "#0284c7"))
            fg = "#ffffff" if not str(t.get("name", "")).startswith("🪙") else "#0A0B0E"
            abg = t.get("accent2", "#38bdf8")
        elif danger:
            bg = t.get("danger", "#ef4444")
            fg = "#ffffff"
            abg = "#dc2626"
        else:
            bg = t.get("panel", "#1e1e1e")
            fg = t.get("text", "#ffffff")
            abg = t.get("border", "#334155")

        b = tk.Button(
            parent, text=text, command=command, font=FONT_BOLD if accent else FONT_NORM,
            bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
            relief="flat", cursor="hand2", padx=kwargs.pop("padx", 10), pady=kwargs.pop("pady", 4), **kwargs
        )
        return b

    def _setup_tree_styles(self):
        style = ttk.Style()
        style.configure(
            "BrandModal.Treeview",
            background=self._t("entry_bg", "#0f172a"),
            foreground=self._t("text", "#f8fafc"),
            fieldbackground=self._t("entry_bg", "#0f172a"),
            font=FONT_NORM,
            rowheight=26
        )
        style.configure(
            "BrandModal.Treeview.Heading",
            background=self._t("panel", "#1e1e1e"),
            foreground=self._t("text", "#f8fafc"),
            font=FONT_BOLD
        )
        style.map(
            "BrandModal.Treeview",
            background=[("selected", self._t("select_bg", "#0284c7"))],
            foreground=[("selected", self._t("select_fg", "#ffffff"))]
        )

    # ── Header & Profile Switcher ─────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=self._t("panel", "#1e1e1e"), padx=16, pady=10)
        hdr.pack(fill="x", side="top")

        # Left Info
        left_info = tk.Frame(hdr, bg=self._t("panel", "#1e1e1e"))
        left_info.pack(side="left", fill="y")

        t_row = tk.Frame(left_info, bg=self._t("panel", "#1e1e1e"))
        t_row.pack(anchor="w")

        tk.Label(
            t_row, text="🏷", font=("Segoe UI", 14),
            bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")
        ).pack(side="left", padx=(0, 6))

        tk.Label(
            t_row, text="Brand Intelligence Registry & Profile Manager", font=FONT_TITLE,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#ffffff")
        ).pack(side="left")

        tk.Label(
            left_info,
            text="Manage isolated brand workspaces, sub-brands, player/model lines, mandatory inclusion keywords, and pack exports.",
            font=FONT_SM, bg=self._t("panel", "#1e1e1e"), fg=self._t("subtext", "#94a3b8")
        ).pack(anchor="w", pady=(2, 0))

        # Right Profile Selector Toolbar
        prof_bar = tk.Frame(hdr, bg=self._t("panel", "#1e1e1e"))
        prof_bar.pack(side="right", fill="y")

        tk.Label(
            prof_bar, text="Active Profile:", font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")
        ).pack(side="left", padx=(0, 6))

        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            prof_bar, textvariable=self.profile_var, width=18, state="readonly", font=FONT_NORM
        )
        self.profile_combo.pack(side="left", padx=(0, 6))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        self._btn(prof_bar, "＋ New", self._create_new_profile, accent=True).pack(side="left", padx=(0, 3))
        self._btn(prof_bar, "📋 Clone", self._clone_profile).pack(side="left", padx=(0, 3))
        self._btn(prof_bar, "💾 Export", self._export_active_profile_pack).pack(side="left", padx=(0, 3))
        self._btn(prof_bar, "📥 Import", self._import_profile_pack).pack(side="left", padx=(0, 3))
        self._btn(prof_bar, "🗑 Delete", self._delete_active_profile, danger=True).pack(side="left")

    def _refresh_profile_selector(self):
        if not self.data_store:
            return
        profiles = self.data_store.get_profile_names()
        active = self.data_store.get_active_profile_name()
        self.profile_combo["values"] = profiles
        if active in profiles:
            self.profile_var.set(active)
        elif profiles:
            self.profile_var.set(profiles[0])
            self.data_store.set_active_profile(profiles[0])

    def _on_profile_selected(self, event=None):
        sel_prof = self.profile_var.get()
        if sel_prof and self.data_store:
            self.data_store.set_active_profile(sel_prof)
            self._populate_brand_tree()
            self._clear_editor()
            self._set_status(f"Switched to Brand Profile: '{sel_prof}'")
            if self.on_save_callback:
                self.on_save_callback()

    def _create_new_profile(self):
        name = simpledialog.askstring(
            "New Brand Profile",
            "Enter a name for the new Brand Profile:\n(e.g., 'NFL 32 Teams', 'Luxury Apparel', 'Auto OEM')",
            parent=self
        )
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self.data_store.get_profile_names():
            messagebox.showwarning("Profile Exists", f"A profile named '{name}' already exists.", parent=self)
            return
        self.data_store.create_profile(name, initial_brands={})
        self.data_store.set_active_profile(name)
        self._refresh_profile_selector()
        self._populate_brand_tree()
        self._clear_editor()
        self._set_status(f"Created and activated new profile: '{name}'")
        if self.on_save_callback:
            self.on_save_callback()

    def _clone_profile(self):
        active = self.data_store.get_active_profile_name()
        new_name = simpledialog.askstring(
            "Clone Brand Profile",
            f"Enter name for the copy of '{active}':",
            initialvalue=f"{active} (Copy)",
            parent=self
        )
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name in self.data_store.get_profile_names():
            messagebox.showwarning("Profile Exists", f"A profile named '{new_name}' already exists.", parent=self)
            return
        self.data_store.duplicate_profile(active, new_name)
        self.data_store.set_active_profile(new_name)
        self._refresh_profile_selector()
        self._populate_brand_tree()
        self._set_status(f"Cloned profile '{active}' to '{new_name}'")
        if self.on_save_callback:
            self.on_save_callback()

    def _delete_active_profile(self):
        active = self.data_store.get_active_profile_name()
        if len(self.data_store.get_profile_names()) <= 1:
            messagebox.showwarning(
                "Cannot Delete",
                "You cannot delete the only remaining Brand Profile.",
                parent=self
            )
            return
        if not messagebox.askyesno(
            "Delete Profile",
            f"Are you sure you want to permanently delete profile '{active}' and all its registered brands?",
            parent=self
        ):
            return
        self.data_store.delete_profile(active)
        self._refresh_profile_selector()
        self._populate_brand_tree()
        self._clear_editor()
        self._set_status(f"Deleted profile '{active}'")
        if self.on_save_callback:
            self.on_save_callback()

    def _export_active_profile_pack(self):
        active = self.data_store.get_active_profile_name()
        f_path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Export Profile '{active}' Pack",
            initialfile=f"{active.replace(' ', '_')}_BrandPack.apollo-pack",
            filetypes=[("Apollo Brand Pack", "*.apollo-pack"), ("JSON Files", "*.json")]
        )
        if not f_path:
            return
        if not f_path.endswith(".apollo-pack") and not f_path.endswith(".json"):
            f_path += ".apollo-pack"
        ok = self.data_store.export_profile_pack(active, f_path)
        if ok:
            messagebox.showinfo("Export Successful", f"Brand Profile '{active}' exported to:\n{f_path}", parent=self)
        else:
            messagebox.showerror("Export Failed", f"Could not export Brand Profile to '{f_path}'.", parent=self)

    def _import_profile_pack(self):
        f_path = filedialog.askopenfilename(
            parent=self,
            title="Import Brand Profile Pack",
            filetypes=[("Apollo Brand Pack / JSON", "*.apollo-pack;*.json"), ("All Files", "*.*")]
        )
        if not f_path:
            return
        ok, res_name = self.data_store.import_profile_pack(f_path)
        if ok:
            self.data_store.set_active_profile(res_name)
            self._refresh_profile_selector()
            self._populate_brand_tree()
            self._set_status(f"Imported profile pack '{res_name}' successfully.")
            messagebox.showinfo("Import Successful", f"Successfully imported Brand Profile: '{res_name}'!", parent=self)
            if self.on_save_callback:
                self.on_save_callback()
        else:
            messagebox.showerror("Import Error", f"Failed to import brand pack:\n{res_name}", parent=self)

    # ── Body (Dual-Pane Split) ────────────────────────────────────────────────
    def _build_body(self):
        body = tk.PanedWindow(
            self, orient="horizontal", bg=self._t("border", "#334155"),
            sashrelief="flat", sashwidth=4
        )
        body.pack(fill="both", expand=True, padx=12, pady=6)

        # ── LEFT PANE: Tree & Tools ───────────────────────────────────────────
        left_pane = tk.Frame(body, bg=self._t("bg", "#121212"))
        body.add(left_pane, minsize=400, width=520)

        # Filter row
        filt_row = tk.Frame(left_pane, bg=self._t("panel", "#1e1e1e"), padx=8, pady=6)
        filt_row.pack(fill="x", side="top", pady=(0, 4))

        tk.Label(
            filt_row, text="🔍", font=FONT_NORM,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")
        ).pack(side="left", padx=(0, 4))

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._on_filter_changed)
        filt_entry = tk.Entry(
            filt_row, textvariable=self.filter_var, font=FONT_NORM,
            bg=self._t("entry_bg", "#0f172a"), fg=self._t("text", "#ffffff"),
            insertbackground=self._t("text", "#ffffff"), relief="flat"
        )
        filt_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._btn(filt_row, "✕ Clear", lambda: self.filter_var.set(""), padx=6, pady=2).pack(side="left")

        # Treeview Container
        tree_frame = tk.Frame(left_pane, bg=self._t("entry_bg", "#0f172a"))
        tree_frame.pack(fill="both", expand=True)

        cols = ("type", "count", "inclusions")
        self.brand_tree = ttk.Treeview(
            tree_frame, columns=cols, selectmode="extended", style="BrandModal.Treeview"
        )
        self.brand_tree.heading("#0", text="Brand / Sub-Brand / Line", anchor="w")
        self.brand_tree.heading("type", text="Type", anchor="center")
        self.brand_tree.heading("count", text="Items", anchor="center")
        self.brand_tree.heading("inclusions", text="Mandatory Inclusions", anchor="w")

        self.brand_tree.column("#0", width=230, minwidth=160, stretch=True)
        self.brand_tree.column("type", width=70, minwidth=50, anchor="center", stretch=False)
        self.brand_tree.column("count", width=60, minwidth=40, anchor="center", stretch=False)
        self.brand_tree.column("inclusions", width=140, minwidth=80, stretch=True)

        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.brand_tree.yview)
        tree_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.brand_tree.xview)
        self.brand_tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)

        self.brand_tree.grid(row=0, column=0, sticky="nsew")
        tree_vsb.grid(row=0, column=1, sticky="ns")
        tree_hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.brand_tree.bind("<<TreeviewSelect>>", self._on_tree_selected)
        self.brand_tree.bind("<Double-1>", lambda e: self._on_tree_double_click())

        # Left Toolbar Actions
        act_row1 = tk.Frame(left_pane, bg=self._t("bg", "#121212"), pady=4)
        act_row1.pack(fill="x", side="top")

        self._btn(act_row1, "＋ Parent Brand", self._add_parent_brand, accent=True).pack(side="left", padx=(0, 4))
        self._btn(act_row1, "＋ Sub-Brand", self._add_sub_brand).pack(side="left", padx=(0, 4))
        self._btn(act_row1, "＋ Model / Line", self._add_model_item).pack(side="left", padx=(0, 4))
        self._btn(act_row1, "▲ Up", lambda: self._move_brand(-1)).pack(side="left", padx=(0, 2))
        self._btn(act_row1, "▼ Down", lambda: self._move_brand(1)).pack(side="left", padx=(0, 4))
        self._btn(act_row1, "🗑 Remove", self._remove_selected_nodes, danger=True).pack(side="right")
        self._btn(act_row1, "🗑 Purge", self._purge_active_profile, danger=True).pack(side="right", padx=(0, 4))

        # ── RIGHT PANE: Brand Detail Editor ───────────────────────────────────
        right_pane = tk.Frame(body, bg=self._t("panel", "#1e1e1e"), padx=14, pady=12)
        body.add(right_pane, minsize=380, width=520)

        r_hdr = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"))
        r_hdr.pack(fill="x", pady=(0, 8))

        self.editor_icon = tk.Label(r_hdr, text="🏢", font=("Segoe UI", 12), bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8"))
        self.editor_icon.pack(side="left", padx=(0, 6))

        self.editor_title = tk.Label(r_hdr, text="Select a brand to inspect or edit details", font=FONT_HEADING, bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#ffffff"))
        self.editor_title.pack(side="left")

        div1 = tk.Frame(right_pane, bg=self._t("border", "#334155"), height=1)
        div1.pack(fill="x", pady=(0, 10))

        # Brand Name Entry
        lbl_bn = tk.Label(right_pane, text="Brand / Entity Name:", font=FONT_BOLD, bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#ffffff"))
        lbl_bn.pack(anchor="w")
        self.edit_name_var = tk.StringVar()
        self.edit_name_entry = tk.Entry(
            right_pane, textvariable=self.edit_name_var, font=FONT_NORM,
            bg=self._t("entry_bg", "#0f172a"), fg=self._t("text", "#ffffff"),
            insertbackground=self._t("text", "#ffffff"), relief="flat"
        )
        self.edit_name_entry.pack(fill="x", pady=(2, 8))

        # Mandatory Inclusions Box
        inc_hdr = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"))
        inc_hdr.pack(fill="x")
        tk.Label(
            inc_hdr, text="Mandatory Inclusions (Always match on scan):", font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")
        ).pack(side="left")
        tk.Label(
            inc_hdr, text="(Comma-separated keywords)", font=FONT_SM,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("subtext", "#94a3b8")
        ).pack(side="right")

        self.edit_inc_text = tk.Text(
            right_pane, height=3, font=FONT_NORM,
            bg=self._t("entry_bg", "#0f172a"), fg=self._t("text", "#ffffff"),
            insertbackground=self._t("text", "#ffffff"), relief="flat", wrap="word"
        )
        self.edit_inc_text.pack(fill="x", pady=(2, 8))

        # Sub-Brands & Models Multi-Line Box
        mod_hdr = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"))
        mod_hdr.pack(fill="x")
        tk.Label(
            mod_hdr, text="Models / Sub-Brands / Variations:", font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#ffffff")
        ).pack(side="left")
        tk.Label(
            mod_hdr, text="(One per line or comma-separated)", font=FONT_SM,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("subtext", "#94a3b8")
        ).pack(side="right")

        self.edit_models_text = tk.Text(
            right_pane, height=6, font=FONT_NORM,
            bg=self._t("entry_bg", "#0f172a"), fg=self._t("text", "#ffffff"),
            insertbackground=self._t("text", "#ffffff"), relief="flat", wrap="word"
        )
        self.edit_models_text.pack(fill="both", expand=True, pady=(2, 8))

        # Save Button Row
        save_row = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"))
        save_row.pack(fill="x", pady=(4, 8))

        self.save_detail_btn = self._btn(save_row, "⚡ Save Brand Details", self._save_brand_details, accent=True)
        self.save_detail_btn.pack(side="left")

        # Live Terms Preview Box
        prev_hdr = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"))
        prev_hdr.pack(fill="x")
        tk.Label(
            prev_hdr, text="Scraper Target Terms Preview:", font=FONT_SM,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("subtext", "#94a3b8")
        ).pack(side="left")

        self.preview_text = tk.Text(
            right_pane, height=3, font=FONT_CODE,
            bg=self._t("entry_bg", "#0f172a"), fg=self._t("accent2", "#38bdf8"),
            relief="flat", wrap="word", state="disabled"
        )
        self.preview_text.pack(fill="x", pady=(2, 0))

    # ── Bottom: Bulk Import & Paste Section ───────────────────────────────────
    def _build_bulk_import_section(self):
        bot_frame = tk.Frame(self, bg=self._t("panel", "#1e1e1e"), padx=12, pady=8)
        bot_frame.pack(fill="x", side="top", padx=12, pady=(0, 4))

        hdr_row = tk.Frame(bot_frame, bg=self._t("panel", "#1e1e1e"))
        hdr_row.pack(fill="x", pady=(0, 4))

        tk.Label(
            hdr_row, text="📥 Quick Bulk Import & Paste:", font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")
        ).pack(side="left")

        tk.Label(
            hdr_row,
            text="Supports simple team lists (one per line / comma-separated) or hierarchies ('Toyota -> Lexus -> RX').",
            font=FONT_SM, bg=self._t("panel", "#1e1e1e"), fg=self._t("subtext", "#94a3b8")
        ).pack(side="left", padx=8)

        input_row = tk.Frame(bot_frame, bg=self._t("panel", "#1e1e1e"))
        input_row.pack(fill="x")

        self.bulk_text = tk.Text(
            input_row, height=3, font=FONT_NORM,
            bg=self._t("entry_bg", "#0f172a"), fg=self._t("text", "#ffffff"),
            insertbackground=self._t("text", "#ffffff"), relief="flat", wrap="word"
        )
        self.bulk_text.pack(side="left", fill="both", expand=True, padx=(0, 8))

        btn_col = tk.Frame(input_row, bg=self._t("panel", "#1e1e1e"))
        btn_col.pack(side="right", fill="y")

        self._btn(btn_col, "📋 Bulk Import", self._execute_bulk_import, accent=True, pady=6).pack(fill="x", pady=(0, 4))
        self._btn(btn_col, "✕ Clear Box", lambda: self.bulk_text.delete("1.0", "end"), pady=2).pack(fill="x")

    # ── Footer ────────────────────────────────────────────────────────────────
    def _build_footer(self):
        ftr = tk.Frame(self, bg=self._t("bg", "#121212"), padx=16, pady=8)
        ftr.pack(fill="x", side="bottom")

        self.status_lbl = tk.Label(
            ftr, text="Ready", font=FONT_SM,
            bg=self._t("bg", "#121212"), fg=self._t("subtext", "#94a3b8")
        )
        self.status_lbl.pack(side="left")

        self._btn(ftr, "✓ Close & Save", self._close_and_save, accent=True, padx=16).pack(side="right")

    def _set_status(self, msg: str):
        self.status_lbl.config(text=msg)

    # ── Treeview Population & Interaction ─────────────────────────────────────
    def _populate_brand_tree(self):
        self.brand_tree.delete(*self.brand_tree.get_children())
        if not self.data_store:
            return

        brands = self.data_store.get_brands()
        q = self._filter_query.strip().lower()

        total_brands = len(brands)
        shown_brands = 0

        for b_name, b_data in brands.items():
            subs = b_data.get("subs", {})
            models = b_data.get("models", [])
            inclusions = b_data.get("inclusions", [])

            # Filter logic
            b_match = (not q) or (q in b_name.lower())
            subs_match = any(q in s.lower() or any(q in m.lower() for m in (s_mods if isinstance(s_mods, list) else [])) for s, s_mods in subs.items())
            mods_match = any(q in m.lower() for m in models)
            inc_match = any(q in str(inc).lower() for inc in inclusions)

            if not (b_match or subs_match or mods_match or inc_match):
                continue

            shown_brands += 1
            total_items = len(models) + sum(len(m_list) for m_list in subs.values()) + len(subs)
            inc_str = ", ".join(inclusions) if inclusions else "—"

            parent_id = self.brand_tree.insert(
                "", "end", text=f"🏢 {b_name}",
                values=("Parent", f"{total_items} items", inc_str),
                open=bool(q)  # Auto expand if searching
            )

            # Insert Sub-brands
            for sub_name, sub_models in subs.items():
                s_id = self.brand_tree.insert(
                    parent_id, "end", text=f"🏷 {sub_name}",
                    values=("Sub-Brand", f"{len(sub_models)} models", "—"),
                    open=bool(q)
                )
                for mod in sub_models:
                    self.brand_tree.insert(
                        s_id, "end", text=f"📦 {mod}",
                        values=("Model", "—", "—")
                    )

            # Insert Parent-level direct models
            for mod in models:
                self.brand_tree.insert(
                    parent_id, "end", text=f"📦 {mod}",
                    values=("Model", "—", "—")
                )

        prof = self.data_store.get_active_profile_name()
        self._set_status(f"Profile: '{prof}' | Showing {shown_brands} of {total_brands} parent brands.")

    def _on_filter_changed(self, *args):
        self._filter_query = self.filter_var.get()
        self._populate_brand_tree()

    def _on_tree_selected(self, event=None):
        sel = self.brand_tree.selection()
        if not sel:
            return
        item_id = sel[0]
        self._selected_tree_item = item_id
        item = self.brand_tree.item(item_id)
        raw_text = item["text"]
        clean_text = re.sub(r"^[🏢🏷📦]\s*", "", raw_text).strip()
        vals = item["values"]
        item_type = vals[0] if vals else "Parent"

        parent_item_id = self.brand_tree.parent(item_id)
        if not parent_item_id:
            # Parent Brand selected
            self._selected_brand = clean_text
            self._selected_sub = None
            self._selected_model = None
            self._load_brand_into_editor(clean_text)
        else:
            grandparent_id = self.brand_tree.parent(parent_item_id)
            if not grandparent_id:
                # Sub-Brand or Direct Model
                parent_text = re.sub(r"^[🏢🏷📦]\s*", "", self.brand_tree.item(parent_item_id)["text"]).strip()
                if item_type == "Sub-Brand":
                    self._selected_brand = parent_text
                    self._selected_sub = clean_text
                    self._selected_model = None
                    self._load_sub_into_editor(parent_text, clean_text)
                else:
                    self._selected_brand = parent_text
                    self._selected_sub = None
                    self._selected_model = clean_text
                    self._load_brand_into_editor(parent_text)
            else:
                # Sub-Model
                grandparent_text = re.sub(r"^[🏢🏷📦]\s*", "", self.brand_tree.item(grandparent_id)["text"]).strip()
                parent_text = re.sub(r"^[🏢🏷📦]\s*", "", self.brand_tree.item(parent_item_id)["text"]).strip()
                self._selected_brand = grandparent_text
                self._selected_sub = parent_text
                self._selected_model = clean_text
                self._load_sub_into_editor(grandparent_text, parent_text)

    def _load_brand_into_editor(self, brand_name: str):
        brands = self.data_store.get_brands()
        b_data = brands.get(brand_name, {})
        self.editor_icon.config(text="🏢")
        self.editor_title.config(text=f"Parent Brand: {brand_name}")
        self.edit_name_var.set(brand_name)

        # Inclusions
        inc_list = b_data.get("inclusions", [])
        self.edit_inc_text.delete("1.0", "end")
        self.edit_inc_text.insert("1.0", ", ".join(inc_list))

        # Models / Subs
        models = b_data.get("models", [])
        subs = b_data.get("subs", {})
        lines = []
        for m in models:
            lines.append(m)
        for s_name, s_mods in subs.items():
            lines.append(f"{s_name} -> {', '.join(s_mods)}")
        self.edit_models_text.delete("1.0", "end")
        self.edit_models_text.insert("1.0", "\n".join(lines))

        self._update_preview(brand_name)

    def _load_sub_into_editor(self, parent_name: str, sub_name: str):
        brands = self.data_store.get_brands()
        b_data = brands.get(parent_name, {})
        subs = b_data.get("subs", {})
        sub_models = subs.get(sub_name, [])

        self.editor_icon.config(text="🏷")
        self.editor_title.config(text=f"Sub-Brand: {sub_name} (under {parent_name})")
        self.edit_name_var.set(sub_name)

        inc_list = b_data.get("inclusions", [])
        self.edit_inc_text.delete("1.0", "end")
        self.edit_inc_text.insert("1.0", ", ".join(inc_list))

        self.edit_models_text.delete("1.0", "end")
        self.edit_models_text.insert("1.0", "\n".join(sub_models))

        self._update_preview(parent_name)

    def _update_preview(self, brand_name: str):
        terms = self.data_store.get_terms_for_brand(brand_name)
        inclusions = self.data_store.get_brand_inclusions(brand_name)
        prev_str = f"Search Terms ({len(terms)}): {', '.join(terms)}\nMandatory Inclusions: {', '.join(inclusions) if inclusions else 'None'}"
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", prev_str)
        self.preview_text.config(state="disabled")

    def _clear_editor(self):
        self._selected_tree_item = None
        self._selected_brand = None
        self._selected_sub = None
        self._selected_model = None
        self.editor_icon.config(text="🏢")
        self.editor_title.config(text="Select a brand to inspect or edit details")
        self.edit_name_var.set("")
        self.edit_inc_text.delete("1.0", "end")
        self.edit_models_text.delete("1.0", "end")
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.config(state="disabled")

    def _on_tree_double_click(self):
        pass

    # ── CRUD Operations ───────────────────────────────────────────────────────
    def _add_parent_brand(self):
        name = simpledialog.askstring("Add Parent Brand", "Enter new Parent Brand name:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        self.data_store.add_parent_brand(name)
        self._populate_brand_tree()
        self._load_brand_into_editor(name)
        self._set_status(f"Added Parent Brand: '{name}'")
        if self.on_save_callback:
            self.on_save_callback()

    def _add_sub_brand(self):
        if not self._selected_brand:
            messagebox.showinfo("Select Parent", "Please select a Parent Brand first to add a sub-brand under it.", parent=self)
            return
        sub = simpledialog.askstring("Add Sub-Brand", f"Enter Sub-Brand name under '{self._selected_brand}':", parent=self)
        if not sub or not sub.strip():
            return
        sub = sub.strip()
        self.data_store.add_sub_brand(self._selected_brand, sub)
        self._populate_brand_tree()
        self._load_sub_into_editor(self._selected_brand, sub)
        self._set_status(f"Added Sub-Brand '{sub}' under '{self._selected_brand}'")
        if self.on_save_callback:
            self.on_save_callback()

    def _add_model_item(self):
        if not self._selected_brand:
            messagebox.showinfo("Select Brand", "Please select a Parent Brand or Sub-Brand first.", parent=self)
            return
        target = self._selected_sub or self._selected_brand
        m_name = simpledialog.askstring("Add Model / Variation", f"Enter Model / Line name under '{target}':", parent=self)
        if not m_name or not m_name.strip():
            return
        m_name = m_name.strip()
        self.data_store.add_model(self._selected_brand, self._selected_sub or "", m_name)
        self._populate_brand_tree()
        if self._selected_sub:
            self._load_sub_into_editor(self._selected_brand, self._selected_sub)
        else:
            self._load_brand_into_editor(self._selected_brand)
        self._set_status(f"Added Model '{m_name}' to '{target}'")
        if self.on_save_callback:
            self.on_save_callback()

    def _save_brand_details(self):
        if not self._selected_brand:
            messagebox.showinfo("No Brand Selected", "Please select a brand to save details for.", parent=self)
            return

        new_name = self.edit_name_var.get().strip()
        if not new_name:
            messagebox.showwarning("Empty Name", "Brand name cannot be blank.", parent=self)
            return

        # Parse Inclusions
        inc_raw = self.edit_inc_text.get("1.0", "end").strip()
        inclusions = [str(x).strip().strip('"\'') for x in inc_raw.split(",") if str(x).strip().strip('"\'')]

        # Parse Models/Subs lines
        mod_raw = self.edit_models_text.get("1.0", "end").strip()
        lines = mod_raw.splitlines()

        if self._selected_sub:
            # Updating sub-brand
            sub_models = []
            for l in lines:
                l_clean = l.strip()
                if not l_clean:
                    continue
                for m in l_clean.split(","):
                    if m.strip():
                        sub_models.append(m.strip())
            
            brands = self.data_store.get_brands()
            if self._selected_brand in brands:
                subs = brands[self._selected_brand].setdefault("subs", {})
                if self._selected_sub != new_name:
                    subs.pop(self._selected_sub, None)
                subs[new_name] = sub_models
                self.data_store._save()
                self._selected_sub = new_name
        else:
            # Updating parent brand
            parsed_models = []
            parsed_subs = {}
            for l in lines:
                l_clean = l.strip()
                if not l_clean:
                    continue
                if "->" in l_clean or ":" in l_clean or ">" in l_clean:
                    delim = "->" if "->" in l_clean else (":" if ":" in l_clean else ">")
                    parts = [p.strip() for p in l_clean.split(delim) if p.strip()]
                    if parts:
                        s_name = parts[0]
                        s_mods = [sm.strip() for sm in parts[1].split(",") if sm.strip()] if len(parts) > 1 else []
                        parsed_subs[s_name] = s_mods
                else:
                    for m in l_clean.split(","):
                        if m.strip():
                            parsed_models.append(m.strip())

            brands = self.data_store.get_brands()
            if self._selected_brand in brands:
                b_data = brands.pop(self._selected_brand)
                b_data["models"] = parsed_models
                if parsed_subs:
                    b_data["subs"] = parsed_subs
                b_data["inclusions"] = inclusions
                brands[new_name] = b_data
                self.data_store._save()
                self._selected_brand = new_name

        self._populate_brand_tree()
        self._update_preview(self._selected_brand)
        self._set_status(f"Saved brand details for '{new_name}' successfully.")
        if self.on_save_callback:
            self.on_save_callback()

    def _remove_selected_nodes(self):
        sel = self.brand_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select one or more items to remove.", parent=self)
            return

        names_to_remove = []
        for item_id in sel:
            raw_text = self.brand_tree.item(item_id)["text"]
            clean_text = re.sub(r"^[🏢🏷📦]\s*", "", raw_text).strip()
            names_to_remove.append(clean_text)

        if not messagebox.askyesno(
            "Remove Items",
            f"Are you sure you want to remove {len(names_to_remove)} selected item(s)?",
            parent=self
        ):
            return

        self.data_store.remove_multiple_brands(names_to_remove)
        self._populate_brand_tree()
        self._clear_editor()
        self._set_status(f"Removed {len(names_to_remove)} item(s).")
        if self.on_save_callback:
            self.on_save_callback()

    def _purge_active_profile(self):
        active = self.data_store.get_active_profile_name()
        if not messagebox.askyesno(
            "Purge Profile Brands",
            f"Are you sure you want to PURGE ALL brands from active profile '{active}'?\nThis will clear the profile to a blank slate.",
            parent=self
        ):
            return
        self.data_store.purge_all_brands()
        self._populate_brand_tree()
        self._clear_editor()
        self._set_status(f"Purged all brands from active profile '{active}'.")
        if self.on_save_callback:
            self.on_save_callback()

    def _move_brand(self, direction: int):
        sel = self.brand_tree.selection()
        if not sel:
            return
        item_id = sel[0]
        parent_id = self.brand_tree.parent(item_id)
        if parent_id:
            return  # Move currently applies to parent brands
        raw_text = self.brand_tree.item(item_id)["text"]
        brand_name = re.sub(r"^[🏢🏷📦]\s*", "", raw_text).strip()

        brands = list(self.data_store.get_brands().keys())
        if brand_name not in brands:
            return
        idx = brands.index(brand_name)
        new_idx = idx + direction
        if 0 <= new_idx < len(brands):
            brands[idx], brands[new_idx] = brands[new_idx], brands[idx]
            self.data_store.reorder_parent_brands(brands)
            self._populate_brand_tree()
            if self.on_save_callback:
                self.on_save_callback()

    # ── Bulk Import Execution ─────────────────────────────────────────────────
    def _execute_bulk_import(self):
        raw_text = self.bulk_text.get("1.0", "end").strip()
        if not raw_text:
            messagebox.showinfo("Empty Input", "Please paste one or more brand names into the box.", parent=self)
            return

        active_prof = self.data_store.get_active_profile_name()
        count = self.data_store.bulk_import_brands_to_profile(active_prof, raw_text)
        self.bulk_text.delete("1.0", "end")
        self._populate_brand_tree()
        self._set_status(f"Bulk imported {count} brand entity/entities into profile '{active_prof}'.")
        messagebox.showinfo(
            "Bulk Import Complete",
            f"Successfully imported {count} brand entities into active profile '{active_prof}'!",
            parent=self
        )
        if self.on_save_callback:
            self.on_save_callback()

    def _close_and_save(self):
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()
