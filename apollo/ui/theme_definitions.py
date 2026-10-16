"""
Shared theme palette definitions for Apollo Brand Intelligence and Artemis Rights Engine.
Re-exports from the canonical apollo.ui.theme_engine module to eliminate duplicate dictionaries.
"""

from apollo.ui.theme_engine import (
    THEMES,
    THEME_QUOTES,
    THEME_SUBHEADERS,
    CONTINENTAL_QUOTES,
    FIR_QUOTES,
)

__all__ = [
    "THEMES",
    "THEME_QUOTES",
    "THEME_SUBHEADERS",
    "CONTINENTAL_QUOTES",
    "FIR_QUOTES",
]
