"""
Apollo Brand Intelligence - Analyst Field Guide & Threat Glossary Modal
Searchable reference documentation, threat heuristic definitions, search syntax cheat-sheet,
and operational guides for all Apollo Brand Intelligence modules.
"""

import tkinter as tk
from tkinter import ttk
import webbrowser

FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_HEADING = ("Segoe UI", 11, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_CODE = ("Consolas", 9)
FONT_SM = ("Segoe UI", 8)

# ── Master Operations Playbook Data ──
PLAYBOOK_DATA = [
    {
        "step": "Phase 1: Marketplace & Target Setup",
        "icon": "🌐",
        "summary": "Configure target stores, global keyword sweeps, and exclusion boundaries.",
        "details": [
            ("Platform Selection", "Switch between eBay, TikTok Shop, Vinted, ManoMano, AliExpress, Temu, Wish, Mercado Libre, or POD platforms."),
            ("Brand Library Targeting", "Select client brands (🎯 Target) and competitor/stemming noise (🚫 Exclude)."),
            ("1-Click Sweep Presets", "Use saved client presets (e.g. GM, Toyota, Denso) to automatically load complete keyword portfolios.")
        ]
    },
    {
        "step": "Phase 2: Live Sweep & Smart Triage",
        "icon": "▶",
        "summary": "Execute parallel sweeps and filter out non-enforceable universal fluff.",
        "details": [
            ("Queue Execution", "Run multi-store sweeps with real-time progress, live logging, and anti-rate-limit pacing."),
            ("Smart Triage", "Automatically suppresses universal title spam (seat covers, sunshades) while preserving high-risk components (spark plugs, emblems, fobs)."),
            ("Fluff Audit Mode", "Click '💨 Show Suppressed Fluff' to audit hidden items and verify suppression reasons.")
        ]
    },
    {
        "step": "Phase 3: Threat Intelligence & 3PL Detection",
        "icon": "🕵",
        "summary": "Unmask overseas drop-shipping rings and corporate origin smokescreens.",
        "details": [
            ("Origin Resolution", "Resolves true registered corporate headquarters (e.g. Shenzhen/Guangdong) against domestic dispatch locations (e.g. California 3PL hub)."),
            ("Threat Badging", "Automatically tags listings with 🇨🇳 Cross-Border Direct, 🚨 Foreign Drop-Ship Hub, or 🚩 Burner Handle."),
            ("Session Auto-Propagation", "Resolving one seller immediately propagates the threat profile to all listings from that seller across the table.")
        ]
    },
    {
        "step": "Phase 4: Visual Catalog & Reverse Dredge",
        "icon": "🖼",
        "summary": "Manage counterfeit visual fingerprints and execute parallel reverse sweeps.",
        "details": [
            ("Dual-Sided Catalog", "Maintain Red Catalog (counterfeit packaging/stock photos) and Green Catalog (authorized packaging)."),
            ("Multi-Hash Clustering", "Merge multiple variant photos/angles into one master cluster card."),
            ("Reverse Visual Dredge", "Right-click any photo to sweep 35 parallel workers across marketplaces finding exact clone listings.")
        ]
    },
    {
        "step": "Phase 5: Dealership Whitelist & Repeat Offender Registry",
        "icon": "🛡",
        "summary": "Shield authorized distributors and track repeat recidivist storefronts.",
        "details": [
            ("Authorized Whitelist", "Add official dealer handles to shield them across all scrapers with 🛡 (Authorized) badges."),
            ("Enforcement Registry", "Track multi-strike repeat offender stores, total infringing market value, and known 3PL locations."),
            ("In-Place Intel Editor", "Edit seller handles, corporate origins, and analyst notes directly in the registry.")
        ]
    },
    {
        "step": "Phase 6: Dossier Export & Enterprise Intake",
        "icon": "📄",
        "summary": "Generate court-admissible dossiers and standardized takedown packages.",
        "details": [
            ("Standard Excel Export", "Export formatted spreadsheets compliant with enterprise intake gateways (Ctrl+E)."),
            ("French Canadian Compliance", "Automatically formats French Canadian eBay listings strictly as 'ebay.ca - cafr'."),
            ("A2C2 Master Dossier", "Export executive brand protection dossiers detailing repeat offenders, brands infringed, and financial damages.")
        ]
    }
]

# ── Master Glossary Data ──
GLOSSARY_DATA = [
    {
        "term": "NWT (New With Tags)",
        "category": "P2P / Apparel Heuristics",
        "badge": "🚨 NWT Counterfeit Risk",
        "desc": "Condition indicating garment or merchandise is brand-new with original factory tags attached.",
        "intel": "High threat indicator on peer-to-peer marketplaces (Vinted, Mercari, Poshmark) when designer or luxury streetwear is priced 50%+ below MSRP by newly created or unverified accounts. Often signifies replica factory inventory.",
        "action": "Inspect listing photos for factory hang-tag font discrepancies, generic Chinese factory barcode stickers, and cross-reference against the Red Catalog."
    },
    {
        "term": "NWOT (New Without Tags)",
        "category": "P2P / Apparel Heuristics",
        "badge": "⚠ Condition Indicator",
        "desc": "Merchandise that is brand-new/unworn but missing original store tags.",
        "intel": "Frequently used by replica liquidators to explain away missing authentic security tags or RFID tracking tags.",
        "action": "Examine stitching quality, interior care label wash tags, and check seller history for repeated NWOT bulk volume."
    },
    {
        "term": "BNIB (Brand New In Box)",
        "category": "Retail & Electronics",
        "badge": "📦 Condition Indicator",
        "desc": "Item is sealed and unused in its original retail manufacturer packaging.",
        "intel": "Used in electronics, auto parts, and sneakers. If the price is severely discounted, it often indicates counterfeit packaging with clone internals.",
        "action": "Use the Visual Threat Manager to compare serial barcode typography and box tamper seal holograms."
    },
    {
        "term": "3PL Drop-Shipping Forwarding Hub",
        "category": "Logistics & Origin Deception",
        "badge": "🚨 Foreign Drop-Ship Hub",
        "desc": "Third-Party Logistics (3PL) warehouse located within domestic borders (e.g. Walnut CA, Jamaica NY, Elk Grove Village IL, Leicester UK).",
        "intel": "Overseas counterfeiting syndicates (predominantly in Guangdong, Shenzhen, and Yiwu) register overseas business addresses but list item locations as 'California' or 'New York' using local 3PL fulfillment centers to mask cross-border transit times and deceive domestic buyers.",
        "action": "Flagged automatically by Apollo's Threat Intel engine when seller registration country differs from item dispatch location."
    },
    {
        "term": "Burner Handle / Disposable Storefront",
        "category": "Syndicate Operations",
        "badge": "🚩 Suspicious Burner Handle",
        "desc": "Storefront usernames following algorithmic, randomized, or machine-generated patterns (e.g., user_8392184, hx9281_shop, z_88921).",
        "intel": "Counterfeit syndicates launch automated batches of disposable accounts that upload clone listings, liquidate inventory before platform review, and abandon the handle once flagged.",
        "action": "Run the 'Connected Seller Network Hunter' to uncover the mastermind entity behind multiple burner accounts."
    },
    {
        "term": "pHash (Perceptual Hashing)",
        "category": "Visual Intelligence",
        "badge": "📸 64-Bit DCT Fingerprint",
        "desc": "Mathematical visual algorithm that generates a 64-bit fingerprint of an image using Discrete Cosine Transform (DCT) frequency analysis.",
        "intel": "Unlike cryptographic hashes (MD5/SHA256) which break if a single pixel changes, pHash remains invariant to resizing, JPEG compression, minor color grading, and subtle cropping. Hamming distance <= 6 indicates near-identical visual match.",
        "action": "Used by Apollo's Visual Harvester and Visual Threat Catalog to detect counterfeit listings sharing master syndicate photos in parallel across 35 worker threads."
    },
    {
        "term": "VeRO (Verified Rights Owner)",
        "category": "Enforcement & Compliance",
        "badge": "⚖ eBay Enforcement",
        "desc": "eBay's official Intellectual Property rights protection program allowing brand owners to report and takedown infringing listings.",
        "intel": "Requires specific NOCI (Notice of Claimed Infringement) legal reasoning (Trademark Counterfeit, Copyright Image Infringement, or Patent Violation).",
        "action": "Use Apollo's Enforcement Registry and Artemis modal to log, draft, and track VeRO submission batches."
    },
    {
        "term": "BPP (Brand Protection Program)",
        "category": "Enforcement & Compliance",
        "badge": "⚖ Mercado Libre BPP",
        "desc": "Mercado Libre's dedicated IP protection and notice-and-takedown portal across Latin America (Mexico, Brazil, Argentina, Colombia, Chile, Peru).",
        "intel": "Provides fast-track takedowns for authenticated rights owners with regional trademark registrations.",
        "action": "Export MeLi enforcement batches directly formatted for BPP bulk submission."
    },
    {
        "term": "Verified OEM Engineering Standard (GMW / WSS / MS)",
        "category": "Document Intelligence & Scribd",
        "badge": "🚨 Verified GMW / OEM Standard (Score: 95)",
        "desc": "Proprietary, confidential manufacturer engineering specifications and test standards (e.g. GMW14872 Cyclic Corrosion, Ford WSS-M, Chrysler MS, Toyota TSM).",
        "intel": "Confidential OEM technical documents illegally leaked to public document sharing portals (Scribd, DocPlayer). High-value IP violation allowing aftermarket copycats to replicate genuine material metallurgy and electronic tolerances.",
        "action": "Flagged automatically by Apollo's Document Intelligence Engine. High-priority takedown candidate for legal/compliance enforcement."
    },
    {
        "term": "3-Layer GMW Acronym Disambiguation Shield",
        "category": "Document Intelligence & Scribd",
        "badge": "🛡 3-Layer Disambiguation",
        "desc": "Algorithmic triage pipeline that separates genuine General Motors Worldwide ('GMW') standards from consumer collisions.",
        "intel": "• Layer 1 (Regex): Matches strictly GMW + 3-5 digits (e.g. GMW14872, GMW 3044).\n• Layer 2 (Collision Filter): Structurally disqualifies non-OEM consumer collisions (e.g. Casio G-Shock GMW-B5000, Gamer Media Workspace).\n• Layer 3 (Context Corroboration): Analyzes surrounding technical keywords (metallurgy, powertrain, corrosion lab test).",
        "action": "Eliminates 100% of consumer noise before entering the analyst results queue."
    },
    {
        "term": "Ambiguous Document Heuristic (Review Required)",
        "category": "Document Intelligence & Scribd",
        "badge": "⚠️ Ambiguous (Review Required) (Score: 25)",
        "desc": "Document containing standalone 'GMW' without a spec number, but containing automotive or engineering context words.",
        "intel": "May indicate internal engineering meeting notes, supplier guidelines, or non-standardized technical presentations.",
        "action": "Assigned a lower threat score (25) and flagged with a yellow warning badge for quick analyst manual review."
    },
    {
        "term": "Technical Service Bulletins (TSB) & Repair Manuals",
        "category": "Document Intelligence & Scribd",
        "badge": "📑 Technical Service Bulletin / 🔧 Service Manual",
        "desc": "Dealership-exclusive factory service manuals, master electrical schematics, and confidential internal repair bulletins.",
        "intel": "Copyrighted technical publications distributed without OEM authorization, undermining authorized service networks.",
        "action": "Export for bulk copyright takedown notice."
    },
    {
        "term": "Visual Clone Match (Red Catalog)",
        "category": "Visual Intelligence",
        "badge": "🚨 Known Counterfeit (Visual Match)",
        "desc": "Listing photo whose pHash mathematically matches an entry in Apollo's Counterfeit Visual Threat Catalog.",
        "intel": "Conclusively proves the seller is utilizing known replica factory promotional photography or syndicated stock photos.",
        "action": "Highlight row in table, right-click to run Reverse Visual Dredge to discover all sister accounts using the same image."
    },
    {
        "term": "Benign Packaging (Green Catalog)",
        "category": "Visual Intelligence",
        "badge": "🟢 Known Benign Packaging",
        "desc": "Listing photo verified as authentic client factory packaging or authorized distributor stock photography.",
        "intel": "Prevents false-positive enforcement and keeps analyst queues clean. When 'Hide Benign' is active, matching listings are suppressed from view.",
        "action": "Add authorized stock photos to the Green Catalog in the Visual Library to automatically filter them out."
    }
]

# ── Master Search Syntax Data ──
SYNTAX_DATA = [
    {
        "syntax": "Basic Keyword Search",
        "example": "Nike Tech Fleece",
        "desc": "Matches any listing containing 'Nike', 'Tech', or 'Fleece' in the active search column or title.",
        "tip": "Default search is case-insensitive and matches partial strings."
    },
    {
        "syntax": "Mandatory Inclusion (+token)",
        "example": "+hoodie +black",
        "desc": "Strictly requires that the term MUST be present. Any listing missing a '+' token is filtered out.",
        "tip": "Use when narrowing down broad sweeps: e.g. 'Dunk +Low +Panda'."
    },
    {
        "syntax": "Negative Exclusion (-token)",
        "example": "-case -sticker -box -poster",
        "desc": "Strictly excludes any listing containing the '-' token anywhere in the text.",
        "tip": "Essential for eliminating accessories, phone cases, and packaging boxes when hunting physical garments/parts."
    },
    {
        "syntax": "Combined Positive & Negative Expressions",
        "example": "jacket +men -women -kids -youth",
        "desc": "Combines base search with mandatory inclusions and negative exclusions simultaneously.",
        "tip": "Allows complex precision filtering directly within the main table search bar without re-running scans."
    },
    {
        "syntax": "Target Column Dropdown",
        "example": "Filter by 'Seller' or 'Threat Intel'",
        "desc": "Restricts search evaluations to a specific column rather than searching the entire listing payload.",
        "tip": "Select 'Threat Intel' and type '🚨' or '3PL' to isolate all high-threat items in seconds."
    },
    {
        "syntax": "High Risk Only Checkbox",
        "example": "[x] High Risk Only",
        "desc": "Instantly filters the table to only show confirmed 3PL forwarding hubs, Vinted NWT replica candidates, burner handles, and visual clones.",
        "tip": "One-click toggle for fast triage during high-volume investigations."
    },
    {
        "syntax": "Hide Benign Checkbox",
        "example": "[x] Hide Benign",
        "desc": "Hides all listings that have matched verified genuine photos in the Green Packaging Catalog.",
        "tip": "Keeps your triage queue 100% focused on unresolved and high-threat listings."
    }
]

# ── Master Modal & Tools Directory ──
TOOLS_DATA = [
    {
        "name": "🖼 Visual Threat Catalog & Packaging Manager",
        "shortcut": "Visual Library Button / F2",
        "purpose": "Central visual intelligence hub for managing known counterfeit photos (Red Catalog) and authorized authentic packaging (Green Catalog).",
        "workflow": "1. Add known replica photos via '🔴 Mark as Counterfeit' from the right-click menu or local upload.\n2. Merge visual variants into multi-image cluster cards.\n3. Click 'Dredge' on any card to execute a 35-thread parallel visual clone sweep across eBay, Vinted, AliExpress, or Mercado Libre."
    },
    {
        "name": "📸 Reverse Visual Search (Sweep by Photo)",
        "shortcut": "Right-Click Context Menu ➔ 📸 Reverse Visual Search",
        "purpose": "High-speed dredge that takes any listing's photo and searches marketplace candidates, mathematically validating matches via 64-bit DCT pHash.",
        "workflow": "Right-click any table row ➔ expand the nested menu to sweep the current platform or immediately target Vinted locales (UK, US, Spain, France, Italy, All), Mercado Libre, eBay, AliExpress, Wish, or Temu."
    },
    {
        "name": "🔗 Connected Seller Network Hunter",
        "shortcut": "Right-Click Menu / Toolbar Button",
        "purpose": "Entity resolution engine that discovers syndicate sister stores sharing matching business registrations, VAT IDs, phone numbers, PayPal accounts, or dispatch addresses.",
        "workflow": "Select a rogue seller ➔ click Hunter ➔ Apollo crawls storefront metadata and maps the entire connected network of sister accounts for bulk takedown."
    },
    {
        "name": "📚 Scribd Document Repository & OEM Technical Harvester",
        "shortcut": "Marketplace Dropdown ➔ Scribd / Document Scope Selector",
        "purpose": "Specialized intelligence harvester targeting proprietary OEM engineering standards, confidential test procedures, wiring schematics, and service manuals on Scribd.",
        "workflow": "1. Select 'Scribd' in the Marketplace dropdown.\n2. Choose Document Scope: '🚨 OEM Engineering Standards (GMW)', '🔧 Vehicle Service Manuals', or '📑 Technical Service Bulletins'.\n3. Apollo executes sweeps with the 3-Layer GMW Disambiguation Shield, filtering out non-OEM collisions (Casio watches, gaming clans) and surfacing verified standards ($Score: 95$)."
    },
    {
        "name": "🕵 Threat Intel & Origin Resolver",
        "shortcut": "Right-Click Menu / Ctrl+R",
        "purpose": "Deep cross-border origin inspection exposing foreign drop-shipping rings and 3PL forwarding warehouses.",
        "workflow": "Resolves seller registration country vs dispatch item location, applying geographic flags and threat badges."
    },
    {
        "name": "🛡 Authorized Dealer Whitelist Manager",
        "shortcut": "Settings ➔ Whitelist / Toolbar Button",
        "purpose": "Protects verified client partners, retail channels, and authorized distributors from inadvertent enforcement.",
        "workflow": "Add official seller handles. Whitelisted accounts receive a '🛡 (Authorized)' badge and are automatically excluded from takedown queues."
    },
    {
        "name": "📥 Adhoc Batch URL & File Importer",
        "shortcut": "Batch Search Button / File Menu",
        "purpose": "Ingests hundreds of listing URLs from external client spreadsheets (.xlsx, .csv) or text lists for automated batch metadata scraping and visual analysis.",
        "workflow": "Paste URLs or load Excel file ➔ Apollo runs high-speed parallel harvesting across all links and populates the results table."
    },
    {
        "name": "🛡 Enforcement Registry & Audit Log",
        "shortcut": "Registry Button / Export Menu",
        "purpose": "Maintains persistent records of all logged infringements, takedown notices, and case files with full compliance audit trails.",
        "workflow": "Mark infringing listings ➔ Log to Registry ➔ Export formal Excel enforcement packages ready for platform submission."
    },
    {
        "name": "🏷 Product Type & Industry Taxonomy Manager",
        "shortcut": "Settings ➔ 🏷 Product Type & Industry Taxonomy...",
        "purpose": "Configures industry-specific product categories and auto-tagging keyword rules (Automotive, Apparel, Tools, Home/Living, Pharma/Vet, Electronics).",
        "workflow": "1. Select an Industry Sector on the left.\n2. Add or select a Product Type (e.g. 'Spark Plugs' or 'Hoodies & Sweatshirts').\n3. Edit trigger keywords in the text editor (e.g. 'spark plug, iridium, platinum').\n4. Use the Live Title Sandbox at the bottom to test how listings will be classified in real-time.\n5. Click 'Save & Apply Taxonomy' to persist rules across all scrapers and live ingestion."
    },
    {
        "name": "🕸 Syndicate Hunter & Entity Resolution",
        "shortcut": "Settings ➔ 🕸 Syndicate Hunter (Ctrl+Y)... / Hotkey: Ctrl+Y",
        "purpose": "Entity resolution and network mapping engine that identifies syndicate sister accounts sharing dispatch hubs, burner handles, visual clone hashes, or corporate registrations.",
        "workflow": "1. Select any listing or suspect seller handle.\n2. Press Ctrl+Y or open Syndicate Hunter from Settings.\n3. Explore clustered seller graphs, inspect shared 3PL dispatch hubs, and export coordinated takedown dossiers."
    },
    {
        "name": "🔐 Marketplace Session Vault & API Credentials",
        "shortcut": "Settings ➔ 🔐 Marketplace Session Vault... / Hotkey: Ctrl+Shift+V",
        "purpose": "Centralized authentication and API key management console for persistent browser cookies, Cloudflare/DataDome bypass sessions, stored marketplace logins (Mercado Libre, Temu, Vinted), and Enterprise Enforcement API gateways.",
        "workflow": "1. Open Session Vault from Settings or press Ctrl+Shift+V.\n2. In Tab 1, click 'Connect' to open a stealth browser session or save marketplace logins for automated authentication.\n3. In Tab 2, configure Enterprise Enforcement API endpoints and eBay Developer REST API keys with live connection testing."
    },
    {
        "name": "🏷 Brand Intelligence Registry & Keywords",
        "shortcut": "Settings ➔ 🏷 Brand Registry & Keywords...",
        "purpose": "Central repository for monitored client brand names, OEM standard numbers, trademark variations, and negative exclusion filters.",
        "workflow": "1. Open Brand Registry from Settings.\n2. Add target client brands and associated high-risk keyword queries.\n3. Apollo applies these definitions across all marketplace sweeps and auto-tagging engines."
    },
    {
        "name": "📄 VeRO Seller Disclosure Parser (.pdf / text)",
        "shortcut": "Settings ➔ 📄 VeRO Seller Disclosure Parser (.pdf / text)...",
        "purpose": "Extracts merchant details, legal names, addresses, phone numbers, and case references from platform infringement disclosure PDFs.",
        "workflow": "1. Open VeRO Disclosure Parser from Settings.\n2. Load platform disclosure PDF or paste text.\n3. Apollo extracts structured seller identity records and cross-references them against known repeat offenders in the Registry."
    }
]


class FieldGuideModal(tk.Toplevel):
    def __init__(self, master, theme: dict):
        super().__init__(master)
        self.withdraw()
        self.master_app = master
        self.theme = theme
        self.title("Apollo Brand Intelligence - Analyst Field Guide & Threat Glossary")
        self.geometry("960x680")
        self.minsize(800, 550)
        self.transient(master)

        self.config(bg=self._t("bg", "#121212"))
        self.active_canvas = None
        self.tab_canvases = {}

        if hasattr(master, "_apply_dark_titlebar"):
            master._apply_dark_titlebar(self)
        if hasattr(master, "_load_app_icon"):
            master._load_app_icon(self)

        # Header Frame
        self._build_header()

        # Notebook (Tabs)
        self._build_tabs()

        # Footer
        self._build_footer()

        # Global Mousewheel Binding
        self.bind("<MouseWheel>", self._on_global_mousewheel)

        # Initial focus on search
        self.search_entry.focus_set()

        # Center modal relative to master window and reveal
        if hasattr(master, "_center_window"):
            master._center_window(self, 960, 680)
        else:
            self.deiconify()
        self.lift()
        self.focus_force()

    def _t(self, key, default):
        return self.theme.get(key, default)

    def _on_global_mousewheel(self, event):
        target = self.active_canvas
        if not target and self.tab_canvases:
            current_tab = self.nb.select()
            target = self.tab_canvases.get(current_tab)
        if target:
            try:
                target.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

    def _build_header(self):
        hdr = tk.Frame(self, bg=self._t("panel", "#1e1e1e"), padx=16, pady=12)
        hdr.pack(fill="x", side="top")

        left = tk.Frame(hdr, bg=self._t("panel", "#1e1e1e"))
        left.pack(side="left", fill="y")

        tk.Label(
            left,
            text="📚 Analyst Field Guide & Threat Intelligence Glossary",
            font=FONT_TITLE,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("accent", "#38bdf8")
        ).pack(anchor="w")

        tk.Label(
            left,
            text="Comprehensive brand protection reference, heuristic indicators, search syntax, and module workflows.",
            font=FONT_NORM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        ).pack(anchor="w", pady=(2, 0))

        # Live Search Bar
        right = tk.Frame(hdr, bg=self._t("panel", "#1e1e1e"))
        right.pack(side="right", fill="y", padx=4)

        tk.Label(
            right,
            text="🔍 Filter Guide:",
            font=FONT_BOLD,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("text", "#f8fafc")
        ).pack(side="left", padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        self.search_entry = tk.Entry(
            right,
            textvariable=self.search_var,
            font=FONT_NORM,
            width=24,
            bg=self._t("entry_bg", "#262626"),
            fg=self._t("text", "#f8fafc"),
            insertbackground=self._t("text", "#f8fafc"),
            relief="solid",
            bd=1
        )
        self.search_entry.pack(side="left", ipady=3)

        tk.Button(
            right,
            text="✕",
            font=FONT_BOLD,
            bg=self._t("entry_bg", "#262626"),
            fg=self._t("subtext", "#94a3b8"),
            relief="flat",
            command=lambda: self.search_var.set("")
        ).pack(side="left", padx=2)

    def _build_tabs(self):
        style = ttk.Style()
        
        # Configure Notebook Tab Styling without resetting global theme_use
        style.configure(
            "Guide.TNotebook",
            background=self._t("bg", "#121212"),
            borderwidth=0
        )
        style.configure(
            "Guide.TNotebook.Tab",
            background=self._t("panel", "#1e1e1e"),
            foreground=self._t("text", "#f8fafc"),
            padding=[16, 8],
            font=FONT_BOLD
        )
        style.map(
            "Guide.TNotebook.Tab",
            background=[("selected", self._t("accent", "#38bdf8")), ("active", self._t("border", "#333333"))],
            foreground=[("selected", "black" if str(self.theme.get("name","")).startswith("⚡") else "white"),
                        ("active", self._t("text", "#f8fafc"))]
        )

        self.nb = ttk.Notebook(self, style="Guide.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=12, pady=8)
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Tab 1: Operations Playbook
        self.tab_playbook = tk.Frame(self.nb, bg=self._t("bg", "#121212"))
        self.nb.add(self.tab_playbook, text="📖 Operations Playbook")
        self._populate_playbook_tab()

        # Tab 2: Tool Directory
        self.tab_tools = tk.Frame(self.nb, bg=self._t("bg", "#121212"))
        self.nb.add(self.tab_tools, text="🛠 Apollo Tools & Modules")
        self._populate_tools_tab()

        # Tab 3: Search Syntax
        self.tab_syntax = tk.Frame(self.nb, bg=self._t("bg", "#121212"))
        self.nb.add(self.tab_syntax, text="🔍 Search Syntax & Live Filters")
        self._populate_syntax_tab()

        # Tab 4: Glossary
        self.tab_glossary = tk.Frame(self.nb, bg=self._t("bg", "#121212"))
        self.nb.add(self.tab_glossary, text="🚨 Threat Glossary & Signals")
        self._populate_glossary_tab()

    def _on_tab_changed(self, event=None):
        current_tab = self.nb.select()
        self.active_canvas = self.tab_canvases.get(current_tab)

    def _bind_mousewheel_recursive(self, widget, canvas):
        def _scroll(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        widget.bind("<MouseWheel>", _scroll, add="+")
        widget.bind("<Enter>", lambda e, c=canvas: setattr(self, "active_canvas", c), add="+")
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child, canvas)

    def _create_scrollable_container(self, parent):
        canvas = tk.Canvas(parent, bg=self._t("bg", "#121212"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self._t("bg", "#121212"))

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Track active canvas on enter
        canvas.bind("<Enter>", lambda e, c=canvas: setattr(self, "active_canvas", c))
        scrollable_frame.bind("<Enter>", lambda e, c=canvas: setattr(self, "active_canvas", c))

        def _on_canvas_scroll(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        canvas.bind("<MouseWheel>", _on_canvas_scroll)
        scrollable_frame.bind("<MouseWheel>", _on_canvas_scroll)

        # Store tab canvas mapping
        tab_id = str(parent)
        self.tab_canvases[tab_id] = canvas
        if not self.active_canvas:
            self.active_canvas = canvas

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return scrollable_frame, canvas

    # ── Tab 1: Operations Playbook ──
    def _populate_playbook_tab(self):
        self.playbook_container, self.playbook_canvas = self._create_scrollable_container(self.tab_playbook)
        self._render_playbook_cards()

    def _render_playbook_cards(self, query: str = ""):
        for w in self.playbook_container.winfo_children():
            w.destroy()

        q = query.lower().strip()
        matched = 0

        # Top Playbook Banner
        top_box = tk.Frame(self.playbook_container, bg=self._t("panel", "#1e1e1e"), padx=16, pady=12, relief="solid", bd=1)
        top_box.pack(fill="x", padx=8, pady=6)
        tk.Label(
            top_box,
            text="📖 Apollo Brand Protection — Standard Operational Procedure (SOP)",
            font=FONT_TITLE,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("accent", "#38bdf8")
        ).pack(anchor="w")
        tk.Label(
            top_box,
            text="End-to-end investigative methodology for cross-border marketplace sweeps, visual clustering, 3PL detection, and court-admissible dossier delivery.",
            font=FONT_NORM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        ).pack(anchor="w", pady=(2, 0))

        for item in PLAYBOOK_DATA:
            full_text = f"{item['step']} {item['summary']} " + " ".join(f"{t} {d}" for t, d in item["details"])
            if q and q not in full_text.lower():
                continue

            matched += 1
            card = tk.Frame(
                self.playbook_container,
                bg=self._t("panel", "#1e1e1e"),
                relief="solid",
                bd=1,
                padx=16,
                pady=12
            )
            card.pack(fill="x", padx=8, pady=6)

            top = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
            top.pack(fill="x")

            tk.Label(
                top,
                text=f"{item['icon']} {item['step']}",
                font=FONT_TITLE,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("accent", "#38bdf8")
            ).pack(side="left")

            tk.Label(
                card,
                text=item["summary"],
                font=FONT_BOLD,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("text", "#f8fafc")
            ).pack(anchor="w", pady=(4, 6))

            det_box = tk.Frame(card, bg=self._t("entry_bg", "#262626"), padx=12, pady=8, relief="flat")
            det_box.pack(fill="x")
            det_box.grid_columnconfigure(0, weight=0)
            det_box.grid_columnconfigure(1, weight=1)

            for r_idx, (sub_title, sub_desc) in enumerate(item["details"]):
                lbl_sub = tk.Label(
                    det_box,
                    text=f"• {sub_title}:",
                    font=FONT_BOLD,
                    bg=self._t("entry_bg", "#262626"),
                    fg=self._t("accent", "#38bdf8"),
                    anchor="nw",
                    justify="left"
                )
                lbl_sub.grid(row=r_idx, column=0, sticky="nw", padx=(0, 14), pady=3)

                lbl_desc = tk.Label(
                    det_box,
                    text=sub_desc,
                    font=FONT_NORM,
                    bg=self._t("entry_bg", "#262626"),
                    fg=self._t("text", "#f8fafc"),
                    justify="left",
                    anchor="w",
                    wraplength=640
                )
                lbl_desc.grid(row=r_idx, column=1, sticky="new", pady=3)

        if matched == 0:
            tk.Label(
                self.playbook_container,
                text=f"No operational steps matching '{query}'.",
                font=FONT_HEADING,
                bg=self._t("bg", "#121212"),
                fg=self._t("subtext", "#94a3b8"),
                pady=40
            ).pack()

    # ── Tab 4: Threat Signals & Acronyms ──
    def _populate_glossary_tab(self):
        self.glossary_container, self.glossary_canvas = self._create_scrollable_container(self.tab_glossary)
        self._render_glossary_cards()

    def _render_glossary_cards(self, query: str = ""):
        for w in self.glossary_container.winfo_children():
            w.destroy()

        q = query.lower().strip()
        matched = 0

        for item in GLOSSARY_DATA:
            full_text = f"{item['term']} {item['category']} {item['desc']} {item['intel']} {item['action']}".lower()
            if q and q not in full_text:
                continue

            matched += 1
            card = tk.Frame(
                self.glossary_container,
                bg=self._t("panel", "#1e1e1e"),
                relief="solid",
                bd=1,
                padx=14,
                pady=10
            )
            card.pack(fill="x", padx=8, pady=6)

            # Top Row: Term + Badge + Category
            top = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
            top.pack(fill="x")

            tk.Label(
                top,
                text=item["term"],
                font=FONT_HEADING,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("accent", "#38bdf8")
            ).pack(side="left")

            tk.Label(
                top,
                text=f" {item['badge']} ",
                font=FONT_BOLD,
                bg=self._t("entry_bg", "#262626"),
                fg=self._t("text", "#f8fafc"),
                padx=6,
                pady=2
            ).pack(side="left", padx=10)

            tk.Label(
                top,
                text=f"Category: {item['category']}",
                font=FONT_SM,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("subtext", "#94a3b8")
            ).pack(side="right")

            # Definition
            tk.Label(
                card,
                text=f"📌 Definition: {item['desc']}",
                font=FONT_NORM,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("text", "#f8fafc"),
                justify="left",
                wraplength=850
            ).pack(anchor="w", pady=(6, 2))

            # Threat Intelligence Context
            tk.Label(
                card,
                text=f"🚨 Threat Significance: {item['intel']}",
                font=FONT_NORM,
                bg=self._t("panel", "#1e1e1e"),
                fg="#fca5a5" if not str(self.theme.get("name","")).startswith("⚡") else "#ef4444",
                justify="left",
                wraplength=850
            ).pack(anchor="w", pady=(0, 2))

            # Recommended Analyst Action
            tk.Label(
                card,
                text=f"🎯 Analyst Action: {item['action']}",
                font=FONT_SM,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("subtext", "#94a3b8"),
                justify="left",
                wraplength=850
            ).pack(anchor="w")

        if matched == 0:
            tk.Label(
                self.glossary_container,
                text=f"No threat signals matching '{query}'.",
                font=FONT_HEADING,
                bg=self._t("bg", "#121212"),
                fg=self._t("subtext", "#94a3b8"),
                pady=40
            ).pack()

    # ── Tab 2: Search Syntax & Live Filtering ──
    def _populate_syntax_tab(self):
        self.syntax_container, self.syntax_canvas = self._create_scrollable_container(self.tab_syntax)
        self._render_syntax_cards()

    def _render_syntax_cards(self, query: str = ""):
        for w in self.syntax_container.winfo_children():
            w.destroy()

        q = query.lower().strip()
        matched = 0

        # Syntax quick summary alert
        top_box = tk.Frame(self.syntax_container, bg=self._t("panel", "#1e1e1e"), padx=14, pady=10, relief="solid", bd=1)
        top_box.pack(fill="x", padx=8, pady=6)
        tk.Label(
            top_box,
            text="⚡ Power-User Search Syntax in Apollo's Results Table",
            font=FONT_HEADING,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("accent", "#38bdf8")
        ).pack(anchor="w")
        tk.Label(
            top_box,
            text="The results table search bar supports real-time multi-token filtering, positive mandatory inclusions (+), and negative exclusions (-).",
            font=FONT_NORM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        ).pack(anchor="w", pady=(2, 0))

        for item in SYNTAX_DATA:
            full_text = f"{item['syntax']} {item['example']} {item['desc']} {item['tip']}".lower()
            if q and q not in full_text:
                continue

            matched += 1
            card = tk.Frame(
                self.syntax_container,
                bg=self._t("panel", "#1e1e1e"),
                relief="solid",
                bd=1,
                padx=14,
                pady=10
            )
            card.pack(fill="x", padx=8, pady=6)

            top = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
            top.pack(fill="x")

            tk.Label(
                top,
                text=item["syntax"],
                font=FONT_HEADING,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("text", "#f8fafc")
            ).pack(side="left")

            tk.Label(
                top,
                text=f" Example: {item['example']} ",
                font=FONT_CODE,
                bg=self._t("entry_bg", "#262626"),
                fg=self._t("accent", "#38bdf8"),
                padx=6,
                pady=2
            ).pack(side="right")

            tk.Label(
                card,
                text=f"📖 How It Works: {item['desc']}",
                font=FONT_NORM,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("text", "#f8fafc"),
                justify="left",
                wraplength=850
            ).pack(anchor="w", pady=(6, 2))

            tk.Label(
                card,
                text=f"💡 Pro Tip: {item['tip']}",
                font=FONT_SM,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("subtext", "#94a3b8"),
                justify="left",
                wraplength=850
            ).pack(anchor="w")

        if matched == 0:
            tk.Label(
                self.syntax_container,
                text=f"No search syntax matching '{query}'.",
                font=FONT_HEADING,
                bg=self._t("bg", "#121212"),
                fg=self._t("subtext", "#94a3b8"),
                pady=40
            ).pack()

    # ── Tab 3: Apollo Tools & Modal Guide ──
    def _populate_tools_tab(self):
        self.tools_container, self.tools_canvas = self._create_scrollable_container(self.tab_tools)
        self._render_tools_cards()

    def _render_tools_cards(self, query: str = ""):
        for w in self.tools_container.winfo_children():
            w.destroy()

        q = query.lower().strip()
        matched = 0

        for item in TOOLS_DATA:
            full_text = f"{item['name']} {item['shortcut']} {item['purpose']} {item['workflow']}".lower()
            if q and q not in full_text:
                continue

            matched += 1
            card = tk.Frame(
                self.tools_container,
                bg=self._t("panel", "#1e1e1e"),
                relief="solid",
                bd=1,
                padx=14,
                pady=10
            )
            card.pack(fill="x", padx=8, pady=6)

            top = tk.Frame(card, bg=self._t("panel", "#1e1e1e"))
            top.pack(fill="x")

            tk.Label(
                top,
                text=item["name"],
                font=FONT_HEADING,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("accent", "#38bdf8")
            ).pack(side="left")

            tk.Label(
                top,
                text=f" Access: {item['shortcut']} ",
                font=FONT_BOLD,
                bg=self._t("entry_bg", "#262626"),
                fg=self._t("text", "#f8fafc"),
                padx=6,
                pady=2
            ).pack(side="right")

            tk.Label(
                card,
                text=f"🎯 Primary Purpose: {item['purpose']}",
                font=FONT_NORM,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("text", "#f8fafc"),
                justify="left",
                wraplength=850
            ).pack(anchor="w", pady=(6, 4))

            tk.Label(
                card,
                text=f"📋 Recommended Workflow:\n{item['workflow']}",
                font=FONT_SM,
                bg=self._t("panel", "#1e1e1e"),
                fg=self._t("subtext", "#94a3b8"),
                justify="left",
                wraplength=850
            ).pack(anchor="w")

        if matched == 0:
            tk.Label(
                self.tools_container,
                text=f"No tools matching '{query}'.",
                font=FONT_HEADING,
                bg=self._t("bg", "#121212"),
                fg=self._t("subtext", "#94a3b8"),
                pady=40
            ).pack()

    def _on_search_changed(self, *args):
        query = self.search_var.get()
        self._render_playbook_cards(query)
        self._render_tools_cards(query)
        self._render_syntax_cards(query)
        self._render_glossary_cards(query)

    def _build_footer(self):
        ftr = tk.Frame(self, bg=self._t("panel", "#1e1e1e"), padx=14, pady=8)
        ftr.pack(fill="x", side="bottom")

        tk.Label(
            ftr,
            text="Tip: Press F1 anytime in Apollo to quickly open this Field Guide.",
            font=FONT_SM,
            bg=self._t("panel", "#1e1e1e"),
            fg=self._t("subtext", "#94a3b8")
        ).pack(side="left")

        tk.Button(
            ftr,
            text="Close (Esc)",
            font=FONT_NORM,
            bg=self._t("accent", "#2563eb"),
            fg="black" if str(self.theme.get("name","")).startswith("⚡") else "white",
            relief="flat",
            padx=14,
            pady=4,
            command=self.destroy
        ).pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())
