# Apollo Brand Intelligence — State of the Union & Architectural Dossier

> **Purpose**: Master context bridge between Antigravity, GitHub Copilot, and future AI models. Summarizes 5 months of architectural evolution, critical bug fixes, active subsystems, and current backlog.

---

## 1. Executive Summary & Core Identity

- **Application**: Apollo Brand Intelligence (Enterprise Edition)
- **Primary Mission**: High-performance investigative desktop workstation for corporate brand protection analysts, investigators, and IP counsel.
- **Key Capabilities**: Multi-marketplace scraping (15+ platforms), perceptual image hash clustering (`pHash`), rogue seller syndicate mapping, 1-click Auto-Pipeline seller enrichment, 18-column Excel exports, and legal takedown notice generation (Artemis & Argus).
- **Core Partnership**: Built as a pair-programming project between Jer and Trace (AI copilot, synthesized from TARS & CASE).

---

## 2. Architectural Evolution (The Transition from Monolith to Enterprise)

Over 5 months, Apollo grew to a 17,315-line monolith in `main.py`. In October 2026, the project underwent a formal architectural evolution into an **Agent-First Modular Architecture** at `C:\Users\Dub\Desktop\Apollo-Enterprise`:

1. **Domain Package Isolation**:
   - `apollo/core/`: Persistence, session encryption, perceptual catalog, contracts, and APIs.
   - `apollo/ui/`: Theme engine (24 unified palettes), dialogs, multi-monitor centering, and 16 isolated modals in `apollo/ui/modals/`.
   - `apollo/scrapers/`: `ScraperRegistry` factory and 21 marketplace/POD engines.
   - `apollo/export/`: `ExcelExporter` (18-column A–R contract) and unified VeRO disclosure parser.
   - `apollo/compliance/`: Artemis legal rights engine and Argus monitoring sentinel.

2. **Surgical Monolith Peeling**:
   - `apollo/app.py` was peeled by ~3,780 lines (down to ~13,540 lines): theme dictionaries, quote catalogs, `center_window_on_parent`, `ThemedMessageBoxProxy`, and all 6 remaining inline modals (`ExportProgressModal`, `MultiLocaleModal`, `ConnectedNetworkModal`, `ReverseVisualModal`, `WhitelistManagerModal`, `AnalystGuideModal`) now live cleanly in their respective sub-packages.
   - Wired `ScraperRegistry` into `EbayTool` while maintaining backward-compatible scraper attributes.

3. **Immutable Contracts (`apollo/core/contracts.py`)**:
   - `ListingRecord`: Typed dataclass synchronized with production dictionary keys (`url`/`listing_url`, `image_url`/`thumbnail`, `brand`/`brand_targeted`).
   - `EXPORT_HEADERS` & `EXPORT_COLUMNS`: Single source of truth for the standardized 18-column (A–R) Excel layout imported directly by `ExcelExporter`.

---

## 3. Hard-Won Lessons & Non-Negotiable Invariants

1. **The 7-Point Scraper Audit**:
   - Any scraper modification must be validated against: (1) Direct Store Search, (2) Global Organic Search, (3) Full Store Sweeps, (4) Connected Seller Network, (5) Whitelist/Dealer Shields, (6) 1-Click Seller Enrichment, and (7) Artemis Notice Assembly.

2. **Absolute Brand Fidelity (No Unsolicited Sub-Brand Auto-Expansion)**:
   - When a user selects a corporate brand (e.g. `General Motors`), the scraper must NEVER automatically expand searches to unselected sub-brands (`Chevrolet`, `Cadillac`, `GMC`). Search only what the user specifically checked.

3. **Zero Stark-White Popups**:
   - Native `tkinter.messagebox` is transparently proxied by `ThemedMessageBoxProxy` to ensure every dialog matches the user's active theme palette.

4. **Multi-Monitor Window Centering**:
   - Every `tk.Toplevel` modal must call `center_window_on_parent(win, parent, width, height)` to prevent spawning off-screen or on detached secondary monitors.

5. **Universal Recursive Mousewheel Scrolling**:
   - Canvas, inner frame, and all child widgets walk recursively to bind `<MouseWheel>`.

6. **High-Performance Excel Export**:
   - Pre-allocated style singletons and direct column index maps in `exporter.py`.
   - Batch persistence in `data_store.py` (`record_enforcement_scans_batch`), eliminating per-cell disk writes. 1,600 listings export in 2.6s (was 2–3 minutes).

---

## 4. Active Configuration & Key Settings

- **Active Theme**: Jer's active profile runs `🪙 The Continental` (`continental` in `data.json`). Fresh out-of-the-box installations default to standard themes; `🪙 The Continental` is an unlocked/secret theme earned via the achievement/unlock system.
- **Installed Marketplaces**: eBay (14 locales), Mercado Libre (7 locales), AliExpress, Temu, Wish, Redbubble, Printerval, Printblur, TeePublic, Etsy, Spreadshirt, Zazzle, CafePress, Threadless, TeeSpring, Fine Art America, TikTok Shop, ManoMano, Scribd, Shopify.
- **Verification Gate**: `python verify.py` $\rightarrow$ **115 / 115 Tests Passing (100% Pass)**.

---

## 5. Active Backlog & Next Steps

1. **Continued Peeling of `apollo/app.py`**:
   - Extract `results_table.py` (Treeview, row styling, thumbnail caching).
   - Extract `toolbar.py` (search controls, action bars).
   - Extract `context_menus.py` (right-click actions and backdoors).
2. **Scraper Enhancements**:
   - Deepen anti-bot resilience on European locales.
3. **Packaging**:
   - Test standalone compiled executables using `build_exe.bat`.
