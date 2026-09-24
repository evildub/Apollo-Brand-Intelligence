# Apollo Brand Intelligence v3.3.0 — Printblur Platform Integration & Syndicate Hunter

### 👕 Printblur.com Print-on-Demand (POD) Suite
- **Dedicated Scraper Engine (`printblur_scraper.py`)**:
  - Playwright + native Microsoft Edge stealth browser automation with anti-bot evasion (`--disable-blink-features=AutomationControlled`, `--no-sandbox`).
  - Persistent Cloudflare clearance profile (`Apollo_Printblur_Session`) with 1-click interactive authentication helper (`launch_interactive_auth()`).
  - Comprehensive catalog search (`/search?interest={term}&page={page}`), creator sweeps (`/@{creator}`), and storefront sweeps (`/shops/{shop}`).
- **High-Yield POD Variant Dredging (`expand_design_variants`)**:
  - Automatically explodes confirmed infringing designs into 50–90+ real product variants (t-shirts, hoodies, mugs, canvases, blankets, etc.).
  - Title synthesis preserving parent capitalization and artwork context while filtering out unrelated merchandise.
- **Creator & Storefront Enrichment (`enrich_seller_info`)**:
  - Resolves creator and shop handles from product pages and Nuxt hydration state with persistent disk-backed caching (`printblur_seller_cache.json`).
- **Connected Seller Network & Syndicate Discovery (`find_connected_network`)**:
  - Live inspection of product recommendation sliders, viewed carousels, and related merchandise.
  - Perceptual image hashing (`compute_dhash`) with Hamming distance comparison to identify exact photo matches ($d \le 6$) and visual clones ($d \le 14$).

---

### 🌐 Main Application Integration & Workflow Polish
- **UI & Marketplace Controls**:
  - Added `"👕 Printblur.com"` to platform dropdown selector.
  - Added dynamic `👕 Printblur Connect` authentication button and depth selector (`1 Page (50)` up to `10 Pages (500)`).
  - Configured referer headers and placeholder prompts for seamless searching.
- **Multi-Stage Hero Pipeline**:
  - **Stage 1**: Integrated Printblur into automated POD variant expansion.
  - **Stage 2**: Integrated into multi-marketplace creator enrichment registry.
- **Connected Network Modal (`ConnectedNetworkModal`)**:
  - Full platform recognition, carousel scraping, POD syndicate classification, and canonical URL reconstruction (`https://printblur.com/product-p{item_id}`).
- **Regression Test Suite**:
  - Added `test_75_printblur_scraper_contract_and_integration` validating scraper contracts, store resolution, dHash computation, and variant synthesis (75/75 tests passing).