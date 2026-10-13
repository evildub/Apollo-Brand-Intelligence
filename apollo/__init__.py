"""
Apollo Brand Intelligence Enterprise Package.
"""

import os
import sys

_PKG_ROOT = os.path.dirname(os.path.abspath(__file__))
_SUBPACKAGES = [
    _PKG_ROOT,
    os.path.join(_PKG_ROOT, "core"),
    os.path.join(_PKG_ROOT, "export"),
    os.path.join(_PKG_ROOT, "compliance"),
    os.path.join(_PKG_ROOT, "scrapers"),
    os.path.join(_PKG_ROOT, "scrapers", "engines"),
    os.path.join(_PKG_ROOT, "ui"),
    os.path.join(_PKG_ROOT, "ui", "modals"),
    os.path.join(_PKG_ROOT, "ui", "components"),
]

for _p in _SUBPACKAGES:
    if _p not in sys.path:
        sys.path.insert(0, _p)
