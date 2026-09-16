# Apollo Brand Intelligence — Security & Architecture Audit
**Application Name:** Apollo Brand Intelligence (Anti-Counterfeit & Brand Protection Harvester)  
**Lead Author & Creator:** Jerry Seidenstucker  
**Copyright:** © 2026 Jerry Seidenstucker. All Rights Reserved.  
**Intended Use:** Brand Protection, Trademark Compliance, Threat Actor Intelligence, and Multi-Marketplace Listing Aggregation  
**Target Workstation Environment:** Enterprise Windows (Corporate / Brand Protection Environments)  
**Runtime Architecture:** Standalone Windows Executable (`--onedir` via PyInstaller, Native Microsoft Edge stealth automation)  

---

## 1. Executive Security & Compliance Summary

| Category | Policy / Status | Enterprise Detail |
| :--- | :--- | :--- |
| **Administrative Privileges** | 🟢 **Zero Required (Standard User)** | Runs strictly in user-space (`Standard User`). Never requires UAC prompts, never writes to `C:\Windows` or `C:\Program Files`. |
| **Registry Access** | 🟢 **Zero Writes** | Does not modify Windows Registry keys, system startup entries, or OS security policies. |
| **Telemetry / Tracking** | 🟢 **Zero External Telemetry** | No external analytics, crash reporters, tracking pixels, or third-party servers are contacted. All traffic is strictly bounded to user-targeted marketplaces. |
| **Network Protocol** | 🟢 **Encrypted HTTPS Only (Port 443)** | All outbound network traffic uses TLS 1.2 / TLS 1.3 over standard HTTPS. No unencrypted HTTP is transmitted. |
| **Inbound Ports / Listeners** | 🟢 **Zero Inbound Ports** | Opens no network listeners, local servers, or P2P connections. |
| **Data Storage & Privacy** | 🟢 **100% Local Storage** | Scraped listings, brand registries, seller caches, and exported `.xlsx` dossiers remain strictly on the local machine. |
| **Browser Execution Model** | 🟢 **Native Edge Driver** | Uses Windows' pre-installed Microsoft Edge (`msedge.exe`) in user-profile space without requiring external browser installs or administrative rights. |

---

## 2. Multi-Marketplace Destination Whitelist

The application strictly communicates with the following public e-commerce endpoints and their official Content Delivery Networks (CDNs) for listing retrieval and image previews:

| Marketplace | Primary Endpoints | Asset / Image CDN Endpoints |
| :--- | :--- | :--- |
| **eBay** | `https://www.ebay.com/*`, `https://api.ebay.com/*` | `https://i.ebayimg.com/*` |
| **AliExpress** | `https://www.aliexpress.com/*` | `https://ae01.alicdn.com/*`, `https://*.alicdn.com/*` |
| **Temu** | `https://www.temu.com/*` | `https://img.kwcdn.com/*` |
| **Wish** | `https://www.wish.com/*` | `https://canary.contestimg.wish.com/*` |
| **Printerval** | `https://printerval.com/*` | `https://cdn.printerval.com/*` |
| **Redbubble** | `https://www.redbubble.com/*` | `https://ih1.redbubble.net/*` |
| **Mercado Libre** | `https://*.mercadolibre.com/*`, `https://*.mercadolivre.com.br/*` | `https://http2.mlstatic.com/*` |

---

## 3. Data Flow & Security Architecture

```mermaid
graph TD
    User[Analyst Workstation (Local User Space)] -->|Encrypted HTTPS (TLS 1.2/1.3)| Targets[Target Marketplaces & CDNs]
    Targets -->|Public Listing Data & Thumbnails| User
    User -->|Local Disk Only| LocalDB[(Local data.json & Session Caches)]
    User -->|Analyst Export| Reports[A2C2 / Brand Protection Dossiers (.xlsx)]
```

### Key Controls:
- **API Credentials:** If optional eBay Developer API keys (`App ID`, `Cert ID`) are entered, they are stored locally in plaintext/user-space in `data.json` and transmitted strictly to `https://api.ebay.com/identity/v1/oauth2/token`.
- **Local Disk Isolation:** All session caches and cookies are isolated in `%LOCALAPPDATA%\Apollo_Brand_Intelligence` within the user's personal profile directory.
- **Enterprise EDR Compatibility:** Operating in a fixed folder structure (`--onedir`) prevents heuristic behavioral flags triggered by one-file extraction into temporary folders.

---

## 4. Integrity Verification

To verify the SHA-256 cryptographic checksum of `Apollo Brand Intelligence.exe` on your workstation:
```powershell
Get-FileHash -Algorithm SHA256 .\"Apollo Brand Intelligence.exe"
```

---

## 5. Security Attestation & Compliance Statement

Apollo Brand Intelligence v3.0 is engineered specifically for brand protection and intellectual property enforcement operations. It introduces no background services, no persistent system hooks, and adheres strictly to corporate data containment policies by maintaining all investigation records locally.
