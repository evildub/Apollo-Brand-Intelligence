"""
argus_compliance_modal.py - Argus Compliance Sentinel Modal UI
Interactive multi-marketplace takedown verification and listing availability auditor.
Ingests enterprise Excel / CSV exports, probes URLs across all platforms concurrently,
and outputs formatted compliance audit dossiers.
"""

import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from datetime import datetime
from typing import Dict, List, Any, Optional

from argus_engine import (
    ArgusEngine,
    ComplianceResult,
    STATUS_REMOVED,
    STATUS_ENDED,
    STATUS_ACTIVE,
    STATUS_BLOCKED,
    STATUS_ERROR,
    STATUS_BADGES
)

try:
    from theme_definitions import THEMES
except ImportError:
    THEMES = {}

FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_HEAD = ("Segoe UI", 10, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SM = ("Segoe UI", 8)
FONT_CODE = ("Consolas", 9)


class ArgusComplianceModal(tk.Toplevel):
    """High-volume multi-marketplace takedown and availability compliance audit modal."""

    def __init__(self, master=None, theme: Optional[Dict[str, str]] = None):
        super().__init__(master)
        self.master = master
        self.theme = theme or getattr(master, "theme", None) or {
            "bg": "#000227",
            "panel": "#0A0E36",
            "accent": "#38BDF8",
            "accent2": "#347BB7",
            "text": "#FFFFFF",
            "subtext": "#7C8FA3",
            "border": "#1E295D",
            "entry_bg": "#05071F",
            "btn_normal_bg": "#0F1642",
            "btn_normal_fg": "#FFFFFF",
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444"
        }

        self.title("👁 Argus Compliance Sentinel — Multi-Marketplace Availability & Takedown Verifier")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.configure(bg=self._t("bg", "#000227"))
        if master:
            self.transient(master)

        if hasattr(master, "_apply_dark_titlebar"):
            master._apply_dark_titlebar(self, force=True)
            self.after(50, lambda: master._apply_dark_titlebar(self, force=True))
            self.after(200, lambda: master._apply_dark_titlebar(self, force=True))
        else:
            self._apply_local_dark_titlebar()

        if hasattr(master, "_load_app_icon"):
            master._load_app_icon(self)

        self.engine = ArgusEngine(max_workers=8)
        self.loaded_items: List[Dict[str, Any]] = []
        self.audit_results: List[ComplianceResult] = []
        self.original_columns: List[str] = []
        self.detected_url_col: str = ""
        self.is_auditing = False
        self.is_paused = False

        self._build_ui()

        if hasattr(master, "_center_window"):
            master._center_window(self, 1180, 760)
        else:
            self.deiconify()
            self.lift()
            self.focus_force()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _t(self, key: str, default: str) -> str:
        return self.theme.get(key, default)

    def _apply_local_dark_titlebar(self):
        try:
            import ctypes
            w_id = self.winfo_id()
            hwnd = ctypes.windll.user32.GetAncestor(w_id, 2)
            if not hwnd:
                hwnd = self.winfo_id()
            v_dark = ctypes.c_int(1)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v_dark), ctypes.sizeof(v_dark))
        except Exception:
            pass

    def _btn(self, parent, text, command, accent=False, danger=False, **kwargs):
        t = self.theme
        if accent:
            bg = t.get("accent", "#38BDF8")
            fg = "#000227"
            abg = t.get("accent2", "#347BB7")
        elif danger:
            bg = t.get("danger", "#EF4444")
            fg = "#FFFFFF"
            abg = "#DC2626"
        else:
            bg = t.get("btn_normal_bg", "#0F1642")
            fg = t.get("btn_normal_fg", "#FFFFFF")
            abg = t.get("border", "#1E295D")

        return tk.Button(
            parent, text=text, command=command, font=FONT_BOLD if accent else FONT_NORM,
            bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
            relief="flat", cursor="hand2", padx=kwargs.pop("padx", 10), pady=kwargs.pop("pady", 4), **kwargs
        )

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        t = self.theme

        # ── 1. Top Header Banner ──
        header = tk.Frame(self, bg=t["panel"], padx=16, pady=10, highlightbackground=t["border"], highlightthickness=1)
        header.pack(fill="x", side="top")

        t_row = tk.Frame(header, bg=t["panel"])
        t_row.pack(fill="x")
        tk.Label(t_row, text="👁", font=("Segoe UI", 16), bg=t["panel"], fg=t["accent"]).pack(side="left", padx=(0, 6))
        tk.Label(t_row, text="ARGUS COMPLIANCE SENTINEL", font=FONT_TITLE, bg=t["panel"], fg=t["text"]).pack(side="left")
        
        tag_lbl = tk.Label(t_row, text="ALL-SEEING TAKEDOWN AUDITOR", font=("Segoe UI", 8, "bold"), bg=t["accent"], fg="#000227", padx=8, pady=2)
        tag_lbl.pack(side="left", padx=10)

        # Telemetry Metrics Row
        cards_f = tk.Frame(header, bg=t["panel"], pady=6)
        cards_f.pack(fill="x", pady=(6, 0))

        self.card_total = self._create_card(cards_f, "0", "INGESTED LISTINGS", t["subtext"])
        self.card_removed = self._create_card(cards_f, "0", "🔴 REMOVED / 404", t["danger"])
        self.card_ended = self._create_card(cards_f, "0", "🟡 ENDED / INACTIVE", t["warning"])
        self.card_active = self._create_card(cards_f, "0", "🟢 ACTIVE / LIVE", t["success"])
        self.card_blocked = self._create_card(cards_f, "0", "⚪ BLOCKED / CAPTCHA", t["subtext"])

        # ── 2. Action Toolbar ──
        toolbar = tk.Frame(self, bg=t["panel"], padx=14, pady=6, highlightbackground=t["border"], highlightthickness=1)
        toolbar.pack(fill="x", side="top", pady=(4, 0))

        self.btn_import = self._btn(toolbar, "📂 Import Excel / CSV", self._import_file, accent=True)
        self.btn_import.pack(side="left", padx=(0, 4))

        self.btn_paste = self._btn(toolbar, "📋 Paste URLs", self._prompt_paste_urls)
        self.btn_paste.pack(side="left", padx=(0, 8))

        # Divider
        tk.Frame(toolbar, bg=t["border"], width=1, height=22).pack(side="left", padx=6)

        self.btn_start = self._btn(toolbar, "▶ Start Audit", self._start_audit, accent=True)
        self.btn_start.pack(side="left", padx=(0, 4))

        self.btn_pause = self._btn(toolbar, "⏸ Pause", self._toggle_pause)
        self.btn_pause.pack(side="left", padx=(0, 4))
        self.btn_pause.config(state="disabled")

        self.btn_stop = self._btn(toolbar, "⏹ Abort", self._abort_audit, danger=True)
        self.btn_stop.pack(side="left", padx=(0, 8))
        self.btn_stop.config(state="disabled")

        # Concurrency thread slider
        tk.Label(toolbar, text="Threads:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(6, 2))
        self.thread_var = tk.StringVar(value="8")
        self.thread_combo = ttk.Combobox(toolbar, textvariable=self.thread_var, values=["2", "4", "8", "12", "16"], width=3, state="readonly")
        self.thread_combo.pack(side="left", padx=(0, 10))

        # Filter View dropdown
        tk.Label(toolbar, text="Filter View:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(6, 2))
        self.filter_var = tk.StringVar(value="All Statuses")
        self.filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var, values=[
            "All Statuses",
            "🔴 Removed / 404 Only",
            "🟡 Ended / Inactive Only",
            "🟢 Active / Live Only",
            "⚪ Blocked / Errors Only"
        ], state="readonly", width=18)
        self.filter_combo.pack(side="left")
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_table_view())

        # Right Export Button
        self.btn_export = self._btn(toolbar, "💾 Export Audit Report (.xlsx)", self._export_report, accent=True)
        self.btn_export.pack(side="right")

        # ── 3. Progress Telemetry Bar ──
        prog_f = tk.Frame(self, bg=t["bg"], padx=14, pady=4)
        prog_f.pack(fill="x", side="top")

        self.progress_var = tk.DoubleVar(value=0.0)
        self.prog_bar = ttk.Progressbar(prog_f, variable=self.progress_var, maximum=100.0, mode="determinate")
        self.prog_bar.pack(fill="x", side="top")

        self.status_lbl = tk.Label(prog_f, text="Ingest a file or paste URLs to begin takedown compliance audit.", font=FONT_SM, bg=t["bg"], fg=t["subtext"])
        self.status_lbl.pack(anchor="w", pady=(2, 0))

        # ── 4. Main Results Treeview Table ──
        table_f = tk.Frame(self, bg=t["entry_bg"], padx=12, pady=4)
        table_f.pack(fill="both", expand=True)

        cols = ("status", "marketplace", "detail", "http_code", "latency", "url", "timestamp")
        self.tree = ttk.Treeview(table_f, columns=cols, show="headings", selectmode="extended", style="Argus.Treeview")

        headings = {
            "status": "Compliance Status",
            "marketplace": "Marketplace",
            "detail": "Verification Details & Trigger",
            "http_code": "HTTP",
            "latency": "Latency",
            "url": "Listing / Item URL",
            "timestamp": "Audited At"
        }
        widths = {
            "status": 150,
            "marketplace": 110,
            "detail": 280,
            "http_code": 65,
            "latency": 75,
            "url": 340,
            "timestamp": 130
        }
        for c in cols:
            self.tree.heading(c, text=headings[c], anchor="w" if c not in ("http_code", "latency", "status") else "center")
            self.tree.column(c, width=widths[c], minwidth=50, stretch=True if c in ("detail", "url") else False, anchor="w" if c not in ("http_code", "latency", "status") else "center")

        style = ttk.Style(self)
        style.configure("Argus.Treeview", background=t["entry_bg"], foreground=t["text"], fieldbackground=t["entry_bg"], rowheight=24, font=FONT_NORM)
        style.configure("Argus.Treeview.Heading", background=t["panel"], foreground=t["text"], font=FONT_BOLD)

        # Status Tag Colors
        self.tree.tag_configure("REMOVED", foreground=t.get("danger", "#EF4444"))
        self.tree.tag_configure("ENDED", foreground=t.get("warning", "#F59E0B"))
        self.tree.tag_configure("ACTIVE", foreground=t.get("success", "#10B981"))
        self.tree.tag_configure("BLOCKED", foreground=t.get("subtext", "#7C8FA3"))

        vsb = ttk.Scrollbar(table_f, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_f, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_f.rowconfigure(0, weight=1)
        table_f.columnconfigure(0, weight=1)

        # Context Menu & Double-click
        self.tree.bind("<Double-1>", self._on_double_click_url)
        self.tree.bind("<Button-3>", self._show_context_menu)

        # ── 5. Bottom Status Strip ──
        bot_strip = tk.Frame(self, bg=t["panel"], padx=14, pady=6, highlightbackground=t["border"], highlightthickness=1)
        bot_strip.pack(fill="x", side="bottom")

        self.bot_lbl = tk.Label(bot_strip, text="Ready. Zero external trackers. Deterministic local execution.", font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        self.bot_lbl.pack(side="left")

        self._btn(bot_strip, "✕ Close Sentinel", self.destroy, padx=12).pack(side="right")

    def _create_card(self, parent, val: str, title: str, color: str) -> tk.Label:
        t = self.theme
        frame = tk.Frame(parent, bg=t["entry_bg"], padx=12, pady=6, relief="solid", bd=1, highlightbackground=t["border"])
        frame.pack(side="left", padx=4)
        v_lbl = tk.Label(frame, text=val, font=("Segoe UI", 12, "bold"), bg=t["entry_bg"], fg=color)
        v_lbl.pack(anchor="w")
        tk.Label(frame, text=title, font=("Segoe UI", 7, "bold"), bg=t["entry_bg"], fg=t["subtext"]).pack(anchor="w")
        return v_lbl

    # ── File Ingestion & Parsing ──────────────────────────────────────────────
    def _import_file(self):
        fpath = filedialog.askopenfilename(
            title="Import Enterprise Intake / URLs File",
            filetypes=[("Excel & CSV Files", "*.xlsx *.xls *.csv"), ("Excel Workbooks", "*.xlsx *.xls"), ("CSV Files", "*.csv"), ("All Files", "*.*")],
            parent=self
        )
        if not fpath:
            return

        try:
            rows, detected_col, all_cols = ArgusEngine.parse_import_file(fpath)
            if not rows:
                messagebox.showwarning("Empty File", "No data rows found in the selected file.", parent=self)
                return

            self.loaded_items = rows
            self.original_columns = all_cols
            self.detected_url_col = detected_col
            self.audit_results.clear()

            self.card_total.config(text=str(len(self.loaded_items)))
            self.card_removed.config(text="0")
            self.card_ended.config(text="0")
            self.card_active.config(text="0")
            self.card_blocked.config(text="0")

            self.status_lbl.config(
                text=f"Loaded {len(rows)} listings from '{os.path.basename(fpath)}'. Identified URL column: [{detected_col}]. Ready to audit.",
                fg=self.theme.get("accent", "#38BDF8")
            )
            self._refresh_table_view()
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to parse file:\n{e}", parent=self)

    def _prompt_paste_urls(self):
        text = simpledialog.askstring(
            "Paste URLs for Audit",
            "Paste listing URLs (one per line):",
            parent=self
        )
        if not text:
            return

        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        if not lines:
            return

        self.loaded_items = [{"url": ln} for ln in lines]
        self.original_columns = ["url"]
        self.detected_url_col = "url"
        self.audit_results.clear()

        self.card_total.config(text=str(len(self.loaded_items)))
        self.card_removed.config(text="0")
        self.card_ended.config(text="0")
        self.card_active.config(text="0")
        self.card_blocked.config(text="0")

        self.status_lbl.config(
            text=f"Loaded {len(lines)} pasted URLs. Ready to audit.",
            fg=self.theme.get("accent", "#38BDF8")
        )
        self._refresh_table_view()

    # ── Audit Execution ───────────────────────────────────────────────────────
    def _start_audit(self):
        if not self.loaded_items:
            messagebox.showinfo("No URLs", "Please import an Excel/CSV file or paste URLs first.", parent=self)
            return

        if self.is_auditing:
            return

        self.is_auditing = True
        self.is_paused = False
        self.btn_start.config(state="disabled")
        self.btn_import.config(state="disabled")
        self.btn_paste.config(state="disabled")
        self.btn_pause.config(state="normal", text="⏸ Pause")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0.0)

        try:
            workers = int(self.thread_var.get())
        except Exception:
            workers = 8
        self.engine.max_workers = workers

        self.audit_results.clear()
        self.tree.delete(*self.tree.get_children())

        # Launch background audit thread
        threading.Thread(target=self._run_audit_thread, daemon=True).start()

    def _run_audit_thread(self):
        def _prog(completed, total, res: ComplianceResult):
            self.audit_results.append(res)
            # Dispatch UI updates via thread-safe after()
            self.after(0, lambda: self._on_result_received(completed, total, res))

        self.engine.audit_batch(
            items=self.loaded_items,
            url_field=self.detected_url_col or "url",
            progress_callback=_prog
        )

        self.after(0, self._on_audit_completed)

    def _on_result_received(self, completed: int, total: int, res: ComplianceResult):
        pct = (completed / total) * 100.0 if total > 0 else 0.0
        self.progress_var.set(pct)
        self.status_lbl.config(
            text=f"Audited: {completed}/{total} ({pct:.1f}%) — [{res.marketplace}] {res.details[:60]}",
            fg=self.theme["text"]
        )

        # Update metric counters
        counts = {
            STATUS_REMOVED: 0,
            STATUS_ENDED: 0,
            STATUS_ACTIVE: 0,
            STATUS_BLOCKED: 0
        }
        for r in self.audit_results:
            if r.status in counts:
                counts[r.status] += 1
            else:
                counts[STATUS_BLOCKED] += 1

        self.card_removed.config(text=str(counts[STATUS_REMOVED]))
        self.card_ended.config(text=str(counts[STATUS_ENDED]))
        self.card_active.config(text=str(counts[STATUS_ACTIVE]))
        self.card_blocked.config(text=str(counts[STATUS_BLOCKED]))

        # Insert row into tree if matching current view filter
        f_val = self.filter_var.get()
        if self._matches_filter(res.status, f_val):
            tag = "BLOCKED"
            if res.status == STATUS_REMOVED:
                tag = "REMOVED"
            elif res.status == STATUS_ENDED:
                tag = "ENDED"
            elif res.status == STATUS_ACTIVE:
                tag = "ACTIVE"

            self.tree.insert("", "end", values=(
                STATUS_BADGES.get(res.status, res.status),
                res.marketplace,
                res.details,
                res.status_code if res.status_code else "ERR",
                f"{res.latency_ms}ms",
                res.url,
                res.timestamp
            ), tags=(tag,))

    def _on_audit_completed(self):
        self.is_auditing = False
        self.is_paused = False
        self.btn_start.config(state="normal")
        self.btn_import.config(state="normal")
        self.btn_paste.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_stop.config(state="disabled")

        total = len(self.audit_results)
        rem = sum(1 for r in self.audit_results if r.status == STATUS_REMOVED)
        end = sum(1 for r in self.audit_results if r.status == STATUS_ENDED)
        act = sum(1 for r in self.audit_results if r.status == STATUS_ACTIVE)

        self.status_lbl.config(
            text=f"Audit complete: {total} URLs verified. 🔴 {rem} Removed/404 | 🟡 {end} Ended | 🟢 {act} Active.",
            fg=self.theme.get("success", "#10B981")
        )

    def _toggle_pause(self):
        if not self.is_auditing:
            return
        if self.is_paused:
            self.engine.resume()
            self.is_paused = False
            self.btn_pause.config(text="⏸ Pause")
            self.status_lbl.config(text="Audit resumed...")
        else:
            self.engine.pause()
            self.is_paused = True
            self.btn_pause.config(text="▶ Resume")
            self.status_lbl.config(text="Audit paused.")

    def _abort_audit(self):
        if not self.is_auditing:
            return
        if messagebox.askyesno("Abort Audit", "Are you sure you want to abort the compliance audit?", parent=self):
            self.engine.abort()
            self.is_auditing = False
            self.status_lbl.config(text="Audit aborted by user.")

    # ── Table View Filtering & Context Actions ────────────────────────────────
    def _matches_filter(self, status: str, filter_str: str) -> bool:
        if filter_str == "All Statuses":
            return True
        if "Removed" in filter_str and status == STATUS_REMOVED:
            return True
        if "Ended" in filter_str and status == STATUS_ENDED:
            return True
        if "Active" in filter_str and status == STATUS_ACTIVE:
            return True
        if "Blocked" in filter_str and status in (STATUS_BLOCKED, STATUS_ERROR):
            return True
        return False

    def _refresh_table_view(self):
        self.tree.delete(*self.tree.get_children())
        f_val = self.filter_var.get()
        for res in self.audit_results:
            if self._matches_filter(res.status, f_val):
                tag = "BLOCKED"
                if res.status == STATUS_REMOVED:
                    tag = "REMOVED"
                elif res.status == STATUS_ENDED:
                    tag = "ENDED"
                elif res.status == STATUS_ACTIVE:
                    tag = "ACTIVE"

                self.tree.insert("", "end", values=(
                    STATUS_BADGES.get(res.status, res.status),
                    res.marketplace,
                    res.details,
                    res.status_code if res.status_code else "ERR",
                    f"{res.latency_ms}ms",
                    res.url,
                    res.timestamp
                ), tags=(tag,))

    def _on_double_click_url(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        if vals and len(vals) >= 6:
            url = str(vals[5])
            if url.startswith("http"):
                webbrowser.open_new_tab(url)

    def _show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            menu = tk.Menu(self, tearoff=0, bg=self._t("panel", "#0A0E36"), fg=self._t("text", "#FFFFFF"))
            vals = self.tree.item(iid)["values"]
            url = str(vals[5]) if len(vals) >= 6 else ""

            menu.add_command(label="🌐 Open URL in Browser", command=lambda: webbrowser.open_new_tab(url) if url else None)
            menu.add_command(label="📋 Copy Listing URL", command=lambda: self._copy_to_clipboard(url))
            menu.add_separator()
            menu.add_command(label="📋 Copy Row Summary", command=lambda: self._copy_to_clipboard(" | ".join(str(v) for v in vals)))
            menu.post(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text: str):
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    # ── Exporting ─────────────────────────────────────────────────────────────
    def _export_report(self):
        if not self.audit_results:
            messagebox.showinfo("No Results", "No audit findings available to export.", parent=self)
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        def_name = f"Argus_Compliance_Audit_{ts}.xlsx"
        filepath = filedialog.asksaveasfilename(
            title="Save Argus Compliance Audit Report",
            defaultextension=".xlsx",
            initialfile=def_name,
            filetypes=[("Excel Workbook", "*.xlsx"), ("All Files", "*.*")],
            parent=self
        )
        if not filepath:
            return

        try:
            ArgusEngine.export_compliance_report(filepath, self.audit_results, self.original_columns)
            messagebox.showinfo(
                "Export Complete",
                f"Successfully exported Argus Compliance Audit Dossier to:\n\n{filepath}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export compliance report:\n{e}", parent=self)

    def _on_closing(self):
        if self.is_auditing:
            if not messagebox.askyesno("Exit Argus", "A compliance audit is currently running. Exit anyway?", parent=self):
                return
            self.engine.abort()
        self.destroy()


def open_argus_compliance_modal(parent=None, theme=None) -> ArgusComplianceModal:
    """Helper entry point to launch Argus Sentinel from Apollo or standalone."""
    return ArgusComplianceModal(master=parent, theme=theme)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = ArgusComplianceModal(master=root)
    app.protocol("WM_DELETE_WINDOW", lambda: root.destroy())
    root.mainloop()
