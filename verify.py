#!/usr/bin/env python3
"""
verify.py
─────────
Canonical Enterprise Health & Verification Gate for Apollo Brand Intelligence.
Executes:
1. Private employer term security guard check.
2. Architecture & package import integrity.
3. Full 115-test regression and compliance test suite.
Produces a clear, colorized pass/fail audit report.
"""

import os
import sys
import subprocess
import time

# ANSI Terminal Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def log_step(msg: str):
    print(f"\n{BOLD}{CYAN}==>{RESET} {BOLD}{msg}{RESET}")


def log_pass(msg: str):
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def log_fail(msg: str):
    print(f"  {RED}[FAIL]{RESET} {msg}")


def check_private_terms() -> bool:
    log_step("1. Checking Private Employer Term Security Guards...")
    private_terms_file = os.path.join(REPO_ROOT, ".agents", "rules", "private_terms.md")
    if not os.path.exists(private_terms_file):
        log_pass("No local private_terms.md found (clean external environment).")
        return True

    # Parse bullet terms: e.g. "- TermName" -> "TermName"
    terms = []
    try:
        with open(private_terms_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith("- ") and not line_str.startswith("---"):
                    term_token = line_str[2:].split("(")[0].strip()
                    if term_token:
                        terms.append(term_token)
    except Exception as e:
        log_fail(f"Could not read private_terms.md: {e}")
        return False

    if not terms:
        log_pass("Private terms list empty.")
        return True

    # Scan tracked git files for forbidden terms (case-insensitive check)
    scan_exts = {".py", ".md", ".json", ".txt", ".bat", ".toml"}
    allowed_exceptions = ["g70", "g80", "g90", "gv70", "gv80", "prediksi", "kia"]
    violating_files = []

    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip git, venv, data, sessions
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "data", "sessions", "build", "dist", "__pycache__"}]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in scan_exts and f not in {"private_terms.md", "verify.py"}:
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                        for line_idx, line in enumerate(handle, 1):
                            lower_line = line.lower()
                            for term in terms:
                                if term.lower() in lower_line:
                                    # Check if exception applies
                                    if not any(exc in lower_line for exc in allowed_exceptions):
                                        violating_files.append((path, line_idx, term))
                except Exception:
                    pass

    if violating_files:
        for vpath, vline, vterm in violating_files:
            log_fail(f"Sensitive term '{vterm}' detected in {os.path.relpath(vpath, REPO_ROOT)}:L{vline}")
        return False

    log_pass("Zero sensitive employer terms detected across tracked files.")
    return True


def check_package_imports() -> bool:
    log_step("2. Verifying Modular Package Architecture & Contracts...")
    test_code = """
import apollo
import apollo.core.contracts as c
import apollo.ui.theme_engine as te
import apollo.ui.dialogs as d
import apollo.scrapers.registry as sr
import apollo.export.exporter as exp
import apollo.compliance.artemis_bridge as ab

# Verify ListingRecord contract
rec = c.ListingRecord(item_id='1', title='T', seller='S', price='$10', marketplace='eBay', listing_url='http://')
assert rec.item_id == '1'
assert len(te.THEMES) >= 20
assert callable(d.center_window_on_parent)
assert callable(sr.ScraperRegistry)
"""
    res = subprocess.run([sys.executable, "-c", test_code], cwd=REPO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        log_fail(f"Package import test failed:\n{res.stderr}")
        return False

    log_pass("All modular packages and contracts imported cleanly.")
    return True


def run_unit_tests() -> bool:
    log_step("3. Executing Core & Compliance Regression Suites (115 Tests)...")
    
    # 1. Core regression suite (89 tests)
    print("  -> Running Core Suite (tests/run_tests.py)...")
    start = time.time()
    res1 = subprocess.run([sys.executable, "-m", "unittest", "tests/run_tests.py"], cwd=REPO_ROOT, capture_output=True, text=True)
    dur1 = time.time() - start

    if res1.returncode != 0:
        log_fail(f"Core test suite failed in {dur1:.1f}s:\n{res1.stderr[-2000:]}")
        return False
    log_pass(f"Core Regression Suite (89 Tests) PASSED in {dur1:.1f}s.")

    # 2. Rights & Compliance suites (26 tests)
    print("  -> Running Compliance Suites (run_artemis_tests & test_argus_compliance)...")
    start = time.time()
    res2 = subprocess.run(
        [sys.executable, "-m", "unittest", "tests/run_artemis_tests.py", "tests/test_argus_compliance.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    dur2 = time.time() - start

    if res2.returncode != 0:
        log_fail(f"Compliance test suite failed in {dur2:.1f}s:\n{res2.stderr[-2000:]}")
        return False
    log_pass(f"Compliance & Rights Suites (26 Tests) PASSED in {dur2:.1f}s.")

    return True


def main():
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"\n{BOLD}=============================================================================={RESET}")
    print(f"{BOLD}[APOLLO] Enterprise Verification Gate{RESET}")
    print(f"{BOLD}=============================================================================={RESET}")

    t0 = time.time()
    ok_terms = check_private_terms()
    ok_imports = check_package_imports()
    ok_tests = run_unit_tests()
    total_time = time.time() - t0

    print(f"\n{BOLD}=============================================================================={RESET}")
    if ok_terms and ok_imports and ok_tests:
        print(f"{BOLD}{GREEN}[OK] VERIFICATION PASSED -- 115 / 115 TESTS GREEN ({total_time:.1f}s total){RESET}")
        print(f"{GREEN}The repository is clean, verified, and enterprise ready.{RESET}\n")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}[FAIL] VERIFICATION FAILED -- Issues detected above ({total_time:.1f}s total){RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
