# Apollo Brand Intelligence v3.4.0 — Enterprise Tactical Suite

[![Version](https://img.shields.io/badge/Version-3.4.0-blue.svg?style=flat-square)](https://github.com/evildub/Apollo-Brand-Intelligence/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(x64)-0078D6.svg?style=flat-square)](https://github.com/evildub/Apollo-Brand-Intelligence)
[![Compliance](https://img.shields.io/badge/Enterprise%20Compliance-100%25%20Verified-00C853.svg?style=flat-square)](https://github.com/evildub/Apollo-Brand-Intelligence)
[![Security](https://img.shields.io/badge/Security-Local%20Execution%20%7C%20Zero%20Telemetry-38BDF8.svg?style=flat-square)](https://github.com/evildub/Apollo-Brand-Intelligence)

**Apollo Brand Intelligence v3.4.0** is a specialized, high-velocity intellectual property protection, anti-counterfeit discovery, and enforcement triage platform engineered for brand security analysts, legal enforcement teams, and investigative operations.

---

## 🌟 Core Capabilities

### 1. Multi-Platform Market Discovery (22+ Platforms)
Automates high-precision discovery across primary e-commerce, print-on-demand, and document repositories:
- **Tier-1 E-Commerce:** Global eBay ecosystem (13 international locales), Amazon, Walmart, AliExpress, Mercado Libre (7 Latin American regions), TikTok Shop, Vinted (10 European locales).
- **Print-on-Demand (POD) Dredge Engines (10 Platforms):** Printblur, Redbubble, Printerval, TeePublic, Spreadshirt, Zazzle, CafePress, Threadless, TeeSpring, Fine Art America (up to 1-to-74 SKU variant expansion).
- **Direct Web & Specialized Repositories:** Native Shopify Stores (`/products.json`), Etsy, ManoMano, Temu, Wish, Scribd OEM manuals.

### 2. 🛡️ Argus URL Compliance Sentinel
- **Real-Time Availability Auditing:** Mass-audits enforcement URLs to confirm takedown compliance (Active vs. Delisted / 404).
- **High-Velocity Async Probes:** Audits 100+ URLs in under 30 seconds with zero false delisting flags and multi-threaded connection pools.
- **Takedown SLA Verification:** Generates timestamped compliance reports for brand counsel and platform SLA benchmarking.

### 3. 🏹 Artemis Rights Engine & Air-Gapped IPC
- **Companion Enforcement Hub:** Direct 1-click dispatch from Apollo to the standalone Artemis Rights Engine (`Artemis.exe`).
- **Corporate LOA Vault:** Local management of trademark registrations, copyright schedules, and Letters of Authorization.
- **Assisted Portal Submissions:** Accelerated submission sessions for Amazon Brand Registry, Walmart Brand Portal, and platform VeRO portals.

### 4. Reverse Visual Dredge & Asset Protection
- **64-bit DCT pHash Fingerprinting:** Detects exact photographic asset theft and digital clone listings in seconds using multithreaded parallel visual hashing.
- **Automated Merchant Intel Enrichment:** Instantly extracts registered seller handles, live prices, item locations, and registered origin flags directly from discovered visual clones.

### 5. Cross-Border Threat Intelligence & 3PL Detection
- **Domestic vs. Drop-Ship Heuristics:** Identifies cross-border shell merchants, overseas manufacturing syndicates, and domestic 3PL fulfillment hubs.
- **Automated Threat Badging:** Flags suspect listings with tactical threat indicators (`🚨 Drop-Ship Hub`, `🇨🇳 Cross-Border Direct`, `🛡️ Dealership Verified`).

### 6. Standardized 18-Column Enterprise Export
- **18-Column Standard Schema:** Formatted to exact enterprise import specifications with normalized platform domains and column C embedded thumbnails.
- **Court-Ready Legal Dossiers:** Exports structured, audit-ready compliance spreadsheets ready for counsel review and legal notice attachments.

---

## 🚀 Quick Start (Analyst Deployment)

### Standalone Executables (Recommended)
1. Download the latest release from [Releases](https://github.com/evildub/Apollo-Brand-Intelligence/releases/latest).
2. Extract `ApolloBrandIntelligence-v3.4.0.zip`.
3. Launch:
   - **`Apollo Brand Intelligence.exe`** for forensic scanning, visual clustering, and dossier compilation.
   - **`Artemis.exe`** for rights registry, LOA management, and platform enforcement.

### Python Developer Environment
```bash
# Clone the repository
git clone https://github.com/evildub/Apollo-Brand-Intelligence.git
cd Apollo-Brand-Intelligence

# Install dependencies
pip install -r requirements.txt

# Run Apollo Brand Intelligence
python main.py

# Run Artemis Rights Engine
python artemis.py
```

---

## 🛡️ Architecture & Security Posture

- **100% Local Execution:** All database queries, image hashes, and report generation run strictly on local analyst hardware. Zero third-party telemetry or cloud data leakage.
- **Persistent Anti-Bot Session Engine:** Uses dedicated local browser profiles with synchronous interactive challenge recovery to prevent IP throttling during large store audits.
- **Cloudflare Stealth Fallback:** Direct HTTP requests automatically fall back to persistent stealth browser automation when Cloudflare challenge pages are encountered.
- **Thread-Safe Queue Execution:** Supports live pausing, stop controls, and real-time result streaming.

---

## 📊 Technical Architecture

| Component | Module | Responsibility |
| :--- | :--- | :--- |
| **Apollo Orchestrator** | `main.py` | GUI, multi-monitor window management, theme engine, queue runner |
| **Artemis Engine** | `artemis.py` | Rights registry, LOA management, takedown notice compilation |
| **Artemis Bridge** | `artemis_bridge.py` | Secure air-gapped IPC and batch transfer pipeline |
| **Argus Sentinel** | `argus_modal.py` | Real-time URL availability auditing and takedown SLA verification |
| **eBay Engine** | `scraper.py` | URL-first seller extraction, rate-limit recovery, Playwright driver |
| **Visual Dredge** | `visual_harvester.py` | Multithreaded DCT pHash image clone detection |
| **Catalog DB** | `visual_catalog.py` | Reference asset fingerprint repository |
| **Marketplace Scrapers** | `*_scraper.py` | Scraper modules for 22+ supported e-commerce and POD platforms |
| **Threat Engine** | `data_store.py` | JSON configuration, whitelist registry, 3PL threat heuristics |
| **Compliance Exporter** | `exporter.py` | Enterprise 18-column Excel dossier formatting |
| **Batch Importer** | `batch_importer.py` | Ad-hoc URL list ingestion and single-item enrichment |

---

## 🔒 Confidentiality & License
*Proprietary Brand Protection Tooling — For Authorized Corporate Enforcement & Legal Investigation Use Only.*
