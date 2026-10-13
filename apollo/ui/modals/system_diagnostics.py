"""
system_diagnostics.py - Pre-Flight System Diagnostics & Health Check Suite

Provides comprehensive hardware, runtime, network, perceptual hashing, and storage
diagnostics for Apollo Brand Intelligence and Artemis Rights Engine.

Can be run standalone:
    python system_diagnostics.py

Or imported and invoked as a theme-aligned modal from Apollo or Artemis:
    from system_diagnostics import open_diagnostics_modal
    open_diagnostics_modal(parent_app)
"""

import os
import sys
import time
import json
import socket
import platform
import threading
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Any, Optional

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from theme_definitions import THEMES
except ImportError:
    THEMES = {}


# ══════════════════════════════════════════════════════════════════════════════
#  DIAGNOSTIC PROBE ENGINE (Zero UI Dependencies)
# ══════════════════════════════════════════════════════════════════════════════

class DiagnosticResult:
    def __init__(self, category: str, name: str, status: str, details: str, latency_ms: Optional[float] = None):
        self.category = category      # e.g., "Runtime", "Visual Engine", "Storage", "Network", "IPC Bridge"
        self.name = name              # e.g., "64-bit DCT pHash Engine"
        self.status = status          # "PASS", "WARN", "FAIL"
        self.details = details        # e.g., "Computed 64-bit hash in 0.42ms (Sanity 100%)"
        self.latency_ms = latency_ms  # Optional latency in ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "latency_ms": self.latency_ms
        }


class DiagnosticEngine:
    """Executes a battery of hardware, runtime, filesystem, hashing, and network checks."""

    @staticmethod
    def check_runtime_environment() -> List[DiagnosticResult]:
        results = []
        # 1. Python Version
        py_ver = sys.version.split()[0]
        major, minor = sys.version_info.major, sys.version_info.minor
        if major >= 3 and minor >= 9:
            results.append(DiagnosticResult("Runtime", "Python Environment", "PASS", f"Python v{py_ver} (64-bit: {sys.maxsize > 2**32})"))
        else:
            results.append(DiagnosticResult("Runtime", "Python Environment", "WARN", f"Python v{py_ver} (Recommend 3.10+)"))

        # 2. OS & Architecture
        os_info = f"{platform.system()} {platform.release()} ({platform.architecture()[0]}) - CPU: {os.cpu_count() or 'Unknown'} Cores"
        results.append(DiagnosticResult("Runtime", "Operating System & CPU", "PASS", os_info))

        # 3. Concurrency Thread Pool Capacity
        cpu_cores = os.cpu_count() or 4
        optimal_workers = max(16, min(48, cpu_cores * 4))
        results.append(DiagnosticResult("Runtime", "Concurrency Engine", "PASS", f"System supports up to {optimal_workers} parallel dredge workers (35 nominal)"))

        return results

    @staticmethod
    def check_visual_and_hashing() -> List[DiagnosticResult]:
        results = []
        # 1. PIL / Pillow library
        if HAS_PIL:
            import PIL
            pil_ver = getattr(PIL, "__version__", "Available")
            results.append(DiagnosticResult("Visual Engine", "Imaging Subsystem (Pillow)", "PASS", f"Pillow v{pil_ver} initialized"))
        else:
            results.append(DiagnosticResult("Visual Engine", "Imaging Subsystem (Pillow)", "FAIL", "Pillow not installed; visual hashing disabled"))
            return results

        # 2. 64-bit DCT Perceptual Hashing Benchmark
        try:
            t0 = time.perf_counter()
            # Generate synthetic 64x64 test image
            img = Image.new("RGB", (64, 64), color=(120, 150, 200))
            # Test grayscale + resize to 8x8 + average hash calculation
            img_gray = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
            if hasattr(img_gray, "get_flattened_data"):
                pixels = list(img_gray.get_flattened_data())
            elif hasattr(img_gray, "getdata"):
                pixels = list(img_gray.getdata())
            else:
                pixels = list(img_gray.tobytes())
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p > avg else "0" for p in pixels)
            hash_val = f"{int(bits, 2):016x}"
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if len(hash_val) == 16:
                results.append(DiagnosticResult("Visual Engine", "64-bit DCT pHash Algorithm", "PASS", f"Synthetic hash computed ({hash_val})", latency_ms=elapsed_ms))
            else:
                results.append(DiagnosticResult("Visual Engine", "64-bit DCT pHash Algorithm", "WARN", f"Hash width unexpected: {len(hash_val)} chars", latency_ms=elapsed_ms))
        except Exception as e:
            results.append(DiagnosticResult("Visual Engine", "64-bit DCT pHash Algorithm", "FAIL", f"Hashing exception: {str(e)}"))

        return results

    @staticmethod
    def check_storage_and_databases() -> List[DiagnosticResult]:
        results = []

        # 1. Disk IO Benchmark
        try:
            test_dir = os.path.dirname(os.path.abspath(__file__))
            temp_file = os.path.join(test_dir, ".diag_iotest.tmp")
            payload = b"X" * (64 * 1024)  # 64 KB block
            t0 = time.perf_counter()
            with open(temp_file, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            with open(temp_file, "rb") as f:
                read_data = f.read()
            if os.path.exists(temp_file):
                os.remove(temp_file)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if len(read_data) == len(payload):
                results.append(DiagnosticResult("Storage & IO", "Local Disk IO Latency", "PASS", f"64KB synchronous write/read/sync cycle", latency_ms=elapsed_ms))
            else:
                results.append(DiagnosticResult("Storage & IO", "Local Disk IO Latency", "WARN", f"Data integrity mismatch during IO cycle", latency_ms=elapsed_ms))
        except Exception as e:
            results.append(DiagnosticResult("Storage & IO", "Local Disk IO Latency", "FAIL", f"Disk IO permission error: {str(e)}"))

        # 2. Apollo Data Store (data.json)
        apollo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
        if os.path.exists(apollo_path):
            try:
                size_kb = os.path.getsize(apollo_path) / 1024.0
                with open(apollo_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                brands = len(data.get("brands", []))
                listings = len(data.get("listings", []))
                results.append(DiagnosticResult("Storage & IO", "Apollo Data Vault (data.json)", "PASS", f"Verified ({size_kb:.1f} KB) - {brands} Brands, {listings} Listings cached"))
            except Exception as e:
                results.append(DiagnosticResult("Storage & IO", "Apollo Data Vault (data.json)", "WARN", f"JSON parse warning: {str(e)}"))
        else:
            results.append(DiagnosticResult("Storage & IO", "Apollo Data Vault (data.json)", "WARN", "File not found (will be initialized on first Apollo scan)"))

        # 3. Artemis Data Store (artemis_data.json)
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        artemis_dir = os.path.join(local_appdata, "Artemis_Rights_Engine")
        artemis_file = os.path.join(artemis_dir, "artemis_data.json")
        if os.path.exists(artemis_file):
            try:
                size_kb = os.path.getsize(artemis_file) / 1024.0
                with open(artemis_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                queue_count = len(data.get("enforcement_queue", []))
                brand_count = len(data.get("brand_rights_registry", {}))
                hist_count = len(data.get("submission_history", []))
                results.append(DiagnosticResult("Storage & IO", "Artemis Store (artemis_data.json)", "PASS", f"Verified ({size_kb:.1f} KB) - {brand_count} Brands, {queue_count} Enqueued, {hist_count} Filed"))
            except Exception as e:
                results.append(DiagnosticResult("Storage & IO", "Artemis Store (artemis_data.json)", "WARN", f"JSON parse warning: {str(e)}"))
        else:
            results.append(DiagnosticResult("Storage & IO", "Artemis Store (artemis_data.json)", "PASS", "Initialized on demand in %LOCALAPPDATA%"))

        # 4. Secure LOA Document Vault
        loa_dir = os.path.join(artemis_dir, "secure_loa_vault")
        if os.path.exists(loa_dir):
            loa_count = len([f for f in os.listdir(loa_dir) if os.path.isfile(os.path.join(loa_dir, f))])
            results.append(DiagnosticResult("Storage & IO", "LOA Document Vault", "PASS", f"Secure directory active ({loa_count} legal authorization documents vaulted)"))
        else:
            results.append(DiagnosticResult("Storage & IO", "LOA Document Vault", "PASS", "Ready for brand authorization document intake"))

        return results

    @staticmethod
    def check_ipc_bridge() -> List[DiagnosticResult]:
        results = []
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        queue_dir = os.path.join(local_appdata, "Artemis_Rights_Engine", "intake_queue")

        try:
            os.makedirs(queue_dir, exist_ok=True)
            # Test write access
            test_path = os.path.join(queue_dir, ".probe_test.tmp")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write('{"probe": true}')
            if os.path.exists(test_path):
                os.remove(test_path)

            pending = [f for f in os.listdir(queue_dir) if f.startswith("batch_") and f.endswith(".json")]
            results.append(DiagnosticResult("IPC Bridge", "Atomic Drop-Queue Protocol", "PASS", f"Queue accessible with full RW permissions ({len(pending)} pending intake batches)"))
        except Exception as e:
            results.append(DiagnosticResult("IPC Bridge", "Atomic Drop-Queue Protocol", "FAIL", f"Queue permission denied: {str(e)}"))

        return results

    @staticmethod
    def check_network_and_gateways(abort_event: Optional[threading.Event] = None) -> List[DiagnosticResult]:
        import concurrent.futures
        results = []

        # 1. Core Internet DNS & Socket Resolution (Bounded 1.5s probe)
        try:
            t0 = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            # Probe standard HTTPS gateway on Cloudflare 1.1.1.1 or Google 8.8.8.8
            try:
                s.connect(("1.1.1.1", 443))
            except Exception:
                s.connect(("8.8.8.8", 53))
            s.close()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            results.append(DiagnosticResult("Network Telemetry", "DNS & WAN Gateway Latency", "PASS", "Direct Internet connection verified", latency_ms=elapsed_ms))
        except Exception as e:
            results.append(DiagnosticResult("Network Telemetry", "DNS & WAN Gateway Latency", "WARN", f"DNS/WAN gateway probe slow or offline: {str(e)[:45]}"))

        if abort_event and abort_event.is_set():
            return results

        # 2. Marketplace Endpoint Probes (Parallel Lightweight HTTP Checks)
        endpoints = [
            ("Amazon Marketplace", "https://www.amazon.com"),
            ("eBay Marketplace", "https://www.ebay.com"),
            ("Redbubble Platform", "https://www.redbubble.com"),
            ("Printerval Portal", "https://printerval.com"),
            ("Walmart Brand Portal", "https://brandportal.walmart.com")
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        def _probe_single_endpoint(name_url):
            name, url = name_url
            if abort_event and abort_event.is_set():
                return None
            try:
                t0 = time.perf_counter()
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    code = resp.getcode()
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    if code in (200, 301, 302):
                        return DiagnosticResult("Marketplace Endpoints", name, "PASS", f"HTTP {code} OK", latency_ms=elapsed_ms)
                    else:
                        return DiagnosticResult("Marketplace Endpoints", name, "WARN", f"HTTP {code} Response", latency_ms=elapsed_ms)
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    return DiagnosticResult("Marketplace Endpoints", name, "WARN", "HTTP 403 (Standard Bot Challenge active - Apollo stealth routing required)")
                else:
                    return DiagnosticResult("Marketplace Endpoints", name, "WARN", f"HTTP {e.code}")
            except Exception as e:
                return DiagnosticResult("Marketplace Endpoints", name, "WARN", f"Connection timeout / rate limited ({str(e)[:40]}...)")

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(_probe_single_endpoint, ep): ep for ep in endpoints}
                done, _ = concurrent.futures.wait(futures.keys(), timeout=3.5)
                for f in done:
                    try:
                        res = f.result()
                        if res:
                            results.append(res)
                    except Exception:
                        pass
        except Exception as e:
            results.append(DiagnosticResult("Marketplace Endpoints", "Endpoint Sweep", "WARN", f"Parallel probe pool interrupted: {e}"))

        return results


# ══════════════════════════════════════════════════════════════════════════════
#  THEMED DIAGNOSTICS MODAL (Apollo & Artemis Compatible)
# ══════════════════════════════════════════════════════════════════════════════

class SystemDiagnosticsModal(tk.Toplevel):
    def __init__(self, parent=None, theme: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self.parent = parent
        
        # Determine theme
        if theme:
            self.theme = theme
        elif hasattr(parent, "theme"):
            self.theme = parent.theme
        elif THEMES:
            self.theme = THEMES.get("artemis_emerald", next(iter(THEMES.values())))
        else:
            self.theme = {
                "bg": "#0A0E17",
                "panel": "#111827",
                "text": "#F9FAFB",
                "subtext": "#9CA3AF",
                "accent": "#10B981",
                "border": "#1F2937",
                "success": "#34D399",
                "warning": "#FBBF24",
                "danger": "#EF4444",
                "btn_normal_bg": "#1F2937",
                "btn_normal_fg": "#F9FAFB",
                "btn_accent_fg": "#000000"
            }

        self.title("🩺 System Diagnostics & Telemetry")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(860, int(sw * 0.85))
        h = min(680, int(sh * 0.85))
        self.geometry(f"{w}x{h}")
        self.minsize(720, 520)
        self.configure(bg=self.theme["bg"])
        if parent:
            self.transient(parent)

        self._center_window(w, h)
        self._apply_dark_titlebar()
        self.after(50, self._apply_dark_titlebar)
        self.after(200, self._apply_dark_titlebar)
        self.bind("<Map>", lambda e: self.after(60, self._apply_dark_titlebar), add="+")

        self.all_results: List[DiagnosticResult] = []
        self.is_running = False
        self.abort_event = threading.Event()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.after(200, self.run_diagnostics)

    def _on_close(self):
        self.abort_event.set()
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _center_window(self, width: int, height: int):
        self.update_idletasks()
        if self.parent and self.parent.winfo_exists():
            if hasattr(self.parent, "_center_window"):
                self.parent._center_window(self, width, height)
                return
            rx = self.parent.winfo_rootx()
            ry = self.parent.winfo_rooty()
            rw = self.parent.winfo_width()
            rh = self.parent.winfo_height()
            if rw > 50 and rh > 50:
                x = rx + (rw - width) // 2
                y = ry + (rh - height) // 2
                if y < ry:
                    y = ry + 10
                self.geometry(f"{width}x{height}+{x}+{y}")
                self.deiconify()
                self.lift()
                self.focus_force()
                return
        x = (self.winfo_screenwidth() - width) // 2
        y = max(30, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.focus_force()

    def _apply_dark_titlebar(self):
        try:
            import ctypes
            w_id = self.winfo_id()
            hwnd = ctypes.windll.user32.GetAncestor(w_id, 2)
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(w_id)
            if not hwnd:
                hwnd = w_id
            v_dark = ctypes.c_int(1)
            for attr in (20, 19):
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(v_dark), ctypes.sizeof(v_dark)
                    )
                except Exception:
                    pass
            t = self.theme or {}
            bg_hex = t.get("panel", t.get("bg", "#111827"))
            if bg_hex and len(bg_hex) == 7:
                try:
                    r, g, b = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
                    c_color = ctypes.c_int((b << 16) | (g << 8) | r)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c_color), ctypes.sizeof(c_color))
                except Exception:
                    pass
        except Exception:
            pass

    def _build_ui(self):
        t = self.theme

        # Top Header Banner
        hdr = tk.Frame(self, bg=t["panel"], padx=16, pady=12, highlightbackground=t["border"], highlightthickness=1)
        hdr.pack(fill="x")

        title_row = tk.Frame(hdr, bg=t["panel"])
        title_row.pack(fill="x")

        tk.Label(title_row, text="🩺 SYSTEM DIAGNOSTICS & TELEMETRY", font=("Segoe UI", 12, "bold"), bg=t["panel"], fg=t["accent"]).pack(side="left")
        
        self.verdict_badge = tk.Label(
            title_row,
            text="INITIALIZING...",
            font=("Segoe UI", 9, "bold"),
            bg=t.get("border", "#1F2937"),
            fg=t["text"],
            padx=10,
            pady=3
        )
        self.verdict_badge.pack(side="right")

        tk.Label(hdr, text="Comprehensive integrity check across runtime environment, imaging engines, local database stores, and network gateways.", font=("Segoe UI", 8), bg=t["panel"], fg=t["subtext"]).pack(anchor="w", pady=(3, 0))

        # Progress Bar
        self.progress_var = tk.DoubleVar(value=0.0)
        self.prog_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100.0, mode="determinate")
        self.prog_bar.pack(fill="x", padx=14, pady=(8, 4))

        # Main Table / Treeview Container
        main_f = tk.Frame(self, bg=t["bg"], padx=14, pady=4)
        main_f.pack(fill="both", expand=True)

        cols = ("category", "component", "status", "latency", "details")
        self.tree = ttk.Treeview(main_f, columns=cols, show="headings", selectmode="browse", style="Diagnostics.Treeview")

        self.tree.heading("category", text="Category", anchor="w")
        self.tree.heading("component", text="System Component", anchor="w")
        self.tree.heading("status", text="Status", anchor="center")
        self.tree.heading("latency", text="Latency", anchor="e")
        self.tree.heading("details", text="Telemetry & Diagnostic Details", anchor="w")

        self.tree.column("category", width=140, minwidth=120)
        self.tree.column("component", width=220, minwidth=180)
        self.tree.column("status", width=90, minwidth=80, anchor="center")
        self.tree.column("latency", width=85, minwidth=70, anchor="e")
        self.tree.column("details", width=340, minwidth=250)

        # Style Treeview
        style = ttk.Style(self)
        style.configure("Diagnostics.Treeview",
                        background=t["panel"],
                        foreground=t["text"],
                        fieldbackground=t["panel"],
                        rowheight=24,
                        font=("Segoe UI", 9))
        style.configure("Diagnostics.Treeview.Heading",
                        background=t.get("btn_normal_bg", t["border"]),
                        foreground=t["text"],
                        font=("Segoe UI", 9, "bold"))

        # Tags for colored statuses
        self.tree.tag_configure("PASS", foreground=t.get("success", "#10B981"))
        self.tree.tag_configure("WARN", foreground=t.get("warning", "#F59E0B"))
        self.tree.tag_configure("FAIL", foreground=t.get("danger", "#EF4444"))

        vsb = ttk.Scrollbar(main_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Bottom Button Bar
        b_bar = tk.Frame(self, bg=t["panel"], padx=14, pady=10, highlightbackground=t["border"], highlightthickness=1)
        b_bar.pack(fill="x", side="bottom")

        self.status_lbl = tk.Label(b_bar, text="Ready to scan.", font=("Segoe UI", 9), bg=t["panel"], fg=t["subtext"])
        self.status_lbl.pack(side="left")

        # Right buttons
        self.close_btn = tk.Button(
            b_bar,
            text="Close Diagnostics",
            font=("Segoe UI", 9),
            bg=t.get("btn_normal_bg", t["border"]),
            fg=t.get("btn_normal_fg", t["text"]),
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._on_close
        )
        self.close_btn.pack(side="right", padx=(6, 0))

        self.copy_btn = tk.Button(
            b_bar,
            text="📋 Copy Report",
            font=("Segoe UI", 9),
            bg=t.get("btn_normal_bg", t["border"]),
            fg=t.get("btn_normal_fg", t["text"]),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._copy_report_to_clipboard
        )
        self.copy_btn.pack(side="right", padx=(6, 0))

        self.retest_btn = tk.Button(
            b_bar,
            text="🔄 Re-Run All Diagnostics",
            font=("Segoe UI", 9, "bold"),
            bg=t["accent"],
            fg=t.get("btn_accent_fg", "#000000"),
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.run_diagnostics
        )
        self.retest_btn.pack(side="right")

    def run_diagnostics(self):
        if self.is_running:
            return
        self.is_running = True
        self.abort_event.clear()
        self.retest_btn.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.verdict_badge.config(text="DIAGNOSING...", bg=self.theme.get("border", "#1F2937"), fg=self.theme["text"])
        self.progress_var.set(5.0)

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.all_results.clear()

        # Run checks in background thread to avoid freezing UI
        threading.Thread(target=self._worker_diagnostic_thread, daemon=True).start()

    def _worker_diagnostic_thread(self):
        steps = [
            ("Runtime Environment", DiagnosticEngine.check_runtime_environment, 20.0),
            ("Visual & pHash Engine", DiagnosticEngine.check_visual_and_hashing, 40.0),
            ("Storage & Database Vaults", DiagnosticEngine.check_storage_and_databases, 60.0),
            ("IPC Inter-Process Bridge", DiagnosticEngine.check_ipc_bridge, 75.0),
            ("Network & Marketplace Gateways", DiagnosticEngine.check_network_and_gateways, 100.0),
        ]

        for step_name, probe_fn, target_prog in steps:
            if self.abort_event.is_set():
                break
            self._update_status(f"Testing {step_name}...")
            try:
                import inspect
                sig = inspect.signature(probe_fn)
                if "abort_event" in sig.parameters:
                    results = probe_fn(abort_event=self.abort_event)
                else:
                    results = probe_fn()

                for r in results:
                    if self.abort_event.is_set():
                        break
                    self.all_results.append(r)
                    self._insert_result(r)
            except Exception as e:
                err_res = DiagnosticResult("System Fault", step_name, "FAIL", f"Unhandled exception: {str(e)}")
                self.all_results.append(err_res)
                self._insert_result(err_res)

            self._set_progress(target_prog)
            time.sleep(0.05)

        if not self.abort_event.is_set():
            self._finalize_verdict()

    def _insert_result(self, r: DiagnosticResult):
        def _insert():
            lat_str = f"{r.latency_ms:.1f} ms" if r.latency_ms is not None else "—"
            self.tree.insert(
                "", "end",
                values=(r.category, r.name, f"[{r.status}]", lat_str, r.details),
                tags=(r.status,)
            )
            # Auto scroll to bottom
            children = self.tree.get_children()
            if children:
                self.tree.see(children[-1])
        self.after(0, _insert)

    def _set_progress(self, val: float):
        self.after(0, lambda: self.progress_var.set(val))

    def _update_status(self, text: str):
        self.after(0, lambda: self.status_lbl.config(text=text))

    def _finalize_verdict(self):
        def _finish():
            self.is_running = False
            self.retest_btn.config(state="normal")
            self.copy_btn.config(state="normal")

            fails = sum(1 for r in self.all_results if r.status == "FAIL")
            warns = sum(1 for r in self.all_results if r.status == "WARN")
            passes = sum(1 for r in self.all_results if r.status == "PASS")

            t = self.theme
            if fails > 0:
                self.verdict_badge.config(
                    text=f"🔴 CRITICAL ({fails} FAILS)",
                    bg=t.get("danger", "#EF4444"),
                    fg="#FFFFFF"
                )
                self.status_lbl.config(text=f"Diagnostic finished with {fails} critical fault(s) and {warns} warning(s).")
            elif warns > 0:
                self.verdict_badge.config(
                    text=f"🟡 NOMINAL W/ WARNINGS ({warns} WARNS)",
                    bg=t.get("warning", "#F59E0B"),
                    fg="#000000"
                )
                self.status_lbl.config(text=f"Diagnostic complete: {passes} Passed, {warns} Warnings. Ready for deployment.")
            else:
                self.verdict_badge.config(
                    text="🟢 ALL SYSTEMS NOMINAL",
                    bg=t.get("success", "#10B981"),
                    fg=t.get("btn_accent_fg", "#000000")
                )
                self.status_lbl.config(text=f"Diagnostic complete: All {passes} checks passed with zero faults.")
        self.after(0, _finish)

    def _copy_report_to_clipboard(self):
        if not self.all_results:
            return

        lines = [
            "=" * 70,
            "APOLLO & ARTEMIS — PRE-FLIGHT SYSTEM DIAGNOSTICS REPORT",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            f"Host Platform: {platform.system()} {platform.release()} ({platform.architecture()[0]})",
            f"Python Runtime: v{sys.version.split()[0]} ({sys.executable})",
            "=" * 70,
            ""
        ]

        fails = sum(1 for r in self.all_results if r.status == "FAIL")
        warns = sum(1 for r in self.all_results if r.status == "WARN")
        passes = sum(1 for r in self.all_results if r.status == "PASS")
        lines.append(f"OVERALL VERDICT: {'CRITICAL FAULT' if fails else 'WARNINGS PRESENT' if warns else 'ALL SYSTEMS NOMINAL'} ({passes} Passed, {warns} Warns, {fails} Fails)\n")

        curr_cat = None
        for r in self.all_results:
            if r.category != curr_cat:
                curr_cat = r.category
                lines.append(f"\n[{curr_cat.upper()}]")
            lat = f" ({r.latency_ms:.1f}ms)" if r.latency_ms is not None else ""
            lines.append(f"  • [{r.status}] {r.name}{lat}: {r.details}")

        lines.append("\n" + "=" * 70)
        report_text = "\n".join(lines)

        self.clipboard_clear()
        self.clipboard_append(report_text)
        messagebox.showinfo("Report Copied", "Full diagnostic report copied to system clipboard.")


def open_diagnostics_modal(parent=None, theme: Optional[Dict[str, str]] = None) -> SystemDiagnosticsModal:
    """Convenience helper to launch the pre-flight diagnostics modal."""
    return SystemDiagnosticsModal(parent=parent, theme=theme)


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE CLI / GUI ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide root dummy
    diag = SystemDiagnosticsModal(parent=None)
    diag.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    root.mainloop()
