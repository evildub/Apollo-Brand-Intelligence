---
always_on: true
description: Mandatory rules for Apollo Brand Intelligence GitHub updates, UI standards, versioning, and field guide documentation
---

# CRITICAL RULES: Apollo Brand Intelligence

## 1. GitHub Releases & Push Conditions
1. **DO NOT PUSH TO GITHUB UNLESS EXPLICITLY INSTRUCTED**:
   - Never push a new version, commit, or release to GitHub unless the user explicitly tells you to do so (e.g., "update github", "upload to github", "push a new version", "release to github", "make the release").
   - During regular tasks, code modifications, or bug fixes, keep changes local and verified.

2. **WHEN INSTRUCTED TO PUSH / UPDATE GITHUB**:
   - **IT MUST ALWAYS INCLUDE THE FULL ZIP RELEASE**:
     - Never just push git commits without the compiled standalone distribution ZIP release.
     - When a GitHub update/version push is requested, you must execute the full release pipeline:
       - **Step 1: Build Executable**: Run `build_exe.bat` to compile `dist/Apollo Brand Intelligence/`.
       - **Step 2: Package & Publish GitHub Release**: Run `python release.py` (or specify `--version vX.Y.Z`). This compresses the full compiled distribution into `ApolloBrandIntelligence-vX.Y.Z.zip`, uploads the `.zip` archive to GitHub Releases via `gh release`, and syncs/pushes source code to `origin main`.
       - **Step 3: Verification**: Verify that `gh release list` and `gh release view <tag>` show the release with the attached `.zip` asset.
       - **Step 4: Report**: Provide the direct release download link (`https://github.com/evildub/Apollo-Brand-Intelligence/releases/tag/<tag>`) and confirm the attached zip file.

## 2. Strict UI Layout & Icon Spacing Invariants
1. **Top Toolbar is Frozen**: NEVER add new buttons to the top toolbar row. All new modals and features MUST live inside `⚙ Settings ▾`, the right-click context menu, and a keyboard shortcut.
2. **Menu Accelerator Alignment**: NEVER use `accelerator="..."` on isolated menu items in Tkinter. Always embed shortcuts directly in the label string: `label="Icon Name (Shortcut)..."` (e.g. `label="📚 Field Guide (F1)"`).
3. **Clean Menu Emojis**: Never use emojis with Unicode variation selectors (`\ufe0f`) or compound glyphs in menus or buttons. Always use clean single-width glyphs with exactly one space before the text.
4. **Window Button Padding**: Always use `self._btn()` with the standard `padx=(0, 4)` spacing; never introduce custom pixel margins.

## 3. Version Alignment Standard
- Maintain a single source of truth: `APP_VERSION = "X.Y.Z"` at the top of `main.py`.
- Never define duplicate `VERSION` variables that shadow each other.
- The window title (`self.title()`), about dialog, and `release.py` MUST all reference `APP_VERSION`.

## 4. Mandatory Field Guide Documentation
- Whenever a new modal, tool, or major intelligence capability is created, it MUST be documented in `TOOLS_DATA` in `field_guide_modal.py` (Tab 3: Apollo Tools & Modules) with its Name, Shortcut, Purpose, and Workflow.

## 5. Universal Mousewheel Scrolling Invariant
- Every modal or dialog containing a scrollable container (`tk.Canvas` with `ttk.Scrollbar`) MUST bind `<MouseWheel>` recursively to:
  1. The canvas itself.
  2. The inner scroll frame.
  3. All child widgets contained within the scroll frame (using a recursive widget walk).
  4. The top-level dialog or tab switch handler, routing scroll deltas to the currently active tab's canvas.
- A scrollable view must NEVER fail to scroll regardless of where the mouse cursor is hovering inside the container.
