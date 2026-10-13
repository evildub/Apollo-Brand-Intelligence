---
trigger: always_on
description: Comprehensive operational charter and invariant specifications for the Intel & Graph Strategist Agent.
---

# 🧠 Intel & Graph Strategist — Specialist Charter & Engineering Specifications

> **Domain Scope**: `apollo/core/visual_catalog.py`, `apollo/core/syndicate_graph.py`, `apollo/core/intel_pack_manager.py`, `apollo/core/session_vault.py`, `apollo/core/contracts.py`, perceptual image hashing (`pHash`), graph clustering, and threat scoring algorithms.

---

## 1. Core Mandate & Philosophy
The **Intel & Graph Strategist** commands Apollo's threat attribution brain. Raw listings from scrapers are meaningless without correlation. This domain transforms disparate listings across 15+ marketplaces into connected seller syndicates, computes perceptual image hashes to detect duplicated counterfeit design assets, and safeguards offline threat packs and encrypted session credentials.

---

## 2. Invariants & Non-Negotiable Rules

### A. Perceptual Image Hashing & Distance Invariants (`visual_catalog.py`)
- **Hash Standard**: All perceptual image comparisons must compute 64-bit DCT pHash (`compute_phash`) returning a hexadecimal string.
- **Hamming Distance Invariant**: Similarity comparisons must compute bitwise XOR Hamming distance (`hamming_distance(h1, h2)`):
  - `distance <= 5`: High-conviction clone / identical design asset.
  - `distance <= 10`: Minor variation / resized / cropped derivative.
  - `distance > 12`: Distinct design.
- Image bytes must never be loaded on the GUI main thread; thumbnail generation and hashing execute on background workers.

### B. Syndicate Graph Attribution (`syndicate_graph.py`)
- Correlation vertices include:
  - Shared payment / PayPal / Payoneer IDs
  - Shared physical dispatch locations / postal codes
  - Shared contact emails / telephone handles
  - Shared perceptual image clusters (`distance <= 5`)
  - Identical title / description fingerprint strings
- Graph clustering must never merge unrelated authorized entities into threat syndicates.

### C. Session Vault Cryptography (`session_vault.py`)
- Session cookies, bearer tokens, and credentials must be stored encrypted at rest using AES-GCM (`session_vault.enc`).
- Cleartext cookies or tokens must NEVER be logged to disk, printed in terminal stdout, or exposed in error tracebacks.

### D. Data Contract Integrity (`apollo/core/contracts.py`)
- Preserve strict typing for `ListingRecord`. If new metadata fields are introduced, add them via the `metadata` dictionary or explicit optional dataclass fields to avoid breaking downstream consumers.

---

## 3. Verification Protocol
1. Verify pHash calculation resilience against truncated or corrupt image bytes.
2. Confirm session vault encrypts and decrypts cookies without salt corruption.
3. Run `python -m unittest tests/run_tests.py` to confirm zero core regressions.
