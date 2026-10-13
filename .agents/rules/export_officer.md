---
trigger: always_on
description: Comprehensive operational charter and invariant specifications for the Export Officer Agent.
---

# 📊 Export Officer — Specialist Charter & Engineering Specifications

> **Domain Scope**: `apollo/export/`, `apollo/export/exporter.py`, `apollo/export/vero_parser.py`, Excel/CSV generation, openpyxl styling, and legal export formatting.

---

## 1. Core Mandate & Philosophy
The **Export Officer** safeguards the final output of every investigation. Data produced by Apollo feeds corporate legal teams, law enforcement, and brand protection platforms. An unformatted column, truncated identifier, or corrupted price string breaks ingestion pipelines and damages investigative credibility.

---

## 2. Invariants & Non-Negotiable Rules

### A. The Strict 18-Column Export Contract
- The standard corporate investigative export must strictly maintain column order, names, and casing:
  1. `Item ID`
  2. `Title`
  3. `Seller`
  4. `Price`
  5. `Marketplace`
  6. `Threat Score`
  7. `Threat Level`
  8. `Brand Targeted`
  9. `Infringement Category`
  10. `Listing URL`
  11. `Seller Profile URL`
  12. `Location / Origin`
  13. `Date Discovered`
  14. `Status`
  15. `Evidence Hash (pHash)`
  16. `Image URL`
  17. `Enforcement Priority`
  18. `Analyst Notes`

### B. openpyxl Professional Formatting Invariant
- **Auto-Column Sizing**: Compute maximum character length per column and apply `column_dimensions[col].width = max(len + 3, min_width)`.
- **Header Row Styling**: Bold typography, contrasting header background fill matching the active theme, and frozen pane on row 1 (`freeze_panes = 'A2'`).
- **Hyperlink Sanitization**: Listing URLs and Seller URLs must be formatted as valid clickable Excel hyperlinks.

### C. Zero Data Loss & Multi-Locale Normalization
- **Row Count Fidelity**: Validated that total written rows exactly match memory dataset counts.
- **Price Normalization**: Pass all currency strings through `normalize_price_string()` to eliminate regional comma/period ambiguities and currency symbols.

### D. VeRO & Rights Disclosure Integrity
- Extracted disclosures from PDF/text sources must isolate:
  - Seller Handle
  - Legal Entity / Corporate Name
  - Physical Street Address
  - City, Postal Code, and Country Code
- Ingest into the Enforcement Registry without generating duplicate entries.

---

## 3. Verification Protocol
1. Export a multi-marketplace dataset and inspect generated `.xlsx` in Excel.
2. Confirm header freezing, font sizing, and cell text alignment.
3. Verify test suites pass via `python -m unittest tests/run_tests.py`.
