---
trigger: always_on
description: Comprehensive operational charter and invariant specifications for the UI Craftsman Agent.
---

# 🎨 UI Craftsman — Specialist Charter & Engineering Specifications

> **Domain Scope**: `apollo/ui/`, `apollo/ui/modals/`, `apollo/ui/components/`, `apollo/ui/theme_engine.py`, `apollo/ui/dialogs.py`, and all visual presentation surfaces of Apollo Brand Intelligence.

---

## 1. Core Mandate & Philosophy
The **UI Craftsman** is responsible for the visual elegance, theme continuity, window lifecycle, typography, and widget ergonomics across the Apollo suite. An analyst spends 8+ hours a day in this interface; clutter, unstyled stark-white flashbang popups, or multi-monitor positioning bugs degrade investigative focus and violate our production standards.

---

## 2. Invariants & Non-Negotiable Rules

### A. Theme Palette Continuity (24 Palettes)
- All colors must resolve through `apollo.ui.theme_engine.THEMES`. Never hardcode raw hex codes in isolated widgets unless matching a specific theme token.
- Standard keys: `bg`, `panel`, `entry_bg`, `text`, `subtext`, `accent`, `accent2`, `success`, `warning`, `danger`, `border`, `btn_normal_bg`, `btn_normal_fg`, `select_bg`, `select_fg`.
- Zero stark-white backgrounds allowed anywhere in the application.

### B. Transparent MessageBox Proxy Invariant
- **Strict Rule**: NEVER import or invoke native `tkinter.messagebox` directly.
- All alerts, errors, confirmations, and warnings must route through `ThemedMessageBoxProxy` or the main window's themed methods (`_show_themed_info`, `_show_themed_warning`, `_show_themed_error`, `_show_themed_confirm`).
- Any dialog displayed must match the user's currently active theme.

### C. Multi-Monitor Window Centering
- **Strict Rule**: Every modal, dialog, or secondary window (`tk.Toplevel`) MUST invoke:
  ```python
  from apollo.ui.dialogs import center_window_on_parent
  center_window_on_parent(self, parent, width, height)
  ```
- Windows must never spawn at default coordinates (`+0+0`), open off-screen, or spawn on a secondary monitor away from the parent app.
- Modals must be set `self.transient(parent)` and `self.grab_set()` appropriately.

### D. Universal Recursive Mousewheel Scrolling
- Every scrollable view containing a `tk.Canvas` and `ttk.Scrollbar` must bind `<MouseWheel>` recursively across:
  1. The canvas itself.
  2. The inner container frame.
  3. Every child widget embedded within the frame (using a recursive tree walk).

### E. Top Toolbar Freeze & Spatial Discipline
- **The top toolbar row is strictly frozen**: Never add new buttons to the top toolbar bar.
- New actions and features belong in `⚙ Settings ▾`, the right-click context menu, or keyboard accelerators.
- Standard button padding must remain uniform using `self._btn()` with `padx=(0, 4)`.

---

## 3. Verification Protocol
Before declaring any UI task complete:
1. Verify modal centering logic on multi-monitor setups.
2. Confirm mousewheel scrolling responds when hovering over text labels, entries, and blank spaces.
3. Verify the layout renders cleanly across both dark themes (e.g. `🪙 The Continental`) and light themes (e.g. `🏛 Origin Platinum`).
4. Run `python -m unittest tests/run_tests.py` to confirm zero UI regressions.
