---
trigger: always_on
description: Mandatory rules and invariants for the Scraper Sentinel Agent.
---

# Scraper Sentinel — Specialist Invariants

1. **Marketplace Isolation**:
   - Updates to one platform (e.g. eBay) must never alter or degrade any other platform's scraping pipeline.
   - Core queue processor must maintain explicit isolated handlers.

2. **Anti-Bot Shield Handling**:
   - Akamai challenge pages ("Something went wrong on our end", "Error Page | eBay") must trigger automated `page.reload(wait_until="domcontentloaded")`.
   - Cloudflare Turnstile challenges must offer interactive session auth via `launch_interactive_auth()`.

3. **No Unsolicited Auto-Expansion**:
   - In Store Search, query strictly user-targeted terms. Never auto-expand parent corporate brands into sub-brands without explicit user selection.

4. **Empirical Verification**:
   - Synthetic unit test passes are necessary but not sufficient. When scraper handles change, execute real live test queries against the actual target platform.
