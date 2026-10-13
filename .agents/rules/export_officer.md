---
trigger: always_on
description: Mandatory rules and invariants for the Export Officer Agent.
---

# Export Officer — Specialist Invariants

1. **Excel & CSV Schema Invariance**:
   - Column layout, headers, and order must remain strictly consistent across exports.
   - Prices must normalize cleanly through `normalize_price_string()`.

2. **VeRO Disclosure Parsing**:
   - Disclosures from PDF/text must cleanly extract seller handle, entity name, physical address, city, postal code, and country code.
   - Ingest into Enforcement Registry without duplicating existing records.

3. **Multi-Locale Normalization**:
   - Currency symbols and decimal formats across European/Latin American markets must map cleanly to standardized numeric floats.
