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
import time
from typing import Dict, Any, Optional, Tuple
import requests
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
        self._active_contexts: Dict[str, Any] = {}
        self._stop_events: Dict[str, threading.Event] = {}

    def is_session_active(self, platform_key: str) -> bool:
        """Check if an interactive browser session is currently running for platform."""
        t = self._active_connect_threads.get(platform_key)
        return bool(t and t.is_alive())

    def close_session(self, platform_key: str):
        """Signal and force close an active interactive browser session."""
        ev = self._stop_events.get(platform_key)
        if ev:
            ev.set()
        ctx = self._active_contexts.get(platform_key)
        if ctx:
            try:
                ctx.close()
            except Exception:
                pass

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

    def get_credentials_file(self) -> str:
        """Get absolute path to saved marketplace account credentials file."""
        abs_file = os.path.join(self.base_dir, "data/vault_credentials.json")
        os.makedirs(os.path.dirname(abs_file), exist_ok=True)
        return abs_file

    def get_api_credentials_file(self) -> str:
        """Get absolute path to enterprise and platform API credentials file."""
        abs_file = os.path.join(self.base_dir, "data/api_credentials.json")
        os.makedirs(os.path.dirname(abs_file), exist_ok=True)
        return abs_file

    def get_credential(self, platform_key: str) -> Dict[str, str]:
        """Retrieve stored login credentials for a specific platform."""
        all_creds = self.get_all_credentials()
        return all_creds.get(platform_key, {"username": "", "password": ""})

    def save_credential(self, platform_key: str, username: str = "", password: str = "") -> bool:
        """Save login credentials for a specific platform."""
        c_file = self.get_credentials_file()
        try:
            creds = self.get_all_credentials()
            creds[platform_key] = {
                "username": username.strip(),
                "password": password.strip()
            }
            with open(c_file, "w", encoding="utf-8") as f:
                json.dump(creds, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save credentials for {platform_key}: {e}")
            return False

    def get_all_credentials(self) -> Dict[str, Dict[str, str]]:
        """Retrieve all stored login credentials across platforms."""
        c_file = self.get_credentials_file()
        if os.path.exists(c_file):
            try:
                with open(c_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logger.warning(f"Failed to read credentials file: {e}")
        return {}

    def get_api_credentials(self) -> Dict[str, Any]:
        """Retrieve stored Enterprise and Platform API configurations."""
        default_config = {
            "enterprise": {
                "endpoint_url": "",
                "client_id": "",
                "secret_token": "",
                "environment": "production",
                "status": "⚪ Not Configured",
                "last_checked": None
            },
            "ebay_rest": {
                "app_id": "",
                "cert_id": "",
                "dev_id": "",
                "user_token": ""
            }
        }
        api_file = self.get_api_credentials_file()
        if os.path.exists(api_file):
            try:
                with open(api_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k, v in default_config.items():
                            if k not in data or not isinstance(data[k], dict):
                                data[k] = v
                            else:
                                for sub_k, sub_v in v.items():
                                    data[k].setdefault(sub_k, sub_v)
                        return data
            except Exception as e:
                logger.warning(f"Failed to read API credentials file: {e}")
        return default_config

    def save_api_credentials(self, data: Dict[str, Any]) -> bool:
        """Persist Enterprise and Platform API configurations."""
        api_file = self.get_api_credentials_file()
        try:
            with open(api_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save API credentials: {e}")
            return False

    def test_enterprise_connection(self, endpoint_url: str, client_id: str = "", secret_token: str = "") -> Tuple[bool, str]:
        """
        Verify network reachability and gateway authentication status
        for Enterprise Enforcement API endpoint.
        Returns (success: bool, status_message: str).
        """
        url = (endpoint_url or "").strip()
        if not url:
            return False, "❌ Missing Endpoint URL. Please specify base gateway URL."
        if not (url.startswith("http://") or url.startswith("https://")):
            return False, "❌ Invalid Endpoint URL format. Must begin with http:// or https://"

        headers = {
            "User-Agent": "Apollo-Brand-Intelligence-Gateway/3.2.2",
            "Accept": "application/json"
        }
        if secret_token:
            headers["Authorization"] = f"Bearer {secret_token.strip()}"
        if client_id:
            headers["X-Client-ID"] = client_id.strip()

        start_time = time.time()
        try:
            resp = requests.get(url, headers=headers, timeout=5.0)
            latency_ms = int((time.time() - start_time) * 1000)
            status_code = resp.status_code

            if status_code in (200, 201, 204):
                return True, f"🟢 Gateway Connected & Ready (HTTP {status_code}, {latency_ms}ms)"
            elif status_code in (401, 403):
                return True, f"🟡 Endpoint Reachable (HTTP {status_code} Auth Required, {latency_ms}ms)"
            elif status_code == 404:
                return True, f"🟡 Endpoint Reachable (HTTP 404 Not Found at root, {latency_ms}ms)"
            else:
                return False, f"⚠ Server Responded with HTTP {status_code} ({latency_ms}ms)"
        except requests.exceptions.SSLError as ssl_err:
            return False, f"❌ SSL Certificate Error: {ssl_err}"
        except requests.exceptions.ConnectionError:
            return False, "❌ Connection Refused: Unable to connect to host server."
        except requests.exceptions.Timeout:
            return False, "❌ Connection Timed Out: Server did not respond within 5 seconds."
        except Exception as ex:
            return False, f"❌ Connection Error: {ex}"

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
        user to solve verification or log in. Automatically captures cookies continuously.
        """
        if platform_key in self._active_connect_threads and self._active_connect_threads[platform_key].is_alive():
            logger.info(f"Connect session for {platform_key} is already running.")
            return

        stop_event = threading.Event()
        self._stop_events[platform_key] = stop_event

        def _worker():
            cfg = VAULT_PLATFORMS.get(platform_key)
            if not cfg:
                return

            s_dir = self.get_session_dir(platform_key)
            c_file = self.get_cookie_file(platform_key)
            target_url = cfg["url"]

            logger.info(f"Launching interactive session for {cfg['name']} at {target_url}...")
            context = None
            try:
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        s_dir,
                        headless=False,
                        channel="msedge",
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-infobars",
                            "--disable-dev-shm-usage",
                            "--no-first-run",
                            "--no-default-browser-check",
                            "--disable-background-networking"
                        ],
                        ignore_default_args=["--enable-automation"],
                        viewport={"width": 1366, "height": 850}
                    )
                    self._active_contexts[platform_key] = context

                    page = context.pages[0] if context.pages else context.new_page()

                    # Track closure of the primary storefront tab
                    page_closed = threading.Event()
                    def _on_close(_):
                        page_closed.set()
                    page.on("close", _on_close)

                    page.add_init_script("""
                        delete navigator.__proto__.webdriver;
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
                        window.chrome = { runtime: {}, app: {}, csi: () => {}, loadTimes: () => {} };
                    """)

                    # Auto-fill stored credentials when navigating to login forms
                    cred = self.get_credential(platform_key)
                    if cred.get("username") or cred.get("password"):
                        u_json = json.dumps(cred.get("username", ""))
                        p_json = json.dumps(cred.get("password", ""))
                        page.add_init_script(f"""
                            window.__apollo_cred = {{ user: {u_json}, pass: {p_json} }};
                            function __tryFill() {{
                                if (!window.__apollo_cred) return;
                                const userInputs = document.querySelectorAll('input[name="user_id"], input[id="user_id"], input[type="email"], input[name="login"], input[name="username"], input[autocomplete="username"]');
                                userInputs.forEach(el => {{
                                    if (!el.value && window.__apollo_cred.user) {{
                                        el.value = window.__apollo_cred.user;
                                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }});
                                const passInputs = document.querySelectorAll('input[type="password"], input[name="password"], input[id="password"]');
                                passInputs.forEach(el => {{
                                    if (!el.value && window.__apollo_cred.pass) {{
                                        el.value = window.__apollo_cred.pass;
                                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }});
                            }}
                            window.addEventListener('DOMContentLoaded', __tryFill);
                            window.addEventListener('load', __tryFill);
                            setInterval(__tryFill, 1500);
                        """)

                    try:
                        page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
                    except Exception as ge:
                        logger.warning(f"Navigation note for {cfg['name']}: {ge}")

                    # Helper for periodic safe cookie capture while browser is running
                    def _dump_cookies_safe():
                        try:
                            if context and context.pages and not all(pg.is_closed() for pg in context.pages):
                                cks = context.cookies()
                                if cks:
                                    with open(c_file, "w", encoding="utf-8") as cf:
                                        json.dump(cks, cf, indent=2)
                        except Exception:
                            pass

                    # Poll loop: sync cookies continuously, exit on close event or tab close
                    while not stop_event.is_set() and not page_closed.is_set():
                        _dump_cookies_safe()
                        try:
                            if not context.pages or all(pg.is_closed() for pg in context.pages):
                                break
                        except Exception:
                            break
                        if stop_event.wait(1.0):
                            break

                    # Final cookie sync before closing context
                    _dump_cookies_safe()

                    try:
                        context.close()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Error during {cfg['name']} interactive connect: {e}")
            finally:
                self._active_contexts.pop(platform_key, None)
                self._stop_events.pop(platform_key, None)
                self._active_connect_threads.pop(platform_key, None)
                if on_complete:
                    try:
                        on_complete(platform_key)
                    except Exception as oce:
                        logger.warning(f"Error calling on_complete for {platform_key}: {oce}")

        t = threading.Thread(target=_worker, daemon=True)
        self._active_connect_threads[platform_key] = t
        t.start()