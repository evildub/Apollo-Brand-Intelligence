"""
Session & Account Vault Module for Apollo Brand Intelligence Suite 2.1.
Centralizes persistent browser profiles, cookies, and authentication state
across all gated and anti-bot protected marketplaces (Temu, TikTok, Vinted,
Mercado Libre, ManoMano, TeePublic, Etsy, etc.).
"""

import os
import json
import logging
import threading
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

logger = logging.getLogger("ApolloSessionVault")

VAULT_PLATFORMS = {
    "teepublic": {
        "name": "TeePublic",
        "url": "https://www.teepublic.com/",
        "session_dir": "data/teepublic_session",
        "cookie_file": "data/teepublic_cookies.json",
        "icon": "👕",
        "auth_type": "Cloudflare Turnstile & Bot Protection",
        "help": "Pass Cloudflare verification once to enable seamless background POD scraping."
    },
    "etsy": {
        "name": "Etsy",
        "url": "https://www.etsy.com/",
        "session_dir": "data/etsy_session",
        "cookie_file": "data/etsy_cookies.json",
        "icon": "🧶",
        "auth_type": "DataDome & Regional Geo-Cookie",
        "help": "Solve DataDome challenge once to unlock high-volume commercial enforcement sweeps."
    },
    "temu": {
        "name": "Temu",
        "url": "https://www.temu.com/",
        "session_dir": "data/temu_session",
        "cookie_file": "data/temu_cookies.json",
        "icon": "🟠",
        "auth_type": "Akamai Bot Manager & Login",
        "help": "Pass initial slide verification / captcha to enable wholesale supplier searches."
    },
    "tiktok": {
        "name": "TikTok Shop",
        "url": "https://www.tiktok.com/shop",
        "session_dir": "data/tiktok_session",
        "cookie_file": "data/tiktok_cookies.json",
        "icon": "🎵",
        "auth_type": "TikTok Security & Edge Session",
        "help": "Maintain active TikTok search session for deep merchant and PDP extraction."
    },
    "vinted": {
        "name": "Vinted",
        "url": "https://www.vinted.com/",
        "session_dir": "data/vinted_session",
        "cookie_file": "data/vinted_cookies.json",
        "icon": "👗",
        "auth_type": "Cloudflare & Multi-Region Token",
        "help": "Maintain valid region tokens across UK, France, Germany, US, and Spain."
    },
    "meli": {
        "name": "Mercado Libre",
        "url": "https://www.mercadolibre.com/",
        "session_dir": "data/meli_session",
        "cookie_file": "data/meli_cookies.json",
        "icon": "🌎",
        "auth_type": "LATAM Regional Session",
        "help": "Maintain session for Mexico, Brazil, Argentina, and Colombia storefront scans."
    },
    "manomano": {
        "name": "ManoMano",
        "url": "https://www.manomano.fr/",
        "session_dir": "data/manomano_session",
        "cookie_file": "data/manomano_cookies.json",
        "icon": "🧰",
        "auth_type": "Datadome & EU Regional Token",
        "help": "Maintain valid token for France, UK, Germany, Spain, and Italy scans."
    },
    "facebook": {
        "name": "Facebook Marketplace",
        "url": "https://www.facebook.com/marketplace/",
        "session_dir": "data/facebook_session",
        "cookie_file": "data/facebook_cookies.json",
        "icon": "👥",
        "auth_type": "Meta Account Login & Session",
        "help": "Log in once to enable local and nationwide Facebook Marketplace scans."
    },
    "spreadshirt": {
        "name": "Spreadshirt / Spreadshop",
        "url": "https://www.spreadshirt.com/",
        "session_dir": "data/spreadshirt_session",
        "cookie_file": "data/spreadshirt_cookies.json",
        "icon": "🌿",
        "auth_type": "Cloudflare & Bot Protection Profile",
        "help": "Pass Cloudflare verification once to enable seamless background POD scraping."
    },
    "zazzle": {
        "name": "Zazzle",
        "url": "https://www.zazzle.com/",
        "session_dir": "data/zazzle_session",
        "cookie_file": "data/zazzle_cookies.json",
        "icon": "🎨",
        "auth_type": "Cloudflare / Bot Profile",
        "help": "Maintain persistent session to sweep high-res Zazzle design mockups."
    },
    "cafepress": {
        "name": "CafePress",
        "url": "https://www.cafepress.com/",
        "session_dir": "data/cafepress_session",
        "cookie_file": "data/cafepress_cookies.json",
        "icon": "☕",
        "auth_type": "PerimeterX / Bot Challenge Profile",
        "help": "Maintain session for high-speed CafePress catalog extractions."
    },
    "threadless": {
        "name": "Threadless",
        "url": "https://www.threadless.com/",
        "session_dir": "data/threadless_session",
        "cookie_file": "data/threadless_cookies.json",
        "icon": "🧵",
        "auth_type": "Cloudflare Turnstile Profile",
        "help": "Maintain session for Threadless and Artist Shop catalog sweeps."
    },
    "teespring": {
        "name": "TeeSpring (Spring)",
        "url": "https://spring.com/",
        "session_dir": "data/teespring_session",
        "cookie_file": "data/teespring_cookies.json",
        "icon": "🌱",
        "auth_type": "Creator Spring Session",
        "help": "Maintain session for creator storefront and listing sweeps."
    },
    "fineartamerica": {
        "name": "Fine Art America / Pixels",
        "url": "https://fineartamerica.com/",
        "session_dir": "data/fineartamerica_session",
        "cookie_file": "data/fineartamerica_cookies.json",
        "icon": "🖼",
        "auth_type": "Artist & Gallery Session",
        "help": "Maintain session for fine art and high-ticket merchandise surveillance."
    }
}


class SessionVault:
    """Manages persistent browser contexts and credential health for all marketplaces."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self._active_connect_threads: Dict[str, threading.Thread] = {}

    def get_session_dir(self, platform_key: str) -> str:
        """Get absolute path to persistent user data directory for a platform."""
        cfg = VAULT_PLATFORMS.get(platform_key, {})
        rel_dir = cfg.get("session_dir", f"data/{platform_key}_session")
        abs_dir = os.path.join(self.base_dir, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        return abs_dir

    def get_cookie_file(self, platform_key: str) -> str:
        """Get absolute path to saved JSON cookies for a platform."""
        cfg = VAULT_PLATFORMS.get(platform_key, {})
        rel_file = cfg.get("cookie_file", f"data/{platform_key}_cookies.json")
        abs_file = os.path.join(self.base_dir, rel_file)
        os.makedirs(os.path.dirname(abs_file), exist_ok=True)
        return abs_file

    def get_session_status(self, platform_key: str) -> Dict[str, Any]:
        """
        Check health and presence of persistent session for a given platform.
        Returns dict with keys: 'connected', 'last_modified', 'cookie_count', 'summary'.
        """
        cfg = VAULT_PLATFORMS.get(platform_key)
        if not cfg:
            return {"connected": False, "summary": "Unknown Platform"}

        s_dir = self.get_session_dir(platform_key)
        c_file = self.get_cookie_file(platform_key)

        cookie_count = 0
        if os.path.exists(c_file):
            try:
                with open(c_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    if isinstance(cookies, list):
                        cookie_count = len(cookies)
            except Exception:
                pass

        has_profile_data = False
        last_mod = None
        if os.path.exists(s_dir):
            entries = os.listdir(s_dir)
            if entries:
                has_profile_data = True
                try:
                    mtimes = [os.path.getmtime(os.path.join(s_dir, e)) for e in entries]
                    if mtimes:
                        last_mod = max(mtimes)
                except Exception:
                    pass

        is_connected = has_profile_data or (cookie_count > 0)
        status_text = "🟢 Connected & Active" if is_connected else "⚪ Not Connected"
        return {
            "connected": is_connected,
            "cookie_count": cookie_count,
            "last_modified": last_mod,
            "summary": status_text,
            "platform_name": cfg["name"],
            "icon": cfg["icon"],
            "auth_type": cfg["auth_type"],
            "help": cfg["help"],
            "url": cfg["url"]
        }

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return status dictionary for all registered vault platforms."""
        return {k: self.get_session_status(k) for k in VAULT_PLATFORMS}

    def launch_connect_browser(self, platform_key: str, on_complete=None):
        """
        Launch visible Microsoft Edge browser with persistent context allowing
        user to solve verification or log in. Automatically captures cookies upon close.
        """
        if platform_key in self._active_connect_threads and self._active_connect_threads[platform_key].is_alive():
            logger.info(f"Connect session for {platform_key} is already running.")
            return

        def _worker():
            cfg = VAULT_PLATFORMS.get(platform_key)
            if not cfg:
                return

            s_dir = self.get_session_dir(platform_key)
            c_file = self.get_cookie_file(platform_key)
            target_url = cfg["url"]

            logger.info(f"Launching interactive session for {cfg['name']} at {target_url}...")
            try:
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        s_dir,
                        headless=False,
                        channel="msedge",
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-dev-shm-usage"
                        ],
                        viewport={"width": 1366, "height": 850}
                    )
                    page = context.pages[0] if context.pages else context.new_page()
                    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                    
                    try:
                        page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
                    except Exception as ge:
                        logger.warning(f"Navigation note for {cfg['name']}: {ge}")

                    try:
                        page.wait_for_event("close", timeout=0)
                    except Exception:
                        pass

                    try:
                        cookies = context.cookies()
                        if cookies:
                            with open(c_file, "w", encoding="utf-8") as cf:
                                json.dump(cookies, cf, indent=2)
                            logger.info(f"Saved {len(cookies)} cookies for {cfg['name']}.")
                    except Exception as ce:
                        logger.warning(f"Failed to dump cookies for {cfg['name']}: {ce}")

                    try:
                        context.close()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Error during {cfg['name']} interactive connect: {e}")
            finally:
                if on_complete:
                    on_complete(platform_key)

        t = threading.Thread(target=_worker, daemon=True)
        self._active_connect_threads[platform_key] = t
        t.start()