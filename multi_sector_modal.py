"""
Multi-Sector Target Dispatcher Modal for Apollo Brand Intelligence Suite 2.1.
Enables high-speed multi-marketplace targeting across Print-on-Demand (POD),
Global Wholesale/E-Commerce, and Gated Social sectors in a single unified operation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Any, Callable, Optional

FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_SM   = ("Segoe UI", 8)
FONT_HEAD = ("Segoe UI", 11, "bold")
FONT_TITLE= ("Segoe UI", 12, "bold")

SECTOR_TAXONOMY = {
    "pod": {
        "title": "👕 Print-on-Demand (POD) Matrix",
        "description": "High-yield commercial apparel, stickers, drinkware, and wall art.",
        "platforms": [
            ("TeePublic.com", "👕 TeePublic.com", "High-Volume Apparel, Hoodies, Stickers", True),
            ("Redbubble.com", "🎨 Redbubble.com", "Global Artist Marketplace (50+ Lines)", True),
            ("Printerval.com", "👕 Printerval.com", "High-Yield Creator Merch & Apparel", True),
            ("Spreadshirt.com", "🌿 Spreadshirt.com", "European & Global POD Catalog", True),
            ("Zazzle.com", "🎨 Zazzle.com", "Customizable Merch, Canvas, Phone Cases", True),
            ("CafePress.com", "☕ CafePress.com", "Legacy Commercial Designs & Gifts", False),
            ("Threadless.com", "🧵 Threadless.com", "Independent Artist Shops & Apparel", False),
            ("TeeSpring (Spring)", "🌱 TeeSpring (Spring)", "Social Media Creator Stores", False),
            ("Fine Art America", "🖼 Fine Art America", "High-Ticket Canvas, Metal Art & Pixels", False)
        ]
    },
    "ecom": {
        "title": "🌐 Global E-Commerce & Wholesale",
        "description": "Direct consumer listings, counterfeit parts, and drop-ship supply hubs.",
        "platforms": [
            ("eBay.com", "🛒 eBay.com", "North America & Global Reseller Listings", True),
            ("AliExpress.com", "🌐 AliExpress.com", "Factory-Direct Wholesale & Supply Hubs", True),
            ("Wish.com", "🌠 Wish.com", "Cross-Border Discount Merch", False)
        ]
    },
    "gated": {
        "title": "🔒 Session-Gated & Regional Commerce",
        "description": "Perimeter-protected social commerce and international regional hubs.",
        "platforms": [
            ("TikTok Shop", "🎵 TikTok Shop", "Fast-Moving Viral Social Commerce (US)", False),
            ("Temu.com", "🟠 Temu.com", "Direct Manufacturer & Wholesale Malls", False),
            ("Vinted", "👗 Vinted", "UK, France, Germany, Spain, US Apparel", False),
            ("Mercado Libre", "🛍 Mercado Libre", "Latin America Cross-Border Commerce", False),
            ("ManoMano", "🧰 ManoMano", "European Industrial, Hardware & DIY", False)
        ]
    }
}


class MultiSectorModal(tk.Toplevel):
    """Modern modal dialog allowing multi-marketplace job dispatching with one click."""

    def __init__(
        self,
        parent,
        theme: dict,
        initial_query: str = "",
        initial_excludes: str = "",
        initial_condition: str = "all",
        on_enqueue_callback: Optional[Callable[[str, List[str], str, List[str]], None]] = None
    ):
        super().__init__(parent)
        self.parent = parent
        self.theme = theme
        self.on_enqueue = on_enqueue_callback

        self.title("🌐 Multi-Sector Target Dispatcher")
        self.geometry("960x680")
        self.minsize(880, 560)
        self.configure(bg=self.theme["bg"])
        self.transient(parent)
        self.grab_set()

        if hasattr(parent, "_apply_dark_titlebar"):
            parent._apply_dark_titlebar(self)
        if hasattr(parent, "_load_app_icon"):
            parent._load_app_icon(self)
        if hasattr(parent, "_center_window"):
            parent._center_window(self, 960, 680)

        self.platform_vars: Dict[str, tk.BooleanVar] = {}
        self.initial_query = initial_query
        self.initial_excludes = initial_excludes
        self.initial_condition = initial_condition

        self._build_ui()
        self._apply_preset("top_pod")

    def _build_ui(self):
        t = self.theme

        # ── Top Header Banner ──
        head_frame = tk.Frame(
            self,
            bg=t["panel"],
            padx=20,
            pady=12,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        head_frame.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(
            head_frame,
            text="🌐 Multi-Sector Target Dispatcher",
            font=FONT_TITLE,
            bg=t["panel"],
            fg=t["accent"]
        ).pack(anchor="w")

        tk.Label(
            head_frame,
            text="Simultaneously enqueue verified trademark & brand queries across entire sectors without repetitive manual switching.",
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["subtext"]
        ).pack(anchor="w", pady=(2, 0))

        # ── Target Configuration Panel ──
        config_frame = tk.LabelFrame(
            self,
            text=" 🎯 Target Brand & Search Configuration ",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["accent"],
            padx=14,
            pady=10,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        config_frame.pack(fill="x", padx=16, pady=(0, 8))

        row1 = tk.Frame(config_frame, bg=t["panel"])
        row1.pack(fill="x")

        tk.Label(row1, text="Brand / Query:", font=FONT_BOLD, bg=t["panel"], fg=t["text"]).pack(side="left", padx=(0, 6))
        self.brand_entry = tk.Entry(
            row1,
            font=FONT_NORM,
            bg=t.get("entry_bg", "#05071F"),
            fg=t["text"],
            insertbackground=t["accent"],
            width=28
        )
        self.brand_entry.insert(0, self.initial_query)
        self.brand_entry.pack(side="left", padx=(0, 16))

        tk.Label(row1, text="Exclusions:", font=FONT_BOLD, bg=t["panel"], fg=t["text"]).pack(side="left", padx=(0, 6))
        self.excludes_entry = tk.Entry(
            row1,
            font=FONT_NORM,
            bg=t.get("entry_bg", "#05071F"),
            fg=t["text"],
            insertbackground=t["accent"],
            width=28
        )
        self.excludes_entry.insert(0, self.initial_excludes)
        self.excludes_entry.pack(side="left", padx=(0, 16), fill="x", expand=True)

        tk.Label(row1, text="Condition:", font=FONT_BOLD, bg=t["panel"], fg=t["text"]).pack(side="left", padx=(0, 6))
        self.cond_var = tk.StringVar(value=self.initial_condition.capitalize() if self.initial_condition != "all" else "All")
        self.cond_combo = ttk.Combobox(
            row1,
            textvariable=self.cond_var,
            values=["All", "New", "Used"],
            state="readonly",
            width=8,
            font=FONT_SM
        )
        self.cond_combo.pack(side="left")

        # ── Sector Presets Toolbar ──
        preset_frame = tk.Frame(self, bg=t["bg"])
        preset_frame.pack(fill="x", padx=16, pady=(0, 6))

        tk.Label(preset_frame, text="⚡ Quick Presets:", font=FONT_BOLD, bg=t["bg"], fg=t["subtext"]).pack(side="left", padx=(0, 8))

        presets = [
            ("👕 Top PODs", "top_pod", t["accent"]),
            ("🌐 Core E-Com", "core_ecom", t.get("accent2", "#38BDF8")),
            ("🔒 Gated & Social", "gated_social", t["warning"]),
            ("⚡ Top 5 Enforcement", "top_5", t["success"]),
            ("🌟 Select All", "all", t["text"]),
            ("🧹 Clear All", "clear", t["subtext"])
        ]

        for lbl, key, col in presets:
            btn = tk.Button(
                preset_frame,
                text=lbl,
                font=FONT_SM,
                bg=t["panel"],
                fg=col,
                activebackground=t["accent"],
                activeforeground=t["bg"],
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda k=key: self._apply_preset(k)
            )
            btn.pack(side="left", padx=3)

        # ── Scrollable Sectors Grid Container ──
        sectors_container = tk.Frame(self, bg=t["bg"])
        sectors_container.pack(fill="both", expand=True, padx=16, pady=4)

        canvas = tk.Canvas(sectors_container, bg=t["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(sectors_container, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=t["bg"])

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_win = canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set, yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_win, width=event.width - 6)

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
        scroll_content.bind("<MouseWheel>", _on_mousewheel)
        self.bind("<MouseWheel>", _on_mousewheel)

        # Render Sectors
        for sector_id, sec in SECTOR_TAXONOMY.items():
            s_frame = tk.LabelFrame(
                scroll_content,
                text=f" {sec['title']} ",
                font=FONT_BOLD,
                bg=t["panel"],
                fg=t["accent"],
                padx=12,
                pady=8,
                highlightbackground=t.get("border", "#333"),
                highlightthickness=1
            )
            s_frame.pack(fill="x", pady=5)

            tk.Label(
                s_frame,
                text=sec["description"],
                font=FONT_SM,
                bg=t["panel"],
                fg=t["subtext"]
            ).pack(anchor="w", pady=(0, 6))

            grid_f = tk.Frame(s_frame, bg=t["panel"])
            grid_f.pack(fill="x")

            for idx, (code_name, display_name, subtitle, default_on) in enumerate(sec["platforms"]):
                row = idx // 3
                col = idx % 3

                var = tk.BooleanVar(value=default_on)
                self.platform_vars[code_name] = var

                cell = tk.Frame(grid_f, bg=t["panel"], padx=6, pady=4)
                cell.grid(row=row, column=col, sticky="w", padx=4, pady=2)

                cb = tk.Checkbutton(
                    cell,
                    text=display_name,
                    variable=var,
                    font=FONT_BOLD,
                    bg=t["panel"],
                    fg=t["text"],
                    activebackground=t["panel"],
                    activeforeground=t["accent"],
                    selectcolor=t.get("entry_bg", "#05071F"),
                    command=self._update_selected_count
                )
                cb.pack(anchor="w")

                tk.Label(
                    cell,
                    text=subtitle,
                    font=FONT_SM,
                    bg=t["panel"],
                    fg=t["subtext"]
                ).pack(anchor="w", padx=(20, 0))

        _bind_mousewheel_recursive(scroll_content)

        # ── Bottom Action Footer ──
        foot_frame = tk.Frame(
            self,
            bg=t["panel"],
            padx=16,
            pady=10,
            highlightbackground=t.get("border", "#333"),
            highlightthickness=1
        )
        foot_frame.pack(fill="x", padx=16, pady=(6, 12))

        self.count_lbl = tk.Label(
            foot_frame,
            text="Selected: 0 Marketplaces",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["accent"]
        )
        self.count_lbl.pack(side="left")

        btn_cancel = tk.Button(
            foot_frame,
            text="Cancel",
            font=FONT_NORM,
            bg=t["bg"],
            fg=t["subtext"],
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_dispatch = tk.Button(
            foot_frame,
            text="🚀 Enqueue Selected Platforms",
            font=FONT_BOLD,
            bg=t["accent"],
            fg=t.get("btn_accent_fg", "#000000"),
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._on_dispatch_click
        )
        self.btn_dispatch.pack(side="right")

        self._update_selected_count()

    def _apply_preset(self, preset_key: str):
        """Apply preset selections across checkboxes."""
        for k, var in self.platform_vars.items():
            if preset_key == "clear":
                var.set(False)
            elif preset_key == "all":
                var.set(True)
            elif preset_key == "top_pod":
                var.set(k in ("TeePublic.com", "Redbubble.com", "Printerval.com", "Spreadshirt.com", "Zazzle.com"))
            elif preset_key == "core_ecom":
                var.set(k in ("eBay.com", "AliExpress.com"))
            elif preset_key == "gated_social":
                var.set(k in ("TikTok Shop", "Temu.com", "Vinted", "Mercado Libre"))
            elif preset_key == "top_5":
                var.set(k in ("eBay.com", "TeePublic.com", "Redbubble.com", "Printerval.com", "AliExpress.com"))

        self._update_selected_count()

    def _update_selected_count(self):
        """Update label showing how many platforms are selected."""
        selected = [k for k, v in self.platform_vars.items() if v.get()]
        count = len(selected)
        self.count_lbl.config(text=f"Selected: {count} Marketplace(s)")
        if hasattr(self, "btn_dispatch"):
            self.btn_dispatch.config(
                text=f"🚀 Enqueue {count} Selected Platform{'s' if count != 1 else ''}"
            )

    def _on_dispatch_click(self):
        """Execute dispatch callback to enqueue all checked marketplace jobs."""
        brand = self.brand_entry.get().strip()
        if not brand:
            messagebox.showwarning("Multi-Sector Dispatch", "Please enter a Brand or Target Query term.")
            self.brand_entry.focus_set()
            return

        excludes_raw = self.excludes_entry.get().strip()
        excludes = [x.strip() for x in excludes_raw.split(",") if x.strip()]
        condition = self.cond_var.get().lower()

        selected_platforms = [k for k, v in self.platform_vars.items() if v.get()]
        if not selected_platforms:
            messagebox.showwarning("Multi-Sector Dispatch", "Please select at least one marketplace platform to sweep.")
            return

        if self.on_enqueue:
            self.on_enqueue(brand, excludes, condition, selected_platforms)

        self.destroy()
