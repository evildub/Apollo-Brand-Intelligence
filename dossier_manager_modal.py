"""
Apollo Brand Intelligence - Multi-Dossier Investigation Vault Manager Modal
Allows analysts to manage multiple isolated staged dossiers, park in-progress sweeps,
restore or merge multi-wave investigations, and execute single or master multi-vault Excel exports.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_HEADING = ("Segoe UI", 10, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_CODE = ("Consolas", 9)
FONT_SM = ("Segoe UI", 8)


class DossierManagerModal(tk.Toplevel):
    """Interactive modal for managing multiple isolated investigation dossier vaults."""

    def __init__(self, master, theme: dict, data_store=None, exporter=None, on_restore_callback=None):
        super().__init__(master)
        self.theme = theme or {}
        self.data_store = data_store or getattr(master, "data_store", None)
        self.exporter = exporter or getattr(master, "exporter", None)
        self.on_restore_callback = on_restore_callback

        self.title("📁 Multi-Dossier Investigation Vault Manager")
        self.geometry("1060x720")
        self.minsize(920, 600)
        self.configure(bg=self._t("bg", "#121212"))
        self.transient(master)

        if hasattr(master, "_apply_dark_titlebar"):
            master._apply_dark_titlebar(self)
        if hasattr(master, "_load_app_icon"):
            master._load_app_icon(self)

        self._selected_vault = None

        self._setup_styles()
        self._build_header()
        self._build_body()
        self._build_footer()

        self._populate_vault_list()

        if hasattr(master, "_center_window"):
            master._center_window(self, 1060, 720)
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

    def _setup_styles(self):
        style = ttk.Style()
        style.configure(
            "Dossier.Treeview",
            background=self._t("entry_bg", "#0f172a"),
            foreground=self._t("text", "#f8fafc"),
            fieldbackground=self._t("entry_bg", "#0f172a"),
            font=FONT_NORM,
            rowheight=26
        )
        style.configure(
            "Dossier.Treeview.Heading",
            background=self._t("panel", "#1e1e1e"),
            foreground=self._t("text", "#f8fafc"),
            font=FONT_BOLD
        )
        style.map(
            "Dossier.Treeview",
            background=[("selected", self._t("select_bg", "#0284c7"))],
            foreground=[("selected", self._t("select_fg", "#ffffff"))]
        )

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=self._t("panel", "#1e1e1e"), padx=16, pady=10)
        hdr.pack(fill="x", side="top")

        left_info = tk.Frame(hdr, bg=self._t("panel", "#1e1e1e"))
        left_info.pack(side="left", fill="y")

        t_row = tk.Frame(left_info, bg=self._t("panel", "#1e1e1e"))
        t_row.pack(anchor="w")

        tk.Label(
            t_row, text="📁", font=("Segoe UI", 14),
            bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8")
        ).pack(side="left", padx=(0, 6))

        tk.Label(
            t_row, text="Multi-Dossier Investigation Vault Manager", font=FONT_TITLE,
            bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#ffffff")
        ).pack(side="left")

        tk.Label(
            left_info,
            text="Park clean listings into named staging carts, manage multi-wave investigations, and run single or combined master Excel exports.",
            font=FONT_SM, bg=self._t("panel", "#1e1e1e"), fg=self._t("subtext", "#94a3b8")
        ).pack(anchor="w", pady=(2, 0))

        # Right Summary Badges
        right_info = tk.Frame(hdr, bg=self._t("panel", "#1e1e1e"))
        right_info.pack(side="right", fill="y")

        self.summary_badge = tk.Label(
            right_info, text="0 Vaults | 0 Items", font=FONT_BOLD,
            bg=self._t("entry_bg", "#0f172a"), fg=self._t("accent", "#38bdf8"),
            padx=10, pady=4
        )
        self.summary_badge.pack(side="right")

    # ── Body (Dual-Pane Split) ────────────────────────────────────────────────
    def _build_body(self):
        body = tk.PanedWindow(
            self, orient="horizontal", bg=self._t("border", "#334155"),
            sashrelief="flat", sashwidth=4
        )
        body.pack(fill="both", expand=True, padx=12, pady=6)

        # ── LEFT PANE: Vaults List ────────────────────────────────────────────
        left_pane = tk.Frame(body, bg=self._t("bg", "#121212"))
        body.add(left_pane, minsize=320, width=360)

        v_lbl_bar = tk.Frame(left_pane, bg=self._t("panel", "#1e1e1e"), padx=8, pady=6)
        v_lbl_bar.pack(fill="x", side="top", pady=(0, 4))
        tk.Label(v_lbl_bar, text="🗄️ Investigation Vaults", font=FONT_HEADING, bg=self._t("panel", "#1e1e1e"), fg=self._t("text", "#ffffff")).pack(side="left")

        # Treeview for Vaults
        tree_frame = tk.Frame(left_pane, bg=self._t("entry_bg", "#0f172a"))
        tree_frame.pack(fill="both", expand=True)

        self.vault_tree = ttk.Treeview(
            tree_frame, columns=("count",), selectmode="browse", style="Dossier.Treeview"
        )
        self.vault_tree.heading("#0", text="Vault Name", anchor="w")
        self.vault_tree.heading("count", text="Listings", anchor="center")
        self.vault_tree.column("#0", width=220, minwidth=140, stretch=True)
        self.vault_tree.column("count", width=80, minwidth=60, anchor="center", stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.vault_tree.yview)
        self.vault_tree.configure(yscrollcommand=vsb.set)
        self.vault_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.vault_tree.bind("<<TreeviewSelect>>", self._on_vault_selected)

        # Left Action Toolbar
        v_act_row = tk.Frame(left_pane, bg=self._t("bg", "#121212"), pady=4)
        v_act_row.pack(fill="x", side="top")

        self._btn(v_act_row, "➕ New Vault", self._create_new_vault, accent=True).pack(side="left", padx=(0, 3))
        self._btn(v_act_row, "✏️ Rename", self._rename_selected_vault).pack(side="left", padx=(0, 3))
        self._btn(v_act_row, "🗑️ Delete", self._delete_selected_vault, danger=True).pack(side="right")

        # ── RIGHT PANE: Items Preview & Actions ───────────────────────────────
        right_pane = tk.Frame(body, bg=self._t("panel", "#1e1e1e"), padx=10, pady=10)
        body.add(right_pane, minsize=500, width=680)

        r_hdr = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"))
        r_hdr.pack(fill="x", pady=(0, 6))

        self.r_title = tk.Label(r_hdr, text="Selected Vault: (None)", font=FONT_HEADING, bg=self._t("panel", "#1e1e1e"), fg=self._t("accent", "#38bdf8"))
        self.r_title.pack(side="left")

        # Primary Actions Toolbar on Right Pane
        act_bar = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"), pady=4)
        act_bar.pack(fill="x", pady=(0, 6))

        self._btn(act_bar, "⚡ Restore (Replace Table)", self._restore_active_vault, accent=True).pack(side="left", padx=(0, 4))
        self._btn(act_bar, "➕ Merge into Table", self._merge_active_vault).pack(side="left", padx=(0, 6))
        self._btn(act_bar, "💾 Export Vault to Excel", self._export_selected_vault).pack(side="left", padx=(0, 6))
        self._btn(act_bar, "📦 Master Export (All Vaults)", self._export_all_dossiers_combined, accent=True).pack(side="right")

        # Items Table
        items_frame = tk.Frame(right_pane, bg=self._t("entry_bg", "#0f172a"))
        items_frame.pack(fill="both", expand=True)

        cols = ("brand", "marketplace", "title", "seller", "price", "threat_badge", "location")
        self.items_tree = ttk.Treeview(
            items_frame, columns=cols, show="headings", selectmode="extended", style="Dossier.Treeview"
        )
        headings = {
            "brand": "Brand",
            "marketplace": "Marketplace",
            "title": "Title",
            "seller": "Seller",
            "price": "Price",
            "threat_badge": "Threat Intel",
            "location": "Location"
        }
        widths = {
            "brand": 75,
            "marketplace": 90,
            "title": 220,
            "seller": 110,
            "price": 70,
            "threat_badge": 140,
            "location": 95
        }
        for c in cols:
            self.items_tree.heading(c, text=headings[c], anchor="w")
            self.items_tree.column(c, width=widths[c], minwidth=40, stretch=True if c == "title" else False)

        i_vsb = ttk.Scrollbar(items_frame, orient="vertical", command=self.items_tree.yview)
        i_hsb = ttk.Scrollbar(items_frame, orient="horizontal", command=self.items_tree.xview)
        self.items_tree.configure(yscrollcommand=i_vsb.set, xscrollcommand=i_hsb.set)

        self.items_tree.grid(row=0, column=0, sticky="nsew")
        i_vsb.grid(row=0, column=1, sticky="ns")
        i_hsb.grid(row=1, column=0, sticky="ew")

        items_frame.rowconfigure(0, weight=1)
        items_frame.columnconfigure(0, weight=1)

        # Sub-row for items management
        items_bot = tk.Frame(right_pane, bg=self._t("panel", "#1e1e1e"), pady=4)
        items_bot.pack(fill="x", pady=(4, 0))

        self.items_status = tk.Label(items_bot, text="0 listings in vault", font=FONT_SM, bg=self._t("panel", "#1e1e1e"), fg=self._t("subtext", "#94a3b8"))
        self.items_status.pack(side="left")

        self._btn(items_bot, "🗑️ Clear Vault Items", self._clear_selected_vault_items, danger=True).pack(side="right")
        self._btn(items_bot, "✕ Remove Selected", self._remove_selected_listings_from_vault, danger=True).pack(side="right", padx=(0, 4))

    # ── Footer ────────────────────────────────────────────────────────────────
    def _build_footer(self):
        ftr = tk.Frame(self, bg=self._t("bg", "#121212"), padx=16, pady=8)
        ftr.pack(fill="x", side="bottom")

        self.footer_status = tk.Label(
            ftr, text="Ready", font=FONT_SM,
            bg=self._t("bg", "#121212"), fg=self._t("subtext", "#94a3b8")
        )
        self.footer_status.pack(side="left")

        self._btn(ftr, "✓ Done / Close", self.destroy, accent=True, padx=16).pack(side="right")

    # ── Vault Operations ──────────────────────────────────────────────────────
    def _populate_vault_list(self):
        self.vault_tree.delete(*self.vault_tree.get_children())
        if not self.data_store:
            return

        dossiers = self.data_store.get_dossiers()
        total_items = 0
        first_id = None

        for name, items in dossiers.items():
            count = len(items) if isinstance(items, list) else 0
            total_items += count
            iid = self.vault_tree.insert("", "end", text=f"📁 {name}", values=(f"{count} items",))
            if not first_id:
                first_id = iid

        self.summary_badge.config(text=f"{len(dossiers)} Vaults | {total_items} Staged Listings")

        if first_id:
            self.vault_tree.selection_set(first_id)
            self._on_vault_selected()
        else:
            self._clear_items_view()

    def _on_vault_selected(self, event=None):
        sel = self.vault_tree.selection()
        if not sel:
            return
        item_id = sel[0]
        raw_name = self.vault_tree.item(item_id)["text"]
        clean_name = raw_name.replace("📁", "").strip()
        self._selected_vault = clean_name
        self.r_title.config(text=f"Selected Vault: '{clean_name}'")

        items = self.data_store.get_dossier(clean_name)
        self.items_tree.delete(*self.items_tree.get_children())
        for it in items:
            self.items_tree.insert("", "end", values=(
                it.get("brand", ""),
                it.get("marketplace", ""),
                it.get("title", ""),
                it.get("seller", ""),
                it.get("price", ""),
                it.get("threat_badge", ""),
                it.get("location", "")
            ))
        self.items_status.config(text=f"{len(items)} listing(s) in vault '{clean_name}'")

    def _clear_items_view(self):
        self._selected_vault = None
        self.r_title.config(text="Selected Vault: (None)")
        self.items_tree.delete(*self.items_tree.get_children())
        self.items_status.config(text="0 listings in vault")

    def _create_new_vault(self):
        name = simpledialog.askstring(
            "New Investigation Vault",
            "Enter a name for the new Dossier Vault:\n(e.g., 'Ford Airbags', 'NFL Wave 1', 'Quick Check')",
            parent=self
        )
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self.data_store.get_dossier_names():
            messagebox.showwarning("Vault Exists", f"A vault named '{name}' already exists.", parent=self)
            return
        self.data_store.create_dossier(name, initial_items=[])
        self._populate_vault_list()

    def _rename_selected_vault(self):
        if not self._selected_vault:
            return
        new_name = simpledialog.askstring(
            "Rename Vault",
            f"Enter new name for '{self._selected_vault}':",
            initialvalue=self._selected_vault,
            parent=self
        )
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name == self._selected_vault:
            return
        if new_name in self.data_store.get_dossier_names():
            messagebox.showwarning("Vault Exists", f"A vault named '{new_name}' already exists.", parent=self)
            return
        self.data_store.rename_dossier(self._selected_vault, new_name)
        self._selected_vault = new_name
        self._populate_vault_list()

    def _delete_selected_vault(self):
        if not self._selected_vault:
            return
        if len(self.data_store.get_dossier_names()) <= 1:
            messagebox.showwarning("Cannot Delete", "You cannot delete the only remaining Dossier Vault.", parent=self)
            return
        if not messagebox.askyesno(
            "Delete Vault",
            f"Are you sure you want to permanently delete vault '{self._selected_vault}' and all its staged listings?",
            parent=self
        ):
            return
        self.data_store.delete_dossier(self._selected_vault)
        self._populate_vault_list()

    def _clear_selected_vault_items(self):
        if not self._selected_vault:
            return
        if not messagebox.askyesno(
            "Clear Vault",
            f"Are you sure you want to clear all listings from '{self._selected_vault}'?",
            parent=self
        ):
            return
        self.data_store.clear_dossier(self._selected_vault)
        self._populate_vault_list()

    def _remove_selected_listings_from_vault(self):
        if not self._selected_vault:
            return
        sel = self.items_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select one or more listings to remove.", parent=self)
            return
        
        # Get indices to remove
        items = self.data_store.get_dossier(self._selected_vault)
        sel_indices = set(self.items_tree.index(s) for s in sel)
        new_items = [it for idx, it in enumerate(items) if idx not in sel_indices]
        self.data_store.save_dossier(self._selected_vault, new_items)
        self._on_vault_selected()
        self._populate_vault_list()

    # ── Restore & Merge Actions ───────────────────────────────────────────────
    def _restore_active_vault(self):
        if not self._selected_vault:
            return
        items = self.data_store.get_dossier(self._selected_vault)
        if not items:
            messagebox.showinfo("Empty Vault", f"Vault '{self._selected_vault}' contains no listings to restore.", parent=self)
            return

        if not messagebox.askyesno(
            "Restore Vault",
            f"Restore {len(items)} listing(s) from '{self._selected_vault}' to the Live Results Table?\n\n(This will replace the current table contents with this vault's listings)",
            parent=self
        ):
            return

        if self.on_restore_callback:
            self.on_restore_callback(items, mode="replace", vault_name=self._selected_vault)
        self.destroy()

    def _merge_active_vault(self):
        if not self._selected_vault:
            return
        items = self.data_store.get_dossier(self._selected_vault)
        if not items:
            messagebox.showinfo("Empty Vault", f"Vault '{self._selected_vault}' contains no listings to merge.", parent=self)
            return

        if self.on_restore_callback:
            self.on_restore_callback(items, mode="merge", vault_name=self._selected_vault)
        self.destroy()

    # ── Excel Exports ─────────────────────────────────────────────────────────
    def _export_selected_vault(self):
        if not self._selected_vault:
            return
        items = self.data_store.get_dossier(self._selected_vault)
        if not items:
            messagebox.showinfo("Empty Vault", f"Vault '{self._selected_vault}' is empty.", parent=self)
            return

        f_path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Export Vault '{self._selected_vault}' to Excel",
            initialfile=f"Apollo_{self._selected_vault.replace(' ', '_')}.xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if not f_path:
            return
        if not f_path.endswith(".xlsx"):
            f_path += ".xlsx"

        try:
            from exporter import ExcelExporter
            exp = self.exporter or ExcelExporter()
            exp.export(items, f_path)
            messagebox.showinfo("Export Complete", f"Successfully exported {len(items)} listing(s) from '{self._selected_vault}' to:\n{f_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export vault to Excel:\n{e}", parent=self)

    def _export_all_dossiers_combined(self):
        combined = self.data_store.get_all_dossiers_combined()
        if not combined:
            messagebox.showinfo("Empty Vaults", "All Dossier Vaults are currently empty.", parent=self)
            return

        f_path = filedialog.asksaveasfilename(
            parent=self,
            title="Master Export (All Dossiers Combined)",
            initialfile="Apollo_Master_All_Dossiers.xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if not f_path:
            return
        if not f_path.endswith(".xlsx"):
            f_path += ".xlsx"

        try:
            from exporter import ExcelExporter
            exp = self.exporter or ExcelExporter()
            exp.export(combined, f_path)
            messagebox.showinfo(
                "Master Export Complete",
                f"Successfully exported {len(combined)} verified listing(s) across all Dossier Vaults to:\n{f_path}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Master Dossiers to Excel:\n{e}", parent=self)
