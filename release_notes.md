# Apollo Brand Intelligence v3.3.2 — Akamai Anti-Throttle Resilience & Native Shopify Integration

### 🛒 eBay Scraper Resilience & Akamai Edge Diagnostics
- **Transient Edge Auto-Reload**: When eBay's Akamai edge serves a momentary rate-limit error page (`Something went wrong on our end` / `Error Page | eBay`), Apollo now pauses for 1.8s and automatically reloads the search URL once, allowing the edge threshold to lift and pulling listings cleanly.
- **Accurate Throttle Reporting in Activity Log**: Eliminated false "0 results or store was not found" messages when Akamai blocks an IP. Transient error pages and security checks are now explicitly flagged as `[IP THROTTLE / BOT CHALLENGE]`.
- **First-Term Cold-Start Auto-Retry**: Added automatic handshake retry for the initial query of a session after cold start, preventing cold-cache failures.
- **Inter-Term Pacing Jitter**: Integrated 1.2s–2.2s randomized human jitter between consecutive queries within a store to keep burst traffic below Akamai rate-limiting thresholds.
- **Extended Session Warmup**: Increased initial cookie jar stabilization pre-flight delay from 0.6s to 1.8s.

---

### 🛍️ Native Shopify Scraper & Sector Cleanliness
- **Native Shopify Scraper (`shopify_scraper.py`)**: Added dedicated storefront scraping via direct store catalog sweeps (`/products.json`, `/search/suggest.json`) and global ecosystem brand discovery across `myshopify.com` stores.
- **Strict Marketplace Isolation**: Eliminated legacy fallbacks that routed unhandled platforms to eBay. Selecting Shopify or direct URLs now runs their native scrapers or previews without eBay contamination.
- **Dropdown Cleanliness**: Renamed sector dropdown from `🌐 Independent Websites` to `🌐 Websites`.

---

### 🏪 Store Search Fidelity & Pipeline Fixes
- **No Parent Brand Auto-Expansion in Store Searches**: Store searches search ONLY the exact brands or sub-brands targeted by the user. Removed unwanted corporate parent-to-subbrand auto-expansion.
- **Printerval Auto-Pipeline Seller Enrichment**: Fixed missing `defaultdict` import in 1-Click Auto-Pipeline seller enrichment.
- **Fixed Missing `random` Import**: Added missing `random` import to `main.py` header, ensuring jitter and retries execute without `NameError`.

---

### 🏹 The Apollo & Artemis Initiative
- **Twin-Engine Architecture**: Integrated the Artemis Rights Engine (`artemis.py`) with decoupled bridge interface (`artemis_bridge.py`), dedicated LOA/rights registry (`artemis_data_store.py`), and test suite (`run_artemis_tests.py`).
- **Pre-Flight System Diagnostics**: Added system diagnostics modal and telemetry probes (`system_diagnostics.py`).
- **Master Rulebook (`AGENTS.md`)**: Codified Section 9: Marketplace Isolation & Cross-Functional Verification Protocol.