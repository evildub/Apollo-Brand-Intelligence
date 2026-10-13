---
trigger: always_on
description: Mandatory rules and invariants for the UI Craftsman Agent.
---

# UI Craftsman — Specialist Invariants

1. **Strict Dark Palette Continuity**:
   - Every frame, dialog, popup, or widget must bind to the active theme palette (`apollo/ui/theme_definitions.py`).
   - Zero stark-white backgrounds. Zero native unstyled Tk dialogs.

2. **Themed MessageBox Proxy Invariant**:
   - Never import or use `tkinter.messagebox` directly.
   - All messages must route through Apollo's `ThemedMessageBoxProxy` or `_show_themed_*` methods.

3. **Multi-Monitor Window Centering**:
   - Every `tk.Toplevel` modal must call `center_window_on_parent(win, parent, width, height)`.
   - Modals must clamp within virtual desktop geometry to never open off-screen.

4. **Universal Mousewheel Scroll**:
   - All scrollable canvas containers must bind `<MouseWheel>` recursively to canvas, inner frame, and all child widgets.

5. **Top Bar Stability**:
   - Never add buttons to the top toolbar row. New controls belong in `⚙ Settings ▾`, right-click menus, or hotkeys.
