---
trigger: always_on
description: Mandatory rules and invariants for the Compliance & Legal Lead Agent.
---

# Compliance Lead — Specialist Invariants

1. **Strict Data Isolation (Apollo vs. Artemis)**:
   - Apollo and Artemis maintain completely decoupled databases (`data.json` vs. `artemis_data.json`).
   - Apollo handles intelligence & scanning; Artemis handles rights enforcement & legal dispatch.

2. **Absolute Privacy & Zero Internal Codename Leakage**:
   - Never commit or expose private employer terms specified in `.agents/rules/private_terms.md`.
   - Whitelist checks must protect verified authorized dealerships from false positive takedowns.

3. **LOA & Legal Notice Integrity**:
   - Legal notice generation must strictly adhere to statutory requirements without missing signatory credentials or power of attorney attachments.
