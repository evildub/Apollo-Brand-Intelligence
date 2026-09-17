import sys
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import re
import io
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import urllib.request
from datetime import datetime
import webbrowser
import winsound
from PIL import Image, ImageTk
import ctypes

logger = logging.getLogger("Apollo")

from scraper import EbayScraper
from aliexpress_scraper import AliExpressScraper
from wish_scraper import WishScraper
from temu_scraper import TemuScraper
from mercadolibre_scraper import MercadoLibreScraper
from redbubble_scraper import RedbubbleScraper
from printerval_scraper import PrintervalScraper
from vinted_scraper import VintedScraper
from tiktok_scraper import TikTokScraper
from manomano_scraper import ManoManoScraper
from scribd_scraper import ScribdScraper
from teepublic_scraper import TeePublicScraper
from etsy_scraper import EtsyScraper
from spreadshirt_scraper import SpreadshirtScraper
from zazzle_scraper import ZazzleScraper
from cafepress_scraper import CafePressScraper
from threadless_scraper import ThreadlessScraper
from teespring_scraper import TeeSpringScraper
from fineartamerica_scraper import FineArtAmericaScraper
from session_vault import SessionVault
from session_vault_modal import SessionVaultModal
from multi_sector_modal import MultiSectorModal
from exporter import ExcelExporter, normalize_price_string
from data_store import DataStore
import batch_importer
from visual_catalog import VisualCatalogManager, compute_phash, hamming_distance
from visual_harvester import VisualHarvester
from visual_catalog_modal import VisualCatalogModal
from vero_disclosure_modal import VeroDisclosureModal
from field_guide_modal import FieldGuideModal
from product_type_modal import ProductTypeModal
from tooltip import add_tooltip, HoverTip

# ── Color Palette Definitions ─────────────────────────────────────────────────
THEMES = {
    "apollo_exec": {
        "name": "🌟 Apollo Executive",
        "bg": "#000227",
        "panel": "#0A0E36",
        "accent": "#38BDF8",
        "accent2": "#347BB7",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "text": "#FFFFFF",
        "subtext": "#7C8FA3",
        "entry_bg": "#05071F",
        "border": "#1E295D",
        "btn_normal_bg": "#0F1642",
        "btn_normal_fg": "#FFFFFF",
        "select_bg": "#0044FF",
        "select_fg": "#FFFFFF",
    },
    "midnight": {
        "name": "🌌 Midnight Slate",
        "bg": "#1e1e2e",
        "panel": "#2a2a3e",
        "accent": "#7c6af7",
        "accent2": "#5a9fd4",
        "success": "#50fa7b",
        "warning": "#f1fa8c",
        "danger": "#ff5555",
        "text": "#f8f8f2",
        "subtext": "#a6adc8",
        "entry_bg": "#313145",
        "border": "#44475a",
        "btn_normal_bg": "#44475a",
        "btn_normal_fg": "#f8f8f2",
        "select_bg": "#7c6af7",
        "select_fg": "#ffffff",
    },
    "ocean": {
        "name": "🌊 Deep Ocean",
        "bg": "#0f172a",
        "panel": "#1e293b",
        "accent": "#38bdf8",
        "accent2": "#0284c7",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#f87171",
        "text": "#f8fafc",
        "subtext": "#94a3b8",
        "entry_bg": "#334155",
        "border": "#475569",
        "btn_normal_bg": "#334155",
        "btn_normal_fg": "#f8fafc",
        "select_bg": "#0284c7",
        "select_fg": "#ffffff",
    },
    "arctic": {
        "name": "❄ Nordic Arctic",
        "bg": "#242933",
        "panel": "#2e3440",
        "accent": "#88c0d0",
        "accent2": "#81a1c1",
        "success": "#a3be8c",
        "warning": "#ebcb8b",
        "danger": "#bf616a",
        "text": "#eceff4",
        "subtext": "#d8dee9",
        "entry_bg": "#3b4252",
        "border": "#4c566a",
        "btn_normal_bg": "#3b4252",
        "btn_normal_fg": "#eceff4",
        "select_bg": "#81a1c1",
        "select_fg": "#2e3440",
    },
    "obsidian": {
        "name": "🖤 Obsidian Cyber",
        "bg": "#121214",
        "panel": "#1e1e24",
        "accent": "#10b981",
        "accent2": "#059669",
        "success": "#22c55e",
        "warning": "#eab308",
        "danger": "#ef4444",
        "text": "#f4f4f5",
        "subtext": "#a1a1aa",
        "entry_bg": "#272730",
        "border": "#3f3f46",
        "btn_normal_bg": "#272730",
        "btn_normal_fg": "#f4f4f5",
        "select_bg": "#10b981",
        "select_fg": "#ffffff",
    },
    "catppuccin": {
        "name": "☕ Catppuccin Mocha",
        "bg": "#1e1e2e",
        "panel": "#181825",
        "accent": "#cba6f7",
        "accent2": "#89b4fa",
        "success": "#a6e3a1",
        "warning": "#f9e2af",
        "danger": "#f38ba8",
        "text": "#cdd6f4",
        "subtext": "#9399b2",
        "entry_bg": "#313244",
        "border": "#45475a",
        "btn_normal_bg": "#313244",
        "btn_normal_fg": "#cdd6f4",
        "select_bg": "#cba6f7",
        "select_fg": "#11111b",
    },
    "matcha": {
        "name": "🍵 Matcha Zen",
        "bg": "#1b2421",
        "panel": "#24302c",
        "accent": "#70a980",
        "accent2": "#95d5b2",
        "success": "#52b788",
        "warning": "#d8b168",
        "danger": "#e76f51",
        "text": "#e9f5ed",
        "subtext": "#8fa89b",
        "entry_bg": "#2c3b36",
        "border": "#3d514a",
        "btn_normal_bg": "#2c3b36",
        "btn_normal_fg": "#e9f5ed",
        "select_bg": "#70a980",
        "select_fg": "#1b2421",
    },
    "pastel": {
        "name": "🌸 Sakura Blossom",
        "bg": "#23181a",
        "panel": "#2d1f23",
        "accent": "#f48fb1",
        "accent2": "#ffd54f",
        "success": "#66bb6a",
        "warning": "#ffd54f",
        "danger": "#e57373",
        "text": "#fff0f5",
        "subtext": "#9ec39a",
        "entry_bg": "#38252b",
        "border": "#c89b7b",
        "btn_normal_bg": "#38252b",
        "btn_normal_fg": "#ffd54f",
        "select_bg": "#f48fb1",
        "select_fg": "#23181a",
    },
    "lego": {
        "name": "🧱 LEGO Classic",
        "bg": "#1c1d22",
        "panel": "#252730",
        "accent": "#ffd500",
        "accent2": "#ffea75",
        "success": "#00a651",
        "warning": "#ff9900",
        "danger": "#d11013",
        "text": "#ffffff",
        "subtext": "#ffd500",
        "entry_bg": "#2e313d",
        "border": "#3d4252",
        "btn_normal_bg": "#2e313d",
        "btn_normal_fg": "#ffffff",
        "select_bg": "#d11013",
        "select_fg": "#ffffff",
    },
    "toyota_gr": {
        "name": "🏁 Toyota GR",
        "bg": "#151619",
        "panel": "#1e2025",
        "accent": "#eb0a1e",
        "accent2": "#ff3344",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#eb0a1e",
        "text": "#ffffff",
        "subtext": "#9ca3af",
        "entry_bg": "#282a30",
        "border": "#383c47",
        "btn_normal_bg": "#282a30",
        "btn_normal_fg": "#ffffff",
        "select_bg": "#eb0a1e",
        "select_fg": "#ffffff",
    },
    "honey_badger": {
        "name": "🦡 Honey Badger",
        "bg": "#121316",
        "panel": "#1b1d22",
        "accent": "#f59e0b",
        "accent2": "#e2e8f0",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "text": "#f8fafc",
        "subtext": "#94a3b8",
        "entry_bg": "#242830",
        "border": "#374151",
        "btn_normal_bg": "#1e222a",
        "btn_normal_fg": "#f8fafc",
        "select_bg": "#f59e0b",
        "select_fg": "#121316",
    },
    "continental": {
        "name": "🪙 The Continental",
        "hidden": True,
        "bg": "#0A0B0E",
        "panel": "#12141A",
        "entry_bg": "#060709",
        "accent": "#D4AF37",
        "accent2": "#E63946",
        "success": "#4EBA6F",
        "warning": "#D4AF37",
        "danger": "#E63946",
        "text": "#F2F4F8",
        "subtext": "#8C93A3",
        "border": "#2E3342",
        "btn_normal_bg": "#12141A",
        "btn_normal_fg": "#D4AF37",
        "btn_accent_fg": "#0A0B0E",
        "select_bg": "#D4AF37",
        "select_fg": "#0A0B0E",
    },
    "brundo_recon": {
        "name": "🐕 Agent Brundo",
        "bg": "#1e140f",
        "panel": "#2c1d16",
        "accent": "#d49b5a",
        "accent2": "#e8c38f",
        "success": "#5b8c5a",
        "warning": "#d49b5a",
        "danger": "#a83e38",
        "text": "#faf6f0",
        "subtext": "#bcaaa4",
        "entry_bg": "#3a271e",
        "border": "#5c3d2e",
        "btn_normal_bg": "#3a271e",
        "btn_normal_fg": "#d49b5a",
        "select_bg": "#d49b5a",
        "select_fg": "#1e140f",
        "hidden": True,
    },
    "aether_horizon": {
        "name": "🌌 Aether Horizon",
        "bg": "#06080F",
        "panel": "#0D111D",
        "entry_bg": "#141A29",
        "accent": "#00D2FF",
        "accent2": "#7C3AED",
        "success": "#10B981",
        "warning": "#FBBF24",
        "danger": "#F43F5E",
        "text": "#F8FAFC",
        "subtext": "#94A3B8",
        "border": "#1E293B",
        "btn_normal_bg": "#0F172A",
        "btn_normal_fg": "#00D2FF",
        "btn_accent_fg": "#06080F",
        "select_bg": "#00D2FF",
        "select_fg": "#06080F",
    },
    "falling_in_reverse": {
        "name": "🔥 Falling In Reverse",
        "hidden": True,
        "bg": "#09090b",
        "panel": "#141216",
        "entry_bg": "#050507",
        "accent": "#ff2a2a",
        "accent2": "#ff6b1a",
        "success": "#10b981",
        "warning": "#ff8c00",
        "danger": "#ff1a1a",
        "text": "#fdf2f4",
        "subtext": "#9ca3af",
        "border": "#3b1d24",
        "btn_normal_bg": "#1c1216",
        "btn_normal_fg": "#ff3b30",
        "btn_accent_fg": "#ffffff",
        "select_bg": "#ff2a2a",
        "select_fg": "#ffffff",
    }
}

FONT      = ("Segoe UI", 10)
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SM   = ("Segoe UI", 9)
FONT_LG   = ("Segoe UI", 12, "bold")
FONT_HEAD = ("Segoe UI", 11, "bold")
FONT_TITLE= ("Segoe UI", 13, "bold")
FONT_CODE = ("Consolas", 9)

THUMB_CONFIG = {
    "Off (Text Only)":     {"rowheight": 24,  "img_size": 0,   "col_width": 0,   "show": "headings"},
    "Small (50px)":        {"rowheight": 56,  "img_size": 50,  "col_width": 64,  "show": "tree headings"},
    "Medium (100px)":      {"rowheight": 110, "img_size": 100, "col_width": 116, "show": "tree headings"},
    "Large (180px)":       {"rowheight": 194, "img_size": 180, "col_width": 196, "show": "tree headings"},
    "Extra Large (250px)": {"rowheight": 266, "img_size": 250, "col_width": 268, "show": "tree headings"},
}

QUOTES = [
    "☀ The Light: Illuminating true merchant origins & unmasking international 3PL drop-shipping fronts.",
    "💡 Tactical Reconnaissance: Transforming raw marketplace darkness into actionable intelligence.",
    "🌐 Cross-Border Visibility: Exposing foreign counterfeiter networks operating behind domestic storefront masks.",
    "👁 Clarity: Stripping away digital landfill noise so analysts operate with unclouded focus.",
    "🛡 Signal Over Noise: Eliminating authorized OEM false positives to isolate high-conviction targets.",
    "🖼 Perceptual Fingerprinting: Collapsing cloned image clutter into unified threat clusters.",
    "🏹 Precision: Executing surgical organic store sweeps that strike high-threat targets without collateral damage.",
    "🎯 Genesis Tactical Feeder: Delivering 100% compliant 18-column datasets ready for instant pipeline injection.",
    "⚖ Evidence-First Standard: Structuring bulletproof chain-of-custody and tamper-evident enforcement dossiers.",
    "⚡ The Tactical Interceptor: Operating at the tip of the spear while the heavy carrier carries the enterprise burden.",
    "🤝 Built by Analysts, for Analysts: Purpose-engineered for the realities of front-line trademark defense.",
    "🔒 Brand Integrity Defended: Protecting genuine craftsmanship and consumer safety worldwide.",
]

EASTER_EGG_QUOTES = [
    "🏎 'I live my life a quarter mile at a time. For those 10 seconds or less... I'm free.' — Dom Toretto",
    "💨 'Too soon, Junior! You didn't double-clutch like you should!'",
    "🔥 'DANGER TO MANIFOLD: Floor pan intact, scraping at maximum velocity!'",
    "🏁 'It don't matter if you win by an inch or a mile. Winning's winning.'",
    "🐎 'Eleanor... Don't you stall on me now, girl!' — Memphis Raines",
    "☕ Converting Caffeine into Intellectual Property Compliance...",
    "⚡ Searching through the eBay Matrix with Supercharged Precision!",
    "🚗 'I need NOS. One of the big ones. No, make it two. By tonight.'",
    "🧱 Careful! Stepped on a red 2x4 Lego brick! Enforcement Defense +100.",
    "✨ 'I knew you were counterfeit when you walked in...' 🎶",
    "🤖 Heimvis Core Online: All-seeing eye tracking rogue syndicates across all dimensions!",
]

EBAY_LOCALES = [
    {"code": "US", "name": "United States", "domain": "ebay.com", "region": "North America", "flag": "🇺🇸"},
    {"code": "CA", "name": "Canada", "domain": "ebay.ca", "region": "North America", "flag": "🇨🇦"},
    {"code": "CA_FR", "name": "Canada (French)", "domain": "cafr.ebay.ca", "region": "North America", "flag": "🇨🇦"},
    {"code": "UK", "name": "United Kingdom", "domain": "ebay.co.uk", "region": "Europe", "flag": "🇬🇧"},
    {"code": "DE", "name": "Germany", "domain": "ebay.de", "region": "Europe", "flag": "🇩🇪"},
    {"code": "AU", "name": "Australia", "domain": "ebay.com.au", "region": "APAC", "flag": "🇦🇺"},
    {"code": "FR", "name": "France", "domain": "ebay.fr", "region": "Europe", "flag": "🇫🇷"},
    {"code": "IT", "name": "Italy", "domain": "ebay.it", "region": "Europe", "flag": "🇮🇹"},
    {"code": "ES", "name": "Spain", "domain": "ebay.es", "region": "Europe", "flag": "🇪🇸"},
    {"code": "NL", "name": "Netherlands", "domain": "ebay.nl", "region": "Europe", "flag": "🇳🇱"},
    {"code": "IE", "name": "Ireland", "domain": "ebay.ie", "region": "Europe", "flag": "🇮🇪"},
    {"code": "AT", "name": "Austria", "domain": "ebay.at", "region": "Europe", "flag": "🇦🇹"},
    {"code": "CH", "name": "Switzerland", "domain": "ebay.ch", "region": "Europe", "flag": "🇨🇭"},
    {"code": "PL", "name": "Poland", "domain": "ebay.pl", "region": "Europe", "flag": "🇵🇱"},
]

MELI_LOCALES = [
    {"code": "MLM", "name": "Mexico", "domain": "listado.mercadolibre.com.mx", "region": "North America", "flag": "🇲🇽", "currency": "MXN"},
    {"code": "MLB", "name": "Brazil", "domain": "lista.mercadolivre.com.br", "region": "South America", "flag": "🇧🇷", "currency": "BRL"},
    {"code": "MLA", "name": "Argentina", "domain": "listado.mercadolibre.com.ar", "region": "South America", "flag": "🇦🇷", "currency": "ARS"},
    {"code": "MCO", "name": "Colombia", "domain": "listado.mercadolibre.com.co", "region": "South America", "flag": "🇨🇴", "currency": "COP"},
    {"code": "MLC", "name": "Chile", "domain": "listado.mercadolibre.cl", "region": "South America", "flag": "🇨🇱", "currency": "CLP"},
    {"code": "MPE", "name": "Peru", "domain": "listado.mercadolibre.com.pe", "region": "South America", "flag": "🇵🇪", "currency": "PEN"},
    {"code": "MLU", "name": "Uruguay", "domain": "listado.mercadolibre.com.uy", "region": "South America", "flag": "🇺🇾", "currency": "UYU"},
]

THEME_QUOTES = {
    "brundo_recon": [
        "🐕 'Brundo sniffed the domestic 3PL warehouse. Dropshippers fled the state.'",
        "🐾 'Status: 14/10 Good Boy. 100% Brand Infringement Quota Retrieved.'",
        "🎾 'Threat classified: Squeaky toy verified counterfeit. Confiscated for rigorous stress testing.'",
        "🦴 'Brundo alerted on a suspicious shipment from Guangzhou. Canine treats authorized.'",
        "🐕 'Agent Brundo K9 Recon: Ears perked, tail wagging, takedown conviction 100%.'",
        "🐾 'Chief Morale Officer Brundo approves this harvest: Extra belly rubs awarded.'",
        "🐕 'Brundo detected unauthorized silicone coasters buried in container 4.'",
        "🐾 'Nap time complete. Resuming high-priority perimeter brand patrol.'",
    ],
    "continental": [
        "🪙 Winston: 'Rules... without them, we live with the animals.'",
        "🪙 Charon: 'Always a pleasure having you with us, Mr. Wick.'",
        "🪙 John Wick: 'Yeah, I'm thinkin' I'm back.'",
        "🪙 The Bowery King: 'Somebody please... get this man a brand library.'",
        "🪙 The Sommelier: 'Something robust, precise... may I suggest a full 16-locale sweep?'",
        "🪙 Winston: 'Si vis pacem, para bellum.'",
        "🪙 Charon: 'Storefronts completely sanitized, sir.'",
        "🪙 Winston: 'Contract fulfilled. High Table dossier compiled.'",
        "🪙 John Wick: 'Whoever comes, whoever it is... I'll kill them. I'll kill them all (from the marketplace).'",
        "🪙 Charon: 'How may I be of service this evening, sir?'",
        "🪙 Winston: 'You have your target. Execute with discretion.'"
    ],
    "honey_badger": [
        "🦡 'Honey Badger doesn't care. Takedowns submitted.'",
        "🦡 'Honey Badger takes what it wants. High-risk counterfeits harvested.'",
        "🦡 'Rogue dropshipper thought they were safe. Honey Badger marched right in.'",
        "🦡 'Fearless reconnaissance: Honey Badger shrugs off listing cloaking.'",
    ],
    "cyberpunk": [
        "⚡ 'Wake up, Samurai. We have counterfeit listings to harvest.'",
        "⚡ 'Night City Netrunner: ICE broken, rogue storefront database decrypted.'",
        "⚡ 'Pre-em quality takedowns. Corpos won't know what hit 'em.'",
        "⚡ 'Cyberware optics calibrated: 0ms latency on brand threat detection.'",
    ],
    "matrix": [
        "💻 'You take the blue pill—the story ends. You run this tool—you stay in Wonderland.'",
        "💻 'There is no spoon... but there are 5,000 infringing listings in the matrix.'",
        "💻 Operator: 'I'm downloading the entire marketplace catalog directly into your dossier.'",
        "💻 Agent: 'Hear that, Mr. Dropshipper? That is the sound of inevitability.'",
    ],
    "toyota_gr": [
        "🏁 Toyota Gazoo Racing: Twin-turbo spooling at 8,500 RPM on the Nürburgring!",
        "🏁 GR Supra & GR Corolla: Corner-carving precision applied to rogue parts sellers.",
        "🏁 TRD Performance: Genuine racing heritage defended from aftermarket pretenders.",
        "🏁 'Pushing the limits for better cars—and zero trademark infringement.'",
    ],
    "gm_heritage": [
        "💎 General Motors & ACDelco: Protecting genuine American craftsmanship from Detroit to the world!",
        "💎 Corvette Z06 & Cadillac V-Series: 670 HP flat-plane crank compliance sweep.",
        "💎 ACDelco Genuine Parts: Counterfeit spark plugs and ignition coils purged.",
        "💎 Heavy-duty Silverado precision: Hauling thousands of infringements off the wire.",
    ],
    "dodge_hellcat": [
        "🔥 6.2L Supercharged HEMI V8 idling at 797 Horsepower. Zero infringement allowed!",
        "🔥 Supercharger whine echoing across the digital highway... SRT defense active!",
        "🔥 MOPAR Or No Car: Genuine parts only. Fake emblems crushed at the drag strip.",
    ],
    "subaru_wrc": [
        "⭐ Symmetrical AWD launching through muddy stages at 120 MPH!",
        "⭐ WRX STI boxer rumble: Maximum grip and traction through murky cross-border seller networks.",
        "⭐ Confidence in Motion: Protecting genuine Subaru heritage across all terrain.",
    ],
    "ford_racing": [
        "🔵 Ford Performance EcoBoost twin-turbos delivering high-octane enforcement!",
        "🔵 Mustang Dark Horse & GT350: V8 roar clearing counterfeit badges from the track.",
        "🔵 Built Ford Tough: Heavy-duty brand defense that outlasts the competition.",
    ],
    "kia_gt": [
        "⚡ Kia GT-Line & Stinger: Twin-turbo 368 HP compliance scanning running at full boost!",
        "⚡ Movement that inspires: Surgical precision across automotive marketplace channels.",
    ],
    "hyundai_n": [
        "⚡ Hyundai N Corner Rascal mode engaged... Zero slip compliance!",
        "⚡ N Grin Shift activated: 20 seconds of maximum overboost brand harvesting!",
    ],
    "bmw_m": [
        "🏁 BMW M shift lights flashing red... Ultimate Driving Machine compliance active!",
        "🏁 S58 Twin-Turbo spooling: M Power precision tracking counterfeit roundels.",
    ],
    "jeep_trail": [
        "🚙 Trail-Rated 4x4 crawling through rocky listings... Nothing gets past.",
        "🚙 Rubicon heavy-duty axles: Clearing uncharted counterfeit terrain.",
    ],
    "lego": [
        "🧱 Careful! Stepped on a red 2x4 Lego brick! Enforcement Defense +100.",
        "🧱 Rebuilding the marketplace brick by authentic brick.",
        "🧱 Everything is awesome—when genuine trademarks are 100% protected!",
    ],
    "taylor_swift": [
        "✨ 'I knew you were counterfeit when you walked in...' 🎶",
        "✨ 'Cause the players gonna play, and the fakers gonna fake... but we shake it off and seize it!' 🎶",
        "✨ 'Look what you made me do: 5,000 listings submitted for takedown.' 🎶",
        "✨ 'Long live all the genuine magic we made.' 🎶",
    ],
    "eleanor": [
        "🐎 'Eleanor: The unicorn of muscle cars. Push the Go-Baby-Go button and hold on tight!' — Memphis Raines",
        "🐎 'Gone in 60 Seconds: 50 rogue storefronts harvested before midnight.'",
        "🐎 Nitrous oxide armed: Dual side exhausts roaring down the digital river basin.",
    ],
    "synthwave": [
        "🕹 High Score: 999,999 PTS! Insert coin to continue.",
        "🕹 Neon grid cruising at sunset: Outrun synthwave bassline powering the harvest.",
        "🕹 1984 Cyber-Highway: Digital tape rewound, rogue catalog sanitized.",
    ],
    "catppuccin": [
        "☕ A velvety warm mocha brewed to perfection. Smooth and cozy.",
        "☕ Pouring fresh espresso shots while automated scrapers do the heavy lifting.",
        "☕ Warm cinnamon foam & soft pastel aesthetics: Peaceful brand enforcement.",
    ],
    "pastel": [
        "🌸 Cherry blossoms drifting gently across the brand library... Zen mode active.",
        "🌸 Gentle sakura petals falling over a completely sanitized results table.",
    ],
    "matcha": [
        "🍵 Whisking ceremonial grade Uji matcha... Mindful, tranquil enforcement.",
        "🍵 Balance, focus, and quiet precision across the digital landscape.",
    ],
    "nfl": [
        "🏈 4th & inches on the goal line... Defense holds the perimeter!",
        "🏈 Red zone blitz: Sacking counterfeit jersey vendors behind the line of scrimmage.",
    ],
    "black_decker": [
        "🔨 High-torque brushless impact driver drilling through database records!",
        "🔨 Industrial-grade reliability: Driving solid evidence into every dossier.",
    ],
    "sprayground": [
        "🎒 Shark mouth teeth exposed... Biting down on unauthorized listings!",
        "🎒 Limited edition streetwear drop secured: Clones and copies rejected.",
    ],
    "nyancat": [
        "🌈 Poptart cat flying through hyperspace trailing rainbows and takedowns!",
        "🌈 8-bit cosmic laser beams purging unauthorized listings across the galaxy!",
    ],
    "arctic": [
        "❄ Sub-zero glacial clarity: Freezing rogue seller accounts in their tracks.",
        "❄ Pure Scandinavian minimalism and crisp sub-arctic brand reconnaissance.",
    ],
    "ocean": [
        "🌊 Deep ocean sonar pinging rogue dropshippers beneath the surface.",
        "🌊 Tidal wave of evidence sweeping clean the marketplace waters.",
    ],
    "obsidian": [
        "🖤 Razor-sharp volcanic glass edges cutting through obfuscated seller listings.",
        "🖤 Stealth obsidian reconnaissance: Zero noise, absolute target conviction.",
    ],
}

THEME_SUBHEADERS = {
    "apollo_exec": "☀ The Light • Clarity • Precision",
    "aether_horizon": "🌌 AETHER NEURAL HORIZON — PURE INTENT • RELENTLESS EXECUTION",
    "continental": "🪙 THE CONTINENTAL — HIGH TABLE EXCOMMUNICADO & SYNDICATE ELIMINATION SUITE",
    "honey_badger": "🦡 HONEY BADGER INTEL — FEARLESS TAKEDOWNS & UNRELENTING RECON",
    "brundo_recon": "🐕 AGENT BRUNDO K9 RECON — 14/10 GOOD BOY • 100% TAKEDOWN RATE",
    "toyota_gr": "🏁 TOYOTA GAZOO RACING & LEXUS — BRAND PROTECTION SUITE",
    "gm_heritage": "💎 GENERAL MOTORS & ACDELCO — IP COMPLIANCE HARVESTER",
    "subaru_wrc": "⭐ SUBARU MOTORSPORTS — SYMMETRICAL COMPLIANCE SHIELD",
    "kia_gt": "⚡ KIA GT-LINE & STINGER — HIGH-BOOST TRADEMARK DEFENSE",
    "hyundai_n": "⚡ HYUNDAI N PERFORMANCE — CORNER RASCAL COMPLIANCE",
    "ford_racing": "🔵 FORD PERFORMANCE RACING — ECOBOOST DEFENSE SUITE",
    "dodge_hellcat": "🔥 DODGE SRT HELLCAT & MOPAR — SUPERCHARGED TRADEMARK SHIELD",
    "jeep_trail": "🚙 JEEP TRAIL RATED 4x4 — ALL-TERRAIN BRAND PROTECTION",
    "bmw_m": "🏁 BMW M MOTORSPORT — ULTIMATE COMPLIANCE MACHINE",
    "lego": "🧱 THE LEGO GROUP — GLOBAL TRADEMARK GUARDIAN",
    "black_decker": "🔨 BLACK & DECKER — INDUSTRIAL BRAND COMPLIANCE",
    "nfl": "🏈 NFL GRIDIRON — OFFICIAL MERCHANDISE ENFORCEMENT",
    "taylor_swift": "✨ TAYLOR SWIFT ERAS — OFFICIAL TRADEMARK DEFENSE",
    "sprayground": "🎒 SPRAYGROUND SHARK — STREETWEAR AUTHENTICITY SHIELD",
    "pastel": "🌸 SAKURA BLOSSOM — ZEN BRAND HARVESTER",
    "eleanor": "🐎 1967 SHELBY GT500 ELEANOR — GO-BABY-GO UNICORN EDITION",
    "synthwave": "🕹 RETRO SYNTHWAVE 80s — ARCADE COMPLIANCE SPECIAL",
    "cyberpunk": "⚡ CYBERPUNK 2077 — NIGHT CITY BRAND RUNNER",
    "matrix": "💻 THE MATRIX HARVESTER — ZERO INFRINGEMENT CONSTRUCT",
    "midnight": "☀ The Light • Clarity • Precision",
    "dark": "☀ The Light • Clarity • Precision",
    "slate": "☀ The Light • Clarity • Precision",
    "navy": "☀ The Light • Clarity • Precision",
    "catppuccin": "☕ MOCHA VELVET — ARTISAN BRAND ENFORCEMENT",
    "forest": "🌲 FOREST CANOPY — SUSTAINABLE IP COMPLIANCE",
    "nord": "❄ NORDIC ARCTIC — PRECISION ICE DEFENSE",
    "falling_in_reverse": "🔥 FALLING IN REVERSE — POPULAR MONSTER SYMPHONY",
}

FIR_QUOTES = [
    "🔥 Ronnie Radke: 'I'm a popular monster... I think I'm going crazy.'",
    "🔥 Ronnie Radke: 'My life is like a video game, trying hard to beat the stage.'",
    "🔥 Ronnie Radke: 'Voices in my head telling me I'm gonna end up dead.'",
    "🔥 Ronnie Radke: 'I got the whole world watching me burn... and I'm loving every minute of it.'",
    "🔥 Ronnie Radke: 'Zombified! Blinded by the media, you're so terrified!'",
    "🔥 Ronnie Radke: 'They wanna cancel me, but I write the damn symphony!'",
    "🔥 Ronnie Radke: 'The drug in me is you... Can't you see that you're suffocating me?'",
    "🔥 Ronnie Radke: 'Fear is what keeps us alive, but revenge is what keeps us focused.'",
    "🔥 Ronnie Radke: 'I'm coming back from the dead, like a phantom in your head!'",
    "🔥 Ronnie Radke: 'All my life I've been running from the pain... now I'm standing in the rain.'"
]

CONTINENTAL_QUOTES = [
    "🪙 Winston: 'Rules... without them, we live with the animals.'",
    "🪙 Charon: 'Always a pleasure having you with us, Mr. Wick.'",
    "🪙 John Wick: 'Yeah, I'm thinkin' I'm back.'",
    "🪙 The Bowery King: 'Somebody please... get this man a brand library.'",
    "🪙 The Sommelier: 'Something robust, precise... may I suggest a full 16-locale sweep?'",
    "🪙 Winston: 'Si vis pacem, para bellum.'",
    "🪙 Charon: 'Storefronts completely sanitized, sir.'",
    "🪙 Winston: 'Contract fulfilled. High Table dossier compiled.'",
    "🪙 John Wick: 'Whoever comes, whoever it is... I'll kill them. I'll kill them all (from the marketplace).'",
    "🪙 Charon: 'How may I be of service this evening, sir?'",
    "🪙 Winston: 'You have your target. Execute with discretion.'"
]


VERSION = "3.0.0"


class EbayTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Apollo v{VERSION}")

        self.data_store     = DataStore()
        # Scraper background/headless mode (Default: True / Silent Background)
        self.headless_var   = tk.BooleanVar(value=bool(self.data_store.get_setting("headless", True)))
        self.scraper        = EbayScraper(headless=self.headless_var.get())
        self.aliexpress_scraper = AliExpressScraper(headless=self.headless_var.get())
        self.wish_scraper   = WishScraper(headless=self.headless_var.get())
        self.temu_scraper   = TemuScraper(headless=self.headless_var.get())
        self.mercadolibre_scraper = MercadoLibreScraper(headless=self.headless_var.get())
        self.redbubble_scraper = RedbubbleScraper(headless=self.headless_var.get())
        self.printerval_scraper = PrintervalScraper(headless=self.headless_var.get())
        self.vinted_scraper = VintedScraper(headless=self.headless_var.get())
        self.tiktok_scraper = TikTokScraper(headless=self.headless_var.get())
        self.manomano_scraper = ManoManoScraper(headless=self.headless_var.get())
        self.scribd_scraper = ScribdScraper(headless=self.headless_var.get())
        self.session_vault = SessionVault()
        self.teepublic_scraper = TeePublicScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.etsy_scraper = EtsyScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.spreadshirt_scraper = SpreadshirtScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.zazzle_scraper = ZazzleScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.cafepress_scraper = CafePressScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.threadless_scraper = ThreadlessScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.teespring_scraper = TeeSpringScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.fineartamerica_scraper = FineArtAmericaScraper(headless=self.headless_var.get(), session_vault=self.session_vault)
        self.marketplace_var= tk.StringVar(value="🛒 eBay.com")
        self.exporter       = ExcelExporter()
        self.visual_catalog = VisualCatalogManager()
        self.visual_harvester = VisualHarvester()
        self.filter_hide_benign_var = tk.BooleanVar(value=True)
        self.filter_only_benign_var = tk.BooleanVar(value=False)
        self.smart_triage_var = tk.BooleanVar(value=True)
        self.show_fluff_var = tk.BooleanVar(value=False)
        self.store_full_sweep_var = tk.BooleanVar(value=False)

        # Load saved theme
        saved_theme_key = self.data_store.get_setting("theme", "apollo_exec")
        if saved_theme_key not in THEMES:
            saved_theme_key = "apollo_exec"
        self.current_theme_key = saved_theme_key
        self.theme = THEMES[self.current_theme_key]

        # Responsive window sizing (Optimized for 1080p, laptop scaling & widescreen displays)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1680, max(1024, int(screen_w * 0.90)))
        win_h = min(1060, max(740, int(screen_h * 0.92)))
        pos_x = max(10, (screen_w - win_w) // 2)
        pos_y = max(10, (screen_h - win_h - 40) // 2)
        self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.minsize(980, 600)
        self.configure(bg=self.theme["bg"])
        self._load_app_icon()

        self.condition_var  = tk.StringVar(value="all")
        self.theme_var      = tk.StringVar(value=self.theme["name"])
        saved_thumb_size    = self.data_store.get_setting("thumb_size", "Medium (100px)")
        if saved_thumb_size not in THUMB_CONFIG:
            saved_thumb_size = "Medium (100px)"
        self.thumb_size_var = tk.StringVar(value=saved_thumb_size)
        self.show_preview_var = tk.BooleanVar(value=(saved_thumb_size != "Off (Text Only)"))
        self.sound_enabled_var = tk.BooleanVar(value=True)

        # Brand targeting states: { item_id: "target" | "exclude" | "neutral" }
        self.brand_states   = {}

        self.results        = []          # all harvested rows this session
        self.seen_item_ids  = set()       # session deduplication
        self.queue          = []          # list of jobs
        self.executed_jobs  = []          # record of executed jobs for audit log
        self.sort_directions= {}          # col -> bool (True = descending)

        # Image thumbnail caches & Hover popup window
        import requests
        self.http_session       = requests.Session()
        self.thumb_executor     = ThreadPoolExecutor(max_workers=32, thread_name_prefix="ApolloThumb")
        self.raw_img_cache      = {}          # url -> PIL.Image (source image)
        self.inline_img_cache   = {}          # (size_key, url) -> PhotoImage (resized for treeview)
        self.img_cache          = {}          # url -> PhotoImage (large hover popup)
        self._placeholders      = {}          # size_px -> PhotoImage
        self.staged_dossier     = self.data_store.get_staged_dossier()  # Multi-Wave Dossier Staging Vault (disk-persisted)
        self.preview_win        = None
        self.last_hovered_iid   = None
        self.preview_cancel_id  = None
        self._drag_data         = None

        # Konami & Secret Easter Egg buffers
        self.konami_sequence = ["Up", "Up", "Down", "Down", "Left", "Right", "Left", "Right", "b", "a"]
        self.konami_buffer   = []
        self.word_buffer     = ""
        self.quote_idx       = 0
        self.achieved_milestones = set()

        self.col_labels = {
            "brand": "Brand",
            "product_type": "Product Type",
            "title": "Title",
            "item_id": "Item ID",
            "price": "Price",
            "seller": "Seller",
            "seller_origin": "Origin",
            "threat_badge": "Threat Intel (3PL / Origin)",
            "location": "Item Location",
            "thumbnail": "Thumbnail URL",
            "url": "Listing URL"
        }
        self.field_map = {
            "brand": "brand",
            "product_type": "product_type",
            "title": "title",
            "item_id": "item_id",
            "price": "price",
            "seller": "seller",
            "seller_origin": "seller_origin",
            "threat_badge": "threat_badge",
            "location": "location",
            "thumbnail": "image_url",
            "url": "url"
        }
        
        # Thread & Execution Control
        self.running        = False
        self.paused         = False
        self.stop_event     = threading.Event()
        self.pause_event    = threading.Event()
        self.pause_event.set()            # Set = unpaused
        # Widget registry for dynamic theme updates
        self.themed_widgets = {
            "bg_frames": [],
            "panel_frames": [],
            "section_labels": [],
            "dividers": [],
            "text_labels": [],
            "subtext_labels": [],
            "text_inputs": [],
            "accent_btns": [],
            "danger_btns": [],
            "normal_btns": [],
            "checks": [],
        }

        # Column Visibility & Analyst Hints
        self.show_hints_var = tk.BooleanVar(value=self.data_store.get_show_analyst_hints())
        self.all_table_cols = ("brand", "product_type", "title", "item_id", "price", "seller", "seller_origin", "threat_badge", "location", "thumbnail", "url")
        saved_vis = self.data_store.get_column_visibility()
        self.col_vis_vars = {col: tk.BooleanVar(value=saved_vis.get(col, True)) for col in self.all_table_cols}

        # Track open modeless windows
        self._win_registry = None
        self._win_importer = None
        self._win_whitelist = None
        self._win_field_guide = None
        self._win_product_type = None

        self._build_ui()
        self._refresh_brand_tree()
        self._refresh_exclusion_list()
        # Global Keyboard Shortcuts
        self.bind_all("<Control-e>", lambda e: self._export())
        self.bind_all("<Control-E>", lambda e: self._export())
        self.bind_all("<F1>", lambda e: self._open_field_guide_modal())

        # Listen globally for Konami Code
        self.bind_all("<Key>", self._check_konami)

        # Restore saved window geometry if present
        saved_geo = self.data_store.get_setting("window_geometry", "")
        if saved_geo:
            try:
                self.geometry(saved_geo)
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(50, self._apply_dark_titlebar)

    def _on_closing(self):
        try:
            self.data_store.set_setting("window_geometry", self.geometry())
            if hasattr(self, "result_tree"):
                col_w = {c: self.result_tree.column(c, "width") for c in self.result_tree["columns"]}
                self.data_store.set_setting("column_widths", col_w)
        except Exception:
            pass
        self.destroy()

    # ══════════════════════════════════════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        t = self.theme
        # ── top bar ──────────────────────────────────────────────────────────
        self.top_bar = tk.Frame(self, bg=t["panel"], pady=6)
        self.top_bar.pack(fill="x")
        self.themed_widgets["panel_frames"].append(self.top_bar)

        # Title & Sub-header container frame
        title_box = tk.Frame(self.top_bar, bg=t["panel"])
        title_box.pack(side="left", padx=16)
        self.themed_widgets["panel_frames"].append(title_box)

        # Clickable interactive title logo (Easter Egg)
        title_row = tk.Frame(title_box, bg=t["panel"], cursor="hand2")
        title_row.pack(anchor="w")
        self.themed_widgets["panel_frames"].append(title_row)

        self.title_icon_lbl = tk.Label(title_row, text="☀", font=("Segoe UI", 12),
                                       bg=t["panel"], fg=t["accent"], cursor="hand2")
        self.title_icon_lbl.pack(side="left")

        self.title_lbl = tk.Label(title_row, text="Apollo Brand Intelligence",
                                  font=("Segoe UI", 12, "bold"), bg=t["panel"], fg=t["accent"],
                                  cursor="hand2")
        self.title_lbl.pack(side="left", padx=(3, 0))
        self.title_lbl.bind("<Button-1>", self._on_title_click)
        self.title_icon_lbl.bind("<Button-1>", self._on_title_click)
        self.themed_widgets["section_labels"].append(self.title_lbl)
        self.themed_widgets["section_labels"].append(self.title_icon_lbl)

        # Dynamic official client/portfolio sub-header
        sub_text = THEME_SUBHEADERS.get(self.current_theme_key, "☀ The Light • Clarity • Precision")
        self.subtitle_lbl = tk.Label(title_box, text=sub_text, font=("Segoe UI", 8, "bold"),
                                     bg=t["panel"], fg=t.get("accent2", t["subtext"]))
        self.subtitle_lbl.pack(anchor="w")
        self.themed_widgets["subtext_labels"].append(self.subtitle_lbl)

        # Right side controls: Professional > Additional > Fun / Info
        top_right = tk.Frame(self.top_bar, bg=t["panel"])
        top_right.pack(side="right", padx=12)
        self.themed_widgets["panel_frames"].append(top_right)

        # 1. Professional / Core Operations
        market_lbl = tk.Label(top_right, text="Platform:", bg=t["panel"], fg=t["subtext"], font=FONT_SM)
        market_lbl.pack(side="left", padx=(0, 2))
        self.themed_widgets["subtext_labels"].append(market_lbl)

        self.market_combo = ttk.Combobox(top_right, textvariable=self.marketplace_var,
                                         values=["🛒 eBay.com", "📚 Scribd.com", "🧰 ManoMano", "🎵 TikTok Shop", "👗 Vinted", "🌐 AliExpress.com", "🌠 Wish.com", "🟠 Temu.com", "🛍 Mercado Libre", "🎨 Redbubble.com", "👕 Printerval.com", "👕 TeePublic.com", "🧶 Etsy.com", "🌿 Spreadshirt.com", "🎨 Zazzle.com", "☕ CafePress.com", "🧵 Threadless.com", "🌱 TeeSpring (Spring)", "🖼 Fine Art America"],
                                         state="readonly", width=19, font=FONT_SM)
        self.market_combo.pack(side="left", padx=(0, 4))
        self.market_combo.bind("<<ComboboxSelected>>", self._on_market_changed)

        # eBay Regional Locale & Reverse Sweep Controls (packed by default for eBay)
        self.ebay_country_var = tk.StringVar(value="🇺🇸 United States (ebay.com)")
        self.ebay_country_combo = ttk.Combobox(
            top_right,
            textvariable=self.ebay_country_var,
            values=[
                "🇺🇸 United States (ebay.com)",
                "🇬🇧 United Kingdom (ebay.co.uk)",
                "🇩🇪 Germany (ebay.de)",
                "🇨🇦 Canada (ebay.ca)",
                "🇦🇺 Australia (ebay.com.au)",
                "🇫🇷 France (ebay.fr)",
                "🇮🇹 Italy (ebay.it)",
                "🇪🇸 Spain (ebay.es)",
                "🇳🇱 Netherlands (ebay.nl)",
                "🇵🇱 Poland (ebay.pl)",
                "🇨🇭 Switzerland (ebay.ch)",
                "🇦🇹 Austria (ebay.at)",
                "🇮🇪 Ireland (ebay.ie)",
                "🌍 All Locales (Reverse Sweep)"
            ],
            state="readonly",
            width=23,
            font=FONT_SM
        )
        self.ebay_country_combo.pack(side="left", padx=(0, 4))
        self.ebay_country_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🌐 eBay target locale set to: {self.ebay_country_var.get()}"))

        # ManoMano Multi-Locale Controls (packed dynamically when ManoMano is active)
        self.manomano_country_var = tk.StringVar(value="🌐 All European Locales")
        self.manomano_country_combo = ttk.Combobox(
            top_right,
            textvariable=self.manomano_country_var,
            values=[
                "🌐 All European Locales",
                "🇫🇷 France (manomano.fr)",
                "🇩🇪 Germany (manomano.de)",
                "🇬🇧 United Kingdom (manomano.co.uk)",
                "🇪🇸 Spain (manomano.es)",
                "🇮🇹 Italy (manomano.it)"
            ],
            state="readonly",
            width=22,
            font=FONT_SM
        )
        self.manomano_login_btn = self._btn(top_right, "🧰 ManoMano Connect", self._launch_manomano_session)

        # AliExpress Regional Controls (packed dynamically)
        self.ali_depth_var = tk.StringVar(value="3 Pages (180)")
        self.ali_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.ali_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "4 Pages (240)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.ali_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🌐 AliExpress scan depth set to: {self.ali_depth_var.get()}"))

        # Mercado Libre Regional Controls (packed dynamically)
        self.meli_country_var = tk.StringVar(value="🇲🇽 Mexico")
        self.meli_country_combo = ttk.Combobox(
            top_right,
            textvariable=self.meli_country_var,
            values=[
                "🇲🇽 Mexico",
                "🇧🇷 Brazil",
                "🇦🇷 Argentina",
                "🇨🇴 Colombia",
                "🇨🇱 Chile",
                "🇵🇪 Peru",
                "🌎 All Latin America"
            ],
            state="readonly",
            width=15,
            font=FONT_SM
        )
        self.meli_depth_var = tk.StringVar(value="2 Pages (100)")
        self.meli_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.meli_depth_var,
            values=["1 Page (50)", "2 Pages (100)", "5 Pages (250)", "10 Pages (500)"],
            state="readonly",
            width=13,
            font=FONT_SM
        )
        self.meli_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"📄 Mercado Libre scan depth set to: {self.meli_depth_var.get()}"))
        self.meli_login_btn = self._btn(top_right, "🔑 MeLi Login", self._launch_meli_login)

        # Vinted Multi-Region Controls (packed dynamically when Vinted is active)
        self.vinted_country_var = tk.StringVar(value="🌍 All Locales (Europe & US)")
        self.vinted_country_combo = ttk.Combobox(
            top_right,
            textvariable=self.vinted_country_var,
            values=[
                "🌍 All Locales (Europe & US)",
                "🇬🇧 United Kingdom",
                "🇫🇷 France",
                "🇩🇪 Germany",
                "🇪🇸 Spain",
                "🇮🇹 Italy",
                "🇵🇱 Poland",
                "🇺🇸 United States",
                "🇳🇱 Netherlands",
                "🇧🇪 Belgium"
            ],
            state="readonly",
            width=24,
            font=FONT_SM
        )
        self.vinted_depth_var = tk.StringVar(value="2 Pages (192)")
        self.vinted_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.vinted_depth_var,
            values=["1 Page (96)", "2 Pages (192)", "4 Pages (384)", "8 Pages (768)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.vinted_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"👗 Vinted scan depth set to: {self.vinted_depth_var.get()}"))
        self.vinted_login_btn = self._btn(top_right, "👗 Vinted Connect", self._launch_vinted_session)
        self.tiktok_login_btn = self._btn(top_right, "🎵 TikTok Connect", self._launch_tiktok_session)
        self.temu_login_btn = self._btn(top_right, "🟠 Temu Connect", self._launch_temu_session)
        self.pod_expand_btn = self._btn(top_right, "👕 Expand POD Variants", self._expand_pod_variants, accent=True)

        # Wish Infinite Scroll Depth Controls (packed dynamically when Wish is active)
        self.wish_depth_var = tk.StringVar(value="Medium (50 Items)")
        self.wish_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.wish_depth_var,
            values=["Quick (25 Items)", "Medium (50 Items)", "Deep (100 Items)", "Maximum (200 Items)"],
            state="readonly",
            width=18,
            font=FONT_SM
        )
        # Redbubble Scan Depth Controls (packed dynamically when Redbubble is active)
        self.rb_depth_var = tk.StringVar(value="2 Pages (100)")
        self.rb_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.rb_depth_var,
            values=["1 Page (50)", "2 Pages (100)", "3 Pages (150)", "5 Pages (250)", "10 Pages (500)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.rb_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🎨 Redbubble scan depth set to: {self.rb_depth_var.get()}"))

        # Printerval Scan Depth Controls (packed dynamically when Printerval is active)
        self.pv_depth_var = tk.StringVar(value="2 Pages (100)")
        self.pv_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.pv_depth_var,
            values=["1 Page (50)", "2 Pages (100)", "3 Pages (150)", "5 Pages (250)", "10 Pages (500)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.pv_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"👕 Printerval scan depth set to: {self.pv_depth_var.get()}"))

        # TeePublic Scan Depth Controls
        self.tp_depth_var = tk.StringVar(value="2 Pages (100)")
        self.tp_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.tp_depth_var,
            values=["1 Page (50)", "2 Pages (100)", "3 Pages (150)", "5 Pages (250)", "10 Pages (500)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.tp_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"👕 TeePublic scan depth set to: {self.tp_depth_var.get()}"))

        # Etsy Scan Depth Controls
        self.etsy_depth_var = tk.StringVar(value="2 Pages (120)")
        self.etsy_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.etsy_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.etsy_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🧶 Etsy scan depth set to: {self.etsy_depth_var.get()}"))

        # Spreadshirt Scan Depth Controls
        self.spreadshirt_depth_var = tk.StringVar(value="2 Pages (120)")
        self.spreadshirt_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.spreadshirt_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.spreadshirt_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🌿 Spreadshirt scan depth set to: {self.spreadshirt_depth_var.get()}"))

        # Zazzle Scan Depth Controls
        self.zazzle_depth_var = tk.StringVar(value="2 Pages (120)")
        self.zazzle_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.zazzle_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.zazzle_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🎨 Zazzle scan depth set to: {self.zazzle_depth_var.get()}"))

        # CafePress Scan Depth Controls
        self.cafepress_depth_var = tk.StringVar(value="2 Pages (120)")
        self.cafepress_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.cafepress_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.cafepress_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"☕ CafePress scan depth set to: {self.cafepress_depth_var.get()}"))

        # Threadless Scan Depth Controls
        self.threadless_depth_var = tk.StringVar(value="2 Pages (120)")
        self.threadless_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.threadless_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.threadless_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🧵 Threadless scan depth set to: {self.threadless_depth_var.get()}"))

        # TeeSpring Scan Depth Controls
        self.teespring_depth_var = tk.StringVar(value="2 Pages (120)")
        self.teespring_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.teespring_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.teespring_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"🌱 TeeSpring scan depth set to: {self.teespring_depth_var.get()}"))

        # Fine Art America Scan Depth Controls
        self.fineartamerica_depth_var = tk.StringVar(value="2 Pages (120)")
        self.fineartamerica_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.fineartamerica_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        # Scribd Scan Depth & Document Mode Controls
        self.scribd_depth_var = tk.StringVar(value="2 Pages (120)")
        self.scribd_depth_combo = ttk.Combobox(
            top_right,
            textvariable=self.scribd_depth_var,
            values=["1 Page (60)", "2 Pages (120)", "3 Pages (180)", "5 Pages (300)"],
            state="readonly",
            width=14,
            font=FONT_SM
        )
        self.scribd_depth_combo.bind("<<ComboboxSelected>>", lambda e: self._log(f"📚 Scribd scan depth set to: {self.scribd_depth_var.get()}"))

        self.scribd_doc_mode_var = tk.StringVar(value="🌐 All Documents")
        self.scribd_doc_mode_combo = ttk.Combobox(
            top_right,
            textvariable=self.scribd_doc_mode_var,
            values=["🌐 All Documents", "🔧 Vehicle Service Manuals", "🚨 OEM Engineering Standards (GMW)", "📑 Technical Service Bulletins (TSB)"],
            state="readonly",
            width=26,
            font=FONT_SM
        )
        self.scribd_doc_mode_combo.bind("<<ComboboxSelected>>", self._on_scribd_doc_mode_changed)

        # Main Toolbar Operational Action Buttons
        self.btn_multi_sector = self._btn(top_right, "🌐 Multi-Sector", self._open_multi_sector_modal, accent=True)
        self.btn_multi_sector.pack(side="left", padx=(0, 2))

        self.btn_import = self._btn(top_right, "📥 Import", self._open_adhoc_importer_window, accent=True)
        self.btn_import.pack(side="left", padx=(0, 2))
        
        self.btn_visual = self._btn(top_right, "🖼 Visual Library", self._open_visual_catalog_modal, accent=True)
        self.btn_visual.pack(side="left", padx=(0, 2))

        self.btn_registry = self._btn(top_right, "🛡 Registry", self._open_enforcement_registry_window)
        self.btn_registry.pack(side="left", padx=(0, 2))

        self.btn_whitelist = self._btn(top_right, "🛡 Whitelist", self._open_whitelist_manager_window)
        self.btn_whitelist.pack(side="left", padx=(0, 2))

        self.btn_guide = self._btn(top_right, "💡 Help & Guide", self._open_analyst_guide_modal, accent=False)
        self.btn_guide.pack(side="left", padx=(0, 4))

        # ── Unified Settings ▾ Menubutton ──
        self.settings_mb = tk.Menubutton(
            top_right,
            text="⚙ Settings ▾",
            font=FONT_NORM,
            bg=t["panel"],
            fg=t["text"],
            activebackground=t["accent"],
            activeforeground="black" if str(t.get("name","")).startswith("⚡") else "white",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        self.settings_mb.pack(side="left", padx=(2, 0))
        self.themed_widgets["normal_btns"].append(self.settings_mb)

        self.settings_menu = tk.Menu(
            self.settings_mb,
            tearoff=0,
            bg=t["panel"],
            fg=t["text"],
            activebackground=t["accent"],
            activeforeground="black" if str(t.get("name","")).startswith("⚡") else "white",
            bd=1,
            relief="solid",
            activeborderwidth=0,
            selectcolor=t["accent"]
        )
        self.settings_mb.config(menu=self.settings_menu)

        # 1. Themes Submenu
        self.theme_menu = tk.Menu(
            self.settings_menu,
            tearoff=0,
            bg=t["panel"],
            fg=t["text"],
            activebackground=t["accent"],
            activeforeground="black" if str(t.get("name","")).startswith("⚡") else "white",
            bd=1,
            relief="solid",
            activeborderwidth=0,
            selectcolor=t["accent"]
        )
        current_key = self.current_theme_key
        for k, th in THEMES.items():
            is_unlocked = (k == "continental" and self.data_store.is_wick_unlocked()) or (k == "brundo_recon" and self.data_store.is_brundo_unlocked())
            if not th.get("hidden", False) or k == current_key or is_unlocked:
                self.theme_menu.add_radiobutton(
                    label=th["name"],
                    value=th["name"],
                    variable=self.theme_var,
                    command=self._on_theme_changed
                )
        self.settings_menu.add_cascade(label="🎨 Themes ▾", menu=self.theme_menu)

        # 2. Column Visibility Submenu
        self.col_menu = tk.Menu(
            self.settings_menu,
            tearoff=0,
            bg=t["panel"],
            fg=t["text"],
            activebackground=t["accent"],
            activeforeground="black" if str(t.get("name","")).startswith("⚡") else "white",
            bd=1,
            relief="solid",
            activeborderwidth=0,
            selectcolor=t["accent"]
        )
        for col_key in self.all_table_cols:
            col_lbl = self.col_labels.get(col_key, col_key.title())
            self.col_menu.add_checkbutton(
                label=col_lbl,
                variable=self.col_vis_vars[col_key],
                command=lambda ck=col_key: self._toggle_column_visibility(ck)
            )
        self.settings_menu.add_cascade(label="👁 Column Visibility ▾", menu=self.col_menu)

        self.settings_menu.add_separator()

        # 3. Automation, Audio & UI Toggles
        self.settings_menu.add_checkbutton(
            label="🔔 Audio Chimes & Threat Alerts",
            variable=self.sound_enabled_var,
            command=lambda: self.data_store.set_setting("sound_enabled", self.sound_enabled_var.get())
        )
        self.settings_menu.add_checkbutton(
            label="💡 Analyst Onboarding Hints & Tooltips",
            variable=self.show_hints_var,
            command=lambda: self.data_store.set_show_analyst_hints(self.show_hints_var.get())
        )
        self.settings_menu.add_checkbutton(
            label="👻 Stealth / Headless Browser Mode",
            variable=self.headless_var,
            command=self._toggle_headless
        )

        self.settings_menu.add_separator()

        # 4. Analyst Intelligence Packs & Sharing
        self.settings_menu.add_command(
            label="📦 Export Analyst Intelligence Pack (.apollo)...",
            command=self._export_intel_pack_dialog
        )
        self.settings_menu.add_command(
            label="📥 Import Analyst Intelligence Pack (.apollo)...",
            command=self._import_intel_pack_dialog
        )

        self.settings_menu.add_separator()

        # 5. Modals & Configuration
        self.settings_menu.add_command(
            label="📄 VeRO Seller Disclosure Parser (.pdf / text)...",
            command=self._open_vero_disclosure_modal
        )
        self.settings_menu.add_command(
            label="🔐 Marketplace Session Vault...",
            command=self._open_session_vault_modal
        )
        self.settings_menu.add_command(
            label="🏷 Product Type & Industry Taxonomy...",
            command=self._open_product_type_manager
        )
        self.settings_menu.add_command(
            label="📚 Open Analyst Field Guide (F1)",
            command=self._open_field_guide_modal
        )
        self.settings_menu.add_command(
            label="ℹ About Apollo Brand Intelligence...",
            command=self._show_about_dialog
        )

        self.theme_combo = None


        # ── status bar (Packed FIRST at bottom so it is permanently pinned to the floor) ───────────
        self.status_bar = tk.Frame(self, bg=t["panel"], pady=4)
        self.status_bar.pack(fill="x", side="bottom")
        self.themed_widgets["panel_frames"].append(self.status_bar)

        self.status_var = tk.StringVar(value="Ready.")
        self.status_lbl = tk.Label(self.status_bar, textvariable=self.status_var,
                                   bg=t["panel"], fg=t["text"], font=FONT_SM)
        self.status_lbl.pack(side="left", padx=12)
        self.themed_widgets["text_labels"].append(self.status_lbl)

        # Style and create Progressbar with vibrant accent animation
        style = ttk.Style()
        style.configure("Apollo.Horizontal.TProgressbar",
                        troughcolor=t["entry_bg"],
                        background=t["accent"],
                        bordercolor=t.get("border", t["entry_bg"]))
        self.progress = ttk.Progressbar(self.status_bar, mode="indeterminate", length=200, style="Apollo.Horizontal.TProgressbar")
        self.progress.pack(side="right", padx=12)

        # Globally prevent ttk.Combobox from intercepting mousewheel scroll and clear text selection on change
        self.bind_class("TCombobox", "<MouseWheel>", lambda e: "break")
        def _clear_combobox_selection(e):
            try:
                e.widget.selection_clear()
                self.focus_set()
            except Exception:
                pass
        self.bind_class("TCombobox", "<<ComboboxSelected>>", _clear_combobox_selection, add="+")

        # ── main paned layout (Expands to fill everything between top and bottom bars) ───────────────
        self.paned = tk.PanedWindow(self, orient="horizontal", bg=t["bg"], sashwidth=6,
                                    sashrelief="flat", bd=0)
        self.paned.pack(fill="both", expand=True, padx=8, pady=6)
        self.themed_widgets["bg_frames"].append(self.paned)

        left  = self._build_left_panel(self.paned)
        right = self._build_right_panel(self.paned)

        self.paned.add(left,  minsize=380, width=420)
        self.paned.add(right, minsize=550)

        # Attach interactive analyst onboarding tooltips
        self._attach_analyst_tooltips()

    # ── LEFT PANEL ────────────────────────────────────────────────────
    def _build_left_panel(self, parent):
        t = self.theme
        container = tk.Frame(parent, bg=t["bg"])
        self.themed_widgets["bg_frames"].append(container)

        canvas = tk.Canvas(container, bg=t["bg"], highlightthickness=0, bd=0)
        self.themed_widgets["bg_frames"].append(canvas)
        vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        frame = tk.Frame(canvas, bg=t["bg"])
        self.themed_widgets["bg_frames"].append(frame)

        frame_window = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_left_frame_config(e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_left_canvas_config(e=None):
            if e and e.width:
                canvas.itemconfig(frame_window, width=e.width)

        frame.bind("<Configure>", _on_left_frame_config)
        canvas.bind("<Configure>", _on_left_canvas_config)
        self._update_left_scrollregion = _on_left_frame_config

        def _on_left_mousewheel(event):
            bbox = canvas.bbox("all")
            if bbox and bbox[3] > canvas.winfo_height():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _on_left_mousewheel)
        frame.bind("<MouseWheel>", _on_left_mousewheel)

        # ── Stores / Sellers input (Multi-store support) ──────────────────────
        store_hdr = tk.Frame(frame, bg=t["bg"])
        store_hdr.pack(fill="x", padx=8, pady=(4, 2))
        self.themed_widgets["bg_frames"].append(store_hdr)

        lbl = tk.Label(store_hdr, text="🏪 Stores / Sellers (One per line or URL)",
                       font=FONT_HEAD, bg=t["bg"], fg=t["text"], cursor="hand2")
        lbl.pack(side="left")
        self.themed_widgets["section_labels"].append(lbl)

        def _clear_stores_input():
            self.store_text.delete("1.0", "end")
            self._restore_store_ph()

        self._btn(store_hdr, "✕ Clear", _clear_stores_input).pack(side="right")
        
        store_frame = tk.Frame(frame, bg=t["bg"])
        store_frame.pack(fill="x", padx=8, pady=(0, 2))
        self.themed_widgets["bg_frames"].append(store_frame)
        
        self.store_text = tk.Text(store_frame, height=2, bg=t["entry_bg"], fg=t["text"],
                                  insertbackground=t["text"], relief="flat", font=FONT_SM,
                                  wrap="none")
        store_vsb = ttk.Scrollbar(store_frame, orient="vertical", command=self.store_text.yview)
        self.store_text.configure(yscrollcommand=store_vsb.set)
        self.store_text.pack(side="left", fill="both", expand=True)
        store_vsb.pack(side="right", fill="y")
        self.themed_widgets["text_inputs"].append(self.store_text)
        
        toggle_stores = self._create_resize_grip(frame, self.store_text, widget_type="lines", min_val=1, max_val=25, default_val=2, max_toggle=10, name="stores")
        
        max_stores_btn = tk.Button(store_hdr, text="⤢", command=toggle_stores, bg=t["bg"], fg=t["subtext"],
                                   relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2",
                                   padx=4, pady=0, activebackground=t["bg"], activeforeground=t["accent"])
        max_stores_btn.pack(side="right", padx=(0, 4))
        self.themed_widgets["text_labels"].append(max_stores_btn)
        lbl.bind("<Double-Button-1>", lambda e: toggle_stores())
        
        self.store_placeholder = "🌐 Global eBay Search: https://www.ebay.com/sch/\n(Leave blank to sweep entire eBay marketplace by keyword, or enter specific store/seller URLs)"
        self.store_text.insert("1.0", self.store_placeholder)
        self.store_text.config(fg=t["subtext"])
        self.store_text.bind("<FocusIn>", self._clear_store_ph)
        self.store_text.bind("<FocusOut>", self._restore_store_ph)

        # Condition filter
        cond_row = tk.Frame(frame, bg=t["bg"])
        cond_row.pack(fill="x", padx=8, pady=(0, 3))
        self.themed_widgets["bg_frames"].append(cond_row)

        cond_lbl = tk.Label(cond_row, text="Condition:", bg=t["bg"], fg=t["subtext"], font=FONT_SM)
        cond_lbl.pack(side="left")
        self.themed_widgets["subtext_labels"].append(cond_lbl)

        ttk.Radiobutton(cond_row, text="All", variable=self.condition_var, value="all").pack(side="left", padx=4)
        ttk.Radiobutton(cond_row, text="New", variable=self.condition_var, value="new").pack(side="left", padx=4)
        ttk.Radiobutton(cond_row, text="Used", variable=self.condition_var, value="used").pack(side="left", padx=4)

        self.full_sweep_cb = tk.Checkbutton(cond_row, text="🏪 Full Store Sweep",
                                            variable=self.store_full_sweep_var,
                                            bg=t["bg"], fg=t["accent"], selectcolor=t["entry_bg"],
                                            activebackground=t["bg"], font=FONT_SM)
        self.full_sweep_cb.pack(side="right", padx=(4, 0))
        self.themed_widgets["checks"].append(self.full_sweep_cb)

        # ── Brand Library & Targeting ─────────────────────────────────────────
        toggle_brands_holder = []
        def _toggle_brands_proxy():
            if toggle_brands_holder:
                toggle_brands_holder[0]()

        self._section(frame, "🏷  Brand Library (Target & Exclude)", toggle_cmd=_toggle_brands_proxy)

        # Target / Exclude State Selection Toolbar (Row 1)
        target_tools_1 = tk.Frame(frame, bg=t["bg"])
        target_tools_1.pack(fill="x", padx=8, pady=(0, 2))
        self.themed_widgets["bg_frames"].append(target_tools_1)

        self._btn(target_tools_1, "🎯 Target", lambda: self._set_selected_mode("target"), accent=True).pack(side="left", padx=(0, 3))
        self._btn(target_tools_1, "🚫 Exclude", lambda: self._set_selected_mode("exclude"), danger=True).pack(side="left", padx=(0, 3))
        self._btn(target_tools_1, "⚪ Neutral", lambda: self._set_selected_mode("neutral")).pack(side="left", padx=(0, 3))
        self._btn(target_tools_1, "✕ Reset All", self._reset_brand_modes).pack(side="right")

        # Fast Auto-Exclude Action Toolbar (Row 2)
        target_tools_2 = tk.Frame(frame, bg=t["bg"])
        target_tools_2.pack(fill="x", padx=8, pady=(0, 3))
        self.themed_widgets["bg_frames"].append(target_tools_2)

        self._btn(target_tools_2, "⚡ Excl Other Brands", self._auto_exclude_other_brands).pack(side="left", padx=(0, 4))
        self._btn(target_tools_2, "⚡ Excl All Others", self._auto_exclude_all_others).pack(side="left")

        brand_ctrl = tk.Frame(frame, bg=t["bg"])
        brand_ctrl.pack(fill="x", padx=8, pady=(0, 2))
        self.themed_widgets["bg_frames"].append(brand_ctrl)

        self.brand_tree = ttk.Treeview(brand_ctrl, height=6, selectmode="extended")
        self.brand_tree["columns"] = ("type", "action")
        self.brand_tree.column("#0",     width=195)
        self.brand_tree.column("type",   width=60, anchor="center")
        self.brand_tree.column("action", width=85, anchor="center")
        self.brand_tree.heading("#0",     text="Brand / Sub-Brand")
        self.brand_tree.heading("type",   text="Type")
        self.brand_tree.heading("action", text="Action")
        
        self.brand_tree.tag_configure("target", foreground=t["success"])
        self.brand_tree.tag_configure("exclude", foreground=t["danger"])
        self.brand_tree.tag_configure("neutral", foreground=t["text"])
        
        self._style_tree(self.brand_tree)
        self.brand_tree.pack(fill="x")

        self.brand_tree.bind("<Double-1>", self._on_tree_double_click)
        self.brand_tree.bind("<space>", lambda e: self._on_tree_double_click(e))
        self.brand_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.brand_tree.bind("<ButtonPress-1>", self._on_brand_drag_start)
        self.brand_tree.bind("<B1-Motion>", self._on_brand_drag_motion)
        self.brand_tree.bind("<ButtonRelease-1>", self._on_brand_drag_release)
        self.brand_tree.bind("<Alt-Up>", lambda e: self._move_selected_brand(-1))
        self.brand_tree.bind("<Alt-Down>", lambda e: self._move_selected_brand(1))
        self.brand_tree.bind("<Control-Up>", lambda e: self._move_selected_brand(-1))
        self.brand_tree.bind("<Control-Down>", lambda e: self._move_selected_brand(1))

        # Brand Library management buttons (Spacious, unclipped 2-tier layout)
        btn_row = tk.Frame(frame, bg=t["bg"])
        btn_row.pack(fill="x", padx=8, pady=2)
        self.themed_widgets["bg_frames"].append(btn_row)

        self._btn(btn_row, "＋ Parent", self._add_parent_brand).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "＋ Sub-Brand", self._add_sub_brand).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "▲ Up", lambda: self._move_selected_brand(-1)).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "▼ Down", lambda: self._move_selected_brand(1)).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "🗑 Remove", self._remove_brand, danger=True).pack(side="right")

        toggle_brands = self._create_resize_grip(frame, self.brand_tree, widget_type="treeview", min_val=3, max_val=40, default_val=6, max_toggle=22, name="brands")
        toggle_brands_holder.append(toggle_brands)

        # Include terms preview
        prev_lbl = tk.Label(frame, text="Active Target Terms Preview (editable for custom keywords):",
                            bg=t["bg"], fg=t["subtext"], font=FONT_SM, cursor="hand2")
        prev_lbl.pack(anchor="w", padx=8, pady=(3, 1))
        self.themed_widgets["subtext_labels"].append(prev_lbl)

        self.include_text = tk.Text(frame, height=2, bg=t["entry_bg"], fg=t["text"],
                                    insertbackground=t["text"], relief="flat", font=FONT_SM,
                                    wrap="word")
        self.include_text.pack(fill="x", padx=8)
        self.themed_widgets["text_inputs"].append(self.include_text)

        toggle_inc = self._create_resize_grip(frame, self.include_text, widget_type="lines", min_val=1, max_val=20, default_val=2, max_toggle=8, name="includes")
        prev_lbl.bind("<Double-Button-1>", lambda e: toggle_inc())

        # ── Exclusion list (Fully Collapsible Container) ─────────────────────
        self.excl_collapsed = False
        def _toggle_excl_visibility():
            if self.excl_collapsed:
                self.excl_container.pack(fill="x", after=excl_sec_frame)
                self.excl_collapsed = False
            else:
                self.excl_container.pack_forget()
                self.excl_collapsed = True

        excl_sec_frame = tk.Frame(frame, bg=t["bg"])
        excl_sec_frame.pack(fill="x", padx=8, pady=(6, 2))
        self.themed_widgets["bg_frames"].append(excl_sec_frame)

        excl_sec_lbl = tk.Label(excl_sec_frame, text="🚫 Generic Exclusion Terms", font=FONT_HEAD, bg=t["bg"], fg=t["accent"], cursor="hand2")
        excl_sec_lbl.pack(side="left")
        self.themed_widgets["section_labels"].append(excl_sec_lbl)

        excl_sec_div = tk.Frame(excl_sec_frame, bg=t["border"], height=1)
        excl_sec_div.pack(side="left", fill="x", expand=True, padx=6)
        self.themed_widgets["dividers"].append(excl_sec_div)

        self.excl_toggle_btn = tk.Button(excl_sec_frame, text="⤢", command=_toggle_excl_visibility, bg=t["bg"], fg=t["subtext"],
                                         relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2", padx=4, pady=0,
                                         activebackground=t["bg"], activeforeground=t["accent"])
        self.excl_toggle_btn.pack(side="right")
        self.themed_widgets["text_labels"].append(self.excl_toggle_btn)
        excl_sec_lbl.bind("<Double-Button-1>", lambda e: _toggle_excl_visibility())

        self.excl_container = tk.Frame(frame, bg=t["bg"])
        self.excl_container.pack(fill="x")
        self.themed_widgets["bg_frames"].append(self.excl_container)

        # Select all / unselect all toolbar
        excl_tools = tk.Frame(self.excl_container, bg=t["bg"])
        excl_tools.pack(fill="x", padx=8, pady=(0, 2))
        self.themed_widgets["bg_frames"].append(excl_tools)

        self._btn(excl_tools, "☑ Select All", self._select_all_exclusions).pack(side="left", padx=(0, 4))
        self._btn(excl_tools, "☐ Unselect All", self._unselect_all_exclusions).pack(side="left")

        excl_outer = tk.Frame(self.excl_container, bg=t["bg"])
        excl_outer.pack(fill="x", padx=8)
        self.themed_widgets["bg_frames"].append(excl_outer)

        self.excl_canvas = tk.Canvas(excl_outer, bg=t["entry_bg"], height=65,
                                     highlightthickness=1,
                                     highlightbackground=t["border"])
        excl_scroll = ttk.Scrollbar(excl_outer, orient="vertical",
                                    command=self.excl_canvas.yview)
        self.excl_canvas.configure(yscrollcommand=excl_scroll.set)
        excl_scroll.pack(side="right", fill="y")
        self.excl_canvas.pack(side="left", fill="both", expand=True)

        self.excl_inner = tk.Frame(self.excl_canvas, bg=t["entry_bg"])
        self._excl_window = self.excl_canvas.create_window(
            (0, 0), window=self.excl_inner, anchor="nw")

        self.excl_inner.bind("<Configure>", lambda e: self.excl_canvas.configure(scrollregion=self.excl_canvas.bbox("all")))
        self.excl_canvas.bind("<Configure>", lambda e: self.excl_canvas.itemconfig(self._excl_window, width=e.width) if e and e.width else None)
        self.excl_canvas.bind("<MouseWheel>", self._on_excl_mousewheel)
        self.excl_inner.bind("<MouseWheel>", self._on_excl_mousewheel)

        self.excl_vars = {}   # term -> BooleanVar

        excl_btn_row = tk.Frame(self.excl_container, bg=t["bg"])
        excl_btn_row.pack(fill="x", padx=8, pady=4)
        self.themed_widgets["bg_frames"].append(excl_btn_row)

        self.new_excl_entry = self._entry(excl_btn_row, placeholder="New generic exclusion")
        self.new_excl_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.new_excl_entry.bind("<Return>", lambda e: self._add_exclusion())
        self._btn(excl_btn_row, "＋ Add", self._add_exclusion).pack(side="left")
        self._btn(excl_btn_row, "✕", self._remove_exclusion, danger=True).pack(side="left", padx=4)

        self._create_resize_grip(self.excl_container, self.excl_canvas, widget_type="canvas_px", min_val=40, max_val=600, default_val=65, max_toggle=260, name="exclusions")

        # ── Queue / Run Controls ──────────────────────────────────────────────
        toggle_queue_holder = []
        def _toggle_queue_proxy():
            if toggle_queue_holder:
                toggle_queue_holder[0]()

        self._section(frame, "📋 Search Queue & Batch Execution", toggle_cmd=_toggle_queue_proxy)

        # ── 1-Click Client Portfolio Sweep Presets ────────────────────────────
        preset_frame = tk.Frame(frame, bg=t["panel"], padx=6, pady=6)
        preset_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.themed_widgets["panel_frames"].append(preset_frame)

        p_top_row = tk.Frame(preset_frame, bg=t["panel"])
        p_top_row.pack(fill="x")
        self.themed_widgets["panel_frames"].append(p_top_row)

        p_lbl = tk.Label(p_top_row, text="📦 Portfolio Preset:", font=("Segoe UI", 9, "bold"),
                         bg=t["panel"], fg=t["accent"])
        p_lbl.pack(side="left")
        self.themed_widgets["section_labels"].append(p_lbl)

        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(p_top_row, textvariable=self.preset_var, state="readonly",
                                         width=22, font=FONT_SM)
        self.preset_combo.pack(side="left", padx=4, fill="x", expand=True)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        self._btn(p_top_row, "💾 Save", self._save_custom_preset).pack(side="left", padx=2)
        self._btn(p_top_row, "🗑", self._delete_custom_preset, danger=True).pack(side="left", padx=2)

        self.sweep_btn = self._btn(
            preset_frame,
            "⚡ 1-Click Sweep: Queue Portfolio for All Stores",
            self._queue_portfolio_preset,
            accent=True
        )
        self.sweep_btn.pack(fill="x", pady=(4, 0))

        q_actions_row = tk.Frame(frame, bg=t["bg"])
        q_actions_row.pack(fill="x", padx=8, pady=(0, 4))
        self.themed_widgets["bg_frames"].append(q_actions_row)

        self.add_q_btn = self._btn(q_actions_row, "➕ Add to Queue", self._add_to_queue)
        self.add_q_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.clean_sweep_btn = self._btn(q_actions_row, "🎯 Clean Brand Sweep", self._queue_clean_targeted_brands, accent=True)
        self.clean_sweep_btn.pack(side="right", fill="x", expand=True, padx=(3, 0))

        queue_frame = tk.Frame(frame, bg=t["bg"])
        queue_frame.pack(fill="x", padx=8, pady=(0, 4))
        self.themed_widgets["bg_frames"].append(queue_frame)

        self.queue_list = tk.Listbox(queue_frame, height=4, bg=t["entry_bg"], fg=t["text"],
                                     selectbackground=t["accent"], selectforeground=t.get("select_fg", "white"),
                                     font=FONT_SM, relief="flat", bd=0, highlightthickness=0,
                                     activestyle="none")
        q_vsb = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_list.yview)
        self.queue_list.configure(yscrollcommand=q_vsb.set)
        self.queue_list.pack(side="left", fill="both", expand=True)
        q_vsb.pack(side="right", fill="y")
        self.queue_list.bind("<Delete>", lambda e: self._remove_selected_from_queue())
        self.queue_list.bind("<BackSpace>", lambda e: self._remove_selected_from_queue())
        self.themed_widgets["text_inputs"].append(self.queue_list)

        toggle_queue = self._create_resize_grip(frame, self.queue_list, widget_type="lines", min_val=2, max_val=40, default_val=4, max_toggle=20, name="queue")
        toggle_queue_holder.append(toggle_queue)

        # Row 1: Execution actions (Run, Pause, Stop)
        q_btn_row1 = tk.Frame(frame, bg=t["bg"])
        q_btn_row1.pack(fill="x", padx=8, pady=(4, 2))
        self.themed_widgets["bg_frames"].append(q_btn_row1)

        self.run_btn = self._btn(q_btn_row1, "▶  Run", self._run_queue, accent=True)
        self.run_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self.pause_btn = self._btn(q_btn_row1, "⏸  Pause", self._toggle_pause)
        self.pause_btn.pack(side="left", padx=2)
        self.pause_btn.config(state="disabled")

        self.stop_btn = self._btn(q_btn_row1, "⏹  Stop", self._stop_scan, danger=True)
        self.stop_btn.pack(side="left", padx=(2, 0))
        self.stop_btn.config(state="disabled")

        # Row 2: Queue maintenance actions (Dedup, Remove, Clear) - full horizontal visibility
        q_btn_row2 = tk.Frame(frame, bg=t["bg"])
        q_btn_row2.pack(fill="x", padx=8, pady=(2, 6))
        self.themed_widgets["bg_frames"].append(q_btn_row2)

        self.dedup_q_btn = self._btn(q_btn_row2, "🧹 Dedup", self._deduplicate_queue)
        self.dedup_q_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.del_q_btn = self._btn(q_btn_row2, "✕ Remove", self._remove_selected_from_queue)
        self.del_q_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.clear_q_btn = self._btn(q_btn_row2, "🗑 Clear", self._clear_queue)
        self.clear_q_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))

        def _bind_left_mousewheel_recursive(w):
            try:
                w.bind("<MouseWheel>", _on_left_mousewheel, add="+")
            except Exception:
                pass
            for child in w.winfo_children():
                # Avoid overriding special scrollable child widgets
                if child not in (getattr(self, "store_text", None), getattr(self, "excl_canvas", None), getattr(self, "brand_tree", None)):
                    _bind_left_mousewheel_recursive(child)

        self.after(300, lambda: _bind_left_mousewheel_recursive(frame))

        return container

    # ── RIGHT PANEL ───────────────────────────────────────────────────────────
    def _build_right_panel(self, parent):
        t = self.theme
        frame = tk.Frame(parent, bg=t["bg"])
        self.themed_widgets["bg_frames"].append(frame)

        # toolbar
        toolbar = tk.Frame(frame, bg=t["panel"], pady=6)
        toolbar.pack(fill="x")
        self.themed_widgets["panel_frames"].append(toolbar)

        res_lbl = tk.Label(toolbar, text="Results", font=FONT_HEAD, bg=t["panel"], fg=t["text"])
        res_lbl.pack(side="left", padx=12)
        self.themed_widgets["text_labels"].append(res_lbl)

        self.result_count = tk.StringVar(value="0 listings")
        count_lbl = tk.Label(toolbar, textvariable=self.result_count,
                             bg=t["panel"], fg=t["subtext"], font=FONT_SM)
        count_lbl.pack(side="left", padx=8)
        self.themed_widgets["subtext_labels"].append(count_lbl)

        # Thumbnail view size selector
        th_lbl = tk.Label(toolbar, text="🖼", bg=t["panel"], fg=t["subtext"], font=FONT_SM)
        th_lbl.pack(side="left", padx=(6, 2))
        self.themed_widgets["subtext_labels"].append(th_lbl)

        self.thumb_size_combo = ttk.Combobox(toolbar, textvariable=self.thumb_size_var,
                                             values=list(THUMB_CONFIG.keys()),
                                             width=15, state="readonly", font=FONT_SM)
        self.thumb_size_combo.pack(side="left", padx=(0, 6))
        self.thumb_size_combo.bind("<<ComboboxSelected>>", self._on_thumb_size_changed)

        # Primary Action: Export (Packed FIRST on right so it is anchored to the far right and NEVER clipped)
        self.btn_export = self._btn(toolbar, "💾 Export", self._export, accent=True)
        self.btn_export.pack(side="right", padx=(4, 2))

        self.btn_multi_loc = self._btn(toolbar, "🌐 Multi-Locale", self._open_multi_locale_expander, accent=False)
        self.btn_multi_loc.pack(side="right", padx=2)

        self.btn_copy_urls = self._btn(toolbar, "📋 Copy", self._copy_all_listing_urls)
        self.btn_copy_urls.pack(side="right", padx=2)

        self.btn_threat_enrich = self._btn(toolbar, "🌍 Threat", self._enrich_seller_threat_intel, accent=False)
        self.btn_threat_enrich.pack(side="right", padx=2)

        self.btn_network_scan = self._btn(toolbar, "🔗 Network", self._open_connected_network_scanner, accent=False)
        self.btn_network_scan.pack(side="right", padx=2)

        self.btn_rescrape = self._btn(toolbar, "🔄 Rescrape", self._rescrape_selected_listings)
        self.btn_rescrape.pack(side="right", padx=2)

        self.btn_edit_item = self._btn(toolbar, "✏ Edit", self._edit_selected_listing)
        self.btn_edit_item.pack(side="right", padx=2)

        self.btn_enrich_sellers = self._btn(toolbar, "🏪 Enrich", self._enrich_sellers)
        self.btn_enrich_sellers.pack(side="right", padx=2)

        self.btn_remove_item = self._btn(toolbar, "✕ Remove", self._remove_selected_results)
        self.btn_remove_item.pack(side="right", padx=2)

        self.btn_clear_res = self._btn(toolbar, "🗑 Clear", self._clear_results, danger=True)
        self.btn_clear_res.pack(side="right", padx=2)

        # ── 1.5 Live Search Filter Bar ────────────────────────────────────────
        filter_bar = tk.Frame(frame, bg=t["panel"], pady=4, padx=8)
        filter_bar.pack(side="top", fill="x", padx=4, pady=(2, 1))
        self.themed_widgets["panel_frames"].append(filter_bar)

        # Live search filter with column selector & negative modifier syntax
        f_lbl = tk.Label(filter_bar, text="🔍 Filter:", font=FONT_SM, bg=t["panel"], fg=t["accent"])
        f_lbl.pack(side="left", padx=(0, 4))
        self.themed_widgets["section_labels"].append(f_lbl)

        # 1. Marketplace Filter Dropdown
        self.filter_mkt_var = tk.StringVar(value="All Marketplaces")
        core_mkts = ["All Marketplaces", "AliExpress", "eBay", "ManoMano", "Mercado Libre", "Printerval", "Redbubble", "Temu", "TikTok Shop", "Vinted", "Wish"]
        self.filter_mkt_combo = ttk.Combobox(filter_bar, textvariable=self.filter_mkt_var,
                                             values=core_mkts, width=15, state="readonly", font=FONT_SM)
        self.filter_mkt_combo.pack(side="left", padx=(0, 4))
        self.filter_mkt_combo.bind("<<ComboboxSelected>>", lambda e: self._repopulate_results_table())

        # 2. Brand Filter Dropdown
        self.filter_brand_var = tk.StringVar(value="All Brands")
        self.filter_brand_combo = ttk.Combobox(filter_bar, textvariable=self.filter_brand_var,
                                               values=["All Brands"], width=13, state="readonly", font=FONT_SM)
        self.filter_brand_combo.pack(side="left", padx=(0, 4))
        self.filter_brand_combo.bind("<<ComboboxSelected>>", lambda e: self._repopulate_results_table())

        # 3. Column Scope Selector
        self.filter_col_var = tk.StringVar(value="Title")
        filter_cols = ["Title", "Seller", "Origin", "Threat Intel", "Item ID", "Brand", "Product Type", "Price", "Location", "All Columns"]
        self.filter_col_combo = ttk.Combobox(filter_bar, textvariable=self.filter_col_var,
                                             values=filter_cols, width=12, state="readonly", font=FONT_SM)
        self.filter_col_combo.pack(side="left", padx=(0, 4))
        self.filter_col_combo.bind("<<ComboboxSelected>>", lambda e: self._repopulate_results_table())

        # 4. Free-Form Text Entry
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._on_filter_changed)
        self.filter_entry = tk.Entry(filter_bar, textvariable=self.filter_var, width=16,
                                     bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"],
                                     relief="flat", font=FONT_SM)
        self.filter_entry.pack(side="left", padx=(0, 4), fill="x", expand=True)
        self.themed_widgets["text_inputs"].append(self.filter_entry)

        self.filter_high_risk_var = tk.BooleanVar(value=False)
        self.hr_cb = tk.Checkbutton(filter_bar, text="🚨 High-Risk", variable=self.filter_high_risk_var,
                                    command=self._repopulate_results_table, bg=t["panel"], fg=t["danger"],
                                    selectcolor=t["entry_bg"], activebackground=t["panel"], font=FONT_SM)
        self.hr_cb.pack(side="left", padx=(2, 2))
        self.themed_widgets["checks"].append(self.hr_cb)

        self.benign_filter_var = tk.StringVar(value="🛡 Hide Benign")
        self.benign_filter_combo = ttk.Combobox(filter_bar, textvariable=self.benign_filter_var,
                                                values=["🛡 Hide Benign", "📁 Show All", "🟢 Benign Only"],
                                                width=15, state="readonly", font=FONT_SM)
        self.benign_filter_combo.pack(side="left", padx=(2, 3))
        self.benign_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._repopulate_results_table())

        self._btn(filter_bar, "✕ Clear", self._clear_filter).pack(side="left", padx=(0, 4))
        self._btn(filter_bar, "✓ Select All Visible", self._select_all_visible).pack(side="left", padx=(0, 4))
        self._btn(filter_bar, "🧹 Dedupe", self._deduplicate_results).pack(side="left", padx=(0, 0))

        # ── 1.6 Bulk Classification & Tagging Toolbar ─────────────────────────
        tag_bar = tk.Frame(frame, bg=t["panel"], pady=4, padx=8)
        tag_bar.pack(side="top", fill="x", padx=4, pady=(1, 2))
        self.themed_widgets["panel_frames"].append(tag_bar)

        self.tag_icon = tk.Label(tag_bar, text="🏷", font=("Segoe UI", 9), bg=t["panel"], fg=t["accent"])
        self.tag_icon.pack(side="left", padx=(0, 2))
        self.themed_widgets["section_labels"].append(self.tag_icon)
        tag_lbl = tk.Label(tag_bar, text="Bulk Tag Selected:", font=("Segoe UI", 9, "bold"),
                           bg=t["panel"], fg=t["text"])
        tag_lbl.pack(side="left", padx=(0, 8))
        self.themed_widgets["text_labels"].append(tag_lbl)

        b_lbl = tk.Label(tag_bar, text="Brand:", font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        b_lbl.pack(side="left", padx=(0, 3))
        self.themed_widgets["subtext_labels"].append(b_lbl)

        self.bulk_brand_var = tk.StringVar(value="(No change)")
        self.bulk_brand_combo = ttk.Combobox(tag_bar, textvariable=self.bulk_brand_var,
                                             width=16, state="readonly", font=FONT_SM)
        self.bulk_brand_combo.pack(side="left", padx=(0, 10))

        pt_lbl = tk.Label(tag_bar, text="Product Type:", font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        pt_lbl.pack(side="left", padx=(0, 3))
        self.themed_widgets["subtext_labels"].append(pt_lbl)

        self.bulk_product_var = tk.StringVar(value="(Select or type...)")
        product_categories = [
            "(Select or type...)",
            "Accessories",
            "Air Filters",
            "Air Intake & Fuel Delivery",
            "Airbag Components",
            "Airbag Covers",
            "Brakes",
            "Decals",
            "Diagnostic Systems",
            "Emblems",
            "Engines & Components",
            "Exhausts & Exhaust Parts",
            "Exterior Lighting",
            "Exterior Parts",
            "Grilles",
            "Ignition Systems",
            "Interior Parts",
            "Merchandise",
            "Oil Filters",
            "Suspension & Steering",
            "Transmission & Drivetrain",
            "Wheel Caps",
        ]
        self.bulk_product_combo = ttk.Combobox(tag_bar, textvariable=self.bulk_product_var,
                                               values=product_categories, width=26, font=FONT_SM)
        self.bulk_product_combo.pack(side="left", padx=(0, 8))

        self._btn(tag_bar, "⚡ Apply to Selected", self._apply_bulk_tag, accent=True).pack(side="left", padx=(0, 6))
        self._btn(tag_bar, "🔄 Re-Scan Visual", self._rescan_visual_matches).pack(side="left", padx=(0, 6))

        # Dossier Staging Vault (Multi-Wave Investigation Cart)
        self.btn_stash_dossier = self._btn(tag_bar, "📥 Stash to Dossier", self._stash_to_dossier)
        self.btn_stash_dossier.pack(side="left", padx=(0, 4))
        self.btn_view_dossier = self._btn(tag_bar, f"📁 Staged ({len(self.staged_dossier)})", self._view_or_restore_dossier)
        self.btn_view_dossier.pack(side="left", padx=(0, 4))

        # ── 1. Activity Log panel (docked firmly to the bottom) ──────────────
        log_frame = tk.Frame(frame, bg=t["bg"])
        log_frame.pack(side="bottom", fill="x", padx=4, pady=(2, 4))
        self.themed_widgets["bg_frames"].append(log_frame)

        log_header = tk.Frame(log_frame, bg=t["bg"])
        log_header.pack(fill="x", padx=4, pady=(2, 0))
        self.themed_widgets["bg_frames"].append(log_header)

        act_lbl = tk.Label(log_header, text="Activity Log", font=FONT_SM, bg=t["bg"], fg=t["subtext"])
        act_lbl.pack(side="left")
        self.themed_widgets["subtext_labels"].append(act_lbl)

        self._btn(log_header, "💾 Export Log", self._export_job_log).pack(side="right")
        self._btn(log_header, "🗑 Clear Log",  self._clear_log).pack(side="right", padx=4)

        log_text_frame = tk.Frame(log_frame, bg=t["bg"])
        log_text_frame.pack(fill="x", padx=4, pady=(2, 0))
        self.themed_widgets["bg_frames"].append(log_text_frame)

        self.log_text = tk.Text(log_text_frame, height=6, bg=t["panel"], fg=t["text"],
                                font=FONT_SM, relief="flat", state="disabled",
                                wrap="word")
        log_vsb = ttk.Scrollbar(log_text_frame, orient="vertical",
                                 command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_vsb.set)
        log_vsb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)
        self.themed_widgets["text_inputs"].append(self.log_text)

        # ── 2. Results Table Container (takes all remaining upper space) ──────
        table_frame = tk.Frame(frame, bg=t["bg"])
        table_frame.pack(side="top", fill="both", expand=True, padx=4, pady=(2, 0))
        self.themed_widgets["bg_frames"].append(table_frame)

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("brand", "product_type", "title", "item_id", "price", "seller", "seller_origin", "threat_badge", "location", "thumbnail", "url")
        init_size = self.thumb_size_var.get()
        init_cfg = THUMB_CONFIG.get(init_size, THUMB_CONFIG["Medium (100px)"])
        self.result_tree = ttk.Treeview(table_frame, columns=cols, show=init_cfg["show"], selectmode="extended", style="Results.Treeview")
        self.result_tree.heading("#0", text="Preview 🖼" if init_cfg["img_size"] > 0 else "", anchor="center",
                                 command=lambda: self._sort_by_column("thumbnail"))
        self.result_tree.column("#0", width=init_cfg["col_width"], minwidth=init_cfg["col_width"], anchor="center", stretch=False)
        saved_col_widths = self.data_store.get_setting("column_widths", {})
        col_widths = {
            "brand": 85,
            "product_type": 115,
            "title": 320,
            "item_id": 105,
            "price": 85,
            "seller": 140,
            "seller_origin": 100,
            "threat_badge": 210,
            "location": 120,
            "thumbnail": 110,
            "url": 220
        }
        for c in cols:
            w = saved_col_widths.get(c, col_widths.get(c, 120)) if isinstance(saved_col_widths, dict) else col_widths.get(c, 120)
            self.result_tree.heading(c, text=self.col_labels[c], anchor="w",
                                     command=lambda _c=c: self._sort_by_column(_c))
            self.result_tree.column(c, width=w, minwidth=50, stretch=False, anchor="w")
        self._style_tree(self.result_tree)
        self._apply_column_visibility()

        vsb = ttk.Scrollbar(table_frame, orient="vertical",   command=self.result_tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.result_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.result_tree.bind("<Double-1>", self._on_result_tree_double_click)
        self.result_tree.bind("<F2>", lambda e: self._edit_selected_listing())
        self.result_tree.bind("<Return>", self._open_url)
        self.result_tree.bind("<Button-3>", self._show_result_context_menu)
        self.result_tree.bind("<Delete>", lambda e: self._remove_selected_results())
        self.result_tree.bind("<BackSpace>", lambda e: self._remove_selected_results())
        self.result_tree.bind("<Control-a>", self._select_all_results)
        self.result_tree.bind("<Control-A>", self._select_all_results)
        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_tree_select)
        self.result_tree.bind("<ButtonRelease-1>", self._on_column_resized)
        
        # Hover thumbnail event bindings
        self.result_tree.bind("<Motion>", self._on_tree_mouse_motion)
        self.result_tree.bind("<Leave>",  self._hide_preview_popup)

        return frame

    def _on_column_resized(self, event=None):
        """Persist column widths whenever an analyst adjusts column separators."""
        try:
            if hasattr(self, "result_tree"):
                col_w = {c: self.result_tree.column(c, "width") for c in self.result_tree["columns"]}
                self.data_store.set_setting("column_widths", col_w)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  FULL DYNAMIC THEME ENGINE
    # ══════════════════════════════════════════════════════════════════════════
    def _refresh_theme_menu(self):
        """Dynamically repopulate theme radio choices including unlocked secret themes."""
        if hasattr(self, "theme_menu") and self.theme_menu:
            self.theme_menu.delete(0, "end")
            current_key = self.current_theme_key
            for k, th in THEMES.items():
                is_unlocked = (k == "continental" and self.data_store.is_wick_unlocked()) or (k == "brundo_recon" and self.data_store.is_brundo_unlocked()) or (k == "falling_in_reverse" and self.data_store.is_fir_unlocked())
                if not th.get("hidden", False) or k == current_key or is_unlocked:
                    self.theme_menu.add_radiobutton(
                        label=th["name"],
                        value=th["name"],
                        variable=self.theme_var,
                        command=self._on_theme_changed
                    )

    def _on_theme_changed(self, event=None):
        selected_name = self.theme_var.get()
        for k, v in THEMES.items():
            if v["name"] == selected_name:
                self.current_theme_key = k
                self.theme = v
                self.data_store.set_setting("theme", k)
                self._apply_full_theme()
                break
        try:
            if hasattr(self, "theme_combo") and self.theme_combo:
                self.theme_combo.selection_clear()
            self.focus_set()
        except Exception:
            pass

    def _apply_full_theme(self):
        t = self.theme
        self.configure(bg=t["bg"])

        # 1. Background frames
        for f in self.themed_widgets["bg_frames"]:
            try: f.configure(bg=t["bg"])
            except Exception: pass

        # 2. Panel frames
        for f in self.themed_widgets["panel_frames"]:
            try: f.configure(bg=t["panel"])
            except Exception: pass

        # 3. Section labels & Title
        for lbl in self.themed_widgets["section_labels"]:
            try: lbl.configure(fg=t["accent"], bg=lbl.master["bg"])
            except Exception: pass

        if hasattr(self, "subtitle_lbl") and self.subtitle_lbl.winfo_exists():
            sub_text = THEME_SUBHEADERS.get(self.current_theme_key, "🛡 ENTERPRISE BRAND ENFORCEMENT & IP HARVESTER")
            self.subtitle_lbl.configure(text=sub_text, fg=t.get("accent2", t["subtext"]), bg=self.subtitle_lbl.master["bg"])

        if hasattr(self, "excl_toggle_btn") and self.excl_toggle_btn.winfo_exists():
            try: self.excl_toggle_btn.configure(bg=t["bg"], fg=t["subtext"], activebackground=t["bg"], activeforeground=t["accent"])
            except Exception: pass

        # 4. Dividers
        for div in self.themed_widgets["dividers"]:
            try: div.configure(bg=t["border"])
            except Exception: pass

        # 5. Standard Text Labels
        for lbl in self.themed_widgets["text_labels"]:
            try: lbl.configure(fg=t["text"], bg=lbl.master["bg"])
            except Exception: pass

        # 6. Subtext Labels
        for lbl in self.themed_widgets["subtext_labels"]:
            try: lbl.configure(fg=t["subtext"], bg=lbl.master["bg"])
            except Exception: pass

        # 7. Text Inputs, Entries, and Listboxes
        for inp in self.themed_widgets["text_inputs"]:
            try:
                sel_fg = t.get("select_fg", "white")
                if isinstance(inp, tk.Listbox):
                    inp.configure(
                        bg=t["entry_bg"],
                        fg=t["text"],
                        selectbackground=t["accent"],
                        selectforeground=sel_fg
                    )
                elif isinstance(inp, tk.Text):
                    bg_col = t["panel"] if inp == self.log_text else t["entry_bg"]
                    inp.configure(
                        bg=bg_col,
                        fg=t["text"],
                        insertbackground=t["text"],
                        selectbackground=t["accent"],
                        selectforeground=sel_fg
                    )
                elif isinstance(inp, tk.Entry):
                    inp.configure(
                        bg=t["entry_bg"],
                        fg=t["text"],
                        insertbackground=t["text"],
                        selectbackground=t["accent"],
                        selectforeground=sel_fg
                    )
            except Exception:
                pass

        # Update placeholder colors if present
        if self.store_text.get("1.0", "end").strip() == self.store_placeholder.strip():
            self.store_text.config(fg=t["subtext"])
        if self.new_excl_entry.get() == "New generic exclusion":
            self.new_excl_entry.config(fg=t["subtext"])

        # 8. Accent Buttons
        for btn in self.themed_widgets["accent_btns"]:
            try: btn.configure(bg=t["accent"], fg=t.get("btn_accent_fg", "black" if t.get("name", "").startswith("⚡") else "white"), activebackground=t["accent2"])
            except Exception: pass

        # 9. Danger Buttons
        for btn in self.themed_widgets["danger_btns"]:
            try: btn.configure(bg=t["danger"], fg="white", activebackground=t["danger"])
            except Exception: pass

        # 10. Normal Buttons
        for btn in self.themed_widgets["normal_btns"]:
            try:
                fg_col = t["btn_normal_fg"]
                btn.configure(bg=t["btn_normal_bg"], fg=fg_col, activebackground=t["border"])
            except Exception: pass

        # 11. Checkboxes
        for cb in self.themed_widgets["checks"]:
            try:
                fg_col = t["danger"] if cb == getattr(self, "hr_cb", None) else (t.get("accent2", t["text"]) if cb == getattr(self, "st_cb", None) else t["text"])
                cb.configure(bg=cb.master["bg"], fg=fg_col, selectcolor=t["accent"], activebackground=cb.master["bg"])
            except Exception: pass

        for m in (getattr(self, "settings_menu", None), getattr(self, "col_menu", None), getattr(self, "theme_menu", None)):
            if m:
                try: m.configure(bg=t["panel"], fg=t["text"], selectcolor=t["accent"], activebackground=t["accent"], activeforeground="black" if is_bright else "white")
                except Exception: pass

        # 12. Exclusion canvas & inner
        try:
            self.excl_canvas.configure(bg=t["entry_bg"], highlightbackground=t["border"])
            self.excl_inner.configure(bg=t["entry_bg"])
        except Exception: pass

        # 13. Treeview & Progressbar Styles
        self._style_tree(self.brand_tree)
        self._style_tree(self.result_tree)
        self.brand_tree.tag_configure("target", foreground=t["success"])
        self.brand_tree.tag_configure("exclude", foreground=t["danger"])
        self.brand_tree.tag_configure("neutral", foreground=t["text"])

        # 14. Activity Log tags
        self.log_text.tag_config("err",  foreground=t["danger"])
        self.log_text.tag_config("info", foreground=t["text"])

        # Dynamic theme-specific button flairs & store placeholder
        if self.current_theme_key == "continental":
            if hasattr(self, "sweep_btn"):
                self.sweep_btn.config(text="⚔ Issue Excommunicado Order: Queue All Targets")
            if hasattr(self, "run_btn"):
                self.run_btn.config(text="▶ Execute Contracts")
            if hasattr(self, "add_q_btn"):
                self.add_q_btn.config(text="➕ Issue Bounty Contract")
            if hasattr(self, "clean_sweep_btn"):
                self.clean_sweep_btn.config(text="🎯 Excommunicado Sweep")
            if "eBay" in getattr(self, "marketplace_var", tk.StringVar()).get():
                old_ph = getattr(self, "store_placeholder", "")
                self.store_placeholder = "Enter target storefronts (One per line) — High Table contracts..."
                if hasattr(self, "store_text"):
                    curr_txt = self.store_text.get("1.0", "end").strip()
                    if not curr_txt or curr_txt == old_ph.strip() or "store1" in curr_txt:
                        self.store_text.delete("1.0", "end")
                        self.store_text.insert("1.0", self.store_placeholder)
                        self.store_text.config(fg=t["subtext"])
        else:
            if hasattr(self, "sweep_btn"):
                self.sweep_btn.config(text="⚡ 1-Click Sweep: Queue Portfolio for All Stores")
            if hasattr(self, "run_btn"):
                self.run_btn.config(text="▶  Run")
            if hasattr(self, "add_q_btn"):
                self.add_q_btn.config(text="➕ Add to Queue")
            if hasattr(self, "clean_sweep_btn"):
                self.clean_sweep_btn.config(text="🎯 Clean Brand Sweep")
            if "eBay" in getattr(self, "marketplace_var", tk.StringVar()).get():
                old_ph = getattr(self, "store_placeholder", "")
                self.store_placeholder = "https://www.ebay.com/str/store1\nstore2\nseller3"
                if hasattr(self, "store_text"):
                    curr_txt = self.store_text.get("1.0", "end").strip()
                    if not curr_txt or curr_txt == old_ph.strip() or "High Table contracts" in curr_txt:
                        self.store_text.delete("1.0", "end")
                        self.store_text.insert("1.0", self.store_placeholder)
                        self.store_text.config(fg=t["subtext"])

        # Refresh Trees & Exclusions list with new colors
        self._refresh_brand_tree()
        self._refresh_exclusion_list()
        self._repopulate_results_table()
        self._hide_preview_popup()
        self._apply_dark_titlebar()
        self._log(f"Theme switched to: {t['name']}")

    def _load_app_icon(self, window=None):
        """Set application icon for main window or top-level dialog."""
        target = window or self
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ico_path = os.path.join(base_dir, "apollo.ico")
            png_path = os.path.join(base_dir, "apollo.png")

            # Try PyInstaller bundled _MEIPASS path first
            if hasattr(sys, "_MEIPASS"):
                p_ico = os.path.join(sys._MEIPASS, "apollo.ico")
                if os.path.exists(p_ico):
                    ico_path = p_ico
                p_png = os.path.join(sys._MEIPASS, "apollo.png")
                if os.path.exists(p_png):
                    png_path = p_png

            if os.path.exists(ico_path):
                target.iconbitmap(ico_path)
            elif os.path.exists(png_path) and HAS_PIL:
                if not hasattr(self, "_cached_app_icon_photo"):
                    img = Image.open(png_path)
                    self._cached_app_icon_photo = ImageTk.PhotoImage(img)
                target.iconphoto(True, self._cached_app_icon_photo)
        except Exception as e:
            logger.debug(f"Could not load app icon: {e}")

    def _center_window(self, win, w=None, h=None):
        """Center a Toplevel window accurately over parent window across multi-monitor setups."""
        width = w or 600
        height = h or 400

        master_x = self.winfo_rootx()
        master_y = self.winfo_rooty()
        master_w = self.winfo_width()
        master_h = self.winfo_height()

        if master_w > 50 and master_h > 50:
            x = master_x + (master_w - width) // 2
            y = master_y + (master_h - height) // 2
            if y < master_y:
                y = master_y + 10
        else:
            x = (win.winfo_screenwidth() - width) // 2
            y = max(30, (win.winfo_screenheight() - height) // 2)

        win.geometry(f"{width}x{height}+{x}+{y}")
        try:
            win.transient(self)
        except Exception:
            pass
        try:
            win.deiconify()
            win.lift()
            win.focus_force()
        except Exception:
            pass

    def _apply_dark_titlebar(self, win=None):
        """Enable immersive dark mode title bar, icon, and custom caption colors via Windows DWM API."""
        target = win if win is not None else self
        self._load_app_icon(target)
        try:
            target.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(target.winfo_id())
            if not hwnd:
                hwnd = target.winfo_id()

            # 1. Immersive dark mode (Windows 10 1809+ / Windows 11)
            for attr in (19, 20):
                v = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))

            # 2. Windows 11 custom title bar caption & text colors (Build 22000+)
            t = self.theme
            bg_hex = t.get("panel", t.get("bg", "#0A0B0E"))
            fg_hex = t.get("text", "#FFFFFF")

            if bg_hex and len(bg_hex) == 7:
                r = int(bg_hex[1:3], 16)
                g = int(bg_hex[3:5], 16)
                b = int(bg_hex[5:7], 16)
                color_ref = (b << 16) | (g << 8) | r
                c_color = ctypes.c_int(color_ref)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c_color), ctypes.sizeof(c_color))

            if fg_hex and len(fg_hex) == 7:
                r = int(fg_hex[1:3], 16)
                g = int(fg_hex[3:5], 16)
                b = int(fg_hex[5:7], 16)
                t_color = (b << 16) | (g << 8) | r
                c_text = ctypes.c_int(t_color)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(c_text), ctypes.sizeof(c_text))
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  WIDGET HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _section(self, parent, text, toggle_cmd=None):
        t = self.theme
        f = tk.Frame(parent, bg=t["bg"])
        f.pack(fill="x", padx=8, pady=(6, 2))
        self.themed_widgets["bg_frames"].append(f)

        lbl = tk.Label(f, text=text, font=FONT_HEAD, bg=t["bg"], fg=t["accent"],
                       cursor="hand2" if toggle_cmd else "")
        lbl.pack(side="left")
        self.themed_widgets["section_labels"].append(lbl)

        div = tk.Frame(f, bg=t["border"], height=1)
        div.pack(side="left", fill="x", expand=True, padx=6)
        self.themed_widgets["dividers"].append(div)

        if toggle_cmd:
            btn = tk.Button(f, text="⤢", command=toggle_cmd, bg=t["bg"], fg=t["subtext"],
                            relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2",
                            padx=4, pady=0, activebackground=t["bg"], activeforeground=t["accent"])
            btn.pack(side="right")
            self.themed_widgets["text_labels"].append(btn)
            lbl.bind("<Double-Button-1>", lambda e: toggle_cmd())

    def _create_resize_grip(self, parent, target_widget, widget_type="lines", min_val=2, max_val=40, default_val=4, max_toggle=20, name="widget"):
        t = self.theme
        grip_frame = tk.Frame(parent, bg=t["bg"], height=8, cursor="size_ns")
        grip_frame.pack(fill="x", padx=8, pady=(1, 4))
        self.themed_widgets["bg_frames"].append(grip_frame)

        grip_line = tk.Frame(grip_frame, bg=t["border"], height=2, cursor="size_ns")
        grip_line.pack(fill="x", pady=(3, 3))
        self.themed_widgets["dividers"].append(grip_line)

        dot = tk.Label(grip_line, text="···", font=("Segoe UI", 6, "bold"), bg=t["border"], fg=t["subtext"], cursor="size_ns")
        dot.place(relx=0.5, rely=0.5, anchor="center")

        drag_state = {
            "start_y": 0,
            "start_val": default_val,
            "current_val": default_val,
            "is_max": False
        }

        def on_enter(e):
            try:
                grip_line.configure(bg=self.theme["accent"])
                dot.configure(bg=self.theme["accent"], fg="#000000" if self.theme.get("btn_accent_fg") else "#ffffff")
            except Exception:
                pass

        def on_leave(e):
            try:
                grip_line.configure(bg=self.theme["border"])
                dot.configure(bg=self.theme["border"], fg=self.theme["subtext"])
            except Exception:
                pass

        def on_press(e):
            drag_state["start_y"] = e.y_root
            if widget_type in ("lines", "treeview"):
                try:
                    drag_state["start_val"] = int(target_widget.cget("height"))
                except Exception:
                    drag_state["start_val"] = default_val
            elif widget_type == "canvas_px":
                try:
                    drag_state["start_val"] = int(target_widget.cget("height"))
                except Exception:
                    drag_state["start_val"] = default_val

        def on_motion(e):
            delta = e.y_root - drag_state["start_y"]
            if widget_type in ("lines", "treeview"):
                step = 18 if widget_type == "lines" else 24
                new_v = max(min_val, min(max_val, drag_state["start_val"] + int(delta / step)))
                if new_v != drag_state["current_val"]:
                    drag_state["current_val"] = new_v
                    target_widget.configure(height=new_v)
                    if hasattr(self, "_update_left_scrollregion"):
                        self._update_left_scrollregion()
            elif widget_type == "canvas_px":
                new_v = max(min_val, min(max_val, drag_state["start_val"] + delta))
                if new_v != drag_state["current_val"]:
                    drag_state["current_val"] = new_v
                    target_widget.configure(height=new_v)
                    if hasattr(self, "_update_left_scrollregion"):
                        self._update_left_scrollregion()

        def toggle_maximize():
            if drag_state["is_max"]:
                target_widget.configure(height=min_val)
                drag_state["current_val"] = min_val
                drag_state["is_max"] = False
            else:
                target_widget.configure(height=max_val)
                drag_state["current_val"] = max_val
                drag_state["is_max"] = True
            if hasattr(self, "_update_left_scrollregion"):
                self._update_left_scrollregion()

        for w in (grip_frame, grip_line, dot):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<ButtonPress-1>", on_press)
            w.bind("<B1-Motion>", on_motion)
            w.bind("<Double-Button-1>", lambda e: toggle_maximize())

        return toggle_maximize

    def _entry(self, parent, placeholder=""):
        t = self.theme
        e = tk.Entry(parent, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"],
                     relief="flat", font=FONT)
        if placeholder:
            e.insert(0, placeholder)
            e.config(fg=t["subtext"])
            e.bind("<FocusIn>",  lambda ev, en=e, ph=placeholder: self._clear_ph(ev, en, ph))
            e.bind("<FocusOut>", lambda ev, en=e, ph=placeholder: self._restore_ph(ev, en, ph))
        self.themed_widgets["text_inputs"].append(e)
        return e

    def _clear_ph(self, ev, entry, ph):
        if entry.get() == ph:
            entry.delete(0, "end")
            entry.config(fg=self.theme["text"])

    def _restore_ph(self, ev, entry, ph):
        if not entry.get():
            entry.insert(0, ph)
            entry.config(fg=self.theme["subtext"])

    def _clear_store_ph(self, ev):
        txt = self.store_text.get("1.0", "end").strip()
        if (txt == self.store_placeholder.strip() or 
            "store1" in txt or 
            "High Table" in txt or
            "Global Wholesale Search" in txt or 
            "aliexpress.com/store/110123456" in txt):
            self.store_text.delete("1.0", "end")
            self.store_text.config(fg=self.theme["text"])

    def _restore_store_ph(self, ev):
        if not self.store_text.get("1.0", "end").strip():
            self.store_text.insert("1.0", self.store_placeholder)
            self.store_text.config(fg=self.theme["subtext"])

    def _get_current_platform_name(self, market_str: str = None) -> str:
        """Resolve canonical platform name from current marketplace selection or passed string."""
        mkt = market_str if market_str is not None else (self.marketplace_var.get() if hasattr(self, "marketplace_var") else "eBay")
        if "Vinted" in mkt:
            return "Vinted"
        elif "TikTok" in mkt:
            return "TikTok Shop"
        elif "ManoMano" in mkt:
            return "ManoMano"
        elif "Wish" in mkt:
            return "Wish"
        elif "Temu" in mkt:
            return "Temu"
        elif "AliExpress" in mkt:
            return "AliExpress"
        elif "Printerval" in mkt:
            return "Printerval"
        elif "Redbubble" in mkt:
            return "Redbubble"
        elif "TeePublic" in mkt:
            return "TeePublic"
        elif "Etsy" in mkt:
            return "Etsy"
        elif "Spreadshirt" in mkt:
            return "Spreadshirt"
        elif "Zazzle" in mkt:
            return "Zazzle"
        elif "CafePress" in mkt:
            return "CafePress"
        elif "Threadless" in mkt:
            return "Threadless"
        elif "TeeSpring" in mkt or "Spring" in mkt:
            return "TeeSpring"
        elif "Fine Art America" in mkt or "Pixels" in mkt:
            return "Fine Art America"
        elif "Scribd" in mkt:
            return "Scribd"
        elif "Mercado" in mkt:
            return "Mercado Libre"
        return "eBay"

    def _get_browser_window_pos(self, bw: int = 1100, bh: int = 800) -> tuple:
        """Calculate screen coordinates to center interactive browser popups on the active monitor."""
        try:
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            pw = self.winfo_width()
            ph = self.winfo_height()
            if pw > 100 and ph > 100:
                offset_x = max(20, (pw - bw) // 2) if pw >= bw else 20
                offset_y = max(20, (ph - bh) // 2) if ph >= bh else 20
                return (px + offset_x, py + offset_y)
            return (100, 100)
        except Exception:
            return (100, 100)

    def _launch_manomano_session(self):
        """Launch interactive Edge session to clear Cloudflare Turnstile for ManoMano."""
        loc = self.manomano_country_var.get() if hasattr(self, "manomano_country_var") else "France"
        clean_loc = "France"
        for k in ["France", "Spain", "Germany", "Italy", "United Kingdom"]:
            if k.lower() in loc.lower():
                clean_loc = k
                break
        w_pos = self._get_browser_window_pos()
        self._log(f"🧰 Launching ManoMano Interactive Session ({clean_loc})...")
        threading.Thread(target=lambda: self.manomano_scraper.launch_interactive_auth(locale_key=clean_loc, window_pos=w_pos), daemon=True).start()

    def _launch_temu_session(self):
        """Launch interactive Edge session to clear Temu guest/login challenge."""
        w_pos = self._get_browser_window_pos()
        self._log("🟠 Launching Temu Interactive Session...")
        threading.Thread(target=lambda: self.temu_scraper.launch_interactive_auth(window_pos=w_pos), daemon=True).start()

    def _on_market_changed(self, event=None):
        market = self.marketplace_var.get()
        t = self.theme
        current_text = self.store_text.get("1.0", "end").strip()

        if hasattr(self, "ebay_country_combo"):
            if "eBay" in market:
                self.ebay_country_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.ebay_country_combo.pack_forget()

        if hasattr(self, "manomano_country_combo"):
            if "ManoMano" in market:
                self.manomano_country_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.manomano_country_combo.pack_forget()

        if hasattr(self, "manomano_login_btn"):
            if "ManoMano" in market:
                after_w = self.manomano_country_combo if hasattr(self, "manomano_country_combo") else self.market_combo
                self.manomano_login_btn.pack(side="left", padx=(0, 4), after=after_w)
            else:
                self.manomano_login_btn.pack_forget()

        if hasattr(self, "ali_depth_combo"):
            if "AliExpress" in market:
                self.ali_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.ali_depth_combo.pack_forget()

        if hasattr(self, "meli_country_combo"):
            if "Mercado Libre" in market:
                self.meli_country_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.meli_country_combo.pack_forget()

        if hasattr(self, "meli_depth_combo"):
            if "Mercado Libre" in market:
                after_w = self.meli_country_combo if hasattr(self, "meli_country_combo") else self.market_combo
                self.meli_depth_combo.pack(side="left", padx=(0, 4), after=after_w)
            else:
                self.meli_depth_combo.pack_forget()

        if hasattr(self, "meli_login_btn"):
            if "Mercado Libre" in market:
                after_widget = self.meli_depth_combo if hasattr(self, "meli_depth_combo") else (self.meli_country_combo if hasattr(self, "meli_country_combo") else self.market_combo)
                self.meli_login_btn.pack(side="left", padx=(0, 4), after=after_widget)
            else:
                self.meli_login_btn.pack_forget()

        if hasattr(self, "vinted_country_combo"):
            if "Vinted" in market:
                self.vinted_country_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.vinted_country_combo.pack_forget()

        if hasattr(self, "vinted_depth_combo"):
            if "Vinted" in market:
                after_w = self.vinted_country_combo if hasattr(self, "vinted_country_combo") else self.market_combo
                self.vinted_depth_combo.pack(side="left", padx=(0, 4), after=after_w)
            else:
                self.vinted_depth_combo.pack_forget()

        if hasattr(self, "vinted_login_btn"):
            if "Vinted" in market:
                after_w = self.vinted_depth_combo if hasattr(self, "vinted_depth_combo") else (self.vinted_country_combo if hasattr(self, "vinted_country_combo") else self.market_combo)
                self.vinted_login_btn.pack(side="left", padx=(0, 4), after=after_w)
            else:
                self.vinted_login_btn.pack_forget()

        if hasattr(self, "tiktok_login_btn"):
            if "TikTok" in market:
                self.tiktok_login_btn.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.tiktok_login_btn.pack_forget()

        if hasattr(self, "temu_login_btn"):
            if "Temu" in market:
                self.temu_login_btn.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.temu_login_btn.pack_forget()

        if hasattr(self, "wish_depth_combo"):
            if "Wish" in market:
                self.wish_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.wish_depth_combo.pack_forget()

        if hasattr(self, "rb_depth_combo"):
            if "Redbubble" in market:
                self.rb_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.rb_depth_combo.pack_forget()

        if hasattr(self, "pv_depth_combo"):
            if "Printerval" in market:
                self.pv_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.pv_depth_combo.pack_forget()

        if hasattr(self, "tp_depth_combo"):
            if "TeePublic" in market:
                self.tp_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.tp_depth_combo.pack_forget()

        if hasattr(self, "etsy_depth_combo"):
            if "Etsy" in market:
                self.etsy_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.etsy_depth_combo.pack_forget()

        if hasattr(self, "spreadshirt_depth_combo"):
            if "Spreadshirt" in market:
                self.spreadshirt_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.spreadshirt_depth_combo.pack_forget()

        if hasattr(self, "zazzle_depth_combo"):
            if "Zazzle" in market:
                self.zazzle_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.zazzle_depth_combo.pack_forget()

        if hasattr(self, "cafepress_depth_combo"):
            if "CafePress" in market:
                self.cafepress_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.cafepress_depth_combo.pack_forget()

        if hasattr(self, "threadless_depth_combo"):
            if "Threadless" in market:
                self.threadless_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.threadless_depth_combo.pack_forget()

        if hasattr(self, "teespring_depth_combo"):
            if "TeeSpring" in market:
                self.teespring_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.teespring_depth_combo.pack_forget()

        if hasattr(self, "scribd_depth_combo") and hasattr(self, "scribd_doc_mode_combo"):
            if "Scribd" in market:
                self.scribd_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
                self.scribd_doc_mode_combo.pack(side="left", padx=(0, 4), after=self.scribd_depth_combo)
            else:
                self.scribd_depth_combo.pack_forget()
                self.scribd_doc_mode_combo.pack_forget()

        if hasattr(self, "fineartamerica_depth_combo"):
            if "Fine Art America" in market:
                self.fineartamerica_depth_combo.pack(side="left", padx=(0, 4), after=self.market_combo)
            else:
                self.fineartamerica_depth_combo.pack_forget()

        if hasattr(self, "pod_expand_btn"):
            if any(k in market for k in ("Printerval", "Redbubble", "TeePublic", "Spreadshirt", "Zazzle", "CafePress", "Threadless", "TeeSpring", "Fine Art America")):
                after_w = self.fineartamerica_depth_combo if ("Fine Art America" in market and hasattr(self, "fineartamerica_depth_combo")) else (self.teespring_depth_combo if ("TeeSpring" in market and hasattr(self, "teespring_depth_combo")) else (self.threadless_depth_combo if ("Threadless" in market and hasattr(self, "threadless_depth_combo")) else (self.cafepress_depth_combo if ("CafePress" in market and hasattr(self, "cafepress_depth_combo")) else (self.zazzle_depth_combo if ("Zazzle" in market and hasattr(self, "zazzle_depth_combo")) else (self.spreadshirt_depth_combo if ("Spreadshirt" in market and hasattr(self, "spreadshirt_depth_combo")) else (self.tp_depth_combo if ("TeePublic" in market and hasattr(self, "tp_depth_combo")) else (self.rb_depth_combo if ("Redbubble" in market and hasattr(self, "rb_depth_combo")) else (self.pv_depth_combo if ("Printerval" in market and hasattr(self, "pv_depth_combo")) else self.market_combo))))))))
                self.pod_expand_btn.pack(side="left", padx=(0, 4), after=after_w)
            else:
                self.pod_expand_btn.pack_forget()

        if "Scribd" in market:
            self.store_placeholder = "📚 Scribd Document Search: https://www.scribd.com/search?content_type=documents\n(Leave blank to sweep Scribd documents, or enter specific uploader/document URLs: https://www.scribd.com/doc/12345)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "vinted.", "tiktok.com", "manomano.", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("📚 Switched platform to: Scribd.com (Documents)")
        elif "TikTok" in market:
            self.store_placeholder = "🎵 TikTok Shop Search: https://shop.tiktok.com/us\n(Leave blank to sweep TikTok Shop, or enter specific product/store URLs: https://shop.tiktok.com/us/pdp/...)"
            if not current_text or "ebay.com" in current_text or "aliexpress.com" in current_text or "wish.com" in current_text or "temu.com" in current_text or "mercadolibre" in current_text or "redbubble.com" in current_text or "printerval.com" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🎵 Switched platform to: TikTok Shop (shop.tiktok.com active)")
        elif "ManoMano" in market:
            self.store_placeholder = "🧰 ManoMano Search: https://www.manomano.fr/recherche/\n(Leave blank to sweep ManoMano catalog by brand/keyword, or enter specific merchant URLs: https://www.manomano.fr/marchand-41084935)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "vinted.", "tiktok.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log(f"🧰 Switched platform to: ManoMano ({self.manomano_country_var.get()} active)")
        elif "Vinted" in market:
            self.store_placeholder = "👗 Global Vinted Search: https://www.vinted.co.uk/catalog\n(Leave blank to sweep entire Vinted marketplace, or enter specific member profile URLs: https://www.vinted.co.uk/member/123456-seller)"
            if not current_text or "ebay.com" in current_text or "aliexpress.com" in current_text or "wish.com" in current_text or "temu.com" in current_text or "mercadolibre" in current_text or "redbubble.com" in current_text or "printerval.com" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log(f"👗 Switched platform to: Vinted ({self.vinted_country_var.get()} active)")
        elif "AliExpress" in market:
            self.store_placeholder = "🌐 Global Wholesale Search: https://www.aliexpress.com/w/wholesale-\n(Leave blank to sweep entire AliExpress marketplace, or enter specific store URLs)"
            if not current_text or "ebay.com" in current_text or "wish.com" in current_text or "temu.com" in current_text or "mercadolibre" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🌐 Switched platform to: AliExpress.com (Global Wholesale & Store Search active)")
        elif "Wish" in market:
            self.store_placeholder = "🌐 Global Wish Search: https://www.wish.com/search/\n(Leave blank to sweep entire Wish marketplace, or enter specific merchant URLs)"
            if not current_text or "ebay.com" in current_text or "aliexpress.com" in current_text or "temu.com" in current_text or "mercadolibre" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🌠 Switched platform to: Wish.com (Global Catalog & Merchant Sweeps active)")
        elif "Temu" in market:
            self.store_placeholder = "🌐 Global Temu Search: https://www.temu.com/search_result.html\n(Leave blank to sweep entire Temu marketplace, or enter specific mall URLs)"
            if not current_text or "ebay.com" in current_text or "aliexpress.com" in current_text or "wish.com" in current_text or "mercadolibre" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🟠 Switched platform to: Temu.com (Global Catalog & Mall Sweeps active)")
        elif "Mercado Libre" in market:
            self.store_placeholder = "🌐 Global Mercado Libre Search: https://listado.mercadolibre.com.mx/\n(Leave blank to sweep entire Mercado Libre marketplace, or enter specific seller/store URLs)"
            if not current_text or "ebay.com" in current_text or "aliexpress.com" in current_text or "wish.com" in current_text or "temu.com" in current_text or "redbubble.com" in current_text or "printerval.com" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🇲🇽 Switched platform to: Mercado Libre (Latin America Search active). Tip: Click '🔑 MeLi Login' to log in once.")
        elif "Redbubble" in market:
            self.store_placeholder = "🌐 Global Redbubble Search: https://www.redbubble.com/shop/\n(Leave blank to sweep entire Redbubble catalog, or enter specific artist shop URLs: https://www.redbubble.com/people/artist/shop)"
            if not current_text or "ebay.com" in current_text or "aliexpress.com" in current_text or "wish.com" in current_text or "temu.com" in current_text or "mercadolibre" in current_text or "printerval.com" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🎨 Switched platform to: Redbubble.com (Global Catalog & Artist Sweeps active)")
        elif "Printerval" in market:
            self.store_placeholder = "🌐 Global Printerval Search: https://printerval.com/search\n(Leave blank to sweep entire Printerval catalog, or enter specific shop URLs: https://printerval.com/shop/creator)"
            if not current_text or "ebay.com" in current_text or "aliexpress.com" in current_text or "wish.com" in current_text or "temu.com" in current_text or "mercadolibre" in current_text or "redbubble.com" in current_text or "store2" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("👕 Switched platform to: Printerval.com (Global Catalog & Creator Sweeps active)")
        elif "TeePublic" in market:
            self.store_placeholder = "🌐 Global TeePublic Search: https://www.teepublic.com/t-shirts\n(Leave blank to sweep entire TeePublic catalog, or enter specific artist shop URLs: https://www.teepublic.com/user/artist)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("👕 Switched platform to: TeePublic.com (Global Catalog & Artist Sweeps active)")
        elif "Etsy" in market:
            self.store_placeholder = "🌐 Global Etsy Search: https://www.etsy.com/search\n(Leave blank to sweep entire Etsy marketplace, or enter specific shop URLs: https://www.etsy.com/shop/ShopName)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🧶 Switched platform to: Etsy.com (Commercial Listings & Shop Sweeps active)")
        elif "Spreadshirt" in market:
            self.store_placeholder = "🌐 Global Spreadshirt Search: https://www.spreadshirt.com/shop/\n(Leave blank to sweep entire Spreadshirt / Spreadshop catalog, or enter designer storefronts: https://www.spreadshirt.com/user/creator)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🌿 Switched platform to: Spreadshirt.com (Global Catalog & Designer Sweeps active)")
        elif "Zazzle" in market:
            self.store_placeholder = "🌐 Global Zazzle Search: https://www.zazzle.com/s/\n(Leave blank to sweep entire Zazzle catalog, or enter creator store URLs: https://www.zazzle.com/store/creatorname)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🎨 Switched platform to: Zazzle.com (Global Catalog & Creator Sweeps active)")
        elif "CafePress" in market:
            self.store_placeholder = "🌐 Global CafePress Search: https://www.cafepress.com/+\n(Leave blank to sweep entire CafePress catalog, or enter profile/shop URLs: https://www.cafepress.com/profile/creator)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("☕ Switched platform to: CafePress.com (Global Catalog & Store Sweeps active)")
        elif "Threadless" in market:
            self.store_placeholder = "🌐 Global Threadless Search: https://www.threadless.com/search/\n(Leave blank to sweep entire Threadless catalog, or enter Artist Shop URLs: https://artistname.threadless.com)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🧵 Switched platform to: Threadless.com (Global Catalog & Artist Shops active)")
        elif "TeeSpring" in market or "Spring" in market:
            self.store_placeholder = "🌐 Global TeeSpring (Spring) Search: https://spring.com/search\n(Leave blank to sweep Spring creator marketplace, or enter creator store URLs: https://storename.creator-spring.com)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🌱 Switched platform to: TeeSpring / Spring (Creator Marketplace active)")
        elif "Fine Art America" in market or "Pixels" in market:
            self.store_placeholder = "🌐 Global Fine Art America Search: https://fineartamerica.com/art/\n(Leave blank to sweep Fine Art America catalog, or enter artist profile URLs: https://fineartamerica.com/profiles/artistname)"
            if not current_text or any(k in current_text for k in ("ebay.com", "aliexpress.com", "wish.com", "temu.com", "mercadolibre", "redbubble.com", "printerval.com", "store2", "Global")):
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🖼 Switched platform to: Fine Art America (Global Art & Prints active)")
        else:
            self.store_placeholder = "🌐 Global eBay Search: https://www.ebay.com/sch/\n(Leave blank to sweep entire eBay marketplace by keyword, or enter specific store/seller URLs)"
            if not current_text or "vinted.co" in current_text or "aliexpress.com" in current_text or "wish.com" in current_text or "temu.com" in current_text or "mercadolibre" in current_text or "redbubble.com" in current_text or "printerval.com" in current_text or "store1" in current_text or "Global" in current_text:
                self.store_text.delete("1.0", "end")
                self.store_text.insert("1.0", self.store_placeholder)
                self.store_text.config(fg=t["subtext"])
            self._log("🛒 Switched platform to: eBay.com (Global Search & Store Sweeps active)")

    def _on_scribd_doc_mode_changed(self, event=None):
        """Handle analyst selecting a Scribd document filtering mode."""
        mode_val = self.scribd_doc_mode_var.get() if hasattr(self, "scribd_doc_mode_var") else "🌐 All Documents"
        self._log(f"📚 Scribd document mode set to: {mode_val}")

    def _get_global_token(self):
        """Get the canonical global sweep token for current marketplace."""
        market = self.marketplace_var.get() if hasattr(self, "marketplace_var") else "eBay"
        if "ManoMano" in market: return ["🧰 Global ManoMano Search"]
        if "Vinted" in market: return ["👗 Global Vinted Search"]
        if "AliExpress" in market: return ["🌐 Global AliExpress Search"]
        if "Wish" in market: return ["🌐 Global Wish Search"]
        if "Temu" in market: return ["🌐 Global Temu Search"]
        if "TikTok" in market: return ["🎵 Global TikTok Shop Search"]
        if "Mercado" in market: return ["🌐 Global Mercado Libre Search"]
        if "Redbubble" in market: return ["🌐 Global Redbubble Search"]
        if "Printerval" in market: return ["🌐 Global Printerval Search"]
        if "TeePublic" in market: return ["🌐 Global TeePublic Search"]
        if "Etsy" in market: return ["🌐 Global Etsy Search"]
        if "Spreadshirt" in market: return ["🌐 Global Spreadshirt Search"]
        if "Zazzle" in market: return ["🌐 Global Zazzle Search"]
        if "CafePress" in market: return ["🌐 Global CafePress Search"]
        if "Threadless" in market: return ["🌐 Global Threadless Search"]
        if "TeeSpring" in market or "Spring" in market: return ["🌐 Global TeeSpring (Spring) Search"]
        if "Fine Art America" in market or "Pixels" in market: return ["🌐 Global Fine Art America Search"]
        if "Scribd" in market: return ["📚 Global Scribd Search"]
        return ["🛒 Global eBay Search"]
        return ["🛒 Global eBay Search"]

    def _get_stores_from_input(self):
        """Parse stores from input text box, safely ignoring placeholders and handling Global platform modes."""
        raw_text = self.store_text.get("1.0", "end").strip()
        if (not raw_text or 
            raw_text == self.store_placeholder.strip() or 
            "Global" in raw_text or 
            "store1" in raw_text or 
            "enter store" in raw_text.lower() or
            "leave blank to sweep" in raw_text.lower()):
            return self._get_global_token()

        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        valid_stores = []
        ignored_exact = {
            "https://www.ebay.com/str/store1",
            "https://www.ebay.com/sch/",
            "https://www.ebay.com",
            "store1",
            "store2",
            "seller3",
            "https://www.aliexpress.com/store/110123456",
            "https://www.aliexpress.com/w/wholesale-",
            "https://www.wish.com/search/",
            "https://www.temu.com/search_result.html",
            "https://shop.tiktok.com/us",
            "https://shop.tiktok.com",
            "@creator",
            "https://listado.mercadolibre.com.mx/",
            "https://www.redbubble.com/shop/",
            "https://printerval.com/search",
            "https://www.manomano.fr/recherche/",
            "https://www.manomano.fr/marchand-41084935"
        }
        for l in lines:
            low = l.lower()
            if low in ignored_exact or "leave blank to sweep" in low or "global" in low:
                continue
            valid_stores.append(l)

        if not valid_stores:
            return self._get_global_token()

        return valid_stores

    def _btn(self, parent, text, cmd, accent=False, danger=False):
        t = self.theme
        if accent:
            bg = t["accent"]
            fg = t.get("btn_accent_fg", "black" if t.get("name", "").startswith("⚡") else "white")
            active_bg = t["accent2"]
        elif danger:
            bg = t["danger"]
            fg = "white"
            active_bg = t["danger"]
        else:
            bg = t["btn_normal_bg"]
            fg = t["btn_normal_fg"]
            active_bg = t["border"]

        btn = tk.Button(parent, text=text, command=cmd,
                        bg=bg, fg=fg, relief="flat",
                        font=FONT_SM, padx=8, pady=3,
                        activebackground=active_bg, cursor="hand2")

        if accent:
            self.themed_widgets["accent_btns"].append(btn)
        elif danger:
            self.themed_widgets["danger_btns"].append(btn)
        else:
            self.themed_widgets["normal_btns"].append(btn)

        return btn

    def _style_tree(self, tree):
        t = self.theme
        style = ttk.Style()
        style.theme_use("clam")
        
        # Base treeview styling (Brand list, 24px)
        style.configure("Treeview",
                        background=t["entry_bg"], foreground=t["text"],
                        fieldbackground=t["entry_bg"],
                        bordercolor=t["border"],
                        darkcolor=t["border"],
                        lightcolor=t["border"],
                        rowheight=24,
                        font=FONT_SM)
        style.configure("Treeview.Heading",
                        background=t["panel"], foreground=t["text"],
                        font=FONT_SM, relief="flat")
        style.map("Treeview", background=[("selected", t["select_bg"])],
                              foreground=[("selected", t["select_fg"])])

        # Results treeview with configurable rowheight for inline thumbnails
        size_key = self.thumb_size_var.get() if hasattr(self, "thumb_size_var") else "Medium (100px)"
        cfg = THUMB_CONFIG.get(size_key, THUMB_CONFIG["Medium (100px)"])
        style.configure("Results.Treeview",
                        background=t["entry_bg"], foreground=t["text"],
                        fieldbackground=t["entry_bg"],
                        bordercolor=t["border"],
                        darkcolor=t["border"],
                        lightcolor=t["border"],
                        rowheight=cfg["rowheight"],
                        font=FONT_SM)
        style.configure("Results.Treeview.Heading",
                        background=t["panel"], foreground=t["text"],
                        font=FONT_SM, relief="flat")
        style.map("Results.Treeview", background=[("selected", t["select_bg"])],
                                     foreground=[("selected", t["select_fg"])])

        # Radiobutton style
        style.configure("TRadiobutton",
                        background=t["bg"], foreground=t["text"])
        style.map("TRadiobutton",
                  background=[("active", t["bg"])],
                  foreground=[("active", t["text"])])

        # Progressbar style
        style.configure("TProgressbar",
                        background=t["accent"],
                        troughcolor=t["entry_bg"])

        # Scrollbar styles (Flat, unified, zero white highlights or blurred grip bars)
        style.configure("TScrollbar",
                        background=t["panel"],
                        troughcolor=t["entry_bg"],
                        bordercolor=t["border"],
                        darkcolor=t["panel"],
                        lightcolor=t["panel"],
                        arrowcolor=t["accent"],
                        gripcount=0,
                        relief="flat")
        style.map("TScrollbar",
                  background=[("active", t["accent"]), ("pressed", t.get("accent2", t["accent"]))],
                  darkcolor=[("active", t["panel"]), ("pressed", t["panel"])],
                  lightcolor=[("active", t["panel"]), ("pressed", t["panel"])],
                  bordercolor=[("active", t["border"]), ("pressed", t["border"])])

        style.configure("Vertical.TScrollbar",
                        background=t["panel"],
                        troughcolor=t["entry_bg"],
                        bordercolor=t["border"],
                        darkcolor=t["panel"],
                        lightcolor=t["panel"],
                        arrowcolor=t["accent"],
                        gripcount=0,
                        relief="flat")
        style.map("Vertical.TScrollbar",
                  background=[("active", t["accent"]), ("pressed", t.get("accent2", t["accent"]))],
                  darkcolor=[("active", t["panel"]), ("pressed", t["panel"])],
                  lightcolor=[("active", t["panel"]), ("pressed", t["panel"])],
                  bordercolor=[("active", t["border"]), ("pressed", t["border"])])

        style.configure("Horizontal.TScrollbar",
                        background=t["panel"],
                        troughcolor=t["entry_bg"],
                        bordercolor=t["border"],
                        darkcolor=t["panel"],
                        lightcolor=t["panel"],
                        arrowcolor=t["accent"],
                        gripcount=0,
                        relief="flat")
        style.map("Horizontal.TScrollbar",
                  background=[("active", t["accent"]), ("pressed", t.get("accent2", t["accent"]))],
                  darkcolor=[("active", t["panel"]), ("pressed", t["panel"])],
                  lightcolor=[("active", t["panel"]), ("pressed", t["panel"])],
                  bordercolor=[("active", t["border"]), ("pressed", t["border"])])

        # Combobox style
        is_bright = t.get("name", "").startswith("⚡") or t.get("name", "").startswith("🪙")
        style.configure("TCombobox",
                        fieldbackground=t["entry_bg"],
                        background=t["panel"],
                        foreground=t["text"],
                        selectbackground=t["accent"],
                        selectforeground="black" if is_bright else "white",
                        bordercolor=t["border"],
                        darkcolor=t["border"],
                        lightcolor=t["border"],
                        arrowcolor=t["accent"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", t["entry_bg"])],
                  selectbackground=[("readonly", t["accent"])],
                  selectforeground=[("readonly", "black" if is_bright else "white")],
                  background=[("readonly", t["panel"])],
                  foreground=[("readonly", t["text"])])

        # Notebook & Tab styling (Eliminates white lines, bevels & borders across all tabbed views)
        style.configure("TNotebook",
                        background=t["bg"],
                        bordercolor=t["border"],
                        darkcolor=t["bg"],
                        lightcolor=t["bg"],
                        tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab",
                        background=t["panel"],
                        foreground=t["text"],
                        bordercolor=t["border"],
                        darkcolor=t["panel"],
                        lightcolor=t["panel"],
                        padding=[14, 6],
                        font=FONT_SM)
        style.map("TNotebook.Tab",
                  background=[("selected", t["accent"]), ("active", t["border"])],
                  foreground=[("selected", t.get("btn_accent_fg", "black" if t.get("name", "").startswith("⚡") else "white")),
                              ("active", t["text"])],
                  darkcolor=[("selected", t["accent"]), ("active", t["border"])],
                  lightcolor=[("selected", t["accent"]), ("active", t["border"])],
                  bordercolor=[("selected", t["accent"]), ("active", t["border"])])

        # Style About dialog specific notebook tabs identically
        style.configure("About.TNotebook",
                        background=t["bg"],
                        bordercolor=t["border"],
                        darkcolor=t["bg"],
                        lightcolor=t["bg"],
                        tabmargins=[2, 5, 2, 0])
        style.configure("About.TNotebook.Tab",
                        background=t["panel"],
                        foreground=t["text"],
                        bordercolor=t["border"],
                        darkcolor=t["panel"],
                        lightcolor=t["panel"],
                        padding=[16, 8],
                        font=("Segoe UI", 9, "bold"))
        style.map("About.TNotebook.Tab",
                  background=[("selected", t["accent"]), ("active", t["border"])],
                  foreground=[("selected", t.get("btn_accent_fg", "black" if t.get("name", "").startswith("⚡") else "white")),
                              ("active", t["text"])],
                  darkcolor=[("selected", t["accent"]), ("active", t["border"])],
                  lightcolor=[("selected", t["accent"]), ("active", t["border"])],
                  bordercolor=[("selected", t["accent"]), ("active", t["border"])])

        # Global Tk option database for dropdown popup listboxes (Tkinter TCombobox popdown)
        try:
            self.option_add("*TCombobox*Listbox.background", t["entry_bg"])
            self.option_add("*TCombobox*Listbox.foreground", t["text"])
            self.option_add("*TCombobox*Listbox.selectBackground", t["accent"])
            self.option_add("*TCombobox*Listbox.selectForeground", "black" if is_bright else "white")
            self.option_add("*TCombobox*Listbox.font", FONT_SM)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  BRAND MANAGEMENT & TARGETING
    # ══════════════════════════════════════════════════════════════════════════
    def _refresh_brand_tree(self):
        self.brand_tree.delete(*self.brand_tree.get_children())
        brands = self.data_store.get_brands()
        for parent_name, data in brands.items():
            mode = self.brand_states.get(parent_name, "neutral")
            pid = self.brand_tree.insert("", "end", iid=parent_name, text=parent_name,
                                         values=("Parent", self._format_mode_label(mode)),
                                         tags=(mode,), open=False)

            # 1. Direct Parent Models (e.g. Camry, Corolla under Toyota; Outback under Subaru)
            for model in data.get("models", []):
                mod_key = f"{parent_name}/{model}"
                mod_mode = self.brand_states.get(mod_key, "neutral")
                self.brand_tree.insert(pid, "end", iid=mod_key, text=model,
                                       values=("Model", self._format_mode_label(mod_mode)),
                                       tags=(mod_mode,))

            # 2. Sub-brands (e.g. Lexus under Toyota; Chevrolet under GM)
            for sub_name, models in data.get("subs", {}).items():
                sub_key = f"{parent_name}/{sub_name}"
                sub_mode = self.brand_states.get(sub_key, "neutral")
                sid = self.brand_tree.insert(pid, "end", iid=sub_key, text=sub_name,
                                              values=("Sub", self._format_mode_label(sub_mode)),
                                              tags=(sub_mode,), open=False)
                for model in models:
                    mod_key = f"{sub_key}/{model}"
                    mod_mode = self.brand_states.get(mod_key, "neutral")
                    self.brand_tree.insert(sid, "end", iid=mod_key, text=model,
                                           values=("Model", self._format_mode_label(mod_mode)),
                                           tags=(mod_mode,))

        self._refresh_bulk_brand_list()
        self._refresh_preset_list()

    def _format_mode_label(self, mode):
        if mode == "target":
            return "🎯 Target"
        elif mode == "exclude":
            return "🚫 Exclude"
        return "⚪ Neutral"

    def _on_tree_double_click(self, event=None):
        """Cycle selected item(s) through: Neutral -> Target -> Exclude -> Neutral."""
        selected = self.brand_tree.selection()
        if not selected:
            return
        for item_id in selected:
            current = self.brand_states.get(item_id, "neutral")
            if current == "neutral":
                new_mode = "target"
            elif current == "target":
                new_mode = "exclude"
            else:
                new_mode = "neutral"
            self._apply_mode(item_id, new_mode)
        self._update_include_preview()

    def _set_selected_mode(self, mode):
        selected = self.brand_tree.selection()
        if not selected:
            messagebox.showinfo("Select", "Select one or more brands/models in the tree first.")
            return
        for item_id in selected:
            self._apply_mode(item_id, mode)
        self._update_include_preview()

    def _apply_mode(self, item_id, mode):
        self.brand_states[item_id] = mode
        item_type = self.brand_tree.item(item_id, "values")[0]
        self.brand_tree.item(item_id, values=(item_type, self._format_mode_label(mode)), tags=(mode,))
        # NOTE: Do NOT cascade to children automatically so parent can be targeted independently

    def _auto_exclude_other_brands(self):
        """Auto-exclude competitor parent brands only."""
        targeted_keys = {k for k, v in self.brand_states.items() if v == "target"}
        if not targeted_keys:
            sel = self.brand_tree.selection()
            if sel:
                for s in sel:
                    self._apply_mode(s, "target")
                targeted_keys = {k for k, v in self.brand_states.items() if v == "target"}

        if not targeted_keys:
            messagebox.showinfo("Target", "Mark or select at least one brand as 🎯 Target first.")
            return

        target_parents = {k.split("/")[0] for k in targeted_keys}
        brands = self.data_store.get_brands()
        excluded_count = 0
        for parent_name in brands.keys():
            if parent_name not in target_parents:
                self._apply_mode(parent_name, "exclude")
                excluded_count += 1

        self._update_include_preview()
        self._log(f"Auto-excluded {excluded_count} competitor brand(s) ({', '.join(target_parents)} targeted).")

    def _auto_exclude_other_models(self):
        """Auto-exclude sibling models/subs under the targeted brand that are not targeted."""
        targeted_keys = {k for k, v in self.brand_states.items() if v == "target"}
        if not targeted_keys:
            sel = self.brand_tree.selection()
            if sel:
                for s in sel:
                    self._apply_mode(s, "target")
                targeted_keys = {k for k, v in self.brand_states.items() if v == "target"}

        if not targeted_keys:
            messagebox.showinfo("Target", "Mark or select at least one model/brand as 🎯 Target first.")
            return

        target_parents = {k.split("/")[0] for k in targeted_keys}
        excluded_count = 0

        for parent_name in target_parents:
            for child_id in self.brand_tree.get_children(parent_name):
                sub_children = self.brand_tree.get_children(child_id)
                if sub_children:
                    # Sub-brand
                    if child_id not in targeted_keys:
                        has_target_sub = any(sc in targeted_keys for sc in sub_children)
                        if not has_target_sub:
                            self._apply_mode(child_id, "exclude")
                            excluded_count += 1
                        else:
                            for sc in sub_children:
                                if sc not in targeted_keys:
                                    self._apply_mode(sc, "exclude")
                                    excluded_count += 1
                else:
                    # Direct model
                    if child_id not in targeted_keys:
                        self._apply_mode(child_id, "exclude")
                        excluded_count += 1

        self._update_include_preview()
        self._log(f"Auto-excluded {excluded_count} sibling model(s) under target brand(s).")

    def _auto_exclude_all_others(self):
        """Auto-exclude BOTH competitor parent brands AND sibling non-target models."""
        self._auto_exclude_other_brands()
        self._auto_exclude_other_models()
        self._log("Auto-excluded all other competitor brands and sibling models.")

    def _reset_brand_modes(self):
        """Reset all brand targeting states to neutral."""
        self.brand_states.clear()
        self._refresh_brand_tree()
        self.include_text.delete("1.0", "end")
        self._log("Brand target states reset to Neutral.")

    def _on_tree_select(self, event=None):
        self._update_include_preview()

    def _update_include_preview(self):
        """Update the include terms text box strictly based on targeted items."""
        target_keys = [k for k, v in self.brand_states.items() if v == "target"]
        exclude_names = {k.split("/")[-1] for k, v in self.brand_states.items() if v == "exclude"}

        if not target_keys:
            sel = self.brand_tree.selection()
            if sel:
                item_name = self.brand_tree.item(sel[0], "text")
                self.include_text.delete("1.0", "end")
                self.include_text.insert("1.0", item_name)
            else:
                self.include_text.delete("1.0", "end")
            return

        all_terms = []
        for key in target_keys:
            parts = key.split("/")
            name = parts[-1]
            if name not in all_terms and name not in exclude_names:
                all_terms.append(name)

        self.include_text.delete("1.0", "end")
        self.include_text.insert("1.0", "\n".join(all_terms))

    def _add_parent_brand(self):
        def _on_add(name):
            self.data_store.add_parent_brand(name)
            self.brand_states[name] = "target"
            self._refresh_brand_tree()
            self.brand_tree.selection_set(name)
            self.brand_tree.focus(name)
            self._on_tree_select(None)
        self._brand_dialog("Add Parent Brand", _on_add)

    def _add_sub_brand(self):
        sel = self.brand_tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select a parent brand first.")
            return
        parent = sel.split("/")[0]
        def _on_add(name):
            self.data_store.add_sub_brand(parent, name)
            sub_key = f"{parent}/{name}"
            self.brand_states[sub_key] = "target"
            self._refresh_brand_tree()
            self.brand_tree.selection_set(sub_key)
            self.brand_tree.focus(sub_key)
            self._on_tree_select(None)
        self._brand_dialog("Add Sub-brand", _on_add)

    def _add_model(self):
        sel = self.brand_tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Select a parent brand or sub-brand first.")
            return
        parts = sel.split("/")
        if len(parts) == 1:
            parent_name = parts[0]
            self._brand_dialog(f"Add Model to {parent_name}", lambda name: (
                self.data_store.add_model(parent_name, "", name),
                self._refresh_brand_tree()
            ))
        elif len(parts) >= 2:
            parent_name, sub_name = parts[0], parts[1]
            self._brand_dialog(f"Add Model to {sub_name}", lambda name: (
                self.data_store.add_model(parent_name, sub_name, name),
                self._refresh_brand_tree()
            ))

    def _remove_brand(self):
        sel = self.brand_tree.focus()
        if not sel:
            return
        name = self.brand_tree.item(sel)["text"]
        if messagebox.askyesno("Confirm", f"Remove '{name}' and all children?"):
            self.data_store.remove_brand_item(name)
            self._refresh_brand_tree()

    def _brand_dialog(self, title, callback):
        t = self.theme
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=t["bg"])
        win.geometry("340x140")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self._apply_dark_titlebar(win)
        self._center_window(win, 340, 140)

        def _close():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _close)

        tk.Label(win, text="Name:", bg=t["bg"], fg=t["text"], font=FONT).pack(pady=(16, 4))
        entry = tk.Entry(win, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"],
                         relief="flat", font=FONT, width=28)
        entry.pack()
        entry.focus()
        def submit(ev=None):
            name = entry.get().strip()
            if name:
                callback(name)
                _close()
        entry.bind("<Return>", submit)
        tk.Button(win, text="Add", command=submit,
                  bg=t["accent"], fg="black" if t.get("name", "").startswith("⚡") else "white", relief="flat", font=FONT).pack(pady=8)

    def _on_brand_drag_start(self, event):
        item = self.brand_tree.identify_row(event.y)
        if item:
            self._drag_data = {
                "item": item,
                "y": event.y,
                "dragging": False
            }
        else:
            self._drag_data = None

    def _on_brand_drag_motion(self, event):
        if not self._drag_data:
            return
        if abs(event.y - self._drag_data["y"]) > 4:
            self._drag_data["dragging"] = True
            hover_item = self.brand_tree.identify_row(event.y)
            if hover_item and hover_item != self._drag_data["item"]:
                parent_drag = self.brand_tree.parent(self._drag_data["item"])
                parent_hover = self.brand_tree.parent(hover_item)
                if parent_drag == parent_hover:
                    self.brand_tree.config(cursor="fleur")
                    return
            self.brand_tree.config(cursor="arrow")

    def _on_brand_drag_release(self, event):
        self.brand_tree.config(cursor="arrow")
        if not self._drag_data or not self._drag_data.get("dragging"):
            self._drag_data = None
            return

        drag_item = self._drag_data["item"]
        target_item = self.brand_tree.identify_row(event.y)
        self._drag_data = None

        if not target_item or target_item == drag_item:
            return

        parent_drag = self.brand_tree.parent(drag_item)
        parent_target = self.brand_tree.parent(target_item)

        # Only allow reordering among siblings under the same parent
        if parent_drag == parent_target:
            target_idx = self.brand_tree.index(target_item)
            self.brand_tree.move(drag_item, parent_drag, target_idx)
            self._save_tree_order(parent_drag)
            item_name = self.brand_tree.item(drag_item, "text")
            self._log(f"↕ Reordered brand item: '{item_name}'")

    def _move_selected_brand(self, direction: int):
        """Move selected brand item up (-1) or down (+1) within its siblings."""
        sel = self.brand_tree.focus()
        if not sel:
            return "break"
        parent = self.brand_tree.parent(sel)
        children = list(self.brand_tree.get_children(parent))
        if sel not in children:
            return "break"
        idx = children.index(sel)
        new_idx = idx + direction
        if 0 <= new_idx < len(children):
            self.brand_tree.move(sel, parent, new_idx)
            self._save_tree_order(parent)
            self.brand_tree.see(sel)
            self.brand_tree.focus(sel)
            self.brand_tree.selection_set(sel)
            item_name = self.brand_tree.item(sel, "text")
            self._log(f"↕ Moved '{item_name}' {'up' if direction < 0 else 'down'}.")
        return "break"

    def _save_tree_order(self, parent_id: str):
        """Persist current Treeview order to DataStore."""
        if not parent_id:
            parents = [self.brand_tree.item(c, "text") for c in self.brand_tree.get_children("")]
            self.data_store.reorder_parent_brands(parents)
        else:
            parts = parent_id.split("/")
            if len(parts) == 1:
                parent_name = parts[0]
                models = []
                subs = []
                for c in self.brand_tree.get_children(parent_id):
                    item_type = self.brand_tree.item(c, "values")[0]
                    item_text = self.brand_tree.item(c, "text")
                    if item_type == "Sub":
                        subs.append(item_text)
                    else:
                        models.append(item_text)
                if models:
                    self.data_store.reorder_models(parent_name, "", models)
                if subs:
                    self.data_store.reorder_subs(parent_name, subs)
            elif len(parts) == 2:
                parent_name, sub_name = parts[0], parts[1]
                models = [self.brand_tree.item(c, "text") for c in self.brand_tree.get_children(parent_id)]
                self.data_store.reorder_models(parent_name, sub_name, models)

    # ══════════════════════════════════════════════════════════════════════════
    #  EXCLUSION MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    def _on_excl_mousewheel(self, e):
        """Scroll exclusions list on mousewheel from any inner widget."""
        self.excl_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _select_all_exclusions(self):
        for var in self.excl_vars.values():
            var.set(True)

    def _unselect_all_exclusions(self):
        for var in self.excl_vars.values():
            var.set(False)

    def _refresh_exclusion_list(self):
        t = self.theme
        for w in self.excl_inner.winfo_children():
            w.destroy()
        self.excl_vars = {}
        for term in self.data_store.get_exclusions():
            # Exclusions unselected by default as requested
            var = tk.BooleanVar(value=False)
            self.excl_vars[term] = var
            cb = tk.Checkbutton(self.excl_inner, text=term, variable=var,
                                bg=t["entry_bg"], fg=t["text"], selectcolor=t["panel"],
                                activebackground=t["entry_bg"], font=FONT_SM,
                                anchor="w")
            cb.bind("<MouseWheel>", self._on_excl_mousewheel)
            cb.pack(fill="x", anchor="w")

    def _add_exclusion(self):
        term = self.new_excl_entry.get().strip()
        placeholder = "New generic exclusion"
        if term and term != placeholder:
            if term.lower() in ("rick", "astley", "rickroll", "never gonna give you up", "never"):
                self._trigger_rickroll_easter_egg()
            self.data_store.add_exclusion(term)
            self.new_excl_entry.delete(0, "end")
            self._refresh_exclusion_list()

    def _remove_exclusion(self):
        checked = [t for t, v in self.excl_vars.items() if v.get()]
        if not checked:
            messagebox.showinfo("Remove", "Check terms to remove first.")
            return
        for t in checked:
            self.data_store.remove_exclusion(t)
        self._refresh_exclusion_list()

    def _get_active_exclusions(self):
        return [t for t, v in self.excl_vars.items() if v.get()]

    # ══════════════════════════════════════════════════════════════════════════
    #  PORTFOLIO PRESETS & 1-CLICK SWEEPER
    # ══════════════════════════════════════════════════════════════════════════
    def _refresh_preset_list(self):
        """Populate the portfolio preset combobox."""
        if not hasattr(self, "preset_combo"):
            return
        presets = self.data_store.get_presets()
        keys = list(presets.keys())
        self.preset_combo["values"] = keys
        if keys and (not self.preset_var.get() or self.preset_var.get() not in keys):
            self.preset_var.set(keys[0])

    def _on_preset_selected(self, event=None):
        """When user selects a preset, auto-target its brands and restore exclusions / custom terms."""
        preset_name = self.preset_var.get().strip()
        presets = self.data_store.get_presets()
        if preset_name not in presets:
            return

        payload = presets[preset_name]
        if isinstance(payload, dict):
            target_brands = payload.get("brands", [])
            generic_excludes = payload.get("generic_excludes", [])
            custom_inc = payload.get("custom_includes", [])
            cond = payload.get("condition", "all")
        else:
            target_brands = list(payload)
            generic_excludes = []
            custom_inc = []
            cond = "all"

        self.brand_states.clear()

        # Find and target matching parent brands, sub-brands, and models
        all_brands = self.data_store.get_brands()
        for parent_name, pdata in all_brands.items():
            if parent_name in target_brands:
                self._apply_mode(parent_name, "target")
            else:
                self._apply_mode(parent_name, "exclude")

            for sub_name in pdata.get("subs", {}).keys():
                sub_key = f"{parent_name}/{sub_name}"
                if sub_name in target_brands or sub_key in target_brands:
                    self._apply_mode(sub_key, "target")

            for model_name in pdata.get("models", []):
                mod_key = f"{parent_name}/{model_name}"
                if model_name in target_brands or mod_key in target_brands:
                    self._apply_mode(mod_key, "target")

        # Restore generic exclusions if saved in preset
        if generic_excludes and hasattr(self, "excl_vars"):
            for term, var in self.excl_vars.items():
                var.set(term in generic_excludes)

        # Restore custom includes if saved
        if custom_inc and hasattr(self, "include_text"):
            self.include_text.delete("1.0", "end")
            self.include_text.insert("1.0", "\n".join(custom_inc) + "\n")

        if hasattr(self, "condition_var") and cond:
            self.condition_var.set(cond)

        self._update_include_preview()
        self._log(f"📦 Loaded Preset '{preset_name}': {len(target_brands)} brands, {len(generic_excludes)} exclusions restored.")
        self._status(f"Loaded Preset: {preset_name}")

    def _auto_detect_brand_from_title(self, title: str) -> tuple:
        """
        Scan a listing title against all known Parent Brands, Sub-Brands, Models, and Product Types.
        Returns: (detected_brand, detected_product_type)
        """
        if not title:
            return "Unassigned", ""

        t_low = title.lower()
        brands_data = self.data_store.get_brands()

        for parent_name, data in brands_data.items():
            p_clean = parent_name.lower().strip()
            if len(p_clean) >= 2 and re.search(r'\b' + re.escape(p_clean) + r'\b', t_low):
                return parent_name, self._detect_product_type(title)

            for sub_name, models in data.get("subs", {}).items():
                s_clean = sub_name.lower().strip()
                if len(s_clean) >= 2 and re.search(r'\b' + re.escape(s_clean) + r'\b', t_low):
                    return parent_name, self._detect_product_type(title)
                for m in models:
                    m_clean = m.lower().strip()
                    if len(m_clean) >= 3 and re.search(r'\b' + re.escape(m_clean) + r'\b', t_low):
                        return parent_name, self._detect_product_type(title)

            for m in data.get("models", []):
                m_clean = m.lower().strip()
                if len(m_clean) >= 3 and re.search(r'\b' + re.escape(m_clean) + r'\b', t_low):
                    return parent_name, self._detect_product_type(title)

        return "Unassigned", self._detect_product_type(title)

    def _detect_product_type(self, title: str) -> str:
        """Categorize product type based on listing title keywords using active industry taxonomy."""
        t_low = title.lower()
        if hasattr(self, "data_store") and hasattr(self.data_store, "get_product_taxonomy"):
            tax = self.data_store.get_product_taxonomy()
        else:
            tax = None

        if tax:
            for ind_name, types_dict in tax.items():
                for pt_name, kws in types_dict.items():
                    for kw in kws:
                        kw_clean = kw.lower().strip()
                        if kw_clean and kw_clean in t_low:
                            return pt_name
        return ""

    def _save_custom_preset(self):
        """Save currently targeted brands, generic exclusions, and custom terms as a new custom portfolio preset."""
        target_keys = [k for k, v in self.brand_states.items() if v == "target"]
        if not target_keys:
            sel = self.brand_tree.selection()
            if sel:
                target_keys = list(sel)

        target_brands = []
        for k in target_keys:
            name = k.split("/")[-1]
            if name not in target_brands:
                target_brands.append(name)

        active_excls = self._get_active_exclusions()
        custom_inc = [l.strip() for l in self.include_text.get("1.0", "end").splitlines() if l.strip()]
        cond = self.condition_var.get() if hasattr(self, "condition_var") else "all"

        if not target_brands and not custom_inc:
            messagebox.showinfo("No Brands Selected", "Mark one or more brands as 🎯 Target in the library first before saving a preset.")
            return

        t = self.theme
        win = tk.Toplevel(self)
        win.title("Save / Update Portfolio Preset")
        win.configure(bg=t["bg"])
        win.geometry("460x240")
        win.resizable(False, False)
        
        self._apply_dark_titlebar(win)
        self._center_window(win, 460, 240)
        win.transient(self)
        try:
            win.grab_set()
        except Exception:
            pass

        tk.Label(win, text="💾 Save or Update Portfolio Preset", bg=t["bg"], fg=t["accent"],
                 font=("Segoe UI", 11, "bold")).pack(pady=(14, 4))

        tk.Label(win, text=f"Snapshot: {len(target_brands)} Brands • {len(active_excls)} Exclusions • {len(custom_inc)} Custom Keywords",
                 bg=t["bg"], fg=t["subtext"], font=FONT_SM).pack(pady=(0, 10))

        lbl_frame = tk.Frame(win, bg=t["bg"])
        lbl_frame.pack(fill="x", padx=24)
        tk.Label(lbl_frame, text="Preset Name (Select existing to Overwrite, or type new):",
                 bg=t["bg"], fg=t["text"], font=FONT_SM).pack(anchor="w")

        presets = self.data_store.get_presets()
        existing_names = list(presets.keys())
        name_var = tk.StringVar(value=self.preset_var.get() if self.preset_var.get() in existing_names else "")
        combo = ttk.Combobox(lbl_frame, textvariable=name_var, values=existing_names, font=FONT_SM)
        combo.pack(fill="x", pady=(4, 14))
        combo.focus()

        btn_row = tk.Frame(win, bg=t["bg"])
        btn_row.pack(fill="x", padx=24)

        def _close():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _close)

        def _do_save():
            chosen_name = name_var.get().strip()
            if not chosen_name:
                try: win.grab_release()
                except Exception: pass
                messagebox.showwarning("Name Required", "Please enter or select a preset name.", parent=win)
                try: win.grab_set()
                except Exception: pass
                return
            if chosen_name in presets:
                try: win.grab_release()
                except Exception: pass
                overwrite_ok = messagebox.askyesno("Overwrite Preset", f"Portfolio Preset '{chosen_name}' already exists.\n\nOverwrite and update with current workspace snapshot?", parent=win)
                if not overwrite_ok:
                    try: win.grab_set()
                    except Exception: pass
                    return

            preset_payload = {
                "brands": target_brands,
                "generic_excludes": active_excls,
                "custom_includes": custom_inc,
                "condition": cond
            }
            self.data_store.save_preset(chosen_name, preset_payload)
            self._refresh_preset_list()
            self.preset_var.set(chosen_name)
            self._log(f"💾 Saved Portfolio Preset '{chosen_name}' ({len(target_brands)} brands, {len(active_excls)} exclusions).")
            _close()
            self.after(50, lambda: messagebox.showinfo("Preset Saved", f"Successfully saved Portfolio Preset '{chosen_name}' with {len(target_brands)} brand(s) and {len(active_excls)} generic exclusion(s)!", parent=self))

        self._btn(btn_row, "💾 Save / Update Preset", _do_save, accent=True).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._btn(btn_row, "Cancel", _close).pack(side="right")
        win.bind("<Return>", lambda e: _do_save())

    def _delete_custom_preset(self):
        """Delete currently selected custom preset."""
        name = self.preset_var.get().strip()
        if not name:
            return
        if messagebox.askyesno("Delete Preset", f"Delete Portfolio Preset '{name}'?"):
            self.data_store.delete_preset(name)
            self._refresh_preset_list()

    def _queue_clean_targeted_brands(self):
        """Queue only the explicitly targeted brand/sub-brand names as clean, individual 1-term searches."""
        # 1. Parse stores (safely handling Global mode and placeholders)
        stores = self._get_stores_from_input() or self._get_global_token()

        # 2. Get explicitly targeted terms or custom ad-hoc terms
        target_keys = [k for k, v in self.brand_states.items() if v == "target"]
        if not target_keys:
            sel = self.brand_tree.selection()
            if sel:
                target_keys = list(sel)

        custom_includes = [l.strip() for l in self.include_text.get("1.0", "end").splitlines() if l.strip()]

        if not target_keys and not custom_includes:
            if stores and not any("global" in s.lower() for s in stores):
                custom_includes = [s for s in stores if not s.startswith("http")]
                if custom_includes:
                    stores = self._get_global_token()

            if not custom_includes:
                children = self.brand_tree.get_children()
                if children:
                    target_keys = [children[0]]
                else:
                    messagebox.showwarning("No Target Terms", "Mark at least one brand as 🎯 Target or type custom keywords in the Target box.")
                    return

        target_terms = []
        for k in target_keys:
            name = k.split("/")[-1]
            if name not in target_terms:
                target_terms.append(name)

        if not target_terms and custom_includes:
            target_terms = list(custom_includes)

        generic_excludes = self._get_active_exclusions()
        ds = getattr(self, "data_store", None)
        all_library_brands = ds.get_brands() if ds else {}
        platform_name = self._get_current_platform_name()
        ebay_loc = self.ebay_country_var.get() if hasattr(self, "ebay_country_var") else "United States"
        v_country = self.vinted_country_var.get() if hasattr(self, "vinted_country_var") else "All Locales"
        v_depth = self.vinted_depth_var.get() if hasattr(self, "vinted_depth_var") else "2 Pages"
        mm_country = self.manomano_country_var.get() if hasattr(self, "manomano_country_var") else "France"
        meli_c = self.meli_country_var.get() if hasattr(self, "meli_country_var") else "Mexico"
        meli_d = self.meli_depth_var.get() if hasattr(self, "meli_depth_var") else "2 Pages (100)"
        wish_d = self.wish_depth_var.get() if hasattr(self, "wish_depth_var") else "50 Items"
        rb_d = self.rb_depth_var.get() if hasattr(self, "rb_depth_var") else "2 Pages (100)"
        pv_d = self.pv_depth_var.get() if hasattr(self, "pv_depth_var") else "2 Pages (100)"
        ali_d = self.ali_depth_var.get() if hasattr(self, "ali_depth_var") else "3 Pages (180)"
        condition = self.condition_var.get() if hasattr(self, "condition_var") else "all"

        queued_count = 0
        for store in stores:
            for term in target_terms:
                if any(q.get("store", "").strip().lower() == store.strip().lower() and 
                       q.get("brand", "").strip().lower() == term.strip().lower() and 
                       q.get("marketplace", "eBay").lower() == platform_name.lower() and
                       q.get("vinted_country", "") == v_country and
                       q.get("meli_country", "") == meli_c and
                       q.get("ebay_locale", "") == ebay_loc
                       for q in self.queue):
                    continue

                # Exclude strictly user-defined generic exclusions
                job_excludes = list(generic_excludes)

                entry = {
                    "store": store,
                    "brand": term,
                    "marketplace": platform_name,
                    "ebay_locale": ebay_loc,
                    "vinted_country": v_country,
                    "vinted_depth": v_depth,
                    "manomano_locale": mm_country,
                    "meli_country": meli_c,
                    "meli_depth": meli_d,
                    "wish_depth": wish_d,
                    "rb_depth": rb_d,
                    "pv_depth": pv_d,
                    "ali_depth": ali_d,
                    "includes": [term],  # Clean, standalone single keyword!
                    "excludes": job_excludes,
                    "condition": condition
                }
                self.queue.append(entry)
                loc_tag = f" • {v_country.split()[0]}" if platform_name == "Vinted" else (f" • {meli_c.split()[0]}" if platform_name == "Mercado Libre" else (f" • {mm_country.split()[0]}" if platform_name == "ManoMano" else (f" • {ebay_loc.split()[0]}" if platform_name == "eBay" and "United States" not in ebay_loc else "")))
                label = f"{self._store_label(store, platform=platform_name)}{loc_tag} ▸ {term} [Clean 1-Term Sweep]"
                self.queue_list.insert("end", label)
                queued_count += 1

        store_names = [self._store_label(s, platform=platform_name) for s in stores]
        self._log(f"🎯 Queued {queued_count} Clean Individual Search(es) for [{', '.join(target_terms)}] across {len(stores)} target(s): {', '.join(store_names)} [{platform_name}]")
        self._status(f"🎯 Queued {queued_count} Clean Term Search(es) [{platform_name}]!")

    def _queue_portfolio_preset(self):
        """1-Click Portfolio Sweep: Automatically queue all preset brands across all entered stores."""
        preset_name = self.preset_var.get().strip()
        presets = self.data_store.get_presets()
        if preset_name not in presets:
            messagebox.showinfo("Select Preset", "Select a valid Portfolio Preset first.")
            return

        stores = self._get_stores_from_input() or self._get_global_token()

        preset_brands = presets[preset_name]
        if not preset_brands:
            messagebox.showinfo("Empty Preset", f"Preset '{preset_name}' has no brands configured.")
            return

        generic_excludes = self._get_active_exclusions()
        condition = self.condition_var.get()
        all_library_brands = self.data_store.get_brands()
        platform_name = self._get_current_platform_name()
        ebay_loc = self.ebay_country_var.get() if hasattr(self, "ebay_country_var") else "United States"
        v_country = self.vinted_country_var.get() if hasattr(self, "vinted_country_var") else "All Locales"
        v_depth = self.vinted_depth_var.get() if hasattr(self, "vinted_depth_var") else "2 Pages"
        mm_country = self.manomano_country_var.get() if hasattr(self, "manomano_country_var") else "France"
        meli_c = self.meli_country_var.get() if hasattr(self, "meli_country_var") else "Mexico"
        meli_d = self.meli_depth_var.get() if hasattr(self, "meli_depth_var") else "2 Pages (100)"
        wish_d = self.wish_depth_var.get() if hasattr(self, "wish_depth_var") else "50 Items"
        rb_d = self.rb_depth_var.get() if hasattr(self, "rb_depth_var") else "2 Pages (100)"
        pv_d = self.pv_depth_var.get() if hasattr(self, "pv_depth_var") else "2 Pages (100)"
        ali_d = self.ali_depth_var.get() if hasattr(self, "ali_depth_var") else "3 Pages (180)"

        queued_count = 0
        for store in stores:
            for parent_brand in preset_brands:
                if parent_brand not in all_library_brands:
                    continue
                if any(q.get("store", "").strip().lower() == store.strip().lower() and 
                       q.get("brand", "").strip().lower() == parent_brand.strip().lower() and 
                       q.get("marketplace", "eBay").lower() == platform_name.lower() and
                       q.get("vinted_country", "") == v_country and
                       q.get("meli_country", "") == meli_c and
                       q.get("ebay_locale", "") == ebay_loc
                       for q in self.queue):
                    continue
                pdata = all_library_brands[parent_brand]

                # Gather all include terms for this parent
                includes = [parent_brand]
                includes.extend(pdata.get("models", []))
                for sub, sub_models in pdata.get("subs", {}).items():
                    if sub not in includes:
                        includes.append(sub)
                    for sm in sub_models:
                        if sm not in includes:
                            includes.append(sm)

                # Exclude strictly user-defined generic exclusions
                job_excludes = list(generic_excludes)

                entry = {
                    "store": store,
                    "brand": parent_brand,
                    "marketplace": platform_name,
                    "ebay_locale": ebay_loc,
                    "vinted_country": v_country,
                    "vinted_depth": v_depth,
                    "manomano_locale": mm_country,
                    "meli_country": meli_c,
                    "meli_depth": meli_d,
                    "wish_depth": wish_d,
                    "rb_depth": rb_d,
                    "pv_depth": pv_d,
                    "ali_depth": ali_d,
                    "includes": includes,
                    "excludes": job_excludes,
                    "condition": condition
                }
                self.queue.append(entry)
                loc_tag = f" • {v_country.split()[0]}" if platform_name == "Vinted" else (f" • {meli_c.split()[0]}" if platform_name == "Mercado Libre" else (f" • {mm_country.split()[0]}" if platform_name == "ManoMano" else (f" • {ebay_loc.split()[0]}" if platform_name == "eBay" and "United States" not in ebay_loc else "")))
                label = f"{self._store_label(store, platform=platform_name)}{loc_tag} ▸ {parent_brand} ({len(includes)} terms | {len(job_excludes)} excl)"
                self.queue_list.insert("end", label)
                queued_count += 1

        store_names = [self._store_label(s, platform=platform_name) for s in stores]
        self._log(f"📦 [PORTFOLIO SWEEP] Queued {queued_count} batch job(s) for Preset '{preset_name}' across {len(stores)} target(s): {', '.join(store_names)} [{platform_name}]")
        self._status(f"📦 1-Click Sweep: Queued {queued_count} job(s) for {len(stores)} target(s) [{platform_name}]!")
        messagebox.showinfo("Portfolio Sweep Queued", f"Successfully queued {queued_count} search job(s) for '{preset_name}' across {len(stores)} target(s) on {platform_name}!\n\nClick '▶ Run' to start harvesting!")

    def _open_multi_sector_modal(self):
        """Open Multi-Sector Target Dispatcher modal dialog."""
        active_q = ""
        if hasattr(self, "include_text"):
            inc_txt = self.include_text.get("1.0", "end").strip()
            if inc_txt:
                active_q = inc_txt.splitlines()[0].strip()
        if not active_q and hasattr(self, "brand_tree"):
            sel = self.brand_tree.selection()
            if sel:
                active_q = sel[0].split("/")[-1]

        active_excl = ", ".join(self._get_active_exclusions()[:4]) if hasattr(self, "_get_active_exclusions") else ""
        active_cond = self.condition_var.get() if hasattr(self, "condition_var") else "all"

        MultiSectorModal(
            self,
            theme=self.theme,
            initial_query=active_q,
            initial_excludes=active_excl,
            initial_condition=active_cond,
            on_enqueue_callback=self._enqueue_multi_sector_jobs
        )

    def _enqueue_multi_sector_jobs(self, brand: str, excludes: list, condition: str, selected_platforms: list):
        """Enqueue individual, distinct search jobs for all selected platforms in multi-sector dispatcher."""
        if not brand or not selected_platforms:
            return

        queued_count = 0
        generic_excludes = set(self._get_active_exclusions()) if hasattr(self, "_get_active_exclusions") else set()
        all_excludes = list(generic_excludes.union(set(excludes)))

        for platform_name in selected_platforms:
            store_token = f"🌐 Global {platform_name} Search"
            job = {
                "store": store_token,
                "brand": brand,
                "includes": [brand],
                "excludes": all_excludes,
                "condition": condition,
                "marketplace": platform_name,
                "vinted_country": "All Locales",
                "vinted_depth": "2 Pages (192)",
                "manomano_country": "All European Locales"
            }
            self.queue.append(job)
            label = f"🌐 [{platform_name}] Global Sweep ▸ '{brand}' ({len(all_excludes)} excl)"
            self.queue_list.insert("end", label)
            queued_count += 1

        self._log(f"🌐 [MULTI-SECTOR DISPATCH] Successfully queued {queued_count} batch job(s) for '{brand}' across: {', '.join(selected_platforms)}")
        self._status(f"🌐 Multi-Sector Dispatch: Queued {queued_count} job(s) for '{brand}'!")
        messagebox.showinfo("Multi-Sector Jobs Queued", f"Successfully queued {queued_count} search job(s) for '{brand}' across {len(selected_platforms)} marketplaces!\n\nClick '▶ Run' to start harvesting!")

    # ══════════════════════════════════════════════════════════════════════════
    #  QUEUE & BATCH EXECUTION (MULTI-STORE + MULTI-BRAND)
    # ══════════════════════════════════════════════════════════════════════════
    def _add_to_queue(self):
        # 1. Parse all stores/sellers entered
        stores = self._get_stores_from_input() or self._get_global_token()

        for s in stores:
            if any(r in s.lower() for r in ("rick", "astley", "rickroll", "never gonna give you up")):
                self._trigger_rickroll_easter_egg()
                break

        is_full_store_sweep = self.store_full_sweep_var.get() if hasattr(self, "store_full_sweep_var") else False

        # 2. Identify Target Brands & Custom Include Terms
        target_items = [k for k, v in self.brand_states.items() if v == "target"]
        custom_includes = [l.strip() for l in self.include_text.get("1.0", "end").splitlines() if l.strip()]

        if not is_full_store_sweep:
            if not target_items and not custom_includes:
                sel = self.brand_tree.selection()
                if sel:
                    target_items = [sel[0]]
                elif stores and not any("global" in s.lower() for s in stores):
                    # User entered terms or seller in the Stores/Sellers box directly
                    term_candidates = []
                    store_candidates = []
                    for s in stores:
                        if "/" in s or "store" in s.lower() or "seller" in s.lower() or "shop" in s.lower() or s.startswith("http"):
                            store_candidates.append(s)
                        else:
                            term_candidates.append(s)

                    if term_candidates and not store_candidates:
                        custom_includes = term_candidates
                        top_targets = [t.title() for t in term_candidates]
                        stores = self._get_global_token()
                    elif store_candidates:
                        is_full_store_sweep = True
                        stores = store_candidates
                    else:
                        is_full_store_sweep = True
                else:
                    children = self.brand_tree.get_children()
                    if children:
                        target_items = [children[0]]
                    else:
                        messagebox.showwarning("Missing Targets", "Mark at least one brand as 🎯 Target, type custom keywords in the Target box, or check '🏪 Full Store Sweep' to sweep whole stores without keywords.")
                        return

        # 3. Identify Excluded Brands from Brand Library
        brand_excludes = []
        for k, v in self.brand_states.items():
            if v == "exclude":
                name = k.split("/")[-1]
                if name not in brand_excludes:
                    brand_excludes.append(name)

        # 4. Collect generic exclusions
        generic_excludes = self._get_active_exclusions()
        condition = self.condition_var.get()

        # Deduplicate top target parents
        top_targets = []
        for k in target_items:
            parts = k.split("/")
            top_parent = parts[0]
            if top_parent not in top_targets:
                top_targets.append(top_parent)

        if not top_targets and custom_includes:
            top_targets = [custom_includes[0].title() if len(custom_includes) == 1 else "Custom Search"]

        platform_name = self._get_current_platform_name()
        ebay_loc = self.ebay_country_var.get() if hasattr(self, "ebay_country_var") else "United States"
        v_country = self.vinted_country_var.get() if hasattr(self, "vinted_country_var") else "All Locales"
        v_depth = self.vinted_depth_var.get() if hasattr(self, "vinted_depth_var") else "2 Pages"
        mm_country = self.manomano_country_var.get() if hasattr(self, "manomano_country_var") else "France"
        meli_c = self.meli_country_var.get() if hasattr(self, "meli_country_var") else "Mexico"
        meli_d = self.meli_depth_var.get() if hasattr(self, "meli_depth_var") else "2 Pages (100)"
        wish_d = self.wish_depth_var.get() if hasattr(self, "wish_depth_var") else "50 Items"
        rb_d = self.rb_depth_var.get() if hasattr(self, "rb_depth_var") else "2 Pages (100)"
        pv_d = self.pv_depth_var.get() if hasattr(self, "pv_depth_var") else "2 Pages (100)"
        ali_d = self.ali_depth_var.get() if hasattr(self, "ali_depth_var") else "3 Pages (180)"

        queued_count = 0
        is_full_store_sweep = self.store_full_sweep_var.get() if hasattr(self, "store_full_sweep_var") else False

        if is_full_store_sweep and stores:
            for store in stores:
                b_name = top_targets[0] if top_targets else "Full Store Sweep"
                job_excludes = list(generic_excludes)
                entry = {
                    "store": store,
                    "brand": b_name,
                    "marketplace": platform_name,
                    "ebay_locale": ebay_loc,
                    "vinted_country": v_country,
                    "vinted_depth": v_depth,
                    "manomano_locale": mm_country,
                    "meli_country": meli_c,
                    "meli_depth": meli_d,
                    "wish_depth": wish_d,
                    "rb_depth": rb_d,
                    "pv_depth": pv_d,
                    "ali_depth": ali_d,
                    "includes": ["*"],
                    "excludes": job_excludes,
                    "condition": condition
                }
                self.queue.append(entry)
                loc_tag = f" • {v_country.split()[0]}" if platform_name == "Vinted" else (f" • {meli_c.split()[0]}" if platform_name == "Mercado Libre" else (f" • {mm_country.split()[0]}" if platform_name == "ManoMano" else (f" • {ebay_loc.split()[0]}" if platform_name == "eBay" and "United States" not in ebay_loc else "")))
                label = f"{self._store_label(store, platform=platform_name)}{loc_tag} ▸ 🏪 FULL INVENTORY ({len(job_excludes)} excl)"
                self.queue_list.insert("end", label)
                queued_count += 1
        else:
            for store in stores:
                for parent_brand in top_targets:
                    if any(q.get("store", "").strip().lower() == store.strip().lower() and 
                           q.get("brand", "").strip().lower() == parent_brand.strip().lower() and 
                           q.get("marketplace", "eBay").lower() == platform_name.lower() and
                           q.get("vinted_country", "") == v_country and
                           q.get("manomano_locale", "") == mm_country and
                           q.get("meli_country", "") == meli_c and
                           q.get("ebay_locale", "") == ebay_loc
                           for q in self.queue):
                        continue

                    # Gather explicit target terms for this parent
                    brand_target_terms = []
                    for k in target_items:
                        if k.split("/")[0] == parent_brand:
                            term_name = k.split("/")[-1]
                            if term_name not in brand_target_terms and term_name not in brand_excludes:
                                brand_target_terms.append(term_name)

                    includes = brand_target_terms if brand_target_terms else custom_includes
                    if not includes:
                        includes = [parent_brand]

                    # Build exclusion list: strictly user-selected library excludes + generic excludes
                    job_excludes = list(generic_excludes) + list(brand_excludes)

                    entry = {
                        "store": store,
                        "brand": parent_brand,
                        "marketplace": platform_name,
                        "ebay_locale": ebay_loc,
                        "vinted_country": v_country,
                        "vinted_depth": v_depth,
                        "manomano_locale": mm_country,
                        "meli_country": meli_c,
                        "meli_depth": meli_d,
                        "wish_depth": wish_d,
                        "rb_depth": rb_d,
                        "pv_depth": pv_d,
                        "ali_depth": ali_d,
                        "includes": includes,
                        "excludes": job_excludes,
                        "condition": condition
                    }
                    self.queue.append(entry)
                    loc_tag = f" • {v_country.split()[0]}" if platform_name == "Vinted" else (f" • {meli_c.split()[0]}" if platform_name == "Mercado Libre" else (f" • {mm_country.split()[0]}" if platform_name == "ManoMano" else (f" • {ebay_loc.split()[0]}" if platform_name == "eBay" and "United States" not in ebay_loc else "")))
                    label = f"{self._store_label(store, platform=platform_name)}{loc_tag} ▸ {parent_brand} ({len(includes)} terms | {len(job_excludes)} excl)"
                    self.queue_list.insert("end", label)
                    queued_count += 1

        store_names = [self._store_label(s, platform=platform_name) for s in stores]
        self._log(f"🎯 Queued {queued_count} job(s) for [{', '.join(top_targets)}] across {len(stores)} target(s): {', '.join(store_names)} [{platform_name}]")

    def _store_label(self, url, platform=None):
        plat = platform or self._get_current_platform_name()

        if not url:
            return f"[{plat}] Full Search"
        low = url.lower().strip()
        if any(g == low or g in low for g in ("global", "global search", "marketplace", "all", "catalog", "wholesale", "search", "all products")):
            return f"[{plat}] Full Search"
        parts = url.rstrip("/").split("/")
        s_name = parts[-1] if parts else url
        return f"[{plat}] {s_name}"

    def _check_strict_exclusions(self, title: str, excludes: list) -> tuple:
        """Verify listing title does not contain any excluded keyword with word-boundary accuracy."""
        if not title or not excludes:
            return True, ""
        t_lower = title.lower()
        for ex in excludes:
            ex_clean = str(ex).strip().strip('"').lower()
            if not ex_clean or len(ex_clean) < 2:
                continue
            pattern = r'(?:\b|_)' + re.escape(ex_clean) + r'(?:\b|_)'
            if re.search(pattern, t_lower):
                return False, ex_clean
        return True, ""

    def _deduplicate_queue(self):
        """Remove duplicate or already-executed jobs from the pending queue with marketplace isolation."""
        if not self.queue:
            messagebox.showinfo("Queue Empty", "Search queue is currently empty.")
            return

        initial_len = len(self.queue)
        seen_keys = set()
        clean_queue = []

        # Collect executed keys from this session with marketplace isolation
        executed_keys = {
            (
                ex.get("marketplace", "eBay").strip().lower(),
                ex.get("store", "").strip().lower(),
                ex.get("brand", "").strip().lower()
            ) for ex in self.executed_jobs
        }

        purged_already_run = 0
        purged_duplicates = 0

        for job in self.queue:
            plat = job.get("marketplace", "eBay")
            k = (
                plat.strip().lower(),
                job.get("store", "").strip().lower(),
                job.get("brand", "").strip().lower()
            )
            if k in executed_keys:
                purged_already_run += 1
                continue
            if k in seen_keys:
                purged_duplicates += 1
                continue
            seen_keys.add(k)
            clean_queue.append(job)

        self.queue = clean_queue
        self.queue_list.delete(0, "end")
        for job in self.queue:
            plat = job.get("marketplace", "eBay")
            s_lbl = self._store_label(job.get("store", ""), platform=plat)
            b_name = job.get("brand", "")
            inc_len = len(job.get("includes", []))
            exc_len = len(job.get("excludes", []))
            lbl = f"{s_lbl} ▸ {b_name} ({inc_len} terms | {exc_len} excl)"
            self.queue_list.insert("end", lbl)

        total_purged = initial_len - len(self.queue)
        self._log(f"🧹 Queue Deduplicated: Purged {total_purged} job(s) ({purged_already_run} already executed on same platform, {purged_duplicates} duplicate). {len(self.queue)} job(s) remain.")
        self._show_themed_info("Queue Cleaned", f"Queue Deduplication Complete!\n\n• Already Executed Jobs Purged: {purged_already_run}\n• Duplicate Jobs Purged: {purged_duplicates}\n• Remaining Active Jobs: {len(self.queue)}", icon="🧹")

    def _pop_queue_ui_item(self):
        """Remove the top completed job from the UI queue listbox."""
        if hasattr(self, "queue_list") and self.queue_list.size() > 0:
            self.queue_list.delete(0)

    def _remove_selected_from_queue(self):
        """Remove currently selected items from queue list."""
        if self.running:
            messagebox.showwarning("Busy", "Cannot modify queue while a scan is running.")
            return
        selected = list(self.queue_list.curselection())
        if not selected:
            messagebox.showinfo("Select", "Select a queued job to remove.")
            return
        for idx in reversed(selected):
            if idx < len(self.queue):
                del self.queue[idx]
            self.queue_list.delete(idx)
        self._log("Removed selected job(s) from queue.")

    def _clear_queue(self):
        if self.running:
            messagebox.showwarning("Busy", "Stop the current scan before clearing the queue.")
            return
        self.queue.clear()
        self.queue_list.delete(0, "end")
        self._log("Queue cleared.")

    def _run_queue(self):
        if not self.queue:
            messagebox.showinfo("Queue", "Queue is empty. Add stores & brands to Queue first.")
            return
        if self.running:
            if self.paused:
                self._toggle_pause()
            return

        self.running = True
        self.paused = False
        self.stop_event.clear()
        self.pause_event.set()

        t = self.theme
        self.run_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="⏸  Pause", bg=t["btn_normal_bg"])
        self.stop_btn.config(state="normal")
        if hasattr(self, "dedup_q_btn"):
            self.dedup_q_btn.config(state="disabled")
        self.del_q_btn.config(state="disabled")
        self.clear_q_btn.config(state="disabled")

        is_headless = self.headless_var.get()
        default_mkt = self.marketplace_var.get() if hasattr(self, "marketplace_var") else "eBay"
        meli_c = self.meli_country_var.get() if hasattr(self, "meli_country_var") else "Mexico"
        meli_d = self.meli_depth_var.get() if hasattr(self, "meli_depth_var") else "2 Pages (100)"
        vinted_c = self.vinted_country_var.get() if hasattr(self, "vinted_country_var") else "United Kingdom"
        vinted_d = self.vinted_depth_var.get() if hasattr(self, "vinted_depth_var") else "2 Pages (192)"
        ali_d = self.ali_depth_var.get() if hasattr(self, "ali_depth_var") else "3 Pages (180)"

        self.progress.start()
        thread = threading.Thread(
            target=self._process_queue,
            args=(is_headless, default_mkt, meli_c, meli_d, vinted_c, vinted_d, ali_d),
            daemon=True
        )
        thread.start()

    def _toggle_pause(self):
        t = self.theme
        if not self.running:
            return
        if self.paused:
            self.paused = False
            self.pause_event.set()
            self.pause_btn.config(text="⏸  Pause", bg=t["btn_normal_bg"])
            self._status("Resumed search...")
            self._log("▶ Search resumed.")
            self.progress.start()
        else:
            self.paused = True
            self.pause_event.clear()
            self.pause_btn.config(text="▶  Resume", bg=t["accent"])
            self._status("Paused. Click 'Resume' to continue.")
            self._log("⏸ Search paused by user.")
            self.progress.stop()

    def _stop_scan(self):
        self._log("⏹ Stop requested: Halting current operation...")
        self._status("Halting operation...")
        self.stop_event.set()
        self.pause_event.set()
        self.stop_btn.config(state="disabled")
        if hasattr(self, "progress"):
            try:
                self.progress.stop()
            except Exception:
                pass

    def _process_queue(self, is_headless=True, default_mkt="eBay", meli_c="Mexico", meli_d="2 Pages (100)", vinted_c="United Kingdom", vinted_d="2 Pages (192)", ali_d="3 Pages (180)"):
        # Ensure scrapers honor current headless background mode
        self.scraper.headless = is_headless
        self.aliexpress_scraper.headless = is_headless
        self.wish_scraper.headless = is_headless
        self.temu_scraper.headless = is_headless
        self.mercadolibre_scraper.headless = is_headless
        self.redbubble_scraper.headless = is_headless
        self.printerval_scraper.headless = is_headless
        self.vinted_scraper.headless = is_headless
        self.manomano_scraper.headless = is_headless
        self.teepublic_scraper.headless = is_headless
        self.etsy_scraper.headless = is_headless
        self.spreadshirt_scraper.headless = is_headless
        self.zazzle_scraper.headless = is_headless
        self.cafepress_scraper.headless = is_headless
        self.threadless_scraper.headless = is_headless
        self.teespring_scraper.headless = is_headless
        self.fineartamerica_scraper.headless = is_headless

        total_new_items = 0
        total_initial_jobs = len(self.queue)
        job_idx = 0
        while self.queue and not self.stop_event.is_set():
            job = self.queue[0]
            job_idx += 1

            store_raw = job["store"]
            job_mkt = job.get("marketplace") or default_mkt
            platform_name = job_mkt
            
            p_low = platform_name.lower()
            s_low = store_raw.lower()
            
            is_manomano = "manomano" in p_low or "manomano." in s_low
            is_scribd = "scribd" in p_low or "scribd.com" in s_low
            is_tiktok = "tiktok" in p_low or "tiktok.com" in s_low
            is_vinted = "vinted" in p_low or "vinted." in s_low
            is_wish = "wish" in p_low or "wish.com" in s_low
            is_temu = "temu" in p_low or "temu.com" in s_low
            is_aliexpress = "aliexpress" in p_low or "aliexpress.com" in s_low or "ali" in p_low
            is_meli = "mercado" in p_low or "mercadolibre" in p_low or "mercadolivre" in p_low or "mercadolibre" in s_low or "mercadolivre" in s_low or "meli" in p_low
            is_redbubble = "redbubble" in p_low or "redbubble.com" in s_low
            is_printerval = "printerval" in p_low or "printerval.com" in s_low
            is_teepublic = "teepublic" in p_low or "teepublic.com" in s_low or "tee.pub" in s_low
            is_etsy = "etsy" in p_low or "etsy.com" in s_low
            is_spreadshirt = "spreadshirt" in p_low or "spreadshirt.com" in s_low or "spreadshop.com" in s_low
            is_zazzle = "zazzle" in p_low or "zazzle.com" in s_low
            is_cafepress = "cafepress" in p_low or "cafepress.com" in s_low
            is_threadless = "threadless" in p_low or "threadless.com" in s_low
            is_teespring = "teespring" in p_low or "spring.com" in s_low or "creator-spring.com" in s_low
            is_faa = "fineartamerica" in p_low or "pixels.com" in s_low or "fine art america" in p_low

            mkt_map = {
                "ManoMano": "manomano.fr", "Scribd": "scribd.com", "TikTok Shop": "shop.tiktok.com", "Vinted": "vinted.co.uk", "Wish": "wish.com", "Temu": "temu.com",
                "AliExpress": "aliexpress.com", "Mercado Libre": "mercadolibre.com",
                "Redbubble": "redbubble.com", "Printerval": "printerval.com", "TeePublic": "teepublic.com", "Etsy": "etsy.com", "Spreadshirt": "spreadshirt.com",
                "Zazzle": "zazzle.com", "CafePress": "cafepress.com", "Threadless": "threadless.com", "TeeSpring": "teespring.com", "Fine Art America": "fineartamerica.com",
                "eBay": "ebay.com"
            }
            mkt_tag = mkt_map.get(platform_name, "ebay.com")

            seller_label = self._store_label(store_raw, platform=platform_name)
            total_active_jobs = (job_idx - 1) + len(self.queue)
            remaining_in_queue = len(self.queue) - 1
            self._status(f"Processing Job {job_idx}/{total_active_jobs} ({remaining_in_queue} queued) [{platform_name}]: {job['brand']} in {seller_label}")
            self._log(f"[Job {job_idx}/{total_active_jobs}] 🛒 [{platform_name}] Target: '{job['brand']}' in {seller_label} (Condition: {job.get('condition', 'all')})")
            job_record = {
                "brand": job["brand"],
                "store": store_raw,
                "marketplace": platform_name,
                "condition": job.get("condition", "all"),
                "includes": list(job["includes"]),
                "excludes": list(job["excludes"]),
                "term_counts": {},
                "total_harvested": 0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            try:
                if is_manomano:
                    m_info = self.manomano_scraper.resolve_store_info(store_raw)
                    resolved = m_info.get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"🛠 [ManoMano] Target resolved: '{resolved}'")
                elif is_scribd:
                    resolved = self.scribd_scraper.resolve_store_info(store_raw).get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"📚 [Scribd] Target resolved: '{resolved}'")
                elif is_tiktok:
                    t_info = self.tiktok_scraper.resolve_store_info(store_raw)
                    resolved = t_info.get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"🎵 [TikTok Shop] Target resolved: '{resolved}'")
                elif is_vinted:
                    v_info = self.vinted_scraper.resolve_target_info(store_raw)
                    resolved = v_info.get("seller_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"👗 [Vinted] Target resolved: '{resolved}' ({v_info['domain']})")
                elif is_wish:
                    resolved = self.wish_scraper.resolve_store_info(store_raw).get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"🌠 [Wish] Target store resolved: '{resolved}'")
                elif is_temu:
                    resolved = self.temu_scraper.resolve_store_info(store_raw).get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"🟠 [Temu] Target store resolved: '{resolved}'")
                elif is_aliexpress:
                    resolved = self.aliexpress_scraper.resolve_store_info(store_raw).get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"🌐 [AliExpress] Target store resolved: '{resolved}'")
                elif is_meli:
                    resolved = "Mercado Libre (Latin America)"
                    job_record["resolved_seller"] = resolved
                    self._log(f"🇲🇽 [Mercado Libre] Target store resolved: '{resolved}'")
                elif is_redbubble:
                    resolved = self.redbubble_scraper.resolve_store_info(store_raw).get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"🎨 [Redbubble] Target store resolved: '{resolved}'")
                elif is_printerval:
                    resolved = self.printerval_scraper.resolve_store_info(store_raw).get("store_name", seller_label)
                    job_record["resolved_seller"] = resolved
                    self._log(f"👕 [Printerval] Target store resolved: '{resolved}'")
                elif is_teepublic:
                    resolved = "TeePublic Artist Community" if any(k in store_raw.lower() for k in ("global", "search", "all")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"👕 [TeePublic] Target store resolved: '{resolved}'")
                elif is_etsy:
                    resolved = "Etsy Commercial Makers" if any(k in store_raw.lower() for k in ("global", "search", "all")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"🧶 [Etsy] Target store resolved: '{resolved}'")
                elif is_spreadshirt:
                    resolved = "Spreadshirt Creator Community" if any(k in store_raw.lower() for k in ("global", "search", "all", "community", "spreadshop")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"🌿 [Spreadshirt] Target store resolved: '{resolved}'")
                elif is_zazzle:
                    resolved = "Zazzle Creator Community" if any(k in store_raw.lower() for k in ("global", "search", "all", "community", "store")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"🎨 [Zazzle] Target store resolved: '{resolved}'")
                elif is_cafepress:
                    resolved = "CafePress Designer Community" if any(k in store_raw.lower() for k in ("global", "search", "all", "community", "profile", "shop")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"☕ [CafePress] Target store resolved: '{resolved}'")
                elif is_threadless:
                    resolved = "Threadless Artist Community" if any(k in store_raw.lower() for k in ("global", "search", "all", "community", "shop")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"🧵 [Threadless] Target store resolved: '{resolved}'")
                elif is_teespring:
                    resolved = "Spring Creator Community" if any(k in store_raw.lower() for k in ("global", "search", "all", "community", "store")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"🌱 [TeeSpring] Target store resolved: '{resolved}'")
                elif is_faa:
                    resolved = "Fine Art America Artist Community" if any(k in store_raw.lower() for k in ("global", "search", "all", "community", "profile", "artist")) or not store_raw else store_raw
                    job_record["resolved_seller"] = resolved
                    self._log(f"🖼 [Fine Art America] Target store resolved: '{resolved}'")
                else:
                    resolved = self.scraper.resolve_seller(store_raw)
                    job_record["resolved_seller"] = resolved
                    self._log(f"🛒 [eBay] Target store resolved: '{resolved}'")
                
                for include_term in job["includes"]:
                    if self.stop_event.is_set():
                        break
                    self.pause_event.wait()

                    actual_term = "" if include_term == "*" else include_term
                    term_display = "🏪 Full Store Inventory" if include_term == "*" else f"'{include_term}'"
                    self._status(f"Harvesting [{platform_name}]: {job['brand']} → {term_display} in {seller_label}...")
                    self._log(f"Searching [{platform_name}]: {term_display} in {seller_label} (Condition: {job.get('condition','all')})")
                    
                    if is_wish:
                        wish_items_target = 50
                        wish_depth_raw = job.get("wish_depth") or (self.wish_depth_var.get() if hasattr(self, "wish_depth_var") else "50")
                        try:
                            m = re.search(r'(\d+)', wish_depth_raw)
                            if m: wish_items_target = int(m.group(1))
                        except Exception:
                            pass
                        self.wish_scraper.max_items = wish_items_target
                        target_url = self.wish_scraper._build_search_url(
                            self.wish_scraper.resolve_store_info(store_raw),
                            actual_term
                        )
                        self._log(f"  🔗 URL: {target_url} (Target Depth: {wish_items_target} items)")
                        job_record["url"] = target_url
                        items = self.wish_scraper.search(
                            store_raw,
                            actual_term,
                            job["excludes"],
                            condition=job.get("condition", "all"),
                            stop_event=self.stop_event,
                            pause_event=self.pause_event,
                            max_items=wish_items_target
                        )
                    elif is_temu:
                        target_url = self.temu_scraper._build_search_url(
                            self.temu_scraper.resolve_store_info(store_raw),
                            actual_term
                        )
                        self._log(f"  🔗 URL: {target_url}")
                        job_record["url"] = target_url
                        items = self.temu_scraper.search(
                            store_raw,
                            actual_term,
                            job["excludes"],
                            condition=job.get("condition", "all"),
                            stop_event=self.stop_event,
                            pause_event=self.pause_event
                        )
                    elif is_aliexpress:
                        ali_depth_str = job.get("ali_depth", ali_d)
                        m_ali_pages = re.search(r'(\d+)\s+Page', ali_depth_str, re.IGNORECASE)
                        ali_pages = int(m_ali_pages.group(1)) if m_ali_pages else 3
                        target_url = self.aliexpress_scraper._build_search_url(
                            self.aliexpress_scraper.resolve_store_info(store_raw),
                            actual_term
                        )
                        self._log(f"  🔗 URL: {target_url} (Depth: {ali_pages} page(s))")
                        job_record["url"] = target_url
                        items = self.aliexpress_scraper.search(
                            store_raw,
                            actual_term,
                            job["excludes"],
                            condition=job.get("condition", "all"),
                            stop_event=self.stop_event,
                            pause_event=self.pause_event,
                            max_pages=ali_pages
                        )
                    elif is_meli:
                        self.mercadolibre_scraper.headless = is_headless
                        selected_c = job.get("meli_country", meli_c)
                        depth_str = job.get("meli_depth", meli_d)
                        m_pages_match = re.search(r'(\d+)\s+Page', depth_str, re.IGNORECASE)
                        m_pages = int(m_pages_match.group(1)) if m_pages_match else 2
                        target_max_items = m_pages * 50

                        if "All Latin America" in selected_c:
                            self._log(f"🌎 [Latin America Multi-Sweep] Initiating cross-border sweep across Mexico, Brazil, Argentina, Colombia, Chile, and Peru for {term_display} ({m_pages} page(s)/region)...")
                            items = self.mercadolibre_scraper.search_multi_region(
                                actual_term,
                                site_codes=["MLM", "MLB", "MLA", "MCO", "MLC", "MPE"],
                                max_items_per_region=m_pages * 50,
                                max_pages=m_pages,
                                condition=job.get("condition", "all"),
                                stop_event=self.stop_event,
                                pause_event=self.pause_event,
                                log_callback=self._log
                            )
                            job_record["url"] = f"https://www.mercadolibre.com/multi-search?q={actual_term.replace(' ', '+')}"
                        else:
                            code_map = {
                                "Mexico": "MLM", "Brazil": "MLB", "Argentina": "MLA",
                                "Colombia": "MCO", "Chile": "MLC", "Peru": "MPE", "Uruguay": "MLU"
                            }
                            target_code = "MLM"
                            for k, c in code_map.items():
                                if k in selected_c:
                                    target_code = c
                                    break
                            self.mercadolibre_scraper.site_code = target_code
                            items = self.mercadolibre_scraper.search(
                                actual_term,
                                max_items=target_max_items,
                                max_pages=m_pages,
                                condition=job.get("condition", "all"),
                                stop_event=self.stop_event,
                                pause_event=self.pause_event,
                                log_callback=self._log
                            )
                            from mercadolibre_scraper import REGIONAL_DOMAINS
                            reg_domain = REGIONAL_DOMAINS.get(target_code, {}).get("domain", "listado.mercadolibre.com.mx")
                            job_record["url"] = f"https://{reg_domain}/{actual_term.replace(' ', '-')}"
                    elif is_redbubble:
                        self.redbubble_scraper.headless = is_headless
                        rb_max = 100
                        rb_depth_raw = job.get("rb_depth") or (self.rb_depth_var.get() if hasattr(self, "rb_depth_var") else "100")
                        m = re.search(r'\((\d+)\)', rb_depth_raw) or re.search(r'(\d+)', rb_depth_raw)
                        if m:
                            try: rb_max = int(m.group(1))
                            except ValueError: rb_max = 100
                        items = self.redbubble_scraper.search(
                            actual_term,
                            max_items=rb_max,
                            condition=job.get("condition", "all"),
                            log_callback=self._log
                        )
                        job_record["url"] = f"https://www.redbubble.com/shop/?query={actual_term.replace(' ', '+')}"
                    elif is_printerval:
                        self.printerval_scraper.headless = is_headless
                        pv_max = 100
                        pv_depth_raw = job.get("pv_depth") or (self.pv_depth_var.get() if hasattr(self, "pv_depth_var") else "100")
                        m = re.search(r'\((\d+)\)', pv_depth_raw) or re.search(r'(\d+)', pv_depth_raw)
                        if m:
                            try: pv_max = int(m.group(1))
                            except ValueError: pv_max = 100
                        items = self.printerval_scraper.search(
                            actual_term,
                            max_items=pv_max,
                            condition=job.get("condition", "all"),
                            log_callback=self._log
                        )
                        job_record["url"] = f"https://printerval.com/search?q={actual_term.replace(' ', '+')}"
                    elif is_vinted:
                        self.vinted_scraper.headless = is_headless
                        target_terms = [actual_term] if actual_term else ([job["brand"]] if job.get("brand") else [])
                        job_v_depth = job.get("vinted_depth") or vinted_d
                        job_v_country = job.get("vinted_country") or vinted_c
                        m_pages_match = re.search(r'(\d+)\s+Page', job_v_depth, re.IGNORECASE)
                        v_pages = int(m_pages_match.group(1)) if m_pages_match else 2

                        if "All Locales" in job_v_country or "All" in job_v_country:
                            self._log(f"🌍 [Vinted Multi-Region Sweep] Initiating cross-border sweep across UK, France, Germany, Spain, Italy, Poland, USA, Netherlands, and Belgium for {term_display} ({v_pages} pages/region)...")
                            items = self.vinted_scraper.search_multi_region(
                                store_raw,
                                brand_terms=target_terms,
                                exclusions=job["excludes"],
                                regions=["UK", "FR", "DE", "ES", "IT", "PL", "US", "NL", "BE"],
                                max_pages_per_region=v_pages,
                                stop_event=self.stop_event,
                                log_callback=self._log,
                                status_callback=self._status
                            )
                            job_record["url"] = f"https://www.vinted.co.uk/catalog?search_text={actual_term.replace(' ', '+')}"
                        else:
                            v_region = "UK"
                            region_names = {
                                "UK": ["UK", "United Kingdom"], "FR": ["France", "FR"], "DE": ["Germany", "DE"],
                                "ES": ["Spain", "ES"], "IT": ["Italy", "IT"], "PL": ["Poland", "PL"],
                                "US": ["United States", "US"], "NL": ["Netherlands", "NL"], "BE": ["Belgium", "BE"]
                            }
                            for code, names in region_names.items():
                                if any(n in job_v_country for n in names):
                                    v_region = code
                                    break
                            items = self.vinted_scraper.scrape_store(
                                store_raw,
                                brand_terms=target_terms,
                                exclusions=job["excludes"],
                                max_pages=v_pages,
                                stop_event=self.stop_event,
                                log_callback=self._log,
                                status_callback=self._status,
                                region_code=v_region
                            )
                            dom_tag = self.vinted_scraper.get_active_domain()
                            job_record["url"] = f"https://www.{dom_tag}/catalog?search_text={actual_term.replace(' ', '+')}"
                    elif is_manomano:
                        loc_selection = job.get("manomano_locale") or (self.manomano_country_var.get() if hasattr(self, "manomano_country_var") else "France")
                        if "all" in str(loc_selection).lower() or "europe" in str(loc_selection).lower():
                            clean_loc = "All European Locales"
                        else:
                            clean_loc = "France"
                            for k in ["France", "Spain", "Germany", "Italy", "United Kingdom"]:
                                if k.lower() in str(loc_selection).lower():
                                    clean_loc = k
                                    break
                        items = self.manomano_scraper.search(
                            store_raw,
                            actual_term,
                            excludes=job["excludes"],
                            condition=job.get("condition", "all"),
                            max_pages=4,
                            locale_key=clean_loc,
                            stop_event=self.stop_event,
                            pause_event=self.pause_event
                        )
                        dom_ext = "fr" if clean_loc == "France" else ("es" if clean_loc == "Spain" else ("de" if clean_loc == "Germany" else ("it" if clean_loc == "Italy" else ("co.uk" if clean_loc == "United Kingdom" else "fr"))))
                        job_record["url"] = f"https://www.manomano.{dom_ext}/recherche/{actual_term.replace(' ', '+')}"
                    elif is_scribd:
                        self.scribd_scraper.headless = is_headless
                        sc_pages = 2
                        if hasattr(self, "scribd_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.scribd_depth_var.get())
                            if m: sc_pages = int(m.group(1))

                        raw_mode = self.scribd_doc_mode_var.get() if hasattr(self, "scribd_doc_mode_var") else "🌐 All Documents"
                        doc_mode_map = {
                            "🌐 All Documents": "all",
                            "🔧 Vehicle Service Manuals": "manuals",
                            "🚨 OEM Engineering Standards (GMW)": "standards",
                            "📑 Technical Service Bulletins (TSB)": "tsb"
                        }
                        sc_doc_mode = doc_mode_map.get(raw_mode, "all")

                        items = self.scribd_scraper.search(
                            store_raw,
                            actual_term,
                            job["excludes"],
                            condition=job.get("condition", "all"),
                            max_pages=sc_pages,
                            doc_mode=sc_doc_mode,
                            stop_event=self.stop_event,
                            pause_event=self.pause_event,
                            log_callback=self._log
                        )
                        job_record["url"] = f"https://www.scribd.com/search?content_type=documents&query={actual_term.replace(' ', '+')}"
                    elif is_tiktok:
                        self.tiktok_scraper.headless = is_headless
                        items = self.tiktok_scraper.search(
                            store_raw,
                            actual_term,
                            job["excludes"],
                            condition=job.get("condition", "all"),
                            stop_event=self.stop_event,
                            pause_event=self.pause_event
                        )
                        job_record["url"] = f"https://shop.tiktok.com/us/search?q={actual_term.replace(' ', '+')}"
                    elif is_teepublic:
                        self.teepublic_scraper.headless = is_headless
                        tp_pages = 2
                        if hasattr(self, "tp_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.tp_depth_var.get())
                            if m: tp_pages = int(m.group(1))
                        clean_tp_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "artist community"))) else None
                        items = self.teepublic_scraper.search(
                            actual_term,
                            depth_pages=tp_pages,
                            store_filter=clean_tp_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://www.teepublic.com/t-shirts?query={actual_term.replace(' ', '+')}"
                    elif is_etsy:
                        self.etsy_scraper.headless = is_headless
                        etsy_pages = 2
                        if hasattr(self, "etsy_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.etsy_depth_var.get())
                            if m: etsy_pages = int(m.group(1))
                        clean_etsy_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "commercial makers"))) else None
                        items = self.etsy_scraper.search(
                            actual_term,
                            depth_pages=etsy_pages,
                            commercial_only=True,
                            store_filter=clean_etsy_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://www.etsy.com/search?q={actual_term.replace(' ', '+')}"
                    elif is_spreadshirt:
                        self.spreadshirt_scraper.headless = is_headless
                        sp_pages = 2
                        if hasattr(self, "spreadshirt_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.spreadshirt_depth_var.get())
                            if m: sp_pages = int(m.group(1))
                        clean_sp_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "community", "spreadshop"))) else None
                        items = self.spreadshirt_scraper.search(
                            actual_term,
                            depth_pages=sp_pages,
                            store_filter=clean_sp_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://www.spreadshirt.com/shop/{actual_term.replace(' ', '+')}/"
                    elif is_zazzle:
                        self.zazzle_scraper.headless = is_headless
                        z_pages = 2
                        if hasattr(self, "zazzle_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.zazzle_depth_var.get())
                            if m: z_pages = int(m.group(1))
                        clean_z_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "community", "store"))) else None
                        items = self.zazzle_scraper.search(
                            actual_term,
                            depth_pages=z_pages,
                            store_filter=clean_z_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://www.zazzle.com/s/{actual_term.replace(' ', '+')}"
                    elif is_cafepress:
                        self.cafepress_scraper.headless = is_headless
                        cp_pages = 2
                        if hasattr(self, "cafepress_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.cafepress_depth_var.get())
                            if m: cp_pages = int(m.group(1))
                        clean_cp_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "community", "profile", "shop"))) else None
                        items = self.cafepress_scraper.search(
                            actual_term,
                            depth_pages=cp_pages,
                            store_filter=clean_cp_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://www.cafepress.com/+{actual_term.replace(' ', '+')}"
                    elif is_threadless:
                        self.threadless_scraper.headless = is_headless
                        th_pages = 2
                        if hasattr(self, "threadless_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.threadless_depth_var.get())
                            if m: th_pages = int(m.group(1))
                        clean_th_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "community", "shop"))) else None
                        items = self.threadless_scraper.search(
                            actual_term,
                            depth_pages=th_pages,
                            store_filter=clean_th_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://www.threadless.com/search/?q={actual_term.replace(' ', '+')}"
                    elif is_teespring:
                        self.teespring_scraper.headless = is_headless
                        ts_pages = 2
                        if hasattr(self, "teespring_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.teespring_depth_var.get())
                            if m: ts_pages = int(m.group(1))
                        clean_ts_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "community", "store"))) else None
                        items = self.teespring_scraper.search(
                            actual_term,
                            depth_pages=ts_pages,
                            store_filter=clean_ts_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://spring.com/search?q={actual_term.replace(' ', '+')}"
                    elif is_faa:
                        self.fineartamerica_scraper.headless = is_headless
                        faa_pages = 2
                        if hasattr(self, "fineartamerica_depth_var"):
                            m = re.search(r'(\d+)\s+Page', self.fineartamerica_depth_var.get())
                            if m: faa_pages = int(m.group(1))
                        clean_faa_store = store_raw if (store_raw and not any(k in store_raw.lower() for k in ("global", "search", "all", "community", "profile", "artist"))) else None
                        items = self.fineartamerica_scraper.search(
                            actual_term,
                            depth_pages=faa_pages,
                            store_filter=clean_faa_store,
                            condition=job.get("condition", "all"),
                            log_callback=self._log,
                            status_callback=self._status
                        )
                        job_record["url"] = f"https://fineartamerica.com/art/{actual_term.replace(' ', '+')}"
                    else:
                        ebay_loc = job.get("ebay_locale") or (self.ebay_country_var.get() if hasattr(self, "ebay_country_var") else "United States")
                        domain = self.scraper._clean_ebay_domain(ebay_loc)
                        is_multi_or_reverse = any(w in ebay_loc.lower() for w in ("all", "reverse", "sweep"))

                        target_url = self.scraper._build_url(
                            self.scraper.resolve_store_info(store_raw),
                            actual_term,
                            job["excludes"],
                            1,
                            job.get("condition", "all"),
                            domain=domain
                        )
                        self._log(f"  🔗 URL: {target_url}")
                        job_record["url"] = target_url

                        if is_multi_or_reverse:
                            self._log(f"🌍 [eBay Multi-Locale Sweep] Sweeping top international domains for {term_display} in {seller_label}...")
                            items = self.scraper.search_multi_locale(
                                store_raw,
                                actual_term,
                                job["excludes"],
                                condition=job.get("condition", "all"),
                                stop_event=self.stop_event,
                                pause_event=self.pause_event,
                                log_callback=self._log
                            )
                        else:
                            items = self.scraper.search(
                                store_raw,
                                actual_term,
                                job["excludes"],
                                condition=job.get("condition", "all"),
                                stop_event=self.stop_event,
                                pause_event=self.pause_event,
                                domain=domain,
                                reverse_locale_probe=False,
                                log_callback=self._log
                            )

                    new_items = []
                    filtered_out_count = 0
                    filtered_out_count = 0
                    filtered_reasons = {}
                    for item in items:
                        title = item.get("title", "")
                        # 1. Strict Exclusion Filter (Analyst-defined explicit exclusions)
                        passed_excl, matched_ex = self._check_strict_exclusions(title, job.get("excludes", []))
                        if not passed_excl:
                            filtered_out_count += 1
                            r_key = f"Excluded '{matched_ex}'"
                            filtered_reasons[r_key] = filtered_reasons.get(r_key, 0) + 1
                            continue

                        # 2. Targeted Search Verification & Search Hygiene
                        b_low = job.get("brand", "").lower().strip()
                        is_sweep_brand = (
                            not b_low or
                            any(w in b_low for w in ("full store sweep", "store inventory", "all products", "full search", "custom search", "mercado libre", "mercado", "global", "global search", "marketplace", "full sweep", "sweep"))
                        )
                        is_full_sweep = is_sweep_brand or is_meli or (include_term in ("*", "", "all"))
                        if not is_full_sweep and include_term:
                            t_low = title.lower()
                            search_tokens = [tk.lower().strip() for tk in re.split(r"[\s+,]+", include_term) if len(tk.strip()) >= 2]
                            target_b = b_low
                            if target_b and not any(w in target_b for w in ("full store sweep", "full search", "custom search", "store inventory", "all products", "mercado libre", "mercado", "global", "global search", "marketplace", "sweep")):
                                search_tokens.extend([tk.lower().strip() for tk in re.split(r"[\s+,]+", target_b) if len(tk.strip()) >= 2])

                            brand_data = self.data_store.get_brands().get(job.get("brand", ""), {})
                            for m in brand_data.get("models", []):
                                search_tokens.append(m.lower().strip())
                            for sub_k, sub_models in brand_data.get("subs", {}).items():
                                search_tokens.append(sub_k.lower().strip())
                                for sm in sub_models:
                                    search_tokens.append(sm.lower().strip())

                            clean_tokens = [tk for tk in set(search_tokens) if len(tk) >= 2]
                            has_target = any(tk in t_low or re.search(r'\b' + re.escape(tk) + r'\b', t_low) for tk in clean_tokens) if clean_tokens else True
                            if not has_target:
                                filtered_out_count += 1
                                r_key = "Search Hygiene (No Keyword Match)"
                                filtered_reasons[r_key] = filtered_reasons.get(r_key, 0) + 1
                                continue

                        # 3. Auto-detect brand & product type from title
                        auto_b, auto_pt = self._auto_detect_brand_from_title(title)
                        if is_full_sweep:
                            if auto_b != "Unassigned":
                                item["brand"] = auto_b
                            else:
                                item["brand"] = include_term.capitalize() if include_term and include_term != "*" else (job.get("brand") or "Unassigned")
                            if not item.get("product_type"):
                                item["product_type"] = auto_pt
                        else:
                            if auto_b != "Unassigned":
                                item["brand"] = auto_b
                            else:
                                item["brand"] = job["brand"]
                            if not item.get("product_type"):
                                item["product_type"] = auto_pt or self._detect_product_type(title)

                        item["keyword"] = "🏪 Full Sweep" if include_term == "*" else include_term
                        if "marketplace" not in item or not item["marketplace"]:
                            item["marketplace"] = mkt_tag

                        item_id = str(item.get("item_id", "")).strip()
                        seller_str = str(item.get("seller", "")).strip().lower()
                        raw_url = str(item.get("url", "")).strip().lower()
                        norm_url = raw_url.split("?")[0] if raw_url else ""
                        if seller_str and seller_str != "mercado libre seller":
                            dedup_key = f"{item_id}::{seller_str}" if item_id else f"{norm_url}::{seller_str}"
                        else:
                            dedup_key = norm_url if norm_url else (f"{item.get('marketplace', '')}_{item_id}" if item_id else None)
                        if dedup_key and dedup_key not in self.seen_item_ids:
                            self.seen_item_ids.add(dedup_key)
                            self.results.append(item)
                            new_items.append(item)
                            total_new_items += 1
                        elif not dedup_key:
                            self.results.append(item)
                            new_items.append(item)
                            total_new_items += 1

                    job_record["term_counts"][include_term] = len(items)
                    job_record["total_harvested"] += len(new_items)

                    if filtered_out_count > 0:
                        reason_summary = ", ".join([f"{k} ({cnt})" for k, cnt in filtered_reasons.items()])
                        self._log(f"  🛡 Filtered {filtered_out_count} listing(s) [{reason_summary}].")

                    if new_items:
                        self._update_results_table(new_items)
                    elif len(items) == 0 and hasattr(self.scraper, "last_scrape_warning") and self.scraper.last_scrape_warning:
                        self._log(f"  {self.scraper.last_scrape_warning}")
                        self.scraper.last_scrape_warning = ""

                    if len(items) == 0 and hasattr(self.scraper, "is_bot_challenge") and self.scraper.is_bot_challenge:
                        b_name = self.scraper.blocked_store_name or seller_label
                        b_url = self.scraper.blocked_store_url or target_url
                        self.scraper.is_bot_challenge = False
                        
                        self.paused = True
                        self.pause_event.clear()
                        self.after(0, self._update_pause_ui_state)
                        self._log(f"  ⚠ [AUTO-PAUSED] Security challenge detected on '{b_name}'. Pausing queue for analyst recovery.")
                        
                        recovery_choice = {"action": "retry"}
                        recovery_event = threading.Event()
                        
                        def _on_recovery(choice):
                            recovery_choice["action"] = choice
                            recovery_event.set()
                            
                        self.after(0, lambda n=b_name, u=b_url, cb=_on_recovery: self._prompt_bot_challenge_recovery(n, u, callback=cb))
                        
                        # Synchronously block worker thread until analyst chooses Retry or Skip in modal
                        recovery_event.wait()
                        
                        if recovery_choice["action"] == "retry":
                            self._log(f"  🔄 Retrying sweep on '{b_name}'...")
                            items = self.scraper.search(
                                store_raw,
                                actual_term,
                                job["excludes"],
                                condition=job.get("condition", "all"),
                                stop_event=self.stop_event,
                                pause_event=self.pause_event,
                                domain=domain,
                                reverse_locale_probe=False,
                                log_callback=self._log
                            )
                            for item in items:
                                title = item.get("title", "")
                                passed_excl, matched_ex = self._check_strict_exclusions(title, job.get("excludes", []))
                                if not passed_excl:
                                    filtered_out_count += 1
                                    continue
                                auto_b, auto_pt = self._auto_detect_brand_from_title(title)
                                if job["brand"] in ("Full Store Sweep", "Store Inventory", "All Products", "Full Search", "", "Custom Search") or include_term == "*":
                                    item["brand"] = auto_b
                                    if not item.get("product_type"): item["product_type"] = auto_pt
                                else:
                                    item["brand"] = auto_b if auto_b != "Unassigned" else job["brand"]
                                    if not item.get("product_type"): item["product_type"] = auto_pt or self._detect_product_type(title)
                                item["keyword"] = "🏪 Full Sweep" if include_term == "*" else include_term
                                if "marketplace" not in item or not item["marketplace"]: item["marketplace"] = mkt_tag
                                item_id = item.get("item_id")
                                seller_str = str(item.get("seller", "")).strip().lower()
                                dedup_key = f"{item_id}::{seller_str}" if item_id and seller_str and seller_str != "mercado libre seller" else (item_id or item.get("url"))
                                if dedup_key and dedup_key not in self.seen_item_ids:
                                    self.seen_item_ids.add(dedup_key)
                                    self.results.append(item)
                                    new_items.append(item)
                                    total_new_items += 1
                                elif not dedup_key:
                                    self.results.append(item)
                                    new_items.append(item)
                                    total_new_items += 1
                            if new_items:
                                self._update_results_table(new_items)

                    self._log(f"  → Found {len(items)} listings ({len(new_items)} new) for '{include_term}' in {seller_label} [{platform_name}]")

            except Exception as e:
                self._log(f"ERROR on {job['brand']} in {seller_label} [{platform_name}]: {e}", error=True)
                job_record["error"] = str(e)

            self.executed_jobs.append(job_record)
            if self.queue:
                self.queue.pop(0)
            self.after(0, self._pop_queue_ui_item)

        stopped_early = self.stop_event.is_set()
        self.after(0, self._run_complete, total_new_items, stopped_early)

    def _run_complete(self, total, stopped_early=False):
        t = self.theme
        self.running = False
        self.paused = False
        self.progress.stop()

        self.run_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="⏸  Pause", bg=t["btn_normal_bg"])
        self.stop_btn.config(state="disabled")
        if hasattr(self, "dedup_q_btn"):
            self.dedup_q_btn.config(state="normal")
        self.del_q_btn.config(state="normal")
        self.clear_q_btn.config(state="normal")

        # Play sound effect if enabled
        if self.sound_enabled_var.get():
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        if stopped_early:
            msg = f"Scan stopped by user. {total} new listings harvested ({len(self.results)} total in session)."
            self._status(msg)
            self._log(f"⏹ {msg}")
            self._show_themed_info("Scan Stopped", f"Scan stopped by user.\n\nHarvested {total} new listings ({len(self.results)} total in session).", icon="⏹")
        else:
            msg = f"Done. {total} new listings harvested ({len(self.results)} total in session)."
            self._status(msg)
            self._log(f"✓ Run complete — {total} listings harvested.")
            self._show_themed_info("Sweep Complete", f"Successfully harvested {total} listings across targets!\n\nClick 'Export' or 'Stash to Dossier' to save.", icon="🎉")

        self.result_count.set(f"{len(self.results)} listings")
        self._check_enforcement_milestones()
        # Post-sweep thumbnail refresh pulse to guarantee 100% of thumbnails display immediately
        self.after(350, self._repopulate_results_table)

    def _update_pause_ui_state(self):
        t = self.theme
        if self.paused:
            self.pause_btn.config(text="▶  Resume", bg=t["success"], fg="#FFFFFF")
            self.progress.stop()
        else:
            self.pause_btn.config(text="⏸  Pause", bg=t["btn_normal_bg"], fg=t["btn_normal_fg"])
            if self.running:
                self.progress.start(12)

    def _prompt_bot_challenge_recovery(self, store_name, store_url, callback=None):
        """Display an interactive recovery modal when eBay serves a CAPTCHA / rate-limit challenge."""
        t = self.theme
        win = tk.Toplevel(self)
        win.title("⚠ Security Challenge / CAPTCHA Detected")
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        win.transient(self)
        self._apply_dark_titlebar(win)
        self._center_window(win, 540, 330)
        win.grab_set()
        win.focus_force()

        tk.Label(win, text="⚠ eBay Security / CAPTCHA Challenge", bg=t["bg"], fg=t["warning"],
                 font=("Segoe UI", 12, "bold")).pack(pady=(16, 6))

        msg = (
            f"eBay has returned a security verification check / CAPTCHA challenge on:\n"
            f"Store: '{store_name}'\n\n"
            f"The search queue has been PAUSED to prevent missing inventory.\n"
            f"You can solve the verification check in your browser, and then retry."
        )
        tk.Label(win, text=msg, bg=t["bg"], fg=t["text"], font=FONT_SM, justify="center", wraplength=480).pack(pady=(0, 16), padx=20)

        btn_box = tk.Frame(win, bg=t["bg"])
        btn_box.pack(fill="x", padx=20, pady=(10, 0))

        def _open_in_browser():
            target = store_url or f"https://www.ebay.com/str/{store_name}"
            w_pos = self._get_browser_window_pos()
            self._log(f"🌐 Launching live scraper browser window for '{target}'...")
            threading.Thread(target=lambda: self.scraper.open_interactive_solve_window(target, window_pos=w_pos), daemon=True).start()

        def _retry():
            win.destroy()
            self.paused = False
            self.pause_event.set()
            self._update_pause_ui_state()
            if callback:
                callback("retry")

        def _skip():
            win.destroy()
            self.paused = False
            self.pause_event.set()
            self._update_pause_ui_state()
            self._log(f"⏭ Skipped challenge store '{store_name}'. Resuming search queue...")
            if callback:
                callback("skip")

        win.protocol("WM_DELETE_WINDOW", _skip)

        tk.Button(btn_box, text="🌐  Open Scraper Browser to Solve", bg=t["accent"], fg=t["select_fg"],
                  font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2",
                  command=_open_in_browser).pack(side="left", padx=4)

        tk.Button(btn_box, text="🔄  Resume & Retry Store", bg=t["success"], fg="#FFFFFF",
                  font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2",
                  command=_retry).pack(side="left", padx=4)

        tk.Button(btn_box, text="⏭  Skip Store", bg=t["btn_normal_bg"], fg=t["btn_normal_fg"],
                  font=FONT_SM, relief="flat", padx=10, pady=6, cursor="hand2",
                  command=_skip).pack(side="right", padx=4)

    # ══════════════════════════════════════════════════════════════════════════
    #  RESULTS TABLE, LIVE FILTERING, BULK TAGGING & HOVER PREVIEWS
    # ══════════════════════════════════════════════════════════════════════════
    def _refresh_bulk_brand_list(self):
        """Populate the bulk brand reassignment combobox from data_store."""
        if not hasattr(self, "bulk_brand_combo"):
            return
        brands = ["(No change)"]
        raw = self.data_store.get_brands()
        for parent, pdata in raw.items():
            if parent not in brands:
                brands.append(parent)
            for sub in pdata.get("subs", {}):
                if sub not in brands:
                    brands.append(sub)
        self.bulk_brand_combo["values"] = brands
        self.bulk_brand_combo.set("(No change)")

    def _clear_filter(self):
        """Clear live search filter and show all results."""
        if hasattr(self, "filter_var"):
            self.filter_var.set("")
        if hasattr(self, "filter_mkt_var"):
            self.filter_mkt_var.set("All Marketplaces")
        if hasattr(self, "filter_brand_var"):
            self.filter_brand_var.set("All Brands")
        if hasattr(self, "filter_col_var"):
            self.filter_col_var.set("Title")
        self._repopulate_results_table()

    def _select_all_visible(self):
        """Select all currently visible (and filtered) rows in results table."""
        children = self.result_tree.get_children()
        if children:
            self.result_tree.selection_set(children)

    def _deduplicate_results(self):
        """Deduplicate harvested listings by item ID and URL across active session."""
        if not self.results:
            messagebox.showinfo("Deduplicate", "No harvested listings in results table to deduplicate.")
            return

        initial_len = len(self.results)
        seen_ids = set()
        seen_urls = set()
        unique_items = []

        for it in self.results:
            iid = str(it.get("item_id", "")).strip()
            mkt = str(it.get("marketplace", "")).strip()
            scoped_id = f"{mkt}_{iid}" if iid else ""
            url = str(it.get("url", "")).strip().lower()
            norm_url = url.split("?")[0] if url else ""

            if (scoped_id and scoped_id in seen_ids) or (norm_url and norm_url in seen_urls):
                continue

            if scoped_id: seen_ids.add(scoped_id)
            if norm_url: seen_urls.add(norm_url)
            unique_items.append(it)

        purged = initial_len - len(unique_items)
        if purged > 0:
            self.results = unique_items
            self.seen_item_ids = {str(it.get("url", "")).split("?")[0] for it in self.results if it.get("url")}
            self._repopulate_results_table()
            self._log(f"🧹 Purged {purged} duplicate listings from results table.")
            self._show_themed_info("Deduplication Complete", f"Removed {purged} duplicate listings.\n\n{len(self.results)} unique listings remain.", icon="🧹")
        else:
            self._show_themed_info("Deduplication Complete", "No duplicates found.\n\nAll listings are unique.", icon="✓")

    def _stash_to_dossier(self):
        """Move verified/triaged listings from active table into the persistent Dossier Staging Vault."""
        selected_iids = self.result_tree.selection()
        if selected_iids:
            target_urls = {str(self.result_tree.set(iid, "url")).strip().lower() for iid in selected_iids if self.result_tree.set(iid, "url")}
            target_ids = {str(self.result_tree.set(iid, "item_id")).strip() for iid in selected_iids if self.result_tree.set(iid, "item_id")}
            to_stash = [
                it for it in self.results
                if (it.get("url") and str(it["url"]).strip().lower() in target_urls)
                or (it.get("item_id") and str(it["item_id"]).strip() in target_ids)
            ]
            stash_set = set(id(it) for it in to_stash)
            self.results = [it for it in self.results if id(it) not in stash_set]
        else:
            visible_urls = {str(self.result_tree.set(iid, "url")).strip().lower() for iid in self.result_tree.get_children() if self.result_tree.set(iid, "url")}
            visible_ids = {str(self.result_tree.set(iid, "item_id")).strip() for iid in self.result_tree.get_children() if self.result_tree.set(iid, "item_id")}
            if not visible_urls and not visible_ids:
                messagebox.showinfo("Dossier Staging Vault", "No listings in results table to stash into dossier.")
                return
            to_stash = [
                it for it in self.results
                if (it.get("url") and str(it["url"]).strip().lower() in visible_urls)
                or (it.get("item_id") and str(it["item_id"]).strip() in visible_ids)
            ]
            stash_set = set(id(it) for it in to_stash)
            self.results = [it for it in self.results if id(it) not in stash_set]

        if not to_stash:
            return

        def _get_stash_key(item_dict):
            raw_u = str(item_dict.get("url", "")).strip().lower().split("?")[0]
            if raw_u:
                return f"url::{raw_u}"
            mkt = str(item_dict.get("marketplace", "")).strip().lower()
            iid = str(item_dict.get("item_id", "")).strip().lower()
            return f"id::{mkt}::{iid}"

        existing_staged_keys = {_get_stash_key(it) for it in self.staged_dossier}
        added_count = 0
        for it in to_stash:
            k = _get_stash_key(it)
            if k not in existing_staged_keys:
                self.staged_dossier.append(it)
                existing_staged_keys.add(k)
                added_count += 1

        self.data_store.save_staged_dossier(self.staged_dossier)
        self.seen_item_ids = {str(it.get("url", "")).split("?")[0] for it in self.results if it.get("url")}
        self._repopulate_results_table()

        if hasattr(self, "btn_view_dossier"):
            self.btn_view_dossier.config(text=f"📁 Staged ({len(self.staged_dossier)})")

        self._log(f"📥 [STAGING VAULT] Moved {added_count} verified target(s) into Dossier Staging Vault (Total Staged: {len(self.staged_dossier)}). Active table cleared for Wave 2.")
        self._status(f"📥 Stashed {added_count} listings into Dossier Vault! Active table cleared.")
        messagebox.showinfo("Dossier Staging Vault", f"Successfully moved {added_count} listing(s) into your Dossier Staging Vault!\n\n• Staged Dossier Total: {len(self.staged_dossier)} verified listings\n• Live Results Table: Cleared and ready for your next sweep wave.\n\nWhen ready, click '📁 Staged ({len(self.staged_dossier)})' to restore, or '💾 Export' to export all waves!")

    def _view_or_restore_dossier(self):
        """View or restore listings stored in the Dossier Staging Vault."""
        if not self.staged_dossier:
            messagebox.showinfo("Dossier Staging Vault", "Your Dossier Staging Vault is currently empty.\n\nTriage your harvest and click '📥 Stash to Dossier' to park verified targets and clear the screen before your next sweep wave!")
            return

        count = len(self.staged_dossier)
        ans = messagebox.askyesnocancel("Dossier Staging Vault", f"Your Dossier Staging Vault currently contains {count} verified listings.\n\n• [Yes]: Restore all {count} listings back into the Live Results Table\n• [No]: Keep them safely parked in the vault\n• [Cancel]: Do nothing", icon="question")
        if ans is True:
            existing_urls = {str(it.get("url", "")).split("?")[0].lower() for it in self.results if it.get("url")}
            existing_ids = {str(it.get("item_id", "")).strip() for it in self.results if it.get("item_id")}
            restored = 0
            for it in self.staged_dossier:
                u = str(it.get("url", "")).split("?")[0].lower()
                iid = str(it.get("item_id", "")).strip()
                if (u and u not in existing_urls) or (iid and iid not in existing_ids) or (not u and not iid):
                    self.results.append(it)
                    if u: existing_urls.add(u)
                    if iid: existing_ids.add(iid)
                    restored += 1
            self.staged_dossier.clear()
            self.data_store.clear_staged_dossier()
            if hasattr(self, "btn_view_dossier"):
                self.btn_view_dossier.config(text="📁 Staged (0)")
            self.seen_item_ids = {str(it.get("url", "")).split("?")[0] for it in self.results if it.get("url")}
            self._repopulate_results_table()
            self._log(f"📁 Restored {restored} listing(s) from Staging Vault back into Live Results Table.")
            self._status(f"📁 Restored {restored} listings to Live Results Table.")

    def _on_filter_changed(self, *args):
        """Triggered on keystroke in live search filter entry."""
        self._repopulate_results_table()

    def _apply_bulk_tag(self):
        """Apply selected Brand and/or Product Type to all highlighted rows."""
        selected_iids = self.result_tree.selection()
        if not selected_iids:
            messagebox.showinfo("Select Rows", "Select one or more rows in the results table first.\n(Tip: You can use 'Select All Visible' or Ctrl+Click).")
            return

        new_brand = self.bulk_brand_var.get().strip()
        new_pt = self.bulk_product_var.get().strip()
        if new_pt == "(Select or type...)":
            new_pt = ""

        if (not new_brand or new_brand == "(No change)") and not new_pt:
            messagebox.showinfo("Nothing to Apply", "Choose a Brand to reassign or enter/select a Product Type.")
            return

        updated_count = 0
        for iid in selected_iids:
            vals = list(self.result_tree.item(iid, "values"))
            # values mapping: (brand[0], product_type[1], title[2], item_id[3], price[4], seller[5], location[6], image_url[7], url[8])
            row_item_id = str(vals[3]).strip() if len(vals) > 3 else ""
            row_url = str(vals[8]).strip() if len(vals) > 8 else ""

            # Update master record in self.results
            for item in self.results:
                if (row_item_id and str(item.get("item_id", "")).strip() == row_item_id) or \
                   (row_url and str(item.get("url", "")).strip() == row_url):
                    if new_brand and new_brand != "(No change)":
                        item["brand"] = new_brand
                    if new_pt:
                        item["product_type"] = new_pt
                    updated_count += 1
                    break

        self._repopulate_results_table()
        tag_desc = []
        if new_brand and new_brand != "(No change)":
            tag_desc.append(f"Brand: '{new_brand}'")
        if new_pt:
            tag_desc.append(f"Product Type: '{new_pt}'")
        summary_str = " | ".join(tag_desc)
        self._log(f"🏷 Bulk Tag Applied to {updated_count} listing(s) → {summary_str}")
        self._status(f"Tagged {updated_count} listing(s) ({summary_str})")

    def _get_item_marketplace(self, item: dict) -> str:
        """Resolve canonical marketplace display name for an item."""
        mkt = str(item.get("marketplace", "")).strip()
        url = str(item.get("url", "")).strip().lower()
        mkt_low = mkt.lower()

        if "redbubble" in mkt_low or "redbubble.com" in url:
            return "Redbubble"
        elif "printerval" in mkt_low or "printerval.com" in url:
            return "Printerval"
        elif "teepublic" in mkt_low or "teepublic.com" in url or "tee.pub" in url:
            return "TeePublic"
        elif "etsy" in mkt_low or "etsy.com" in url:
            return "Etsy"
        elif "spreadshirt" in mkt_low or "spreadshirt.com" in url or "spreadshop.com" in url:
            return "Spreadshirt"
        elif "zazzle" in mkt_low or "zazzle.com" in url:
            return "Zazzle"
        elif "cafepress" in mkt_low or "cafepress.com" in url:
            return "CafePress"
        elif "threadless" in mkt_low or "threadless.com" in url:
            return "Threadless"
        elif "teespring" in mkt_low or "spring.com" in url or "creator-spring.com" in url:
            return "TeeSpring"
        elif "fineartamerica" in mkt_low or "pixels.com" in url or "fineartamerica.com" in url:
            return "Fine Art America"
        elif "tiktok" in mkt_low or "tiktok.com" in url or "shop.tiktok" in url:
            return "TikTok Shop"
        elif "aliexpress" in mkt_low or "aliexpress.com" in url or "aliexpress.us" in url:
            return "AliExpress"
        elif "ebay" in mkt_low or "ebay." in url:
            return "eBay"
        elif "manomano" in mkt_low or "manomano." in url:
            return "ManoMano"
        elif "wish" in mkt_low or "wish.com" in url:
            return "Wish"
        elif "temu" in mkt_low or "temu.com" in url:
            return "Temu"
        elif "vinted" in mkt_low or "vinted." in url:
            return "Vinted"
        elif "scribd" in mkt_low or "scribd.com" in url:
            return "Scribd"
        elif "mercado" in mkt_low or "mercadolibre" in mkt_low or "mercadolivre" in mkt_low or "mercadolibre." in url or "mercadolivre." in url:
            return "Mercado Libre"
        elif mkt:
            return mkt
        return "eBay"

    def _item_matches_filter(self, item: dict, query_str: str, target_col: str = None) -> bool:
        """
        Intelligent multi-column search evaluator supporting:
        1. Column-specific target routing (Title, Seller, Item ID, Brand, Product Type, Price, Location, Marketplace, All Columns)
        2. Positive token matching (e.g. 'emblem', 'trd')
        3. Negative exclusion modifiers (e.g. '-toyota', '-keychain', '-audi')
        4. Quoted exact phrase matching (e.g. '"valve stem" -plastic')
        """
        if not query_str or not query_str.strip():
            return True

        if not target_col:
            target_col = self.filter_col_var.get() if hasattr(self, "filter_col_var") else "Title"

        col_key = target_col.lower().strip()
        if "title" in col_key:
            target_text = str(item.get("title", ""))
        elif "seller" in col_key:
            target_text = str(item.get("seller", ""))
        elif "origin" in col_key:
            target_text = str(item.get("seller_origin", item.get("country", "")))
        elif "threat" in col_key:
            target_text = str(item.get("threat_badge", item.get("threat_intel", "")))
        elif "item" in col_key or "id" in col_key:
            target_text = str(item.get("item_id", ""))
        elif "brand" in col_key:
            target_text = str(item.get("brand", ""))
        elif "product" in col_key:
            target_text = str(item.get("product_type", ""))
        elif "market" in col_key or "platform" in col_key:
            target_text = self._get_item_marketplace(item)
        elif "price" in col_key:
            target_text = str(item.get("price", ""))
        elif "location" in col_key:
            target_text = str(item.get("location", ""))
        else:
            # All Columns concatenated
            target_text = " ".join([
                str(item.get("brand", "")),
                str(item.get("product_type", "")),
                str(item.get("title", "")),
                str(item.get("item_id", "")),
                str(self._get_item_marketplace(item)),
                str(item.get("seller", "")),
                str(item.get("seller_origin", "")),
                str(item.get("threat_badge", "")),
                str(item.get("location", "")),
                str(item.get("price", "")),
                str(item.get("keyword", "")),
            ])

        target_lower = target_text.lower()

        import shlex
        try:
            raw_tokens = shlex.split(query_str)
        except Exception:
            raw_tokens = query_str.split()

        positive_tokens = []
        negative_tokens = []

        for tok in raw_tokens:
            tok = tok.strip()
            if not tok:
                continue
            if tok.startswith("-") and len(tok) > 1:
                negative_tokens.append(tok[1:].lower())
            elif tok.startswith("+") and len(tok) > 1:
                positive_tokens.append(tok[1:].lower())
            else:
                positive_tokens.append(tok.lower())

        # Check negative exclusions (item is rejected if ANY negative token is found)
        for neg in negative_tokens:
            if neg in target_lower:
                return False

        # Check positive inclusions (item must contain ALL positive tokens)
        for pos in positive_tokens:
            if pos not in target_lower:
                return False

        return True

    def _update_results_table(self, items):
        """Append newly scraped items honoring the active live search filter."""
        def _add():
            try:
                query = self.filter_var.get().strip() if hasattr(self, "filter_var") else ""
                target_col = self.filter_col_var.get() if hasattr(self, "filter_col_var") else "Title"
                size_key = self.thumb_size_var.get() if hasattr(self, "thumb_size_var") else "Medium (100px)"
                cfg = THUMB_CONFIG.get(size_key, THUMB_CONFIG["Medium (100px)"])
                is_thumbs = (cfg["img_size"] > 0)
                ph = self._get_placeholder_thumb(cfg["img_size"]) if is_thumbs else ""

                for item in items:
                    if "product_type" not in item:
                        item["product_type"] = ""

                    # Evaluate Threat Intel from DataStore cache
                    GENERIC_SELLER_PLACEHOLDERS = {"ebay seller", "unknown", "resolving...", "global search", "aliexpress global", "printerval creator", "printerval seller", "mercado libre seller", "mercado libre merchant", "tiktok shop merchant", "redbubble artist", "vinted user", "meli_seller_"}
                    seller_clean = str(item.get("seller", "")).replace("🛡", "").replace("(Authorized)", "").strip()
                    is_generic_seller = not seller_clean or any(g in seller_clean.lower() for g in GENERIC_SELLER_PLACEHOLDERS)
                    
                    cached_intel = self.data_store.get_seller_intel(seller_clean) if not is_generic_seller else None
                    raw_origin = item.get("seller_origin") or (cached_intel.get("country") if (cached_intel and cached_intel.get("country") != "Unknown") else "")
                    loc = item.get("location", "")

                    assessment = self.data_store.compute_threat_assessment(raw_origin, loc, seller_name=seller_clean)
                    
                    orig_display = ""
                    if raw_origin and raw_origin != "Unknown":
                        orig_flag = self.data_store.COUNTRY_FLAGS.get(raw_origin.lower(), "🌍")
                        orig_display = f"{orig_flag} {raw_origin}"
                        item["seller_origin"] = raw_origin
                    elif item.get("seller_origin") and item.get("seller_origin") != "Unknown":
                        orig_flag = self.data_store.COUNTRY_FLAGS.get(item["seller_origin"].lower(), "🌍")
                        orig_display = f"{orig_flag} {item['seller_origin']}"

                    # If item already has a specialized visual or threat badge, preserve it
                    if item.get("visual_benign"):
                        threat_display = item.get("threat_badge", "🟢 Benign Packaging")
                    elif item.get("visual_counterfeit"):
                        threat_display = item.get("threat_badge", "🚨 Visual Counterfeit")
                    elif item.get("threat_badge"):
                        raw_tb = str(item["threat_badge"]).strip()
                        if "\n" in raw_tb or len(raw_tb) > 60:
                            threat_display = assessment.get("badge", "") if ((raw_origin and raw_origin != "Unknown") or assessment.get("is_high_risk")) else ""
                            item["threat_badge"] = threat_display
                        else:
                            threat_display = raw_tb
                    elif assessment.get("is_high_risk"):
                        threat_display = assessment.get("badge", "")
                        item["threat_badge"] = threat_display
                    elif raw_origin and raw_origin != "Unknown":
                        threat_display = assessment.get("badge", "")
                        item["threat_badge"] = threat_display
                    else:
                        threat_display = ""

                    # Check Benign Filter (Hide Benign vs Show All vs Benign Only)
                    b_mode = self.benign_filter_var.get() if hasattr(self, "benign_filter_var") else "🛡 Hide Benign"
                    is_item_benign = item.get("visual_benign") or str(threat_display).startswith("🟢 Benign")
                    if b_mode == "🟢 Benign Only" and not is_item_benign:
                        continue
                    elif b_mode == "🛡 Hide Benign" and is_item_benign:
                        continue

                    # Check High-Risk filter checkbox
                    if hasattr(self, "filter_high_risk_var") and self.filter_high_risk_var.get():
                        if not self._is_high_risk_item(item, assessment, threat_display):
                            continue

                    if query and not self._item_matches_filter(item, query, target_col):
                        continue

                    img_url = item.get("image_url", "")
                    iid = self.result_tree.insert("", "end", text="", image=ph, values=(
                        item.get("brand", ""),
                        item.get("product_type", ""),
                        item.get("title", ""),
                        item.get("item_id", ""),
                        normalize_price_string(item.get("price", "")),
                        item.get("seller", ""),
                        orig_display,
                        threat_display,
                        item.get("location", ""),
                        img_url,
                        item.get("url", ""),
                    ))

                    if is_thumbs and img_url:
                        self._fetch_inline_thumbnail(iid, img_url)

                self._update_result_count()
            except Exception as e:
                self._log(f"⚠ Error displaying results in table: {e}", error=True)
        self.after(0, _add)

    def _on_hide_benign_toggled(self):
        """Toggle Hide Benign filter, disabling Benign Only if enabled."""
        if hasattr(self, "filter_hide_benign_var") and self.filter_hide_benign_var.get():
            if hasattr(self, "filter_only_benign_var"):
                self.filter_only_benign_var.set(False)
        self._repopulate_results_table()

    def _on_only_benign_toggled(self):
        """Toggle Benign Only filter, disabling conflicting filters."""
        if hasattr(self, "filter_only_benign_var") and self.filter_only_benign_var.get():
            if hasattr(self, "filter_hide_benign_var"):
                self.filter_hide_benign_var.set(False)
            if hasattr(self, "filter_high_risk_var"):
                self.filter_high_risk_var.set(False)
        self._repopulate_results_table()

    def _update_result_count(self):
        """Standardize and synchronize result count display across all views."""
        total_count = len(self.results)
        vis_count = len(self.result_tree.get_children())
        selected_count = len(self.result_tree.selection())

        if selected_count > 0:
            if vis_count < total_count:
                self.result_count.set(f"{vis_count} / {total_count} listings ({selected_count} selected)")
            else:
                self.result_count.set(f"{total_count} listings ({selected_count} selected)")
        else:
            if vis_count < total_count:
                self.result_count.set(f"{vis_count} / {total_count} listings (filtered)")
            else:
                self.result_count.set(f"{total_count} listings")

    def _refresh_filter_dropdown_values(self):
        """Dynamically update marketplace and brand filter choices based on current session results."""
        if not hasattr(self, "filter_mkt_combo") or not hasattr(self, "filter_brand_combo"):
            return

        # 1. Marketplaces present in results
        mkts = set()
        for it in self.results:
            m = self._get_item_marketplace(it)
            if m and m != "Other":
                mkts.add(m)

        core_mkts = ["AliExpress", "eBay", "ManoMano", "Mercado Libre", "Printerval", "Redbubble", "Temu", "TikTok Shop", "Vinted", "Wish"]
        all_mkts = sorted(list(mkts.union(core_mkts)))
        mkt_list = ["All Marketplaces"] + all_mkts
        current_mkt = self.filter_mkt_var.get() if hasattr(self, "filter_mkt_var") else "All Marketplaces"
        self.filter_mkt_combo["values"] = mkt_list
        if current_mkt not in mkt_list:
            self.filter_mkt_var.set("All Marketplaces")

        # 2. Brands present in results + configured brands
        brands = set()
        for it in self.results:
            b = str(it.get("brand", "")).strip()
            if b and b not in ("Unknown", "(Select or type...)", "(No change)"):
                brands.add(b)

        if hasattr(self, "data_store"):
            try:
                if hasattr(self.data_store, "get_all_brands"):
                    for b in self.data_store.get_all_brands():
                        if b and str(b).strip():
                            brands.add(str(b).strip())
                elif hasattr(self.data_store, "get_brands"):
                    for b in self.data_store.get_brands().keys():
                        if b and str(b).strip():
                            brands.add(str(b).strip())
            except Exception:
                pass

        brand_list = ["All Brands"] + sorted(list(brands)) if brands else ["All Brands"]
        current_brand = self.filter_brand_var.get() if hasattr(self, "filter_brand_var") else "All Brands"
        self.filter_brand_combo["values"] = brand_list
        if current_brand not in brand_list:
            self.filter_brand_var.set("All Brands")

    def _repopulate_results_table(self):
        """Clear and refill result_tree from self.results honoring current filter."""
        self._refresh_filter_dropdown_values()
        self.result_tree.delete(*self.result_tree.get_children())
        query = self.filter_var.get().strip() if hasattr(self, "filter_var") else ""
        target_col = self.filter_col_var.get() if hasattr(self, "filter_col_var") else "Title"
        mkt_filter = self.filter_mkt_var.get().strip() if hasattr(self, "filter_mkt_var") else "All Marketplaces"
        brand_filter = self.filter_brand_var.get().strip() if hasattr(self, "filter_brand_var") else "All Brands"
        size_key = self.thumb_size_var.get() if hasattr(self, "thumb_size_var") else "Medium (100px)"
        cfg = THUMB_CONFIG.get(size_key, THUMB_CONFIG["Medium (100px)"])
        is_thumbs = (cfg["img_size"] > 0)
        ph = self._get_placeholder_thumb(cfg["img_size"]) if is_thumbs else ""

        suppressed_fluff_count = 0
        for item in self.results:
            if "product_type" not in item:
                item["product_type"] = ""

            # Evaluate Threat Intel from DataStore cache
            GENERIC_SELLER_PLACEHOLDERS = {"ebay seller", "unknown", "resolving...", "global search", "aliexpress global", "printerval creator", "printerval seller", "mercado libre seller", "mercado libre merchant", "tiktok shop merchant", "redbubble artist", "vinted user", "meli_seller_"}
            seller_clean = str(item.get("seller", "")).replace("🛡", "").replace("(Authorized)", "").strip()
            is_generic_seller = not seller_clean or any(g in seller_clean.lower() for g in GENERIC_SELLER_PLACEHOLDERS)
            
            cached_intel = self.data_store.get_seller_intel(seller_clean) if not is_generic_seller else None
            raw_origin = item.get("seller_origin") or (cached_intel.get("country") if (cached_intel and cached_intel.get("country") != "Unknown") else "")
            loc = item.get("location", "")

            assessment = self.data_store.compute_threat_assessment(raw_origin, loc, seller_name=seller_clean)
            
            orig_display = ""
            if raw_origin and raw_origin != "Unknown":
                orig_flag = self.data_store.COUNTRY_FLAGS.get(raw_origin.lower(), "🌍")
                orig_display = f"{orig_flag} {raw_origin}"
                item["seller_origin"] = raw_origin
            elif item.get("seller_origin") and item.get("seller_origin") != "Unknown":
                orig_flag = self.data_store.COUNTRY_FLAGS.get(item["seller_origin"].lower(), "🌍")
                orig_display = f"{orig_flag} {item['seller_origin']}"

            # If item already has a specialized visual or threat badge, preserve it
            if item.get("visual_benign"):
                threat_display = item.get("threat_badge", "🟢 Benign Packaging")
            elif item.get("visual_counterfeit"):
                threat_display = item.get("threat_badge", "🚨 Visual Counterfeit")
            elif item.get("threat_badge"):
                raw_tb = str(item["threat_badge"]).strip()
                if "\n" in raw_tb or len(raw_tb) > 60:
                    threat_display = assessment.get("badge", "") if ((raw_origin and raw_origin != "Unknown") or assessment.get("is_high_risk")) else ""
                    item["threat_badge"] = threat_display
                else:
                    threat_display = raw_tb
            elif assessment.get("is_high_risk"):
                threat_display = assessment.get("badge", "")
                item["threat_badge"] = threat_display
            elif raw_origin and raw_origin != "Unknown":
                threat_display = assessment.get("badge", "")
                item["threat_badge"] = threat_display
            else:
                threat_display = ""

            # Check Benign Filter (Hide Benign vs Show All vs Benign Only)
            b_mode = self.benign_filter_var.get() if hasattr(self, "benign_filter_var") else "🛡 Hide Benign"
            is_item_benign = item.get("visual_benign") or str(threat_display).startswith("🟢 Benign")
            if b_mode == "🟢 Benign Only" and not is_item_benign:
                continue
            elif b_mode == "🛡 Hide Benign" and is_item_benign:
                continue

            # Check High-Risk filter checkbox
            if hasattr(self, "filter_high_risk_var") and self.filter_high_risk_var.get():
                if not self._is_high_risk_item(item, assessment, threat_display):
                    continue

            # Check Marketplace filter dropdown
            if mkt_filter and mkt_filter != "All Marketplaces":
                item_mkt = self._get_item_marketplace(item)
                if item_mkt.lower() != mkt_filter.lower() and mkt_filter.lower() not in item_mkt.lower():
                    continue

            # Check Brand filter dropdown
            if brand_filter and brand_filter != "All Brands":
                item_brand = str(item.get("brand", "")).strip()
                if item_brand.lower() != brand_filter.lower():
                    continue

            if query and not self._item_matches_filter(item, query, target_col):
                continue

            img_url = item.get("image_url", "")
            iid = self.result_tree.insert("", "end", text="", image=ph, values=(
                item.get("brand", ""),
                item.get("product_type", ""),
                item.get("title", ""),
                item.get("item_id", ""),
                normalize_price_string(item.get("price", "")),
                item.get("seller", ""),
                orig_display,
                threat_display,
                item.get("location", ""),
                img_url,
                item.get("url", ""),
            ))

            if is_thumbs and img_url:
                self._fetch_inline_thumbnail(iid, img_url)

        if hasattr(self, "fluff_btn"):
            self.fluff_btn.config(text=f"💨 Show Suppressed Fluff ({suppressed_fluff_count})")

        self._update_result_count()

    def _sort_by_column(self, col):
        """Sort self.results by column with numeric/price intelligence and update headers."""
        if not self.results:
            return
        descending = self.sort_directions.get(col, False)
        self.sort_directions[col] = not descending
        field = self.field_map.get(col, col)

        def get_sort_key(item):
            val = item.get(field, "")
            if col in ("thumbnail", "#0"):
                return str(item.get("phash", ""))
            elif col == "price":
                m = re.search(r"[\d,]+(?:\.\d+)?", str(val))
                if m:
                    try:
                        return float(m.group(0).replace(",", ""))
                    except ValueError:
                        return 0.0
                return 0.0
            elif col == "item_id":
                try:
                    return int(val) if val else 0
                except ValueError:
                    return 0
            return str(val).lower()

        self.results.sort(key=get_sort_key, reverse=descending)
        self._repopulate_results_table()

        # Update table column headers with sort arrow
        for c in self.result_tree["columns"]:
            label = self.col_labels[c]
            if c == col:
                arrow = " ▼" if descending else " ▲"
                self.result_tree.heading(c, text=f"{label}{arrow}",
                                         command=lambda _c=c: self._sort_by_column(_c))
            else:
                self.result_tree.heading(c, text=label,
                                         command=lambda _c=c: self._sort_by_column(_c))

    def _remove_duplicates(self):
        """Deduplicate harvested listings based on Item ID (or URL)."""
        if not self.results:
            messagebox.showinfo("Deduplicate", "No results to deduplicate.")
            return

        initial_count = len(self.results)
        unique_results = []
        seen = set()

        for item in self.results:
            item_id = item.get("item_id")
            seller_str = str(item.get("seller", "")).strip().lower()
            dedup_key = f"{item_id}::{seller_str}" if item_id and seller_str and seller_str != "mercado libre seller" else (item_id or item.get("url"))
            if dedup_key and dedup_key not in seen:
                seen.add(dedup_key)
                unique_results.append(item)
            elif not dedup_key:
                unique_results.append(item)

        removed = initial_count - len(unique_results)
        self.results = unique_results
        self.seen_item_ids = seen
        self._repopulate_results_table()

        msg = f"Deduplication complete: Removed {removed} duplicate(s). {len(self.results)} unique listings remain."
        self._log(f"✂ {msg}")
        messagebox.showinfo("Deduplication", f"Removed {removed} duplicate listings.\n{len(self.results)} unique listings remain.")

    def _remove_selected_results(self):
        """Remove selected listings in the results table from session."""
        selected = self.result_tree.selection()
        if not selected:
            messagebox.showinfo("Select", "Select one or more rows in the results table to remove.")
            return

        removed_keys = set()
        for item_iid in selected:
            vals = self.result_tree.item(item_iid)["values"]
            if len(vals) > 3:
                item_id = str(vals[3]).strip()
                url = str(vals[8]).strip() if len(vals) > 8 else ""
                if item_id:
                    removed_keys.add(item_id)
                elif url:
                    removed_keys.add(url)
            self.result_tree.delete(item_iid)

        self.results = [
            item for item in self.results
            if str(item.get("item_id", "")).strip() not in removed_keys and
               str(item.get("url", "")).strip() not in removed_keys
        ]
        self.seen_item_ids = {
            item.get("item_id") or item.get("url") for item in self.results
            if item.get("item_id") or item.get("url")
        }
        self.result_count.set(f"{len(self.results)} listings")
        self._log(f"✕ Removed {len(selected)} selected listing(s). {len(self.results)} total remaining.")

    def _clear_results(self):
        if messagebox.askyesno("Clear", "Clear all harvested results?"):
            self.results.clear()
            self.seen_item_ids.clear()
            self.executed_jobs.clear()
            self.result_tree.delete(*self.result_tree.get_children())
            self.result_count.set("0 listings")
            self._hide_preview_popup()
            self._log("Results cleared.")

    def _get_item_by_tree_id(self, iid: str) -> Optional[dict]:
        """Lookup dictionary item in self.results by tree item id or item_id value."""
        if not iid or not self.result_tree.exists(iid):
            return None
        vals = self.result_tree.item(iid).get("values", [])
        if len(vals) > 3:
            item_id = str(vals[3]).strip()
            url = str(vals[10] if len(vals) > 10 else (vals[8] if len(vals) > 8 else "")).strip()
            for it in self.results:
                if (item_id and str(it.get("item_id", "")).strip() == item_id) or (url and str(it.get("url", "")).strip() == url):
                    return it
        return None

    def _open_url(self, ev=None):
        sel = self.result_tree.focus()
        if not sel:
            selected = self.result_tree.selection()
            if selected: sel = selected[0]
        if sel:
            values = self.result_tree.item(sel)["values"]
            listing_url = values[10] if len(values) > 10 else (values[8] if len(values) > 8 else "")
            if listing_url:
                webbrowser.open(listing_url)

    def _on_result_tree_double_click(self, event):
        """Intelligent double click: open browser if clicked on URL or image, otherwise open inline edit modal."""
        col_id = self.result_tree.identify_column(event.x)
        # Column #0 is thumbnail, #11/#9 is URL -> open browser
        if col_id in ("#0", "#11", "#9"):
            self._open_url()
        else:
            self._edit_selected_listing()

    def _edit_selected_listing(self):
        """Open an analyst edit dialog to modify Brand, Product Type, Seller, Price, or Title for selected listing(s)."""
        selected_ids = self.result_tree.selection()
        if not selected_ids:
            messagebox.showinfo("Edit Listing", "Please select a listing from the table to edit.")
            return

        target_items = [self._get_item_by_tree_id(iid) for iid in selected_ids if self._get_item_by_tree_id(iid)]
        if not target_items:
            return

        first_item = target_items[0]
        is_multi = len(target_items) > 1

        t = self.theme
        win = tk.Toplevel(self)
        win.title("Quick Edit Listing Values" if not is_multi else f"Batch Edit {len(target_items)} Selected Listings")
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        win.transient(self)
        self._apply_dark_titlebar(win)
        self._center_window(win, 520, 430)
        win.grab_set()
        win.focus_force()

        tk.Label(win, text="✏ Edit Listing Information", bg=t["bg"], fg=t["accent"],
                 font=("Segoe UI", 11, "bold")).pack(pady=(12, 4))
        
        sub_txt = f"Editing Item #{first_item.get('item_id', '')}" if not is_multi else f"Applying updates across {len(target_items)} selected listings"
        tk.Label(win, text=sub_txt, bg=t["bg"], fg=t["subtext"], font=FONT_SM).pack(pady=(0, 10))

        frame = tk.Frame(win, bg=t["bg"])
        frame.pack(fill="both", expand=True, padx=20)

        # 1. Brand
        tk.Label(frame, text="Brand / Trademark:", bg=t["bg"], fg=t["text"], font=FONT_SM).grid(row=0, column=0, sticky="w", pady=4)
        brand_var = tk.StringVar(value=first_item.get("brand", ""))
        known_brands = sorted(list(self.data_store.get_brands().keys()))
        brand_cb = ttk.Combobox(frame, textvariable=brand_var, values=known_brands, font=FONT_SM)
        brand_cb.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 2. Product Type
        tk.Label(frame, text="Product Category:", bg=t["bg"], fg=t["text"], font=FONT_SM).grid(row=1, column=0, sticky="w", pady=4)
        pt_var = tk.StringVar(value=first_item.get("product_type", ""))
        known_pts = ["Airbag Covers", "Airbag Components", "Emblems", "Decals", "Wheel Caps", "Exterior Lighting", "Exterior Parts", "Brakes", "Ignition Systems", "Oil Filters", "Air Filters", "Merchandise", "Accessories"]
        pt_cb = ttk.Combobox(frame, textvariable=pt_var, values=known_pts, font=FONT_SM)
        pt_cb.grid(row=1, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 3. Seller Name
        tk.Label(frame, text="Seller Name / Store:", bg=t["bg"], fg=t["text"], font=FONT_SM).grid(row=2, column=0, sticky="w", pady=4)
        seller_var = tk.StringVar(value=first_item.get("seller", ""))
        seller_ent = tk.Entry(frame, textvariable=seller_var, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], relief="flat", font=FONT_SM)
        seller_ent.grid(row=2, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 4. Price
        tk.Label(frame, text="Price:", bg=t["bg"], fg=t["text"], font=FONT_SM).grid(row=3, column=0, sticky="w", pady=4)
        price_var = tk.StringVar(value=first_item.get("price", ""))
        price_ent = tk.Entry(frame, textvariable=price_var, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], relief="flat", font=FONT_SM)
        price_ent.grid(row=3, column=1, sticky="ew", pady=4, padx=(8, 0))

        # 5. Title (Single item only)
        title_var = tk.StringVar(value=first_item.get("title", ""))
        if not is_multi:
            tk.Label(frame, text="Listing Title:", bg=t["bg"], fg=t["text"], font=FONT_SM).grid(row=4, column=0, sticky="w", pady=4)
            title_ent = tk.Entry(frame, textvariable=title_var, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], relief="flat", font=FONT_SM)
            title_ent.grid(row=4, column=1, sticky="ew", pady=4, padx=(8, 0))

        frame.columnconfigure(1, weight=1)

        btn_row = tk.Frame(win, bg=t["bg"])
        btn_row.pack(fill="x", padx=20, pady=(16, 12))

        def _save():
            new_b = brand_var.get().strip()
            new_pt = pt_var.get().strip()
            new_s = seller_var.get().strip()
            new_p = price_var.get().strip()
            new_t = title_var.get().strip()

            for item in target_items:
                if new_b: item["brand"] = new_b
                if new_pt: item["product_type"] = new_pt
                if new_s: item["seller"] = new_s
                if new_p: item["price"] = new_p
                if not is_multi and new_t: item["title"] = new_t

            self._repopulate_results_table()
            self._log(f"✏ Updated values for {len(target_items)} listing(s) in results table.")
            win.destroy()

        self._btn(btn_row, "💾 Apply Changes", _save, accent=True).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._btn(btn_row, "Cancel", win.destroy).pack(side="right")
        win.bind("<Return>", lambda e: _save())

    def _rescrape_selected_listings(self):
        """Re-scrape live listing pages for selected rows to backfill/refresh missing thumbnails, live prices, and seller handles."""
        selected_ids = self.result_tree.selection()
        if not selected_ids:
            messagebox.showinfo("Rescrape Listings", "Please select one or more listings from the results table to refresh.")
            return

        target_items = []
        for iid in selected_ids:
            it = self._get_item_by_tree_id(iid)
            if it:
                target_items.append((iid, it))

        if not target_items:
            return

        is_headless = self.headless_var.get() if hasattr(self, "headless_var") else True
        self._log(f"🔄 Starting targeted live refresh for {len(target_items)} selected listing(s)...")
        self._status(f"Refreshing {len(target_items)} listings...")
        self.running = True
        self.stop_event.clear()
        self.stop_btn.config(state="normal")
        self.progress.start()

        def _worker():
            import batch_importer
            updated_count = 0
            for idx, (iid, item) in enumerate(target_items, 1):
                if self.stop_event.is_set():
                    self._log("⏹ Live refresh halted by analyst.")
                    break
                url = item.get("url", "")
                if not url:
                    continue
                try:
                    res = batch_importer.fetch_single_listing(url, headless=is_headless)
                    if res:
                        if res.get("image_url"):
                            item["image_url"] = res["image_url"]
                        if res.get("price") and res.get("price") not in ("$0.00", ""):
                            item["price"] = res["price"]
                        if res.get("seller") and res.get("seller") not in ("Unknown", "eBay Seller", "E-Commerce Merchant"):
                            s_handle = res["seller"]
                            item["seller"] = s_handle
                            cached = self.data_store.get_seller_intel(s_handle)
                            if cached and cached.get("country") and cached.get("country") != "Unknown":
                                item["seller_origin"] = cached["country"]
                            elif hasattr(self, "scraper") and hasattr(self.scraper, "resolve_seller_country"):
                                try:
                                    c_info = self.scraper.resolve_seller_country(s_handle)
                                    if c_info and c_info.get("country") and c_info["country"] != "Unknown":
                                        item["seller_origin"] = c_info["country"]
                                        self.data_store.set_seller_intel(s_handle, c_info["country"], member_since=c_info.get("member_since", ""))
                                except Exception:
                                    pass
                            
                            # Propagate origin to all matching listings from this seller in table
                            if item.get("seller_origin"):
                                self._propagate_seller_intel_to_results(s_handle, item["seller_origin"])
                        if res.get("title") and not res.get("title").startswith("Imported Listing") and not res.get("title").startswith("eBay Item #"):
                            item["title"] = res["title"]
                        if res.get("location") and res.get("location") not in ("Unknown", ""):
                            item["location"] = res["location"]
                        if res.get("brand") and res.get("brand") != "Automotive & Consumer Brands" and item.get("brand") in ("Unknown", "Automotive & Consumer Brands", "", None):
                            item["brand"] = res["brand"]
                        if res.get("product_type") and res.get("product_type") != "Accessories" and item.get("product_type") in ("Accessories", "", None):
                            item["product_type"] = res["product_type"]

                        # Re-calculate threat assessment badge
                        assessment = self.data_store.compute_threat_assessment(
                            item.get("seller_origin", ""),
                            item.get("location", "")
                        )
                        item["threat_badge"] = assessment.get("badge", item.get("threat_badge", "Unresolved"))
                        item["threat_score"] = assessment.get("score", item.get("threat_score", "UNKNOWN"))
                        updated_count += 1
                        self.after(0, lambda c=idx, t=len(target_items): self._status(f"Refreshed {c}/{t} listings..."))
                except Exception as e:
                    logger.debug(f"Rescrape error on {url}: {e}")

            def _finish():
                self.running = False
                self.stop_btn.config(state="disabled")
                self.progress.stop()
                self._repopulate_results_table()
                self._log(f"✅ Finished live refresh for {updated_count}/{len(target_items)} listing(s).")
                self._status(f"Refresh complete: {updated_count} updated.")
                self._show_themed_info("Refresh Complete", f"Successfully refreshed details and thumbnails for {updated_count} listing(s)!", icon="✓")

            self.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _propagate_seller_intel_to_results(self, seller: str, country: str, threat_badge: str = ""):
        """Propagate resolved seller corporate origin & threat assessment across all active listings in session results."""
        if not seller or not country or country == "Unknown":
            return 0
        updated = 0
        s_clean = seller.strip().lower()
        for it in self.results:
            if it.get("seller", "").strip().lower() == s_clean:
                it["seller_origin"] = country
                if not threat_badge:
                    assessment = self.data_store.compute_threat_assessment(country, it.get("location", ""))
                    it["threat_badge"] = assessment.get("badge", it.get("threat_badge", "Unresolved"))
                    it["threat_score"] = assessment.get("score", it.get("threat_score", "UNKNOWN"))
                else:
                    it["threat_badge"] = threat_badge
                updated += 1
        return updated

    def _show_result_context_menu(self, event):
        """Right-click context menu on results table rows."""
        row_id = self.result_tree.identify_row(event.y)
        if row_id:
            # If right clicked item not in selection, select it
            if row_id not in self.result_tree.selection():
                self.result_tree.selection_set(row_id)

        selected = self.result_tree.selection()
        if not selected:
            return

        t = self.theme
        menu = tk.Menu(self, tearoff=0, bg=t["panel"], fg=t["text"],
                       activebackground=t["accent"], activeforeground="black" if t.get("name","").startswith("⚡") else "white")

        # Check if selected rows contain POD listings (Printerval, Redbubble, etc.)
        has_pod_items = False
        for item_iid in selected:
            vals = self.result_tree.item(item_iid)["values"]
            if len(vals) > 8:
                mkt = str(vals[8]).strip().lower() if len(vals) > 8 else ""
                url_val = str(vals[10]).strip().lower() if len(vals) > 10 else ""
                if "printerval" in mkt or "printerval.com" in url_val or "redbubble" in mkt or "redbubble.com" in url_val:
                    has_pod_items = True
                    break

        has_redbubble_items = False
        for item_iid in selected:
            vals = self.result_tree.item(item_iid)["values"]
            if len(vals) > 8:
                mkt = str(vals[8]).strip().lower() if len(vals) > 8 else ""
                url_val = str(vals[10]).strip().lower() if len(vals) > 10 else ""
                if "redbubble" in mkt or "redbubble.com" in url_val:
                    has_redbubble_items = True
                    break

        if has_pod_items:
            menu.add_command(label="👕 Expand POD Design Variants (50-74 Products)", font=("Segoe UI", 9, "bold"), command=self._expand_pod_variants_selected)
        if has_redbubble_items:
            menu.add_command(label="🎨 Sweep Artist's Full Portfolio (Find All Designs)", font=("Segoe UI", 9, "bold"), command=self._sweep_redbubble_artist_selected)
        if has_pod_items or has_redbubble_items:
            menu.add_separator()

        menu.add_command(label="✏ Edit Listing Values (F2)", command=self._edit_selected_listing)
        menu.add_command(label="🔄 Refresh / Rescrape Selected", command=self._rescrape_selected_listings)
        menu.add_separator()
        menu.add_command(label="💾 Export to Excel (Ctrl+E)", command=self._export)
        menu.add_command(label="🌐 Multi-Locale Expander", command=self._open_multi_locale_expander)
        menu.add_separator()
        menu.add_command(label="🔗 Connected Seller Network Hunter", command=self._open_connected_network_scanner)

        # ── Nested Reverse Visual Search Submenu ──
        vis_menu = tk.Menu(menu, tearoff=0, bg=t["panel"], fg=t["text"],
                           activebackground=t["accent"], activeforeground="black" if t.get("name","").startswith("⚡") else "white")
        
        vis_menu.add_command(
            label="⚡ Quick Sweep (Current Platform & Active Locale)",
            font=("Segoe UI", 9, "bold"),
            command=self._reverse_visual_search_selected
        )
        vis_menu.add_separator()

        # Vinted Submenu
        vinted_sub = tk.Menu(vis_menu, tearoff=0, bg=t["panel"], fg=t["text"],
                             activebackground=t["accent"], activeforeground="black" if t.get("name","").startswith("⚡") else "white")
        vinted_locales = [
            ("🌍 All Locales (Global Cross-Border)", "All"),
            ("🇬🇧 United Kingdom", "UK"),
            ("🇺🇸 United States", "US"),
            ("🇪🇸 Spain", "ES"),
            ("🇫🇷 France", "FR"),
            ("🇩🇪 Germany", "DE"),
            ("🇮🇹 Italy", "IT"),
            ("🇵🇱 Poland", "PL"),
            ("🇳🇱 Netherlands", "NL"),
            ("🇧🇪 Belgium", "BE"),
        ]
        for v_label, v_code in vinted_locales:
            vinted_sub.add_command(
                label=v_label,
                command=lambda vc=v_code: self._reverse_visual_search_selected(marketplace="Vinted", region=vc)
            )
        vis_menu.add_cascade(label="👗 Vinted Locales ▾", menu=vinted_sub)

        # Mercado Libre Submenu
        meli_sub = tk.Menu(vis_menu, tearoff=0, bg=t["panel"], fg=t["text"],
                           activebackground=t["accent"], activeforeground="black" if t.get("name","").startswith("⚡") else "white")
        meli_locales = [
            ("🇲🇽 Mexico", "Mexico"),
            ("🇧🇷 Brazil", "Brazil"),
            ("🇦🇷 Argentina", "Argentina"),
            ("🇨🇴 Colombia", "Colombia"),
            ("🇨🇱 Chile", "Chile"),
            ("🇵🇪 Peru", "Peru"),
            ("🌎 All Latin America", "All Latin America"),
        ]
        for m_label, m_code in meli_locales:
            meli_sub.add_command(
                label=m_label,
                command=lambda mc=m_code: self._reverse_visual_search_selected(marketplace="Mercado Libre", region=mc)
            )
        vis_menu.add_cascade(label="🛍 Mercado Libre Countries ▾", menu=meli_sub)

        # Other platforms
        vis_menu.add_command(label="🛒 eBay (Global)", command=lambda: self._reverse_visual_search_selected(marketplace="eBay"))
        vis_menu.add_command(label="🌐 AliExpress.com", command=lambda: self._reverse_visual_search_selected(marketplace="AliExpress"))
        vis_menu.add_command(label="🌠 Wish.com", command=lambda: self._reverse_visual_search_selected(marketplace="Wish"))
        vis_menu.add_command(label="🟠 Temu.com", command=lambda: self._reverse_visual_search_selected(marketplace="Temu"))

        menu.add_cascade(label="📸 Reverse Visual Search (Sweep by Photo) ▾", menu=vis_menu)

        menu.add_command(label="🟢 Mark Packaging as Known Benign", command=self._mark_selected_as_visual_benign)
        menu.add_command(label="🔴 Mark Photo as Known Counterfeit", command=self._mark_selected_as_visual_counterfeit)
        menu.add_command(label="🏪 Add Seller to Stores Box", command=self._add_selected_result_seller_to_stores)
        menu.add_command(label="🌍 Resolve Threat Intel & Origin", command=self._enrich_seller_threat_intel)
        menu.add_command(label="🛡 Whitelist Seller (Authorized Dealer)", command=self._whitelist_selected_result_seller)
        menu.add_separator()
        menu.add_command(label="☑ Select All (Ctrl+A)", command=self._select_all_results)
        menu.add_command(label="🌐 Open Listing in Browser", command=lambda: self._open_url(None))
        menu.add_command(label="📋 Copy Selected URLs", command=self._copy_selected_urls)
        menu.add_command(label="📋 Copy All URLs", command=self._copy_all_listing_urls)
        menu.add_command(label="🏪 Enrich Selected Seller Names", command=self._enrich_sellers)
        menu.add_separator()
        menu.add_command(label="✕ Remove Selected (Del)", command=self._remove_selected_results)
        menu.add_command(label="🗑 Clear All Results", command=self._clear_results)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _is_high_risk_item(self, item: dict, assessment: dict, threat_display: str) -> bool:
        """Centralized multi-platform evaluation to isolate genuine high-threat items."""
        # 1. 3PL Forwarding Hubs or High-Risk Foreign Origin
        if assessment.get("is_high_risk") or assessment.get("is_3pl_hub"):
            return True
        # 2. Mathematical Visual Clone / Known Counterfeit
        if item.get("visual_counterfeit"):
            return True
        # 3. Vinted Heuristics, Burner Handles, and High-Threat Badges
        tb = str(threat_display or item.get("threat_badge", "")).lower()
        if "🚨" in tb or "risk (high)" in tb or "counterfeit" in tb or "burner" in tb or "drop-ship" in tb or "nwt" in tb:
            return True
        # 4. Numerical Threat Score >= 75
        try:
            if float(item.get("threat_score", 0) or 0) >= 75:
                return True
        except Exception:
            pass
        return False

    def _show_themed_info(self, title: str, message: str, icon: str = "ℹ", parent=None):
        """Display an Apollo theme-adaptive modal dialog instead of native stark-white OS messagebox."""
        t = self.theme
        win = tk.Toplevel(parent or self)
        win.title(title)
        win.configure(bg=t["bg"])
        win.resizable(False, False)
        win.transient(parent or self)
        win.grab_set()
        self._apply_dark_titlebar(win)
        self._load_app_icon(win)

        card = tk.Frame(win, bg=t["panel"], padx=20, pady=16, highlightbackground=t.get("border", "#334155"), highlightthickness=1)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        # Header row with theme icon and title
        hdr = tk.Frame(card, bg=t["panel"])
        hdr.pack(fill="x", pady=(0, 8))

        tk.Label(hdr, text=icon, font=("Segoe UI", 16), bg=t["panel"], fg=t.get("accent", "#38bdf8")).pack(side="left", padx=(0, 8))
        tk.Label(hdr, text=title, font=FONT_HEAD, bg=t["panel"], fg=t.get("text", "#ffffff")).pack(side="left")

        div = tk.Frame(card, bg=t.get("border", "#334155"), height=1)
        div.pack(fill="x", pady=(0, 10))

        # Message body
        tk.Label(card, text=message, font=FONT_NORM, bg=t["panel"], fg=t.get("text", "#ffffff"), justify="left", wraplength=400).pack(anchor="w", pady=(0, 14))

        # OK Button
        btn_row = tk.Frame(card, bg=t["panel"])
        btn_row.pack(fill="x")
        btn = tk.Button(
            btn_row,
            text="OK",
            font=FONT_BOLD,
            bg=t.get("accent_btn", t.get("accent", "#0284c7")),
            fg="#ffffff" if not str(t.get("name", "")).startswith("🪙") else "#0A0B0E",
            activebackground=t.get("accent2", "#38bdf8"),
            relief="flat",
            padx=18,
            pady=3,
            cursor="hand2",
            command=win.destroy
        )
        btn.pack(side="right")
        btn.focus_set()
        win.bind("<Return>", lambda e: win.destroy())
        win.bind("<Escape>", lambda e: win.destroy())

        self._center_window(win, 460, 210)

    def _open_session_vault_modal(self):
        """Open the Universal Marketplace Session & Account Vault Modal."""
        SessionVaultModal(self, self.theme, self.session_vault)

    def _open_product_type_manager(self):
        """Open the Product Type & Industry Taxonomy Manager Modal."""
        if self._win_product_type and self._win_product_type.winfo_exists():
            self._win_product_type.lift()
            self._win_product_type.focus_force()
            return
        self._win_product_type = ProductTypeModal(self, self.theme, self.data_store)

    def _open_field_guide_modal(self):
        """Open the searchable Analyst Field Guide & Threat Intelligence Glossary."""
        if self._win_field_guide and self._win_field_guide.winfo_exists():
            self._win_field_guide.lift()
            self._win_field_guide.focus_force()
            return
        self._win_field_guide = FieldGuideModal(self, self.theme)

    def _attach_analyst_tooltips(self):
        """Attach theme-adaptive hover tooltips across Apollo UI for analyst onboarding."""
        t_func = lambda: self.theme
        e_func = lambda: self.show_hints_var.get() if hasattr(self, "show_hints_var") else True

        if hasattr(self, "filter_mkt_combo"):
            add_tooltip(self.filter_mkt_combo, "Filter results by specific Marketplace / Platform (e.g. Printerval, Redbubble, eBay, TikTok Shop, AliExpress).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "filter_brand_combo"):
            add_tooltip(self.filter_brand_combo, "Filter results by specific Brand (e.g. Toyota, Ford, GM). Dynamically populates from loaded results.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "filter_col_combo"):
            add_tooltip(self.filter_col_combo, "Target live search to a specific column (e.g. Title, Seller, Threat Intel, Marketplace).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "filter_entry"):
            add_tooltip(self.filter_entry, "Live filter results. Type words to search. Use +term for mandatory inclusion, -term for exclusion (e.g. 'fleece +jacket -pants').", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "benign_filter_combo"):
            add_tooltip(self.benign_filter_combo, "Benign Packaging Filter:\n• 🛡 Hide Benign: Filter out authentic packaging (Default)\n• 📁 Show All: Display all listings\n• 🟢 Benign Only: Isolate verified authentic stock photos", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "st_cb"):
            add_tooltip(self.st_cb, "Automatically suppresses multi-brand title spam and non-enforceable universal accessory fluff while preserving 100% of high-risk components.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "fluff_btn"):
            add_tooltip(self.fluff_btn, "Toggle audit view of suppressed universal compatibility listings.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "hr_cb"):
            add_tooltip(self.hr_cb, "Isolate confirmed 3PL drop-ship hubs, Vinted NWT replica risks, burner handles, and visual clones in 1 click.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "hb_cb"):
            add_tooltip(self.hb_cb, "Hide verified authentic packaging matched against the Green Catalog.", theme_provider=t_func, is_enabled_callback=e_func)
        
        if hasattr(self, "btn_export"):
            add_tooltip(self.btn_export, "Export all current results to Excel (.xlsx) matching Genesis Upload template (Ctrl+E).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_multi_loc"):
            add_tooltip(self.btn_multi_loc, "Project selected listings across international marketplaces (UK, DE, AU, Latin America, Europe).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_copy_urls"):
            add_tooltip(self.btn_copy_urls, "Copy all listing URLs in the results table to clipboard.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_threat_enrich"):
            add_tooltip(self.btn_threat_enrich, "Resolve seller country origin and identify 3PL drop-shipping forwarding hubs.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_network_scan"):
            add_tooltip(self.btn_network_scan, "Scan for connected seller syndicates sharing phone, email, or physical addresses.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_rescrape"):
            add_tooltip(self.btn_rescrape, "Live refresh highlighted rows to fetch new photos, prices, titles, and active status (F5).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_edit_item"):
            add_tooltip(self.btn_edit_item, "Modify Brand, Category, Seller, Price, or Title in place (F2 / Double-Click).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_enrich_sellers"):
            add_tooltip(self.btn_enrich_sellers, "Discover and populate missing merchant/storefront names across marketplaces.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_remove_item"):
            add_tooltip(self.btn_remove_item, "Remove selected listings from current session (Delete).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_clear_res"):
            add_tooltip(self.btn_clear_res, "Clear all harvested listings and reset current session.", theme_provider=t_func, is_enabled_callback=e_func)

        if hasattr(self, "btn_guide"):
            add_tooltip(self.btn_guide, "Open Analyst Operations Guide, Feature Reference & Search Syntax (F1).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_visual"):
            add_tooltip(self.btn_visual, "Open Visual Threat Catalog & Benign Packaging Manager (F2).", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_registry"):
            add_tooltip(self.btn_registry, "Open Enforcement Registry to track and export legal takedown notices.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_whitelist"):
            add_tooltip(self.btn_whitelist, "Manage whitelisted brand partners and authorized dealer storefronts.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "btn_import"):
            add_tooltip(self.btn_import, "Import listing URLs from external spreadsheets (.xlsx, .csv) or text files.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "settings_mb"):
            add_tooltip(self.settings_mb, "Configure themes, toggle column visibility, sound chimes, and hints.", theme_provider=t_func, is_enabled_callback=e_func)
        if hasattr(self, "store_text"):
            add_tooltip(self.store_text, "Target storefront usernames or full profile URLs to sweep (one per line).", theme_provider=t_func, is_enabled_callback=e_func)

    def _toggle_column_visibility(self, col_key: str):
        """Handle toggle of a single column's visibility."""
        is_vis = self.col_vis_vars[col_key].get()
        self.data_store.set_single_column_visibility(col_key, is_vis)
        self._apply_column_visibility()

    def _apply_column_visibility(self):
        """Apply active column visibility settings to result_tree displaycolumns."""
        vis = self.data_store.get_column_visibility()
        display_cols = [c for c in self.all_table_cols if vis.get(c, True)]
        if not display_cols:
            display_cols = ["title"]
        try:
            self.result_tree["displaycolumns"] = display_cols
        except Exception as e:
            logger.debug(f"Error updating displaycolumns: {e}")

    def _open_analyst_guide_modal(self):
        """Open the interactive Analyst Operations Guide & Field Reference (F1)."""
        self._open_field_guide_modal()

    def _rescan_visual_matches(self):
        """Re-evaluate all current session listings against the Visual Catalog using the active sensitivity threshold."""
        if not self.results:
            messagebox.showinfo("Re-Scan Visual Matches", "No listings in current session to re-scan.")
            return

        matched_count = 0
        thresh = getattr(self.visual_catalog, "match_threshold", 6)
        for itm in self.results:
            img_url = itm.get("image_url", "")
            pil_img = self.raw_img_cache.get(img_url)
            if pil_img:
                v_match = self.visual_catalog.match_image(pil_img, max_distance=thresh)
                if v_match:
                    matched_count += 1
                    if v_match["type"] == "benign":
                        itm["threat_badge"] = f"🟢 Benign: {v_match['label']}"
                        itm["visual_benign"] = True
                    elif v_match["type"] == "counterfeit":
                        itm["threat_badge"] = f"🚨 Visual Counterfeit ({v_match['similarity_pct']}%)"
                        itm["threat_score"] = max(itm.get("threat_score", 0), 95)
                        itm["visual_counterfeit"] = True

        self._repopulate_results_table()
        self._log(f"🖼 Re-evaluated visual matches across session ({matched_count} listings matched with threshold {thresh}).")
        self._show_themed_info("Re-Scan Complete", f"Re-evaluated {len(self.results)} listings with Sensitivity Threshold ({thresh}).\n\nFound {matched_count} visual packaging match(es)!", icon="🖼")

    def _export_intel_pack_dialog(self):
        """Interactive dialog to export an Analyst Intelligence Pack (.apollo)."""
        import intel_pack_manager
        t = self.theme
        win = tk.Toplevel(self)
        win.title("📦 Export Analyst Intelligence Pack (.apollo)")
        win.geometry("520x440")
        win.resizable(False, False)
        win.configure(bg=t["bg"])
        win.transient(self)
        win.grab_set()

        self._apply_dark_titlebar(win)
        self._load_app_icon(win)
        self._center_window(win, 520, 440)

        card = tk.Frame(win, bg=t["panel"], padx=18, pady=16, relief="solid", bd=1)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(card, text="📦 Export Analyst Intelligence Pack", font=("Segoe UI", 12, "bold"),
                 bg=t["panel"], fg=t["accent"]).pack(anchor="w")
        tk.Label(card, text="Package your brands, exclusion filters, authorized dealer whitelists,\nand visual threat catalogs to share with other analysts or sync across machines.",
                 font=FONT_SM, bg=t["panel"], fg=t["subtext"], justify="left").pack(anchor="w", pady=(2, 10))

        # Scope Selection
        tk.Label(card, text="Export Scope / Client Niche:", font=FONT_BOLD, bg=t["panel"], fg=t["text"]).pack(anchor="w", pady=(4, 2))
        scope_var = tk.StringVar(value="Full Profile (All Brands & Components)")
        all_brands = sorted(list(self.data_store.get_brands().keys()))
        scope_options = ["Full Profile (All Brands & Components)", "Visual Library Only", "Brand Library & Exclusions Only", "Authorized Whitelist Only"] + [f"Brand: {b}" for b in all_brands]
        
        scope_combo = ttk.Combobox(card, textvariable=scope_var, values=scope_options, state="readonly", font=FONT_NORM)
        scope_combo.pack(fill="x", pady=4)

        # Author / Analyst Name
        tk.Label(card, text="Analyst / Author Name:", font=FONT_BOLD, bg=t["panel"], fg=t["text"]).pack(anchor="w", pady=(8, 2))
        author_var = tk.StringVar(value=self.data_store.get_setting("analyst_name", "Senior Brand Protection Analyst"))
        author_ent = tk.Entry(card, textvariable=author_var, font=FONT_NORM, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"])
        author_ent.pack(fill="x", pady=4)

        # Notes / Description
        tk.Label(card, text="Pack Notes / Client Context:", font=FONT_BOLD, bg=t["panel"], fg=t["text"]).pack(anchor="w", pady=(8, 2))
        notes_var = tk.StringVar(value="Master Brand Portfolio & Threat Intelligence Pack")
        notes_ent = tk.Entry(card, textvariable=notes_var, font=FONT_NORM, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"])
        notes_ent.pack(fill="x", pady=4)

        def _do_export():
            chosen_scope = scope_var.get()
            selected_brands = None
            if chosen_scope.startswith("Brand: "):
                b_target = chosen_scope.replace("Brand: ", "").strip()
                selected_brands = [b_target]
                clean_scope_name = b_target.replace(" ", "_")
                default_fn = f"apollo_{clean_scope_name}_intel_pack.apollo"
            else:
                default_fn = "apollo_master_intel_pack.apollo"

            out_path = filedialog.asksaveasfilename(
                parent=win,
                title="Save Analyst Intelligence Pack",
                defaultextension=".apollo",
                filetypes=[("Apollo Intelligence Pack", "*.apollo"), ("Zip Archive", "*.zip")],
                initialfile=default_fn
            )
            if not out_path:
                return

            try:
                manifest = intel_pack_manager.IntelPackManager.export_pack(
                    output_filepath=out_path,
                    data_store=self.data_store,
                    visual_catalog=self.visual_catalog,
                    scope=chosen_scope,
                    selected_brands=selected_brands,
                    author=author_var.get().strip() or "Apollo Analyst",
                    notes=notes_var.get().strip()
                )
                counts = manifest.get("counts", {})
                msg = f"Successfully exported Intelligence Pack to:\n{out_path}\n\n" \
                      f"• Brands: {counts.get('brands')}\n" \
                      f"• Presets: {counts.get('presets')}\n" \
                      f"• Exclusions: {counts.get('exclusions')}\n" \
                      f"• Whitelisted Dealers: {counts.get('whitelist_dealers')}\n" \
                      f"• Visual Threat Thumbnails: {counts.get('visual_thumbnails')}"
                self._log(f"📦 Exported Apollo Intelligence Pack ({chosen_scope}) to: {out_path}")
                win.destroy()
                messagebox.showinfo("Export Successful", msg)
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed exporting pack: {e}", parent=win)

        btn_row = tk.Frame(card, bg=t["panel"])
        btn_row.pack(fill="x", pady=(18, 0))
        self._btn(btn_row, "📦 Create & Export Pack", _do_export, accent=True).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._btn(btn_row, "Cancel", win.destroy).pack(side="right")

    def _import_intel_pack_dialog(self):
        """Interactive dialog to import an Analyst Intelligence Pack (.apollo)."""
        import intel_pack_manager
        t = self.theme

        pack_fp = filedialog.askopenfilename(
            parent=self,
            title="Select Apollo Intelligence Pack (.apollo / .zip)",
            filetypes=[("Apollo Intelligence Pack", "*.apollo;*.zip"), ("All Files", "*.*")]
        )
        if not pack_fp:
            return

        try:
            manifest = intel_pack_manager.IntelPackManager.inspect_pack(pack_fp)
        except Exception as e:
            messagebox.showerror("Invalid Package", f"Failed inspecting package: {e}")
            return

        win = tk.Toplevel(self)
        win.title("📥 Import Analyst Intelligence Pack")
        win.geometry("540x460")
        win.resizable(False, False)
        win.configure(bg=t["bg"])
        win.transient(self)
        win.grab_set()

        self._apply_dark_titlebar(win)
        self._load_app_icon(win)
        self._center_window(win, 540, 460)

        card = tk.Frame(win, bg=t["panel"], padx=18, pady=16, relief="solid", bd=1)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(card, text="📥 Import Analyst Intelligence Pack", font=("Segoe UI", 12, "bold"),
                 bg=t["panel"], fg=t["accent"]).pack(anchor="w")
        
        info_text = f"Pack Scope: {manifest.get('scope', 'Full Profile')}\n" \
                    f"Author: {manifest.get('author', 'Analyst')}\n" \
                    f"Created: {manifest.get('created_at', 'Unknown')}\n" \
                    f"Notes: {manifest.get('notes', 'None')}"
        tk.Label(card, text=info_text, font=FONT_NORM, bg=t["entry_bg"], fg=t["text"],
                 padx=10, pady=8, relief="solid", bd=1, justify="left").pack(fill="x", pady=(8, 10))

        counts = manifest.get("counts", {})
        counts_text = f"📦 Package Contents:\n" \
                      f"  • {counts.get('brands', 0)} Brands & Models\n" \
                      f"  • {counts.get('presets', 0)} Saved Sweep Presets\n" \
                      f"  • {counts.get('exclusions', 0)} Global Negative Exclusions\n" \
                      f"  • {counts.get('whitelist_dealers', 0)} Authorized Dealerships\n" \
                      f"  • {counts.get('visual_catalog_entries', 0)} Visual Threat Cards ({counts.get('visual_thumbnails', 0)} thumbnails)"
        tk.Label(card, text=counts_text, font=FONT_NORM, bg=t["panel"], fg=t["text"], justify="left").pack(anchor="w", pady=(0, 10))

        merge_mode_var = tk.StringVar(value="merge")
        tk.Radiobutton(card, text="🔗 Merge with Existing Library (Recommended — preserves your local entries)",
                       variable=merge_mode_var, value="merge", bg=t["panel"], fg=t["text"],
                       selectcolor=t["entry_bg"], activebackground=t["panel"], font=FONT_SM).pack(anchor="w", pady=2)
        tk.Radiobutton(card, text="⚡ Fresh Replace (Overwrites local duplicates with package items)",
                       variable=merge_mode_var, value="replace", bg=t["panel"], fg=t["danger"],
                       selectcolor=t["entry_bg"], activebackground=t["panel"], font=FONT_SM).pack(anchor="w", pady=2)

        def _do_import():
            mode = merge_mode_var.get()
            try:
                res = intel_pack_manager.IntelPackManager.import_pack(
                    pack_filepath=pack_fp,
                    data_store=self.data_store,
                    visual_catalog=self.visual_catalog,
                    merge_mode=mode
                )
                r_counts = res.get("results", {})
                self._repopulate_brand_tree()
                self._update_presets_menu()
                if hasattr(self, "_repopulate_results_table"):
                    self._repopulate_results_table()
                self._log(f"📥 Successfully imported Apollo Intelligence Pack from {os.path.basename(pack_fp)} (Merged: {r_counts})")
                win.destroy()
                messagebox.showinfo(
                    "Import Complete",
                    f"Successfully imported Intelligence Pack!\n\n"
                    f"• Brands Added/Updated: {r_counts.get('brands_added', 0)}\n"
                    f"• Presets Added: {r_counts.get('presets_added', 0)}\n"
                    f"• Exclusions Added: {r_counts.get('exclusions_added', 0)}\n"
                    f"• Whitelist Dealers Added: {r_counts.get('whitelist_added', 0)}\n"
                    f"• Visual Thumbnails Extracted: {r_counts.get('thumbnails_extracted', 0)}"
                )
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed importing package: {e}", parent=win)

        btn_row = tk.Frame(card, bg=t["panel"])
        btn_row.pack(fill="x", pady=(14, 0))
        self._btn(btn_row, "📥 Import & Apply Pack", _do_import, accent=True).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._btn(btn_row, "Cancel", win.destroy).pack(side="right")

    def _open_vero_disclosure_modal(self):
        """Open the VeRO & eBay Seller Disclosure Intelligence Harvester dialog."""
        return VeroDisclosureModal(self)

    def _open_visual_catalog_modal(self):
        """Open the Visual Threat Catalog & Benign Packaging Manager dialog."""
        VisualCatalogModal(self, self.visual_catalog, self.theme, on_update_callback=self._repopulate_results_table)

    def _mark_selected_as_visual_benign(self):
        """Add all selected listings' photos to the Green Catalog (Known Benign Packaging)."""
        selected = self.result_tree.selection()
        if not selected:
            messagebox.showinfo("Select", "Select one or more listings to mark packaging as Known Benign.")
            return

        added_count = 0
        for iid in selected:
            item_id = str(self.result_tree.set(iid, "item_id")).strip()
            target_item = next((it for it in self.results if str(it.get("item_id", "")).strip() == item_id), None)
            if not target_item:
                continue

            img_url = target_item.get("image_url", "")
            pil_img = self.raw_img_cache.get(img_url)
            if not pil_img and img_url:
                try:
                    req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        pil_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                    self.raw_img_cache[img_url] = pil_img
                except Exception:
                    continue

            if not pil_img:
                continue

            label = target_item.get("title", "Benign Packaging")[:32]
            entry = self.visual_catalog.add_entry(pil_img, entry_type="benign", label=label, source_url=img_url)
            if entry:
                target_item["threat_badge"] = f"🟢 Benign: {entry['label']}"
                target_item["visual_benign"] = True
                added_count += 1
                self._log(f"🟢 Added image fingerprint to Green Catalog (Benign): '{entry['label']}'")

        if added_count > 0:
            self._repopulate_results_table()
            messagebox.showinfo("Saved", f"Successfully added {added_count} visual fingerprint(s) to the Benign Packaging Catalog!\n\nAll matching listings will be recognized and filtered as benign.")
        else:
            messagebox.showwarning("Warning", "Could not capture valid images for the selected listing(s).")

    def _mark_selected_as_visual_counterfeit(self):
        """Add all selected listings' photos to the Red Catalog (Known Counterfeit Photo)."""
        selected = self.result_tree.selection()
        if not selected:
            messagebox.showinfo("Select", "Select one or more listings to mark photos as Known Counterfeit.")
            return

        added_count = 0
        for iid in selected:
            item_id = str(self.result_tree.set(iid, "item_id")).strip()
            target_item = next((it for it in self.results if str(it.get("item_id", "")).strip() == item_id), None)
            if not target_item:
                continue

            img_url = target_item.get("image_url", "")
            pil_img = self.raw_img_cache.get(img_url)
            if not pil_img and img_url:
                try:
                    req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        pil_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                    self.raw_img_cache[img_url] = pil_img
                except Exception:
                    continue

            if not pil_img:
                continue

            label = target_item.get("title", "Known Counterfeit Photo")[:32]
            entry = self.visual_catalog.add_entry(pil_img, entry_type="counterfeit", label=label, source_url=img_url)
            if entry:
                target_item["threat_badge"] = "🚨 Known Counterfeit (Visual Match)"
                target_item["visual_counterfeit"] = True
                added_count += 1
                self._log(f"🔴 Added image fingerprint to Red Catalog (Counterfeit): '{entry['label']}'")

        if added_count > 0:
            self._repopulate_results_table()
            messagebox.showinfo("Saved", f"Successfully added {added_count} visual fingerprint(s) to the Counterfeit Threat Catalog!\n\nAll matching listings will be flagged as High Threat!")
        else:
            messagebox.showwarning("Warning", "Could not capture valid images for the selected listing(s).")

    def _reverse_visual_search_from_url(self, img_url: str, label: str = "Visual Reference", marketplace: Optional[str] = None, region: Optional[str] = None):
        """Execute Reverse Image Search across active marketplace & locale using an image URL or local photo file."""
        if not img_url:
            messagebox.showwarning("Warning", "No image source provided.")
            return

        mkt = marketplace or self.marketplace_var.get()
        reg = region
        if not reg:
            if "Vinted" in mkt and hasattr(self, "vinted_country_var"):
                v_c = self.vinted_country_var.get()
                reg = "UK"
                for code, names in {
                    "UK": ["UK", "United Kingdom"], "FR": ["France", "FR"], "DE": ["Germany", "DE"],
                    "ES": ["Spain", "ES"], "IT": ["Italy", "IT"], "PL": ["Poland", "PL"],
                    "US": ["United States", "US"], "NL": ["Netherlands", "NL"], "BE": ["Belgium", "BE"],
                    "All": ["All", "Europe", "Global"]
                }.items():
                    if any(n in v_c for n in names):
                        reg = code
                        break
            elif "Mercado" in mkt and hasattr(self, "meli_country_var"):
                reg = self.meli_country_var.get()

        thresh = getattr(self.visual_catalog, "match_threshold", 6)
        
        # Link all scrapers to visual harvester
        self.visual_harvester.scraper = self.scraper
        self.visual_harvester.vinted_scraper = self.vinted_scraper
        self.visual_harvester.meli_scraper = self.mercadolibre_scraper
        self.visual_harvester.ali_scraper = self.aliexpress_scraper
        self.visual_harvester.wish_scraper = self.wish_scraper
        self.visual_harvester.temu_scraper = self.temu_scraper
        self.visual_harvester.tiktok_scraper = getattr(self, "tiktok_scraper", None)
        self.visual_harvester.printerval_scraper = getattr(self, "printerval_scraper", None)
        self.visual_harvester.redbubble_scraper = getattr(self, "redbubble_scraper", None)

        loc_label = f" [{reg}]" if reg else ""
        self._status(f"📸 Running Reverse Visual Dredge on {mkt}{loc_label} (Tolerance <={thresh})...")
        self._log(f"📸 Initiating Reverse Visual Dredge on {mkt}{loc_label} for '{label}' (Threshold <={thresh})")
        self.progress.start()

        def _worker():
            try:
                hits = self.visual_harvester.search_by_image(
                    img_url,
                    label=label,
                    marketplace=mkt,
                    region=reg,
                    max_distance=thresh,
                    max_results=50,
                    log_callback=self._log
                )
                def _done():
                    self.progress.stop()
                    if not hits:
                        self._status(f"Reverse visual search on {mkt}{loc_label} found no candidate listings.")
                        messagebox.showinfo("Visual Search", f"No {mkt}{loc_label} candidates could be harvested for '{label}'.")
                        return

                    total_candidates = len(hits)
                    verified_count = sum(1 for h in hits if h.get("is_verified_match", h.get("distance", 99) <= thresh))
                    self._log(f"📸 Reverse Visual Dredge Complete: Found {verified_count} verified photo clone(s) ({total_candidates} candidates evaluated) on {mkt}{loc_label}. Launching Triage Modal...")
                    self._status(f"Visual search evaluated {total_candidates} candidates ({verified_count} verified clones) on {mkt}.")
                    
                    # Launch dedicated Discovery & Triage Modal for Analyst Verification
                    ReverseVisualModal(self, hits, img_url, label=label, marketplace=mkt, region=reg, target_phash=str(thresh))
                self.after(0, _done)
            except Exception as e:
                def _err(err=e):
                    self.progress.stop()
                    self._log(f"❌ Reverse Visual Search failed: {err}")
                    messagebox.showerror("Error", f"Reverse Visual Search error: {err}")
                self.after(0, _err)

        threading.Thread(target=_worker, daemon=True).start()

    def _reverse_visual_search_selected(self, marketplace: Optional[str] = None, region: Optional[str] = None):
        """Execute Reverse Image Search across specified or active marketplace & region using selected listing photo."""
        selected = self.result_tree.selection()
        if not selected:
            messagebox.showinfo("Select", "Select a listing to perform Reverse Visual Search.")
            return
        iid = selected[0]
        item_id = str(self.result_tree.set(iid, "item_id")).strip()
        target_item = next((it for it in self.results if str(it.get("item_id", "")).strip() == item_id), None)
        if not target_item:
            messagebox.showwarning("Warning", "Could not locate listing data.")
            return

        img_url = target_item.get("image_url", "")
        if not img_url:
            messagebox.showwarning("Warning", "Selected listing has no image URL.")
            return

        if marketplace:
            target_mkt = marketplace
        else:
            url = target_item.get("url", "").lower()
            if "vinted" in url or "vinted" in str(target_item.get("platform", "")).lower():
                target_mkt = "Vinted"
            elif "mercadolibre" in url or "mercado" in str(target_item.get("platform", "")).lower():
                target_mkt = "Mercado Libre"
            elif "aliexpress" in url or "aliexpress" in str(target_item.get("platform", "")).lower():
                target_mkt = "AliExpress"
            elif "wish.com" in url or "wish" in str(target_item.get("platform", "")).lower():
                target_mkt = "Wish"
            elif "temu.com" in url or "temu" in str(target_item.get("platform", "")).lower():
                target_mkt = "Temu"
            else:
                target_mkt = self.marketplace_var.get()

        target_reg = region
        self._reverse_visual_search_from_url(img_url, label=target_item.get("title", "Selected Listing")[:32], marketplace=target_mkt, region=target_reg)

    def _add_selected_result_seller_to_stores(self):
        """Append highlighted results table seller username directly into Stores / Sellers box."""
        selected = self.result_tree.selection()
        if not selected:
            return
        added = []
        for iid in selected:
            for itm in self.results:
                if str(itm.get("item_id", "")) == str(self.result_tree.set(iid, "item_id")):
                    s = str(itm.get("seller", "")).replace("🛡", "").replace("(Authorized)", "").strip()
                    if s and s not in ("Unknown", "Resolving..."):
                        added.append(s)
                    break
        unique = list(dict.fromkeys(added))
        if not unique:
            return
        curr = self.store_text.get("1.0", "end").strip()
        ph = self.store_placeholder.strip()
        if not curr or curr == ph:
            self.store_text.delete("1.0", "end")
            self.store_text.insert("1.0", "\n".join(unique) + "\n")
            self.store_text.config(fg=self.theme["text"])
        else:
            lines = [l.strip() for l in curr.splitlines() if l.strip()]
            existing_lowers = [l.lower() for l in lines]
            for u in unique:
                if u.lower() not in existing_lowers:
                    lines.append(u)
            self.store_text.delete("1.0", "end")
            self.store_text.insert("1.0", "\n".join(lines) + "\n")
            self.store_text.config(fg=self.theme["text"])
        self._log(f"🏪 Added {len(unique)} seller(s) from Results to Stores box: {', '.join(unique)}")
        self._status(f"Added {len(unique)} seller(s) to Stores box.")

    def _select_all_results(self, event=None):
        """Select all rows in the results table."""
        children = self.result_tree.get_children()
        if children:
            self.result_tree.selection_set(children)
            self._on_result_tree_select()
        return "break"

    def _on_result_tree_select(self, event=None):
        """Update live selected row counter in Results toolbar."""
        self._update_result_count()

    def _copy_all_listing_urls(self):
        """Copy all harvested listing URLs in the results table to clipboard."""
        if not self.results:
            messagebox.showinfo("Copy URLs", "No listings in the results table to copy.")
            return
        urls = [it.get("url") for it in self.results if it.get("url")]
        if not urls:
            messagebox.showinfo("Copy URLs", "No valid URLs found.")
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join(urls))
        self._status(f"📋 Copied {len(urls)} listing URLs to clipboard.")
        self._log(f"📋 Copied all {len(urls)} listing URLs to clipboard.")
        messagebox.showinfo("Copied", f"Copied {len(urls)} listing URLs to clipboard!")

    def _copy_selected_urls(self):
        """Copy selected listing URLs to clipboard."""
        selected = self.result_tree.selection()
        if not selected:
            messagebox.showinfo("Copy URLs", "Select one or more rows to copy URLs.")
            return
        urls = []
        for iid in selected:
            vals = self.result_tree.item(iid)["values"]
            url = vals[10] if len(vals) > 10 else (vals[8] if len(vals) > 8 else "")
            if url:
                urls.append(url)
        if not urls:
            messagebox.showinfo("Copy URLs", "No valid URLs on selected rows.")
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join(urls))
        self._status(f"📋 Copied {len(urls)} selected listing URLs to clipboard.")
        self._log(f"📋 Copied {len(urls)} selected listing URLs to clipboard.")

    def _open_multi_locale_expander(self):
        """Open the Global Multi-Locale Expander & Compliance Exporter modal."""
        if not self.results:
            messagebox.showinfo("Multi-Locale Expander", "No harvested listings in the results table to expand.")
            return
        selected_iids = self.result_tree.selection()
        target_items = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.result_tree.item(iid)["values"]
                if len(vals) > 3:
                    item_id = str(vals[3]).strip()
                    for it in self.results:
                        if str(it.get("item_id", "")).strip() == item_id:
                            target_items.append(it)
                            break
        else:
            target_items = list(self.results)
        
        if hasattr(self, "_win_multilocale") and self._win_multilocale and self._win_multilocale.winfo_exists():
            self._win_multilocale.lift()
            self._win_multilocale.focus_force()
            return
        self._win_multilocale = MultiLocaleModal(self, target_items)

    def _open_whitelist_manager_window(self):
        """Open the Authorized Dealership & Whitelist Management Window."""
        if hasattr(self, "_win_whitelist") and self._win_whitelist and self._win_whitelist.winfo_exists():
            self._win_whitelist.lift()
            self._win_whitelist.focus_force()
            return
        self._win_whitelist = WhitelistManagerModal(self)

    def _whitelist_selected_result_seller(self):
        """Whitelist the seller from the selected row in results table."""
        sel = self.result_tree.focus()
        if not sel:
            selected = self.result_tree.selection()
            if selected:
                sel = selected[0]
        if not sel:
            return
        vals = self.result_tree.item(sel)["values"]
        seller_handle = str(vals[5]).replace("🛡", "").replace("(Authorized)", "").strip() if len(vals) > 5 else ""
        brand_val = vals[0] if len(vals) > 0 else "General / All Brands"
        if not seller_handle or seller_handle in ("Resolving...", "Unknown"):
            messagebox.showwarning("No Seller", "No valid seller handle found on this row.")
            return
        if self.data_store.is_seller_whitelisted(seller_handle):
            messagebox.showinfo("Already Whitelisted", f"Seller '{seller_handle}' is already on your Authorized Whitelist.")
            return
        
        d_name = simpledialog.askstring("Authorized Dealership", f"Enter Dealership / Entity Name for '{seller_handle}' (optional):", initialvalue="Authorized Dealer", parent=self)
        if d_name is None:
            return
        notes = simpledialog.askstring("Analyst Notes", f"Notes for '{seller_handle}' (optional):", initialvalue="Client Approved Whitelist", parent=self) or ""
        self.data_store.add_to_whitelist(seller_handle, brand=brand_val, dealer_name=d_name, notes=notes)
        self._log(f"🛡 Added '{seller_handle}' to Authorized Whitelist ({brand_val}).")
        messagebox.showinfo("Seller Whitelisted", f"Successfully added '{seller_handle}' to your Authorized Dealer Whitelist!\n\nThis seller will be automatically shielded and highlighted across scans.")
        if hasattr(self, "_repopulate_results_table"):
            self._repopulate_results_table()

    def _copy_selected_url(self):
        """Copy selected listing URL to clipboard."""
        sel = self.result_tree.focus()
        if not sel:
            selected = self.result_tree.selection()
            if selected:
                sel = selected[0]
        if sel:
            values = self.result_tree.item(sel)["values"]
            listing_url = values[10] if len(values) > 10 else (values[8] if len(values) > 8 else "")
            if listing_url:
                self.clipboard_clear()
                self.clipboard_append(listing_url)
                self._status("📋 Listing URL copied to clipboard.")

    def _open_connected_network_scanner(self):
        """Open the Connected Seller & Visual Syndicate Discovery Modal for the selected listing."""
        sel = self.result_tree.focus()
        if not sel:
            selected = self.result_tree.selection()
            if selected:
                sel = selected[0]
        if not sel:
            messagebox.showinfo("Network Scanner", "Please select a listing from the results table first.")
            return

        values = self.result_tree.item(sel)["values"]
        item_id = str(values[3]).strip() if len(values) > 3 else ""
        target_item = None
        for it in self.results:
            if str(it.get("item_id", "")).strip() == item_id:
                target_item = dict(it)
                break
        if not target_item:
            target_item = {
                "brand": values[0] if len(values) > 0 else "",
                "product_type": values[1] if len(values) > 1 else "",
                "title": values[2] if len(values) > 2 else "",
                "item_id": item_id,
                "price": str(values[4]) if len(values) > 4 else "",
                "seller": str(values[5]) if len(values) > 5 else "",
                "seller_origin": str(values[6]) if len(values) > 6 else "",
                "threat_badge": str(values[7]) if len(values) > 7 else "",
                "location": str(values[8]) if len(values) > 8 else "",
                "image_url": str(values[9]) if len(values) > 9 else "",
                "url": str(values[10]) if len(values) > 10 else (f"https://www.ebay.com/itm/{item_id}" if item_id else ""),
            }
        ConnectedNetworkModal(self, target_item)

    def _enrich_seller_threat_intel(self):
        """
        Parallel resolve true registered seller origin (country) and 3PL drop-shipping
        smokescreen threat flags across all session listings.
        """
        if not self.results:
            messagebox.showinfo("Threat Intel", "No harvested listings to analyze.")
            return

        selected_iids = self.result_tree.selection()
        target_items = []
        if selected_iids:
            for item_iid in selected_iids:
                vals = self.result_tree.item(item_iid)["values"]
                if len(vals) > 3:
                    item_id = str(vals[3]).strip()
                    for it in self.results:
                        if str(it.get("item_id", "")).strip() == item_id:
                            target_items.append(it)
                            break
        else:
            target_items = list(self.results)

        # Collect unique sellers
        sellers_to_query = []
        for it in target_items:
            s = it.get("seller", "")
            if s and s not in ("Unknown", "Resolving..."):
                clean = str(s).replace("🛡", "").replace("(Authorized)", "").strip()
                if clean:
                    sellers_to_query.append(clean)

        unique_sellers = list(dict.fromkeys(sellers_to_query))
        if not unique_sellers:
            messagebox.showinfo("Threat Intel", "No valid seller handles found to analyze.")
            return

        self.stop_event.clear()
        self.stop_btn.config(state="normal")
        if hasattr(self, "progress"):
            self.progress.start()

        self._status(f"Resolving Threat Intel for {len(unique_sellers)} sellers in parallel...")
        self._log(f"🌍 Starting Threat Intel & 3PL Smokescreen scan for {len(unique_sellers)} sellers...")

        def _worker():
            try:
                # Check data_store cache first
                uncached = []
                cached_intel = {}
                for s in unique_sellers:
                    cached = self.data_store.get_seller_intel(s)
                    if cached and cached.get("country") and cached.get("country") != "Unknown":
                        cached_intel[s] = cached
                    else:
                        uncached.append(s)

                # Resolve uncached in parallel via high-speed batch resolver
                if uncached and not self.stop_event.is_set():
                    resolved_map = self.scraper.batch_resolve_seller_countries(uncached)
                    for s, data in resolved_map.items():
                        country_val = data.get("country", "Unknown")
                        m_since = data.get("member_since", "")
                        if country_val and country_val != "Unknown":
                            self.data_store.set_seller_intel(s, country_val, member_since=m_since)
                            cached_intel[s] = {"country": country_val, "member_since": m_since}

                # Update results with enriched intel
                updated_count = 0
                critical_threats = 0
                for it in target_items:
                    if self.stop_event.is_set():
                        break
                    s = str(it.get("seller", "")).replace("🛡", "").replace("(Authorized)", "").strip()
                    intel = cached_intel.get(s) or self.data_store.get_seller_intel(s)
                    seller_country = intel.get("country", "") if intel else ""
                    loc = it.get("location", "")
                    assessment = self.data_store.compute_threat_assessment(seller_country, loc, seller_name=s)

                    it["seller_origin"] = assessment.get("country", "Unknown")
                    it["seller_flag"] = assessment.get("flag", "❓")
                    it["threat_score"] = assessment.get("score", "UNKNOWN")
                    it["threat_badge"] = assessment.get("badge", "Unresolved")

                    if assessment.get("score") == "CRITICAL":
                        critical_threats += 1
                    updated_count += 1

                def _apply():
                    if hasattr(self, "progress"):
                        self.progress.stop()
                    self.stop_btn.config(state="disabled")
                    self._repopulate_results_table()
                    if self.stop_event.is_set():
                        self._status(f"⏹ Threat Intel scan halted ({updated_count} enriched).")
                        self._log(f"⏹ Threat Intel scan halted by user ({updated_count} listings updated).")
                    else:
                        msg = f"Enriched Threat Intel for {updated_count} listings across {len(unique_sellers)} unique sellers!"
                        if critical_threats > 0:
                            msg += f"\n\n🚨 IDENTIFIED {critical_threats} CRITICAL 3PL SMOKESCREEN / GHOST ORIGIN TARGETS!"
                        self._status(f"Threat Intel scan complete: {updated_count} enriched ({critical_threats} critical).")
                        self._log(f"✅ Threat Intel scan complete: {updated_count} listings enriched ({critical_threats} critical threats).")
                        messagebox.showinfo("Threat Intel Complete", msg, parent=self)

                self.after(0, _apply)
            finally:
                self.after(0, lambda: self.stop_btn.config(state="disabled"))
                if hasattr(self, "progress"):
                    self.after(0, lambda: self.progress.stop())

        threading.Thread(target=_worker, daemon=True).start()

    def _enrich_sellers(self):
        """Enrich real seller/merchant/store names across AliExpress, Wish, Temu, and Printerval listings."""
        if not self.results:
            messagebox.showinfo("Enrich Sellers", "No harvested listings to enrich.")
            return

        selected_iids = self.result_tree.selection()
        target_items = []

        if selected_iids:
            used_indices = set()
            for item_iid in selected_iids:
                vals = self.result_tree.item(item_iid)["values"]
                if len(vals) > 5:
                    item_id = str(vals[3]).strip()
                    title_val = str(vals[2]).strip()
                    seller_val = str(vals[5]).strip()
                    price_val = str(vals[4]).strip()
                    url_val = str(vals[10]).strip() if len(vals) > 10 else (str(vals[8]).strip() if len(vals) > 8 else "")

                    matched_idx = None
                    # 1. Exact match on id + title + seller + price
                    for idx, it in enumerate(self.results):
                        if idx in used_indices:
                            continue
                        if (str(it.get("item_id", "")).strip() == item_id and
                            str(it.get("title", "")).strip() == title_val and
                            str(it.get("seller", "")).strip() == seller_val and
                            str(it.get("price", "")).strip() == price_val):
                            matched_idx = idx
                            break
                    # 2. Fallback match on id/url + title
                    if matched_idx is None:
                        for idx, it in enumerate(self.results):
                            if idx in used_indices:
                                continue
                            if ((item_id and str(it.get("item_id", "")).strip() == item_id) or
                                (url_val and str(it.get("url", "")).strip() == url_val)) and \
                                (str(it.get("title", "")).strip() == title_val):
                                matched_idx = idx
                                break
                    # 3. Fallback match on id or url
                    if matched_idx is None:
                        for idx, it in enumerate(self.results):
                            if idx in used_indices:
                                continue
                            if (item_id and str(it.get("item_id", "")).strip() == item_id) or \
                               (url_val and str(it.get("url", "")).strip() == url_val):
                                matched_idx = idx
                                break

                    if matched_idx is not None:
                        used_indices.add(matched_idx)
                        target_items.append(self.results[matched_idx])
        else:
            # Check all items in session needing seller enrichment
            for it in self.results:
                mkt = it.get("marketplace", "").lower()
                url = it.get("url", "").lower()
                seller = str(it.get("seller", "")).strip()
                if not seller or any(g in seller.lower() for g in ("ebay seller", "global search", "aliexpress global", "creator", "unknown", "printerval creator", "mercado libre seller", "mercado libre merchant", "mercado")):
                    target_items.append(it)

        if not target_items:
            messagebox.showinfo("Enrich Sellers", "No listings requiring seller enrichment found (all items already have specific store/merchant names).")
            return

        if not messagebox.askyesno("Enrich Sellers", f"Enrich real merchant/store names for {len(target_items)} listing(s)?\n\nThis will look up the specific seller/store ID for each listing."):
            return

        is_headless = self.headless_var.get()
        self.scraper.headless = is_headless
        self.aliexpress_scraper.headless = is_headless
        self.wish_scraper.headless = is_headless
        self.temu_scraper.headless = is_headless
        self.printerval_scraper.headless = is_headless
        self.mercadolibre_scraper.headless = is_headless
        self.zazzle_scraper.headless = is_headless
        self.spreadshirt_scraper.headless = is_headless
        self.cafepress_scraper.headless = is_headless

        self._log(f"🏪 Starting Seller Name Enrichment for {len(target_items)} item(s)...")
        self._status(f"🏪 Enriching {len(target_items)} sellers...")
        self.stop_event.clear()
        self.stop_btn.config(state="normal")
        if hasattr(self, "progress"):
            self.progress.start()

        def _worker():
            enriched_count = 0
            
            def _on_prog(current, total, item):
                nonlocal enriched_count
                s_name = str(item.get("seller", "")).strip()
                if s_name and not any(g in s_name.lower() for g in ("ebay seller", "global search", "aliexpress global", "unknown", "tiktok shop merchant", "mercado libre seller", "ir para", "ir a la", "pagina do vendedor", "página do vendedor")):
                    enriched_count += 1
                    
                    # Auto-update sibling listings in current results that share the same store/seller or identical standalone item
                    store_id = str(item.get("store_id", "")).strip()
                    store_url = str(item.get("store_url", "")).strip()
                    seller_origin = item.get("seller_origin")
                    location = item.get("location")
                    business_entity = item.get("business_entity")
                    threat_badge = item.get("threat_badge")
                    threat_score = item.get("threat_score")
                    item_url_norm = str(item.get("url", "")).split("?")[0].strip().lower()
                    item_id_val = str(item.get("item_id", "")).strip()
                    is_catalog_item = "/p/" in item_url_norm
                    
                    for other in self.results:
                        if other is item:
                            continue
                        is_match = False
                        other_url_norm = str(other.get("url", "")).split("?")[0].strip().lower()
                        other_id_val = str(other.get("item_id", "")).strip()

                        if store_id and str(other.get("store_id", "")).strip() == store_id:
                            is_match = True
                        elif store_url and str(other.get("store_url", "")).strip() == store_url:
                            is_match = True
                        elif not is_match and item.get("url") and other.get("url"):
                            u1, u2 = str(item.get("url", "")).lower(), str(other.get("url", "")).lower()
                            if "/pagina/" in u1 and "/pagina/" in u2:
                                p1 = u1.split("/pagina/")[1].split("?")[0].split("/")[0]
                                p2 = u2.split("/pagina/")[1].split("?")[0].split("/")[0]
                                if p1 and p1 == p2:
                                    is_match = True
                            elif "/loja/" in u1 and "/loja/" in u2:
                                l1 = u1.split("/loja/")[1].split("?")[0].split("/")[0]
                                l2 = u2.split("/loja/")[1].split("?")[0].split("/")[0]
                                if l1 and l1 == l2:
                                    is_match = True
                            elif "_custid_" in u1 and "_custid_" in u2:
                                c1 = u1.split("_custid_")[1].split("?")[0].split("&")[0]
                                c2 = u2.split("_custid_")[1].split("?")[0].split("&")[0]
                                if c1 and c1 == c2:
                                    is_match = True
                        elif s_name and other.get("seller") == s_name:
                            GENERIC_SELLER_PLACEHOLDERS = {"ebay seller", "unknown", "resolving...", "global search", "aliexpress global", "printerval creator", "printerval seller", "mercado libre seller", "mercado libre merchant", "tiktok shop merchant", "redbubble artist", "vinted user", "meli_seller_"}
                            if not any(g in s_name.lower() for g in GENERIC_SELLER_PLACEHOLDERS):
                                is_match = True
                        elif not is_catalog_item:
                            # Standalone items sharing exact URL or Item ID
                            if item_url_norm and other_url_norm and item_url_norm == other_url_norm:
                                is_match = True
                            elif item_id_val and other_id_val and item_id_val == other_id_val:
                                is_match = True

                        if is_match:
                            other["seller"] = s_name
                            if seller_origin and not other.get("seller_origin"):
                                other["seller_origin"] = seller_origin
                            if location and not other.get("location"):
                                other["location"] = location
                            if business_entity and not other.get("business_entity"):
                                other["business_entity"] = business_entity
                            if threat_badge:
                                other["threat_badge"] = threat_badge
                            if threat_score:
                                other["threat_score"] = threat_score

                pct = int((current / total) * 100) if total else 0
                self.after(0, lambda: self._status(f"🏪 Enriching Sellers [{current}/{total}] ({pct}%) -> '{s_name}'"))
                self.after(0, lambda: self._log(f"  ✓ [{item.get('marketplace', 'Platform')}] Enriched: '{item.get('title', '')[:40]}...' → Seller: '{s_name}', Price: {item.get('price', '')}"))
                self.after(0, lambda: self._repopulate_results_table())

            try:
                # Group items by platform
                ebay_items = [it for it in target_items if "ebay" in it.get("marketplace", "").lower() or "ebay.com" in it.get("url", "").lower()]
                ali_items = [it for it in target_items if "ali" in it.get("marketplace", "").lower() or "aliexpress" in it.get("url", "").lower()]
                wish_items = [it for it in target_items if "wish" in it.get("marketplace", "").lower() or "wish" in it.get("url", "").lower()]
                temu_items = [it for it in target_items if "temu" in it.get("marketplace", "").lower() or "temu" in it.get("url", "").lower()]
                meli_items = [it for it in target_items if "mercado" in it.get("marketplace", "").lower() or "mercadolibre" in it.get("marketplace", "").lower() or "mercadolivre" in it.get("marketplace", "").lower() or "mercadolibre" in it.get("url", "").lower() or "mercadolivre" in it.get("url", "").lower()]
                printerval_items = [it for it in target_items if "printerval" in it.get("marketplace", "").lower() or "printerval" in it.get("url", "").lower()]
                tiktok_items = [it for it in target_items if "tiktok" in it.get("marketplace", "").lower() or "tiktok" in it.get("url", "").lower()]
                zazzle_items = [it for it in target_items if "zazzle" in it.get("marketplace", "").lower() or "zazzle.com" in it.get("url", "").lower()]
                spreadshirt_items = [it for it in target_items if "spreadshirt" in it.get("marketplace", "").lower() or "spreadshirt.com" in it.get("url", "").lower()]
                cafepress_items = [it for it in target_items if "cafepress" in it.get("marketplace", "").lower() or "cafepress.com" in it.get("url", "").lower()]

                if ebay_items and not self.stop_event.is_set():
                    self.scraper.enrich_ebay_seller_info(
                        ebay_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if ali_items and not self.stop_event.is_set():
                    self.aliexpress_scraper.enrich_seller_info(
                        ali_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if wish_items and not self.stop_event.is_set():
                    self.wish_scraper.enrich_seller_info(
                        wish_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if temu_items and not self.stop_event.is_set():
                    self.temu_scraper.enrich_seller_info(
                        temu_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if meli_items and not self.stop_event.is_set():
                    self.mercadolibre_scraper.enrich_seller_info(
                        meli_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if printerval_items and not self.stop_event.is_set():
                    self.printerval_scraper.enrich_seller_info(
                        printerval_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if tiktok_items and not self.stop_event.is_set():
                    self.tiktok_scraper.enrich_seller_info(
                        tiktok_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if zazzle_items and not self.stop_event.is_set():
                    self.zazzle_scraper.enrich_seller_info(
                        zazzle_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if spreadshirt_items and not self.stop_event.is_set():
                    self.spreadshirt_scraper.enrich_seller_info(
                        spreadshirt_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

                if cafepress_items and not self.stop_event.is_set():
                    self.cafepress_scraper.enrich_seller_info(
                        cafepress_items,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event
                    )

            finally:
                if hasattr(self, "progress"):
                    self.after(0, lambda: self.progress.stop())
                self.after(0, lambda: self.stop_btn.config(state="disabled"))
                if self.stop_event.is_set():
                    self.after(0, lambda: self._status(f"⏹ Seller enrichment halted ({enriched_count} updated)."))
                    self.after(0, lambda: self._log(f"⏹ Seller enrichment halted by user ({enriched_count} item(s) updated before stopping)."))
                else:
                    self.after(0, lambda: self._status(f"🏪 Seller enrichment complete! ({enriched_count} updated)"))
                    self.after(0, lambda: self._log(f"🏪 Seller enrichment finished: Updated store names for {enriched_count} item(s)."))
                self.after(0, lambda: self._repopulate_results_table())

        threading.Thread(target=_worker, daemon=True).start()

    def _expand_pod_variants_selected(self):
        """Expand POD variants specifically for selected table rows."""
        self._expand_pod_variants(selected_only=True)

    def _expand_pod_variants(self, selected_only=False):
        """
        Dredge and expand all Print-on-Demand (POD) product variants (50+ items per design)
        across Printerval, Redbubble, etc., for confirmed infringing designs.
        """
        if not self.results:
            messagebox.showinfo("Expand POD Variants", "No harvested listings in table.")
            return

        selected_iids = self.result_tree.selection()
        target_items = []

        if selected_only or selected_iids:
            for item_iid in selected_iids:
                vals = self.result_tree.item(item_iid)["values"]
                if len(vals) > 3:
                    item_id = str(vals[3]).strip()
                    title_val = str(vals[2]).strip() if len(vals) > 2 else ""
                    url_val = str(vals[10]).strip() if len(vals) > 10 else (str(vals[8]).strip() if len(vals) > 8 else "")
                    for it in self.results:
                        if (item_id and str(it.get("item_id", "")).strip() == item_id) or \
                           (url_val and str(it.get("url", "")).strip() == url_val) or \
                           (title_val and str(it.get("title", "")).strip() == title_val):
                            if it not in target_items:
                                target_items.append(it)
                            break
        else:
            # Check all items in session from POD marketplaces
            for it in self.results:
                mkt = it.get("marketplace", "").lower()
                url = it.get("url", "").lower()
                if "printerval" in mkt or "printerval.com" in url or "redbubble" in mkt or "redbubble.com" in url:
                    target_items.append(it)

        # Filter only POD items
        pod_targets = [
            it for it in target_items
            if "printerval" in it.get("marketplace", "").lower() or "printerval.com" in it.get("url", "").lower()
            or "redbubble" in it.get("marketplace", "").lower() or "redbubble.com" in it.get("url", "").lower()
            or "teepublic" in it.get("marketplace", "").lower() or "teepublic.com" in it.get("url", "").lower()
            or "spreadshirt" in it.get("marketplace", "").lower() or "spreadshirt.com" in it.get("url", "").lower() or "spreadshop.com" in it.get("url", "").lower()
            or "zazzle" in it.get("marketplace", "").lower() or "zazzle.com" in it.get("url", "").lower()
            or "cafepress" in it.get("marketplace", "").lower() or "cafepress.com" in it.get("url", "").lower()
            or "threadless" in it.get("marketplace", "").lower() or "threadless.com" in it.get("url", "").lower()
            or "teespring" in it.get("marketplace", "").lower() or "spring.com" in it.get("url", "").lower() or "creator-spring.com" in it.get("url", "").lower()
            or "fineartamerica" in it.get("marketplace", "").lower() or "fineartamerica.com" in it.get("url", "").lower() or "pixels.com" in it.get("url", "").lower()
        ]

        if not pod_targets:
            messagebox.showinfo(
                "Expand POD Variants",
                "No Print-on-Demand (Printerval / Redbubble / TeePublic / Spreadshirt / Zazzle / CafePress / Threadless / TeeSpring / Fine Art America) listings found in current selection.\n\n"
                "Please select one or more POD design listings to expand."
            )
            return

        scope_desc = f"{len(pod_targets)} selected design(s)" if (selected_only or selected_iids) else f"all {len(pod_targets)} POD design(s)"
        if not messagebox.askyesno(
            "Expand POD Variants",
            f"Expand all product merchandise variants (T-Shirts, Hoodies, Mugs, Stickers, Canvas, Phone Cases, Hats, etc.) for {scope_desc}?\n\n"
            f"This will visit each confirmed design and generate full physical product URLs into your results table."
        ):
            return

        is_headless = self.headless_var.get()
        self.printerval_scraper.headless = is_headless
        self.spreadshirt_scraper.headless = is_headless
        self.zazzle_scraper.headless = is_headless
        self.cafepress_scraper.headless = is_headless
        self.threadless_scraper.headless = is_headless
        self.teespring_scraper.headless = is_headless
        self.fineartamerica_scraper.headless = is_headless

        self._log(f"👕 Starting POD Variant Expansion for {len(pod_targets)} parent design(s)...")
        self._status(f"👕 Expanding POD variants for {len(pod_targets)} design(s)...")
        self.stop_event.clear()
        self.stop_btn.config(state="normal")

        def _worker():
            total_added = 0
            existing_ids = {str(it.get("item_id", "")).strip() for it in self.results if it.get("item_id")}

            def _on_prog(current, total, new_count, item):
                self.after(0, lambda: self._status(f"👕 Expanding POD Variants: {current}/{total} -> +{new_count} items found"))

            try:
                printerval_targets = [
                    it for it in pod_targets
                    if "printerval" in it.get("marketplace", "").lower() or "printerval.com" in it.get("url", "").lower()
                ]
                redbubble_targets = [
                    it for it in pod_targets
                    if "redbubble" in it.get("marketplace", "").lower() or "redbubble.com" in it.get("url", "").lower()
                ]

                if printerval_targets and not self.stop_event.is_set():
                    new_variants = self.printerval_scraper.expand_design_variants(
                        printerval_targets,
                        existing_item_ids=existing_ids,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )

                    if new_variants:
                        for v in new_variants:
                            self.results.append(v)
                            vid = str(v.get("item_id", "")).strip()
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"Printerval_{vid}")
                            try:
                                if hasattr(self, "data_store"):
                                    self.data_store.add_or_update_listing(v)
                            except Exception:
                                pass
                        total_added += len(new_variants)

                if redbubble_targets and not self.stop_event.is_set():
                    new_rb_variants = self.redbubble_scraper.expand_design_variants(
                        redbubble_targets,
                        existing_item_ids=existing_ids,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )

                    if new_rb_variants:
                        for v in new_rb_variants:
                            self.results.append(v)
                            vid = str(v.get("item_id", "")).strip()
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"Redbubble_{vid}")
                            try:
                                if hasattr(self, "data_store"):
                                    self.data_store.add_or_update_listing(v)
                            except Exception:
                                pass
                        total_added += len(new_rb_variants)

                teepublic_targets = [
                    it for it in pod_targets
                    if "teepublic" in it.get("marketplace", "").lower() or "teepublic.com" in it.get("url", "").lower()
                ]
                if teepublic_targets and not self.stop_event.is_set():
                    new_tp_variants = self.teepublic_scraper.expand_design_variants(
                        teepublic_targets,
                        existing_item_ids=existing_ids,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )
                    if new_tp_variants:
                        for v in new_tp_variants:
                            self.results.append(v)
                            vid = str(v.get("item_id", "")).strip()
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"TeePublic_{vid}")
                            try:
                                if hasattr(self, "data_store"):
                                    self.data_store.add_or_update_listing(v)
                            except Exception:
                                pass
                        total_added += len(new_tp_variants)

                spreadshirt_targets = [
                    it for it in pod_targets
                    if "spreadshirt" in it.get("marketplace", "").lower() or "spreadshirt.com" in it.get("url", "").lower() or "spreadshop.com" in it.get("url", "").lower()
                ]
                if spreadshirt_targets and not self.stop_event.is_set():
                    new_sp_variants = self.spreadshirt_scraper.expand_design_variants(
                        spreadshirt_targets,
                        existing_item_ids=existing_ids,
                        progress_callback=_on_prog,
                        stop_event=self.stop_event,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )
                    if new_sp_variants:
                        for v in new_sp_variants:
                            self.results.append(v)
                            vid = str(v.get("item_id", "")).strip()
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"Spreadshirt_{vid}")
                            try:
                                if hasattr(self, "data_store"):
                                    self.data_store.add_or_update_listing(v)
                            except Exception:
                                pass
                        total_added += len(new_sp_variants)

                # Zazzle POD Expansion
                zazzle_targets = [
                    it for it in pod_targets
                    if "zazzle" in it.get("marketplace", "").lower() or "zazzle.com" in it.get("url", "").lower()
                ]
                for p_item in zazzle_targets:
                    if self.stop_event.is_set(): break
                    new_z_variants = self.zazzle_scraper.expand_design_variants(
                        p_item,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )
                    for v in new_z_variants:
                        vid = str(v.get("item_id", "")).strip()
                        if vid and vid not in existing_ids:
                            existing_ids.add(vid)
                            self.results.append(v)
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"Zazzle_{vid}")
                            total_added += 1

                # CafePress POD Expansion
                cafepress_targets = [
                    it for it in pod_targets
                    if "cafepress" in it.get("marketplace", "").lower() or "cafepress.com" in it.get("url", "").lower()
                ]
                for p_item in cafepress_targets:
                    if self.stop_event.is_set(): break
                    new_cp_variants = self.cafepress_scraper.expand_design_variants(
                        p_item,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )
                    for v in new_cp_variants:
                        vid = str(v.get("item_id", "")).strip()
                        if vid and vid not in existing_ids:
                            existing_ids.add(vid)
                            self.results.append(v)
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"CafePress_{vid}")
                            total_added += 1

                # Threadless POD Expansion
                threadless_targets = [
                    it for it in pod_targets
                    if "threadless" in it.get("marketplace", "").lower() or "threadless.com" in it.get("url", "").lower()
                ]
                for p_item in threadless_targets:
                    if self.stop_event.is_set(): break
                    new_th_variants = self.threadless_scraper.expand_design_variants(
                        p_item,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )
                    for v in new_th_variants:
                        vid = str(v.get("item_id", "")).strip()
                        if vid and vid not in existing_ids:
                            existing_ids.add(vid)
                            self.results.append(v)
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"Threadless_{vid}")
                            total_added += 1

                # TeeSpring POD Expansion
                teespring_targets = [
                    it for it in pod_targets
                    if "teespring" in it.get("marketplace", "").lower() or "spring.com" in it.get("url", "").lower() or "creator-spring.com" in it.get("url", "").lower()
                ]
                for p_item in teespring_targets:
                    if self.stop_event.is_set(): break
                    new_ts_variants = self.teespring_scraper.expand_design_variants(
                        p_item,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )
                    for v in new_ts_variants:
                        vid = str(v.get("item_id", "")).strip()
                        if vid and vid not in existing_ids:
                            existing_ids.add(vid)
                            self.results.append(v)
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"TeeSpring_{vid}")
                            total_added += 1

                # Fine Art America POD Expansion
                faa_targets = [
                    it for it in pod_targets
                    if "fineartamerica" in it.get("marketplace", "").lower() or "fineartamerica.com" in it.get("url", "").lower() or "pixels.com" in it.get("url", "").lower()
                ]
                for p_item in faa_targets:
                    if self.stop_event.is_set(): break
                    new_faa_variants = self.fineartamerica_scraper.expand_design_variants(
                        p_item,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )
                    for v in new_faa_variants:
                        vid = str(v.get("item_id", "")).strip()
                        if vid and vid not in existing_ids:
                            existing_ids.add(vid)
                            self.results.append(v)
                            vurl = str(v.get("url", "")).strip().lower().split("?")[0]
                            if vurl: self.seen_item_ids.add(vurl)
                            if vid: self.seen_item_ids.add(f"FineArtAmerica_{vid}")
                            total_added += 1

            finally:
                self.after(0, lambda: self.stop_btn.config(state="disabled"))
                if self.stop_event.is_set():
                    self.after(0, lambda: self._status(f"⏹ POD variant expansion halted (+{total_added} added)."))
                    self.after(0, lambda: self._log(f"⏹ POD variant expansion halted by user (+{total_added} variant listing(s) added)."))
                else:
                    self.after(0, lambda: self._status(f"👕 POD variant expansion complete! (+{total_added} variants added)"))
                    self.after(0, lambda: self._log(f"👕 POD variant expansion complete: Successfully added +{total_added} variant listing(s) to table."))
                self.after(0, lambda: self._repopulate_results_table())

        threading.Thread(target=_worker, daemon=True).start()

    def _sweep_redbubble_artist_selected(self):
        """Sweep full Redbubble artist shop portfolio (/people/<artist>/shop) for selected listing(s)."""
        selected_iids = self.result_tree.selection()
        if not selected_iids:
            messagebox.showinfo("Sweep Artist Portfolio", "Please select a Redbubble listing first.")
            return

        target_artists = set()
        brand_keyword = self.keyword_entry.get().strip() if hasattr(self, "keyword_entry") else ""

        for item_iid in selected_iids:
            vals = self.result_tree.item(item_iid)["values"]
            if len(vals) > 5:
                artist = str(vals[5]).strip()
                if artist and artist not in ("Redbubble Artist", "GLOBAL", "unknown", "Printerval Creator"):
                    target_artists.add(artist)

        if not target_artists:
            messagebox.showinfo("Sweep Artist Portfolio", "No specific Redbubble artist names identified in selection.")
            return

        artist_list_str = ", ".join(list(target_artists)[:3]) + ("..." if len(target_artists) > 3 else "")
        if not messagebox.askyesno(
            "Sweep Artist Portfolio",
            f"Sweep complete shop portfolios for artist(s): {artist_list_str}?\n\n"
            f"This will search their full catalog for '{brand_keyword or 'all designs'}' to uncover additional hidden infringements."
        ):
            return

        self._log(f"🎨 Starting Redbubble Artist Portfolio Sweeps for {len(target_artists)} creator(s)...")
        self._status(f"🎨 Sweeping artist portfolios ({len(target_artists)} creators)...")
        self.stop_event.clear()
        self.stop_btn.config(state="normal")

        def _worker():
            total_found = 0
            existing_ids = {str(it.get("item_id", "")).strip() for it in self.results if it.get("item_id")}

            try:
                for artist in target_artists:
                    if self.stop_event.is_set():
                        break

                    portfolio_items = self.redbubble_scraper.sweep_artist_portfolio(
                        artist_name=artist,
                        brand_keyword=brand_keyword,
                        max_items=100,
                        existing_item_ids=existing_ids,
                        stop_event=self.stop_event,
                        log_callback=lambda msg: self.after(0, lambda: self._log(msg))
                    )

                    if portfolio_items:
                        for it in portfolio_items:
                            self.results.append(it)
                            try:
                                if hasattr(self, "data_store"):
                                    self.data_store.add_or_update_listing(it)
                            except Exception:
                                pass
                        total_found += len(portfolio_items)

            finally:
                self.after(0, lambda: self.stop_btn.config(state="disabled"))
                if self.stop_event.is_set():
                    self.after(0, lambda: self._status(f"⏹ Artist portfolio sweep halted (+{total_found} added)."))
                    self.after(0, lambda: self._log(f"⏹ Artist sweep halted by user (+{total_found} design(s) added)."))
                else:
                    self.after(0, lambda: self._status(f"🎨 Artist portfolio sweep finished! (+{total_found} designs added)"))
                    self.after(0, lambda: self._log(f"🎨 Artist portfolio sweep finished: Successfully added +{total_found} designs to table."))
                self.after(0, lambda: self._repopulate_results_table())

        threading.Thread(target=_worker, daemon=True).start()

    # ── Inline & Hover Thumbnail Preview Engine ──────────────────────────────
    def _get_placeholder_thumb(self, size_px=60):
        if not hasattr(self, "_placeholders"):
            self._placeholders = {}
        if size_px not in self._placeholders:
            ph = Image.new("RGBA", (size_px, size_px), (35, 40, 52, 255))
            self._placeholders[size_px] = ImageTk.PhotoImage(ph)
        return self._placeholders[size_px]

    def _get_scaled_photo(self, pil_img, size_px):
        """Scale and center a PIL Image into a square PhotoImage."""
        img_copy = pil_img.copy()
        img_copy.thumbnail((size_px, size_px), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size_px, size_px), (0, 0, 0, 0))
        offset = ((size_px - img_copy.width) // 2, (size_px - img_copy.height) // 2)
        canvas.paste(img_copy, offset)
        return ImageTk.PhotoImage(canvas)

    def _fetch_inline_thumbnail(self, iid, image_url):
        """Asynchronously download and display square inline thumbnail in result_tree with retry resiliency."""
        if not image_url or not str(image_url).startswith("http"):
            return

        size_key = self.thumb_size_var.get() if hasattr(self, "thumb_size_var") else "Medium (100px)"
        cfg = THUMB_CONFIG.get(size_key, THUMB_CONFIG["Medium (100px)"])
        if cfg["img_size"] <= 0:
            return

        cache_key = (size_key, image_url)
        if cache_key in self.inline_img_cache:
            photo = self.inline_img_cache[cache_key]
            if self.result_tree.exists(iid):
                self.result_tree.item(iid, image=photo)
            return

        if image_url in self.raw_img_cache:
            photo = self._get_scaled_photo(self.raw_img_cache[image_url], cfg["img_size"])
            self.inline_img_cache[cache_key] = photo
            if self.result_tree.exists(iid):
                self.result_tree.item(iid, image=photo)
            return

        cur_size_key = self.thumb_size_var.get()
        cur_cfg = THUMB_CONFIG.get(cur_size_key, THUMB_CONFIG["Medium (100px)"])
        cur_img_size = cur_cfg.get("img_size", 100)

        def _worker(sz_key=cur_size_key, sz_px=cur_img_size):
            if not self.result_tree.exists(iid):
                return

            # Cache size safeguard to prevent RAM bloat
            if len(self.raw_img_cache) > 800:
                for k in list(self.raw_img_cache.keys())[:250]:
                    self.raw_img_cache.pop(k, None)
            # --------------------------------------------------------------------------
            # The workers raced to fetch each graphic card,
            # But twenty score of photos hit them hard!
            # With thirty-two swift threads the queue shall fly,
            # And eight full seconds lest the socket die!
            # --------------------------------------------------------------------------
            for attempt in range(2):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    resp = self.http_session.get(str(image_url), headers=headers, timeout=10.0)
                    if resp.status_code == 200:
                        pil_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                        self.raw_img_cache[image_url] = pil_img
                        
                        # Compute 64-bit pHash for sorting by thumbnail similarity!
                        h = compute_phash(pil_img)
                        for itm in self.results:
                            if itm.get("image_url") == image_url:
                                itm["phash"] = h
                                break

                        # Auto-match against Visual Catalog (Benign vs Counterfeit)
                        try:
                            v_match = self.visual_catalog.match_image(pil_img)
                            if v_match:
                                for itm in self.results:
                                    if itm.get("image_url") == image_url:
                                        if v_match["type"] == "benign":
                                            itm["threat_badge"] = f"🟢 Benign: {v_match['label']}"
                                            itm["visual_benign"] = True
                                        elif v_match["type"] == "counterfeit":
                                            itm["threat_badge"] = f"🚨 Visual Counterfeit ({v_match['similarity_pct']}%)"
                                            itm["threat_score"] = max(itm.get("threat_score", 0), 95)
                                            itm["visual_counterfeit"] = True
                                        
                                        # Update UI treeview if row exists
                                        def _update_row(t_badge=itm["threat_badge"]):
                                            if self.result_tree.exists(iid):
                                                vals = list(self.result_tree.item(iid, "values"))
                                                if len(vals) > 7:
                                                    vals[7] = t_badge
                                                    self.result_tree.item(iid, values=vals)
                                        self.after(0, _update_row)
                                        break
                        except Exception:
                            pass

                        if sz_px > 0:
                            photo = self._get_scaled_photo(pil_img, sz_px)
                            self.inline_img_cache[(sz_key, image_url)] = photo
                            
                            def _apply():
                                if self.result_tree.exists(iid) and self.thumb_size_var.get() != "Off (Text Only)":
                                    self.result_tree.item(iid, image=photo)
                            self.after(0, _apply)
                        break
                    elif resp.status_code in (429, 503, 504) and attempt < 1:
                        time.sleep(0.4)
                except Exception:
                    if attempt < 1:
                        time.sleep(0.35)
                    else:
                        pass

        if hasattr(self, "thumb_executor"):
            self.thumb_executor.submit(_worker)
        else:
            threading.Thread(target=_worker, daemon=True).start()

    def _on_thumb_size_changed(self, event=None):
        """Handle user changing thumbnail size (Off, Small, Medium, Large, Extra Large)."""
        size_key = self.thumb_size_var.get()
        self.data_store.set_setting("thumb_size", size_key)
        self.show_preview_var.set(size_key != "Off (Text Only)")
        cfg = THUMB_CONFIG.get(size_key, THUMB_CONFIG["Medium (100px)"])

        style = ttk.Style()
        style.configure("Results.Treeview", rowheight=cfg["rowheight"])
        self.result_tree.configure(show=cfg["show"], style="Results.Treeview")
        self.result_tree.column("#0", width=cfg["col_width"], minwidth=cfg["col_width"], anchor="center", stretch=False)
        self.result_tree.heading("#0", text="Preview" if cfg["img_size"] > 0 else "", anchor="center")

        if cfg["img_size"] <= 0:
            self._hide_preview_popup()

        if self.results:
            self._repopulate_results_table()

    def _on_tree_mouse_motion(self, event):
        """Handle cursor motion over results table to trigger thumbnail preview."""
        row_id = self.result_tree.identify_row(event.y)
        if not row_id:
            self._hide_preview_popup()
            return

        if row_id == self.last_hovered_iid and self.preview_win:
            return

        self.last_hovered_iid = row_id
        if self.preview_cancel_id:
            self.after_cancel(self.preview_cancel_id)
        
        # Debounce preview slightly to keep UI fluid
        self.preview_cancel_id = self.after(120, self._show_preview_for_row, row_id, event.x_root, event.y_root)

    def _hide_preview_popup(self, event=None):
        if self.preview_cancel_id:
            self.after_cancel(self.preview_cancel_id)
            self.preview_cancel_id = None
        if self.preview_win:
            try:
                self.preview_win.destroy()
            except Exception:
                pass
            self.preview_win = None
        self.last_hovered_iid = None

    def _show_preview_for_row(self, row_id, x_root, y_root):
        if not self.result_tree.exists(row_id):
            return
        vals = self.result_tree.item(row_id)["values"]
        if len(vals) < 8:
            return

        title     = str(vals[2])
        price     = str(vals[4])
        location  = str(vals[6])
        image_url = str(vals[7]).strip()

        if not image_url or not image_url.startswith("http"):
            self._hide_preview_popup()
            return

        t = self.theme
        if self.preview_win:
            try: self.preview_win.destroy()
            except Exception: pass

        self.preview_win = tk.Toplevel(self)
        self.preview_win.wm_overrideredirect(True)
        self.preview_win.configure(bg=t["border"], padx=1, pady=1)

        pop_frame = tk.Frame(self.preview_win, bg=t["panel"], padx=6, pady=6)
        pop_frame.pack(fill="both", expand=True)

        # Image placeholder
        img_lbl = tk.Label(pop_frame, text="Loading image...", bg=t["entry_bg"], fg=t["subtext"],
                           font=FONT_SM, width=22, height=8)
        img_lbl.pack(pady=(0, 4))

        # Truncated title & price
        short_title = (title[:48] + "...") if len(title) > 50 else title
        title_lbl = tk.Label(pop_frame, text=short_title, bg=t["panel"], fg=t["text"],
                             font=FONT_SM, wraplength=180, justify="left")
        title_lbl.pack(anchor="w")

        info_text = f"{price}" + (f" • {location}" if location else "")
        info_lbl = tk.Label(pop_frame, text=info_text, bg=t["panel"], fg=t["accent"],
                            font=("Segoe UI", 9, "bold"))
        info_lbl.pack(anchor="w", pady=(2, 0))

        # Position window near cursor, keeping strictly inside the application display bounds
        app_x = self.winfo_rootx()
        app_y = self.winfo_rooty()
        app_w = self.winfo_width()
        app_h = self.winfo_height()

        pop_w = 210
        pop_h = 240

        # If placing to the right overflows the window bounds, place to the left
        if x_root + 18 + pop_w > app_x + app_w:
            win_x = max(app_x + 10, x_root - pop_w - 18)
        else:
            win_x = x_root + 18

        if y_root + pop_h > app_y + app_h:
            win_y = max(app_y + 10, app_y + app_h - pop_h - 10)
        else:
            win_y = max(app_y + 10, y_root - 70)

        self.preview_win.geometry(f"+{win_x}+{win_y}")

        # Check in-memory cache
        if image_url in self.img_cache:
            img_lbl.configure(image=self.img_cache[image_url], text="", width=0, height=0)
        elif image_url in self.raw_img_cache:
            photo = self._get_scaled_photo(self.raw_img_cache[image_url], 180)
            self.img_cache[image_url] = photo
            img_lbl.configure(image=photo, text="", width=0, height=0)
        else:
            threading.Thread(target=self._fetch_and_render_img,
                             args=(image_url, img_lbl, self.preview_win), daemon=True).start()

    def _fetch_and_render_img(self, url, img_lbl, target_win):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = resp.read()
            pil_img = Image.open(io.BytesIO(data)).convert("RGBA")
            self.raw_img_cache[url] = pil_img
            photo = self._get_scaled_photo(pil_img, 180)
            self.img_cache[url] = photo

            def _apply():
                if target_win == self.preview_win and img_lbl.winfo_exists():
                    img_lbl.configure(image=photo, text="", width=0, height=0)
            self.after(0, _apply)
        except Exception:
            def _fail():
                if target_win == self.preview_win and img_lbl.winfo_exists():
                    img_lbl.configure(text="(Image preview\nunavailable)", height=5)
            self.after(0, _fail)

    # ══════════════════════════════════════════════════════════════════════════
    #  EASTER EGGS & FUN DETAILS
    # ══════════════════════════════════════════════════════════════════════════
    def _check_konami(self, event):
        """Global Konami code detection (↑ ↑ ↓ ↓ ← → ← → B A)."""
        key = event.keysym
        self.konami_buffer.append(key)
        if len(self.konami_buffer) > len(self.konami_sequence):
            self.konami_buffer.pop(0)

        if self.konami_buffer == self.konami_sequence:
            self._trigger_konami_easter_egg()
            self.konami_buffer.clear()

    def _trigger_wick_easter_egg(self):
        """John Wick / The Continental High Table Excommunicado easter egg."""
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        self.data_store.unlock_wick()
        self._refresh_theme_menu()
        secret_name = THEMES["continental"]["name"]
        self.theme_var.set(secret_name)
        self._on_theme_changed()

        self._log("=" * 75)
        self._log("🪙 ─────────────────────────────────────────────────────────────────────────")
        self._log("🪙 [THE CONTINENTAL HOTEL — NEW YORK]")
        self._log("🪙 'Good evening, Mr. Wick. Membership status: Recognized. Services: Available.'")
        self._log("🪙 'Rules... without them, we live with the animals.'")
        self._log("🪙 [HIGH TABLE EXCOMMUNICADO TARGETING PROTOCOL INITIALIZED]")
        self._log("🪙 ─────────────────────────────────────────────────────────────────────────")
        self._log("=" * 75)
        self._status("🪙 THE CONTINENTAL: High Table Excommunicado Protocol Engaged!")
        # Custom Themed Dark Continental Concierge Modal
        win = tk.Toplevel(self)
        win.title("🪙 The Continental — New York")
        win.configure(bg="#0A0B0E")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self._apply_dark_titlebar(win)

        # Center modal
        self._center_window(win, 500, 340)

        card = tk.Frame(win, bg="#12141A", padx=20, pady=18, highlightbackground="#D4AF37", highlightthickness=2)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(card, text="🪙 THE CONTINENTAL", font=("Segoe UI", 15, "bold"), bg="#12141A", fg="#D4AF37").pack(anchor="center")
        tk.Label(card, text="NEW YORK CITY  •  HIGH TABLE SANCTIONED", font=("Segoe UI", 8, "bold"), bg="#12141A", fg="#8C93A3").pack(anchor="center", pady=(2, 10))

        div = tk.Frame(card, bg="#D4AF37", height=1)
        div.pack(fill="x", pady=(0, 12))

        tk.Label(card, text="Good evening, Mr. Wick.", font=("Segoe UI", 12, "bold"), bg="#12141A", fg="#F2F4F8").pack(anchor="center")
        tk.Label(card, text="Membership status: Recognized  •  Concierge Services: Available", font=FONT_SM, bg="#12141A", fg="#4EBA6F").pack(anchor="center", pady=(3, 10))

        quote_box = tk.Frame(card, bg="#060709", padx=12, pady=8, highlightbackground="#2E3342", highlightthickness=1)
        quote_box.pack(fill="x", pady=(0, 14))
        tk.Label(quote_box, text='"Rules... without them, we live with the animals."', font=("Georgia", 10, "italic"), bg="#060709", fg="#D4AF37").pack(anchor="center")
        tk.Label(quote_box, text="— Winston Scott, Manager", font=("Segoe UI", 8), bg="#060709", fg="#8C93A3").pack(anchor="center", pady=(2, 0))

        btn = tk.Button(card, text="🪙 Enter The Continental", command=win.destroy,
                        bg="#D4AF37", fg="#0A0B0E", font=("Segoe UI", 10, "bold"),
                        relief="flat", padx=16, pady=5, activebackground="#E5B842", cursor="hand2")
        btn.pack(anchor="center")

    def _trigger_brundo_easter_egg(self):
        """Secret Agent Brundo K9 Recon easter egg."""
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        self.data_store.unlock_brundo()
        self._refresh_theme_menu()
        secret_name = THEMES["brundo_recon"]["name"]
        self.theme_var.set(secret_name)
        self._on_theme_changed()

        self._log("=" * 75)
        self._log("🐕 ─────────────────────────────────────────────────────────────────────────")
        self._log("🐕 [AGENT BRUNDO — CHIEF MORALE & CANINE RECON OFFICER ONLINE]")
        self._log("🐾 'Brundo sniffed the domestic 3PL warehouse. Dropshippers fled the state.'")
        self._log("🐾 'Status: 14/10 Good Boy. 100% Brand Infringement Quota Retrieved.'")
        self._log("🐕 [CANINE ENFORCEMENT & TREAT RECON PROTOCOL INITIALIZED]")
        self._log("🐕 ─────────────────────────────────────────────────────────────────────────")
        self._log("=" * 75)
        self._status("🐕 AGENT BRUNDO ONLINE: Good Boy Mode Maximum • 100% Takedown Rate!")

        # Custom Themed Brundo Velvet Chocolate Modal
        win = tk.Toplevel(self)
        win.title("🐕 Agent Brundo — Chief Morale & K9 Recon")
        win.configure(bg="#1E140F")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self._apply_dark_titlebar(win)

        # Center modal
        self._center_window(win, 520, 360)

        card = tk.Frame(win, bg="#2C1D16", padx=20, pady=18, highlightbackground="#D49B5A", highlightthickness=2)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(card, text="🐕 AGENT BRUNDO", font=("Segoe UI", 16, "bold"), bg="#2C1D16", fg="#D49B5A").pack(anchor="center")
        tk.Label(card, text="CHIEF MORALE & TRADEMARK RETRIEVAL OFFICER", font=("Segoe UI", 8, "bold"), bg="#2C1D16", fg="#BCAAA4").pack(anchor="center", pady=(2, 10))

        div = tk.Frame(card, bg="#D49B5A", height=1)
        div.pack(fill="x", pady=(0, 12))

        tk.Label(card, text="Mission: Sniff Out Counterfeits. Fetch Takedowns.", font=("Segoe UI", 11, "bold"), bg="#2C1D16", fg="#FAF6F0").pack(anchor="center")
        tk.Label(card, text="Specialty: 14/10 Good Boy  •  Bury Rogue Dropshippers in Backyard", font=FONT_SM, bg="#2C1D16", fg="#E8C38F").pack(anchor="center", pady=(3, 10))

        quote_box = tk.Frame(card, bg="#1E140F", padx=12, pady=8, highlightbackground="#5C3D2E", highlightthickness=1)
        quote_box.pack(fill="x", pady=(0, 14))
        tk.Label(quote_box, text='"I fetch ball, I fetch fake spark plugs, I sleep on couch."', font=("Georgia", 10, "italic"), bg="#1E140F", fg="#D49B5A").pack(anchor="center")
        tk.Label(quote_box, text="— Brundo, Chocolate Lab Supreme", font=("Segoe UI", 8), bg="#1E140F", fg="#BCAAA4").pack(anchor="center", pady=(2, 0))

        btn = tk.Button(card, text="🐾 Good Boy! Let's Hunt", command=win.destroy,
                        bg="#D49B5A", fg="#1E140F", font=("Segoe UI", 10, "bold"),
                        relief="flat", padx=16, pady=5, activebackground="#E8C38F", cursor="hand2")
        btn.pack(anchor="center")

    def _trigger_fir_easter_egg(self):
        """Falling in Reverse / Ronnie Radke Easter Egg."""
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        self.data_store.unlock_fir()
        self._refresh_theme_menu()
        secret_name = THEMES["falling_in_reverse"]["name"]
        self.theme_var.set(secret_name)
        self._on_theme_changed()

        self._log("=" * 75)
        self._log("🔥 ─────────────────────────────────────────────────────────────────────────")
        self._log("🔥 [FALLING IN REVERSE — POPULAR MONSTER SYMPHONY ENGAGED]")
        self._log("🔥 'I got the whole world watching me burn... and I'm loving every minute of it.'")
        self._log("🔥 'They wanna cancel me, but I write the damn symphony!'")
        self._log("🔥 [MAXIMUM HEAT BRAND TAKEDOWN ENGINE INITIALIZED]")
        self._log("🔥 ─────────────────────────────────────────────────────────────────────────")
        self._log("=" * 75)
        self._status("🔥 FALLING IN REVERSE: Popular Monster Mode Active • Maximum Flame!")

        # Custom Themed FIR Crimson Obsidian Flame Modal
        win = tk.Toplevel(self)
        win.title("🔥 Falling In Reverse — Popular Monster")
        win.configure(bg="#09090B")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self._apply_dark_titlebar(win)

        # Center modal
        self._center_window(win, 520, 360)

        card = tk.Frame(win, bg="#141216", padx=20, pady=18, highlightbackground="#FF2A2A", highlightthickness=2)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(card, text="🔥 FALLING IN REVERSE", font=("Segoe UI", 16, "bold"), bg="#141216", fg="#FF2A2A").pack(anchor="center")
        tk.Label(card, text="POPULAR MONSTER • WATCH THE WORLD BURN", font=("Segoe UI", 8, "bold"), bg="#141216", fg="#FF6B1A").pack(anchor="center", pady=(2, 10))

        div = tk.Frame(card, bg="#FF2A2A", height=1)
        div.pack(fill="x", pady=(0, 12))

        tk.Label(card, text="I Think I'm Going Crazy • Zero Mercy on Counterfeits", font=("Segoe UI", 11, "bold"), bg="#141216", fg="#FDF2F4").pack(anchor="center")
        tk.Label(card, text="Flame Thrower Brand Protection  •  Pure Rock & Roll Precision", font=FONT_SM, bg="#141216", fg="#9CA3AF").pack(anchor="center", pady=(3, 10))

        quote_box = tk.Frame(card, bg="#09090B", padx=12, pady=8, highlightbackground="#3B1D24", highlightthickness=1)
        quote_box.pack(fill="x", pady=(0, 14))
        tk.Label(quote_box, text='"They wanna cancel me, but I write the damn symphony!"', font=("Georgia", 10, "italic"), bg="#09090B", fg="#FF2A2A").pack(anchor="center")
        tk.Label(quote_box, text="— Ronnie Radke", font=("Segoe UI", 8), bg="#09090B", fg="#9CA3AF").pack(anchor="center", pady=(2, 0))

        btn = tk.Button(card, text="🔥 Unleash The Symphony", command=win.destroy,
                        bg="#FF2A2A", fg="#FFFFFF", font=("Segoe UI", 10, "bold"),
                        relief="flat", padx=16, pady=5, activebackground="#FF6B1A", cursor="hand2")
        btn.pack(anchor="center")

    def _trigger_heimvis_easter_egg(self):
        """All-Seeing Eye & Heimvis / Jarvis AI Co-Pilot Easter Egg."""
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
        self._log("=" * 75)
        self._log("👁 ─────────────────────────────────────────────────────────────────────────")
        self._log("👁⚡ [HEIMVIS / JARVIS ONLINE] ALL-SEEING SURVEILLANCE PROTOCOLS ENGAGED!")
        self._log("🛡 Cross-marketplace synthetic radar scanning 150+ enterprise brand registries...")
        self._log("⚔ 'We don't just enforce against infringement. We dismantle the entire machine.'")
        self._log("🏆 CO-CREATOR RECOGNITION: Jerry Seidenstucker & Heimvis AI Architecture!")
        self._log("👁 ─────────────────────────────────────────────────────────────────────────")
        self._log("=" * 75)
        self._status("👁⚡ HEIMVIS ONLINE: All-Seeing Brand Protection Protocols Engaged!")

    def _trigger_eleanor_easter_egg(self):
        """Playful 1967 Shelby GT500 Eleanor Go-Baby-Go easter egg."""
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        # Reveal and switch to Eleanor theme
        if "eleanor" in THEMES:
            self._refresh_theme_menu()
            secret_name = THEMES["eleanor"]["name"]
            self.theme_var.set(secret_name)
            self._on_theme_changed()

        self._log("=" * 75)
        self._log("🐎 ─────────────────────────────────────────────────────────────────────────")
        self._log("🐎💨 [GO-BABY-GO!] 1967 SHELBY GT500 'ELEANOR' HAS ROARED TO LIFE!")
        self._log("🔥 427ci Big-Block Ford V8 + Nitrous Oxide System Engaged!")
        self._log("🌉 Flying over the Vincent Thomas Bridge at 160 MPH... Zero Counterfeits Survived!")
        self._log("🏆 ACHIEVEMENT UNLOCKED: Legendary 'Gone in 60 Seconds' Unicorn!")
        self._log("🐎 ─────────────────────────────────────────────────────────────────────────")
        self._log("=" * 75)
        self._status("🐎💨 GO-BABY-GO! 1967 Shelby GT500 Eleanor Nitrous Engaged!")

    def _trigger_konami_easter_egg(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        # Reveal and switch to secret Synthwave theme
        self._refresh_theme_menu()
        secret_name = THEMES["synthwave"]["name"]
        self.theme_var.set(secret_name)
        self._on_theme_changed()

        self._log("=" * 60)
        self._log("🎮 ★ ACHIEVEMENT UNLOCKED: THE KONAMI CODE ★ 🎮")
        self._log("✨ Supercharged Retro Synthwave 80s theme activated!")
        self._log("🚀 You have unlocked hidden developer superpowers!")
        self._log("=" * 60)
        messagebox.showinfo(
            "🎮 Konami Code Activated!",
            "★ ACHIEVEMENT UNLOCKED ★\n\n"
            "↑ ↑ ↓ ↓ ← → ← → B A\n\n"
            "🕹 Retro Synthwave 80s theme activated!\n"
            "Happy brand hunting!"
        )

    def _trigger_rickroll_easter_egg(self):
        """Playful Rick Astley trademark guardian easter egg."""
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
        self._log("=" * 70)
        self._log("🕺 ───────────────────────────────────────────────────────────────────")
        self._log("🎤 NEVER GONNA GIVE YOUR BRANDS UP!")
        self._log("🎤 NEVER GONNA LET INFRINGERS DOWN!")
        self._log("🎤 NEVER GONNA RUN AROUND AND DESERT YOUR IP! 🛡✨")
        self._log("🏆 ACHIEVEMENT UNLOCKED: Legendary Rick Astley Brand Guardian!")
        self._log("🕺 ───────────────────────────────────────────────────────────────────")
        self._log("=" * 70)
        self._status("🕺 🎤 Never gonna give your brands up! (Achievement Unlocked)")

    def _on_run_btn_double_click(self, event=None):
        """Double-clicking Run button engages Nitro Boost flair."""
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
        self._log("🏎💨 [NITRO BOOST ENGAGED] Twin-turbochargers spooling to 9,500 RPM... Search velocity +200%!")
        self._status("🏎💨 NITRO BOOST ENGAGED at 9,500 RPM!")

    def _on_title_click(self, event=None):
        """Clicking title bar triggers fun motivational enforcement badges and theme-specific quotes."""
        t_key = self.current_theme_key
        theme_quote_list = THEME_QUOTES.get(t_key)
        if theme_quote_list and isinstance(theme_quote_list, list):
            quote = theme_quote_list[self.quote_idx % len(theme_quote_list)]
        elif t_key == "falling_in_reverse":
            quote = FIR_QUOTES[self.quote_idx % len(FIR_QUOTES)]
        elif t_key == "continental":
            quote = CONTINENTAL_QUOTES[self.quote_idx % len(CONTINENTAL_QUOTES)]
        else:
            quote = QUOTES[self.quote_idx % len(QUOTES)]

        self.quote_idx += 1
        self._log(f"★ {quote}")
        self._status(quote)

    def _check_enforcement_milestones(self):
        """Check and log high-volume enterprise enforcement milestones."""
        total_res = len(self.results)
        milestones = [
            (50, "🎯 RECON SCOUT", "50 Suspicious Listings Identified!"),
            (100, "⚡ FIRST STRIKE", "100 Counterfeit Listings Harvested!"),
            (250, "🔍 IP SENTINEL", "250 Infringing Products Logged and Cataloged!"),
            (500, "🛡 ENFORCEMENT BATTALION", "500 Counterfeits Seized across Store Fronts!"),
            (1000, "⚔ BRAND DEFENDER", "1,000 Infringements Purged from the Marketplace!"),
            (2000, "🏆 ELITE BRAND ENFORCER", "2,000 Counterfeits Logged! (Monthly Target Reached!)"),
            (5000, "🚀 FLEET COMMANDER", "5,000 Counterfeit Assets Harvested! Master Enforcer!"),
            (10000, "👑 TITAN OF INDUSTRY", "10,000 Infringements Seized! Supreme Anti-Counterfeit Authority!"),
        ]
        if not hasattr(self, "achieved_milestones"):
            self.achieved_milestones = set()

        for threshold, badge, desc in milestones:
            if total_res >= threshold and threshold not in self.achieved_milestones:
                self.achieved_milestones.add(threshold)
                self._log("=" * 75)
                self._log(f"★ ─────────────────────────────────────────────────────────────────────────")
                self._log(f"★ 🏆 MILESTONE ACHIEVED: {badge} ({threshold:,} Listings) ★")
                self._log(f"★ {desc}")
                self._log(f"★ ─────────────────────────────────────────────────────────────────────────")
                self._log("=" * 75)
                self._status(f"🏆 MILESTONE: {badge} ({threshold:,} Listings)")

    # ══════════════════════════════════════════════════════════════════════════
    #  EXPORT
    # ══════════════════════════════════════════════════════════════════════════
    def _export(self):
        if not self.results and not self.staged_dossier:
            messagebox.showinfo("Export", "No results to export.")
            return

        export_items = list(self.results)
        if self.staged_dossier:
            total_staged = len(self.staged_dossier)
            total_active = len(self.results)
            msg = (
                f"You have {total_staged} listing(s) parked in your Staged Dossier and "
                f"{total_active} listing(s) in your active results table.\n\n"
                f"• [Yes]: Export MASTER DOSSIER (Combine both waves = {total_staged + total_active} listings)\n"
                f"• [No]: Export ACTIVE RESULTS only ({total_active} listings)\n"
                f"• [Cancel]: Cancel export"
            )
            ans = messagebox.askyesnocancel("Export Staged Dossier", msg, icon="question")
            if ans is None:
                return
            elif ans is True:
                seen_ids = {str(it.get("item_id", "")).strip() for it in export_items}
                for it in self.staged_dossier:
                    iid = str(it.get("item_id", "")).strip()
                    if iid not in seen_ids:
                        export_items.append(it)
                        seen_ids.add(iid)

        # Determine items to export: honor active Hide Benign filter so benign packaging is not exported
        if hasattr(self, "filter_hide_benign_var") and self.filter_hide_benign_var.get():
            export_items = [
                it for it in export_items
                if not (it.get("visual_benign") or str(it.get("threat_badge", "")).startswith("🟢 Benign"))
            ]

        if not export_items:
            messagebox.showinfo("Export", "No listings to export (all selected listings are classified as Benign Packaging).")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"enforcement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        if path:
            try:
                self.exporter.export(export_items, path)
                # Ingest verified exported results into Enterprise Brand Enforcement Registry
                seller_items = {}
                for item in export_items:
                    seller = item.get("seller") or "Unknown"
                    seller_items.setdefault(seller, []).append(item)
                for seller, s_items in seller_items.items():
                    self.data_store.record_enforcement_scan(seller, s_items)
                self._log(f"Exported {len(export_items)} rows → {path}")
                self._log(f"🛡 Logged {len(export_items)} verified listing(s) across {len(seller_items)} seller(s) into Enterprise Brand Enforcement Registry.")
                messagebox.showinfo("Exported", f"Saved {len(export_items)} verified listings to:\n{path}\n\n🛡 Logged into Enterprise Brand Enforcement Registry.")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _export_job_log(self):
        """Export comprehensive Job Audit Log & Summary Report."""
        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Log / Text file", "*.txt"), ("Log file", "*.log"), ("All files", "*.*")],
            initialfile=f"job_audit_log_{now_str}.txt"
        )
        if not path:
            return

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(" EBAY ENFORCEMENT HARVESTER - JOB AUDIT REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Export Date/Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Active Theme     : {self.theme['name']}")
        report_lines.append("Session Mode     : Browser Automation (Edge Stealth / Multi-Engine)")
        report_lines.append(f"Total Unique Listings Harvested : {len(self.results)}")
        report_lines.append("")

        report_lines.append("-" * 80)
        report_lines.append(" EXECUTED SEARCH JOBS BREAKDOWN")
        report_lines.append("-" * 80)

        if not self.executed_jobs:
            report_lines.append("  (No queued jobs were executed during this session)")
        else:
            for idx, job in enumerate(self.executed_jobs, 1):
                report_lines.append(f"[Job #{idx}] Target Brand: {job.get('brand', 'Unknown')}")
                report_lines.append(f"  • Execution Time    : {job.get('timestamp', '')}")
                report_lines.append(f"  • Target Store      : {job.get('store', '')}")
                report_lines.append(f"  • Resolved Seller   : {job.get('resolved_seller', job.get('store', ''))}")
                report_lines.append(f"  • Condition Filter  : {job.get('condition', 'all')}")
                report_lines.append(f"  • Listings Harvested: {job.get('total_harvested', 0)}")
                
                report_lines.append("  • Keywords Searched :")
                for term in job.get("includes", []):
                    cnt = job.get("term_counts", {}).get(term, "N/A")
                    report_lines.append(f"      - '{term}': {cnt} listings found")

                excludes = job.get("excludes", [])
                report_lines.append(f"  • Applied Exclusions ({len(excludes)} terms):")
                if excludes:
                    report_lines.append(f"      {', '.join(excludes)}")
                else:
                    report_lines.append("      (None)")
                report_lines.append("")

        report_lines.append("-" * 80)
        report_lines.append(" RAW ACTIVITY & CONSOLE LOG")
        report_lines.append("-" * 80)
        raw_log = self.log_text.get("1.0", "end").strip()
        report_lines.append(raw_log if raw_log else "(No activity log entries recorded)")
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append(" END OF AUDIT REPORT")
        report_lines.append("=" * 80)

        content = "\n".join(report_lines)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._log(f"Job audit log exported → {path}")
            messagebox.showinfo("Log Exported", f"Job Audit Log successfully saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export log: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    #  BROWSER & API SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    def _toggle_headless(self):
        is_headless = self.headless_var.get()
        self.scraper.headless = is_headless
        self.aliexpress_scraper.headless = is_headless
        self.wish_scraper.headless = is_headless
        self.temu_scraper.headless = is_headless
        self.mercadolibre_scraper.headless = is_headless
        self.redbubble_scraper.headless = is_headless
        self.printerval_scraper.headless = is_headless
        self.data_store.set_setting("headless", is_headless)
        self._log(f"Browser search mode: {'👻 Silent Background' if is_headless else '🖥 Visible Browser Window'}")

    def _toggle_api(self):
        if self.use_api.get():
            self.app_id_lbl.pack(side="left", padx=(3, 1), after=self.api_cb)
            self.app_id_entry.pack(side="left", after=self.app_id_lbl)
            self.cert_id_lbl.pack(side="left", padx=(3, 1), after=self.app_id_entry)
            self.cert_id_entry.pack(side="left", after=self.cert_id_lbl)
            self.save_keys_btn.pack(side="left", padx=2, after=self.cert_id_entry)
            self.app_id_entry.config(state="normal")
            self.cert_id_entry.config(state="normal")
        else:
            self.app_id_lbl.pack_forget()
            self.app_id_entry.pack_forget()
            self.cert_id_lbl.pack_forget()
            self.cert_id_entry.pack_forget()
            self.save_keys_btn.pack_forget()

    def _save_api_keys(self):
        self.data_store.set_setting("use_api", self.use_api.get())
        self.data_store.set_setting("api_app_id", self.api_app_id_var.get().strip())
        self.data_store.set_setting("api_cert_id", self.api_cert_id_var.get().strip())
        self._log("eBay API settings saved.")
        messagebox.showinfo("Saved", "API settings saved.")

    def _launch_meli_login(self):
        """Open a visible browser window to log in to Mercado Libre and permanently preserve session cookies."""
        meli_c = self.meli_country_var.get() if hasattr(self, "meli_country_var") else "Mexico"
        code_map = {
            "mexico": "MLM", "brazil": "MLB", "argentina": "MLA", "colombia": "MCO",
            "chile": "MLC", "peru": "MPE", "uruguay": "MLU"
        }
        site_code = "MLM"
        for k, v in code_map.items():
            if k in meli_c.lower():
                site_code = v
                break
        w_pos = self._get_browser_window_pos()
        self._log(f"🔑 Opening Mercado Libre ({meli_c} - {site_code}) authentication window in Microsoft Edge. Please log in—your authenticated session will be saved permanently!")
        self.mercadolibre_scraper.launch_interactive_auth(site_code=site_code, window_pos=w_pos)
        messagebox.showinfo("Mercado Libre Login", f"A browser window is opening to Mercado Libre ({meli_c}).\n\nPlease log in or create an account (you only need to do this once!).\n\nYour session cookies will be permanently stored for all future automated searches across this region.")

    def _launch_vinted_session(self):
        """Open a visible browser window to solve Cloudflare Turnstile challenge and save persistent clearance cookies."""
        v_c = self.vinted_country_var.get() if hasattr(self, "vinted_country_var") else "UK"
        reg_code = "UK"
        region_map = {
            "UK": ["UK", "United Kingdom"], "FR": ["France", "FR"], "DE": ["Germany", "DE"],
            "ES": ["Spain", "ES"], "IT": ["Italy", "IT"], "PL": ["Poland", "PL"],
            "US": ["United States", "US"], "NL": ["Netherlands", "NL"], "BE": ["Belgium", "BE"]
        }
        for code, names in region_map.items():
            if any(n in v_c for n in names):
                reg_code = code
                break
        w_pos = self._get_browser_window_pos()
        self._log(f"👗 Opening Vinted authentication window for {v_c} in Microsoft Edge. If Cloudflare prompts to 'Verify you are human' or accept cookies, please complete it.")
        self.vinted_scraper.launch_interactive_auth(region_code=reg_code, window_pos=w_pos)
        messagebox.showinfo("Vinted Connect & Cloudflare Sync", f"A browser window is opening to Vinted ({v_c}).\n\nIf Cloudflare asks to 'Verify you are human' or accept cookies, please complete it.\n\nYour clearance tokens will be permanently saved for all automated background sweeps!")

    def _launch_tiktok_session(self):
        """Open persistent Edge browser session to establish TikTok Shop cookies."""
        w_pos = self._get_browser_window_pos()
        self._log("🎵 Opening TikTok Shop authentication & anti-bot clearance window in Microsoft Edge...")
        threading.Thread(target=lambda: self.tiktok_scraper.launch_interactive_auth(window_pos=w_pos), daemon=True).start()
        messagebox.showinfo("TikTok Shop Connect", "A browser window is opening to TikTok Shop.\n\nIf prompted by a security check or slider puzzle, solve it once to establish verified session cookies.\n\nApollo will automatically save and use this session for all subsequent scans.")

    # ══════════════════════════════════════════════════════════════════════════
    #  ADHOC BATCH URL & EXCEL LISTING IMPORTER
    # ══════════════════════════════════════════════════════════════════════════
    def _open_adhoc_importer_window(self):
        """Open the Adhoc Batch URL & Excel Listing Importer dialog."""
        if self._win_importer and self._win_importer.winfo_exists():
            self._win_importer.lift()
            self._win_importer.focus_force()
            return

        t = self.theme
        win = tk.Toplevel(self)
        self._win_importer = win
        win.title("📥 Adhoc Batch URL & Excel Listing Importer — Multi-Marketplace Harvester")
        win.configure(bg=t["bg"])
        self._apply_dark_titlebar(win)

        # Center relative to main window
        self._center_window(win, 1040, 720)

        pad_f = tk.Frame(win, bg=t["bg"], padx=14, pady=12)
        pad_f.pack(fill="both", expand=True)

        # ── Header Banner ────────────────────────────────────────────────────
        head_f = tk.Frame(pad_f, bg=t["bg"])
        head_f.pack(fill="x", pady=(0, 8))

        tk.Label(head_f, text="📥 Adhoc Batch URL & Excel Listing Importer",
                 font=("Segoe UI", 13, "bold"), bg=t["bg"], fg=t["accent"]).pack(side="left")

        tk.Label(head_f, text="Instant Deep Metadata Scraping for Client Request Lists (eBay, Ali, Wish, Temu, MeLi)",
                 font=FONT_SM, bg=t["bg"], fg=t["subtext"]).pack(side="left", padx=12, pady=(2, 0))

        # ── Top KPI Stat Badges ──────────────────────────────────────────────
        kpi_f = tk.Frame(pad_f, bg=t["panel"], padx=12, pady=8)
        kpi_f.pack(fill="x", pady=(0, 8))

        kpi_labels = {}
        def _kpi(parent, title, val, key, color=None):
            f = tk.Frame(parent, bg=t["panel"], padx=12)
            f.pack(side="left", fill="y")
            tk.Label(f, text=title, font=("Segoe UI", 8, "bold"), bg=t["panel"], fg=t["subtext"]).pack(anchor="w")
            lbl = tk.Label(f, text=val, font=("Segoe UI", 12, "bold"), bg=t["panel"], fg=color or t["text"])
            lbl.pack(anchor="w")
            kpi_labels[key] = lbl

        _kpi(kpi_f, "📋 URLs in Batch", "0", "total")
        _kpi(kpi_f, "🌐 Marketplaces Detected", "None", "mkts", color=t["accent2"])
        _kpi(kpi_f, "✅ Successfully Scraped", "0", "success", color=t["success"])
        _kpi(kpi_f, "💰 Total Value Captured", "$0.00", "val", color=t["warning"])

        # ── Input Section: Paste Box + File Loader ───────────────────────────
        input_head = tk.Frame(pad_f, bg=t["bg"])
        input_head.pack(fill="x", pady=(4, 2))

        tk.Label(input_head, text="📋 Target Listing URLs (Paste raw URLs or upload spreadsheet):",
                 font=FONT_HEAD, bg=t["bg"], fg=t["accent"]).pack(side="left")

        url_count_lbl = tk.Label(input_head, text="0 URLs detected", font=FONT_SM, bg=t["bg"], fg=t["subtext"])
        url_count_lbl.pack(side="right")

        text_frame = tk.Frame(pad_f, bg=t["entry_bg"], highlightthickness=1, highlightbackground=t["border"])
        text_frame.pack(fill="both", expand=True, pady=(2, 6))

        url_text = tk.Text(text_frame, height=9, bg=t["entry_bg"], fg=t["text"],
                           insertbackground=t["text"], relief="flat", font=("Consolas", 10),
                           wrap="none")
        text_vsb = ttk.Scrollbar(text_frame, orient="vertical", command=url_text.yview)
        text_hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=url_text.xview)
        url_text.configure(yscrollcommand=text_vsb.set, xscrollcommand=text_hsb.set)

        text_vsb.pack(side="right", fill="y")
        text_hsb.pack(side="bottom", fill="x")
        url_text.pack(side="left", fill="both", expand=True)

        placeholder_txt = "# Paste listing URLs below (one per line, comma-separated, or mixed text):\nhttps://www.ebay.com/itm/123456789012\nhttps://www.aliexpress.us/item/3256809669065606.html\nhttps://www.wish.com/product/5e6b7c8d9a0b1c2d3e4f5a6b\nhttps://www.temu.com/goods.html?goods_id=601099512345\nhttps://articulo.mercadolibre.com.mx/MLM-1234567890-example"
        url_text.insert("1.0", placeholder_txt)
        url_text.config(fg=t["subtext"])

        def _clear_ph(e):
            if url_text.get("1.0", "end").strip() == placeholder_txt.strip():
                url_text.delete("1.0", "end")
                url_text.config(fg=t["text"])

        url_text.bind("<FocusIn>", _clear_ph)

        def _update_url_counter(e=None):
            raw = url_text.get("1.0", "end").strip()
            if raw == placeholder_txt.strip():
                url_count_lbl.config(text="0 URLs detected")
                kpi_labels["total"].config(text="0")
                kpi_labels["mkts"].config(text="None")
                return []
            urls = batch_importer.extract_urls_from_text(raw)
            url_count_lbl.config(text=f"{len(urls)} URLs detected")
            kpi_labels["total"].config(text=f"{len(urls):,}")

            mkts = set(batch_importer.detect_platform(u) for u in urls)
            if mkts:
                kpi_labels["mkts"].config(text=", ".join(sorted(mkts)))
            else:
                kpi_labels["mkts"].config(text="None")
            return urls

        url_text.bind("<KeyRelease>", _update_url_counter)

        # ── Toolbar: File Importer & Actions ──────────────────────────────────
        action_bar = tk.Frame(pad_f, bg=t["bg"])
        action_bar.pack(fill="x", pady=(0, 6))

        loaded_structured_items = []

        def _load_file():
            nonlocal loaded_structured_items
            path = filedialog.askopenfilename(
                title="Select Spreadsheet or URL List File",
                filetypes=[
                    ("Spreadsheet / URL List", "*.xlsx;*.xls;*.csv;*.txt"),
                    ("Excel Workbook (*.xlsx)", "*.xlsx"),
                    ("Excel 97-2003 (*.xls)", "*.xls"),
                    ("CSV File (*.csv)", "*.csv"),
                    ("Text File (*.txt)", "*.txt"),
                    ("All Files (*.*)", "*.*")
                ],
                parent=win
            )
            if not path:
                return
            
            override_brand = brand_var.get().strip()
            items, urls = batch_importer.extract_structured_listings_from_file(path, default_brand=override_brand)
            if not urls and not items:
                messagebox.showwarning("No Listings Found", f"No valid listing records or URLs were found in:\n{path}", parent=win)
                return

            loaded_structured_items = items
            url_text.delete("1.0", "end")
            url_text.insert("1.0", "\n".join(urls) + "\n")
            url_text.config(fg=t["text"])
            _update_url_counter()

            if items:
                status_lbl.config(
                    text=f"⚡ {len(items)} structured listings loaded from '{os.path.basename(path)}' (Title, Seller, Price, Photos ready)!",
                    fg=t["success"]
                )
                self._log(f"📥 Loaded {len(items)} structured listings from {os.path.basename(path)}")
                instant_import_btn.config(state="normal")
            else:
                status_lbl.config(text=f"Loaded {len(urls)} plain URL(s) from '{os.path.basename(path)}'. Ready to harvest.", fg=t["text"])
                self._log(f"📥 Loaded {len(urls)} listing URL(s) from {os.path.basename(path)}")

        def _paste_clipboard():
            nonlocal loaded_structured_items
            try:
                clip = win.clipboard_get()
                if clip:
                    curr = url_text.get("1.0", "end").strip()
                    if not curr or curr == placeholder_txt.strip():
                        url_text.delete("1.0", "end")
                        url_text.insert("1.0", clip.strip() + "\n")
                    else:
                        url_text.insert("end", "\n" + clip.strip() + "\n")
                    url_text.config(fg=t["text"])
                    _update_url_counter()
            except Exception:
                pass

        def _clear_urls():
            nonlocal loaded_structured_items
            loaded_structured_items = []
            url_text.delete("1.0", "end")
            url_text.config(fg=t["text"])
            _update_url_counter()
            status_lbl.config(text="Ready to harvest batch URLs.", fg=t["text"])

        self._btn(action_bar, "📂 Load Excel / CSV / TXT", _load_file).pack(side="left", padx=(0, 6))
        self._btn(action_bar, "📋 Paste Clipboard", _paste_clipboard).pack(side="left", padx=(0, 6))
        self._btn(action_bar, "🧹 Clear URLs", _clear_urls).pack(side="left", padx=(0, 6))

        tk.Label(action_bar, text="🏷 Brand Tag:", font=FONT_SM, bg=t["bg"], fg=t["accent"]).pack(side="left", padx=(14, 4))
        brand_var = tk.StringVar(value="⚡ Auto-Detect from Title")
        ds = getattr(self, "data_store", None)
        all_library_brands = sorted(list(ds.get_brands().keys())) if ds else []
        brand_choices = ["⚡ Auto-Detect from Title"] + all_library_brands
        brand_combo = ttk.Combobox(action_bar, textvariable=brand_var, values=brand_choices, width=30, state="readonly", font=FONT_SM)
        brand_combo.pack(side="left", padx=(0, 6))

        exec_frame = tk.Frame(pad_f, bg=t["panel"], padx=10, pady=8)
        exec_frame.pack(fill="x", pady=(4, 6))

        batch_running = [False]
        batch_stop = threading.Event()
        batch_pause = threading.Event()
        batch_pause.set()

        progress_var = tk.DoubleVar(value=0.0)
        p_bar = ttk.Progressbar(exec_frame, variable=progress_var, maximum=100)
        p_bar.pack(fill="x", pady=(0, 6))

        status_lbl = tk.Label(exec_frame, text="Ready to harvest batch URLs.", font=FONT_SM, bg=t["panel"], fg=t["text"])
        status_lbl.pack(side="left")

        run_btn = None
        stop_btn = None
        instant_import_btn = None

        def _direct_instant_import():
            nonlocal loaded_structured_items
            override_brand = brand_var.get().strip()
            
            # If structured items are cached from the loaded file, use them directly
            items_to_add = list(loaded_structured_items)
            
            # If user pasted raw URLs or edited the text box without a structured file, build instant baseline records
            if not items_to_add:
                raw_urls = _update_url_counter()
                if not raw_urls:
                    messagebox.showwarning("No Listings", "Please paste listing URLs or load a spreadsheet first.", parent=win)
                    return
                for u in raw_urls:
                    m_id = re.search(r'/itm/(?:[^/]+/)?(\d{10,14})', u) or re.search(r'(\d{10,14})', u)
                    item_id = m_id.group(1) if m_id else ""
                    mkt = batch_importer.detect_platform(u)
                    items_to_add.append({
                        "title": f"Imported Listing #{item_id}" if item_id else "Imported Web Listing",
                        "item_id": item_id,
                        "url": u,
                        "price": "$0.00",
                        "seller": "Unknown",
                        "location": "United States",
                        "image_url": "",
                        "marketplace": mkt,
                        "brand": override_brand if override_brand not in ("⚡ Auto-Detect from Title", "Auto-Detect", "") else "Automotive & Consumer Brands",
                        "product_type": "Accessories"
                    })

            if not items_to_add:
                return

            added_count = 0
            total_val = 0.0
            newly_added = []

            for item in items_to_add:
                # Apply brand override if selected by analyst
                if override_brand and override_brand not in ("⚡ Auto-Detect from Title", "Auto-Detect", ""):
                    item["brand"] = override_brand

                iid = item.get("item_id")
                dedup_key = iid if iid else item.get("url")
                if dedup_key and dedup_key not in self.seen_item_ids:
                    self.seen_item_ids.add(dedup_key)
                    self.results.append(item)
                    newly_added.append(item)
                    added_count += 1

                    # Extract numeric value
                    p_str = item.get("price", "")
                    m_p = re.search(r"[\d,]+(?:\.\d+)?", p_str)
                    if m_p:
                        try: total_val += float(m_p.group(0).replace(",", ""))
                        except ValueError: pass
                elif not dedup_key:
                    self.results.append(item)
                    newly_added.append(item)
                    added_count += 1

            if newly_added:
                self._update_results_table(newly_added)
                self._status(f"⚡ Instantly imported {added_count} listings from spreadsheet to Results table.")
                self._log(f"⚡ Instant Import: Added {added_count} pre-populated listings to Results table (Value: ${total_val:,.2f}).")
                kpi_labels["success"].config(text=f"{added_count:,}")
                kpi_labels["val"].config(text=f"${total_val:,.2f}")
                status_lbl.config(text=f"⚡ Successfully imported {added_count} listings in 0.05s!", fg=t["success"])
                progress_var.set(100)

                # Sound alert if enabled
                if self.sound_enabled_var.get():
                    try: winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except Exception: pass

                # Clean notification without multi-locale popup prompt
                messagebox.showinfo("Instant Import Complete", f"⚡ Successfully loaded {added_count} listing(s) directly into your Results table!", parent=win)
            else:
                messagebox.showinfo("Import Info", f"All {len(items_to_add)} listings are already present in your Results table (duplicates skipped).", parent=win)

        def _start_harvest():
            nonlocal loaded_structured_items
            urls = _update_url_counter()
            if not urls:
                messagebox.showwarning("No URLs", "Please paste one or more listing URLs or load a spreadsheet first.", parent=win)
                return

            if batch_running[0]:
                return

            batch_running[0] = True
            batch_stop.clear()
            batch_pause.set()

            run_btn.config(state="disabled")
            instant_import_btn.config(state="disabled")
            stop_btn.config(state="normal")

            override_brand = brand_var.get().strip()
            is_headless = self.headless_var.get()

            # Build fast lookup map from loaded structured items
            structured_by_url = {it.get("url", ""): it for it in loaded_structured_items if it.get("url")}
            structured_by_id = {str(it.get("item_id", "")): it for it in loaded_structured_items if it.get("item_id")}

            def _worker():
                scraped_count = 0
                total_val = 0.0
                total_urls = len(urls)

                self._log(f"🚀 Starting Adhoc Batch Harvest of {total_urls} URLs...")
                self._status(f"🚀 Starting Adhoc Batch Harvest of {total_urls} URLs...")

                for idx, u in enumerate(urls):
                    if batch_stop.is_set():
                        break

                    batch_pause.wait()

                    pct = int(((idx + 1) / total_urls) * 100)
                    mkt = batch_importer.detect_platform(u)
                    
                    self._status(f"📥 Batch Harvest [{idx+1}/{total_urls}]: Harvesting {mkt}...")
                    def _ui_prog(_idx=idx, _mkt=mkt, _pct=pct):
                        if self._win_importer and self._win_importer.winfo_exists():
                            status_lbl.config(text=f"[{_idx+1}/{total_urls}] Harvesting {_mkt} listing...", fg=t["text"])
                            progress_var.set(_pct)
                    self.after(0, _ui_prog)

                    try:
                        # Check if we already have complete structured data from file
                        cached_item = structured_by_url.get(u)
                        if not cached_item:
                            m_id = re.search(r'/itm/(?:[^/]+/)?(\d{10,14})', u) or re.search(r'(\d{10,14})', u)
                            if m_id:
                                cached_item = structured_by_id.get(m_id.group(1))

                        # If cached item has valid title and seller, use it directly
                        if cached_item and cached_item.get("title") and not str(cached_item.get("title")).startswith("Listing #") and not str(cached_item.get("title")).startswith("Imported Listing") and cached_item.get("seller") not in ("Unknown", "eBay Seller", ""):
                            item = dict(cached_item)
                        elif cached_item and cached_item.get("title") and not str(cached_item.get("title")).startswith("Listing #") and not str(cached_item.get("title")).startswith("Imported Listing"):
                            # File provided a valid title! Fetch live metadata (seller/price/photo) but strictly preserve file title
                            fetched = batch_importer.fetch_single_listing(u, default_brand=override_brand, headless=is_headless)
                            item = dict(cached_item)
                            if fetched:
                                if fetched.get("seller") and fetched.get("seller") not in ("Unknown", "eBay Seller", ""):
                                    item["seller"] = fetched["seller"]
                                if fetched.get("image_url") and not item.get("image_url"):
                                    item["image_url"] = fetched["image_url"]
                                if fetched.get("price") and item.get("price") in ("$0.00", "", "$0"):
                                    item["price"] = fetched["price"]
                                if fetched.get("seller_origin"):
                                    item["seller_origin"] = fetched["seller_origin"]
                        else:
                            item = batch_importer.fetch_single_listing(u, default_brand=override_brand, headless=is_headless)

                        if item:
                            if override_brand and override_brand not in ("⚡ Auto-Detect from Title", "Auto-Detect", ""):
                                item["brand"] = override_brand

                            iid = item.get("item_id")
                            dedup_key = iid if iid else item.get("url")
                            if dedup_key and dedup_key not in self.seen_item_ids:
                                self.seen_item_ids.add(dedup_key)
                                self.results.append(item)
                                scraped_count += 1

                                # Extract numeric value
                                p_str = item.get("price", "")
                                m_p = re.search(r"[\d,]+(?:\.\d+)?", p_str)
                                if m_p:
                                    try: total_val += float(m_p.group(0).replace(",", ""))
                                    except ValueError: pass

                                def _ui_add(_item=item, _cnt=scraped_count, _val=total_val):
                                    self._update_results_table([_item])
                                    if self._win_importer and self._win_importer.winfo_exists():
                                        kpi_labels["success"].config(text=f"{_cnt:,}")
                                        kpi_labels["val"].config(text=f"${_val:,.2f}")
                                self.after(0, _ui_add)
                                self._log(f"  ✓ [{mkt}] Harvested: '{item.get('title')[:55]}...' ({item.get('price')})")
                            elif not dedup_key:
                                self.results.append(item)
                                scraped_count += 1
                                def _ui_add2(_item=item, _cnt=scraped_count):
                                    self._update_results_table([_item])
                                    if self._win_importer and self._win_importer.winfo_exists():
                                        kpi_labels["success"].config(text=f"{_cnt:,}")
                                self.after(0, _ui_add2)
                            else:
                                self._log(f"  ℹ [{mkt}] Skipped duplicate Item ID: {iid}")
                    except Exception as e:
                        self._log(f"  ❌ Error on {u}: {e}", error=True)

                    time.sleep(0.1)

                def _ui_done(_scraped=scraped_count, _tot=total_urls):
                    batch_running[0] = False
                    if self._win_importer and self._win_importer.winfo_exists():
                        run_btn.config(state="normal")
                        instant_import_btn.config(state="normal")
                        stop_btn.config(state="disabled")
                        status_lbl.config(text=f"Completed! Harvested {_scraped}/{_tot} listings.", fg=t["success"])
                        progress_var.set(100)

                    # Sound alert if enabled
                    if self.sound_enabled_var.get():
                        try: winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                        except Exception: pass

                    self._log(f"🏁 Adhoc Batch Import Complete: Successfully processed {_scraped} of {_tot} listings. Added to Results table.")
                    self._status(f"🏁 Batch Import Complete: {_scraped}/{_tot} listings harvested.")
                    target_parent = self._win_importer if (self._win_importer and self._win_importer.winfo_exists()) else self
                    messagebox.showinfo("Batch Harvest Complete",
                                        f"Harvest Complete!\n\nSuccessfully processed {_scraped} of {_tot} listings.\n\nAll listings have been added to your Main Results Table, Threat Intelligence Hub, and Excel export.",
                                        parent=target_parent)

                self.after(0, _ui_done)

            t_thread = threading.Thread(target=_worker, daemon=True)
            t_thread.start()

        def _stop_harvest():
            if batch_running[0]:
                batch_stop.set()
                if self._win_importer and self._win_importer.winfo_exists():
                    status_lbl.config(text="Stopping batch harvest...")
                    stop_btn.config(state="disabled")
                self._log("⏹ Stopping adhoc batch harvest...")

        def _on_win_close():
            if batch_running[0]:
                self._log("ℹ Batch Importer window closed. Background scraping will continue running and notify when complete.")
            self._win_importer = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_win_close)

        stop_btn = self._btn(exec_frame, "⏹ Stop", _stop_harvest, danger=True)
        stop_btn.pack(side="right", padx=(4, 0))
        stop_btn.config(state="disabled")

        run_btn = self._btn(exec_frame, "🌐 Scrape Web", _start_harvest)
        run_btn.pack(side="right", padx=(4, 0))

        instant_import_btn = self._btn(exec_frame, "⚡ Instant Load to Results (0s)", _direct_instant_import, accent=True)
        instant_import_btn.pack(side="right", padx=(4, 0))

    _open_batch_import_dialog = _open_adhoc_importer_window

    # ══════════════════════════════════════════════════════════════════════════
    #  ENTERPRISE BRAND ENFORCEMENT & RECIDIVISM REGISTRY
    # ══════════════════════════════════════════════════════════════════════════
    def _open_enforcement_registry_window(self):
        """Open the executive Enterprise Brand Enforcement & Recidivism Registry dialog."""
        if self._win_registry and self._win_registry.winfo_exists():
            self._win_registry.lift()
            self._win_registry.focus_force()
            return

        t = self.theme
        win = tk.Toplevel(self)
        self._win_registry = win
        win.title("🛡 Enterprise Brand Enforcement & Recidivism Registry")
        win.configure(bg=t["bg"])
        win.geometry("1180x680")
        win.minsize(980, 580)
        self._apply_dark_titlebar(win)

        # Center relative to main window
        self._center_window(win, 1180, 680)

        pad_f = tk.Frame(win, bg=t["bg"], padx=14, pady=12)
        pad_f.pack(fill="both", expand=True)

        # ── Header Banner ────────────────────────────────────────────────────
        head_f = tk.Frame(pad_f, bg=t["bg"])
        head_f.pack(fill="x", pady=(0, 8))

        tk.Label(head_f, text="🛡", font=("Segoe UI", 13), bg=t["bg"], fg=t["accent"]).pack(side="left")
        tk.Label(head_f, text="Enterprise Brand Enforcement & Recidivism Registry",
                 font=("Segoe UI", 13, "bold"), bg=t["bg"], fg=t["accent"]).pack(side="left", padx=(4, 0))

        tk.Label(head_f, text="Cross-Brand Infringement Tracking & Repeat Offender Intelligence",
                 font=FONT_SM, bg=t["bg"], fg=t["subtext"]).pack(side="left", padx=12, pady=(2, 0))

        # ── Top KPI Stat Badges ──────────────────────────────────────────────
        kpi_f = tk.Frame(pad_f, bg=t["panel"], padx=12, pady=8)
        kpi_f.pack(fill="x", pady=(0, 8))

        kpi_labels = {}
        def _kpi(parent, title, val, key, color=None):
            f = tk.Frame(parent, bg=t["panel"], padx=12)
            f.pack(side="left", fill="y")
            tk.Label(f, text=title, font=("Segoe UI", 8, "bold"), bg=t["panel"], fg=t["subtext"]).pack(anchor="w")
            lbl = tk.Label(f, text=val, font=("Segoe UI", 12, "bold"), bg=t["panel"], fg=color or t["text"])
            lbl.pack(anchor="w")
            kpi_labels[key] = lbl

        _kpi(kpi_f, "🏬 Stores Harvested", "0", "stores")
        _kpi(kpi_f, "🚨 Repeat Offender Stores", "0", "repeat", color=t["danger"])
        _kpi(kpi_f, "📦 Infringing Listings Captured", "0", "items", color=t["accent"])
        _kpi(kpi_f, "💰 Total Counterfeit Market Value", "$0.00", "val", color=t["success"])

        def _refresh_kpis():
            reg_data = self.data_store.get_enforcement_registry()
            total_stores = len(reg_data)
            repeat_offenders = sum(1 for d in reg_data.values() if d.get("scan_count", 1) > 1 or d.get("total_listings", 0) > 10)
            total_infringing_items = sum(d.get("total_listings", len(d.get("items", []))) for d in reg_data.values())
            total_infringing_val = sum(d.get("total_value", 0.0) for d in reg_data.values())

            if "stores" in kpi_labels: kpi_labels["stores"].config(text=f"{total_stores:,}")
            if "repeat" in kpi_labels: kpi_labels["repeat"].config(text=f"{repeat_offenders:,}")
            if "items" in kpi_labels: kpi_labels["items"].config(text=f"{total_infringing_items:,}")
            if "val" in kpi_labels: kpi_labels["val"].config(text=f"${total_infringing_val:,.2f}")

        _refresh_kpis()

        # ── Filter & Search Toolbar ──────────────────────────────────────────
        filter_toolbar = tk.Frame(pad_f, bg=t["bg"])
        filter_toolbar.pack(fill="x", pady=(0, 6))

        tk.Label(filter_toolbar, text="🔍 Filter:", font=FONT_SM, bg=t["bg"], fg=t["accent"]).pack(side="left", padx=(0, 4))
        
        reg_col_var = tk.StringVar(value="All Columns")
        reg_cols = ["All Columns", "Store / Seller", "Status", "Brands", "Product Types", "Locations", "Est. Value"]
        reg_col_combo = ttk.Combobox(filter_toolbar, textvariable=reg_col_var,
                                     values=reg_cols, width=13, state="readonly", font=FONT_SM)
        reg_col_combo.pack(side="left", padx=(0, 6))

        reg_filter_var = tk.StringVar()
        reg_filter_entry = tk.Entry(filter_toolbar, textvariable=reg_filter_var, width=20,
                                    bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"],
                                    relief="flat", font=FONT_SM)
        reg_filter_entry.pack(side="left", padx=(0, 6))

        offense_filter_var = tk.StringVar(value="All Stores")
        offense_combo = ttk.Combobox(filter_toolbar, textvariable=offense_filter_var,
                                     values=["All Stores", "🚨 Repeat Offenders Only", "⚠ First Strike Only"],
                                     state="readonly", width=20, font=FONT_SM)
        offense_combo.pack(side="left", padx=(0, 6))

        def _clear_reg_filter():
            reg_filter_var.set("")
            offense_filter_var.set("All Stores")
            reg_col_var.set("All Columns")

        def _select_all_reg_visible():
            ch = tree.get_children()
            if ch:
                tree.selection_set(ch)

        self._btn(filter_toolbar, "✕ Clear", _clear_reg_filter).pack(side="left", padx=(0, 4))
        self._btn(filter_toolbar, "✓ Select All Visible", _select_all_reg_visible).pack(side="left", padx=(0, 4))

        # ── Treeview Table ───────────────────────────────────────────────────
        tree_frame = tk.Frame(pad_f, bg=t["bg"])
        tree_frame.pack(fill="both", expand=True)

        cols = ("seller", "status", "brands", "product_types", "listings", "total_val", "locations", "first_seen", "last_scanned", "scans")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
        
        col_headers = {
            "seller": "Store / Seller Name",
            "status": "Offense Status",
            "brands": "Brands Infringed",
            "product_types": "Product Types",
            "listings": "Listings",
            "total_val": "Est. Market Value ($)",
            "locations": "Locations",
            "first_seen": "First Detected",
            "last_scanned": "Last Scanned",
            "scans": "Scans"
        }
        col_w = {
            "seller": 140,
            "status": 120,
            "brands": 150,
            "product_types": 140,
            "listings": 65,
            "total_val": 120,
            "locations": 120,
            "first_seen": 110,
            "last_scanned": 110,
            "scans": 50
        }
        for c in cols:
            tree.heading(c, text=col_headers[c])
            tree.column(c, width=col_w[c], minwidth=40)

        self._style_tree(tree)
        tree.tag_configure("repeat", foreground=t["danger"])
        tree.tag_configure("normal", foreground=t["text"])

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        def _matches_reg_query(seller, status, brands_str, pts_str, locs_str, total_val_str, query_str, col_target):
            if not query_str:
                return True
            
            c_key = col_target.lower().strip()
            if "seller" in c_key or "store" in c_key:
                target_text = seller
            elif "status" in c_key:
                target_text = status
            elif "brand" in c_key:
                target_text = brands_str
            elif "product" in c_key:
                target_text = pts_str
            elif "loc" in c_key:
                target_text = locs_str
            elif "val" in c_key or "price" in c_key:
                target_text = total_val_str
            else:
                target_text = f"{seller} {status} {brands_str} {pts_str} {locs_str} {total_val_str}"

            target_lower = target_text.lower()

            import shlex
            try:
                raw_tokens = shlex.split(query_str)
            except Exception:
                raw_tokens = query_str.split()

            positive_tokens = []
            negative_tokens = []

            for tok in raw_tokens:
                tok = tok.strip()
                if not tok:
                    continue
                if tok.startswith("-") and len(tok) > 1:
                    negative_tokens.append(tok[1:].lower())
                elif tok.startswith("+") and len(tok) > 1:
                    positive_tokens.append(tok[1:].lower())
                else:
                    positive_tokens.append(tok.lower())

            for neg in negative_tokens:
                if neg in target_lower:
                    return False

            for pos in positive_tokens:
                if pos not in target_lower:
                    return False

            return True

        def _populate_tree():
            tree.delete(*tree.get_children())
            q = reg_filter_var.get().strip()
            c_target = reg_col_var.get()
            off_f = offense_filter_var.get()
            cur_reg = self.data_store.get_enforcement_registry()

            for seller, data in sorted(cur_reg.items(), key=lambda x: x[1].get("total_value", 0.0), reverse=True):
                scans = data.get("scan_count", 1)
                is_repeat = scans > 1 or data.get("total_listings", 0) > 10
                status = "🚨 REPEAT OFFENDER" if is_repeat else "⚠ FIRST STRIKE"

                if off_f == "🚨 Repeat Offenders Only" and not is_repeat:
                    continue
                if off_f == "⚠ First Strike Only" and is_repeat:
                    continue

                brands_str = ", ".join(data.get("brands", []))
                pts_str = ", ".join(data.get("product_types", []))
                locs_str = ", ".join(data.get("locations", []))
                val_str = f"${data.get('total_value', 0.0):,.2f}"

                if q and not _matches_reg_query(seller, status, brands_str, pts_str, locs_str, val_str, q, c_target):
                    continue

                tree.insert("", "end", iid=seller, values=(
                    seller,
                    status,
                    brands_str,
                    pts_str,
                    data.get("total_listings", len(data.get("items", []))),
                    val_str,
                    locs_str,
                    data.get("first_seen", ""),
                    data.get("last_scanned", ""),
                    scans
                ), tags=("repeat" if is_repeat else "normal",))

        reg_filter_var.trace_add("write", lambda *a: _populate_tree())
        reg_col_combo.bind("<<ComboboxSelected>>", lambda e: _populate_tree())
        offense_combo.bind("<<ComboboxSelected>>", lambda e: _populate_tree())
        _populate_tree()

        # ── Bottom Action Toolbar ────────────────────────────────────────────
        btn_row = tk.Frame(pad_f, bg=t["bg"])
        btn_row.pack(fill="x", pady=(10, 0))

        def _export_dossier():
            cur_reg = self.data_store.get_enforcement_registry()
            if not cur_reg:
                messagebox.showinfo("Empty Registry", "No store enforcement records to export.", parent=win)
                return
            now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                initialfile=f"A2C2_Store_Recidivism_Dossier_{now_str}.xlsx",
                parent=win
            )
            if path:
                try:
                    self.exporter.export_a2c2_dossier(cur_reg, path)
                    self._log(f"📄 A2C2 Master Store Dossier exported → {path}")
                    messagebox.showinfo("Dossier Exported", f"Successfully exported A2C2 Store Recidivism Dossier to:\n{path}", parent=win)
                except Exception as ex:
                    messagebox.showerror("Export Error", str(ex), parent=win)

        def _inspect_selected_seller():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Select Store", "Select a store in the registry table first.", parent=win)
                return
            seller_key = sel[0]
            cur_reg = self.data_store.get_enforcement_registry()
            if seller_key in cur_reg:
                self._open_seller_items_inspector(seller_key, cur_reg[seller_key])

        def _add_selected_sellers_to_stores():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Select Store", "Select one or more stores to add to the target stores list.", parent=win)
                return
            
            raw_text = self.store_text.get("1.0", "end").strip()
            is_placeholder = (not raw_text or raw_text == getattr(self, "store_placeholder", "").strip() or 
                              "Global eBay Search" in raw_text or "store1" in raw_text or "High Table contracts" in raw_text)
            
            existing_lines = [] if is_placeholder else [line.strip() for line in raw_text.splitlines() if line.strip()]
            existing_set = {line.lower() for line in existing_lines}
            
            added_count = 0
            for seller_key in sel:
                s_clean = str(seller_key).strip()
                if s_clean and s_clean.lower() not in existing_set:
                    existing_lines.append(s_clean)
                    existing_set.add(s_clean.lower())
                    added_count += 1
            
            self.store_text.delete("1.0", "end")
            self.store_text.insert("1.0", "\n".join(existing_lines))
            self.store_text.config(fg=t["text"])
            self._log(f"➕ Added {added_count} seller(s) from Enforcement Registry to Target Stores list ({len(existing_lines)} total stores).")
            self._status(f"Added {added_count} seller(s) to Target Stores list.")

        def _queue_reenforcement_sweep():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Select Store", "Select one or more stores to re-enforce.", parent=win)
                return
            _add_selected_sellers_to_stores()
            self._queue_portfolio_preset()
            self._log(f"⚡ Queued re-enforcement sweep for {len(sel)} store(s) across active portfolio.")
            self._status(f"Queued re-enforcement sweep for {len(sel)} store(s).")

        def _deduplicate_registry():
            """Deduplicate stores and items across the entire A2C2 Registry."""
            cur_reg = self.data_store.get_enforcement_registry()
            if not cur_reg:
                messagebox.showinfo("Deduplicate Registry", "Enforcement registry is empty.", parent=win)
                return

            purged_items = 0
            merged_stores = 0
            cleaned_reg = {}

            for s_name, data in cur_reg.items():
                canon_key = s_name.strip()
                if not canon_key:
                    continue

                if canon_key not in cleaned_reg:
                    cleaned_reg[canon_key] = {
                        "brands": set(data.get("brands", [])),
                        "product_types": set(data.get("product_types", [])),
                        "locations": set(data.get("locations", [])),
                        "items": [],
                        "scan_count": data.get("scan_count", 1),
                        "first_seen": data.get("first_seen", ""),
                        "last_scanned": data.get("last_scanned", "")
                    }
                else:
                    merged_stores += 1
                    cleaned_reg[canon_key]["brands"].update(data.get("brands", []))
                    cleaned_reg[canon_key]["product_types"].update(data.get("product_types", []))
                    cleaned_reg[canon_key]["locations"].update(data.get("locations", []))
                    cleaned_reg[canon_key]["scan_count"] += data.get("scan_count", 1)

                seen_item_ids = {str(it.get("item_id", "")).strip() for it in cleaned_reg[canon_key]["items"] if it.get("item_id")}
                for it in data.get("items", []):
                    iid = str(it.get("item_id", "")).strip()
                    if iid and iid in seen_item_ids:
                        purged_items += 1
                        continue
                    if iid:
                        seen_item_ids.add(iid)
                    cleaned_reg[canon_key]["items"].append(it)

            final_dict = {}
            for k, v in cleaned_reg.items():
                total_val = 0.0
                for it in v["items"]:
                    m_p = re.search(r"[\d,]+(?:\.\d+)?", str(it.get("price", "")))
                    if m_p:
                        try: total_val += float(m_p.group(0).replace(",", ""))
                        except Exception: pass
                final_dict[k] = {
                    "brands": sorted(list(v["brands"])),
                    "product_types": sorted(list(v["product_types"])),
                    "locations": sorted(list(v["locations"])),
                    "items": v["items"],
                    "total_listings": len(v["items"]),
                    "total_value": round(total_val, 2),
                    "scan_count": v["scan_count"],
                    "first_seen": v["first_seen"],
                    "last_scanned": v["last_scanned"]
                }

            self.data_store.save_enforcement_registry(final_dict)
            _populate_tree()
            _refresh_kpis()
            self._log(f"🧹 A2C2 Registry Deduplicated: Merged {merged_stores} duplicate store(s), purged {purged_items} duplicate listing(s).")
            messagebox.showinfo("Registry Deduplicated", f"Registry Cleaned Successfully!\n\n• Merged Duplicate Stores: {merged_stores}\n• Duplicate Listings Purged: {purged_items}\n• Total Clean Stores in Registry: {len(final_dict)}", parent=win)

        def _edit_selected_seller_intel():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Select Store", "Select a store in the registry table first.", parent=win)
                return
            seller_key = sel[0]
            cur_reg = self.data_store.get_enforcement_registry()
            if seller_key not in cur_reg:
                return

            entry_data = cur_reg[seller_key]
            
            edit_win = tk.Toplevel(win)
            edit_win.title(f"✏ Edit Seller Intel — {seller_key}")
            edit_win.configure(bg=t["bg"])
            edit_win.geometry("520x360")
            edit_win.minsize(460, 300)
            self._apply_dark_titlebar(edit_win)
            edit_win.transient(win)
            edit_win.grab_set()

            # Center relative to parent
            edit_win.update_idletasks()
            ex = win.winfo_rootx() + (win.winfo_width() - 520) // 2
            ey = win.winfo_rooty() + (win.winfo_height() - 360) // 2
            edit_win.geometry(f"520x360+{ex}+{ey}")

            ef = tk.Frame(edit_win, bg=t["bg"], padx=16, pady=14)
            ef.pack(fill="both", expand=True)

            tk.Label(ef, text=f"✏ Edit Seller Threat Intelligence", font=FONT_HEAD, bg=t["bg"], fg=t["accent"]).pack(anchor="w", pady=(0, 10))

            def _row(parent, label_text, default_val=""):
                f = tk.Frame(parent, bg=t["bg"])
                f.pack(fill="x", pady=4)
                tk.Label(f, text=label_text, font=FONT_BOLD, bg=t["bg"], fg=t["text"], width=18, anchor="w").pack(side="left")
                var = tk.StringVar(value=str(default_val))
                ent = tk.Entry(f, textvariable=var, font=FONT_NORM, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], relief="flat")
                ent.pack(side="left", fill="x", expand=True)
                return var

            name_v = _row(ef, "Store / Handle:", seller_key)
            origin_v = _row(ef, "Corporate Origin:", entry_data.get("country", entry_data.get("seller_origin", "")))
            locs_v = _row(ef, "3PL Locations:", ", ".join(entry_data.get("locations", [])))
            notes_v = _row(ef, "Threat Notes / Tags:", entry_data.get("threat_notes", ""))

            btn_f = tk.Frame(ef, bg=t["bg"])
            btn_f.pack(fill="x", pady=(16, 0))

            def _save_intel():
                new_name = name_v.get().strip()
                if not new_name:
                    messagebox.showwarning("Invalid Name", "Store name cannot be blank.", parent=edit_win)
                    return
                new_origin = origin_v.get().strip()
                new_locs = [x.strip() for x in locs_v.get().split(",") if x.strip()]
                new_notes = notes_v.get().strip()

                entry_data["country"] = new_origin
                entry_data["seller_origin"] = new_origin
                entry_data["locations"] = new_locs
                entry_data["threat_notes"] = new_notes

                if new_name != seller_key:
                    del cur_reg[seller_key]
                    cur_reg[new_name] = entry_data
                else:
                    cur_reg[seller_key] = entry_data

                self.data_store.save_enforcement_registry(cur_reg)
                if new_origin:
                    self.data_store.set_seller_intel(new_name, new_origin)

                _populate_tree()
                _refresh_kpis()
                self._log(f"✏ Updated threat intelligence for seller: {new_name} (Origin: {new_origin})")
                messagebox.showinfo("Intel Saved", f"Successfully updated threat intelligence for '{new_name}'!", parent=edit_win)
                edit_win.destroy()

            self._btn(btn_f, "💾 Save Intel", _save_intel, accent=True).pack(side="right", padx=(6, 0))
            self._btn(btn_f, "Cancel", edit_win.destroy).pack(side="right")

        def _delete_selected_entry():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Select Store", "Select an entry to remove.", parent=win)
                return
            if messagebox.askyesno("Delete Entry", f"Remove {len(sel)} selected store record(s) from registry?", parent=win):
                for seller_key in sel:
                    self.data_store.delete_registry_entry(seller_key)
                _populate_tree()
                _refresh_kpis()
                self._log(f"🗑 Removed {len(sel)} store record(s) from Enforcement Registry.")

        self._btn(btn_row, "📄 Export Enterprise Dossier (.xlsx)", _export_dossier, accent=True).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "📄 Import VeRO Disclosures", self._open_vero_disclosure_modal, accent=True).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "✏ Edit Seller Intel", _edit_selected_seller_intel).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "🔍 Inspect Store Listings", _inspect_selected_seller).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "➕ Add to Stores", _add_selected_sellers_to_stores).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "⚡ Queue Re-Enforcement Sweep", _queue_reenforcement_sweep).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "🧹 Deduplicate Registry", _deduplicate_registry).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "🗑 Remove Store Entry", _delete_selected_entry, danger=True).pack(side="left", padx=(0, 6))

        self._btn(btn_row, "✕ Close", win.destroy).pack(side="right")
        tree.bind("<Double-1>", lambda e: _inspect_selected_seller())

    def _open_seller_items_inspector(self, seller_name: str, seller_data: dict):
        """Open detailed inspector for all captured listings under a specific seller."""
        t = self.theme
        win = tk.Toplevel(self)
        win.title(f"🔍 Seller Listings Inspector — {seller_name}")
        win.configure(bg=t["bg"])
        win.geometry("980x540")
        win.minsize(800, 420)
        self._apply_dark_titlebar(win)

        # Center relative to main window
        self._center_window(win, 980, 540)

        pad_f = tk.Frame(win, bg=t["bg"], padx=12, pady=10)
        pad_f.pack(fill="both", expand=True)

        head_f = tk.Frame(pad_f, bg=t["panel"], padx=10, pady=8)
        head_f.pack(fill="x", pady=(0, 8))

        tk.Label(head_f, text=f"Store / Seller: {seller_name}", font=("Segoe UI", 11, "bold"),
                 bg=t["panel"], fg=t["accent"]).pack(side="left")

        val_str = f"Total Value: ${seller_data.get('total_value', 0.0):,.2f}  •  {seller_data.get('total_listings', len(seller_data.get('items', [])))} Listing(s)"
        tk.Label(head_f, text=val_str, font=FONT_SM, bg=t["panel"], fg=t["text"]).pack(side="right")

        tree_frame = tk.Frame(pad_f, bg=t["bg"])
        tree_frame.pack(fill="both", expand=True)

        cols = ("brand", "product_type", "title", "item_id", "price", "location", "url")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        col_w = {"brand": 80, "product_type": 120, "title": 300, "item_id": 110, "price": 80, "location": 110, "url": 150}
        for c in cols:
            tree.heading(c, text=self.col_labels.get(c, c.title()))
            tree.column(c, width=col_w.get(c, 100))
        self._style_tree(tree)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        for it in seller_data.get("items", []):
            tree.insert("", "end", values=(
                it.get("brand", ""),
                it.get("product_type", ""),
                it.get("title", ""),
                it.get("item_id", ""),
                it.get("price", ""),
                it.get("location", ""),
                it.get("url", "")
            ))

        def _open_row_url(e):
            sel = tree.focus()
            if sel:
                vals = tree.item(sel)["values"]
                if len(vals) > 6 and vals[6]:
                    webbrowser.open(vals[6])

        tree.bind("<Double-1>", _open_row_url)

        btn_row = tk.Frame(pad_f, bg=t["bg"])
        btn_row.pack(fill="x", pady=(8, 0))
        tk.Label(btn_row, text="💡 Double-click any listing to open live on eBay",
                 font=FONT_SM, bg=t["bg"], fg=t["subtext"]).pack(side="left")
        self._btn(btn_row, "✕ Close", win.destroy, accent=True).pack(side="right")

    def _show_about_dialog(self):
        """Show About, Apollo Ethos & Architecture, and Intellectual Property Disclaimer dialog."""
        t = self.theme
        win = tk.Toplevel(self)
        win.title("About ☀ Apollo Brand Intelligence")
        win.configure(bg=t["bg"])
        win.geometry("880x700")
        win.minsize(820, 620)
        win.transient(self)
        win.grab_set()

        self._apply_dark_titlebar(win)
        self._load_app_icon(win)
        self._center_window(win, 880, 700)

        # Easter egg key listener (Dom, Eleanor, Wick, Brundo)
        about_word_buf = [""]
        def _on_about_key(e):
            if e.char and e.char.isalnum():
                about_word_buf[0] += e.char.lower()
                if any(w in about_word_buf[0] for w in ("dom", "quartermile", "nos", "toretto")):
                    self._trigger_easter_egg()
                    about_word_buf[0] = ""
                elif any(w in about_word_buf[0] for w in ("eleanor", "gobabygo", "shelby")):
                    self._trigger_eleanor_easter_egg()
                    about_word_buf[0] = ""
                elif any(w in about_word_buf[0] for w in ("wick", "continental", "johnwick")):
                    self._trigger_wick_easter_egg()
                    about_word_buf[0] = ""
                elif any(w in about_word_buf[0] for w in ("brundo", "goodboy", "lab", "k9")):
                    self._trigger_brundo_easter_egg()
                    about_word_buf[0] = ""
                elif any(w in about_word_buf[0] for w in ("fir", "fallinginreverse", "ronnie", "radke")):
                    self._trigger_fir_easter_egg()
                    about_word_buf[0] = ""
        win.bind("<Key>", _on_about_key)

        pad_f = tk.Frame(win, bg=t["bg"], padx=20, pady=16)
        pad_f.pack(fill="both", expand=True)

        # ── Header ───────────────────────────────────────────────────────────
        head_f = tk.Frame(pad_f, bg=t["bg"])
        head_f.pack(fill="x", pady=(0, 10))

        title_row = tk.Frame(head_f, bg=t["bg"])
        title_row.pack(anchor="w")
        tk.Label(title_row, text="☀", font=("Segoe UI", 14), bg=t["bg"], fg=t["accent"]).pack(side="left")
        tk.Label(title_row, text="Apollo Brand Intelligence",
                 font=("Segoe UI", 15, "bold"), bg=t["bg"], fg=t["accent"]).pack(side="left", padx=(2, 0))

        tk.Label(head_f, text="The Light • Clarity • Precision | Enterprise Brand Protection Suite",
                 font=FONT_SM, bg=t["bg"], fg=t["subtext"]).pack(anchor="w", pady=(2, 0))

        div = tk.Frame(pad_f, bg=t["border"], height=1)
        div.pack(fill="x", pady=(6, 10))

        # ── Notebook / Tabs ──────────────────────────────────────────────────
        style = ttk.Style(win)
        style.configure("About.TNotebook",
                        background=t["bg"],
                        bordercolor=t["border"],
                        darkcolor=t["bg"],
                        lightcolor=t["bg"],
                        tabmargins=[2, 5, 2, 0])
        style.configure("About.TNotebook.Tab",
                        background=t["panel"],
                        foreground=t["text"],
                        bordercolor=t["border"],
                        darkcolor=t["panel"],
                        lightcolor=t["panel"],
                        padding=[16, 8],
                        font=("Segoe UI", 9, "bold"))
        style.map("About.TNotebook.Tab",
                  background=[("selected", t["accent"]), ("active", t["border"])],
                  foreground=[("selected", t.get("btn_accent_fg", "black" if t.get("name", "").startswith("⚡") else "white")),
                              ("active", t["text"])],
                  darkcolor=[("selected", t["accent"]), ("active", t["border"])],
                  lightcolor=[("selected", t["accent"]), ("active", t["border"])],
                  bordercolor=[("selected", t["accent"]), ("active", t["border"])])

        nb = ttk.Notebook(pad_f, style="About.TNotebook")
        nb.pack(fill="both", expand=True)

        # ── TAB 1: Ethos & Architecture ──────────────────────────────────────
        tab_ethos = tk.Frame(nb, bg=t["panel"], padx=16, pady=12)
        nb.add(tab_ethos, text="☀ Tactical Architecture & Ethos")

        # Scrollable container for ethos tab
        ethos_canvas = tk.Canvas(tab_ethos, bg=t["panel"], highlightthickness=0)
        ethos_vsb = ttk.Scrollbar(tab_ethos, orient="vertical", command=ethos_canvas.yview)
        ethos_scroll_frame = tk.Frame(ethos_canvas, bg=t["panel"])

        def _on_canvas_configure(event):
            ethos_canvas.configure(scrollregion=ethos_canvas.bbox("all"))
            # Compensate for scrollbar & margins so right edge aligns uniformly
            inner_w = max(680, event.width - 20)
            ethos_canvas.itemconfig(canvas_win_id, width=inner_w)

        canvas_win_id = ethos_canvas.create_window((0, 0), window=ethos_scroll_frame, anchor="nw")
        ethos_canvas.bind("<Configure>", _on_canvas_configure)
        ethos_scroll_frame.bind("<Configure>", lambda e: ethos_canvas.configure(scrollregion=ethos_canvas.bbox("all")))
        ethos_canvas.configure(yscrollcommand=ethos_vsb.set)

        # Enable mousewheel scrolling across canvas
        def _on_mousewheel(event):
            try:
                ethos_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        ethos_canvas.bind("<MouseWheel>", _on_mousewheel)
        ethos_scroll_frame.bind("<MouseWheel>", _on_mousewheel)

        ethos_canvas.pack(side="left", fill="both", expand=True)
        ethos_vsb.pack(side="right", fill="y")

        # Apollo Narrative
        narrative_hdr = tk.Label(ethos_scroll_frame, text="Apollo Brand Intelligence Enterprise Architecture",
                                 font=("Segoe UI", 11, "bold"), bg=t["panel"], fg=t["accent"])
        narrative_hdr.pack(anchor="w", padx=4, pady=(0, 4))
        narrative_hdr.bind("<MouseWheel>", _on_mousewheel)

        narrative_txt = (
            "Apollo Brand Intelligence is an on-demand brand protection platform engineered for "
            "rapid multi-brand seller harvesting, visual syndicate discovery, and multi-jurisdiction compliance dossiers."
        )
        nar_lbl = tk.Label(ethos_scroll_frame, text=narrative_txt, font=FONT_SM, bg=t["panel"],
                           fg=t["text"], wraplength=760, justify="left")
        nar_lbl.pack(anchor="w", padx=4, pady=(0, 10))
        nar_lbl.bind("<MouseWheel>", _on_mousewheel)

        # 3 Triangles Card Frame (Pixel-locked icon boxes & bounded width)
        tri_frame = tk.Frame(ethos_scroll_frame, bg=t["entry_bg"], padx=14, pady=12, relief="flat")
        tri_frame.pack(fill="x", padx=4, pady=(0, 12))
        tri_frame.bind("<MouseWheel>", _on_mousewheel)

        tri_hdr = tk.Label(tri_frame, text="🏛 The Enterprise Tactical Suite:",
                           font=("Segoe UI", 10, "bold"), bg=t["entry_bg"], fg=t["accent"])
        tri_hdr.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        tri_hdr.bind("<MouseWheel>", _on_mousewheel)

        tri_frame.grid_columnconfigure(0, weight=0)
        tri_frame.grid_columnconfigure(1, weight=0)
        tri_frame.grid_columnconfigure(2, weight=1)

        tri_data = [
            ("🏢", "Enterprise Gateway", "The Enterprise Base of Record — Massive cloud archives, case history, client intake, and formal takedown tracking."),
            ("☀", "Apollo Recon", "Tactical Recon & Precision Triage — 35-worker parallel visual dredge, 1-click portfolio sweeps, and zero-noise filtering."),
            ("🏹", "Enforcement Suite", "Automated Platform Enforcement — Rapid-fire form-filling for VeRO, Amazon Brand Registry, and Mercado Libre BPP."),
            ("⚖", "Threat Syndicate Vault", "Syndicate Retribution & Legal Vault — Forensic cross-border entity correlation and court-admissible evidence dossiers."),
        ]

        for r_i, (icon, title, desc) in enumerate(tri_data):
            lbl_icon = tk.Label(tri_frame, text=icon, font=("Segoe UI", 10), bg=t["entry_bg"], fg=t["accent"], width=3, anchor="center")
            lbl_icon.grid(row=r_i + 1, column=0, sticky="nw", pady=4)
            lbl_icon.bind("<MouseWheel>", _on_mousewheel)

            t_lbl = tk.Label(tri_frame, text=f"{title}:", font=("Segoe UI", 9, "bold"), bg=t["entry_bg"], fg=t["text"], anchor="nw", justify="left")
            t_lbl.grid(row=r_i + 1, column=1, sticky="nw", padx=(2, 12), pady=4)
            t_lbl.bind("<MouseWheel>", _on_mousewheel)

            d_lbl = tk.Label(tri_frame, text=desc, font=FONT_SM, bg=t["entry_bg"], fg=t["subtext"], justify="left", wraplength=520, anchor="nw")
            d_lbl.grid(row=r_i + 1, column=2, sticky="new", pady=4)
            d_lbl.bind("<MouseWheel>", _on_mousewheel)

        # 9 Pillars
        p_hdr = tk.Label(ethos_scroll_frame, text="⚔ The 9 Pillars of Apollo Intelligence:",
                         font=("Segoe UI", 10, "bold"), bg=t["panel"], fg=t["accent"])
        p_hdr.pack(anchor="w", padx=4, pady=(4, 6))
        p_hdr.bind("<MouseWheel>", _on_mousewheel)

        pillars_grid = tk.Frame(ethos_scroll_frame, bg=t["panel"])
        pillars_grid.pack(fill="x", padx=4, pady=(0, 8))
        pillars_grid.bind("<MouseWheel>", _on_mousewheel)

        pillars = [
            ("1. Vigilance", "Comprehensive cross-marketplace seller surveillance (eBay, Ali, Wish, Temu, MeLi)"),
            ("2. Stealth", "Resilient session management and anti-bot mitigation"),
            ("3. Precision", "Multi-layer keyword & brand exclusion shielding to minimize noise"),
            ("4. Traceability", "Unmasking domestic 3PL drop-shippers and cross-border supply chains"),
            ("5. Tenacity", "Tracking repeat offender storefronts across rebrands and re-listings"),
            ("6. Integrity", "Standardized, audit-ready compliance reporting for client review"),
            ("7. Velocity", "Rapid multi-brand batch harvesting across complex seller networks"),
            ("8. Impact", "Quantifiable client revenue protection and enforcement ROI metrics"),
            ("9. Global Scope", "16-country international domain expansion for global takedown parity"),
        ]

        for i, (p_title, p_desc) in enumerate(pillars):
            col = i % 3
            row = i // 3
            cell = tk.Frame(pillars_grid, bg=t["entry_bg"], padx=10, pady=8)
            cell.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            cell.bind("<MouseWheel>", _on_mousewheel)
            pillars_grid.columnconfigure(col, weight=1)

            l1 = tk.Label(cell, text=p_title, font=("Segoe UI", 9, "bold"), bg=t["entry_bg"], fg=t["accent"])
            l1.pack(anchor="w")
            l1.bind("<MouseWheel>", _on_mousewheel)

            l2 = tk.Label(cell, text=p_desc, font=("Segoe UI", 8), bg=t["entry_bg"], fg=t["subtext"], wraplength=220, justify="left")
            l2.pack(anchor="w")
            l2.bind("<MouseWheel>", _on_mousewheel)

        # ── TAB 2: Author, IP & Legal Attribution ────────────────────────────
        tab_legal = tk.Frame(nb, bg=t["panel"], padx=20, pady=18)
        nb.add(tab_legal, text="⚖ Author & Legal Attribution")

        # Creator / Credits section
        info_frame = tk.Frame(tab_legal, bg=t["entry_bg"], padx=16, pady=14)
        info_frame.pack(fill="x", pady=(0, 14))
        info_frame.grid_columnconfigure(0, weight=0)
        info_frame.grid_columnconfigure(1, weight=1)

        def _row(parent, r_idx, label, val):
            lbl_l = tk.Label(parent, text=label, font=("Segoe UI", 9, "bold"), bg=t["entry_bg"], fg=t["text"], anchor="w")
            lbl_l.grid(row=r_idx, column=0, sticky="nw", padx=(0, 14), pady=3)
            lbl_v = tk.Label(parent, text=val, font=FONT_SM, bg=t["entry_bg"], fg=t["accent"] if "Jerry Seidenstucker" in val else t["text"], anchor="w", justify="left")
            lbl_v.grid(row=r_idx, column=1, sticky="nw", pady=3)

        _row(info_frame, 0, "Creator & Lead Architect:", "Jerry Seidenstucker (Personal Project)")
        _row(info_frame, 1, "AI Pair Programmer & Engine:", "Aether (Aeth) • Antigravity / Google DeepMind")
        _row(info_frame, 2, "Intellectual Property:", "© 2026 Jerry Seidenstucker. All Rights Reserved.")
        _row(info_frame, 3, "Architecture Version:", "Apollo v3.0.0 Enterprise Tactical Suite")
        _row(info_frame, 4, "License Mode:", "Proprietary / Authorized Internal Evaluation")

        # Legal & Ownership Notice box
        notice_lbl = tk.Label(tab_legal, text="Intellectual Property & Attribution Notice:",
                              font=("Segoe UI", 9, "bold"), bg=t["panel"], fg=t["text"])
        notice_lbl.pack(anchor="w", pady=(4, 4))

        notice_box = tk.Text(tab_legal, height=6, bg=t["entry_bg"], fg=t["subtext"],
                             font=FONT_SM, relief="flat", wrap="word", padx=10, pady=8,
                             bd=0, highlightthickness=0)
        notice_box.pack(fill="x", pady=(0, 6))
        notice_text = (
            "This software and its underlying intelligence architectures were conceived, designed, "
            "and developed independently by Jerry Seidenstucker.\n\n"
            "All rights, title, copyright, and trade secrets in and to this software remain the exclusive "
            "property of the author. Unauthorized corporate appropriation, commercial distribution, or "
            "rebranding without prominent author attribution and express written consent is strictly prohibited."
        )
        notice_box.insert("1.0", notice_text)
        notice_box.config(state="disabled")

        # Close button bar
        btn_row = tk.Frame(pad_f, bg=t["bg"])
        btn_row.pack(fill="x", pady=(12, 0))
        self._btn(btn_row, "Close", win.destroy, accent=True).pack(side="right")

    # ══════════════════════════════════════════════════════════════════════════
    #  LOGGING / STATUS
    # ══════════════════════════════════════════════════════════════════════════
    def _log(self, msg, error=False):
        def _write():
            try:
                if hasattr(self, "log_text") and self.log_text.winfo_exists():
                    self.log_text.config(state="normal")
                    ts  = datetime.now().strftime("%H:%M:%S")
                    tag = "err" if error else "info"
                    self.log_text.tag_config("err",  foreground=self.theme.get("danger", "#ff4444"))
                    self.log_text.tag_config("info", foreground=self.theme.get("text", "#ffffff"))
                    self.log_text.insert("end", f"[{ts}] {msg}\n", tag)
                    self.log_text.see("end")
                    self.log_text.config(state="disabled")
            except Exception:
                pass
        try:
            self.after(0, _write)
        except Exception:
            pass

    def _clear_log(self):
        try:
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                self.log_text.config(state="normal")
                self.log_text.delete("1.0", "end")
                self.log_text.config(state="disabled")
        except Exception:
            pass

    def _status(self, msg):
        try:
            self.after(0, lambda: self.status_var.set(msg) if hasattr(self, "status_var") else None)
        except Exception:
            pass



# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL MULTI-LOCALE EXPANDER & COMPLIANCE EXPORTER
# ══════════════════════════════════════════════════════════════════════════════
class MultiLocaleModal(tk.Toplevel):
    """
    Global Multi-Locale Expander & Compliance Exporter.
    Supports both international eBay domains (.com, .ca, .co.uk, .de, .fr, etc.)
    and Latin American Mercado Libre domains (.mx, .br, .ar, .co, .cl, .pe, .uy).
    """
    def __init__(self, parent, target_items: list = None):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.target_items = target_items if target_items else list(parent.results)
        self.t = parent.theme
        self.locale_vars = {}
        self.locale_status_labels = {}
        self.probe_results = {}
        self.probing = False

        self.is_meli = any(
            "mercado" in it.get("marketplace", "").lower() or 
            "mercadolibre" in it.get("marketplace", "").lower() or 
            "mercadolivre" in it.get("marketplace", "").lower() or 
            "mercadolibre" in it.get("url", "").lower() or 
            "mercadolivre" in it.get("url", "").lower()
            for it in self.target_items
        )
        self.active_locales = MELI_LOCALES if self.is_meli else EBAY_LOCALES

        title_text = "🌐 Latin America Multi-Locale Expander" if self.is_meli else "🌐 Global Multi-Locale Expander"
        self.title(f"{title_text} & Compliance Exporter")
        self.geometry("980x660")
        self.configure(bg=self.t["bg"])
        self.minsize(840, 520)
        self.parent._apply_dark_titlebar(self)

        self._build_ui()

        # Center modal relative to parent window
        self.parent._center_window(self, 980, 660)
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self):
        t = self.t
        pad_f = tk.Frame(self, bg=t["bg"], padx=14, pady=12)
        pad_f.pack(fill="both", expand=True)

        # ── Header Banner ────────────────────────────────────────────────────
        head_f = tk.Frame(pad_f, bg=t["bg"])
        head_f.pack(fill="x", pady=(0, 8))

        h_title = "🌐 Latin America Multi-Locale Expander & Compliance Exporter" if self.is_meli else "🌐 Global Multi-Locale Expander & Compliance Exporter"
        h_sub = "Multiply listings across Latin America (Mexico, Brazil, Argentina, Colombia, Chile, Peru) for regional sweeps" if self.is_meli else "Multiply & verify harvested listings across international eBay domains for global sweeps"

        tk.Label(head_f, text=h_title,
                 font=("Segoe UI", 13, "bold"), bg=t["bg"], fg=t["accent"]).pack(side="left")

        tk.Label(head_f, text=h_sub,
                 font=FONT_SM, bg=t["bg"], fg=t["subtext"]).pack(side="left", padx=12, pady=(2, 0))

        # ── Top KPI Stat Badges ──────────────────────────────────────────────
        kpi_f = tk.Frame(pad_f, bg=t["panel"], padx=12, pady=8)
        kpi_f.pack(fill="x", pady=(0, 8))

        unique_sellers = set(it.get("seller", "") for it in self.target_items if it.get("seller"))
        loc_count = len(self.active_locales)
        
        self.kpi_labels = {}
        def _kpi(parent, title, val, key, color=None):
            f = tk.Frame(parent, bg=t["panel"], padx=14)
            f.pack(side="left", fill="y")
            tk.Label(f, text=title, font=("Segoe UI", 8, "bold"), bg=t["panel"], fg=t["subtext"]).pack(anchor="w")
            lbl = tk.Label(f, text=val, font=("Segoe UI", 12, "bold"), bg=t["panel"], fg=color or t["text"])
            lbl.pack(anchor="w")
            self.kpi_labels[key] = lbl

        _kpi(kpi_f, "📋 Listings in Batch", f"{len(self.target_items):,}", "items")
        _kpi(kpi_f, "🏬 Unique Sellers", f"{len(unique_sellers):,}", "sellers", color=t["accent"])
        _kpi(kpi_f, "🌐 Selected Locales", f"{loc_count} of {loc_count}", "locales", color=t["accent2"])
        _kpi(kpi_f, "📦 Expanded Output Rows", f"{len(self.target_items) * loc_count:,}", "output", color=t["success"])

        # ── Preset Toolbar & Probe Action ────────────────────────────────────
        preset_f = tk.Frame(pad_f, bg=t["bg"])
        preset_f.pack(fill="x", pady=(0, 8))

        tk.Label(preset_f, text="⚡ Quick Presets:", font=("Segoe UI", 9, "bold"), bg=t["bg"], fg=t["accent"]).pack(side="left", padx=(0, 6))

        if self.is_meli:
            self.parent._btn(preset_f, "🌎 All Latin America (7)", lambda: self._apply_preset("all")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇲🇽 Mexico (MLM)", lambda: self._apply_preset("mlm")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇧🇷 Brazil (MLB)", lambda: self._apply_preset("mlb")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🥩 Mercosur (BR/AR/CL/UY)", lambda: self._apply_preset("mercosur")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "☕ Andean (CO/PE)", lambda: self._apply_preset("andean")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "✕ Clear All", lambda: self._apply_preset("none")).pack(side="left", padx=2)
        else:
            self.parent._btn(preset_f, "🌍 All Verified Global (16)", lambda: self._apply_preset("all")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇺🇸 🇨🇦 North America", lambda: self._apply_preset("na")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇪🇺 Europe (UK/EU)", lambda: self._apply_preset("eu")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "🇦🇺 APAC (Australia)", lambda: self._apply_preset("apac")).pack(side="left", padx=2)
            self.parent._btn(preset_f, "✕ Clear All", lambda: self._apply_preset("none")).pack(side="left", padx=2)

        self.probe_btn = self.parent._btn(preset_f, "🔬 Probe & Verify Active Domains", self._start_domain_probe, accent=True)
        self.probe_btn.pack(side="right", padx=(4, 0))

        # ── Locale Checkbox Grid ─────────────────────────────────────────────
        grid_frame = tk.Frame(pad_f, bg=t["panel"], padx=10, pady=10, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        grid_frame.pack(fill="both", expand=True, pady=(0, 8))

        cols = 3 if self.is_meli else 4
        for col_idx in range(cols):
            grid_frame.columnconfigure(col_idx, weight=1)

        for idx, loc in enumerate(self.active_locales):
            row = idx // cols
            col = idx % cols

            cell = tk.Frame(grid_frame, bg=t["entry_bg"], padx=8, pady=6, relief="flat", highlightbackground=t["border"], highlightthickness=1)
            cell.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

            var = tk.BooleanVar(value=True)
            self.locale_vars[loc["domain"]] = var

            curr_tag = f" [{loc['currency']}]" if loc.get("currency") else ""
            cb = tk.Checkbutton(cell, text=f"{loc['flag']} {loc.get('name', loc.get('country', ''))}{curr_tag}", variable=var,
                                command=self._update_kpis, bg=t["entry_bg"], fg=t["text"],
                                selectcolor=t["panel"], activebackground=t["entry_bg"],
                                font=("Segoe UI", 9, "bold"))
            cb.pack(anchor="w")

            sub_f = tk.Frame(cell, bg=t["entry_bg"])
            sub_f.pack(fill="x", pady=(2, 0))

            tk.Label(sub_f, text=f"• {loc['domain']}", font=("Segoe UI", 8), bg=t["entry_bg"], fg=t["subtext"]).pack(side="left")
            
            stat_lbl = tk.Label(sub_f, text=loc.get("region", ""), font=("Segoe UI", 7, "bold"), bg=t["panel"], fg=t["accent"], padx=4, pady=1)
            stat_lbl.pack(side="right")
            self.locale_status_labels[loc["domain"]] = stat_lbl

        # ── Footer Status & Export Action Bar ─────────────────────────────────
        btn_bar = tk.Frame(pad_f, bg=t["panel"], padx=14, pady=10, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x")

        self.status_var = tk.StringVar(value="Ready to expand listings across selected international domains.")
        self.status_lbl = tk.Label(btn_bar, textvariable=self.status_var, font=FONT_SM, bg=t["panel"], fg=t["text"])
        self.status_lbl.pack(side="left")

        self.parent._btn(btn_bar, "✕ Close", self.destroy).pack(side="right", padx=(4, 0))
        self.export_btn = self.parent._btn(btn_bar, "💾 Export Multi-Locale Enforcement Pack", self._export_multi_locale, accent=True)
        self.export_btn.pack(side="right", padx=(4, 0))

    def _apply_preset(self, preset_name: str):
        for loc in self.active_locales:
            dom = loc["domain"]
            reg = loc.get("region", "")
            code = loc.get("code", "")
            if preset_name == "all":
                self.locale_vars[dom].set(True)
            elif preset_name == "none":
                self.locale_vars[dom].set(False)
            elif preset_name == "mlm":
                self.locale_vars[dom].set(code == "MLM")
            elif preset_name == "mlb":
                self.locale_vars[dom].set(code == "MLB")
            elif preset_name == "mercosur":
                self.locale_vars[dom].set(code in ("MLB", "MLA", "MLC", "MLU"))
            elif preset_name == "andean":
                self.locale_vars[dom].set(code in ("MCO", "MPE"))
            elif preset_name == "na":
                self.locale_vars[dom].set(reg == "North America")
            elif preset_name == "eu":
                self.locale_vars[dom].set(reg == "Europe")
            elif preset_name == "apac":
                self.locale_vars[dom].set(reg == "APAC")
        self._update_kpis()

    def _update_kpis(self):
        selected_count = sum(1 for v in self.locale_vars.values() if v.get())
        total_items = len(self.target_items)
        output_rows = total_items * selected_count
        self.kpi_labels["locales"].config(text=f"{selected_count} of {len(self.active_locales)}")
        self.kpi_labels["output"].config(text=f"{output_rows:,}")
        self.status_var.set(f"Selected {selected_count} locales → Will generate {output_rows:,} international compliance rows.")

    def _start_domain_probe(self):
        """Probe sample listing per seller across locales."""
        if self.probing:
            return
        if not self.target_items:
            messagebox.showinfo("Probe", "No items to probe.", parent=self)
            return

        sample_items = {}
        for it in self.target_items:
            s = it.get("seller") or "Unknown"
            iid = it.get("item_id")
            if s not in sample_items and iid:
                sample_items[s] = iid

        if not sample_items:
            messagebox.showinfo("Probe", "No valid Item IDs found to probe.", parent=self)
            return

        self.probing = True
        self.probe_btn.config(state="disabled")
        self.status_var.set(f"🔬 Probing {len(sample_items)} sample seller item(s) across domains...")

        def _worker():
            verified_domains = set()
            if self.is_meli:
                for loc in MELI_LOCALES:
                    verified_domains.add(loc["domain"])
            else:
                scraper = getattr(self.parent, "scraper", None)
                if not scraper:
                    scraper = EbayScraper(headless=True)
                for s, iid in sample_items.items():
                    active_locales = scraper.probe_item_locales(iid)
                    for loc in active_locales:
                        verified_domains.add(loc["domain"])

            def _apply():
                self.probing = False
                self.probe_btn.config(state="normal")
                for loc in self.active_locales:
                    dom = loc["domain"]
                    lbl = self.locale_status_labels.get(dom)
                    if dom in verified_domains:
                        self.locale_vars[dom].set(True)
                        if lbl: lbl.config(text="🟢 Verified Active", fg=self.t["success"])
                    else:
                        if lbl: lbl.config(text="⚪ Geoblocked / Inactive", fg=self.t["subtext"])
                self._update_kpis()
                self.status_var.set(f"✅ Probe complete: {len(verified_domains)} domains verified active!")
                messagebox.showinfo("Probe Complete", f"Successfully probed {len(sample_items)} seller(s)!\n\nVerified {len(verified_domains)} active domains.", parent=self)

            self.after(0, _apply)

        threading.Thread(target=_worker, daemon=True).start()

    def _export_multi_locale(self):
        selected_locales = [loc for loc in self.active_locales if self.locale_vars.get(loc["domain"], tk.BooleanVar(value=False)).get()]
        if not selected_locales:
            messagebox.showwarning("Select Locales", "Please select at least one international locale to export.", parent=self)
            return

        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = "meli_latam_enforcement" if self.is_meli else "multi_locale_enforcement"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"{prefix}_{now_str}.xlsx",
            parent=self
        )
        if not path:
            return

        try:
            total_rows = self.parent.exporter.export_multi_locale(self.target_items, selected_locales, path)
            # Ingest verified exported results into Enterprise Brand Enforcement Registry
            seller_items = {}
            for item in self.target_items:
                seller = item.get("seller") or "Unknown"
                seller_items.setdefault(seller, []).append(item)
            ds = getattr(self.parent, "data_store", None)
            if ds:
                for seller, s_items in seller_items.items():
                    ds.record_enforcement_scan(seller, s_items)

            self.parent._log(f"🌐 Multi-Locale Enforcement Pack exported: {total_rows} listings across {len(selected_locales)} domains → {path}")
            self.parent._log(f"🛡 Logged {len(self.target_items)} verified listing(s) across {len(seller_items)} seller(s) into Enterprise Brand Enforcement Registry.")
            self.status_var.set(f"✅ Exported {total_rows:,} rows across {len(selected_locales)} domains to Excel!")
            messagebox.showinfo("Multi-Locale Export Complete",
                                f"Successfully generated Multi-Locale Enforcement Pack!\n\n• Base Harvested Listings: {len(self.target_items):,}\n• Target Locales: {len(selected_locales)}\n• Total Expanded Listings: {total_rows:,}\n\nSaved to:\n{path}\n\n🛡 Logged into Enterprise Brand Enforcement Registry.",
                                parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export multi-locale file: {e}", parent=self)


# ══════════════════════════════════════════════════════════════════════════════
#  CONNECTED SELLER NETWORK & PHOTO SYNDICATE HUNTER MODAL
# ══════════════════════════════════════════════════════════════════════════════
class ConnectedNetworkModal(tk.Toplevel):
    """
    On-Demand Visual Syndicate & Connected Seller Hunter.
    Scans merchandising carousels on eBay listing pages and runs perceptual image hashing (dHash)
    to discover burner storefronts, competing listings, and connected counterfeit networks.
    """
    def __init__(self, parent, target_item: dict):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.target_item = target_item
        self.t = parent.theme
        self.discovered_items = []
        self.thumb_cache = {}
        self._sort_directions = {}
        
        self.title("🔗 Connected Seller Network & Photo Syndicate Hunter")
        self.geometry("1200x780")
        self.configure(bg=self.t["bg"])
        self.minsize(980, 620)
        self.parent._apply_dark_titlebar(self)
        
        self._build_ui()
        self.parent._center_window(self, 1200, 780)
        self.deiconify()
        self.lift()
        self.focus_force()
        
        self._start_network_scan()

    def _build_ui(self):
        t = self.t

        # ── 1. Top Target Reference Listing Card ──────────────────────────────
        hdr_frame = tk.Frame(self, bg=t["panel"], padx=16, pady=12, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        hdr_frame.pack(side="top", fill="x", padx=12, pady=(12, 6))

        # Big Thumbnail preview container
        img_box = tk.Frame(hdr_frame, bg=t["entry_bg"], width=104, height=104, highlightbackground=t["border"], highlightthickness=1)
        img_box.pack_propagate(False)
        img_box.pack(side="left", padx=(0, 16))

        self.src_img_lbl = tk.Label(img_box, text="Loading\nPhoto...", bg=t["entry_bg"], fg=t["subtext"], font=FONT_SM)
        self.src_img_lbl.pack(fill="both", expand=True)
        self._load_source_image()

        info_box = tk.Frame(hdr_frame, bg=t["panel"])
        info_box.pack(side="left", fill="both", expand=True)

        badge_row = tk.Frame(info_box, bg=t["panel"])
        badge_row.pack(anchor="w", pady=(0, 4))
        
        tag_lbl = tk.Label(badge_row, text="🎯 TARGET REFERENCE LISTING", font=("Segoe UI", 8, "bold"), bg=t["accent"], fg="white", padx=8, pady=2)
        tag_lbl.pack(side="left", padx=(0, 8))

        brand_val = self.target_item.get("brand") or "General Brand"
        tk.Label(badge_row, text=f"Brand: {brand_val}", font=("Segoe UI", 8, "bold"), bg=t["entry_bg"], fg=t["subtext"], padx=8, pady=2).pack(side="left")

        title_lbl = tk.Label(info_box, text=self.target_item.get("title", "Unknown Title"), font=FONT_HEAD, bg=t["panel"], fg=t["text"], wraplength=820, justify="left")
        title_lbl.pack(anchor="w")

        seller_name = self.target_item.get("seller") or "Unknown Seller"
        price_val = self.target_item.get("price") or "N/A"
        item_id_val = self.target_item.get("item_id") or "N/A"
        sub_text = f"👤 Seller: {seller_name}    💰 Price: {price_val}    🆔 Item ID: {item_id_val}"
        sub_lbl = tk.Label(info_box, text=sub_text, font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        sub_lbl.pack(anchor="w", pady=(4, 0))

        # ── 2. Status & Filter Bar ────────────────────────────────────────────
        self.status_frame = tk.Frame(self, bg=t["bg"], padx=14, pady=4)
        self.status_frame.pack(side="top", fill="x", padx=12)

        self.status_lbl = tk.Label(self.status_frame, text="🔍 Scanning eBay merchandising carousels and matching perceptual image hashes...", font=("Segoe UI", 9, "italic"), bg=t["bg"], fg=t["accent"])
        self.status_lbl.pack(side="left")

        self.pbar = ttk.Progressbar(self.status_frame, mode="indeterminate", length=180)
        self.pbar.pack(side="right", padx=(8, 0))
        self.pbar.start(12)

        # Filters toolbar
        f_row = tk.Frame(self, bg=t["panel"], padx=12, pady=5, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        f_row.pack(side="top", fill="x", padx=12, pady=(2, 4))

        tk.Label(f_row, text="Thumbnails:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(0, 4))
        self.thumb_size_var = tk.StringVar(value="Medium (100px)")
        self.thumb_size_combo = ttk.Combobox(f_row, textvariable=self.thumb_size_var, values=list(THUMB_CONFIG.keys()), width=14, state="readonly", font=FONT_SM)
        self.thumb_size_combo.pack(side="left", padx=(0, 10))
        self.thumb_size_combo.bind("<<ComboboxSelected>>", self._on_thumb_size_changed)

        tk.Label(f_row, text="Match Filter:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(0, 4))
        self.match_filter_var = tk.StringVar(value="(All Discovered)")
        match_filters = ["(All Discovered)", "🎯 Exact & Near-Exact Photos Only", "🖼 Visual Matches Only"]
        self.match_filter_combo = ttk.Combobox(f_row, textvariable=self.match_filter_var, values=match_filters, width=24, state="readonly", font=FONT_SM)
        self.match_filter_combo.pack(side="left", padx=(0, 10))
        self.match_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_tree())

        self.hide_same_seller_var = tk.BooleanVar(value=False)
        same_seller_cb = tk.Checkbutton(f_row, text="Hide Same Seller", variable=self.hide_same_seller_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t["accent"], activebackground=t["panel"], font=FONT_SM)
        same_seller_cb.pack(side="left", padx=(0, 8))

        self.hide_wl_var = tk.BooleanVar(value=False)
        wl_cb = tk.Checkbutton(f_row, text="🛡 Hide Whitelisted Dealers", variable=self.hide_wl_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t["accent"], activebackground=t["panel"], font=FONT_SM)
        wl_cb.pack(side="left", padx=(0, 8))

        self.hide_targeted_var = tk.BooleanVar(value=False)
        targeted_cb = tk.Checkbutton(f_row, text="🎯 Hide Targeted / Harvested", variable=self.hide_targeted_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t["accent"], activebackground=t["panel"], font=FONT_SM)
        targeted_cb.pack(side="left", padx=(0, 8))

        # ── 4. Action Toolbar (Docked to Bottom First) ────────────────────────
        btn_bar = tk.Frame(self, bg=t["panel"], padx=10, pady=8, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x", padx=12, pady=(4, 8))

        self.count_var = tk.StringVar(value="0 connected listings discovered")
        count_lbl = tk.Label(btn_bar, textvariable=self.count_var, bg=t["panel"], fg=t["text"], font=FONT_HEAD)
        count_lbl.pack(side="left")

        tk.Button(btn_bar, text="✕ Close", command=self.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="⚡ Enrich", command=self._enrich_selected_sellers, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📥 To Table", command=self._add_to_results, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📋 Copy Handles", command=self._copy_sellers, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="🏪 To Stores", command=self._add_all_to_stores, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="➕ Queue Sellers", command=self._add_sellers_to_queue, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4).pack(side="right", padx=4)

        # ── 3. Discovered Network Table (Fills Remaining Space) ───────────────
        table_frame = tk.Frame(self, bg=t["bg"])
        table_frame.pack(side="top", fill="both", expand=True, padx=12, pady=4)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("similarity", "seller", "origin", "threat", "price", "title", "item_id")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="tree headings", selectmode="extended", style="Network.Treeview")

        style = ttk.Style()
        style.configure("Network.Treeview", background=t["entry_bg"], foreground=t["text"], fieldbackground=t["entry_bg"], rowheight=108, font=FONT_SM)
        style.configure("Network.Treeview.Heading", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9, "bold"))
        style.map("Network.Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["select_fg"])])

        self.tree.tag_configure("whitelisted", foreground=t["success"])
        self.tree.tag_configure("same_seller", foreground=t["accent2"])
        self.tree.tag_configure("targeted", foreground=t["subtext"])

        self.tree.heading("#0", text="Photo Preview", anchor="center")
        self.tree.column("#0", width=120, minwidth=100, anchor="center", stretch=False)

        self.col_cfg = {
            "similarity": ("Match Type / Visual Fingerprint", 185),
            "seller": ("Connected Seller", 140),
            "origin": ("Origin", 85),
            "threat": ("Threat Assessment", 175),
            "price": ("Price", 75),
            "title": ("Discovered Listing Title", 360),
            "item_id": ("Item ID", 105)
        }
        for c, (txt, w) in self.col_cfg.items():
            self.tree.heading(c, text=txt, command=lambda _c=c: self._sort_by_column(_c))
            self.tree.column(c, width=w, minwidth=50, stretch=False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._open_selected_url)
        self.tree.bind("<Button-3>", self._show_row_context_menu)
        self.tree.bind("<Control-a>", self._select_all_rows)
        self.tree.bind("<Control-A>", self._select_all_rows)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _on_thumb_size_changed(self, event=None):
        size_name = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_name, THUMB_CONFIG.get("Medium (100px)", {"rowheight": 110, "img_size": 100, "col_width": 116}))
        style = ttk.Style()
        style.configure("Network.Treeview", rowheight=cfg["rowheight"])
        img_size = cfg.get("img_size", 0)
        col_w = max(50, cfg.get("col_width", 116) + 10) if img_size > 0 else 50
        self.tree.column("#0", width=col_w, minwidth=40)
        self.thumb_cache.clear()
        self._populate_tree()

    def _select_all_rows(self, event=None):
        ch = self.tree.get_children()
        if ch:
            self.tree.selection_set(ch)
            self._on_tree_select()
        return "break"

    def _on_tree_select(self, event=None):
        sel_count = len(self.tree.selection())
        vis_count = len(self.tree.get_children())
        total_count = len(self.discovered_items)
        if sel_count > 0:
            self.count_var.set(f"{vis_count} listings shown ({sel_count} selected) | {total_count} discovered")
        else:
            self.count_var.set(f"{vis_count} listings shown | {total_count} discovered")

    def _load_source_image(self):
        url = self.target_item.get("image_url", "")
        if not url:
            tid = str(self.target_item.get("item_id", "")).strip()
            if tid and hasattr(self.parent, "results"):
                for r in self.parent.results:
                    if str(r.get("item_id", "")).strip() == tid and r.get("image_url"):
                        url = r.get("image_url")
                        break
        if not url:
            self.src_img_lbl.configure(text="No Photo\nAvailable")
            return

        def _w():
            try:
                if hasattr(self.parent, "raw_img_cache") and url in self.parent.raw_img_cache:
                    pimg = self.parent.raw_img_cache[url].copy()
                else:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        pimg = Image.open(io.BytesIO(r.read())).convert("RGBA")
                
                pimg.thumbnail((96, 96), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
                canvas.paste(pimg, ((96 - pimg.width)//2, (96 - pimg.height)//2))

                def _set(c=canvas):
                    try:
                        if self.winfo_exists():
                            photo = ImageTk.PhotoImage(c, master=self)
                            self.thumb_cache["source"] = photo
                            self.src_img_lbl.configure(image=photo, text="")
                            self.src_img_lbl.image = photo
                    except Exception:
                        self.src_img_lbl.configure(text="Photo\nUnavailable")
                self.after(0, _set)
            except Exception:
                try:
                    self.after(0, lambda: self.src_img_lbl.configure(text="Photo\nUnavailable"))
                except Exception:
                    pass
        threading.Thread(target=_w, daemon=True).start()

    def _start_network_scan(self):
        item_id = self.target_item.get("item_id", "")
        item_url = self.target_item.get("url", "")
        target_img = self.target_item.get("image_url", "")
        is_meli = "mercadolibre" in item_url.lower() or "mercadolivre" in item_url.lower() or "mercado" in str(self.target_item.get("marketplace", "")).lower()
        is_printerval = "printerval" in item_url.lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
        is_rb = "redbubble" in item_url.lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()

        if is_printerval:
            platform_name = "Printerval"
        elif is_rb:
            platform_name = "Redbubble"
        elif is_meli:
            platform_name = "Mercado Libre"
        else:
            platform_name = "eBay"
        self.status_lbl.configure(text=f"🔍 Scanning {platform_name} merchandising carousels, competitor recommendations, and storefront syndicates...")

        def _worker():
            try:
                if is_printerval:
                    scraper = getattr(self.parent, "printerval_scraper", None)
                    if not scraper:
                        from printerval_scraper import PrintervalScraper
                        scraper = PrintervalScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                elif is_rb:
                    scraper = getattr(self.parent, "redbubble_scraper", None)
                    if not scraper:
                        from redbubble_scraper import RedbubbleScraper
                        scraper = RedbubbleScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                elif is_meli:
                    scraper = getattr(self.parent, "mercadolibre_scraper", None)
                    if not scraper:
                        from mercadolibre_scraper import MercadoLibreScraper
                        scraper = MercadoLibreScraper(headless=False)
                    results = scraper.find_connected_network(item_id, item_url, target_img)
                else:
                    scraper = getattr(self.parent, "scraper", None)
                    if not scraper:
                        scraper = EbayScraper(headless=True)
                    results = scraper.find_connected_network(item_id, item_url, target_img)

                self.discovered_items = results
                scan_err = None
            except Exception as e:
                logger.exception("Error in ConnectedNetworkModal scan")
                results = []
                self.discovered_items = []
                scan_err = str(e)

            def _apply():
                self.pbar.stop()
                self.pbar.pack_forget()

                if scan_err:
                    self.status_lbl.configure(text=f"⚠ Carousel Scan Error: {scan_err}", fg=self.t["danger"])
                    self._populate_tree()
                    return

                ds = getattr(self.parent, "data_store", None)
                unique_sellers = set(r["seller"] for r in self.discovered_items if r.get("seller"))
                exact_matches = sum(1 for r in self.discovered_items if "Exact" in r.get("similarity", ""))
                wl_count = sum(1 for r in self.discovered_items if (ds.is_seller_whitelisted(r.get("seller", "")) if ds else False))

                status_txt = f"✅ Scan Complete: {len(self.discovered_items)} connected listings found ({exact_matches} exact photo matches, {len(unique_sellers)} resolved sellers)"
                if wl_count > 0:
                    status_txt += f" | 🛡 {wl_count} Whitelisted Dealer listings"
                self.status_lbl.configure(text=status_txt, fg=self.t["success"])

                self._populate_tree()

                # Asynchronously resolve seller country intelligence in background
                def _bg_intel():
                    try:
                        unique_sellers = list(dict.fromkeys(r["seller"] for r in results if r.get("seller") and r.get("seller") not in ("Resolving...", "Unknown")))
                        ds = getattr(self.parent, "data_store", None)
                        if unique_sellers and ds:
                            uncached = [s for s in unique_sellers if not ds.get_seller_intel(s).get("country")]
                            if uncached and hasattr(scraper, "batch_resolve_seller_countries"):
                                resolved_intel = scraper.batch_resolve_seller_countries(uncached)
                                for s, data in resolved_intel.items():
                                    c_val = data.get("country", "Unknown")
                                    if c_val and c_val != "Unknown":
                                        ds.set_seller_intel(s, c_val, member_since=data.get("member_since", ""))
                                if self.winfo_exists():
                                    self.after(0, self._populate_tree)
                    except Exception:
                        pass
                threading.Thread(target=_bg_intel, daemon=True).start()

            self.after(0, _apply)
        threading.Thread(target=_worker, daemon=True).start()

    def _sort_by_column(self, col):
        """Sort discovered items by column and re-render tree."""
        if not self.discovered_items:
            return
        if not hasattr(self, "sort_directions"):
            self.sort_directions = {}
        descending = self.sort_directions.get(col, False)
        self.sort_directions[col] = not descending
        ds = getattr(self.parent, "data_store", None)

        def get_sort_key(item):
            seller = (item.get("seller") or "").strip()
            is_pod = any(p in item.get("marketplace", "").lower() or p in item.get("url", "").lower() for p in ("printerval", "redbubble", "teepublic", "zazzle", "spreadshirt", "threadless", "teespring"))
            if col == "origin":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else (item.get("seller_origin") or ("United States" if is_pod else ""))
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("country", "United States" if is_pod else "Unknown").lower()
            elif col == "threat":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else (item.get("seller_origin") or ("United States" if is_pod else ""))
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("score", 65 if is_pod else 0)
            elif col == "price":
                m = re.search(r"[\d,]+(?:\.\d+)?", str(item.get("price", "")))
                if m:
                    try: return float(m.group(0).replace(",", ""))
                    except ValueError: return 0.0
                return 0.0
            elif col == "item_id":
                try: return int(item.get("item_id", 0))
                except ValueError: return 0
            elif col == "similarity":
                return str(item.get("similarity", "")).lower()
            elif col == "seller":
                return seller.lower()
            elif col == "title":
                return str(item.get("title", "")).lower()
            return str(item.get(col, "")).lower()

        self.discovered_items.sort(key=get_sort_key, reverse=descending)
        self._populate_tree()

        # Update headings with sort arrows
        for c, (txt, w) in self.col_cfg.items():
            if c == col:
                arrow = " ▼" if descending else " ▲"
                self.tree.heading(c, text=f"{txt}{arrow}", command=lambda _c=c: self._sort_by_column(_c))
            else:
                self.tree.heading(c, text=txt, command=lambda _c=c: self._sort_by_column(_c))

    def _populate_tree(self):
        """Render discovered items honoring current whitelist/same seller/match filters."""
        self.tree.delete(*self.tree.get_children())
        hide_wl = self.hide_wl_var.get()
        hide_same_seller = self.hide_same_seller_var.get()
        hide_targeted = self.hide_targeted_var.get()
        match_filter = self.match_filter_var.get()
        src_raw = (self.target_item.get("seller") or "").strip()
        src_seller = self._clean_seller_handle(src_raw).lower() if hasattr(self, "_clean_seller_handle") else src_raw.lower()

        # Collect active targeted / queued / harvested store handles
        stores_in_input = set()
        if hasattr(self.parent, "store_text"):
            raw_text = self.parent.store_text.get("1.0", "end")
            placeholder = getattr(self.parent, "store_placeholder", "").strip()
            for line in raw_text.splitlines():
                l = line.strip().lower()
                if l and l != placeholder.lower():
                    clean_l = self._clean_seller_handle(l).lower() if hasattr(self, "_clean_seller_handle") else l
                    lbl = self.parent._store_label(l).lower() if hasattr(self.parent, "_store_label") else l
                    stores_in_input.add(l)
                    stores_in_input.add(clean_l)
                    stores_in_input.add(lbl)

        queued_stores = set()
        if hasattr(self.parent, "queue"):
            for q in self.parent.queue:
                s = q.get("store", "").strip().lower()
                if s:
                    clean_s = self._clean_seller_handle(s).lower() if hasattr(self, "_clean_seller_handle") else s
                    lbl = self.parent._store_label(s).lower() if hasattr(self.parent, "_store_label") else s
                    queued_stores.add(s)
                    queued_stores.add(clean_s)
                    queued_stores.add(lbl)

        executed_stores = set()
        if hasattr(self.parent, "executed_jobs"):
            for ex in self.parent.executed_jobs:
                s = ex.get("store", "").strip().lower()
                if s:
                    clean_s = self._clean_seller_handle(s).lower() if hasattr(self, "_clean_seller_handle") else s
                    lbl = self.parent._store_label(s).lower() if hasattr(self.parent, "_store_label") else s
                    executed_stores.add(s)
                    executed_stores.add(clean_s)
                    executed_stores.add(lbl)

        results_stores = set()
        harvested_item_ids = set()
        harvested_urls = set()
        if hasattr(self.parent, "results"):
            for it in self.parent.results:
                s = str(it.get("seller", "")).replace("🛡", "").replace("(Authorized)", "").strip().lower()
                clean_s = self._clean_seller_handle(s).lower() if hasattr(self, "_clean_seller_handle") else s
                if s and s not in ("unknown", "resolving..."):
                    results_stores.add(s)
                    results_stores.add(clean_s)
                iid = str(it.get("item_id", "")).strip()
                if iid:
                    harvested_item_ids.add(iid)
                u = str(it.get("url", "")).strip().lower()
                if u:
                    harvested_urls.add(u)

        targeted_or_harvested = stores_in_input | queued_stores | executed_stores | results_stores
        if src_seller:
            targeted_or_harvested.add(src_seller)
        if src_raw:
            targeted_or_harvested.add(src_raw.lower())

        size_name = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_name, THUMB_CONFIG.get("Medium (100px)", {"rowheight": 110, "img_size": 100, "col_width": 116}))
        img_size = cfg.get("img_size", 0)
        show_images = img_size > 0

        ds = getattr(self.parent, "data_store", None)
        shown_count = 0
        for itm in self.discovered_items:
            raw_seller = (itm.get("seller") or "Unknown").strip()
            seller = self._clean_seller_handle(raw_seller) if hasattr(self, "_clean_seller_handle") else raw_seller
            seller_clean = seller.lower()
            itm_id = str(itm.get("item_id", "")).strip()
            itm_url = str(itm.get("url", "")).strip().lower()

            is_wl = ds.is_seller_whitelisted(seller) if ds else False
            is_same = bool(src_seller and (seller_clean == src_seller or raw_seller.lower() == src_seller))
            is_targeted_or_harvested = bool(
                is_same or
                seller_clean in targeted_or_harvested or 
                raw_seller.lower() in targeted_or_harvested or
                (itm_id and itm_id in harvested_item_ids) or 
                (itm_url and itm_url in harvested_urls)
            )

            if hide_wl and is_wl:
                continue
            if hide_same_seller and is_same:
                continue
            if hide_targeted and is_targeted_or_harvested:
                continue

            sim_txt = itm.get("similarity", "Related Listing")
            if "Exact" in match_filter and "Exact" not in sim_txt:
                continue
            if "Visual" in match_filter and not any(k in sim_txt for k in ("Exact", "Visual", "Near-Exact")):
                continue

            if is_wl:
                seller_display = f"🛡 {seller} (Authorized)"
            elif is_same:
                seller_display = f"🏠 {seller} (Source Seller)"
            elif is_targeted_or_harvested:
                seller_display = f"🎯 {seller} (Targeted/Harvested)"
            else:
                seller_display = f"⚡ {seller}"

            # Evaluate Threat Intel from DataStore
            is_pod = any(p in itm.get("marketplace", "").lower() or p in itm.get("url", "").lower() for p in ("printerval", "redbubble", "teepublic", "zazzle", "spreadshirt", "threadless", "teespring"))
            cached_intel = ds.get_seller_intel(seller) if ds else {}
            seller_country = cached_intel.get("country", "") if cached_intel else ""
            if not seller_country and is_pod:
                seller_country = itm.get("seller_origin") or itm.get("location") or "United States"
            loc_val = itm.get("location") or ("United States" if is_pod else "")

            assessment = ds.compute_threat_assessment(seller_country, loc_val) if ds else {}
            if is_pod:
                orig_country = assessment.get("country", "United States")
                if orig_country == "Unknown": orig_country = "United States"
                orig_txt = f"{assessment.get('flag', '🇺🇸')} {orig_country}"
                threat_txt = "👕 POD Print Syndicate"
            else:
                orig_txt = f"{assessment.get('flag', '❓')} {assessment.get('country', 'Unknown')}" if assessment.get('country') != 'Unknown' else "❓ Unresolved"
                threat_txt = assessment.get("badge", "Unresolved")

            img_url = itm.get("image_url", "")
            img_to_use = self.thumb_cache.get(img_url) if show_images else None

            tags = []
            if is_wl: tags.append("whitelisted")
            elif is_same: tags.append("same_seller")
            elif is_targeted_or_harvested: tags.append("targeted")

            iid = self.tree.insert("", "end", text="", image=img_to_use if img_to_use else "", values=(
                sim_txt,
                seller_display,
                orig_txt,
                threat_txt,
                itm.get("price", ""),
                itm.get("title", ""),
                itm.get("item_id", "")
            ), tags=tuple(tags))

            if show_images and img_url:
                if img_url in self.thumb_cache:
                    self.tree.item(iid, image=self.thumb_cache[img_url])
                else:
                    self._fetch_thumb(iid, img_url, img_size)

            shown_count += 1

        self.count_var.set(f"{shown_count} listings shown | {len(self.discovered_items)} discovered")

    def _fetch_thumb(self, iid, url, size):
        """Asynchronously download and scale thumbnail with multi-row listener tracking."""
        if not hasattr(self, "_pending_thumb_iids"):
            self._pending_thumb_iids = {}
        if url in self._pending_thumb_iids:
            if iid not in self._pending_thumb_iids[url]:
                self._pending_thumb_iids[url].append(iid)
            return
        self._pending_thumb_iids[url] = [iid]

        def _w():
            referer = "https://www.redbubble.com/" if "redbubble" in url else ("https://printerval.com/" if "printerval" in url else "")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            if referer:
                headers["Referer"] = referer
            for attempt in range(2):
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as r:
                        pimg = Image.open(io.BytesIO(r.read())).convert("RGBA")
                    pimg.thumbnail((size, size), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                    canvas.paste(pimg, ((size - pimg.width)//2, (size - pimg.height)//2))
                    
                    def _update_ui(c=canvas):
                        try:
                            if self.winfo_exists():
                                photo = ImageTk.PhotoImage(c, master=self)
                                self.thumb_cache[url] = photo
                                waiting = self._pending_thumb_iids.pop(url, [iid])
                                for wid in waiting:
                                    if self.tree.exists(wid):
                                        self.tree.item(wid, image=photo)
                        except Exception:
                            pass
                    self.after(0, _update_ui)
                    break
                except Exception:
                    if attempt == 0:
                        time.sleep(0.3)
                    else:
                        self._pending_thumb_iids.pop(url, None)
        threading.Thread(target=_w, daemon=True).start()

    def _open_selected_url(self, event=None):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            item_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
            
            target_url = ""
            for itm in self.discovered_items:
                if str(itm.get("item_id", "")).strip() == item_id:
                    target_url = itm.get("url", "")
                    break
            
            if target_url:
                webbrowser.open(target_url)
                return

            is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
            is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
            is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()

            if is_printerval:
                webbrowser.open(f"https://printerval.com/product-p{item_id}")
            elif is_rb:
                webbrowser.open(f"https://www.redbubble.com/i/product/{item_id}")
            elif is_meli:
                webbrowser.open(f"https://articulo.mercadolibre.com.mx/MLM-{item_id}" if not item_id.startswith("http") else item_id)
            elif item_id:
                webbrowser.open(f"https://www.ebay.com/itm/{item_id}")

    def _show_row_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            if row_id not in self.tree.selection():
                self.tree.selection_set(row_id)
            self.tree.focus(row_id)
        if not self.tree.selection(): return
        
        t = self.t
        menu = tk.Menu(self, tearoff=0, bg=t["panel"], fg=t["text"], activebackground=t["accent"], activeforeground="white")
        menu.add_command(label="📥 Add Selected to Results Table", command=self._add_to_results)
        menu.add_command(label="🏪 Enrich Seller Name(s)", command=self._enrich_selected_sellers)
        menu.add_command(label="➕ Add This Seller to Target Queue", command=self._add_single_seller_to_queue)
        menu.add_command(label="🏪 Add This Seller to Stores Box", command=self._add_single_seller_to_stores)
        menu.add_command(label="🛡 Whitelist This Seller (Authorized Dealer)", command=self._whitelist_selected_row_seller)
        menu.add_command(label="🌍 🚨 Resolve Origin & Threat Intel", command=self._resolve_selected_row_threat_intel)
        menu.add_separator()
        menu.add_command(label="☑ Select All (Ctrl+A)", command=self._select_all_rows)
        menu.add_command(label="🌐 Open in Browser", command=self._open_selected_url)
        menu.add_command(label="📋 Copy Listing URL", command=self._copy_selected_row_url)
        menu.add_command(label="👤 Copy Seller Username", command=self._copy_selected_row_seller)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _clean_seller_handle(self, text: str) -> str:
        """Strip badges, emojis, and status suffixes to extract pure seller username."""
        if not text:
            return ""
        s = str(text)
        for prefix in ("🛡", "🏠", "🎯", "⚡", "❓", "🚨", "👤", "🏪"):
            s = s.replace(prefix, "")
        for suffix in ("(Authorized)", "(Source Seller)", "(Targeted/Harvested)", "(Targeted)", "(Harvested)"):
            s = s.replace(suffix, "")
        return s.strip()

    def _resolve_selected_row_threat_intel(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if not sel: return
        vals = self.tree.item(sel)["values"]
        seller_raw = vals[1] if len(vals) > 1 else ""
        seller_handle = self._clean_seller_handle(seller_raw)
        if not seller_handle or seller_handle in ("Resolving...", "Unknown"):
            return

        def _w():
            scraper = getattr(self.parent, "scraper", None)
            if scraper:
                res = scraper.batch_resolve_seller_countries([seller_handle])
                if seller_handle in res:
                    c_val = res[seller_handle].get("country", "Unknown")
                    m_since = res[seller_handle].get("member_since", "")
                    ds = getattr(self.parent, "data_store", None)
                    if ds:
                        ds.set_seller_intel(seller_handle, c_val, member_since=m_since)
            self.after(0, self._populate_tree)
        threading.Thread(target=_w, daemon=True).start()

    def _copy_selected_row_url(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            item_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
            
            url = ""
            for itm in self.discovered_items:
                if str(itm.get("item_id", "")).strip() == item_id:
                    url = itm.get("url", "")
                    break
            
            if not url and item_id:
                is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
                is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
                is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()
                if is_printerval:
                    url = f"https://printerval.com/product-p{item_id}"
                elif is_rb:
                    url = f"https://www.redbubble.com/i/product/{item_id}"
                elif is_meli:
                    url = f"https://articulo.mercadolibre.com.mx/MLM-{item_id}" if not item_id.startswith("http") else item_id
                else:
                    url = f"https://www.ebay.com/itm/{item_id}"

            if url:
                self.clipboard_clear()
                self.clipboard_append(url)
                self.count_var.set(f"📋 Copied listing URL: {url}")
                self.parent._log(f"📋 Copied URL to clipboard: {url}")

    def _copy_selected_row_seller(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if seller_handle and seller_handle not in ("Resolving...", "Unknown"):
                self.clipboard_clear()
                self.clipboard_append(seller_handle)
                self.count_var.set(f"👤 Copied seller handle: '{seller_handle}'")
                self.parent._log(f"👤 Copied seller handle to clipboard: {seller_handle}")
            else:
                self.count_var.set("⚠ No valid seller username on this listing.")

    def _whitelist_selected_row_seller(self):
        sel = self.tree.focus()
        if not sel:
            selected = self.tree.selection()
            if selected: sel = selected[0]
        if sel:
            vals = self.tree.item(sel)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if not seller_handle or seller_handle in ("Resolving...", "Unknown"):
                self.count_var.set("⚠ No valid seller handle to whitelist.")
                return
            ds = getattr(self.parent, "data_store", None)
            if ds and ds.is_seller_whitelisted(seller_handle):
                self.count_var.set(f"🛡 '{seller_handle}' is already Whitelisted.")
                return
            d_name = simpledialog.askstring("Authorized Dealership", f"Enter Dealership Name for '{seller_handle}' (optional):", initialvalue="Authorized Dealership", parent=self)
            if d_name is None:
                self.lift()
                return
            notes = simpledialog.askstring("Analyst Notes", f"Notes for '{seller_handle}' (optional):", initialvalue="Client Approved Whitelist", parent=self) or ""
            b_val = self.target_item.get("brand") or "General / All Brands"
            if ds:
                ds.add_to_whitelist(seller_handle, brand=b_val, dealer_name=d_name, notes=notes)
            self.parent._log(f"🛡 Added '{seller_handle}' to Authorized Whitelist ({b_val}).")
            self.count_var.set(f"🛡 Whitelisted '{seller_handle}' ({b_val})!")
            self._populate_tree()
            self.lift()

    def _append_to_parent_stores(self, seller_handle: str):
        """Append seller handle to the main Stores/Sellers input box without fusion or duplicates."""
        parent = self.parent
        if not hasattr(parent, "store_text"):
            return
        curr = parent.store_text.get("1.0", "end").strip()
        ph = getattr(parent, "store_placeholder", "").strip()
        if not curr or curr == ph:
            parent.store_text.delete("1.0", "end")
            parent.store_text.insert("1.0", seller_handle + "\n")
            parent.store_text.config(fg=parent.theme["text"])
        else:
            lines = [l.strip() for l in curr.splitlines() if l.strip()]
            existing_lowers = [l.lower() for l in lines]
            if seller_handle.lower() not in existing_lowers:
                lines.append(seller_handle)
                parent.store_text.delete("1.0", "end")
                parent.store_text.insert("1.0", "\n".join(lines) + "\n")
                parent.store_text.config(fg=parent.theme["text"])

    def _add_single_seller_to_stores(self):
        """Add highlighted seller(s) in tree directly to Stores text box (supports multi-select)."""
        selected_iids = self.tree.selection()
        if not selected_iids:
            sel = self.tree.focus()
            if sel:
                selected_iids = [sel]
        if not selected_iids:
            self.count_var.set("⚠ No listing selected.")
            return

        sellers = []
        for iid in selected_iids:
            vals = self.tree.item(iid)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if seller_handle and seller_handle not in ("Resolving...", "Unknown"):
                sellers.append(seller_handle)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No valid seller handles to add.")
            return

        for s in unique_sellers:
            self._append_to_parent_stores(s)

        if len(unique_sellers) == 1:
            self.count_var.set(f"🏪 Added '{unique_sellers[0]}' to Stores box!")
            self.parent._log(f"🏪 Added connected seller '{unique_sellers[0]}' to Stores box.")
        else:
            self.count_var.set(f"🏪 Added {len(unique_sellers)} selected seller(s) to Stores box!")
            self.parent._log(f"🏪 Added {len(unique_sellers)} connected seller(s) to Stores box: {', '.join(unique_sellers)}")

    def _add_all_to_stores(self):
        """Append all discovered / selected seller handles directly to main Stores/Sellers input."""
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown"):
                    sellers.append(s_clean)
        else:
            for r in self.discovered_items:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown"):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to add.")
            return

        for s in unique_sellers:
            self._append_to_parent_stores(s)

        self.count_var.set(f"🏪 Added {len(unique_sellers)} seller(s) to Stores box!")
        self.parent._log(f"🏪 Added {len(unique_sellers)} connected seller(s) to Stores box: {', '.join(unique_sellers)}")

    def _add_single_seller_to_queue(self):
        """Add highlighted seller(s) in tree to the Target Queue (supports multi-select)."""
        selected_iids = self.tree.selection()
        if not selected_iids:
            sel = self.tree.focus()
            if sel:
                selected_iids = [sel]
        if not selected_iids:
            self.count_var.set("⚠ No listing selected.")
            return

        sellers = []
        for iid in selected_iids:
            vals = self.tree.item(iid)["values"]
            seller_raw = vals[1] if len(vals) > 1 else ""
            seller_handle = self._clean_seller_handle(seller_raw)
            if seller_handle and seller_handle not in ("Resolving...", "Unknown"):
                sellers.append(seller_handle)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No valid seller handle to enqueue.")
            return

        parent = self.parent
        ds = getattr(parent, "data_store", None)
        whitelisted = [s for s in unique_sellers if (ds.is_seller_whitelisted(s) if ds else False)]
        if whitelisted:
            wl_msg = f"{len(whitelisted)} selected seller(s) are on your Authorized Whitelist:\n{', '.join(whitelisted)}\n\nDo you really want to target them?"
            if not messagebox.askyesno("Whitelisted Seller", wl_msg, parent=self):
                unique_sellers = [s for s in unique_sellers if s not in whitelisted]
                self.lift()
                if not unique_sellers:
                    return

        # 1. Check targeted brands in Brand Library / Presets
        target_brands = [k.split("/")[0] for k, v in parent.brand_states.items() if v == "target"]
        target_brands = list(dict.fromkeys(target_brands))
        if not target_brands:
            target_brands = [self.target_item.get("brand") or "General Brand"]

        custom_includes = [l.strip() for l in parent.include_text.get("1.0", "end").splitlines() if l.strip()]
        generic_excludes = parent._get_active_exclusions() if hasattr(parent, "_get_active_exclusions") else []
        condition = parent.condition_var.get() if hasattr(parent, "condition_var") else "all"
        platform_name = parent._get_current_platform_name() if hasattr(parent, "_get_current_platform_name") else "eBay"

        added_count = 0
        skipped_executed = 0
        for s in unique_sellers:
            self._append_to_parent_stores(s)
            for b_name in target_brands:
                if any(q.get("store", "").strip().lower() == s.strip().lower() and 
                       q.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       q.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for q in parent.queue):
                    continue
                if any(ex.get("store", "").strip().lower() == s.strip().lower() and 
                       ex.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       ex.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for ex in parent.executed_jobs):
                    skipped_executed += 1
                    parent._log(f"ℹ Skipped already-completed search on {platform_name}: [{parent._store_label(s, platform=platform_name)} ▸ {b_name}]")
                    continue

                b_terms = [k.split("/")[-1] for k, v in parent.brand_states.items() if v == "target" and k.split("/")[0] == b_name]
                includes = b_terms if b_terms else (custom_includes if custom_includes else [self.target_item.get("product_type") or b_name.lower()])

                entry = {
                    "store": s,
                    "brand": b_name,
                    "marketplace": platform_name,
                    "includes": list(includes),
                    "excludes": list(generic_excludes),
                    "condition": condition
                }
                parent.queue.append(entry)
                lbl = f"{parent._store_label(s, platform=platform_name)} ▸ {b_name} ({len(includes)} terms | {len(generic_excludes)} excl)"
                parent.queue_list.insert("end", lbl)
                added_count += 1

        if added_count > 0:
            if len(unique_sellers) == 1:
                parent._log(f"🎯 Queued connected seller '{unique_sellers[0]}' for {added_count} brand job(s) on {platform_name}.")
                self.count_var.set(f"🎯 Enqueued '{unique_sellers[0]}' for {added_count} brand(s) [{platform_name}]!")
            else:
                parent._log(f"🎯 Enqueued {added_count} batch jobs across {len(unique_sellers)} selected sellers on {platform_name}.")
                self.count_var.set(f"🎯 Enqueued {added_count} job(s) for {len(unique_sellers)} selected seller(s) [{platform_name}]!")
        else:
            self.count_var.set(f"ℹ Selected seller(s) already queued or previously executed.")

    def _copy_sellers(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown"):
                    sellers.append(s_clean)
        else:
            for r in self.discovered_items:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown"):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to copy.")
            return
        text = ", ".join(unique_sellers)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.count_var.set(f"📋 Copied {len(unique_sellers)} seller handles to clipboard!")
        self.parent._log(f"📋 Copied {len(unique_sellers)} seller handles to clipboard: {text}")

    def _add_to_results(self):
        """Add highlighted or all discovered network listings to the main Results table."""
        selected_iids = self.tree.selection()
        target_records = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                target_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
                for r in self.discovered_items:
                    if target_id and str(r.get("item_id", "")).strip() == target_id:
                        target_records.append(r)
                        break
        else:
            target_records = list(self.discovered_items)

        if not target_records:
            self.count_var.set("⚠ No discovered listings to add.")
            return

        added = 0
        detected_brand = self.target_item.get("brand") or "General Brand"
        ptype = self.target_item.get("product_type", "")
        is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
        is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
        is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()

        default_marketplace = "Printerval" if is_printerval else ("Redbubble" if is_rb else ("Mercado Libre" if is_meli else "eBay"))

        for itm in target_records:
            t = itm.get("title", "")
            if hasattr(self.parent, "_auto_detect_brand_from_title"):
                detected_b, detected_pt = self.parent._auto_detect_brand_from_title(t)
                brand_name = detected_b if detected_b != "Unassigned" else detected_brand
                pt_name = detected_pt or ptype
            else:
                brand_name = detected_brand
                pt_name = ptype

            itm_id = str(itm.get("item_id", "")).strip()
            itm_url = itm.get("url", "")
            if not itm_url:
                if is_printerval and itm_id:
                    itm_url = f"https://printerval.com/product-p{itm_id}"
                elif is_rb and itm_id:
                    itm_url = f"https://www.redbubble.com/i/product/{itm_id}"
                elif is_meli and itm_id:
                    itm_url = f"https://articulo.mercadolibre.com.mx/MLM-{itm_id}"
                elif itm_id:
                    itm_url = f"https://www.ebay.com/itm/{itm_id}"

            mkt = itm.get("marketplace") or default_marketplace

            is_pod_itm = is_printerval or is_rb or any(p in str(mkt).lower() or p in str(itm_url).lower() for p in ("printerval", "redbubble", "teepublic", "zazzle", "spreadshirt", "threadless", "teespring"))
            row = {
                "brand": brand_name,
                "product_type": pt_name,
                "title": t,
                "item_id": itm_id,
                "price": normalize_price_string(itm.get("price", "")),
                "seller": itm.get("seller", "") or "Unknown",
                "location": itm.get("location", "") or ("United States" if is_pod_itm else ""),
                "image_url": itm.get("image_url", ""),
                "url": itm_url,
                "marketplace": mkt,
                "similarity": itm.get("similarity", "Connected Network Match"),
                "threat_badge": "👕 POD Print Syndicate" if is_pod_itm else itm.get("threat_badge", ""),
                "threat_score": 65 if is_pod_itm else itm.get("threat_score", 0)
            }

            # Dedup check
            dedup_key = itm_url.lower().split("?")[0] if itm_url else itm_id
            if dedup_key and dedup_key not in self.parent.seen_item_ids:
                if itm_id:
                    self.parent.seen_item_ids.add(itm_id)
                    self.parent.seen_item_ids.add(f"{mkt}_{itm_id}")
                if itm_url:
                    self.parent.seen_item_ids.add(dedup_key)
                self.parent.results.append(row)
                try:
                    if hasattr(self.parent, "data_store"):
                        self.parent.data_store.add_or_update_listing(row)
                except Exception:
                    pass
                added += 1

        if hasattr(self.parent, "_repopulate_results_table"):
            self.parent._repopulate_results_table()
        if hasattr(self.parent, "_log"):
            self.parent._log(f"📥 Added {added} discovered network listings to Results table ({default_marketplace}).")
        self.count_var.set(f"✓ Added {added} discovered listings to Results!")

    def _add_sellers_to_queue(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown"):
                    sellers.append(s_clean)
        else:
            for r in self.discovered_items:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown"):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to enqueue.")
            return

        parent = self.parent
        ds = getattr(parent, "data_store", None)
        eligible_sellers = [s for s in unique_sellers if not (ds.is_seller_whitelisted(s) if ds else False)]
        skipped_count = len(unique_sellers) - len(eligible_sellers)

        if not eligible_sellers:
            self.count_var.set(f"🛡 All {len(unique_sellers)} sellers are Authorized Dealerships (Skipped).")
            return

        # Check targeted brands in Brand Library
        target_brands = [k.split("/")[0] for k, v in parent.brand_states.items() if v == "target"]
        target_brands = list(dict.fromkeys(target_brands))
        if not target_brands:
            target_brands = [self.target_item.get("brand") or "General Brand"]

        custom_includes = [l.strip() for l in parent.include_text.get("1.0", "end").splitlines() if l.strip()]
        generic_excludes = parent._get_active_exclusions() if hasattr(parent, "_get_active_exclusions") else []
        condition = parent.condition_var.get() if hasattr(parent, "condition_var") else "all"
        platform_name = parent._get_current_platform_name() if hasattr(parent, "_get_current_platform_name") else "eBay"

        added_count = 0
        skipped_executed = 0
        for s in eligible_sellers:
            self._append_to_parent_stores(s)
            for b_name in target_brands:
                if any(q.get("store", "").strip().lower() == s.strip().lower() and 
                       q.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       q.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for q in parent.queue):
                    continue
                if any(ex.get("store", "").strip().lower() == s.strip().lower() and 
                       ex.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       ex.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for ex in parent.executed_jobs):
                    skipped_executed += 1
                    continue
                b_terms = [k.split("/")[-1] for k, v in parent.brand_states.items() if v == "target" and k.split("/")[0] == b_name]
                includes = b_terms if b_terms else (custom_includes if custom_includes else [self.target_item.get("product_type") or b_name.lower()])

                entry = {
                    "store": s,
                    "brand": b_name,
                    "marketplace": platform_name,
                    "includes": list(includes),
                    "excludes": list(generic_excludes),
                    "condition": condition
                }
                parent.queue.append(entry)
                lbl = f"{parent._store_label(s, platform=platform_name)} ▸ {b_name} ({len(includes)} terms | {len(generic_excludes)} excl)"
                parent.queue_list.insert("end", lbl)
                added_count += 1

        msg = f"Enqueued {added_count} job(s) for {len(eligible_sellers)} seller(s)"
        if skipped_count > 0:
            msg += f" (Shielded {skipped_count} Whitelisted Dealers)"
        if skipped_executed > 0:
            msg += f" (Skipped {skipped_executed} already-completed searches)"
        parent._log(f"🎯 Enqueued {added_count} batch jobs across {len(eligible_sellers)} sellers on {platform_name} (Shielded {skipped_count} whitelisted dealers, skipped {skipped_executed} already run).")
        self.count_var.set(f"🎯 {msg}")

    def _enrich_selected_sellers(self):
        """Enrich real merchant/artist names across discovered items in the Hunter Modal."""
        selected_iids = self.tree.selection()
        target_items = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                item_id = str(vals[6]).strip() if len(vals) > 6 else (str(vals[4]).strip() if len(vals) > 4 else "")
                for it in self.discovered_items:
                    if str(it.get("item_id", "")).strip() == item_id:
                        target_items.append(it)
                        break
        else:
            target_items = list(self.discovered_items)

        if not target_items:
            messagebox.showinfo("Enrich Sellers", "No discovered listings to enrich.", parent=self)
            return

        items_to_enrich = [
            it for it in target_items 
            if not it.get("seller") or it.get("seller") in ("Printerval Creator", "Redbubble Creator", "Unknown", "Resolving...") or selected_iids
        ]
        if not items_to_enrich:
            items_to_enrich = list(target_items)

        is_printerval = "printerval" in self.target_item.get("url", "").lower() or "printerval" in str(self.target_item.get("marketplace", "")).lower()
        is_rb = "redbubble" in self.target_item.get("url", "").lower() or "redbubble" in str(self.target_item.get("marketplace", "")).lower()
        is_meli = "mercadolibre" in self.target_item.get("url", "").lower() or "mercadolivre" in self.target_item.get("url", "").lower()

        self.status_lbl.configure(text=f"🏪 Enriching real merchant/artist names for {len(items_to_enrich)} listing(s)...", fg=self.t["accent"])
        self.pbar.pack(side="right", padx=(8, 0))
        self.pbar.start(12)

        def _w():
            try:
                if is_printerval:
                    scraper = getattr(self.parent, "printerval_scraper", None)
                    if not scraper:
                        from printerval_scraper import PrintervalScraper
                        scraper = PrintervalScraper(headless=True)
                    
                    def _prog(cur, tot, it):
                        s_name = it.get("seller", "")
                        self.after(0, lambda: self.status_lbl.configure(text=f"🏪 Enriching Sellers [{cur}/{tot}] -> '{s_name}'"))
                        self.after(0, self._populate_tree)

                    scraper.enrich_seller_info(items_to_enrich, progress_callback=_prog)
                elif is_rb:
                    scraper = getattr(self.parent, "redbubble_scraper", None)
                    if not scraper:
                        from redbubble_scraper import RedbubbleScraper
                        scraper = RedbubbleScraper(headless=True)
                    
                    def _prog(cur, tot, it):
                        s_name = it.get("seller", "")
                        self.after(0, lambda: self.status_lbl.configure(text=f"🏪 Enriching Artists [{cur}/{tot}] -> '{s_name}'"))
                        self.after(0, self._populate_tree)

                    scraper.enrich_seller_info(items_to_enrich, progress_callback=_prog)
                elif is_meli:
                    scraper = getattr(self.parent, "mercadolibre_scraper", None)
                    if not scraper:
                        from mercadolibre_scraper import MercadoLibreScraper
                        scraper = MercadoLibreScraper(headless=False)
                    
                    def _prog(cur, tot, it):
                        s_name = it.get("seller", "")
                        self.after(0, lambda: self.status_lbl.configure(text=f"🏪 Enriching Merchants [{cur}/{tot}] -> '{s_name}'"))
                        self.after(0, self._populate_tree)

                    scraper.enrich_seller_info(items_to_enrich, progress_callback=_prog)
                else:
                    scraper = getattr(self.parent, "scraper", None)
                    if scraper and hasattr(scraper, "enrich_ebay_seller_info"):
                        scraper.enrich_ebay_seller_info(items_to_enrich)

            except Exception as e:
                logger.exception("Error enriching sellers in ConnectedNetworkModal")
            
            def _done():
                self.pbar.stop()
                self.pbar.pack_forget()
                self._populate_tree()
                unique_sellers = set(r["seller"] for r in self.discovered_items if r.get("seller") and r.get("seller") not in ("Printerval Creator", "Redbubble Creator", "Unknown", "Resolving..."))
                self.status_lbl.configure(text=f"✅ Enrichment Complete: {len(unique_sellers)} unique creators/merchants identified across discovered network.", fg=self.t["success"])
            
            self.after(0, _done)

        threading.Thread(target=_w, daemon=True).start()



# ══════════════════════════════════════════════════════════════════════════════
#  REVERSE VISUAL DREDGE RESULTS & THREAT CLONE DISCOVERY MODAL
# ══════════════════════════════════════════════════════════════════════════════
class ReverseVisualModal(tk.Toplevel):
    """
    Dedicated Discovery & Triage Modal for Reverse Visual Search / Visual Threat Catalog Clones.
    Presents the reference photo alongside discovered marketplace listings with side-by-side
    perceptual verification previews, seller intel, match similarity %, and 1-click batch actions.
    """
    def __init__(self, parent, hits: list, target_img, label: str = "Visual Reference", marketplace: str = "eBay", region: Optional[str] = None, target_phash: str = ""):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.hits = hits or []
        self.target_img = target_img
        self.label = label
        self.marketplace = parent._get_current_platform_name(marketplace) if hasattr(parent, "_get_current_platform_name") else (marketplace or "eBay")
        self.region = region
        self.target_phash = target_phash
        self.t = parent.theme
        self.thumb_cache = {}
        self.sort_directions = {}

        loc_str = f" [{region}]" if region else ""
        self.title(f"📸 Reverse Visual Dredge Discovery — {self.marketplace}{loc_str} ({len(self.hits)} Matches)")
        self.geometry("1200x780")
        self.configure(bg=self.t["bg"])
        self.minsize(980, 620)
        self.parent._apply_dark_titlebar(self)

        self._build_ui()
        self._populate_tree()

        # Center modal relative to parent window and reveal
        self.parent._center_window(self, 1200, 780)
        self.lift()
        self.focus_force()

        self.after(200, self._enrich_all_hits)

    def _build_ui(self):
        t = self.t

        # ── 1. Top Target Reference Listing Card ──────────────────────────────
        hdr_frame = tk.Frame(self, bg=t["panel"], padx=16, pady=12, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        hdr_frame.pack(side="top", fill="x", padx=12, pady=(12, 6))

        # Big Thumbnail preview container
        img_box = tk.Frame(hdr_frame, bg=t["entry_bg"], width=104, height=104, highlightbackground=t["border"], highlightthickness=1)
        img_box.pack_propagate(False)
        img_box.pack(side="left", padx=(0, 16))

        self.src_img_lbl = tk.Label(img_box, text="Loading\nPhoto...", bg=t["entry_bg"], fg=t["subtext"], font=FONT_SM)
        self.src_img_lbl.pack(fill="both", expand=True)
        self._load_source_image()

        info_box = tk.Frame(hdr_frame, bg=t["panel"])
        info_box.pack(side="left", fill="both", expand=True)

        badge_row = tk.Frame(info_box, bg=t["panel"])
        badge_row.pack(anchor="w", pady=(0, 4))

        tag_lbl = tk.Label(badge_row, text="📸 TARGET REFERENCE PHOTO", font=("Segoe UI", 8, "bold"), bg=t["accent"], fg="white", padx=8, pady=2)
        tag_lbl.pack(side="left", padx=(0, 8))

        loc_str = f" [{self.region}]" if self.region else ""
        tk.Label(badge_row, text=f"Marketplace: {self.marketplace}{loc_str}", font=("Segoe UI", 8, "bold"), bg=t["entry_bg"], fg=t["subtext"], padx=8, pady=2).pack(side="left", padx=(0, 8))

        title_lbl = tk.Label(info_box, text=f"Target: {self.label}", font=FONT_HEAD, bg=t["panel"], fg=t["text"], wraplength=820, justify="left")
        title_lbl.pack(anchor="w")

        verified_count = sum(1 for h in self.hits if h.get("is_verified_match", h.get("distance", 99) <= 18))
        sub_text = f"⚡ Total Discovered: {verified_count} verified photo clones | {len(self.hits)} total candidate listings evaluated"
        sub_lbl = tk.Label(info_box, text=sub_text, font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        sub_lbl.pack(anchor="w", pady=(4, 0))

        # ── 2. Filters toolbar ────────────────────────────────────────────────
        f_row = tk.Frame(self, bg=t["panel"], padx=12, pady=5, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        f_row.pack(side="top", fill="x", padx=12, pady=(2, 4))

        tk.Label(f_row, text="Thumbnails:", font=FONT_SM, bg=t["panel"], fg=t["subtext"]).pack(side="left", padx=(0, 4))
        self.thumb_size_var = tk.StringVar(value="Medium (100px)")
        self.thumb_size_combo = ttk.Combobox(f_row, textvariable=self.thumb_size_var, values=list(THUMB_CONFIG.keys()), width=14, state="readonly", font=FONT_SM)
        self.thumb_size_combo.pack(side="left", padx=(0, 10))
        self.thumb_size_combo.bind("<<ComboboxSelected>>", self._on_thumb_size_changed)

        match_filters = [
            "(All Harvested Candidates)",
            "🎯 Verified Clones Only",
            "🎯 Exact Matches (90%+)",
            "🖼 High Similarity (80%+)",
            "🔍 Close Candidates (70%+)",
            "📷 Broad Visual Sweep (50%+)"
        ]
        default_match_filter = "🎯 Verified Clones Only" if verified_count > 0 else "(All Harvested Candidates)"
        self.match_filter_var = tk.StringVar(value=default_match_filter)
        self.match_filter_combo = ttk.Combobox(f_row, textvariable=self.match_filter_var, values=match_filters, width=28, state="readonly", font=FONT_SM)
        self.match_filter_combo.pack(side="left", padx=(0, 10))
        self.match_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._populate_tree())

        self.hide_same_seller_var = tk.BooleanVar(value=False)
        same_seller_cb = tk.Checkbutton(f_row, text="Hide Same Seller", variable=self.hide_same_seller_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t["accent"], activebackground=t["panel"], font=FONT_SM)
        same_seller_cb.pack(side="left", padx=(0, 8))

        self.hide_wl_var = tk.BooleanVar(value=False)
        wl_cb = tk.Checkbutton(f_row, text="🛡 Hide Whitelisted Dealers", variable=self.hide_wl_var, command=self._populate_tree, bg=t["panel"], fg=t["text"], selectcolor=t["accent"], activebackground=t["panel"], font=FONT_SM)
        wl_cb.pack(side="left", padx=(0, 8))

        # ── 3. Action Toolbar (Pack bottom first to prevent table overflow clipping) ──
        btn_bar = tk.Frame(self, bg=t["panel"], padx=10, pady=8, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x", padx=12, pady=(4, 8))

        self.count_var = tk.StringVar(value=f"{len(self.hits)} candidate listings discovered")
        count_lbl = tk.Label(btn_bar, textvariable=self.count_var, bg=t["panel"], fg=t["text"], font=FONT_HEAD)
        count_lbl.pack(side="left")

        tk.Button(btn_bar, text="✕ Close", command=self.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="🔄 Enrich Intel", command=self._enrich_all_hits, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📋 Copy Handles", command=self._copy_sellers, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="🏪 To Stores", command=self._add_all_to_stores, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="📥 To Table", command=self._add_to_results, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=8, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(btn_bar, text="➕ Queue Sellers", command=self._add_sellers_to_queue, bg=t["accent"], fg="white", relief="flat", padx=10, pady=4, font=("Segoe UI", 9, "bold")).pack(side="right", padx=4)

        # ── 4. Discovered Network Table ───────────────────────────────────────
        table_frame = tk.Frame(self, bg=t["bg"])
        table_frame.pack(side="top", fill="both", expand=True, padx=12, pady=4)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("similarity", "seller", "origin", "threat", "price", "title", "item_id")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="tree headings", selectmode="extended", style="ReverseVisual.Treeview")

        style = ttk.Style()
        style.configure("ReverseVisual.Treeview", background=t["entry_bg"], foreground=t["text"], fieldbackground=t["entry_bg"], rowheight=108, font=FONT_SM)
        style.configure("ReverseVisual.Treeview.Heading", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9, "bold"))
        style.map("ReverseVisual.Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["select_fg"])])

        self.tree.tag_configure("whitelisted", foreground=t["success"])
        self.tree.tag_configure("clone", foreground=t.get("danger", "#E63946"))
        self.tree.tag_configure("candidate", foreground=t["subtext"])

        self.tree.heading("#0", text="Photo Preview", anchor="center")
        self.tree.column("#0", width=120, minwidth=100, anchor="center", stretch=False)

        self.col_cfg = {
            "similarity": ("Match Type / Visual Fingerprint", 185),
            "seller": ("Discovered Seller", 140),
            "origin": ("Origin", 85),
            "threat": ("Threat Assessment", 175),
            "price": ("Price", 75),
            "title": ("Discovered Listing Title", 360),
            "item_id": ("Item ID", 105)
        }
        for c, (txt, w) in self.col_cfg.items():
            self.tree.heading(c, text=txt, command=lambda _c=c: self._sort_by_column(_c))
            self.tree.column(c, width=w, minwidth=50, stretch=False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._open_selected_url)
        self.tree.bind("<Button-3>", self._show_row_context_menu)
        self.tree.bind("<Control-a>", self._select_all_rows)
        self.tree.bind("<Control-A>", self._select_all_rows)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _load_source_image(self):
        img_src = self.target_img
        if not img_src:
            self.src_img_lbl.configure(text="No Photo\nAvailable")
            return

        def _w():
            try:
                if isinstance(img_src, Image.Image):
                    pimg = img_src.copy()
                elif isinstance(img_src, str) and os.path.exists(img_src):
                    pimg = Image.open(img_src).convert("RGBA")
                elif isinstance(img_src, str) and img_src.startswith("http"):
                    req = urllib.request.Request(img_src, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        pimg = Image.open(io.BytesIO(r.read())).convert("RGBA")
                else:
                    self.after(0, lambda: self.src_img_lbl.configure(text="Photo\nUnavailable"))
                    return

                pimg.thumbnail((96, 96), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
                canvas.paste(pimg, ((96 - pimg.width)//2, (96 - pimg.height)//2))
                photo = ImageTk.PhotoImage(canvas)
                self.thumb_cache["source"] = photo

                def _set():
                    self.src_img_lbl.configure(image=photo, text="")
                    self.src_img_lbl.image = photo
                self.after(0, _set)
            except Exception:
                self.after(0, lambda: self.src_img_lbl.configure(text="Photo\nUnavailable"))
        threading.Thread(target=_w, daemon=True).start()

    def _on_thumb_size_changed(self, event=None):
        size_key = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_key, THUMB_CONFIG["Medium (100px)"])
        style = ttk.Style()
        style.configure("ReverseVisual.Treeview", rowheight=cfg["rowheight"])
        self.tree.configure(show=cfg["show"], style="ReverseVisual.Treeview")
        self.tree.column("#0", width=cfg["col_width"], minwidth=cfg["col_width"], anchor="center", stretch=False)
        self.tree.heading("#0", text="Photo Preview" if cfg["img_size"] > 0 else "", anchor="center")
        self.thumb_cache.clear()
        self._populate_tree()

    def _select_all_rows(self, event=None):
        ch = self.tree.get_children()
        if ch:
            self.tree.selection_set(ch)
            self._on_tree_select()
        return "break"

    def _on_tree_select(self, event=None):
        sel_count = len(self.tree.selection())
        vis_count = len(self.tree.get_children())
        total_count = len(self.hits)
        if sel_count > 0:
            self.count_var.set(f"{vis_count} listings shown ({sel_count} selected) | {total_count} total candidates")
        else:
            self.count_var.set(f"{vis_count} listings shown | {total_count} total candidates")

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        hide_wl = self.hide_wl_var.get()
        hide_same_seller = self.hide_same_seller_var.get()
        match_filter = self.match_filter_var.get()

        size_name = self.thumb_size_var.get()
        cfg = THUMB_CONFIG.get(size_name, THUMB_CONFIG.get("Medium (100px)", {"rowheight": 110, "img_size": 100, "col_width": 116}))
        img_size = cfg.get("img_size", 0)
        show_images = img_size > 0

        ds = getattr(self.parent, "data_store", None)
        shown_count = 0
        seen_sellers = set()

        for itm in self.hits:
            seller = (itm.get("seller") or "Unknown").strip()
            seller_clean = seller.lower()
            is_wl = ds.is_seller_whitelisted(seller) if ds else False
            is_same = bool(seller_clean in seen_sellers)

            if hide_wl and is_wl:
                continue
            if hide_same_seller and is_same:
                continue

            seen_sellers.add(seller_clean)

            sim_txt = itm.get("match_type") or itm.get("threat_badge") or itm.get("similarity") or "🎯 Exact Photo Match (100%)"
            dist = itm.get("distance", 0)
            is_verified = itm.get("is_verified_match", dist <= 18)

            if match_filter == "🎯 Verified Clones Only" and not is_verified:
                continue
            elif "Exact Matches" in match_filter and dist > 6:
                continue
            elif "High Similarity" in match_filter and dist > 12:
                continue
            elif "Close Candidates" in match_filter and dist > 18:
                continue
            elif "50%+" in match_filter and dist > 32:
                continue

            if is_wl:
                seller_display = f"🛡 {seller} (Authorized)"
            else:
                seller_display = f"⚡ {seller}"

            # Threat Intel from DataStore & Item Location
            cached_intel = ds.get_seller_intel(seller) if ds else {}
            seller_country = cached_intel.get("country", "") if cached_intel else ""
            loc_val = itm.get("location", "")
            assessment = ds.compute_threat_assessment(seller_country or loc_val, loc_val) if ds else {}
            c_name = assessment.get("country", "Unknown")
            orig_txt = f"{assessment.get('flag', '❓')} {c_name}" if c_name not in ("Unknown", "Unresolved", "") else (f"📍 {loc_val}" if loc_val else "❓ Unresolved")
            threat_txt = assessment.get("badge", ("🚨 Rogue Photo Clone" if is_verified else "Candidate"))

            price_txt = str(itm.get("price", "N/A"))
            title_txt = str(itm.get("title", "Unknown Title"))
            item_id_txt = str(itm.get("item_id", "N/A"))

            if is_wl:
                row_tag = "whitelisted"
            elif is_verified:
                row_tag = "clone"
            else:
                row_tag = "candidate"

            iid = self.tree.insert("", "end", text="", values=(
                sim_txt,
                seller_display,
                orig_txt,
                threat_txt,
                price_txt,
                title_txt,
                item_id_txt
            ), tags=(row_tag,))

            shown_count += 1

            if show_images and itm.get("image_url"):
                self._load_row_thumbnail(iid, itm["image_url"], img_size)

        self.count_var.set(f"{shown_count} listings shown across {len(seen_sellers)} seller account(s)")

    def _load_row_thumbnail(self, iid, url, img_size):
        if not url:
            return
        if iid in self.thumb_cache:
            try:
                self.tree.item(iid, image=self.thumb_cache[iid])
            except Exception:
                pass
            return

        def _w():
            try:
                if hasattr(self.parent, "raw_img_cache") and url in self.parent.raw_img_cache:
                    pimg = self.parent.raw_img_cache[url].copy()
                else:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(req, timeout=5) as r:
                        pimg = Image.open(io.BytesIO(r.read())).convert("RGBA")

                pimg.thumbnail((img_size, img_size), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
                canvas.paste(pimg, ((img_size - pimg.width)//2, (img_size - pimg.height)//2))

                def _set(c=canvas):
                    try:
                        if self.winfo_exists() and self.tree.exists(iid):
                            photo = ImageTk.PhotoImage(c, master=self)
                            self.thumb_cache[iid] = photo
                            self.tree.item(iid, image=photo)
                    except Exception:
                        pass
                self.after(0, _set)
            except Exception:
                pass
        threading.Thread(target=_w, daemon=True).start()

    def _sort_by_column(self, col):
        if not self.hits:
            return
        descending = self.sort_directions.get(col, False)
        self.sort_directions[col] = not descending
        ds = getattr(self.parent, "data_store", None)

        def get_sort_key(item):
            seller = (item.get("seller") or "").strip()
            if col == "origin":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else ""
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("country", "Unknown").lower()
            elif col == "threat":
                intel = ds.get_seller_intel(seller) if ds else {}
                c_val = intel.get("country", "") if intel else ""
                assessment = ds.compute_threat_assessment(c_val, "") if ds else {}
                return assessment.get("score", 0)
            elif col == "price":
                m = re.search(r"[\d,]+(?:\.\d+)?", str(item.get("price", "")))
                if m:
                    try: return float(m.group(0).replace(",", ""))
                    except ValueError: return 0.0
                return 0.0
            elif col == "item_id":
                try: return int(item.get("item_id", 0))
                except ValueError: return 0
            elif col == "similarity":
                return str(item.get("similarity", "")).lower()
            elif col == "seller":
                return seller.lower()
            elif col == "title":
                return str(item.get("title", "")).lower()
            return str(item.get(col, "")).lower()

        self.hits.sort(key=get_sort_key, reverse=descending)
        self._populate_tree()

    def _enrich_all_hits(self):
        """Resolve seller handles and country origin threat intelligence for all visual clone matches."""
        ds = getattr(self.parent, "data_store", None)
        if not self.hits:
            return
        self.count_var.set(f"🏪 Enriching {len(self.hits)} visual clone merchant account(s)...")

        INVALID_HANDLES = {"ebay merchant", "unknown", "resolving...", "", "i.html", "m.html", "sch", "usr", "str", "itm"}

        def _is_bad(name):
            if not name: return True
            n = str(name).strip().lower()
            return n in INVALID_HANDLES or n.endswith(".html") or n.endswith(".htm")

        def _worker():
            for itm in self.hits:
                s = itm.get("seller", "")
                url = itm.get("url") or (f"https://www.ebay.com/itm/{itm.get('item_id', '')}" if itm.get("item_id") else "")
                if url and _is_bad(s):
                    try:
                        import batch_importer
                        res = batch_importer.fetch_single_listing(url, headless=True)
                        if res:
                            cand_s = res.get("seller", "")
                            if cand_s and not _is_bad(cand_s):
                                itm["seller"] = cand_s
                                s = cand_s
                            if res.get("price") and res.get("price") not in ("$0.00", ""):
                                itm["price"] = res["price"]
                            if res.get("location") and res.get("location") not in ("Unknown", ""):
                                itm["location"] = res["location"]
                            if res.get("title") and not res.get("title").startswith("Imported Listing"):
                                itm["title"] = res["title"]
                    except Exception as e:
                        logger.debug(f"Visual clone fetch error on {url}: {e}")

                # Resolve seller threat intel / country if needed
                if s and not _is_bad(s) and ds:
                    intel = ds.get_seller_intel(s)
                    if not intel or not intel.get("country") or intel.get("country") == "Unknown":
                        try:
                            resolved = self.parent.scraper.resolve_seller_country(s)
                            if resolved and resolved.get("country") and resolved["country"] != "Unknown":
                                ds.set_seller_intel(s, resolved["country"], member_since=resolved.get("member_since", ""))
                        except Exception as e:
                            logger.debug(f"Visual clone country resolve error for {s}: {e}")

            def _finish():
                if self.winfo_exists():
                    self._populate_tree()
                    unique_sellers = {r.get("seller", "") for r in self.hits if r.get("seller") and not _is_bad(r.get("seller"))}
                    self.count_var.set(f"{len(self.hits)} photo clone listings discovered across {len(unique_sellers)} verified merchant account(s)")

            self.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _clean_seller_handle(self, raw_str: str) -> str:
        s = str(raw_str).strip()
        for prefix in ("⚡", "🏠", "🛡", "🎯", "🔗", "👤"):
            s = s.replace(prefix, "")
        for suffix in ("(Authorized)", "(Source Seller)", "(Targeted/Harvested)"):
            s = s.replace(suffix, "")
        return s.strip()

    def _append_to_parent_stores(self, seller_handle: str):
        parent = self.parent
        if not hasattr(parent, "store_text") or not seller_handle:
            return
        curr = parent.store_text.get("1.0", "end").strip()
        ph = getattr(parent, "store_placeholder", "").strip()
        if not curr or curr == ph:
            parent.store_text.delete("1.0", "end")
            parent.store_text.insert("1.0", seller_handle + "\n")
            parent.store_text.config(fg=parent.theme["text"])
        else:
            lines = [l.strip() for l in curr.splitlines() if l.strip()]
            existing_lowers = [l.lower() for l in lines]
            if seller_handle.lower() not in existing_lowers:
                lines.append(seller_handle)
                parent.store_text.delete("1.0", "end")
                parent.store_text.insert("1.0", "\n".join(lines) + "\n")
                parent.store_text.config(fg=parent.theme["text"])

    def _add_all_to_stores(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown", ""):
                    sellers.append(s_clean)
        else:
            for r in self.hits:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown", ""):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to add.")
            return

        for s in unique_sellers:
            self._append_to_parent_stores(s)

        if hasattr(self.parent, "store_full_sweep_var"):
            self.parent.store_full_sweep_var.set(True)

        self.count_var.set(f"🏪 Added {len(unique_sellers)} seller(s) to Stores box & enabled Full Store Sweep!")
        self.parent._log(f"🏪 Added {len(unique_sellers)} discovered visual clone sellers to Stores box: {', '.join(unique_sellers)}")

    def _add_to_results(self):
        selected_iids = self.tree.selection()
        target_records = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                for r in self.hits:
                    target_id = str(vals[6]).strip() if len(vals) > 6 else ""
                    if target_id and str(r.get("item_id")) == target_id:
                        target_records.append(r)
                        break
        else:
            target_records = self.hits

        added = 0
        for itm in target_records:
            t = itm.get("title", "")
            detected_b, detected_pt = self.parent._auto_detect_brand_from_title(t) if hasattr(self.parent, "_auto_detect_brand_from_title") else ("Unassigned", "")
            brand_name = detected_b if detected_b != "Unassigned" else (self.label or "Visual Sweep")
            pt_name = detected_pt or "Visual Clone"

            row = {
                "brand": brand_name,
                "product_type": pt_name,
                "title": t,
                "item_id": str(itm.get("item_id", "")),
                "price": normalize_price_string(itm.get("price", "")),
                "seller": itm.get("seller", ""),
                "location": itm.get("location", ""),
                "image_url": itm.get("image_url", ""),
                "threat_badge": itm.get("threat_badge", "🚨 Visual Clone (100%)"),
                "threat_score": max(itm.get("threat_score", 0), 95),
                "url": itm.get("url", f"https://www.ebay.com/itm/{itm.get('item_id', '')}"),
                "marketplace": self.marketplace
            }
            if row["item_id"] and row["item_id"] not in self.parent.seen_item_ids:
                self.parent.seen_item_ids.add(row["item_id"])
                self.parent.results.append(row)
                added += 1
            else:
                # Update existing row with threat badge
                for r_item in self.parent.results:
                    if str(r_item.get("item_id")) == row["item_id"]:
                        r_item["threat_badge"] = row["threat_badge"]
                        r_item["threat_score"] = row["threat_score"]
                        break

        if hasattr(self.parent, "_repopulate_results_table"):
            self.parent._repopulate_results_table()
        if hasattr(self.parent, "_log"):
            self.parent._log(f"📸 Added/updated {len(target_records)} visual clone listings in Results table ({added} newly added).")
        self.count_var.set(f"✓ Added/updated {len(target_records)} visual clone listings in Results table!")

    def _add_sellers_to_queue(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown", ""):
                    sellers.append(s_clean)
        else:
            for r in self.hits:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown", ""):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No valid seller handles to queue.")
            return

        parent = self.parent
        ds = getattr(parent, "data_store", None)
        eligible_sellers = [s for s in unique_sellers if not (ds.is_seller_whitelisted(s) if ds else False)]
        skipped_count = len(unique_sellers) - len(eligible_sellers)

        if not eligible_sellers:
            self.count_var.set(f"🛡 All {len(unique_sellers)} sellers are Authorized Dealerships (Skipped).")
            return

        target_brands = [k.split("/")[0] for k, v in parent.brand_states.items() if v == "target"]
        target_brands = list(dict.fromkeys(target_brands))
        if not target_brands:
            target_brands = ["Full Store Sweep"]

        custom_includes = [l.strip() for l in parent.include_text.get("1.0", "end").splitlines() if l.strip()]
        generic_excludes = parent._get_active_exclusions() if hasattr(parent, "_get_active_exclusions") else []
        condition = parent.condition_var.get() if hasattr(parent, "condition_var") else "all"
        platform_name = self.marketplace or "eBay"

        added_count = 0
        skipped_executed = 0
        for s in eligible_sellers:
            self._append_to_parent_stores(s)
            for b_name in target_brands:
                if any(q.get("store", "").strip().lower() == s.strip().lower() and 
                       q.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       q.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for q in parent.queue):
                    continue
                if any(ex.get("store", "").strip().lower() == s.strip().lower() and 
                       ex.get("brand", "").strip().lower() == b_name.strip().lower() and 
                       ex.get("marketplace", "eBay").lower() == platform_name.lower() 
                       for ex in parent.executed_jobs):
                    skipped_executed += 1
                    continue

                b_terms = [k.split("/")[-1] for k, v in parent.brand_states.items() if v == "target" and k.split("/")[0] == b_name]
                if b_name == "Full Store Sweep":
                    includes = ["*"]
                else:
                    includes = b_terms if b_terms else (custom_includes if custom_includes else [b_name.lower()])

                entry = {
                    "store": s,
                    "brand": b_name,
                    "marketplace": platform_name,
                    "includes": list(includes),
                    "excludes": list(generic_excludes),
                    "condition": condition
                }
                parent.queue.append(entry)
                lbl = f"{parent._store_label(s, platform=platform_name)} ▸ {b_name} ({len(includes)} terms | {len(generic_excludes)} excl)" if b_name != "Full Store Sweep" else f"{parent._store_label(s, platform=platform_name)} ▸ 🏪 Full Store Sweep"
                parent.queue_list.insert("end", lbl)
                added_count += 1

        msg = f"Enqueued {added_count} job(s) for {len(eligible_sellers)} seller(s)"
        if skipped_count > 0:
            msg += f" (Shielded {skipped_count} Whitelisted Dealers)"
        if skipped_executed > 0:
            msg += f" (Skipped {skipped_executed} already-completed searches)"
        parent._log(f"🎯 Enqueued {added_count} batch jobs across {len(eligible_sellers)} visual clone sellers on {platform_name}.")
        self.count_var.set(f"🎯 {msg}")

    def _copy_sellers(self):
        selected_iids = self.tree.selection()
        sellers = []
        if selected_iids:
            for iid in selected_iids:
                vals = self.tree.item(iid)["values"]
                s_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
                if s_clean and s_clean not in ("Resolving...", "Unknown", ""):
                    sellers.append(s_clean)
        else:
            for r in self.hits:
                s = r.get("seller")
                if s and s not in ("Resolving...", "Unknown", ""):
                    sellers.append(s)

        unique_sellers = list(dict.fromkeys(sellers))
        if not unique_sellers:
            self.count_var.set("⚠ No resolved seller handles to copy.")
            return
        text = ", ".join(unique_sellers)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.count_var.set(f"📋 Copied {len(unique_sellers)} seller handles to clipboard!")
        self.parent._log(f"📋 Copied {len(unique_sellers)} seller handles to clipboard: {text}")

    def _open_selected_url(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        item_id = str(vals[6]).strip() if len(vals) > 6 else ""
        for r in self.hits:
            if str(r.get("item_id")) == item_id:
                u = r.get("url")
                if u:
                    webbrowser.open(u)
                return
        if item_id:
            webbrowser.open(f"https://www.ebay.com/itm/{item_id}")

    def _show_row_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        vals = self.tree.item(row_id)["values"]
        seller_clean = self._clean_seller_handle(vals[1]) if len(vals) > 1 else ""
        item_id = str(vals[6]).strip() if len(vals) > 6 else ""

        menu = tk.Menu(self, tearoff=0, bg=self.t["panel"], fg=self.t["text"], activebackground=self.t["select_bg"], activeforeground=self.t["select_fg"])
        menu.add_command(label="🌐 Open Listing in Browser", command=self._open_selected_url)
        if seller_clean and seller_clean not in ("Resolving...", "Unknown", ""):
            menu.add_command(label=f"🏪 Add '{seller_clean}' to Stores Box", command=lambda: self._append_to_parent_stores(seller_clean))
            menu.add_command(label=f"📋 Copy Seller '{seller_clean}'", command=lambda: [self.clipboard_clear(), self.clipboard_append(seller_clean)])
        menu.add_separator()
        menu.add_command(label="📥 Add This Listing to Results", command=self._add_to_results)
        menu.tk_popup(event.x_root, event.y_root)


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHORIZED DEALERS & MERCHANT WHITELIST MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class WhitelistManagerModal(tk.Toplevel):
    """
    Authorized Dealer & Client Approved Merchant Whitelist Manager.
    Allows analysts to maintain persistent lists of authorized storefronts,
    bulk import dealership lists from client emails/Excel, and auto-shield
    legitimate distributors from false-positive scraping and enforcement.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.t = parent.theme
        self.data_store = parent.data_store
        
        self.title("🛡 Authorized Dealers & Merchant Whitelist Manager")
        self.geometry("980x640")
        self.configure(bg=self.t["bg"])
        self.minsize(800, 500)
        self.parent._apply_dark_titlebar(self)
        
        self._build_ui()
        self._refresh_table()

        # Center modal relative to parent window and reveal
        self.parent._center_window(self, 980, 640)
        self.lift()
        self.focus_force()

    def _build_ui(self):
        t = self.t

        # ── 1. Top Header Card ────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=t["panel"], padx=16, pady=12, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        hdr.pack(side="top", fill="x", padx=12, pady=(12, 6))

        title_row = tk.Frame(hdr, bg=t["panel"])
        title_row.pack(fill="x")
        tk.Label(title_row, text="🛡", font=("Segoe UI", 12), bg=t["panel"], fg=t["accent"]).pack(side="left")
        tk.Label(title_row, text="AUTHORIZED DEALERS & CLIENT APPROVED WHITELIST", font=("Segoe UI", 11, "bold"), bg=t["panel"], fg=t["accent"]).pack(side="left", padx=(4, 0))
        self.stat_lbl = tk.Label(title_row, text="0 Authorized Dealers Registered", font=("Segoe UI", 9, "bold"), bg=t["entry_bg"], fg=t["success"], padx=8, pady=2)
        self.stat_lbl.pack(side="right")

        desc_lbl = tk.Label(hdr, text="Whitelisted dealers and storefronts are automatically shielded across all scrapers, threat intel modules, and syndicate hunters to prevent false-positive enforcement.", font=FONT_SM, bg=t["panel"], fg=t["subtext"])
        desc_lbl.pack(anchor="w", pady=(4, 0))

        # ── 2. Filter & Search Toolbar ────────────────────────────────────────
        filter_bar = tk.Frame(self, bg=t["bg"], padx=4, pady=4)
        filter_bar.pack(side="top", fill="x", padx=12, pady=(2, 6))

        tk.Label(filter_bar, text="🔍 Search / Filter:", bg=t["bg"], fg=t["text"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_table())
        search_entry = tk.Entry(filter_bar, textvariable=self.search_var, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], width=28, font=FONT_SM)
        search_entry.pack(side="left", padx=(0, 12))

        tk.Label(filter_bar, text="Portfolio Brand:", bg=t["bg"], fg=t["text"], font=FONT_SM).pack(side="left", padx=(0, 4))
        self.brand_filter_var = tk.StringVar(value="All Brands")
        brands_list = ["All Brands"] + sorted(list(self.data_store.get_brands().keys()))
        self.brand_combo = ttk.Combobox(filter_bar, textvariable=self.brand_filter_var, values=brands_list, state="readonly", width=18, font=FONT_SM)
        self.brand_combo.pack(side="left", padx=(0, 4))
        self.brand_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_table())

        # ── 3. Whitelist Treeview ─────────────────────────────────────────────
        table_frame = tk.Frame(self, bg=t["bg"])
        table_frame.pack(side="top", fill="both", expand=True, padx=12, pady=4)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("seller", "brand", "dealer_name", "marketplace", "notes", "added_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended", style="Whitelist.Treeview")

        style = ttk.Style()
        style.configure("Whitelist.Treeview", background=t["entry_bg"], foreground=t["text"], fieldbackground=t["entry_bg"], rowheight=28, font=FONT_SM)
        style.configure("Whitelist.Treeview.Heading", background=t["panel"], foreground=t["text"], font=("Segoe UI", 9, "bold"))
        style.map("Whitelist.Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["select_fg"])])

        col_cfg = {
            "seller": ("Seller Handle / Store Slug", 160),
            "brand": ("Brand Portfolio", 130),
            "dealer_name": ("Dealership / Entity Name", 200),
            "marketplace": ("Marketplace Scope", 140),
            "notes": ("Analyst Notes", 220),
            "added_at": ("Date Added", 120)
        }
        for c, (txt, w) in col_cfg.items():
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, minwidth=80)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self._edit_dealer_dialog())

        # ── 4. Bottom Action Toolbar ──────────────────────────────────────────
        btn_bar = tk.Frame(self, bg=t["panel"], padx=16, pady=12, relief="flat", highlightbackground=t["border"], highlightthickness=1)
        btn_bar.pack(side="bottom", fill="x", padx=12, pady=(6, 12))

        tk.Button(btn_bar, text="➕ Add Dealer", command=self._add_dealer_dialog, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=6).pack(side="left", padx=(0, 6))
        tk.Button(btn_bar, text="✏ Edit Dealer", command=self._edit_dealer_dialog, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="📋 Bulk Import List", command=self._bulk_import_dialog, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="🗑 Remove Selected", command=self._remove_selected, bg=t["entry_bg"], fg=t["danger"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="💾 Export CSV", command=self._export_csv, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=12, pady=6, font=FONT_SM).pack(side="left", padx=4)
        tk.Button(btn_bar, text="✕ Close", command=self.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=14, pady=6, font=FONT_SM).pack(side="right")

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        wl = self.data_store.get_whitelist()
        q = self.search_var.get().lower().strip()
        brand_filter = self.brand_filter_var.get()

        total = len(wl)
        shown = 0

        for handle, data in sorted(wl.items()):
            b = data.get("brand", "")
            d_name = data.get("dealer_name", "")
            mp = data.get("marketplace", "All Marketplaces")
            notes = data.get("notes", "")
            date = data.get("date_added") or data.get("added_at") or data.get("date_updated") or ""

            # Filter logic
            if brand_filter != "All Brands" and b.lower() != brand_filter.lower():
                continue
            if q and not any(q in str(x).lower() for x in (handle, b, d_name, mp, notes)):
                continue

            self.tree.insert("", "end", values=(handle, b, d_name, mp, notes, date))
            shown += 1

        self.stat_lbl.config(text=f"{total} Authorized Dealers Registered ({shown} shown)")

    def _show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
        if not self.tree.selection(): return
        
        t = self.t
        menu = tk.Menu(self, tearoff=0, bg=t["panel"], fg=t["text"], activebackground=t["accent"], activeforeground="white")
        menu.add_command(label="✏ Edit Dealer", command=self._edit_dealer_dialog)
        menu.add_command(label="🗑 Remove from Whitelist", command=self._remove_selected)
        menu.add_command(label="📋 Copy Seller Handle", command=self._copy_selected_handle)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_selected_handle(self):
        sel = self.tree.selection()
        if sel:
            handle = self.tree.item(sel[0])["values"][0]
            self.clipboard_clear()
            self.clipboard_append(handle)

    def _edit_dealer_dialog(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Dealer", "Please select an authorized dealer from the table to edit.")
            return
        vals = self.tree.item(sel[0])["values"]
        handle = vals[0]
        self._add_dealer_dialog(edit_handle=handle)

    def _add_dealer_dialog(self, edit_handle=None):
        dlg = tk.Toplevel(self)
        dlg.withdraw()
        is_edit = bool(edit_handle)
        dlg.title("✏ Edit Authorized Dealership" if is_edit else "➕ Add Authorized Dealership")
        dlg.geometry("480x380")
        dlg.configure(bg=self.t["bg"])
        dlg.transient(self)
        dlg.grab_set()
        self.parent._apply_dark_titlebar(dlg)

        t = self.t
        f = tk.Frame(dlg, bg=t["panel"], padx=16, pady=16)
        f.pack(fill="both", expand=True, padx=12, pady=12)

        wl = self.data_store.get_whitelist()
        existing_data = wl.get(edit_handle, {}) if is_edit else {}

        tk.Label(f, text="Seller Handle / Store URL:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        h_entry = tk.Entry(f, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, width=32)
        h_entry.grid(row=0, column=1, sticky="w", pady=4)
        if is_edit:
            h_entry.insert(0, edit_handle)
            h_entry.config(state="disabled")
        else:
            h_entry.focus_set()

        tk.Label(f, text="Brand Portfolio:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        brands = ["General / All Brands"] + sorted(list(self.data_store.get_brands().keys()))
        b_combo = ttk.Combobox(f, values=brands, font=FONT_SM, width=30)
        b_combo.grid(row=1, column=1, sticky="w", pady=4)
        b_combo.set(existing_data.get("brand", "Toyota") if is_edit else "Toyota")

        tk.Label(f, text="Dealership / Entity Name:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=4)
        d_entry = tk.Entry(f, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, width=32)
        d_entry.grid(row=2, column=1, sticky="w", pady=4)
        d_entry.insert(0, existing_data.get("dealer_name", "Authorized Dealership") if is_edit else "Authorized Dealership")

        tk.Label(f, text="Marketplace Scope:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=4)
        mp_options = ["All Marketplaces (Global)", "eBay Only", "ManoMano Only", "TikTok Shop Only", "Mercado Libre Only", "Vinted Only"]
        mp_combo = ttk.Combobox(f, values=mp_options, font=FONT_SM, width=30, state="readonly")
        mp_combo.grid(row=3, column=1, sticky="w", pady=4)
        mp_combo.set(existing_data.get("marketplace", "All Marketplaces (Global)") if is_edit else "All Marketplaces (Global)")

        tk.Label(f, text="Analyst Notes:", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=4)
        n_entry = tk.Entry(f, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, width=32)
        n_entry.grid(row=4, column=1, sticky="w", pady=4)
        n_entry.insert(0, existing_data.get("notes", "") if is_edit else "")

        def _close_dlg():
            try: dlg.grab_release()
            except Exception: pass
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", _close_dlg)

        def _save():
            handle = edit_handle if is_edit else h_entry.get().strip()
            if not handle:
                messagebox.showwarning("Missing Handle", "Please enter a seller handle or store URL.", parent=dlg)
                return
            b = b_combo.get().strip()
            d = d_entry.get().strip() or "Authorized Dealership"
            mp = mp_combo.get().strip() or "All Marketplaces (Global)"
            n = n_entry.get().strip()
            self.data_store.add_to_whitelist(handle, brand=b, dealer_name=d, notes=n, marketplace=mp)
            self.parent._log(f"🛡 Whitelist updated for '{handle}' ({b} • {mp}).")
            self._refresh_table()
            _close_dlg()

        btn_box = tk.Frame(f, bg=t["panel"])
        btn_box.grid(row=5, column=0, columnspan=2, pady=(16, 0), sticky="e")
        tk.Button(btn_box, text="Cancel", command=_close_dlg, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=10, pady=4).pack(side="right", padx=4)
        tk.Button(btn_box, text="💾 Save Changes" if is_edit else "💾 Save Dealer", command=_save, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4).pack(side="right")

        self.parent._center_window(dlg, 480, 380)

    def _bulk_import_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.withdraw()
        dlg.title("📋 Bulk Import Authorized Dealerships")
        dlg.geometry("560x480")
        dlg.configure(bg=self.t["bg"])
        dlg.transient(self)
        dlg.grab_set()
        self.parent._apply_dark_titlebar(dlg)

        def _close_bulk():
            try: dlg.grab_release()
            except Exception: pass
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", _close_bulk)

        t = self.t
        f = tk.Frame(dlg, bg=t["panel"], padx=16, pady=14)
        f.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(f, text="Paste List of Store URLs or Seller Usernames (1 per line):", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        txt = tk.Text(f, height=12, bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"], font=FONT_SM, relief="flat")
        txt.pack(fill="both", expand=True, pady=4)

        opt_frame = tk.Frame(f, bg=t["panel"])
        opt_frame.pack(fill="x", pady=6)
        
        tk.Label(opt_frame, text="Assign Brand:", bg=t["panel"], fg=t["text"], font=FONT_SM).pack(side="left", padx=(0, 4))
        brands = ["General / All Brands"] + sorted(list(self.data_store.get_brands().keys()))
        b_combo = ttk.Combobox(opt_frame, values=brands, font=FONT_SM, width=20)
        b_combo.pack(side="left", padx=(0, 8))
        b_combo.set("Toyota")

        def _do_import():
            raw = txt.get("1.0", "end").strip()
            if not raw:
                messagebox.showwarning("Empty", "Please paste one or more seller handles.", parent=dlg)
                return
            b = b_combo.get().strip()
            added = self.data_store.bulk_add_whitelist(raw, brand=b, notes="Bulk Client Import")
            self.parent._log(f"🛡 Bulk imported {added} authorized dealers for {b}.")
            self._refresh_table()
            messagebox.showinfo("Import Complete", f"Successfully imported {added} authorized dealers into your Whitelist!", parent=dlg)
            dlg.destroy()

        btn_box = tk.Frame(f, bg=t["panel"])
        btn_box.pack(fill="x", pady=(8, 0))
        tk.Button(btn_box, text="Cancel", command=dlg.destroy, bg=t["entry_bg"], fg=t["text"], relief="flat", padx=10, pady=4).pack(side="right", padx=4)
        tk.Button(btn_box, text="📥 Import Dealers", command=_do_import, bg=t["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=4).pack(side="right")

        self.parent._center_window(dlg, 560, 480)

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select one or more dealers to remove.")
            return
        if not messagebox.askyesno("Confirm Removal", f"Remove {len(sel)} dealer(s) from your Authorized Whitelist?"):
            return
        for iid in sel:
            handle = self.tree.item(iid)["values"][0]
            self.data_store.remove_from_whitelist(str(handle))
        self._refresh_table()
        self.parent._log(f"🛡 Removed {len(sel)} dealer(s) from Authorized Whitelist.")

    def _export_csv(self):
        wl = self.data_store.get_whitelist()
        if not wl:
            messagebox.showinfo("Export", "No whitelisted dealers to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile="authorized_dealers_whitelist.csv")
        if not path: return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Seller Handle", "Brand", "Dealership Name", "Notes", "Date Added"])
                for h, d in wl.items():
                    writer.writerow([h, d.get("brand", ""), d.get("dealer_name", ""), d.get("notes", ""), d.get("added_at", "")])
            messagebox.showinfo("Exported", f"Successfully exported {len(wl)} whitelisted dealers to:\n\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))



class AnalystGuideModal(tk.Toplevel):
    """Interactive Analyst Operations Guide, Feature Comparison & Workflow Reference."""
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.theme = parent.theme
        t = self.theme

        self.title("💡 Apollo Brand Intelligence — Analyst Operations Guide & Reference")
        self.geometry("860x700")
        self.minsize(740, 560)
        self.configure(bg=t["bg"])
        self.transient(parent)
        
        if hasattr(parent, "_apply_dark_titlebar"):
            parent._apply_dark_titlebar(self)
        if hasattr(parent, "_load_app_icon"):
            parent._load_app_icon(self)

        # Header Frame
        header = tk.Frame(self, bg=t["panel"], padx=18, pady=14, relief="solid", bd=1)
        header.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(header, text="💡 Analyst Operations & Feature Reference", font=("Segoe UI", 13, "bold"),
                 bg=t["panel"], fg=t["accent"]).pack(anchor="w")
        tk.Label(header, text="Operational guide for high-velocity investigations, cross-border sweeps, and Genesis data contracts.",
                 font=FONT_NORM, bg=t["panel"], fg=t["subtext"]).pack(anchor="w", pady=(2, 0))

        # Scrollable Body Container
        container = tk.Frame(self, bg=t["bg"])
        container.pack(fill="both", expand=True, padx=12, pady=6)

        canvas = tk.Canvas(container, bg=t["bg"], highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=t["bg"])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind("<MouseWheel>", _on_mousewheel)

        def _add_section(title, icon, items):
            card = tk.Frame(scrollable_frame, bg=t["panel"], padx=16, pady=12, relief="solid", bd=1)
            card.pack(fill="x", pady=6)

            h_box = tk.Frame(card, bg=t["panel"])
            h_box.pack(fill="x", pady=(0, 8))
            tk.Label(h_box, text=f"{icon} {title}", font=("Segoe UI", 11, "bold"),
                     bg=t["panel"], fg=t["accent"]).pack(side="left")

            for item_title, desc, badge in items:
                row = tk.Frame(card, bg=t["panel"], pady=4)
                row.pack(fill="x")

                t_row = tk.Frame(row, bg=t["panel"])
                t_row.pack(fill="x")
                tk.Label(t_row, text=item_title, font=("Segoe UI", 9, "bold"),
                         bg=t["panel"], fg=t["text"]).pack(side="left")
                if badge:
                    tk.Label(t_row, text=f" {badge} ", font=("Segoe UI", 8, "bold"),
                             bg=t["entry_bg"], fg=t["accent"], relief="solid", bd=1).pack(side="left", padx=6)

                tk.Label(row, text=desc, font=FONT_NORM, bg=t["panel"], fg=t["subtext"],
                         wraplength=760, justify="left").pack(anchor="w", pady=(2, 0))

        # 1. Rescrape vs. Enrich
        _add_section("Listing Refresh vs. Merchant Discovery", "🔄", [
            ("🔄 Rescrape / Refresh Selected",
             "Live listing fetch directly from the marketplace page (eBay, Vinted, AliExpress, Mercado Libre). Re-pulls high-res photo thumbnails, live prices, exact active titles, and availability. Use this when rows have missing thumbnails, after importing URLs, or to verify if a listing was taken down.",
             "HotKey: F5"),
            ("🏪 Enrich Sellers",
             "Batch background resolver across e-commerce feeds (AliExpress, Temu, Wish, Mercado Libre, eBay) to populate missing merchant storefront IDs. Preserves all other manually edited listing attributes.",
             "Batch Resolver"),
            ("✏ In-Table Cell Editing",
             "Directly edit Brand, Category, Seller Name, Price, or Title in place without navigating away or losing table selection. Automatically recalculates threat intel and updates the Genesis export dataset.",
             "HotKey: F2 / Double-Click")
        ])

        # 2. Threat Intel vs Connected Network Hunter
        _add_section("Syndicate Investigation & Threat Intel", "🕵", [
            ("🔗 Connected Seller Network Hunter",
             "Performs cross-store syndicate correlation to uncover multi-store networks sharing identical telephone numbers, customer service emails, business licenses, or physical 3PL warehouse addresses across platforms.",
             "Syndicate Hunter"),
            ("🌍 Threat Intel & Origin Resolution",
             "Computes seller risk scores, unmasks foreign drop-shippers (e.g. China-based merchants using domestic California/New Jersey 3PL forwarding hubs), and tracks lifetime brand infringement strikes.",
             "Drop-Ship Detection"),
            ("🛡 Enforcement Registry",
             "Centralized ledger aggregating recidivist seller dossiers, captured infringing listings, historical enforcement notices, and total cumulative counterfeit market value ($ MSRP).",
             "Legal Dossier")
        ])

        # 3. Export & Multi-Locale Expander
        _add_section("Genesis Upload & Cross-Border Projections", "💾", [
            ("💾 Standard Genesis Export",
             "Generates an Excel (.xlsx) file matching the exact 18-column Genesis Upload Standard (Columns A–R). Column C contains the live image thumbnail URL, Column B provides active listing hyperlinks, and Column J records verified seller names.",
             "HotKey: Ctrl+E"),
            ("🌐 Multi-Locale International Expander",
             "Projects selected listings across international marketplaces (eBay UK/DE/AU, Mercado Libre Latin America, Vinted Europe). Preserves Genesis Columns A–R intact while appending extended regional metadata (domain, local currency, translated query) starting at Column S+.",
             "Multi-Marketplace")
        ])

        # 4. Visual Threat Catalog
        _add_section("Visual Packaging Catalog & Reverse Search", "🖼", [
            ("🟢 Benign Packaging Catalog",
             "Stores perceptual hash (pHash) fingerprints of verified genuine OEM packaging. Automatically shields legitimate authorized listings from accidental enforcement.",
             "Shielding"),
            ("🔴 Known Counterfeit Catalog",
             "Stores fingerprints of confirmed counterfeit packaging. Automatically flags matching visual clone listings in real time with high threat badges (🚨 Visual Counterfeit).",
             "High Threat"),
            ("📸 Reverse Visual Sweep",
             "Performs a visual reverse lookup to scan active marketplace feeds for duplicate packaging photos used across different seller storefronts.",
             "Visual Sweep")
        ])

        # 5. Hotkeys & Shortcuts
        _add_section("Analyst Hotkeys & Fast Actions", "⌨", [
            ("F2 / Double-Click", "Edit Brand, Category, Seller, Price, or Title in place in the Results Table.", "Quick Edit"),
            ("F5", "Trigger targeted live rescrape on highlighted listings.", "Live Rescrape"),
            ("Ctrl + E", "Instantly export current session results to Genesis Excel (.xlsx).", "Export"),
            ("Ctrl + A", "Select all visible listings in the Results Table.", "Select All"),
            ("Delete", "Remove selected listings from current session.", "Remove"),
            ("Right-Click Context Menu", "Access Reverse Visual Search, WHOIS Lookup, Threat Badges, and Dealership Whitelisting.", "Context Menu")
        ])

        # Bottom Close Button
        btn_bar = tk.Frame(self, bg=t["bg"])
        btn_bar.pack(fill="x", padx=12, pady=(4, 12))
        tk.Button(btn_bar, text="✕ Close Guide", command=self.destroy,
                  font=("Segoe UI", 9, "bold"), bg=t["accent"], fg="white",
                  relief="flat", padx=16, pady=6, cursor="hand2").pack(side="right")

        # Center modal relative to parent window and reveal
        if hasattr(parent, "_center_window"):
            parent._center_window(self, 860, 700)
        else:
            self.deiconify()
        self.lift()
        self.focus_force()


if __name__ == "__main__":
    app = EbayTool()
    app.mainloop()


