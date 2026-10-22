# Apollo Brand Intelligence — Architecture & Agent Engineering Specification

> **Scope**: Canonical engineering standards, package boundaries, data contracts, and verification protocols for the Apollo Brand Intelligence suite. All automated coding agents and contributors must adhere to these invariants before staging or committing changes.

---

## 1. Engineering Operating Principles (High-Signal, Evidence-Driven Protocol)

When operating as the AI engineering copilot:
- **Direct Technical Candor & Zero Filler**: Lead with findings, root causes, or completed diffs. Eliminate hollow pleasantries, restatements of prompt text, or boilerplate narrative.
- **Concise Technical Output**: Keep responses tight and high-signal. State what changed, the architectural reason, blast radius, and verification evidence.
- **Clarification Over Assumption**: If an architectural requirement or data contract is underspecified or ambiguous, solicit clarification before modifying production code.
- **Evidence Over Assertion**: Never claim a feature or fix works without executing a runtime verification check or test suite. If an execution path has not been run, explicitly mark it `unverified`.

---

## 2. System Architecture & Package Boundaries

Apollo operates on a domain-isolated modular package architecture paired with a decoupled compliance engine (**Artemis**):

```text
Apollo-Enterprise/
├── apollo/
│   ├── app.py                 # Primary application coordinator (EbayTool)
│   ├── core/                  # DataStore, SessionVault, VisualCatalog (pHash), Contracts
│   ├── ui/                    # Theme Engine (24 palettes), Dialogs, Modals (16), Components
│   ├── scrapers/              # ScraperRegistry factory, Batch Importer, Marketplace Engines (21)
│   ├── export/                # ExcelExporter (18-Column A–R Contract), VeRO Disclosure Parser
│   └── compliance/            # Artemis Rights Engine, IPC Bridge, Argus Listing Sentinel
├── tests/                     # Automated unit, regression, and compliance suites (115 tests)
├── .agents/rules/             # Domain-specific engineering charters
├── run_apollo.py              # Application & CLI entrypoint (--artemis, --argus)
└── verify.py                  # Single-command pre-commit verification gate
```

### Twin-Engine Decoupling (`Apollo` vs. `Artemis`)
1. **Apollo (`apollo/app.py`) — Reconnaissance & Triage**:
   - Multi-marketplace scraping, query hygiene, 64-bit DCT `pHash` visual clustering, seller network correlation, and dossier staging.
   - Persists operational state in `data.json` (AppData / local workspace).
2. **Artemis (`apollo/compliance/artemis.py`) — Rights Enforcement & Notice Assembly**:
   - Standalone compliance application for Letter of Authority (LOA) registries, statutory takedown notice generation, and post-takedown monitoring (**Argus**).
   - Persists legal state independently in `artemis_data.json`.
   - Communicates with Apollo strictly via `apollo/compliance/artemis_bridge.py` JSON intake queues (`artemis_intake/`) or CLI invocation (`python run_apollo.py --artemis`).

---

## 3. Core Engineering Standards & Code Quality

1. **Smallest Effective Diff**:
   - Modify only the code required to solve the stated task. Avoid unrequested cosmetic refactors, variable renames, or scope creep.
   - In large coordinator modules (`apollo/app.py`), isolate edits surgically and verify surrounding state bindings.
2. **Strict Type & Contract Fidelity**:
   - Use type annotations and docstrings on public classes and methods.
   - All exported spreadsheets must adhere to `EXPORT_HEADERS` (`Columns A–R`) defined in `apollo/core/contracts.py` and consumed by `apollo/export/exporter.py`.
3. **Structured Exception Handling**:
   - Catch specific exceptions, log actionable context via `logging.getLogger("Apollo")`, and degrade gracefully. Never use bare `except:` blocks that silently swallow runtime failures.
4. **Source Control Discipline**:
   - Create atomic local commits with descriptive messages (`<type>(<scope>): <summary>`) after verifying changes.
   - **Never** push to remote repositories (`git push`), create tags, or publish releases without explicit user instruction.
5. **Credential & Data Hygiene**:
   - Never commit session cookies, `.db`/`.sqlite3` files, `data.json`, `artemis_data.json`, `session_vault.enc`, client PII, or internal environment markers.
6. **Cold-Start Map & Token Discipline**:
   - **Never Read `apollo/app.py` End-to-End**: Use grep/symbol search first, then read only the targeted 80–150 line slice.
   - **Canonical vs. Root Shim Map** (Always edit canonical modules under `apollo/`; never edit root compatibility shims):
     - UI Coordinator: `apollo/app.py` (never `main.py`)
     - Modals: `apollo/ui/modals/*.py` (never inline inside `apollo/app.py`)
     - Themes & Dialogs: `apollo/ui/themes.py`, `apollo/ui/dialogs.py` (never `theme_definitions.py`)
     - Scrapers: `apollo/scrapers/engines/*_scraper.py` & `apollo/scrapers/registry.py` (never root `*_scraper.py` shims)
     - Export & Contracts: `apollo/core/contracts.py`, `apollo/export/exporter.py` (never `exporter.py`)
     - Compliance & Disclosure: `apollo/compliance/artemis.py`, `apollo/compliance/vero_parser.py` (never `vero_pdf_parser.py`)
   - **Targeted Verification First**: Do not run the full 65-second `python verify.py` on routine edits unless requested; use `<2s` targeted checks (`verify.check_private_terms()`, `verify.check_package_imports()`, or a single `unittest` class).

---

## 4. UI, Threading & Window Management Invariants

1. **Non-Blocking Main Thread**:
   - Network I/O, Playwright browser automation, perceptual image hashing (`compute_phash`), and openpyxl workbook generation must run on background daemon threads or `ThreadPoolExecutor` workers.
2. **Theme Continuity & Dialog Routing**:
   - All colors must resolve dynamically from `apollo.ui.themes.THEMES`.
   - Never invoke native unstyled `tkinter.messagebox` directly; route all user prompts through `ThemedMessageBoxProxy` (`apollo/ui/dialogs.py`).
   - All `ttk.Progressbar` instances must apply themed trough and accent styles.
3. **Multi-Monitor Modal Centering**:
   - Every `tk.Toplevel` dialog or modal must position itself relative to its parent window via `center_window_on_parent(win, parent, width, height)` and bind `self.transient(parent)`.
4. **Recursive Mousewheel Binding**:
   - Any scrollable `tk.Canvas` container must bind `<MouseWheel>` across the canvas, inner frame, and all descendant widgets recursively.
5. **Toolbar & Menu Alignment Stability**:
   - The primary top toolbar layout is fixed. Expose new tools or utilities through `⚙ Settings ▾`, context menus, or keyboard shortcuts.
   - All leading icons in `self.settings_menu` and `_show_result_context_menu` must use single-codepoint `East_Asian_Width=W` characters (`unicodedata.east_asian_width(c) == 'W'`) without `\ufe0f` variation selectors.

---

## 5. Marketplace Scraper & Extraction Standards

1. **Strict Platform Isolation**:
   - Modifications to a specific marketplace engine in `apollo/scrapers/engines/` must never alter dispatch routing or query parsing for other platforms.
   - All scraper engines register and instantiate through `apollo/scrapers/registry.py` (`ScraperRegistry`).
2. **Exact Query Fidelity**:
   - Store and seller sweeps must query only the exact brands or terms selected by the analyst. Never automatically expand a parent corporate brand into unselected sub-brands.
3. **3-Tier Extraction Resilience**:
   - Implement cascading extraction: (1) semantic DOM selectors, (2) structural HTML fallbacks, and (3) embedded JSON-LD / state script parsing.
4. **Process & Browser Hygiene**:
   - All spawned Chromium/Edge browser contexts and CDP sessions must close deterministically on job completion, cancellation, or error to prevent orphaned processes or profile locks.
5. **Cross-Subsystem Verification**:
   - Any scraper update must be validated across: (1) Direct Store Search, (2) Global Organic Search, (3) Full Store Inventory Sweeps, (4) Connected Seller Network correlation, (5) Authorized Dealer Whitelist filtering, (6) Seller Enrichment, and (7) Artemis Bridge dispatch.

---

## 6. Specialist Domain Charters (`.agents/rules/`)

Tasks are partitioned across six domain specifications located in `.agents/rules/`:

| Domain Specialist | Package Scope | Rule Specification |
| :--- | :--- | :--- |
| **UI Craftsman** | `apollo/ui/*` | [`.agents/rules/ui_craftsman.md`](.agents/rules/ui_craftsman.md) |
| **Scraper Sentinel** | `apollo/scrapers/*` | [`.agents/rules/scraper_sentinel.md`](.agents/rules/scraper_sentinel.md) |
| **Export Officer** | `apollo/export/*`, `apollo/core/contracts.py` | [`.agents/rules/export_officer.md`](.agents/rules/export_officer.md) |
| **Compliance Lead** | `apollo/compliance/*` | [`.agents/rules/compliance_lead.md`](.agents/rules/compliance_lead.md) |
| **Intel & Graph Strategist** | `apollo/core/*` | [`.agents/rules/intel_strategist.md`](.agents/rules/intel_strategist.md) |
| **QA & Release Marshal** | `tests/*`, `verify.py`, `build_exe.bat` | [`.agents/rules/qa_marshal.md`](.agents/rules/qa_marshal.md) |

---

## 7. Verification & Build Pipeline

### Pre-Commit Verification Gate
Run the unified verification script before finalizing changes:
```bash
python verify.py
```
`verify.py` executes:
1. **Repository Sanitization Check**: Confirms zero restricted or sensitive terms exist in tracked files.
2. **Architecture & Contract Audit**: Verifies package imports, `EXPORT_HEADERS` alignment, `SessionVault` path resolution, and modal integrity.
3. **Full Regression Suite (115 Tests)**:
   - Core Suite (`python -m unittest tests/run_tests.py` — 89 tests)
   - Compliance & Rights Suite (`python -m unittest tests/run_artemis_tests.py tests/test_argus_compliance.py` — 26 tests)

### Standalone Executable Build
To compile the standalone Windows distribution (`Apollo Brand Intelligence.exe` and `Artemis.exe`):
```bash
build_exe.bat
```
Output binaries and bundled runtime assets are written to `dist/Apollo Brand Intelligence/`.
