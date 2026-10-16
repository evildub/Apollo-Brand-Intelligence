"""
Apollo Brand Intelligence — Enterprise Suite
Entry point runner for Apollo-Enterprise.
"""

import os
import sys

# Ensure repository root is on Python module search path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Also ensure apollo core packages resolve cleanly
APOLLO_PKG = os.path.join(REPO_ROOT, "apollo")
if APOLLO_PKG not in sys.path:
    sys.path.insert(0, APOLLO_PKG)

APOLLO_SCRAPERS = os.path.join(APOLLO_PKG, "scrapers")
if APOLLO_SCRAPERS not in sys.path:
    sys.path.insert(0, APOLLO_SCRAPERS)

APOLLO_ENGINES = os.path.join(APOLLO_PKG, "scrapers", "engines")
if APOLLO_ENGINES not in sys.path:
    sys.path.insert(0, APOLLO_ENGINES)

APOLLO_CORE = os.path.join(APOLLO_PKG, "core")
if APOLLO_CORE not in sys.path:
    sys.path.insert(0, APOLLO_CORE)

APOLLO_EXPORT = os.path.join(APOLLO_PKG, "export")
if APOLLO_EXPORT not in sys.path:
    sys.path.insert(0, APOLLO_EXPORT)

APOLLO_COMPLIANCE = os.path.join(APOLLO_PKG, "compliance")
if APOLLO_COMPLIANCE not in sys.path:
    sys.path.insert(0, APOLLO_COMPLIANCE)

APOLLO_MODALS = os.path.join(APOLLO_PKG, "ui", "modals")
if APOLLO_MODALS not in sys.path:
    sys.path.insert(0, APOLLO_MODALS)

APOLLO_COMPONENTS = os.path.join(APOLLO_PKG, "ui", "components")
if APOLLO_COMPONENTS not in sys.path:
    sys.path.insert(0, APOLLO_COMPONENTS)

from apollo.app import EbayTool, APP_VERSION


def main():
    if "--artemis" in sys.argv:
        from apollo.compliance.artemis import ArtemisApp
        theme_k = None
        for i, a in enumerate(sys.argv):
            if a == "--theme" and i + 1 < len(sys.argv):
                theme_k = sys.argv[i + 1]
                break
        artemis_app = ArtemisApp(initial_theme_key=theme_k)
        artemis_app.mainloop()
        return

    if "--argus" in sys.argv:
        import tkinter as tk
        from apollo.compliance.argus_compliance_modal import ArgusComplianceModal
        root = tk.Tk()
        root.withdraw()
        argus_modal = ArgusComplianceModal(master=root)
        argus_modal.protocol("WM_DELETE_WINDOW", lambda: root.destroy())
        root.mainloop()
        return

    app = EbayTool()
    app.mainloop()


if __name__ == "__main__":
    main()
