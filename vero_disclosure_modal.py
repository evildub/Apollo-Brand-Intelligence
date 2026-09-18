"""
vero_disclosure_modal.py
Interactive VeRO & eBay Seller Disclosure Intelligence Modal for Apollo.

Allows analysts and CSMs to:
1. Open VeRO seller tracking PDF reports or paste raw disclosure text lines.
2. Automatically parse handles, contact names, Chinese & international addresses, postal codes, and countries.
3. Review and inspect parsed records in an interactive table with instant origin analytics.
4. Push disclosures directly into the permanent Enforcement Registry (`data_store.py`).
5. Add seller handles straight to Apollo's store scan queue without losing existing queue items.
6. Export Genesis-ready Excel workbooks and CSV spreadsheets.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import List, Dict, Optional, Any

from vero_pdf_parser import (
    parse_vero_line,
    parse_vero_text,
    parse_vero_pdf,
    push_to_enforcement_registry,
    export_to_excel,
    export_to_csv,
    PYPDF_AVAILABLE
)

FONT_FAMILY = "Segoe UI"
FONT_XS     = (FONT_FAMILY, 8)
FONT_SM     = (FONT_FAMILY, 9)
FONT_MED    = (FONT_FAMILY, 10)
FONT_BOLD   = (FONT_FAMILY, 10, "bold")
FONT_TITLE  = (FONT_FAMILY, 12, "bold")
FONT_HEAD   = (FONT_FAMILY, 14, "bold")


class VeroDisclosureModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.t = getattr(parent, "theme", {
            "bg": "#000227", "panel": "#0A0E36", "accent": "#38BDF8",
            "accent2": "#347BB7", "success": "#10B981", "warning": "#F59E0B",
            "danger": "#EF4444", "subtext": "#94A3B8"
        })
        self.parsed_records: List[Dict[str, str]] = []

        self.title("📄 VeRO & eBay Seller Disclosure Intelligence Harvester")
        self.geometry("1100x740")
        self.configure(bg=self.t["bg"])
        self.minsize(920, 600)
        
        if hasattr(self.parent, "_apply_dark_titlebar"):
            self.parent._apply_dark_titlebar(self)

        self._build_ui()

        if hasattr(self.parent, "_center_window"):
            self.parent._center_window(self, 1100, 740)
        
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self):
        t = self.t
        pad_f = tk.Frame(self, bg=t["bg"], padx=14, pady=12)
        pad_f.pack(fill="both", expand=True)

        # ── 1. Header Banner ──────────────────────────────────────────────────
        head_f = tk.Frame(pad_f, bg=t["bg"])
        head_f.pack(fill="x", pady=(0, 10))

        title_lbl = tk.Label(
            head_f,
            text="📄 VeRO & eBay Seller Disclosure Intelligence Harvester",
            font=FONT_HEAD,
            bg=t["bg"],
            fg=t["accent"]
        )
        title_lbl.pack(side="left")

        sub_lbl = tk.Label(
            head_f,
            text="Decompose VeRO PDF seller tracking lines into structured addresses, sync with Enforcement Registry & Genesis",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["subtext"]
        )
        sub_lbl.pack(side="left", padx=12, pady=(4, 0))

        # ── 2. Top Toolbar (Actions & File Loading) ────────────────────────────
        tool_f = tk.Frame(pad_f, bg=t["panel"], padx=10, pady=8, highlightthickness=1, highlightbackground=t["accent2"])
        tool_f.pack(fill="x", pady=(0, 10))

        pdf_btn = tk.Button(
            tool_f,
            text="📁 Open VeRO PDF...",
            font=FONT_BOLD,
            bg=t["accent2"],
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._on_open_pdf
        )
        pdf_btn.pack(side="left", padx=(0, 6))

        paste_btn = tk.Button(
            tool_f,
            text="📋 Paste Clipboard",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["accent"],
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._on_paste_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 6))

        parse_btn = tk.Button(
            tool_f,
            text="⚡ Parse Text Box",
            font=FONT_BOLD,
            bg=t["success"],
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._on_parse_text_box
        )
        parse_btn.pack(side="left", padx=(0, 6))

        clear_btn = tk.Button(
            tool_f,
            text="🧹 Clear",
            font=FONT_SM,
            bg=t["bg"],
            fg=t["subtext"],
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._on_clear_all
        )
        clear_btn.pack(side="left", padx=(0, 6))

        # Marketplace selector
        tk.Label(tool_f, text="Marketplace:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(10, 4))
        self.mp_var = tk.StringVar(value="eBay")
        self.mp_combo = ttk.Combobox(
            tool_f,
            textvariable=self.mp_var,
            values=["eBay", "AliExpress", "TikTok Shop", "Vinted", "Mercado Libre", "Amazon", "Temu", "Wish", "Etsy", "Redbubble", "Printerval"],
            state="readonly",
            width=13,
            font=FONT_SM
        )
        self.mp_combo.pack(side="left", padx=(0, 6))

        self.lbl_pdf_hint = tk.Label(
            tool_f,
            text="PDF Engine: Active (pypdf)" if PYPDF_AVAILABLE else "⚠ PDF Engine: Missing pypdf (Paste text active)",
            font=FONT_XS,
            bg=t["panel"],
            fg=t["success"] if PYPDF_AVAILABLE else t["warning"]
        )
        self.lbl_pdf_hint.pack(side="right", padx=6)

        # ── 3. Split Text Input & Table ───────────────────────────────────────
        split_pane = tk.PanedWindow(pad_f, orient="vertical", bg=t["bg"], sashrelief="flat", sashwidth=6)
        split_pane.pack(fill="both", expand=True, pady=(0, 8))

        # Upper Frame: Text Input Area (Collapsible feel)
        input_frame = tk.Frame(split_pane, bg=t["panel"], padx=8, pady=6)
        split_pane.add(input_frame, minsize=110, height=130)

        in_lbl = tk.Label(
            input_frame,
            text="Raw Disclosure Text Input (Paste one seller line per row or tab-delimited Genesis lines):",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"]
        )
        in_lbl.pack(anchor="w", pady=(0, 4))

        self.txt_input = tk.Text(
            input_frame,
            height=4,
            font=("Consolas", 9),
            bg="#020617",
            fg="#F8FAFC",
            insertbackground=t["accent"],
            selectbackground=t["accent2"],
            selectforeground="#FFFFFF",
            relief="flat",
            wrap="none"
        )
        txt_scroll_y = ttk.Scrollbar(input_frame, orient="vertical", command=self.txt_input.yview)
        self.txt_input.configure(yscrollcommand=txt_scroll_y.set)
        
        self.txt_input.pack(side="left", fill="both", expand=True)
        txt_scroll_y.pack(side="right", fill="y")

        placeholder_sample = (
            "trdracing / xu jie xu yu xiu qu yong fu lu 35 2, guang zhou, 510000, CN\n"
            "yu1587_21 / zhao kun yu baiyunqujiefangbeilu1461 1469haoshouceng, shengyipijuchengdangkouhaoN22 1fang, guang zhou, 510000, CN"
        )
        self.txt_input.insert("1.0", placeholder_sample)

        # Lower Frame: Structured Table
        table_frame = tk.Frame(split_pane, bg=t["panel"], padx=8, pady=6)
        split_pane.add(table_frame, minsize=200)

        tbl_lbl_frame = tk.Frame(table_frame, bg=t["panel"])
        tbl_lbl_frame.pack(fill="x", pady=(0, 4))

        tk.Label(
            tbl_lbl_frame,
            text="Parsed Structured Disclosures (9-Column Genesis Format):",
            font=FONT_BOLD,
            bg=t["panel"],
            fg=t["accent"]
        ).pack(side="left")

        self.lbl_stats = tk.Label(
            tbl_lbl_frame,
            text="0 Disclosures Loaded",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"]
        )
        self.lbl_stats.pack(side="right")

        cols = (
            "seller_name",
            "marketplace",
            "phone",
            "physical_address",
            "email",
            "authorization",
            "partner_type",
            "tag",
            "category"
        )
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended")
        
        self.tree.heading("seller_name", text="Seller Name (Req)", anchor="w")
        self.tree.heading("marketplace", text="Marketplace (Req)", anchor="w")
        self.tree.heading("phone", text="Seller Phone Number", anchor="w")
        self.tree.heading("physical_address", text="Seller Physical Address", anchor="w")
        self.tree.heading("email", text="Seller Email Address", anchor="w")
        self.tree.heading("authorization", text="Authorization", anchor="w")
        self.tree.heading("partner_type", text="Partner Type", anchor="w")
        self.tree.heading("tag", text="Tag", anchor="w")
        self.tree.heading("category", text="Seller Category", anchor="w")

        self.tree.column("seller_name", width=140, minwidth=100)
        self.tree.column("marketplace", width=100, minwidth=80)
        self.tree.column("phone", width=120, minwidth=90)
        self.tree.column("physical_address", width=250, minwidth=180)
        self.tree.column("email", width=150, minwidth=110)
        self.tree.column("authorization", width=100, minwidth=80)
        self.tree.column("partner_type", width=110, minwidth=90)
        self.tree.column("tag", width=120, minwidth=90)
        self.tree.column("category", width=120, minwidth=90)

        tr_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        tr_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tr_scroll_y.set, xscrollcommand=tr_scroll_x.set)

        self.tree.pack(side="top", fill="both", expand=True)
        tr_scroll_x.pack(side="bottom", fill="x")
        tr_scroll_y.pack(side="right", fill="y", before=self.tree)

        # Context Menu
        self.ctx_menu = tk.Menu(self, tearoff=False, bg=t["panel"], fg="#FFFFFF", activebackground=t["accent2"])
        self.ctx_menu.add_command(label="➕ Push Selected to Enforcement Registry", command=self._on_push_selected_to_registry)
        self.ctx_menu.add_command(label="🏪 Add Selected Handles to Stores Queue", command=self._on_add_selected_to_stores)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="📋 Copy Seller Name", command=self._on_copy_handle)
        self.ctx_menu.add_command(label="📋 Copy Full Address", command=self._on_copy_address)
        self.ctx_menu.add_command(label="📋 Copy Phone Number", command=self._on_copy_phone)
        self.ctx_menu.add_command(label="📋 Copy Email Address", command=self._on_copy_email)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="🗑 Remove Selected from List", command=self._on_remove_selected)

        self.tree.bind("<Button-3>", self._show_ctx_menu)
        self.tree.bind("<Delete>", lambda e: self._on_remove_selected())

        # ── 4. Bottom Action & Export Bar ─────────────────────────────────────
        bot_f = tk.Frame(pad_f, bg=t["bg"])
        bot_f.pack(fill="x", pady=(6, 0))

        push_all_btn = tk.Button(
            bot_f,
            text="➕ Push All to Enforcement Registry",
            font=FONT_BOLD,
            bg=t["accent2"],
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_push_all_to_registry
        )
        push_all_btn.pack(side="left", padx=(0, 6))

        add_stores_btn = tk.Button(
            bot_f,
            text="🏪 Add All to Stores Queue",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["accent"],
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._on_add_all_to_stores
        )
        add_stores_btn.pack(side="left", padx=(0, 6))

        close_btn = tk.Button(
            bot_f,
            text="❌ Close",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"],
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.destroy
        )
        close_btn.pack(side="right", padx=(6, 0))

        csv_btn = tk.Button(
            bot_f,
            text="📄 Export CSV",
            font=FONT_SM,
            bg=t["panel"],
            fg=t["subtext"],
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._on_export_csv
        )
        csv_btn.pack(side="right", padx=(6, 0))

        xlsx_btn = tk.Button(
            bot_f,
            text="💾 Export Genesis Excel (.xlsx)",
            font=FONT_BOLD,
            bg=t["success"],
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_export_excel
        )
        xlsx_btn.pack(side="right", padx=(6, 0))

        # Auto-parse initial sample placeholder
        self._on_parse_text_box()

    def _show_ctx_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            if item_id not in self.tree.selection():
                self.tree.selection_set(item_id)
            self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def _on_open_pdf(self):
        if not PYPDF_AVAILABLE:
            messagebox.showerror(
                "pypdf Required",
                "The 'pypdf' library is required to parse PDF files.\nPlease run 'pip install pypdf' or paste raw disclosure text directly into the text box."
            )
            return

        fp = filedialog.askopenfilename(
            title="Open VeRO Seller Disclosure PDF",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
        )
        if not fp:
            return

        try:
            mkt = self.mp_var.get() or "eBay"
            records = parse_vero_pdf(fp, default_marketplace=mkt)
            if not records:
                messagebox.showwarning("No Disclosures Found", f"Could not find any disclosure lines in '{os.path.basename(fp)}'.")
                return
            self._populate_records(records, append=False)
            messagebox.showinfo(
                "PDF Parsed",
                f"Successfully parsed {len(records)} seller disclosure(s) from '{os.path.basename(fp)}'."
            )
        except Exception as e:
            messagebox.showerror("PDF Read Error", f"Failed to parse PDF document:\n{e}")

    def _on_paste_clipboard(self):
        try:
            cb_text = self.clipboard_get()
            if not cb_text or not cb_text.strip():
                messagebox.showinfo("Clipboard Empty", "No text found on clipboard.")
                return
            self.txt_input.delete("1.0", "end")
            self.txt_input.insert("1.0", cb_text)
            self._on_parse_text_box()
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not paste clipboard content:\n{e}")

    def _on_parse_text_box(self):
        raw = self.txt_input.get("1.0", "end").strip()
        if not raw:
            return
        mkt = self.mp_var.get() or "eBay"
        records = parse_vero_text(raw, default_marketplace=mkt)
        self._populate_records(records, append=False)

    def _on_clear_all(self):
        self.txt_input.delete("1.0", "end")
        self.parsed_records.clear()
        for it in self.tree.get_children():
            self.tree.delete(it)
        self._update_stats()

    def _populate_records(self, records: List[Dict[str, str]], append: bool = False):
        if not append:
            self.parsed_records.clear()
            for it in self.tree.get_children():
                self.tree.delete(it)

        existing_keys = {
            (r.get("seller_name") or r.get("handle", "")).lower()
            for r in self.parsed_records
        }

        for rec in records:
            s_name = rec.get("seller_name") or rec.get("handle") or rec.get("contact_name", "")
            if not s_name:
                continue
            key = s_name.lower()
            if append and key in existing_keys:
                continue
            self.parsed_records.append(rec)
            existing_keys.add(key)

            self.tree.insert("", "end", values=(
                s_name,
                rec.get("marketplace", "eBay"),
                rec.get("seller_phone_number") or rec.get("phone", ""),
                rec.get("seller_physical_address") or rec.get("physical_address") or rec.get("street_address", ""),
                rec.get("seller_email_address") or rec.get("email", ""),
                rec.get("authorization", "Unauthorized"),
                rec.get("partner_type", "3rd-Party Seller"),
                rec.get("tag", "VeRO Disclosed Origin"),
                rec.get("seller_category", "VeRO Disclosed Seller")
            ))

        self._update_stats()

    def _update_stats(self):
        total = len(self.parsed_records)
        cn_count = sum(1 for r in self.parsed_records if "CN" in r.get("country", "").upper() or "CHINA" in r.get("country", "").upper() or "CN" in r.get("seller_physical_address", "").upper())
        us_count = sum(1 for r in self.parsed_records if "US" in r.get("country", "").upper() or "UNITED STATES" in r.get("country", "").upper() or "US" in r.get("seller_physical_address", "").upper())
        other_count = total - (cn_count + us_count)
        self.lbl_stats.config(
            text=f"Total: {total} | 🇨🇳 Direct China: {cn_count} | 🇺🇸 Domestic US: {us_count} | 🌍 Other: {other_count}"
        )

    def _get_selected_records(self) -> List[Dict[str, str]]:
        selected_ids = self.tree.selection()
        if not selected_ids:
            return []
        selected_names = set()
        for sid in selected_ids:
            vals = self.tree.item(sid, "values")
            if vals:
                selected_names.add(str(vals[0]).strip().lower())
        return [
            r for r in self.parsed_records
            if (r.get("seller_name") or r.get("handle", "")).strip().lower() in selected_names
        ]

    def _on_push_all_to_registry(self):
        if not self.parsed_records:
            messagebox.showwarning("No Records", "There are no parsed disclosure records to push.")
            return
        count = push_to_enforcement_registry(self.parsed_records, self.parent.data_store)
        messagebox.showinfo(
            "Registry Updated",
            f"Successfully updated {count} seller disclosure(s) in the permanent Enforcement Registry."
        )

    def _on_push_selected_to_registry(self):
        sel = self._get_selected_records()
        if not sel:
            messagebox.showinfo("Select Sellers", "Please select one or more sellers from the table.")
            return
        count = push_to_enforcement_registry(sel, self.parent.data_store)
        messagebox.showinfo(
            "Registry Updated",
            f"Successfully updated {count} selected seller disclosure(s) in the permanent Enforcement Registry."
        )

    def _on_add_all_to_stores(self):
        if not self.parsed_records:
            messagebox.showwarning("No Records", "There are no parsed disclosure records to add.")
            return
        handles = [r.get("seller_name") or r.get("handle") for r in self.parsed_records if (r.get("seller_name") or r.get("handle"))]
        self._append_to_stores_queue(handles)

    def _on_add_selected_to_stores(self):
        sel = self._get_selected_records()
        if not sel:
            messagebox.showinfo("Select Sellers", "Please select one or more sellers from the table.")
            return
        handles = [r.get("seller_name") or r.get("handle") for r in sel if (r.get("seller_name") or r.get("handle"))]
        self._append_to_stores_queue(handles)

    def _append_to_stores_queue(self, handles: List[str]):
        if not handles:
            return
        current = self.parent.store_text.get("1.0", "end").strip()
        existing_lines = [l.strip() for l in current.splitlines() if l.strip() and not l.startswith("🛒") and not l.startswith("🧰") and not l.startswith("🎵") and not l.startswith("👗") and not l.startswith("🌐") and not l.startswith("🌠") and not l.startswith("🟠") and not l.startswith("🛍") and not l.startswith("🎨") and not l.startswith("👕") and not l.startswith("📚")]
        
        seen = set(existing_lines)
        added = 0
        for h in handles:
            if h not in seen:
                existing_lines.append(h)
                seen.add(h)
                added += 1

        self.parent.store_text.delete("1.0", "end")
        self.parent.store_text.insert("1.0", "\n".join(existing_lines))
        self.parent.store_text.config(fg=self.t["accent"])
        messagebox.showinfo(
            "Stores Queue Updated",
            f"Added {added} seller handle(s) to Apollo Stores Queue (Total: {len(existing_lines)} stores)."
        )

    def _on_copy_handle(self):
        sel = self._get_selected_records()
        if not sel:
            return
        handles = "\n".join(r.get("seller_name") or r.get("handle", "") for r in sel if (r.get("seller_name") or r.get("handle")))
        self.clipboard_clear()
        self.clipboard_append(handles)

    def _on_copy_address(self):
        sel = self._get_selected_records()
        if not sel:
            return
        lines = [r.get("seller_physical_address") or r.get("physical_address") or r.get("street_address", "") for r in sel]
        self.clipboard_clear()
        self.clipboard_append("\n".join(l for l in lines if l))

    def _on_copy_phone(self):
        sel = self._get_selected_records()
        if not sel:
            return
        lines = [r.get("seller_phone_number") or r.get("phone", "") for r in sel]
        self.clipboard_clear()
        self.clipboard_append("\n".join(l for l in lines if l))

    def _on_copy_email(self):
        sel = self._get_selected_records()
        if not sel:
            return
        lines = [r.get("seller_email_address") or r.get("email", "") for r in sel]
        self.clipboard_clear()
        self.clipboard_append("\n".join(l for l in lines if l))

    def _on_remove_selected(self):
        selected_ids = self.tree.selection()
        if not selected_ids:
            return
        selected_names = set()
        for sid in selected_ids:
            vals = self.tree.item(sid, "values")
            if vals:
                selected_names.add(str(vals[0]).strip().lower())
            self.tree.delete(sid)
        self.parsed_records = [
            r for r in self.parsed_records
            if (r.get("seller_name") or r.get("handle", "")).strip().lower() not in selected_names
        ]
        self._update_stats()

    def _on_export_excel(self):
        if not self.parsed_records:
            messagebox.showwarning("No Records", "No disclosure records to export.")
            return
        default_name = f"VeRO_Seller_Disclosures_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        fp = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if not fp:
            return
        try:
            export_to_excel(self.parsed_records, fp)
            messagebox.showinfo("Export Successful", f"Exported {len(self.parsed_records)} disclosures to:\n{fp}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export Excel file:\n{e}")

    def _on_export_csv(self):
        if not self.parsed_records:
            messagebox.showwarning("No Records", "No disclosure records to export.")
            return
        default_name = f"VeRO_Seller_Disclosures_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        fp = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not fp:
            return
        try:
            export_to_csv(self.parsed_records, fp)
            messagebox.showinfo("Export Successful", f"Exported {len(self.parsed_records)} disclosures to:\n{fp}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export CSV file:\n{e}")
