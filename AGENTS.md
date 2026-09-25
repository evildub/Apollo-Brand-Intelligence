# Apollo Brand Intelligence — Master Engineering Rules & Architectural Invariants

> **Notice to AI Pair Programmers**: This file defines mandatory, non-negotiable architectural invariants, development workflows, and UI standards for Apollo Brand Intelligence. These rules supersede assumptions and must be consulted on every task.

---

## 1. Architectural Decision-Making & Communication Protocol

1. **Ask Before Assuming (Measure Twice, Cut Once)**:
   - When a requirement, design decision, or edge-case is ambiguous, stop and ask the user for clarification before writing or modifying code.
   - A 30-second conversation saves hours of complex code rollback. Never guess user intent on architectural or data-flow changes.

2. **No Immediate Auto-Deploy / Push to Git**:
   - Never commit, push, or release code to GitHub automatically without explicit user authorization (e.g., "push to github", "update git", "make a release").
   - Keep development, testing, and debugging strictly local until the user explicitly directs a release.

3. **Descriptive, Granular Commits**:
   - When committing, write precise, informative commit messages detailing *what* changed, *why* it changed, and which components were affected. Never use generic commit messages like "updates" or "bug fix".

---

## 2. GitHub Releases & Packaging Pipeline

When explicitly instructed to update GitHub or publish a release:
1. **Full Compiled ZIP Release is Mandatory**:
   - Never push git commits alone without attaching the compiled standalone distribution ZIP release asset.
2. **The 4-Step Release Pipeline**:
   - **Step 1: Build Executable**: Run `build_exe.bat` to compile `dist/Apollo Brand Intelligence/`.
   - **Step 2: Package & Publish GitHub Release**: Run `python release.py` (or specify `--version vX.Y.Z`). This compresses the full compiled distribution into `ApolloBrandIntelligence-vX.Y.Z.zip`, uploads the `.zip` archive to GitHub Releases via `gh release`, and syncs/pushes source code to `origin main`.
   - **Step 3: Verification**: Verify that `gh release list` and `gh release view <tag>` show the release with the attached `.zip` asset.
   - **Step 4: Report**: Provide the direct release download link (`https://github.com/evildub/Apollo-Brand-Intelligence/releases/tag/<tag>`) and confirm the attached zip file.

---

## 3. UI/UX, Layout & Theme Invariants

1. **Strict Theme Continuity**:
   - Maintain uniform visual hierarchy across the main window, all sub-windows, dialogs, and popups.
   - Adhere strictly to the established Apollo dark-mode palette (`#1e1e2e`, `#252538`, `#2b2b40`, `#3b82f6`, `#a6adc8`, etc.), standard typography, rounded button styling, and border accents. Never introduce mismatched native OS widgets or unstyled white dialogs.

2. **Preemptive Icon & Layout Spacing**:
   - **Top Toolbar is Frozen**: NEVER add new buttons to the top toolbar row. All new modals and features MUST live inside `⚙ Settings ▾`, the right-click context menu, or a keyboard shortcut.
   - **Window Button Padding**: Always use `self._btn()` with the standard `padx=(0, 4)` spacing; never introduce custom pixel margins that cause crowding.
   - **Menu Accelerator Alignment**: NEVER use `accelerator="..."` on isolated menu items in Tkinter. Always embed shortcuts directly in the label string: `label="Icon Name (Shortcut)..."` (e.g. `label="📚 Field Guide (F1)"`).
   - **Clean Menu Emojis**: Never use emojis with Unicode variation selectors (`\ufe0f`) or compound glyphs in menus or buttons. Always use clean single-width glyphs with exactly one space before the text.

3. **Strict Multi-Monitor Window Centering**:
   - Every modal, preview, progress window, or dialog MUST be explicitly positioned relative to the parent window (`transient(parent)`, `grab_set()`, and geometry calculation using parent coordinate offsets).
   - Dialogs must NEVER open on a secondary display or get lost behind background windows.

4. **Universal Mousewheel Scrolling Invariant**:
   - Every modal or dialog containing a scrollable container (`tk.Canvas` with `ttk.Scrollbar`) MUST bind `<MouseWheel>` recursively to:
     1. The canvas itself.
     2. The inner scroll frame.
     3. All child widgets contained within the scroll frame (using a recursive widget walk).
     4. The top-level dialog or tab switch handler, routing scroll deltas to the currently active tab's canvas.
   - A scrollable view must NEVER fail to scroll regardless of where the mouse cursor is hovering inside the container.

5. **Live Progress Feedback & Activity Log Transparency**:
   - No silent background operations: analysts must always see what Apollo is doing.
   - Progress bars must never appear permanently stalled. For long operations (e.g., massive multi-thousand row Excel exports or dredging), ensure the progress bar updates incrementally with row counts or pulses in indeterminate mode.
   - The Activity Log must clearly report filtering decisions (e.g., Search Hygiene inclusions/exclusions, anti-bot puzzle detections, and rate-limit backoffs).

6. **Zero Main-Thread Blocking**:
   - All network calls, scrapers, image hashing (pHash), reverse dredging, and disk exports must execute on background daemon threads or thread pools. The Tkinter GUI main thread must remain completely responsive at all times.

---

## 4. Data Integrity, Session Safety & Diagnostic Backdoors

1. **Non-Destructive Persistence (Preserve Analyst Work)**:
   - Data stores (`data.json`, session vaults, active dossiers) must be atomic and resilient against sudden program exits or force-closes.
   - Never wipe or overwrite dossier listings without explicit confirmation. Merges and updates must append and deduplicate safely.

2. **Always Preserve Diagnostic Backdoors**:
   - While 1-Click high-level automation is the standard for daily operations, **never remove or break manual diagnostic controls or backdoors**.
   - If a target marketplace changes its layout unexpectedly, analysts must always retain the manual ability to enrich individual records, inspect raw payloads, or force specific pipelines.

3. **True 1-Click Pipeline Dispatch**:
   - The unified 1-Click action pipeline must automatically inspect the item URL / marketplace signature and dynamically route to the correct scraper and seller enrichment logic without requiring manual overrides.

---

## 5. Scraper Resilience & Process Hygiene

1. **Adversarial Resilience & Graceful Fallbacks**:
   - Marketplaces change HTML and anti-bot systems without notice. A scraper must **never** crash unhandled or halt a batch run due to missing DOM selectors or modified layout classes.
   - Always implement safe selector extraction chains with fallbacks. If an element cannot be found, log the anomaly and gracefully continue.

2. **Dual Stealth & Visible Scraping with Mid-Run Switching**:
   - Scrapers must support both Stealth (headless CDP-cloaked) and Visible (investigative browser) modes.
   - Scrapers must support dynamic mid-run switching via Chrome DevTools Protocol (CDP) window bounds adjustment so analysts can inspect active sessions without aborting the job list.

3. **Zero Zombie Browser Processes**:
   - When a scan completes, fails, or is cancelled by the user, all spawned browser processes (`chrome.exe`, `msedge.exe`, chromedriver workers) and CDP connections must terminate cleanly and aggressively.
   - Orphaned background processes must never linger to consume CPU/RAM or lock user-data directories (`SingletonLock`).

---

## 6. Documentation & Testing Rigor

1. **Mandatory Field Guide & Documentation Sync**:
   - Whenever a new marketplace, button, modal, or workflow change is introduced, proactively update:
     - `TOOLS_DATA` in `field_guide_modal.py` (Tab 3: Apollo Tools & Modules).
     - The Analyst Field Guide / User Manual (`field_guide.md`).
   - Documentation must never lag behind code.

2. **Single Source of Truth for Versioning**:
   - Maintain a single source of truth: `APP_VERSION = "X.Y.Z"` at the top of `main.py`.
   - Never define duplicate `VERSION` variables that shadow each other.
   - The window title (`self.title()`), about dialog, and `release.py` MUST all reference `APP_VERSION`.

3. **Zero Blind Merges (Test Suite Verification)**:
   - Run `python run_tests.py` before declaring any task complete to ensure 100% test pass rate across all unit and integration tests.
   - Every bug discovered and fixed in the field must have a corresponding regression unit test added to `run_tests.py` to ensure it never recurs.
