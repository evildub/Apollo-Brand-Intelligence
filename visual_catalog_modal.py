# visual_catalog_modal.py
# Apollo Visual Threat & Packaging Intelligence Manager Dialog
# Supports Multi-Hash Threat Asset Clusters, 1-Click Variant Merging, and Cluster Inspector

import os
import io
import uuid
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_SM = ("Segoe UI", 8)


class VisualCatalogModal(tk.Toplevel):
    def __init__(self, master, visual_catalog_manager, theme, on_update_callback=None):
        super().__init__(master)
        self.withdraw()
        self.vcm = visual_catalog_manager
        self.theme = theme
        self.on_update = on_update_callback
        self.photo_refs = []
        self.selected_card_ids = set()
        self.card_registry = {}
        self._card_thumb_cache = {}

        self.title("🖼 Apollo Visual Packaging & Threat Intelligence Library")
        self.geometry("1180x760")
        self.minsize(880, 580)
        self.configure(bg=self._t("bg", "#121212"))

        if hasattr(master, "_apply_dark_titlebar"):
            master._apply_dark_titlebar(self)

        self._build_ui()
        self._load_gallery()
        self._center_window(1180, 760)
        self.deiconify()
        self.lift()
        self.focus_force()

    def _t(self, key, default="#1e1e1e"):
        return self.theme.get(key, default)

    def _center_window(self, width, height, target_win=None):
        win = target_win or self
        parent = self if target_win else self.master
        if hasattr(parent, "_center_window") and target_win is None:
            parent._center_window(win, width, height)
            return

        w = width or 600
        h = height or 400

        try:
            m_x = parent.winfo_rootx()
            m_y = parent.winfo_rooty()
            m_w = parent.winfo_width()
            m_h = parent.winfo_height()
            if m_w > 50 and m_h > 50:
                x = m_x + (m_w - w) // 2
                y = m_y + (m_h - h) // 2
                if y < m_y:
                    y = m_y + 10
            else:
                x = m_x + 20
                y = m_y + 20
        except Exception:
            x = (win.winfo_screenwidth() // 2) - (w // 2)
            y = max(30, (win.winfo_screenheight() // 2) - (h // 2))

        win.geometry(f"{w}x{h}+{x}+{y}")
        try:
            win.transient(parent)
        except Exception:
            pass
        try:
            win.deiconify()
            win.lift()
            win.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        panel_bg = self._t("panel", "#1e1e1e")
        accent_color = self._t("accent", "#00d2ff")
        text_color = self._t("text", "#ffffff")
        subtext_color = self._t("subtext", "#888888")
        btn_bg = self._t("btn_normal_bg", panel_bg)
        btn_fg = self._t("btn_normal_fg", text_color)
        bg_color = self._t("bg", "#121212")

        # Top Header Bar
        header = tk.Frame(self, bg=panel_bg, padx=14, pady=10)
        header.pack(fill="x", side="top")

        lbl_box = tk.Frame(header, bg=panel_bg)
        lbl_box.pack(side="left")

        tk.Label(lbl_box, text="🖼 Visual Threat Intelligence Catalog", font=FONT_TITLE,
                 bg=panel_bg, fg=accent_color).pack(anchor="w")
        tk.Label(lbl_box, text="Multi-Hash Threat Clusters • Match Benign Packaging & Flag Counterfeit Photo Syndicates",
                 font=FONT_SM, bg=panel_bg, fg=subtext_color).pack(anchor="w")

        # Top Right Action Buttons
        top_btns = tk.Frame(header, bg=panel_bg)
        top_btns.pack(side="right")

        self.merge_btn = tk.Button(top_btns, text="🔗 Merge Selected (0)", font=FONT_BOLD, bg=accent_color,
                                   fg="black" if self.theme.get("name","").startswith("⚡") else "white",
                                   relief="flat", padx=8, pady=4, cursor="hand2", command=self._merge_selected_cards)
        self.merge_btn.pack(side="left", padx=3)

        tk.Button(top_btns, text="🔄 Re-Scan Session", font=FONT_BOLD, bg=btn_bg, fg=accent_color,
                  relief="flat", padx=8, pady=4, cursor="hand2", command=self._rescan_session_matches).pack(side="left", padx=3)
        tk.Button(top_btns, text="📤 Export", font=FONT_BOLD, bg=btn_bg, fg=btn_fg,
                  relief="flat", padx=6, pady=4, cursor="hand2", command=self._export_visual_pack).pack(side="left", padx=3)
        tk.Button(top_btns, text="📥 Import", font=FONT_BOLD, bg=btn_bg, fg=btn_fg,
                  relief="flat", padx=6, pady=4, cursor="hand2", command=self._import_visual_pack).pack(side="left", padx=3)
        tk.Button(top_btns, text="➕ Add File", font=FONT_BOLD, bg=btn_bg, fg=btn_fg,
                  relief="flat", padx=8, pady=4, cursor="hand2", command=self._add_from_file).pack(side="left", padx=3)
        tk.Button(top_btns, text="🌐 Add URL", font=FONT_BOLD, bg=btn_bg, fg=btn_fg,
                  relief="flat", padx=8, pady=4, cursor="hand2", command=self._add_from_url).pack(side="left", padx=3)
        tk.Button(top_btns, text="🗑️ Purge All Images", font=FONT_BOLD, bg=self._t("danger", "#dc2626"), fg="#FFFFFF",
                  relief="flat", padx=8, pady=4, cursor="hand2", command=self._on_purge_all).pack(side="left", padx=6)

        # Control Bar: Filters & Sensitivity Slider & Sorting
        ctrl_bar = tk.Frame(self, bg=panel_bg, padx=14, pady=8, bd=1, relief="solid")
        ctrl_bar.pack(fill="x", side="top", pady=(1, 0))

        # Filter Tabs (Segmented Button Bar)
        self.filter_var = tk.StringVar(value="counterfeit")
        tab_box = tk.Frame(ctrl_bar, bg=panel_bg)
        tab_box.pack(side="left")

        tk.Label(tab_box, text="Filter:", font=FONT_BOLD, bg=panel_bg, fg=text_color).pack(side="left", padx=(0, 6))

        self.filter_btns = {}
        filter_options = [
            ("📁 All", "all"),
            ("🟢 Benign Packaging", "benign"),
            ("🔴 Known Counterfeits", "counterfeit")
        ]

        def _on_filter_click(val):
            self.filter_var.set(val)
            self._update_filter_btn_styles()
            self._load_gallery()

        self._on_filter_click = _on_filter_click

        for text, val in filter_options:
            btn = tk.Button(
                tab_box,
                text=text,
                font=FONT_BOLD if val == self.filter_var.get() else FONT_NORM,
                relief="flat",
                bd=0,
                padx=10,
                pady=3,
                cursor="hand2",
                command=lambda v=val: _on_filter_click(v)
            )
            btn.pack(side="left", padx=2)
            self.filter_btns[val] = btn

        self._update_filter_btn_styles()

        # Sort Dropdown
        sort_box = tk.Frame(ctrl_bar, bg=panel_bg)
        sort_box.pack(side="left", padx=(20, 0))
        tk.Label(sort_box, text="Sort:", font=FONT_BOLD, bg=panel_bg, fg=text_color).pack(side="left", padx=(0, 4))
        self.sort_var = tk.StringVar(value="Newest First")
        sort_combo = ttk.Combobox(sort_box, textvariable=self.sort_var, values=["Newest First", "Brand / Label (A-Z)", "pHash", "Most Variants"], width=16, state="readonly", font=FONT_SM)
        sort_combo.pack(side="left")
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._load_gallery())

        # Thumbnail Size Dropdown
        size_box = tk.Frame(ctrl_bar, bg=panel_bg)
        size_box.pack(side="left", padx=(14, 0))
        tk.Label(size_box, text="Size:", font=FONT_BOLD, bg=panel_bg, fg=text_color).pack(side="left", padx=(0, 4))
        self.thumb_size_var = tk.StringVar(value="Compact (72px)")
        size_combo = ttk.Combobox(size_box, textvariable=self.thumb_size_var, values=["Compact (72px)", "Medium (120px)", "Large (180px)"], width=14, state="readonly", font=FONT_SM)
        size_combo.pack(side="left")
        size_combo.bind("<<ComboboxSelected>>", lambda e: self._load_gallery())

        # Sensitivity Slider
        slider_box = tk.Frame(ctrl_bar, bg=panel_bg)
        slider_box.pack(side="right")

        init_sens = getattr(self.vcm, "match_threshold", 6)
        def _get_scope_desc(v):
            return "Exact Clones" if v <= 4 else ("Balanced" if v <= 7 else ("Broad Catch" if v <= 10 else ("Wide Net" if v <= 14 else "Deep Dredge")))

        tk.Label(slider_box, text="Visual Match Scope:", font=FONT_BOLD, bg=panel_bg, fg=text_color).pack(side="left", padx=(0, 6))
        self.sens_lbl = tk.Label(slider_box, text=f"{init_sens} ({_get_scope_desc(init_sens)})", font=FONT_BOLD, bg=panel_bg, fg=accent_color)
        self.sens_lbl.pack(side="right", padx=(4, 0))

        self.sens_slider = tk.Scale(slider_box, from_=2, to=20, orient="horizontal", length=140,
                                    showvalue=False, bg=panel_bg, fg=text_color, highlightthickness=0,
                                    activebackground=accent_color, command=self._on_slider_change)
        self.sens_slider.set(init_sens)
        self.sens_slider.pack(side="right")

        # Scrollable Gallery Body
        body = tk.Frame(self, bg=bg_color)
        body.pack(fill="both", expand=True, side="top")

        self.canvas = tk.Canvas(body, bg=bg_color, highlightthickness=0)
        self.vsb = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.gallery_frame = tk.Frame(self.canvas, bg=bg_color)

        self.gallery_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.gallery_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        self.bind("<MouseWheel>", self._on_mousewheel)

    def _update_filter_btn_styles(self):
        cur_val = self.filter_var.get()
        accent_color = self.theme.get("accent", "#38bdf8")
        entry_bg = self.theme.get("entry_bg", "#262626")
        text_color = self.theme.get("text", "#ffffff")
        subtext = self.theme.get("subtext", "#888888")
        is_gold = str(self.theme.get("name", "")).startswith("⚡")

        for val, btn in getattr(self, "filter_btns", {}).items():
            if val == cur_val:
                btn.configure(
                    bg=accent_color,
                    fg="black" if is_gold else "white",
                    font=FONT_BOLD
                )
            else:
                btn.configure(
                    bg=entry_bg,
                    fg=subtext,
                    font=FONT_NORM
                )

    def _on_slider_change(self, val):
        v = int(val)
        desc = "Exact Clones" if v <= 4 else ("Balanced" if v <= 7 else ("Broad Catch" if v <= 10 else ("Wide Net" if v <= 14 else "Deep Dredge")))
        self.sens_lbl.config(text=f"{v} ({desc})")
        self.vcm.match_threshold = v
        if hasattr(self.master, "data_store"):
            self.master.data_store.set_setting("visual_match_threshold", v)

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _toggle_card_selection(self, entry_id):
        if entry_id in self.selected_card_ids:
            self.selected_card_ids.remove(entry_id)
            is_sel = False
        else:
            self.selected_card_ids.add(entry_id)
            is_sel = True

        self.merge_btn.config(text=f"🔗 Merge Selected ({len(self.selected_card_ids)})")
        
        # In-place UI update: no gallery reload!
        reg = self.card_registry.get(entry_id)
        if reg:
            reg["var"].set(is_sel)
            accent_color = self._t("accent", "#00d2ff")
            border_color = self._t("border", "#333333")
            reg["card"].config(highlightbackground=accent_color if is_sel else border_color,
                               bd=2 if is_sel else 1)

    def _load_gallery(self):
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()
        self.photo_refs.clear()
        self.card_registry.clear()

        bg_color = self._t("bg", "#121212")
        subtext_color = self._t("subtext", "#888888")

        f_val = self.filter_var.get()
        if f_val == "all":
            entries = self.vcm.get_all_entries()
        else:
            entries = self.vcm.list_entries(entry_type=f_val)

        # Apply Sort
        sort_mode = self.sort_var.get()
        if sort_mode == "Newest First":
            entries = sorted(entries, key=lambda e: str(e.get("created_at", "")), reverse=True)
        elif sort_mode == "Brand / Label (A-Z)":
            entries = sorted(entries, key=lambda e: str(e.get("label", "")).lower())
        elif sort_mode == "pHash":
            entries = sorted(entries, key=lambda e: str(e.get("hash", "")).lower())
        elif sort_mode == "Most Variants":
            entries = sorted(entries, key=lambda e: len(e.get("variants", [])) or len(e.get("hashes", [])) or 1, reverse=True)

        if not entries:
            msg_box = tk.Frame(self.gallery_frame, bg=bg_color, pady=60)
            msg_box.pack(fill="both", expand=True)
            tk.Label(msg_box, text="No visual fingerprints stored in this category.",
                     font=FONT_BOLD, bg=bg_color, fg=subtext_color).pack()
            tk.Label(msg_box, text="Right-click any listing in the Results Table to mark packaging as Benign or Counterfeit!",
                     font=FONT_SM, bg=bg_color, fg=subtext_color).pack(pady=4)
            return

        sz_val = self.thumb_size_var.get() if hasattr(self, "thumb_size_var") else "72"
        cols = 1 if "180" in sz_val else 2
        row = 0
        col = 0
        for entry in entries:
            card = self._create_card(self.gallery_frame, entry)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            col += 1
            if col >= cols:
                col = 0
                row += 1

        for c in range(cols):
            self.gallery_frame.grid_columnconfigure(c, weight=1)

    def _create_card(self, parent, entry):
        panel_bg = self._t("panel", "#1e1e1e")
        text_color = self._t("text", "#ffffff")
        subtext_color = self._t("subtext", "#888888")
        entry_bg = self._t("entry_bg", "#1a1a1a")
        accent_color = self._t("accent", "#00d2ff")
        danger_color = self._t("danger", "#ff4444")
        success_color = self._t("success", "#00cc66")
        accent_fg = self._t("btn_accent_fg", "black" if self.theme.get("name","").startswith("⚡") else "white")

        eid = entry.get("id")
        is_selected = eid in self.selected_card_ids

        card_bd_color = accent_color if is_selected else self._t("border", "#333333")
        card = tk.Frame(parent, bg=panel_bg, bd=2 if is_selected else 1, relief="solid",
                        highlightbackground=card_bd_color, highlightcolor=card_bd_color,
                        padx=10, pady=8)

        # Selection Checkbox
        sel_var = tk.BooleanVar(value=is_selected)
        chk = tk.Checkbutton(card, variable=sel_var, bg=panel_bg, selectcolor=accent_color,
                             activebackground=panel_bg, command=lambda: self._toggle_card_selection(eid))
        chk.pack(side="left", padx=(0, 6))

        self.card_registry[eid] = {"card": card, "var": sel_var, "chk": chk}

        # Thumbnail Sizing
        sz = 72
        if hasattr(self, "thumb_size_var"):
            v = self.thumb_size_var.get()
            if "120" in v: sz = 120
            elif "180" in v: sz = 180

        tp = entry.get("thumb_path", "")
        photo = None
        if tp and os.path.exists(tp):
            cache_key = (sz, tp)
            if cache_key in self._card_thumb_cache:
                photo = self._card_thumb_cache[cache_key]
                self.photo_refs.append(photo)
            else:
                try:
                    pimg = Image.open(tp).convert("RGBA")
                    pimg.thumbnail((sz, sz), Image.Resampling.BILINEAR)
                    photo = ImageTk.PhotoImage(pimg)
                    self._card_thumb_cache[cache_key] = photo
                    self.photo_refs.append(photo)
                except Exception:
                    pass

        img_lbl = tk.Label(card, image=photo if photo else "", text="[No Photo]" if not photo else "",
                           bg=entry_bg, width=sz, height=sz, cursor="hand2")
        img_lbl.pack(side="left", padx=(0, 10))
        img_lbl.bind("<Button-1>", lambda e: self._toggle_card_selection(eid))

        # Right Action Buttons
        btn_box = tk.Frame(card, bg=panel_bg)
        btn_box.pack(side="right", fill="y", padx=(6, 0))

        del_btn = tk.Button(btn_box, text="🗑 Delete", font=FONT_SM, bg=danger_color, fg="white",
                            relief="flat", padx=6, pady=2, cursor="hand2",
                            command=lambda: self._delete_entry(eid))
        del_btn.pack(anchor="ne", pady=(0, 4))

        variants_count = len(entry.get("variants", [])) or len(entry.get("hashes", [])) or 1
        if variants_count > 1:
            inspect_btn = tk.Button(btn_box, text=f"🔍 Cluster ({variants_count})", font=("Segoe UI", 8, "bold"),
                                    bg=panel_bg, fg=accent_color, relief="solid", bd=1, padx=4, pady=2, cursor="hand2",
                                    command=lambda: self._open_cluster_inspector(entry))
            inspect_btn.pack(anchor="e", pady=(0, 4))

        sweep_btn = tk.Button(btn_box, text="📸 Sweep", font=("Segoe UI", 8, "bold"),
                              bg=accent_color, fg=accent_fg,
                              relief="flat", padx=6, pady=3, cursor="hand2",
                              command=lambda: self._sweep_from_card(entry))
        sweep_btn.pack(anchor="se")

        # Center Info Box
        info = tk.Frame(card, bg=panel_bg)
        info.pack(side="left", fill="both", expand=True)

        is_benign = entry.get("type") == "benign"
        badge_color = success_color if is_benign else danger_color

        cluster_tag = f" • 🔗 {variants_count} VARIANTS" if variants_count > 1 else ""
        badge_text = ("🟢 BENIGN PACKAGING" if is_benign else "🔴 KNOWN COUNTERFEIT") + cluster_tag

        b_lbl = tk.Label(info, text=badge_text, font=("Segoe UI", 8, "bold"), bg=panel_bg, fg=badge_color)
        b_lbl.pack(anchor="w")

        title_lbl = tk.Label(info, text=entry.get("label", "Untitled Asset"), font=FONT_BOLD,
                             bg=panel_bg, fg=text_color, anchor="w", wraplength=260, justify="left")
        title_lbl.pack(anchor="w", pady=(2, 0))

        phash_str = entry.get("hash", "")[:16] + "..." if entry.get("hash") else "No Hash"
        details_txt = f"Hash: {phash_str} • Matches: {entry.get('match_count', 0)}"
        dt_lbl = tk.Label(info, text=details_txt, font=FONT_SM, bg=panel_bg, fg=subtext_color, anchor="w")
        dt_lbl.pack(anchor="w")

        if entry.get("created_at"):
            cr_lbl = tk.Label(info, text=f"Added: {entry.get('created_at')}", font=FONT_SM, bg=panel_bg, fg=subtext_color)
            cr_lbl.pack(anchor="w")

        return card

    def _open_cluster_inspector(self, entry):
        """Open Cluster Inspector Modal to view and manage all variants in a cluster."""
        win = tk.Toplevel(self)
        win.withdraw()
        win.title(f"🔍 Cluster Inspector: {entry.get('label', 'Multi-Hash Cluster')}")
        win.configure(bg=self._t("bg", "#121212"))
        win.transient(self)
        win.grab_set()

        if hasattr(self.master, "_apply_dark_titlebar"):
            self.master._apply_dark_titlebar(win)
        self._center_window(680, 520, target_win=win)

        p_bg = self._t("panel", "#1e1e1e")
        txt_c = self._t("text", "#ffffff")
        acc_c = self._t("accent", "#00d2ff")

        top_f = tk.Frame(win, bg=p_bg, padx=14, pady=10)
        top_f.pack(fill="x")
        tk.Label(top_f, text=f"🔗 {entry.get('label')}", font=FONT_TITLE, bg=p_bg, fg=acc_c).pack(anchor="w")
        
        variants = entry.get("variants", [])
        tk.Label(top_f, text=f"{len(variants)} Photo Variants Active in Parallel", font=FONT_SM, bg=p_bg, fg=self._t("subtext", "#888888")).pack(anchor="w")

        # Rename Cluster
        rename_f = tk.Frame(top_f, bg=p_bg)
        rename_f.pack(fill="x", pady=(6, 0))
        tk.Label(rename_f, text="Cluster Label:", font=FONT_BOLD, bg=p_bg, fg=txt_c).pack(side="left")
        name_var = tk.StringVar(value=entry.get("label", ""))
        name_e = tk.Entry(rename_f, textvariable=name_var, font=FONT_NORM, bg=self._t("entry_bg", "#1a1a1a"), fg=txt_c, insertbackground=txt_c, width=32)
        name_e.pack(side="left", padx=6)
        
        def _save_label():
            entry["label"] = name_var.get().strip() or entry["label"]
            self.vcm._save_catalog()
            self._load_gallery()
            messagebox.showinfo("Saved", "Cluster label updated!", parent=win)

        tk.Button(rename_f, text="💾 Save", font=FONT_SM, bg=acc_c, fg="black", relief="flat", padx=6, pady=2, command=_save_label).pack(side="left")

        # Variants Grid
        canv = tk.Canvas(win, bg=self._t("bg", "#121212"), highlightthickness=0)
        sb = ttk.Scrollbar(win, orient="vertical", command=canv.yview)
        grid_f = tk.Frame(canv, bg=self._t("bg", "#121212"), padx=12, pady=12)
        grid_f.bind("<Configure>", lambda e: canv.configure(scrollregion=canv.bbox("all")))
        canv.create_window((0, 0), window=grid_f, anchor="nw")
        canv.configure(yscrollcommand=sb.set)
        canv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def _on_wheel(e):
            try:
                canv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass
        canv.bind_all("<MouseWheel>", _on_wheel)
        win.bind("<Destroy>", lambda e: canv.unbind_all("<MouseWheel>"))

        col = 0
        row = 0
        for i, v in enumerate(variants):
            vf = tk.Frame(grid_f, bg=p_bg, bd=1, relief="solid", padx=8, pady=8)
            vf.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            vp = v.get("thumb_path", "")
            photo = None
            if vp and os.path.exists(vp):
                try:
                    pimg = Image.open(vp).convert("RGBA")
                    pimg.thumbnail((80, 80), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(pimg)
                    self.photo_refs.append(photo)
                except Exception:
                    pass

            tk.Label(vf, image=photo if photo else "", text="[No Photo]" if not photo else "", bg=self._t("entry_bg", "#1a1a1a"), width=80, height=80).pack()
            tk.Label(vf, text=f"Variant #{i+1}", font=FONT_BOLD, bg=p_bg, fg=txt_c).pack(pady=(4, 0))
            tk.Label(vf, text=v.get("hash", "")[:12] + "...", font=FONT_SM, bg=p_bg, fg=self._t("subtext", "#888888")).pack()

            # Delete variant button (if > 1 variant remaining)
            def _make_del_v(var_hash=v.get("hash")):
                def _do_del_v():
                    if len(entry.get("variants", [])) <= 1:
                        messagebox.showwarning("Cannot Delete", "A cluster must retain at least one photo variant.", parent=win)
                        return
                    entry["variants"] = [x for x in entry.get("variants", []) if x.get("hash") != var_hash]
                    entry["hashes"] = [x.get("hash") for x in entry["variants"] if x.get("hash")]
                    if entry.get("hash") == var_hash and entry["hashes"]:
                        entry["hash"] = entry["hashes"][0]
                    self.vcm._save_catalog()
                    win.destroy()
                    self._load_gallery()
                    self._open_cluster_inspector(entry)
                return _do_del_v

            tk.Button(vf, text="🗑 Remove", font=FONT_SM, bg=self._t("danger", "#ff4444"), fg="white", relief="flat", padx=4, pady=1, command=_make_del_v()).pack(pady=(4, 0))

            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _merge_selected_cards(self):
        if len(self.selected_card_ids) < 2:
            messagebox.showinfo("Select Items", "Please check at least 2 visual fingerprints to merge them into a unified Multi-Hash Threat Cluster.")
            return

        t = self.theme
        win = tk.Toplevel(self)
        win.withdraw()
        win.title("Merge into Multi-Hash Threat Cluster")
        win.configure(bg=self._t("bg", "#121212"))
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        if hasattr(self.master, "_apply_dark_titlebar"):
            self.master._apply_dark_titlebar(win)
        self._center_window(500, 260, target_win=win)

        selected_entries = [e for e in self.vcm.get_all_entries() if e.get("id") in self.selected_card_ids]
        suggested_label = selected_entries[0].get("label", "Threat Cluster")

        tk.Label(win, text="🔗 Unified Threat Cluster Name:", font=FONT_BOLD,
                 bg=self._t("bg", "#121212"), fg=self._t("text", "#ffffff")).pack(anchor="w", padx=16, pady=(16, 4))

        name_ent = tk.Entry(win, font=FONT_NORM, bg=self._t("entry_bg", "#1a1a1a"),
                            fg=self._t("text", "#ffffff"), insertbackground=self._t("text", "#ffffff"))
        name_ent.pack(fill="x", padx=16, pady=4)
        name_ent.insert(0, suggested_label)
        name_ent.focus_set()

        tk.Label(win, text=f"This will bundle {len(self.selected_card_ids)} photo fingerprints into 1 cluster.\nAny listing matching ANY of these angles/variants will trigger this threat!",
                 font=FONT_SM, bg=self._t("bg", "#121212"), fg=self._t("subtext", "#888888"), justify="left").pack(anchor="w", padx=16, pady=10)

        def _do_merge():
            cluster_name = name_ent.get().strip() or "Unified Threat Cluster"
            res = self.vcm.merge_entries(list(self.selected_card_ids), unified_label=cluster_name)
            win.destroy()
            self.selected_card_ids.clear()
            self.merge_btn.config(text="🔗 Merge Selected (0)")
            self._load_gallery()
            if self.on_update:
                self.on_update()
            messagebox.showinfo("Cluster Merged", f"Successfully created Multi-Hash Threat Cluster:\n'{cluster_name}'\n\nAll variant hashes are now active in parallel!")

        btn_box = tk.Frame(win, bg=self._t("bg", "#121212"))
        btn_box.pack(fill="x", padx=16, pady=14)
        tk.Button(btn_box, text="🔗 Merge Cluster", font=FONT_BOLD, bg=self._t("accent", "#00d2ff"),
                  fg="black" if self.theme.get("name","").startswith("⚡") else "white",
                  relief="flat", padx=12, pady=4, command=_do_merge).pack(side="right")
        tk.Button(btn_box, text="Cancel", font=FONT_NORM, bg=self._t("panel", "#1e1e1e"),
                  fg=self._t("subtext", "#888888"), relief="flat", padx=8, pady=4, command=win.destroy).pack(side="right", padx=6)

    def _sweep_from_card(self, entry):
        source = entry.get("source_url") or entry.get("thumb_path")
        if not source:
            messagebox.showwarning("Warning", "No source image available for this entry.")
            return

        label = entry.get("label", "Visual Search")
        if hasattr(self.master, "_reverse_visual_search_from_url"):
            self.master._reverse_visual_search_from_url(source, label=label)

    def _delete_entry(self, entry_id):
        if messagebox.askyesno("Confirm Delete", "Remove this visual threat asset / cluster from your catalog?", parent=self):
            if self.vcm.delete_entry(entry_id):
                if entry_id in self.selected_card_ids:
                    self.selected_card_ids.remove(entry_id)
                self.merge_btn.config(text=f"🔗 Merge Selected ({len(self.selected_card_ids)})")
                self._load_gallery()
                if self.on_update:
                    self.on_update()

    def _rescan_session_matches(self):
        if hasattr(self.master, "_rescan_visual_matches"):
            self.master._rescan_visual_matches()

    def _export_visual_pack(self):
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Export Visual Threat Catalog",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if dest:
            if self.vcm.export_catalog(dest):
                messagebox.showinfo("Export Successful", f"Visual Threat Catalog exported to:\n{dest}")

    def _import_visual_pack(self):
        src = filedialog.askopenfilename(
            parent=self,
            title="Import Visual Threat Catalog",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if src:
            imported = self.vcm.import_catalog(src)
            self._load_gallery()
            if self.on_update:
                self.on_update()
            messagebox.showinfo("Import Complete", f"Successfully imported {imported} visual fingerprint entries!")

    def _add_from_file(self):
        filepath = filedialog.askopenfilename(
            parent=self,
            title="Select Packaging or Counterfeit Photo",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        self._show_add_dialog(filepath=filepath)

    def _add_from_url(self):
        win = tk.Toplevel(self)
        win.withdraw()
        win.title("Add Photo from Web URL")
        win.configure(bg=self._t("bg", "#121212"))
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        if hasattr(self.master, "_apply_dark_titlebar"):
            self.master._apply_dark_titlebar(win)
        self._center_window(480, 160, target_win=win)

        tk.Label(win, text="Direct Image URL (JPG/PNG/WEBP):", font=FONT_BOLD,
                 bg=self._t("bg", "#121212"), fg=self._t("text", "#ffffff")).pack(anchor="w", padx=16, pady=(16, 4))

        url_ent = tk.Entry(win, font=FONT_NORM, bg=self._t("entry_bg", "#1a1a1a"),
                           fg=self._t("text", "#ffffff"), insertbackground=self._t("text", "#ffffff"))
        url_ent.pack(fill="x", padx=16, pady=4)
        url_ent.focus_set()

        def _proceed():
            u = url_ent.get().strip()
            if not u:
                return
            win.destroy()
            self._show_add_dialog(url=u)

        btn_box = tk.Frame(win, bg=self._t("bg", "#121212"))
        btn_box.pack(fill="x", padx=16, pady=10)
        tk.Button(btn_box, text="Next ➔", font=FONT_BOLD, bg=self._t("accent", "#00d2ff"),
                  fg="black" if self.theme.get("name","").startswith("⚡") else "white",
                  relief="flat", padx=10, pady=4, command=_proceed).pack(side="right")
        tk.Button(btn_box, text="Cancel", font=FONT_NORM, bg=self._t("panel", "#1e1e1e"),
                  fg=self._t("subtext", "#888888"), relief="flat", padx=8, pady=4, command=win.destroy).pack(side="right", padx=6)

    def _show_add_dialog(self, filepath=None, url=None):
        dlg = tk.Toplevel(self)
        dlg.withdraw()
        dlg.title("Add Visual Asset to Catalog")
        dlg.configure(bg=self._t("bg", "#121212"))
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        if hasattr(self.master, "_apply_dark_titlebar"):
            self.master._apply_dark_titlebar(dlg)
        self._center_window(460, 340, target_win=dlg)

        # Asset Type Radio
        type_var = tk.StringVar(value="benign")
        tk.Label(dlg, text="Asset Classification:", font=FONT_BOLD,
                 bg=self._t("bg", "#121212"), fg=self._t("text", "#ffffff")).pack(anchor="w", padx=16, pady=(14, 4))
        type_frame = tk.Frame(dlg, bg=self._t("bg", "#121212"))
        type_frame.pack(fill="x", padx=16)

        tk.Radiobutton(type_frame, text="🟢 Known Benign Packaging (Filter Out)", value="benign", variable=type_var,
                       font=FONT_NORM, bg=self._t("bg", "#121212"), fg=self._t("text", "#ffffff"),
                       selectcolor=self._t("accent", "#f59e0b")).pack(anchor="w")
        tk.Radiobutton(type_frame, text="🔴 Known Counterfeit Photo (High Threat)", value="counterfeit", variable=type_var,
                       font=FONT_NORM, bg=self._t("bg", "#121212"), fg=self._t("text", "#ffffff"),
                       selectcolor=self._t("accent", "#f59e0b")).pack(anchor="w")

        # Label Field
        tk.Label(dlg, text="Packaging / Asset Label:", font=FONT_BOLD,
                 bg=self._t("bg", "#121212"), fg=self._t("text", "#ffffff")).pack(anchor="w", padx=16, pady=(10, 4))
        lbl_ent = tk.Entry(dlg, font=FONT_NORM, bg=self._t("entry_bg", "#1a1a1a"),
                           fg=self._t("text", "#ffffff"), insertbackground=self._t("text", "#ffffff"))
        lbl_ent.pack(fill="x", padx=16)
        lbl_ent.insert(0, "Genuine Retail Box" if type_var.get() == "benign" else "Counterfeit Bubble Packaging")

        # Notes Field
        tk.Label(dlg, text="Analyst Notes:", font=FONT_BOLD,
                 bg=self._t("bg", "#121212"), fg=self._t("text", "#ffffff")).pack(anchor="w", padx=16, pady=(10, 4))
        notes_ent = tk.Entry(dlg, font=FONT_NORM, bg=self._t("entry_bg", "#1a1a1a"),
                             fg=self._t("text", "#ffffff"), insertbackground=self._t("text", "#ffffff"))
        notes_ent.pack(fill="x", padx=16)

        def _do_add():
            l = lbl_ent.get().strip() or "Visual Asset"
            t = type_var.get()
            n = notes_ent.get().strip()

            img = None
            if filepath:
                try:
                    img = Image.open(filepath).convert("RGBA")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image file: {e}")
                    return
            elif url:
                try:
                    import requests
                    resp = requests.get(url, timeout=10)
                    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to download image URL: {e}")
                    return

            if img:
                res = self.vcm.add_entry(img, entry_type=t, label=l, notes=n, source_url=url or filepath)
                dlg.destroy()
                self._load_gallery()
                if self.on_update:
                    self.on_update()
                messagebox.showinfo("Saved", f"Successfully stored visual fingerprint: '{l}'!")

        btn_box = tk.Frame(dlg, bg=self._t("bg", "#121212"))
        btn_box.pack(fill="x", padx=16, pady=16)
        tk.Button(btn_box, text="💾 Save Asset", font=FONT_BOLD, bg=self._t("accent", "#00d2ff"),
                  fg="black" if self.theme.get("name","").startswith("⚡") else "white",
                  relief="flat", padx=12, pady=4, command=_do_add).pack(side="right")
        tk.Button(btn_box, text="Cancel", font=FONT_NORM, bg=self._t("panel", "#1e1e1e"),
                  fg=self._t("subtext", "#888888"), relief="flat", padx=8, pady=4, command=dlg.destroy).pack(side="right", padx=6)

    def _on_purge_all(self):
        """Purge all image entries from the visual catalog with confirmation."""
        cur_filter = self.filter_var.get()
        filter_desc = "ALL visual catalog signatures (Benign & Counterfeit)" if cur_filter == "all" else f"all {cur_filter} image signatures"
        entries = self.vcm.list_entries(cur_filter)
        if not entries:
            messagebox.showinfo("Catalog Empty", "There are no image entries in this view to purge.", parent=self)
            return

        if not messagebox.askyesno(
            "Purge All Images",
            f"Are you sure you want to permanently delete {len(entries)} image signature(s) ({filter_desc}) and wipe all cached thumbnails from disk?\n\nThis action cannot be undone.",
            icon="warning",
            parent=self
        ):
            return

        purged_count = self.vcm.purge_all_entries(cur_filter)
        self.selected_ids.clear()
        self._card_thumb_cache.clear()
        self._load_gallery()
        if self.on_update:
            try:
                self.on_update()
            except Exception:
                pass
        messagebox.showinfo("Purge Complete", f"Successfully purged {purged_count} image signature(s) from the Visual Catalog.", parent=self)
