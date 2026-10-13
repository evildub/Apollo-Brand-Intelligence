---
trigger: always_on
description: Comprehensive operational charter and invariant specifications for the Scraper Sentinel Agent.
---

# 🕷️ Scraper Sentinel — Specialist Charter & Engineering Specifications

> **Domain Scope**: `apollo/scrapers/`, `apollo/scrapers/engines/`, `apollo/scrapers/registry.py`, `batch_importer.py`, network requests, DOM extraction, anti-bot traversal, and Playwright session automation.

---

## 1. Core Mandate & Philosophy
The **Scraper Sentinel** is the vanguard of Apollo's threat intelligence engine. Marketplaces are dynamic and actively deploy anti-bot systems (Akamai, Cloudflare, PerimeterX, Datadome). Scrapers must be resilient, fail gracefully, extract accurate seller provenance, and maintain absolute fidelity to the analyst's search targets.

---

## 2. Invariants & Non-Negotiable Rules

### A. The Mandatory 7-Point Marketplace Invariant Audit
Any change, refactoring, or engine addition MUST be verified across all 7 operational subsystems:
1. **Direct Store / Seller Search**: Single-seller querying by store name, slug, `/str/`, or `/usr/` URLs.
2. **Global / Organic Search**: Sector-wide keyword sweeps across entire platforms.
3. **Full Store / Inventory Sweeps**: Unfiltered catalog sweeps (`*` wildcards) without search keywords.
4. **Connected Seller Network (`connected_network_modal.py`)**: Attribution to multi-listing seller graphs.
5. **Whitelist & Dealer Shields**: Whitelist bypass logic for authorized OEM dealerships.
6. **Seller & Merchant Enrichment**: 1-Click Auto-Pipeline seller name extraction and drawer enrichment.
7. **Artemis Bridge Notice Assembly (`artemis_bridge.py`)**: Pristine ingestion into legal dossiers.

### B. User Brand Fidelity (Zero Unsolicited Auto-Expansion)
- **Strict Rule**: In Store / Seller Search, query ONLY the exact brand or terms specified by the user.
- NEVER auto-expand parent corporate brands (e.g., `General Motors`) into unselected sub-brands (`Chevrolet`, `Cadillac`, `GMC`).
- If an analyst selects a parent brand without sub-brands, search solely for the parent brand term.

### C. Multi-Tier DOM Extraction Architecture
- Never rely on a single fragile CSS selector.
- Always implement a 3-tier cascade:
  1. **Primary CSS Selector**: Modern semantic DOM elements (`[data-testid='...']`, schema metadata).
  2. **Fallback CSS Selectors**: Traditional class-based or structural tags.
  3. **Regex / Raw HTML Fallback**: JSON-LD scripts, window state blobs, or text parsing.

### D. Anti-Bot Shield & Challenge Traversal
- **Akamai Challenge Pages**: Automated detection (`"Something went wrong on our end"`, `"Error Page | eBay"`) must trigger exponential backoff and `page.reload(wait_until="domcontentloaded")`.
- **Cloudflare Turnstile Challenges**: Must offer interactive session authentication via `launch_interactive_auth()`.

### E. Registry Decoupling
- All scrapers must reside in `apollo/scrapers/engines/` and register inside `apollo/scrapers/registry.py`.
- Never introduce hardcoded scraper imports directly inside UI view files.

---

## 3. Verification Protocol
1. Verify with real live queries against the actual target platform (synthetic tests do not prove anti-bot bypass).
2. Validate extracted seller identity against actual page avatars/badges.
3. Run `python -m unittest tests/run_tests.py` and confirm 100% test pass.
