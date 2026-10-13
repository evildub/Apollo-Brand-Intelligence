# Apollo Brand Intelligence — Master Engineering Rules & Architectural Invariants

> **Notice to AI Pair Programmers**: This file defines mandatory, non-negotiable architectural invariants, development workflows, and UI standards for Apollo Brand Intelligence. These rules supersede assumptions and must be consulted on every task.

---

## 1. Architectural Decision-Making & Communication Protocol

1. **Ask Before Assuming (Measure Twice, Cut Once)**:
   - When a requirement, design decision, or edge-case is ambiguous, stop and ask the user for clarification before writing or modifying code.
   - A 30-second conversation saves hours of complex code rollback. Never guess user intent on architectural or data-flow changes.

2. **Commit Locally, Push Only on Approval**:
   - **Commit** = a local save point. After every completed, tested change, make a local commit. This is required, not optional, and needs no approval. It is the change documentation and the rollback point.
   - **Push / Release / Tag** = anything that leaves this machine (Bitbucket, GitHub, any remote). NEVER push, force-push, tag, or publish a release without explicit user authorization (e.g., "push it", "update the remote", "make a release").
   - Before starting a new task or agent session, make sure the working tree is committed (checkpoint commit if needed).

3. **Descriptive, Granular Commits**:
   - One logical change per commit. Write precise, informative commit messages detailing *what* changed, *why* it changed, and which components were affected. Never use generic commit messages like "updates" or "bug fix".
   - When reporting completed work to the user, include the commit hash(es).

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

3. **Strict Multi-Monitor Window Centering & Zero Native Dialogs**:
   - Every modal, preview, progress window, or dialog MUST be explicitly positioned relative to the parent window using `center_window_on_parent(win, parent, width, height)`.
   - Modals must NEVER spawn unpositioned, default to `+0+0`, open on a secondary display off-screen, or get lost behind background windows.
   - **Zero Stark-White Native Messageboxes**: Never use native unstyled `tkinter.messagebox` dialogs directly. All alerts, questions, and warnings must route through Apollo's theme-adaptive modal dialogs (`ThemedMessageBoxProxy`, `_show_themed_info`, `_show_themed_confirm`, etc.).
   - **Themed Progressbars**: Any `ttk.Progressbar` in dialogs or modals must be explicitly styled with themed trough (`entry_bg`) and accent colors (`accent`). Native unstyled white progress bars are strictly prohibited.


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

---

## 7. OPSEC, Confidentiality & Internal Secrets Invariants

1. **Strict Prohibition on Exposing Internal / Employer System Names**:
   - **NEVER** write the name of the employer's enterprise base-of-record system, or any other proprietary backend system name, anywhere in this repository: code, identifiers, docstrings, comments, tests, docs, UI labels, exports, or commit messages.
   - The exact forbidden term(s) are listed in `.agents/rules/private_terms.md`. That file is local only and gitignored. Never commit it, and never copy its contents into tracked files.
   - Use neutral terminology instead: *"Enterprise"*, *"Enterprise Base of Record"*, *"Enterprise 18-Column Schema"*, *"Central Rights System"*, or *"Enterprise Dossier"*.
   - Exception: legitimate vehicle brand and model names in catalog or test data (e.g. Hyundai's luxury line G70/G80/GV80) are domain data and are allowed.

2. **Absolute Secrecy of Hidden Themes & Easter Eggs**:
   - Hidden/secret themes (e.g., The Continental, future easter eggs) and their unlock triggers, cheat codes, or secret keystrokes must **NEVER** be listed, exposed, or detailed in user-facing menus, documentation, the Field Guide, tooltips, or public docs.
   - Keep easter egg conditions and unlock paths strictly internal in code. Do not spoil the surprise or explain how to unlock them in public-facing interfaces.

---

## 8. The Apollo & Artemis Twin-Engine Architecture

1. **Strict Separation of Concerns**:
   - **Apollo (`main.py`)**: *The Eyes* — Dedicated to Multi-Sector Reconnaissance, 19+ Scrapers, Search Hygiene, DCT pHash Visual Dredging, Syndicate Correlation, and Dossier Triage.
   - **Artemis (`artemis.py`)**: *The Hands* — Dedicated to Rights Enforcement, Authenticated Portal Automation (Amazon Brand Registry, Walmart Brand Portal, VeRO, POD portals), Rights Owner / LOA Registries, and Formal Notice Filing.
   - **Zero Monolithic Bloat**: Artemis must never import Apollo's scraping engines. Apollo must never embed heavy Playwright portal automation loops directly inside `main.py`.

2. **The Decoupled Bridge Interface (`artemis_bridge.py`)**:
   - Apollo communicates with Artemis strictly via `artemis_bridge.py` using standardized intake JSON files written to a dedicated drop directory (`artemis_intake/`).
   - Artemis is 100% standalone: enforcement analysts can launch `artemis.py` directly without Apollo running, or Apollo can spawn it via the 1-click bridge.

3. **Isolated State & Session Vaults**:
   - Artemis maintains its own independent configuration and database (`artemis_data.json`), completely decoupled from Apollo's `data.json`.
   - Browser profiles, portal authentication tokens, and legal rights credentials reside strictly within Artemis's own session management.

4. **Independent Test Execution**:
   - Artemis maintains its own dedicated, high-speed test suite (`run_artemis_tests.py`), verifying the bridge, data store, legal notice generator, LOA registry, and portal dispatch logic independently of Apollo's extensive test suite (`run_tests.py`).
   - Run `python run_artemis_tests.py` when modifying rights enforcement or bridge logic.

5. **Universal Theme-Adaptive Dialogs (Zero Native White Popups)**:
   - Every dialog, confirmation prompt, alert, or file notification in both Apollo and Artemis MUST use theme-adaptive modals (`_show_themed_info`, `_show_themed_confirm`, `_show_themed_warning`, `_show_themed_error`).
   - Never use unstyled native Windows `tkinter.messagebox` which causes blinding white flashbangs on dark themes.

---

## 9. Marketplace Isolation & Cross-Functional Verification Protocol

1. **Strict Marketplace Isolation (Zero Collateral Contamination)**:
   - An update or bug fix for one marketplace (e.g. eBay, Shopify, Printerval, Redbubble) must NEVER alter, degrade, or cross-contaminate the scraping, parsing, or queuing behavior of any other marketplace unless explicitly instructed by the user or mutually verified.
   - Core dispatch routines (`_process_queue`, `_add_to_queue`) must maintain explicit, isolated branches for each marketplace. Unhandled or unknown platforms must NEVER fall back into an arbitrary scraper (e.g., never default an unknown or web platform to the eBay scraper).

2. **Mandatory 360° Cross-Functional Verification for Any Marketplace Change**:
   - Whenever an update is made to ANY marketplace scraper, store resolver, or queuing path, the change MUST be verified across ALL functional subsystems touching that platform before declaring completion:
     1. **Direct Store / Seller Search**: Single-seller inventory querying by username, store slug, `/str/`, and `/usr/` URLs.
     2. **Global / Organic Search**: Sector-wide search sweeps with keywords or brand targets without store constraints.
     3. **Full Store / Inventory Sweeps**: Unfiltered catalog sweeps (`*` includes) across all departments.
     4. **Connected Seller Network (`connected_network_modal.py`)**: Multi-listing seller graph correlation and cross-store attribution.
     5. **Whitelist & Dealer Filtering**: Dealer exemption checks, false positive exclusion, and brand safety shields.
     6. **Seller & Merchant Enrichment**: Both 1-Click Auto-Pipeline seller resolution AND manual backdoor / context-menu enrichment.
     7. **Artemis Bridge & Notice Assembly (`artemis_bridge.py`)**: Data ingestion into legal dossiers and format compliance.

3. **Absolute Fidelity to User Selection (No Unsolicited Auto-Expansion)**:
   - In a Store / Seller Search, search ONLY the exact brands or keywords targeted by the user.
   - NEVER auto-expand a parent corporate brand (e.g. `General Motors`) into unselected sub-brands (`Chevrolet`, `Cadillac`, `GMC`, etc.) in store searches. If the user wants specific sub-brands, they will select them.
   - Distinguish strictly between:
     - **Store Search**: Restricted to the user's targeted handle with user-selected search terms.
     - **Organic Search**: Global marketplace sweeps paired with user-entered violation keywords.

4. **Empirical Verification Over Synthetic Test Passes**:
   - Passing synthetic unit test assertions does NOT prove live marketplace resilience against active anti-bot systems, session cookies, or dynamic HTML changes.
   - Whenever touching scraper handles, session management, or routing logic, execute real live test queries against the actual target marketplace to confirm real listings are returned before reporting back to the user.

---

## 10. Engineering Standards (General Code Quality)

1. **Match Before You Write**: Read the surrounding code first and match its existing patterns, naming, and style before introducing anything new.
2. **Smallest Effective Change**: Solve the stated problem with the minimum necessary diff. No unrequested refactors, renames, or "while I'm here" edits.
3. **Typed, Named, Documented**: Use type hints and clear names, and write docstrings for public functions and classes.
4. **No Silent Failures**: Catch specific exceptions only. Log them with context. Never use bare `except:` and never swallow errors quietly.
5. **Claims Require Evidence**: Never report something as working without an actual run. If it hasn't been verified, say "unverified." (Test-suite and regression-test requirements are in §6.3.)
6. **Explain Before Implementing**: For non-trivial changes, describe the approach and get approval before writing code (see §1.1).
7. **Flag Tech Debt**: Call out shortcuts, duplication, or fragile code instead of quietly adding to it.
8. **Surgical Edits in Large Files**: In very large files (e.g. `main.py` / `app.py`), touch only the affected region and state the blast radius of the change.

---

## 11. Multi-Agent Governance & Specialist Squad Model

Apollo-Enterprise operates under an **Agent-First Modular Architecture**, coordinated by an Executive Manager agent that dispatches discrete, domain-bounded tasks to specialized domain agents:

```
                      ┌────────────────────────────────────────┐
                      │          Executive Manager             │
                      │    (Orchestration & Verification)      │
                      └──────────────────┬─────────────────────┘
                                         │
     ┌──────────────┬──────────────┬─────┴──────┬──────────────┬──────────────┐
     ▼              ▼              ▼            ▼              ▼              ▼
┌───────────┐  ┌───────────┐  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│UI Craftsman│ │Scraper Snt│  │Export Off.│ │Compl. Lead│ │Intel Strat│ │ QA Marshal│
│(apollo/ui)│  │(scrapers) │  │(export)   │ │(complianc)│ │ (core)    │ │ (tests)   │
└───────────┘  └───────────┘  └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

### Specialist Squad Charters & Rules:
1. **🎨 UI Craftsman** (`.agents/rules/ui_craftsman.md`):
   - **Domain**: `apollo/ui/`, modals, components, themes, layout widgets.
   - **Invariants**: Strict theme palette fidelity (23 themes), multi-monitor window centering (`center_window_on_parent`), recursive mousewheel scrolling, zero native white messageboxes (`ThemedMessageBoxProxy`), top toolbar button freeze.

2. **🕷️ Scraper Sentinel** (`.agents/rules/scraper_sentinel.md`):
   - **Domain**: `apollo/scrapers/`, scraper engines (15+ marketplaces), batch importer.
   - **Invariants**: 7-Point Marketplace Invariant audit on any modification; exact user brand fidelity (zero unsolicited sub-brand expansion); clean DOM fallback extraction; empirical verification with real listings.

3. **📊 Export Officer** (`.agents/rules/export_officer.md`):
   - **Domain**: `apollo/export/`, Excel/CSV exporter, VeRO disclosures, report styling.
   - **Invariants**: Strict openpyxl auto-column sizing and header formatting; zero data loss on batch export; VeRO statement accuracy and brand rights attributions.

4. **⚖️ Compliance Lead** (`.agents/rules/compliance_lead.md`):
   - **Domain**: `apollo/compliance/`, Artemis engine, Argus sentinel, legal notice generation.
   - **Invariants**: Zero-leakage notice assembly; verified corporate metadata; strict status classification (`Active`, `Removed`, `Ended`, `Blocked`); LOA tracking.

5. **🧠 Intel & Graph Strategist** (`.agents/rules/intel_strategist.md`):
   - **Domain**: `apollo/core/`, visual catalog (`pHash`), syndicate graph correlation, session vault encryption, contracts.
   - **Invariants**: 64-bit DCT pHash calculations on background workers; Hamming distance thresholds (<=5 clone, <=10 variant); AES-GCM encrypted persistence in `session_vault.enc`; ListingRecord typed contracts.

6. **🛡️ QA & Release Marshal** (`.agents/rules/qa_marshal.md`):
   - **Domain**: `tests/`, `verify.py`, `build_exe.bat`, packaging, security auditing.
   - **Invariants**: 100% pass across all 115 tests; zero employer term leakage; PyInstaller compilation smoke tests; maintenance of canonical `python verify.py` gatekeeper.

### Operational Principles:
- **Investigation Protocol**: A regression or bug in one domain triggers a cross-check in connecting domains (e.g. scraper change -> check UI table rendering + export columns).
- **Mandatory Verification**: Every domain change must pass its respective test harness (`python verify.py`) before staging.
- **Enterprise Ready**: Codebase strictly enforces zero employer terminology in commit history or tracked files. All pushes require explicit human authorization.

---

## 12. LLM-Agnostic Portability & The 70/30 Operating Protocol

### A. Model & Platform Independence (Antigravity, Cohere, Claude, OpenAI)
This repository is engineered to be **100% LLM-agnostic**. Whether this codebase is paired with Google Antigravity, Cohere Command, Claude, or any future frontier model:
1. **Zero Proprietary Prompt Dependency**: All architectural rules, invariants, and constraints are codified in Markdown within the repository itself (`AGENTS.md` and `.agents/rules/*.md`), rather than locked in any single proprietary web UI or tool memory.
2. **Deterministic Verification Gateways**: Quality is enforced by reproducible test harnesses (`python -m unittest tests/run_tests.py`), not subjective model opinions. Any AI system operating on this repository must run and pass these suites before claiming victory.
3. **Self-Documenting Specialist Charters**: Each specialist rule file (`ui_craftsman.md`, `scraper_sentinel.md`, `export_officer.md`, `compliance_lead.md`) contains complete, standalone context so any LLM booted in any environment can immediately assume the exact operational role without historical conversation baggage.

### B. The 70/30 Operating Cadence
Development operates on a hybrid dual-track model:
1. **The 70% Executive Track (General Contractor / Tech Lead Hub)**:
   - Orchestrates multi-package features, breaks down tasks, runs regression test suites, coordinates cross-domain bug investigations, and commits verified checkpoints.
2. **The 30% Specialist Track (Direct Surgical Strike Chats)**:
   - The user engages in direct, focused conversations with individual specialists (`🎨 UI Craftsman`, `🕷️ Scraper Sentinel`, `📊 Export Officer`, `⚖️ Compliance Lead`) for deep, isolated domain work.
   - **Handshake Protocol**: After any direct update in a specialist chat, the changes land in the shared workspace, and the Executive Lead validates across the remaining modules before merging or committing.


