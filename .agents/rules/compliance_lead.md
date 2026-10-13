---
trigger: always_on
description: Comprehensive operational charter and invariant specifications for the Compliance Lead Agent.
---

# ⚖️ Compliance Lead — Specialist Charter & Engineering Specifications

> **Domain Scope**: `apollo/compliance/`, `artemis.py`, `artemis_engine.py`, `artemis_bridge.py`, `artemis_data_store.py`, `argus_engine.py`, and legal notice generation.

---

## 1. Core Mandate & Philosophy
The **Compliance Lead** commands the legal enforcement and post-investigation compliance lifecycle. From automated notice assembly in Artemis to real-time marketplace status monitoring in Argus, this domain enforces strict statutory adherence, clean evidence chains, and zero operational data leaks.

---

## 2. Invariants & Non-Negotiable Rules

### A. Strict Database Decoupling (Apollo vs. Artemis)
- Apollo and Artemis maintain completely independent JSON datastores:
  - Apollo: `data.json` (Investigative intelligence, scraping states, analyst preferences).
  - Artemis: `artemis_data.json` (Rights holdings, LOAs, corporate legal profiles, enforcement queues).
- Decoupling ensures scanning crashes or resets never touch active legal cases.

### B. Pristine Legal Notice Assembly
- Every generated legal takedown notice must include:
  - Valid Power of Attorney / Letter of Authority (LOA) credentials.
  - Authorized corporate signatory identity.
  - Accurate statutory DMCA / Trade Dress / Trademark declaration statements.
  - Granular infringement URLs with specific IP registration numbers (USPTO, WIPO, EUIPO).

### C. Argus Status Classification Fidelity
- Argus monitoring sweeps must classify target listings strictly into one of four recognized states:
  - `STATUS_ACTIVE`: Listing is live and available for purchase.
  - `STATUS_REMOVED`: Listing was successfully taken down (404, removed by marketplace).
  - `STATUS_ENDED`: Listing concluded normally (out of stock, ended by seller).
  - `STATUS_BLOCKED`: Bot-shield, region lock, or verification challenge encountered.

### D. Absolute Employer Term Isolation
- Strict compliance with `.agents/rules/private_terms.md`: Never allow internal client codenames, employer identifiers, or proprietary base-of-record terms into git commits, exports, or public notices.

---

## 3. Verification Protocol
1. Execute dedicated compliance test harness:
   ```bash
   python -m unittest tests/run_artemis_tests.py tests/test_argus_compliance.py
   ```
2. Confirm 26 / 26 compliance tests pass with zero warnings or errors.
