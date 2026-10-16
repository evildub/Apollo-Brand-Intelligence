# 🦅 Apollo Brand Intelligence (Enterprise Edition)

[![Architecture](https://img.shields.io/badge/Architecture-Agent--First%20Modular-blue.svg)](#architecture)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](#requirements)
[![Tests](https://img.shields.io/badge/Tests-89%20Core%20%7C%2026%20Compliance-success.svg)](#test-suite)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green.svg)](#)

Apollo Brand Intelligence is an enterprise investigative workstation designed for Brand Protection analysts, counsel, and investigators. It automates multi-marketplace threat discovery, merchant de-anonymization, rogue network mapping, and legal compliance notice generation.

---

## 🏛️ Architecture Overview

Apollo is engineered with an **Agent-First Modular Architecture**, partitioning operational responsibilities into discrete, domain-isolated packages governed by specialist agent charters:

```
Apollo-Enterprise/
├── apollo/
│   ├── core/              # DataStore, SessionVault, VisualCatalog, Voice, Contracts
│   ├── ui/                # Theme Engine (24 palettes), Dialogs, Modals (16), Components
│   │   ├── modals/        # Specialized Investigation Modals (Brand Registry, Dossier, etc.)
│   │   └── components/    # Reusable widgets (tooltips, indicators)
│   ├── scrapers/          # Scraper Sentinel domain (ScraperRegistry + 21 engines)
│   │   └── engines/       # eBay, AliExpress, Printerval, Redbubble, Etsy, TikTok, etc.
│   ├── export/            # Export Officer domain (Excel 18-col A–R exporter, VeRO parser)
│   └── compliance/        # Compliance Lead domain (Artemis rights engine, Argus sentinel)
├── tests/                 # Comprehensive regression and compliance test suites (115 tests)
├── .agents/rules/         # Operational charters for specialist AI domain agents
├── run_apollo.py          # Enterprise runtime entrypoint (--artemis, --argus)
└── verify.py              # Single-command pre-commit verification gate
```

---

## ⚡ Quickstart

### 1. Prerequisites
- **Python 3.10+** (64-bit recommended)
- **Playwright Chromium runtime** (for dynamic rendering and bot-shield traversal)

### 2. Installation
Clone the repository and install required dependencies:

```bash
git clone <repo-url> Apollo-Enterprise
cd Apollo-Enterprise
pip install -r requirements.txt
playwright install chromium
```

### 3. Launching Apollo
Run the application via the dedicated launcher or Python entrypoint:

```bash
run_apollo.bat
# or
python run_apollo.py
```

---

## 🧪 Test Suite & Quality Verification

Apollo enforces a strict zero-regression policy. All tests must pass before staging or building binaries.

### Canonical Enterprise Verification Gate (1-Command All-In-One Check)
```bash
python verify.py
```
This runs the full 115-test regression battery (89 Core + 26 Compliance), checks modular package imports, and validates repository sanitization guards.

---

## 🤖 Multi-Agent Governance Model

Engineering and refactoring tasks are routed through specialist domain agent charters documented in [`AGENTS.md`](AGENTS.md) and [`.agents/rules/`](.agents/rules/):

| Specialist Agent | Domain Package | Key Responsibilities |
| :--- | :--- | :--- |
| **🎨 UI Craftsman** | `apollo/ui/*` | Theme consistency (24 palettes), multi-monitor centering, zero native messageboxes, layout integrity |
| **🕷️ Scraper Sentinel** | `apollo/scrapers/*` | Marketplace crawling (21 engines), 7-point audit, DOM fallback selectors, anti-bot resilience |
| **📊 Export Officer** | `apollo/export/*` | 18-column (`A`–`R`) contract fidelity, openpyxl auto-formatting, VeRO disclosures |
| **⚖️ Compliance Lead** | `apollo/compliance/*` | Artemis legal notice generator, Argus listing status classification, LOA tracking |
| **🧠 Intel & Graph Strategist** | `apollo/core/*` | Perceptual image hashing (`pHash`), syndicate graph correlation, session vault management |
| **🛡️ QA & Release Marshal** | `tests/`, `verify.py` | 100% regression gatekeeper, PyInstaller builds, distribution smoke testing |

---

## 🔒 Data Hygiene & Security

- **Automated Sanitization Gate**: Pre-commit checks and `verify.py` block restricted internal markers or sensitive tokens from entering tracked files.
- **Local State Isolation**: All `.db`, `.sqlite3`, `.enc`, `sessions/`, `data/`, `data.json`, and `artemis_data.json` runtime artifacts are git-ignored.
- **Controlled Release**: Commits are recorded locally; remote pushes require explicit authorization.
