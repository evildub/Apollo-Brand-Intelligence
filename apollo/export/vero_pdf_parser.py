"""
vero_pdf_parser.py
──────────────────
Backward-compatible re-export shim pointing to the canonical apollo.export.vero_parser module.
"""

from apollo.export.vero_parser import (
    PYPDF_AVAILABLE,
    parse_vero_line,
    parse_vero_text,
    parse_vero_pdf,
    push_to_enforcement_registry,
    export_to_excel,
    export_to_csv,
)
from apollo.export.vero_parser import *  # noqa: F401,F403
