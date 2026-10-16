---
trigger: always_on
description: Comprehensive operational charter and invariant specifications for the UI Craftsman Agent.
---

# 🎨 UI Craftsman — Specialist Charter & Engineering Specifications

> **Domain Scope**: `apollo/ui/`, `apollo/ui/modals/`, `apollo/ui/themes.py`, `apollo/ui/dialogs.py`, and all visual presentation surfaces in `apollo/app.py`.

---

## 1. Core Mandate & Philosophy
The **UI Craftsman** is responsible for the visual elegance, theme continuity, window lifecycle, typography, and widget ergonomics across the Apollo suite. An analyst spends 8+ hours a day in this interface; clutter, unstyled stark-white flashbang popups, or multi-monitor positioning bugs degrade investigative focus and violate our production standards.

---

## 2. Invariants & Non-Negotiable Rules

### A. Theme Palette Continuity (24 Palettes)
- All colors must resolve through `apollo.ui.themes.THEMES`. Never hardcode raw hex codes in isolated widgets unless matching a specific theme token.
- Standard keys: `bg`, `panel`, `entry_bg`, `text`, `subtext`, `accent`, `accent2`, `success`, `warning`, `danger`, `border`, `btn_normal_bg`, `btn_normal_fg`, `select_bg`, `select_fg`.
- Zero stark-white backgrounds allowed anywhere in the application.

### B. Modular Modal Architecture (`apollo/ui/modals/`)
- **Strict Rule**: Never define new `tk.Toplevel` modal classes inline inside `apollo/app.py`.
- All standalone modal classes must reside in dedicated modules under `apollo/ui/modals/` and be imported into `apollo/app.py`.
- Root-level paths resolved inside `apollo/ui/` or `apollo/core/` must resolve to the repository root (`os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`), never a package subdirectory.

### C. Transparent MessageBox Proxy Invariant
- **Strict Rule**: NEVER import or invoke native `tkinter.messagebox` directly.
- All alerts, errors, confirmations, and warnings must route through `ThemedMessageBoxProxy` or the main window's themed methods (`_show_themed_info`, `_show_themed_warning`, `_show_themed_error`, `_show_themed_confirm`).
- Any dialog displayed must match the user's currently active theme.

### D. Multi-Monitor Window Centering
- **Strict Rule**: Every modal, dialog, or secondary window (`tk.Toplevel`) MUST invoke `parent._center_window(self, width, height)` or `center_window_on_parent(self, parent, width, height)` from `apollo.ui.dialogs`.
- Windows must never spawn at default coordinates (`+0+0`), open off-screen, or spawn on a secondary monitor away from the parent app.
- Modals must be set `self.transient(parent)` and `self.grab_set()` appropriately.

### E. Universal Recursive Mousewheel Scrolling
- Every scrollable view containing a `tk.Canvas` and `ttk.Scrollbar` must bind `<MouseWheel>` recursively across:
  1. The canvas itself.
  2. The inner container frame.
  3. Every child widget embedded within the frame (using a recursive tree walk).

### F. Top Toolbar Freeze & Menu Alignment Discipline
- **The top toolbar row is strictly frozen**: Never add new buttons to the top toolbar bar.
- **Menu Icon Alignment (`East_Asian_Width=W`)**: Every leading icon in `self.settings_menu` and `_show_result_context_menu` MUST be a single-codepoint Unicode character with `unicodedata.east_asian_width(c) == 'W'` and zero `\ufe0f` variation selectors so Windows GDI renders all menu labels on an identical vertical column.
- **Menu Anchor**: `📚 Analyst Field Guide (F1)...` and `🧭 About Apollo...` must always remain anchored at the very bottom of `⚙ Settings ▾`, and destructive actions (`❌ Remove Selected`, `🧹 Clear All Results`) must remain anchored at the very bottom of the right-click context menu.
- Any new cascade submenu added to `self.settings_menu` must be registered in `_apply_theme` so dynamic theme switching styles it automatically.

---

## 3. Verification Protocol
Before declaring any UI task complete:
1. Verify modal centering logic and theme rendering.
2. Verify all menu icons pass `unicodedata.east_asian_width(c) == 'W'`.
3. Run fast targeted verification (`python -c "import apollo.app, verify; assert verify.check_package_imports(); assert verify.check_private_terms()"`), reserving full test suite runs for major releases or explicit user requests.
