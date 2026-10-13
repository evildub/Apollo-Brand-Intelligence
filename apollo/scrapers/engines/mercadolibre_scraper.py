"""
Mercado Libre Scraper Module for Apollo Brand Intelligence Suite.
Specialized in automated retrieval of Latin American automotive counterfeit listings
across Mexico (MLM), Brazil (MLB), Argentina (MLA), and Colombia (MCO).

Features:
- Playwright + Native Microsoft Edge Stealth automation.
- Persistent session profile to preserve trust cookies.
- Intelligent reCAPTCHA / DataDome wall detection with interactive clearance.
- Mandatory Account Authentication detection with 1-time persistent login saving.
- Structured DOM extraction for both classic (ui-search-layout) and modern (poly-card) layouts.
- Currency normalization (MXN/BRL/ARS to USD) for seamless threat intel and ROI valuation.
"""

import os
import re
import time
import logging
import threading
import urllib.parse
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger("Apollo.MercadoLibreScraper")

# Approximate Latin American currency conversion rates to USD (updated baseline)
EXCHANGE_RATES_TO_USD = {
    "MXN": 0.053,   # Mexican Peso (~18.8 MXN / USD)
    "BRL": 0.180,   # Brazilian Real (~5.55 BRL / USD)
    "ARS": 0.0010,  # Argentine Peso
    "COP": 0.00025, # Colombian Peso
    "CLP": 0.0011,  # Chilean Peso
    "PEN": 0.27,    # Peruvian Sol
    "UYU": 0.025,   # Uruguayan Peso
    "USD": 1.000,
}

# Regional domain mappings
REGIONAL_DOMAINS = {
    "MLM": {"domain": "listado.mercadolibre.com.mx", "home": "https://www.mercadolibre.com.mx", "currency": "MXN", "country": "Mexico", "flag": "🇲🇽", "rate": 0.053},
    "MLB": {"domain": "lista.mercadolivre.com.br", "home": "https://www.mercadolivre.com.br", "currency": "BRL", "country": "Brazil", "flag": "🇧🇷", "rate": 0.180},
    "MLA": {"domain": "listado.mercadolibre.com.ar", "home": "https://www.mercadolibre.com.ar", "currency": "ARS", "country": "Argentina", "flag": "🇦🇷", "rate": 0.0010},
    "MCO": {"domain": "listado.mercadolibre.com.co", "home": "https://www.mercadolibre.com.co", "currency": "COP", "country": "Colombia", "flag": "🇨🇴", "rate": 0.00025},
    "MLC": {"domain": "listado.mercadolibre.cl", "home": "https://www.mercadolibre.cl", "currency": "CLP", "country": "Chile", "flag": "🇨🇱", "rate": 0.0011},
    "MPE": {"domain": "listado.mercadolibre.com.pe", "home": "https://www.mercadolibre.com.pe", "currency": "PEN", "country": "Peru", "flag": "🇵🇪", "rate": 0.27},
    "MLU": {"domain": "listado.mercadolibre.com.uy", "home": "https://www.mercadolibre.com.uy", "currency": "UYU", "country": "Uruguay", "flag": "🇺🇾", "rate": 0.025},
}


class MercadoLibreScraper:
    def __init__(self, headless: bool = True, site_code: str = "MLM"):
        self.headless = headless
        self.site_code = site_code if site_code in REGIONAL_DOMAINS else "MLM"
        self._pw = None
        self._context = None
        
        # Persistent profile directory to store trust cookies & login credentials
        self.profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Apollo_Meli_Session"
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    def _find_edge_path(self) -> Optional[str]:
        """Locate native Microsoft Edge executable on Windows."""
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ]
        return next((p for p in edge_paths if os.path.exists(p)), None)

    def _clean_profile_locks(self):
        """Clean any stale Chromium singleton lock files and terminate orphaned Edge processes to avoid ProcessSingleton errors."""
        lock_files = [os.path.join(self.profile_dir, lk) for lk in ("SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile")]
        has_locks = any(os.path.exists(lf) for lf in lock_files)
        if has_locks:
            try:
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            except Exception:
                pass
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except Exception:
                        pass

    def _apply_cdp_window_bounds(self, is_stealth: bool, window_pos: tuple = (100, 100), window_size: tuple = (1280, 800)):
        """Dynamically move active Playwright browser window on-screen or off-screen via Chrome DevTools Protocol."""
        if not self._context:
            return
        try:
            pages = [p for p in self._context.pages if not p.is_closed()]
            if pages:
                page = pages[0]
                cdp = self._context.new_cdp_session(page)
                win = cdp.send("Browser.getWindowForTarget")
                if is_stealth:
                    target_bounds = {"left": -2400, "top": -2400, "width": 1366, "height": 850, "windowState": "normal"}
                else:
                    target_bounds = {"left": window_pos[0], "top": window_pos[1], "width": window_size[0], "height": window_size[1], "windowState": "normal"}
                cdp.send("Browser.setWindowBounds", {
                    "windowId": win["windowId"],
                    "bounds": target_bounds
                })
                cdp.detach()
        except Exception as e:
            logger.debug(f"CDP window bound shift notice in Mercado Libre: {e}")

    def set_headless(self, is_headless: bool, shift_active_window: bool = True):
        """
        Dynamically update headless/stealth mode.
        If persistent context has active pages, immediately shifts the browser window
        on-screen or off-screen using Chrome DevTools Protocol without interrupting scraping.
        """
        self.headless = is_headless
        if shift_active_window and self._context:
            self._apply_cdp_window_bounds(is_stealth=is_headless)

    def _get_context(self, force_visible: bool = False, window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """Initialize or return existing persistent Playwright context with stealth evasions."""
        from playwright.sync_api import sync_playwright
        if self._context is not None:
            # Context already running: ensure window is positioned correctly for current stealth mode
            target_stealth = self.headless and not force_visible
            self._apply_cdp_window_bounds(is_stealth=target_stealth, window_pos=window_pos, window_size=window_size)
            return self._context

        self._clean_profile_locks()
        if self._pw is None:
            self._pw = sync_playwright().start()
        edge_path = self._find_edge_path()

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--lang=es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7",
        ]

        # Cloudflare Evasion: Never run headless=True on Mercado Libre. Position window offscreen when stealth mode is requested.
        is_headless = False
        if self.headless and not force_visible:
            args.extend(["--window-position=-2400,-2400", "--window-size=1366,850"])
        elif force_visible:
            args.extend([f"--window-position={window_pos[0]},{window_pos[1]}", f"--window-size={window_size[0]},{window_size[1]}"])

        kwargs = {
            "user_data_dir": self.profile_dir,
            "headless": is_headless,
            "args": args,
            "viewport": {"width": window_size[0] if force_visible else 1366, "height": window_size[1] if force_visible else 850},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "locale": "es-MX",
            "timezone_id": "America/Mexico_City",
        }
        if edge_path:
            kwargs["executable_path"] = edge_path

        try:
            self._context = self._pw.chromium.launch_persistent_context(**kwargs)
        except Exception as e:
            logger.warning(f"Persistent context launch retry after process cleanup: {e}")
            self._clean_profile_locks()
            time.sleep(0.6)
            self._context = self._pw.chromium.launch_persistent_context(**kwargs)

        return self._context

    def close(self):
        """Safely close browser context and Playwright instance."""
        try:
            if self._context:
                try:
                    self._context.close()
                except Exception:
                    pass
                self._context = None
            if self._pw:
                try:
                    self._pw.stop()
                except Exception:
                    pass
                self._pw = None
        except Exception as e:
            logger.debug(f"Error closing Mercado Libre browser context: {e}")
        finally:
            self._clean_profile_locks()

    def launch_interactive_auth(self, site_code: str = "MLM", window_pos: tuple = (100, 100), window_size: tuple = (1100, 800)):
        """
        Open a visible browser session for the user to sign in or solve
        the initial security challenge, persisting cookies permanently.
        """
        def _run():
            try:
                self.close()
                self._clean_profile_locks()
                context = self._get_context(force_visible=True, window_pos=window_pos, window_size=window_size)
                
                # Close duplicate restored tabs
                while len(context.pages) > 1:
                    try:
                        context.pages[-1].close()
                    except Exception:
                        break

                page = context.pages[0] if context.pages else context.new_page()
                site_info = REGIONAL_DOMAINS.get(site_code, REGIONAL_DOMAINS.get("MLM", {}))
                home_url = site_info.get("home", "https://www.mercadolibre.com.mx")
                login_url = f"https://www.mercadolibre.com/jms/{site_code.lower()}/lgz/login"

                try:
                    page.goto(login_url, wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    page.goto(home_url, wait_until="domcontentloaded")

                # Wait for user to interact or close browser window
                try:
                    page.wait_for_event("close", timeout=600000)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error launching interactive auth for Mercado Libre: {e}")
            finally:
                self.close()
                self._clean_profile_locks()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _extract_item_id(self, url: str) -> str:
        """
        Extract canonical Mercado Libre listing ID.
        Prioritizes winner ID 'wid=' (per-seller specific listing ID on catalog items)
        and 'item_id=' before falling back to master path ID.
        """
        if not url:
            return ""
        # 1. Check for wid= (Winner ID / Specific Catalog Seller Item ID)
        m_wid = re.search(r'[?&#]wid=(ML[A-Z0-9_-]+|\d+)', url, re.IGNORECASE)
        if m_wid:
            wid_val = m_wid.group(1).replace("-", "").upper()
            if not wid_val.startswith("ML"):
                wid_val = f"{self.site_code}{wid_val}"
            return wid_val

        # 2. Check for item_id=
        m_item = re.search(r'[?&#]item_id=(ML[A-Z0-9_-]+|\d+)', url, re.IGNORECASE)
        if m_item:
            it_val = m_item.group(1).replace("-", "").upper()
            if not it_val.startswith("ML"):
                it_val = f"{self.site_code}{it_val}"
            return it_val

        # 3. Direct listing or catalog ID in URL path
        m = re.search(r"/(ML[A-Z]-?\d+)", url, re.IGNORECASE)
        if m:
            return m.group(1).replace("-", "").upper()
        m_num = re.search(r"(\d{8,15})", url)
        if m_num:
            return f"{self.site_code}{m_num.group(1)}"
        return ""

    def _convert_price_to_usd(self, price_raw: str, currency_code: str = "MXN") -> tuple:
        """
        Parse raw localized price string and calculate estimated USD value.
        Returns (display_price_str, numeric_usd_val).
        """
        if not price_raw:
            return "$0.00", 0.0

        clean = re.sub(r"[^\d.,]", "", str(price_raw))
        if "." in clean and "," in clean:
            if clean.rfind(",") > clean.rfind("."):
                clean = clean.replace(".", "").replace(",", ".")
            else:
                clean = clean.replace(",", "")
        elif "," in clean:
            parts = clean.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                clean = parts[0] + "." + parts[1]
            else:
                clean = clean.replace(",", "")

        try:
            local_val = float(clean)
        except ValueError:
            local_val = 0.0

        rate = EXCHANGE_RATES_TO_USD.get(currency_code.upper(), 0.053)
        usd_val = round(local_val * rate, 2)
        
        display_str = f"${usd_val:.2f} USD (${local_val:,.0f} {currency_code})"
        return display_str, usd_val

    def _clean_seller_name(self, raw_text: str, url: str = "") -> str:
        """
        Sanitize seller name, filtering out navigation boilerplate like
        'Ir para a página do vendedor' or '+5.000 Seguidores', and extracting real seller handles
        from /pagina/{seller}, /loja/{seller}, or _CustId_{id} URLs.
        """
        cleaned = (raw_text or "").strip()
        cleaned = re.sub(r'^(?:Vendido por|Vendido e entregue por|Por|Vendedor)\s+', '', cleaned, flags=re.IGNORECASE).strip()
        
        # Check if it's an Official Store / 1P Retailer
        if "loja oficial" in cleaned.lower() or "tienda oficial" in cleaned.lower():
            if "mercado livre" in cleaned.lower() or "mercado libre" in cleaned.lower():
                return "Mercado Livre (Loja Oficial)"
            return cleaned.title()
        if cleaned.lower() in ("mercado livre (loja oficial)", "mercado libre (tienda oficial)"):
            return cleaned

        noise_patterns = [
            r'\b(?:ir para|ir a la)\b',
            r'p[aá]gina d[eo] vendedor',
            r'\b\+?\d+[\d.,]*\s*seguidores\b',
            r'^\s*mercado\s+(?:livre|libre)\s*$',
            r'^\s*mercado\s+(?:pontos|envios|pago)\b',
            r'\b(?:devolu[cç][aã]o|garant[ií]a|ver ma[ií]s)\b',
            r'\b(?:comprar agora|adicionar ao carrinho|meios de pagamento|formas de pago)\b',
            r'\b(?:sem juros|com juros)\b',
            r'\b\d+%\s*off\b',
            r'\b(?:cupom|cup[oó]n|desconto|frete gr[aá]tis)\b',
            r'^\s*(?:r\$|usd|\$)\b',
        ]
        is_noise = (
            not cleaned or
            len(cleaned) > 70 or
            bool(re.search(r'^\s*R?\$?\s*\d+[,.]\d+', cleaned, re.IGNORECASE)) or
            any(re.search(pat, cleaned, re.IGNORECASE) for pat in noise_patterns)
        )
        
        if not is_noise:
            return cleaned

        if url:
            # /pagina/lojacdc -> LOJACDC
            m_pag = re.search(r'/pagina/([^/?#]+)', url, re.IGNORECASE)
            if m_pag:
                cand = m_pag.group(1).replace("-", " ").replace("_", " ").strip()
                return cand.upper() if len(cand) <= 8 else cand.title()
            
            # /loja/long-dog -> Long Dog
            m_loja = re.search(r'/loja/([^/?#]+)', url, re.IGNORECASE)
            if m_loja:
                cand = m_loja.group(1).replace("-", " ").replace("_", " ").strip()
                return cand.title()
            
            # _CustId_1657944695 or seller_id=1657944695
            m_cust = re.search(r'(?:_CustId_|seller_id=)(\d+)', url, re.IGNORECASE)
            if m_cust:
                return f"MeLi_Seller_{m_cust.group(1)}"

        return "Mercado Libre Seller"

    def _construct_competitor_listing_url(self, href_val: str, catalog_url: str, c_item_id: str) -> tuple[str, str]:
        """
        Construct a direct, functional listing PDP URL for a catalog competitor,
        and preserve the seller profile URL as store_url.
        """
        store_url = href_val if href_val and ("_CustId_" in href_val or "/pagina/" in href_val or "/loja/" in href_val or "seller_id=" in href_val) else ""
        
        # 1. If we have a specific Mercado Libre Item ID (e.g. MLB7069934198 or MLM123456)
        if c_item_id and re.match(r'^ML[A-Z]\d+$', c_item_id, re.IGNORECASE):
            clean_id = c_item_id.upper()
            if catalog_url and "/p/" in catalog_url:
                base_cat = catalog_url.split("?")[0].split("#")[0]
                return f"{base_cat}?pdp_filters=item_id:{clean_id}", store_url
            else:
                site_prefix = clean_id[:3]
                raw_num = clean_id[3:]
                # Canonical regional direct product URL
                if site_prefix == "MLB":
                    return f"https://produto.mercadolivre.com.br/MLB-{raw_num}", store_url
                elif site_prefix == "MLM":
                    return f"https://articulo.mercadolibre.com.mx/MLM-{raw_num}", store_url
                elif site_prefix == "MLA":
                    return f"https://articulo.mercadolibre.com.ar/MLA-{raw_num}", store_url
                elif site_prefix == "MCO":
                    return f"https://articulo.mercadolibre.com.co/MCO-{raw_num}", store_url
                elif site_prefix == "MLC":
                    return f"https://articulo.mercadolibre.com.cl/MLC-{raw_num}", store_url
                elif site_prefix == "MPE":
                    return f"https://articulo.mercadolibre.com.pe/MPE-{raw_num}", store_url
                elif site_prefix == "MLU":
                    return f"https://articulo.mercadolibre.com.uy/MLU-{raw_num}", store_url

        # 2. If catalog_url is available, link directly to the catalog product
        if catalog_url:
            return catalog_url.split("#")[0], store_url

        # 3. Fallback to href_val
        return href_val or "", store_url

    def _is_relevant_search_card(self, title: str, url: str, query: str) -> bool:
        """
        Check if a search card title or URL is reasonably relevant to the search query,
        preventing off-target competitor ad bleed (e.g. Nexgard/Simparic ads during a Bravecto search).
        """
        if not query or query.strip() in ("*", "All", "all", "Full Search", "Full Store Sweep"):
            return True
        
        clean_q = query.strip().lower()
        t_lower = (title or "").lower()
        u_lower = (url or "").lower()
        
        # 1. Exact phrase match in title or URL
        if clean_q in t_lower or clean_q in u_lower:
            return True
        
        # 2. Extract meaningful tokens (>= 3 chars, skip common stopwords)
        STOPWORDS = {"para", "com", "sem", "por", "dos", "das", "de", "do", "da", "em", "um", "uma", "the", "and", "for", "with"}
        q_tokens = [w for w in re.findall(r'[a-zA-Z0-9]+', clean_q) if len(w) >= 3 and w not in STOPWORDS]
        if not q_tokens:
            return True
        
        # Primary / Anchor token (the brand or first main keyword)
        anchor_token = q_tokens[0]
        if anchor_token in t_lower or anchor_token in u_lower:
            return True
        
        # Any match on >= 2 tokens for multi-word queries
        matched_tokens = sum(1 for tok in q_tokens if tok in t_lower or tok in u_lower)
        if matched_tokens >= 1 and len(q_tokens) == 1:
            return True
        if matched_tokens >= 2:
            return True
            
        return False

    def _ensure_search_page_loaded(self, page, target_url: str, log_func) -> bool:
        """
        Handle cookie banners, Captcha walls, and mandatory Account Sign-In gates,
        ensuring the page reaches the search results with verified session cookies.
        """
        for cycle in range(3):
            cur_url = page.url.lower()
            cur_title = page.title().lower()

            # 1. Dismiss cookie banner if present
            try:
                cookie_btn = page.query_selector("button[data-testid='action:understood-button'], button:has-text('Aceptar cookies'), button:has-text('Aceitar cookies'), button:has-text('Entendido'), button:has-text('Concordar')")
                if cookie_btn and cookie_btn.is_visible():
                    cookie_btn.click()
                    page.wait_for_timeout(500)
            except Exception:
                pass

            # 2. Captcha Wall Handling
            if "captcha/wall" in cur_url or "seguridad" in cur_title or "seguranca" in cur_title or "segurança" in cur_title:
                if not self.headless:
                    log_func("⚠ [Mercado Libre] Security captcha challenge presented. Please solve the captcha in the browser window...")
                    for sec in range(45):
                        cur_url = page.url.lower()
                        cur_title = page.title().lower()
                        if "captcha/wall" not in cur_url and "seguridad" not in cur_title and "seguranca" not in cur_title and "segurança" not in cur_title:
                            log_func("✅ [Mercado Libre] Security captcha passed!")
                            page.wait_for_timeout(2000)
                            break
                        page.wait_for_timeout(1000)
                else:
                    log_func("⚠ [Mercado Libre] Security verification prompt (reCAPTCHA wall) active.")
                    log_func("💡 Tip: Toggle off '👻 Stealth Mode' in top bar to solve once and store trust cookies.")
                    for sec in range(6):
                        cur_url = page.url.lower()
                        cur_title = page.title().lower()
                        if "captcha/wall" not in cur_url and "seguridad" not in cur_title and "seguranca" not in cur_title and "segurança" not in cur_title:
                            break
                        page.wait_for_timeout(1000)

            # Update current state
            cur_url = page.url.lower()
            cur_title = page.title().lower()

            # 3. Account Login Gate Detection (Spanish / Portuguese / English)
            is_login_gate = False
            try:
                body_text = page.inner_text("body").lower()
                if ("to continue, log in" in body_text or 
                    "i already have an account" in body_text or 
                    "para continuar, ingresa" in body_text or 
                    "inicia sesión" in body_text or 
                    "para continuar, acesse" in body_text or
                    "acesse a sua conta" in body_text or
                    "acesse sua conta" in body_text or
                    "entre na sua conta" in body_text or
                    "já tenho conta" in body_text or
                    "ja tenho conta" in body_text or
                    "/login" in cur_url or 
                    "auth.mercadolibre" in cur_url or
                    "auth.mercadolivre" in cur_url):
                    is_login_gate = True
            except Exception:
                pass

            if is_login_gate:
                if not self.headless:
                    log_func("🔑 [Mercado Libre] Account sign-in required ('Hello! To continue, log in to your account').")
                    log_func("👉 Please click 'I already have an account' (or 'I'm new') in the open browser to sign in. The session will be saved permanently!")
                    
                    # Wait up to 90 seconds for user to complete sign-in
                    for wait_sec in range(90):
                        cur_url = page.url.lower()
                        cur_title = page.title().lower()
                        try:
                            body_check = page.inner_text("body").lower()
                            if ("to continue, log in" not in body_check and 
                                "i already have an account" not in body_check and 
                                "/login" not in cur_url and 
                                "auth.mercadolibre" not in cur_url):
                                log_func("✅ [Mercado Libre] Account login verified! Session permanently stored.")
                                page.wait_for_timeout(2000)
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)
                else:
                    log_func("🔑 [Mercado Libre] Mandatory login prompt encountered.")
                    log_func("💡 Tip: Toggle off '👻 Stealth Mode' in top bar to sign in once. Your session will persist for all future searches.")

                # Re-navigate directly to target search results with the authenticated session
                try:
                    log_func(f"🌐 [Mercado Libre] Navigating to search results: {target_url}")
                    page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(3000)
                except Exception as ex:
                    log_func(f"⚠ Search navigation after login: {ex}")

            # 4. Check if listing cards are present on page
            cards_count = page.evaluate("""() => {
                return document.querySelectorAll(
                    '.ui-search-layout__item, .poly-card, li.ui-search-layout__item, div.poly-card__content, .ui-search-result, ol.ui-search-layout li'
                ).length;
            }""")

            if cards_count > 0:
                return True

            # If we're on the search URL and cards are still rendering, wait briefly
            if "listado.mercadolibre" in cur_url or "lista.mercadolivre" in cur_url:
                page.wait_for_timeout(2000)
                cards_count = page.evaluate("""() => {
                    return document.querySelectorAll(
                        '.ui-search-layout__item, .poly-card, li.ui-search-layout__item, div.poly-card__content, .ui-search-result, ol.ui-search-layout li'
                    ).length;
                }""")
                if cards_count > 0:
                    return True

        return True

    def search(self, query: str, max_items: int = 50, max_pages: int = None, condition: str = "all", expand_catalog: bool = True, stop_event: threading.Event = None, pause_event: threading.Event = None, log_callback=None) -> List[Dict]:
        """
        Execute search on Mercado Libre using persistent stealth automation.
        Automatically expands Catalog Buy Box listings (/p/) to harvest all competing merchants.
        
        Args:
            query: Keyword string (e.g., 'Bravecto' or 'Toyota emblem')
            max_items: Maximum listings to return (used as fallback when max_pages is None)
            max_pages: Number of search result pages to scan (e.g., 1, 2, 5)
            condition: 'all', 'new', or 'used'
            expand_catalog: If True, deep checks catalog product pages for all competing sellers
            stop_event: Optional threading.Event for stopping
            pause_event: Optional threading.Event for pausing
            log_callback: Optional callable for live UI logging
            
        Returns:
            List of normalized listing dicts with each seller as their own result row.
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            logger.info(msg)

        results = []
        site_info = REGIONAL_DOMAINS.get(self.site_code, REGIONAL_DOMAINS["MLM"])
        domain = site_info["domain"]
        currency = site_info["currency"]
        country = site_info["country"]

        slug = urllib.parse.quote(query.strip().replace(" ", "-"))
        raw_query = urllib.parse.quote(query.strip())
        base_search_url = f"https://{domain}/{slug}#D[A:{raw_query}]"

        limit_pages = max_pages if max_pages is not None else max(1, (max_items + 49) // 50)
        _log(f"🇲🇽 [Mercado Libre {country}] Initiating stealth search for '{query}' (Target: {limit_pages} page(s))...")

        context = self._get_context()
        page = context.pages[0] if context.pages else context.new_page()

        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)

        current_offset = 1
        page_num = 1
        seen_urls = set()

        try:
            while page_num <= limit_pages:
                if stop_event and stop_event.is_set():
                    _log("⏹ [Mercado Libre] Stop signal received.")
                    break
                if pause_event:
                    pause_event.wait()

                if page_num == 1:
                    target_url = base_search_url
                else:
                    target_url = f"https://{domain}/{slug}_Desde_{current_offset}#D[A:{raw_query}]"

                _log(f"🌐 [Mercado Libre] Loading page {page_num}/{limit_pages}...")
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(2500)
                except Exception as ex:
                    _log(f"⚠ Page load timeout on Mercado Libre: {ex}")

                if stop_event and stop_event.is_set():
                    break
                if pause_event:
                    pause_event.wait()

                # Ensure page has cleared security challenge, login redirects, and reached search results
                self._ensure_search_page_loaded(page, target_url, _log)

                if stop_event and stop_event.is_set():
                    break
                if pause_event:
                    pause_event.wait()

                # Extract listing cards via DOM evaluation
                page_items = page.evaluate("""
                    () => {
                        const items = [];
                        const cards = document.querySelectorAll(
                            '.ui-search-layout__item, .poly-card, li.ui-search-layout__item, div.poly-card__content, .ui-search-result, ol.ui-search-layout li'
                        );
                        
                        for (let c of cards) {
                            const titleEl = c.querySelector(
                                '.ui-search-item__title, .poly-component__title, h2, a.poly-component__title, .ui-search-item__group__element, h3.poly-component__title-wrapper'
                            );
                            const linkEl = c.querySelector(
                                'a.ui-search-link, a.poly-component__title, a[href*="articulo.mercadolibre"], a[href*="produto.mercadolivre"], a.ui-search-result__link, a[href*="mercadolibre.com"], a[href*="mercadolivre.com"], a[href*="/p/"]'
                            );
                            const priceEl = c.querySelector(
                                '.andes-money-amount__fraction, .ui-search-price__second-line .andes-money-amount__fraction, .poly-price__current .andes-money-amount__fraction'
                            );
                            const imgEl = c.querySelector('img');
                            const sellerEl = c.querySelector(
                                '.ui-search-official-store-label, .poly-component__seller, span.poly-component__seller, .ui-search-item__brand-discoverability'
                            );
                            const locEl = c.querySelector(
                                '.ui-search-item__location, .ui-search-item__group__element--location, .poly-component__location'
                            );
                            
                            if (titleEl && linkEl) {
                                const title = titleEl.innerText.trim();
                                const url = linkEl.href;
                                const price = priceEl ? priceEl.innerText.trim() : '';
                                const seller = sellerEl ? sellerEl.innerText.trim().replace(/^Por\\s+/i, '') : '';
                                const location = locEl ? locEl.innerText.trim() : '';
                                const img = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '';
                                
                                if (title && url) {
                                    items.push({
                                        title: title,
                                        url: url,
                                        price_raw: price,
                                        seller: seller,
                                        location: location,
                                        image_url: img
                                    });
                                }
                            }
                        }
                        return items;
                    }
                """)

                if not page_items:
                    _log(f"ℹ [Mercado Libre] No additional listing cards found on page {page_num}.")
                    break

                new_count = 0
                for raw_it in page_items:
                    if stop_event and stop_event.is_set():
                        break
                    if pause_event:
                        pause_event.wait()

                    item_url = raw_it.get("url", "").split("?")[0]
                    if not item_url or item_url in seen_urls:
                        continue

                    # Filter out off-target search cards / competitor ad bleed
                    card_title = raw_it.get("title", "")
                    if not self._is_relevant_search_card(card_title, raw_it.get("url", ""), query):
                        logger.debug(f"[Mercado Libre] Skipping off-target search card: '{card_title[:40]}' (query: '{query}')")
                        continue

                    seen_urls.add(item_url)

                    is_catalog = "/p/" in item_url
                    if is_catalog and expand_catalog:
                        _log(f"🔎 [Mercado Libre] Detected Catalog Buy Box: '{raw_it.get('title', '')[:35]}...' -> Expanding all competing sellers...")
                        try:
                            expanded = self.extract_catalog_sellers(
                                item_url,
                                title=raw_it.get("title", ""),
                                default_brand=query,
                                context=context,
                                close_browser=False,
                                stop_event=stop_event,
                                pause_event=pause_event
                            )
                            if expanded:
                                for s_it in expanded:
                                    s_it["keyword"] = query
                                    results.append(s_it)
                                    new_count += 1
                                _log(f"📦 [Mercado Libre Catalog] Extracted {len(expanded)} distinct seller(s) for '{raw_it.get('title', '')[:30]}'.")
                                continue
                        except Exception as cat_ex:
                            logger.debug(f"Catalog expansion failed, falling back to card: {cat_ex}")

                    # Standalone listing (or catalog fallback)
                    item_id = self._extract_item_id(item_url)
                    price_display, price_usd = self._convert_price_to_usd(raw_it.get("price_raw", ""), currency)
                    seller_name = self._clean_seller_name(raw_it.get("seller", ""), item_url)
                    item_loc = raw_it.get("location") or country

                    results.append({
                        "brand": "",
                        "product_type": "",
                        "title": raw_it.get("title", ""),
                        "item_id": item_id,
                        "price": price_display,
                        "price_usd": price_usd,
                        "seller": seller_name,
                        "location": item_loc,
                        "image_url": raw_it.get("image_url", ""),
                        "url": raw_it.get("url", ""),
                        "marketplace": "Mercado Libre",
                        "condition": "Catalog Buy Box" if is_catalog else ("New" if condition == "new" else ("Used" if condition == "used" else "Unspecified")),
                        "keyword": query
                    })
                    new_count += 1

                _log(f"📦 [Mercado Libre] Harvested {new_count} unique listings from page {page_num} ({len(results)} total across {page_num} page(s)).")

                if new_count == 0:
                    break

                page_num += 1
                current_offset += 50
                time.sleep(1.5)

        except Exception as e:
            _log(f"❌ Error during Mercado Libre scraping: {e}")
            logger.exception("Mercado Libre search failure")
        finally:
            self.close()

        _log(f"✅ [Mercado Libre] Search complete: Retrieved {len(results)} listings.")
        return results

    def parse_catalog_html(self, html_content: str, catalog_url: str = "", default_brand: str = "", site_code: str = None) -> List[Dict]:
        """
        Parse static or Playwright-retrieved catalog product HTML with BeautifulSoup.
        Extracts Buy Box winner and all competing catalog merchants from /p/ product pages.
        Supports Spanish (MLM, MLA, MCO, etc.) and Portuguese (MLB Brazil).
        """
        target_code = site_code or self.site_code
        site_info = REGIONAL_DOMAINS.get(target_code, REGIONAL_DOMAINS["MLM"])
        currency = site_info["currency"]
        country = site_info["country"]
        base_item_id = self._extract_item_id(catalog_url)

        soup = BeautifulSoup(html_content, "html.parser")
        results = []
        seen_sellers = set()

        # 1. Product Title
        title_el = soup.select_one("h1.ui-pdp-title, h1.ui-vpp-title, h1")
        title = title_el.get_text(strip=True) if title_el else (default_brand or "Mercado Libre Catalog Product")

        # 2. Main Thumbnail
        img_el = soup.select_one(".ui-pdp-image, .ui-pdp-gallery__figure img, img.ui-pdp-image, .ui-vpp-gallery__figure img, img[data-zoom]")
        img_url = ""
        if img_el:
            img_url = img_el.get("src") or img_el.get("data-src") or ""

        # 3. Buy Box Winner
        main_seller = ""
        for sel_css in (
            ".ui-pdp-seller__link-trigger",
            ".ui-seller-info a",
            "a.ui-pdp-seller__header__title",
            ".ui-pdp-seller__link",
            ".ui-seller-data-header__title-wrapper",
            "a.ui-pdp-official-store-info"
        ):
            if main_seller: break
            el = soup.select_one(sel_css)
            if el:
                txt = el.get_text(strip=True)
                if txt and not any(b in txt.lower() for b in ("mercado pontos", "devolución", "devolucao", "garantía", "garantia", "medios de pago", "ver mais", "ver más")):
                    main_seller = re.sub(r'^(?:Vendido por|Vendido e entregue por|Por)\s+', '', txt, flags=re.IGNORECASE).strip()

        if not main_seller:
            for n in soup.find_all(["p", "span", "div", "a"]):
                txt = n.get_text(strip=True)
                if txt.lower().startswith("vendido por") or txt.lower().startswith("vendido e entregue por"):
                    lines = [line.strip() for line in n.stripped_strings]
                    if len(lines) >= 2:
                        cand = re.sub(r'^(?:por)\s+', '', lines[1], flags=re.IGNORECASE).strip()
                        if cand and not any(b in cand.lower() for b in ("mercado livre", "mercado libre", "ir a la página", "seguir", "mercado pontos")):
                            main_seller = cand
                            break

        main_price_el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__fraction, .andes-money-amount__fraction")
        main_price = main_price_el.get_text(strip=True) if main_price_el else ""

        if main_seller:
            main_seller = self._clean_seller_name(main_seller, catalog_url)
        if main_seller and main_seller.lower() not in seen_sellers and main_seller != "Mercado Libre Seller":
            seen_sellers.add(main_seller.lower())
            p_disp, p_usd = self._convert_price_to_usd(main_price, currency)
            results.append({
                "brand": default_brand,
                "product_type": "Consumer Product",
                "title": f"{title} [Buy Box Winner: {main_seller}]",
                "item_id": base_item_id,
                "price": p_disp,
                "price_usd": p_usd,
                "seller": main_seller,
                "location": country,
                "image_url": img_url,
                "url": catalog_url,
                "marketplace": "Mercado Libre",
                "condition": "Catalog Buy Box",
                "keyword": default_brand
            })

        # 4. Competing Sellers in "Otras opciones de compra" / "Outras opções de compra"
        cards = soup.select(
            ".ui-pdp-other-sellers__card, .ui-pdp-other-sellers__item, div[data-testid='other-sellers-card'], li.ui-pdp-other-sellers__item"
        )
        if not cards:
            cards = soup.select(".ui-pdp-other-sellers a, a[href*='_CustId_'], a[href*='seller_id=']")

        for cont in cards:
            if cont.name == "a":
                s_link = cont
                parent_cont = cont.find_parent(["section", "div", "li"])
            else:
                s_link = cont.select_one("a")
                parent_cont = cont

            s_name = ""
            if s_link:
                s_name = s_link.get_text(strip=True)
            if not s_name and parent_cont:
                for tag in parent_cont.find_all(["span", "p", "div"]):
                    t_str = tag.get_text(strip=True)
                    if t_str.lower().startswith("vendido por") or t_str.lower().startswith("por "):
                        s_name = t_str
                        break

            href_val = s_link.get("href", "") if s_link else catalog_url
            s_name = self._clean_seller_name(s_name, href_val)

            p_el = parent_cont.select_one(".andes-money-amount__fraction") if parent_cont else None
            c_price = p_el.get_text(strip=True) if p_el else main_price
            
            c_item_id = base_item_id
            m_item = re.search(r'(?:item_id=|wid=)(ML[A-Z0-9_-]+)', href_val, re.IGNORECASE)
            if m_item:
                c_item_id = m_item.group(1).replace("-", "").upper()
            elif "_CustId_" in href_val:
                cust_m = re.search(r'_CustId_(\d+)', href_val)
                if cust_m:
                    c_item_id = f"{base_item_id}_{cust_m.group(1)}"
            elif "seller_id=" in href_val:
                s_m = re.search(r'seller_id=(\d+)', href_val)
                if s_m:
                    c_item_id = f"{base_item_id}_{s_m.group(1)}"
            else:
                safe_s = re.sub(r'[^a-zA-Z0-9]', '', s_name)
                c_item_id = f"{base_item_id}_{safe_s}" if safe_s else base_item_id

            if s_name and s_name.lower() not in seen_sellers and s_name != "Mercado Libre Seller":
                seen_sellers.add(s_name.lower())
                p_disp, p_usd = self._convert_price_to_usd(c_price, currency)
                direct_url, store_url = self._construct_competitor_listing_url(href_val, catalog_url, c_item_id)
                results.append({
                    "brand": default_brand,
                    "product_type": "Consumer Product",
                    "title": f"{title} [Catalog Competitor: {s_name}]",
                    "item_id": c_item_id,
                    "price": p_disp,
                    "price_usd": p_usd,
                    "seller": s_name,
                    "location": country,
                    "image_url": img_url,
                    "url": direct_url,
                    "store_url": store_url,
                    "marketplace": "Mercado Libre",
                    "condition": "Catalog Competitor",
                    "keyword": default_brand
                })

        # Fallback if no individual sellers were parsed
        if not results:
            p_disp, p_usd = self._convert_price_to_usd(main_price, currency)
            fallback_seller = self._clean_seller_name(main_seller, catalog_url)
            results.append({
                "brand": default_brand,
                "product_type": "Consumer Product",
                "title": title,
                "item_id": base_item_id,
                "price": p_disp,
                "price_usd": p_usd,
                "seller": fallback_seller or "Mercado Libre Seller",
                "location": country,
                "image_url": img_url,
                "url": catalog_url,
                "marketplace": "Mercado Libre",
                "condition": "Catalog Buy Box",
                "keyword": default_brand
            })

        return results

    def extract_catalog_sellers(self, catalog_url: str, title: str = "", default_brand: str = "", context=None, close_browser: bool = True, stop_event: threading.Event = None, pause_event: threading.Event = None) -> List[Dict]:
        """
        Deep Catalog Multi-Seller Expansion.
        Extracts Buy Box winner and all competing catalog merchants from /p/ product pages.
        Supports multi-page catalog options pagination across Spanish and Portuguese Mercado Libre domains.
        """
        if stop_event and stop_event.is_set():
            return []
        if pause_event:
            pause_event.wait()

        catalog_items = []
        seen_sellers = set()
        site_info = REGIONAL_DOMAINS.get(self.site_code, REGIONAL_DOMAINS["MLM"])
        currency = site_info["currency"]
        country = site_info["country"]
        parsed_netloc = urllib.parse.urlparse(catalog_url).netloc or site_info.get("domain", "www.mercadolibre.com.mx")
        base_item_id = self._extract_item_id(catalog_url)

        ctx = context or self._get_context()
        page = None
        try:
            page = ctx.new_page()
            page.goto(catalog_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)

            if stop_event and stop_event.is_set():
                return []
            if pause_event:
                pause_event.wait()

            # 1. Parse base product page for title, main image, and Buy Box winner
            init_html = page.content()
            soup = BeautifulSoup(init_html, "html.parser")
            
            title_el = soup.select_one("h1.ui-pdp-title, h1.ui-vpp-title, h1")
            parsed_title = title_el.get_text(strip=True) if title_el else (title or default_brand or "Mercado Libre Catalog Product")

            img_el = soup.select_one(".ui-pdp-image, .ui-pdp-gallery__figure img, img.ui-pdp-image, .ui-vpp-gallery__figure img, img[data-zoom]")
            img_url = ""
            if img_el:
                img_url = img_el.get("src") or img_el.get("data-src") or ""

            # Extract Buy Box winner
            main_seller = ""
            for sel_css in (
                ".ui-pdp-seller__link-trigger",
                ".ui-seller-info a",
                "a.ui-pdp-seller__header__title",
                ".ui-pdp-seller__link",
                ".ui-seller-data-header__title-wrapper",
                "a.ui-pdp-official-store-info"
            ):
                if main_seller: break
                el = soup.select_one(sel_css)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and not any(b in txt.lower() for b in ("mercado pontos", "devolución", "devolucao", "garantía", "garantia", "medios de pago", "ver mais", "ver más")):
                        main_seller = re.sub(r'^(?:Vendido por|Vendido e entregue por|Por)\s+', '', txt, flags=re.IGNORECASE).strip()

            main_price_el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__fraction, .andes-money-amount__fraction")
            main_price = main_price_el.get_text(strip=True) if main_price_el else ""

            if main_seller:
                main_seller = self._clean_seller_name(main_seller, catalog_url)
            if main_seller and main_seller != "Mercado Libre Seller":
                seen_sellers.add(main_seller.lower())
                p_disp, p_usd = self._convert_price_to_usd(main_price, currency)
                catalog_items.append({
                    "brand": default_brand,
                    "product_type": "Consumer Product",
                    "title": f"{parsed_title} [Buy Box Winner: {main_seller}]",
                    "item_id": base_item_id,
                    "price": p_disp,
                    "price_usd": p_usd,
                    "seller": main_seller,
                    "location": country,
                    "image_url": img_url,
                    "url": catalog_url,
                    "marketplace": "Mercado Libre",
                    "condition": "Catalog Buy Box",
                    "keyword": default_brand
                })

            # 2. Check if Options sub-page exists and open via natural click
            has_options_button = False
            try:
                opt_btn = page.query_selector(".ui-pdp-other-sellers__button, button.seo-ui-anchor__button, button:has-text('opç'), button:has-text('opc'), a[href*='opcoes-de-compra'], a[href*='opciones-de-compra'], a[href*='/s?']")
                if opt_btn:
                    opt_btn.click()
                    page.wait_for_timeout(2000)
                    has_options_button = True
            except Exception as opt_err:
                logger.debug(f"Options button click error: {opt_err}")

            # 3. Iterate through options pages via in-page pagination ONLY if options view was opened
            if has_options_button:
                opt_page_num = 1
                while opt_page_num <= 25:
                    if stop_event and stop_event.is_set():
                        break
                    if pause_event:
                        pause_event.wait()

                    try:
                        page_data = page.evaluate("""
                            () => {
                                const isError = (
                                    document.title.toLowerCase().includes('ocorreu um problema') ||
                                    document.title.toLowerCase().includes('hubo un problema') ||
                                    document.body.innerText.includes('Ocorreu um problema') ||
                                    document.body.innerText.includes('Hubo un problema') ||
                                    document.body.innerText.includes('Erro: VIP')
                                );
                                if (isError) {
                                    return { parsed: [], hasNext: false, isError: true };
                                }

                                const parsed = [];
                                const allLinks = Array.from(document.querySelectorAll('a'));
                                const sellerLinks = allLinks.filter(a => 
                                    a.href.includes('/pagina/') || 
                                    a.href.includes('/loja/') || 
                                    a.href.includes('_CustId_') || 
                                    a.href.includes('seller_id=') ||
                                    a.className.includes('seller')
                                );

                                for (let a of sellerLinks) {
                                    const sName = a.innerText.trim();
                                    if (!sName || sName.length > 60 || /mercado livre|mercado libre|ir para|seguidores|produtos/i.test(sName)) continue;

                                    let container = a.closest('li') || a.closest('.andes-card') || a.parentElement;
                                    while (container && !container.querySelector('.andes-money-amount__fraction') && container.parentElement && container.parentElement.tagName !== 'BODY') {
                                        container = container.parentElement;
                                    }

                                    let price = '';
                                    let cents = '';
                                    let condition = 'Catalog Competitor';

                                    if (container) {
                                        const priceFrac = container.querySelector('.andes-money-amount__fraction');
                                        if (priceFrac) price = priceFrac.innerText.trim();
                                        const priceCents = container.querySelector('.andes-money-amount__cents');
                                        if (priceCents) cents = priceCents.innerText.trim();
                                        
                                        const textContent = container.innerText;
                                        if (textContent.includes('Usado') || textContent.includes('Recondicionado')) {
                                            condition = 'Used';
                                        }
                                    }

                                    parsed.push({
                                        seller: sName,
                                        href: a.href,
                                        price: cents ? `${price}.${cents}` : price,
                                        condition: condition
                                    });
                                }

                                const hasNext = !!document.querySelector('.andes-pagination__button--next:not(.andes-pagination__button--disabled)');
                                return { parsed, hasNext, isError: false };
                            }
                        """)

                        if page_data.get("isError"):
                            break

                        parsed_sellers = page_data.get("parsed", [])
                        for s_info in parsed_sellers:
                            raw_s = s_info["seller"]
                            href_val = s_info["href"]
                            s_name = self._clean_seller_name(raw_s, href_val)
                            if not s_name or s_name.lower() in seen_sellers or s_name == "Mercado Libre Seller":
                                continue
                            seen_sellers.add(s_name.lower())
                            
                            s_price = s_info["price"] or main_price
                            p_disp, p_usd = self._convert_price_to_usd(s_price, currency)
                            
                            c_item_id = base_item_id
                            m_item = re.search(r'(?:item_id=|wid=)(ML[A-Z0-9_-]+)', href_val, re.IGNORECASE)
                            if m_item:
                                c_item_id = m_item.group(1).replace("-", "").upper()
                            elif "_CustId_" in href_val:
                                cust_m = re.search(r'_CustId_(\d+)', href_val)
                                if cust_m:
                                    c_item_id = f"{base_item_id}_{cust_m.group(1)}"
                            elif "seller_id=" in href_val:
                                s_m = re.search(r'seller_id=(\d+)', href_val)
                                if s_m:
                                    c_item_id = f"{base_item_id}_{s_m.group(1)}"
                            else:
                                safe_s = re.sub(r'[^a-zA-Z0-9]', '', s_name)
                                c_item_id = f"{base_item_id}_{safe_s}" if safe_s else base_item_id

                            direct_url, store_url = self._construct_competitor_listing_url(href_val, catalog_url, c_item_id)
                            catalog_items.append({
                                "brand": default_brand,
                                "product_type": "Consumer Product",
                                "title": f"{parsed_title} [Catalog Competitor: {s_name}]",
                                "item_id": c_item_id,
                                "price": p_disp,
                                "price_usd": p_usd,
                                "seller": s_name,
                                "location": country,
                                "image_url": img_url,
                                "url": direct_url,
                                "store_url": store_url,
                                "marketplace": "Mercado Libre",
                                "condition": s_info.get("condition", "Catalog Competitor"),
                                "keyword": default_brand
                            })

                        if not page_data.get("hasNext") or len(parsed_sellers) == 0:
                            break

                        next_btn = page.query_selector(".andes-pagination__button--next:not(.andes-pagination__button--disabled) a, .andes-pagination__button--next:not(.andes-pagination__button--disabled)")
                        if next_btn:
                            next_btn.click()
                            page.wait_for_timeout(2000)
                            if stop_event and stop_event.is_set():
                                break
                            if pause_event:
                                pause_event.wait()
                        else:
                            break

                        opt_page_num += 1

                    except Exception as opt_ex:
                        logger.debug(f"Options page navigation exception: {opt_ex}")
                        break

            # 4. Fallback: Parse inline other sellers from base page if options endpoint was empty or not available
            if len(catalog_items) <= 1:
                cards = soup.select(
                    ".ui-pdp-other-sellers__card, .ui-pdp-other-sellers__item, div[data-testid='other-sellers-card'], li.ui-pdp-other-sellers__item"
                )
                for cont in cards:
                    s_link = cont.select_one("a") if cont.name != "a" else cont
                    if s_link:
                        raw_s = s_link.get_text(strip=True)
                        href_val = s_link.get("href", "")
                        s_name = self._clean_seller_name(raw_s, href_val)
                        if s_name and s_name.lower() not in seen_sellers and s_name != "Mercado Libre Seller":
                            seen_sellers.add(s_name.lower())
                            p_el = cont.select_one(".andes-money-amount__fraction")
                            c_price = p_el.get_text(strip=True) if p_el else main_price
                            p_disp, p_usd = self._convert_price_to_usd(c_price, currency)
                            c_item_id = base_item_id
                            m_item = re.search(r'(?:item_id=|wid=)(ML[A-Z0-9_-]+)', href_val, re.IGNORECASE)
                            if m_item:
                                c_item_id = m_item.group(1).replace("-", "").upper()
                            elif "_CustId_" in href_val:
                                cust_m = re.search(r'_CustId_(\d+)', href_val)
                                if cust_m:
                                    c_item_id = f"{base_item_id}_{cust_m.group(1)}"
                            elif "seller_id=" in href_val:
                                s_m = re.search(r'seller_id=(\d+)', href_val)
                                if s_m:
                                    c_item_id = f"{base_item_id}_{s_m.group(1)}"
                            else:
                                safe_s = re.sub(r'[^a-zA-Z0-9]', '', s_name)
                                c_item_id = f"{base_item_id}_{safe_s}" if safe_s else base_item_id
                            direct_url, store_url = self._construct_competitor_listing_url(href_val, catalog_url, c_item_id)
                            catalog_items.append({
                                "brand": default_brand,
                                "product_type": "Consumer Product",
                                "title": f"{parsed_title} [Catalog Competitor: {s_name}]",
                                "item_id": c_item_id,
                                "price": p_disp,
                                "price_usd": p_usd,
                                "seller": s_name,
                                "location": country,
                                "image_url": img_url,
                                "url": direct_url,
                                "store_url": store_url,
                                "marketplace": "Mercado Libre",
                                "condition": "Catalog Competitor",
                                "keyword": default_brand
                            })

        except Exception as ex:
            logger.debug(f"Error expanding catalog item {catalog_url}: {ex}")
            if not catalog_items:
                price_disp, price_usd = self._convert_price_to_usd("", currency)
                catalog_items.append({
                    "brand": default_brand,
                    "product_type": "Consumer Product",
                    "title": title or "Mercado Libre Catalog Listing",
                    "item_id": self._extract_item_id(catalog_url),
                    "price": price_disp,
                    "price_usd": price_usd,
                    "seller": "Mercado Libre Seller",
                    "location": country,
                    "image_url": "",
                    "url": catalog_url,
                    "marketplace": "Mercado Libre",
                    "condition": "Catalog Listing",
                    "keyword": default_brand
                })
        finally:
            if page:
                try: page.close()
                except Exception: pass
            if close_browser and context is None:
                self.close()

        return catalog_items

    def enrich_seller_info(self, items: List[Dict], progress_callback=None, stop_event=None):
        """
        Enrich Mercado Libre listings in-place with verified seller handle, location, and reputation.
        """
        if not items:
            return

        total = len(items)
        context = self._get_context()

        try:
            for idx, it in enumerate(items, 1):
                if stop_event and stop_event.is_set():
                    break

                url = it.get("url", "")
                if not url:
                    continue

                try:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)

                    # Dynamic React Hydration polling: Wait until 'Vendido por' or seller triggers appear
                    for _ in range(8):
                        try:
                            has_seller = page.evaluate("() => document.body.innerText.includes('Vendido por') || !!document.querySelector('.ui-pdp-seller__link-trigger, .ui-seller-info a, a.ui-pdp-seller__header__title')")
                            if has_seller:
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(500)

                    info = page.evaluate(r"""
                        () => {
                            let sName = '';
                            let sLoc = '';
                            let sRep = '';

                            // 1. Check direct seller link triggers and official store links
                            const priorityNodes = document.querySelectorAll(
                                'a.ui-pdp-seller-summary__link, a.ui-pdp-seller__link-trigger, a.ui-pdp-seller__header__title, a.ui-pdp-official-store-info, a[href*="/pagina/"], a[href*="/loja/"], .ui-seller-data-header__title-wrapper a'
                            );
                            for (let n of priorityNodes) {
                                const txt = (n.innerText || '').trim();
                                const href = n.getAttribute('href') || '';
                                const isIgnored = (
                                    !txt ||
                                    /r\$|\$|cupom|cupón|desconto|frete|mercado pontos|devolução|devolucao|garantía|garantia|meios de pagamento|formas de pago|ver mais|ver más|ir para|ir a la|seguidores|produtos|saiba mais/i.test(txt) ||
                                    /^\s*r?\$?\s*\d+[,.]\d+/i.test(txt)
                                );
                                if (!isIgnored) {
                                    let clean = txt.replace(/^Vendido por\s+/i, '').replace(/^Por\s+/i, '').trim();
                                    if (clean.toLowerCase() === 'mercado livre' || clean.toLowerCase() === 'mercado libre' || href.includes('/loja/mercado-livre') || href.includes('/loja/mercado-libre')) {
                                        sName = 'Mercado Livre (Loja Oficial)';
                                        break;
                                    } else if (clean) {
                                        sName = clean;
                                        break;
                                    }
                                }
                            }

                            // 2. Extract handle from link href if text was generic
                            if (!sName) {
                                for (let n of priorityNodes) {
                                    const href = n.getAttribute('href') || '';
                                    const mPag = href.match(/\/pagina\/([^/?#]+)/i) || href.match(/\/loja\/([^/?#]+)/i);
                                    if (mPag) {
                                        let hName = mPag[1].replace(/[-_]/g, ' ').trim();
                                        if (hName.toLowerCase() === 'mercado livre' || hName.toLowerCase() === 'mercado libre') {
                                            sName = 'Mercado Livre (Loja Oficial)';
                                        } else {
                                            sName = hName.length <= 8 ? hName.toUpperCase() : hName.replace(/\b\w/g, l => l.toUpperCase());
                                        }
                                        break;
                                    }
                                    const mCust = href.match(/(?:_CustId_|seller_id=)(\d+)/i);
                                    if (mCust) {
                                        sName = `MeLi_Seller_${mCust[1]}`;
                                        break;
                                    }
                                }
                            }

                            // 3. Multiline "Vendido por" fallback
                            if (!sName) {
                                const allNodes = document.querySelectorAll('p, span, div, a');
                                for (let n of allNodes) {
                                    const text = n.innerText ? n.innerText.trim() : '';
                                    if (text.startsWith('Vendido por') || text.startsWith('Vendido e entregue por')) {
                                        const lines = text.split('\n').map(x => x.trim()).filter(x => x.length > 0);
                                        if (lines.length >= 2) {
                                            let candidate = lines[1].replace(/^por\s+/i, '').trim();
                                            if (candidate && !['mercado libre', 'mercado livre', 'ir a la página', 'ir para a página', 'seguir', 'mercado pontos', 'cupom', 'cupón', 'r$', 'meios de pagamento'].some(b => candidate.toLowerCase().includes(b)) && !/^\s*r?\$?\s*\d+[,.]\d+/i.test(candidate)) {
                                                sName = candidate;
                                                break;
                                            }
                                        }
                                    }
                                }
                            }

                            // 4. Storefront Header
                            if (!sName) {
                                const h1El = document.querySelector('h1.eshop-header__title, h1.store-header__title, .ui-pdp-seller__header__title');
                                if (h1El) {
                                    const h1Txt = h1El.innerText.trim();
                                    if (h1Txt && h1Txt.length < 60 && !h1Txt.toLowerCase().includes('mercado')) {
                                        sName = h1Txt;
                                    }
                                }
                            }

                            // 5. Seller Location
                            const locEl = document.querySelector('.ui-seller-info__location, .ui-pdp-seller__location, .poly-component__location');
                            if (locEl) sLoc = locEl.innerText.trim();

                            if (!sLoc) {
                                const allTextNodes = document.querySelectorAll('p, span, div');
                                for (let n of allTextNodes) {
                                    const txt = n.innerText ? n.innerText.trim() : '';
                                    if (txt.startsWith('Envío desde') || txt.startsWith('Envio desde')) {
                                        sLoc = txt.replace(/^Envío desde\\s+/i, '').replace(/^Envio desde\\s+/i, '').trim();
                                        break;
                                    }
                                    if (txt.includes('Ubicación del vendedor') || txt.includes('Ubicacion del vendedor')) {
                                        sLoc = txt.replace(/Ubicaci[oó]n del vendedor/i, '').trim();
                                        break;
                                    }
                                }
                            }

                            // 6. Seller Reputation (strictly single-line MercadoLíder tier or Official status)
                            const sellerBlocks = document.querySelectorAll('.ui-seller-data, .ui-seller-info, .ui-pdp-seller');
                            for (let b of sellerBlocks) {
                                const txt = b.innerText || '';
                                if (/mercadol[ií]der\s+platinum/i.test(txt)) {
                                    sRep = 'MercadoLíder Platinum';
                                    break;
                                } else if (/mercadol[ií]der\s+gold/i.test(txt)) {
                                    sRep = 'MercadoLíder Gold';
                                    break;
                                } else if (/mercadol[ií]der/i.test(txt)) {
                                    sRep = 'MercadoLíder';
                                    break;
                                } else if (/loja oficial|tienda oficial/i.test(txt)) {
                                    sRep = 'Loja Oficial';
                                    break;
                                }
                            }

                            return { seller: sName, location: sLoc, reputation: sRep };
                        }
                    """)
                    page.close()

                    clean_s = self._clean_seller_name(info.get("seller", "") or it.get("seller", ""), url)
                    if clean_s and clean_s != "Mercado Libre Seller":
                        it["seller"] = clean_s
                    if info.get("location"):
                        it["seller_origin"] = info["location"]
                        it["location"] = info["location"]

                    rep_str = (info.get("reputation") or "").strip()
                    if rep_str and any(k in rep_str.lower() for k in ("mercadolíder", "mercadolider", "loja oficial", "tienda oficial")):
                        it["threat_badge"] = f"MeLi: {rep_str}"
                    elif "threat_badge" in it and (str(it["threat_badge"]).startswith("MeLi:") or "\n" in str(it.get("threat_badge", ""))):
                        del it["threat_badge"]

                except Exception as e:
                    logger.debug(f"Error enriching Mercado Libre item {url}: {e}")
                    # Fallback URL cleaning
                    clean_s = self._clean_seller_name(it.get("seller", ""), url)
                    if clean_s and clean_s != "Mercado Libre Seller":
                        it["seller"] = clean_s

                if progress_callback:
                    progress_callback(idx, total, it)
        finally:
            self.close()

    def search_multi_region(self, query: str, site_codes: List[str] = None, max_items_per_region: int = 25, max_pages: int = None, condition: str = "all", stop_event: threading.Event = None, pause_event: threading.Event = None, log_callback=None) -> List[Dict]:
        """
        Execute multi-regional sweep across selected Latin American Mercado Libre domains.
        """
        if not site_codes:
            site_codes = ["MLM", "MLB", "MLA", "MCO"]

        all_results = []
        for code in site_codes:
            if stop_event and stop_event.is_set():
                break
            if pause_event:
                pause_event.wait()

            if code not in REGIONAL_DOMAINS:
                continue
            orig_site = self.site_code
            self.site_code = code
            reg_info = REGIONAL_DOMAINS[code]
            if log_callback:
                log_callback(f"🌎 [{reg_info['flag']} {reg_info['country']}] Initiating scan for '{query}'...")
            try:
                res = self.search(query, max_items=max_items_per_region, max_pages=max_pages, condition=condition, stop_event=stop_event, pause_event=pause_event, log_callback=log_callback)
                for r in res:
                    r["country"] = reg_info["country"]
                    r["marketplace"] = f"Mercado Libre ({reg_info['flag']} {reg_info['country']})"
                all_results.extend(res)
            except Exception as e:
                logger.debug(f"Error in multi-region scan for {code}: {e}")
            finally:
                self.site_code = orig_site

        return all_results

    def find_connected_network(self, item_id: str, item_url: str, target_img: str = "") -> List[Dict]:
        """
        On-Demand Visual Syndicate & Connected Seller Hunter for Mercado Libre.
        Scans product page carousels:
        - "Publicaciones del vendedor" (Seller's other storefront items)
        - "Quienes vieron este producto también compraron" (Competitor & related items)
        - "Otras opciones de compra" (Competing catalog merchants)
        """
        results = []
        if not item_url:
            return results

        site_info = REGIONAL_DOMAINS.get(self.site_code, REGIONAL_DOMAINS["MLM"])
        currency = site_info["currency"]
        country = site_info["country"]

        try:
            context = self._get_context()
            page = context.new_page()
            page.goto(item_url, wait_until="domcontentloaded", timeout=25000)

            # Fast active carousel harvesting with dynamic inactivity early exit
            carousels_data = []
            last_count = 0
            last_change_time = time.time()
            max_scan_duration = 5.0
            idle_threshold = 1.5
            start_scan = time.time()

            extract_script = """
                () => {
                    const discovered = [];
                    const seen = new Set();

                    const sections = document.querySelectorAll('section, div.ui-pdp-recommendations, div.ui-recommendations-carousel, div[class*="recommendations"], div[class*="carousel"], div.ui-pdp-other-sellers');
                    for (let sec of sections) {
                        const hEl = sec.querySelector('h2, h3, .ui-recommendations-title, .ui-pdp-container__title');
                        let secTitle = hEl ? hEl.innerText.trim() : '';
                        let secType = '👥 Related / Competitor Product';

                        if (secTitle.toLowerCase().includes('vendedor')) {
                            secType = '🏪 Seller\\'s Other Products';
                        } else if (secTitle.toLowerCase().includes('opciones de compra') || secTitle.toLowerCase().includes('otras opciones')) {
                            secType = '⚔ Buy Box Competitor';
                        } else if (secTitle.toLowerCase().includes('vieron') || secTitle.toLowerCase().includes('compraron')) {
                            secType = '👥 Customers Also Viewed';
                        }

                        const cards = sec.querySelectorAll('.ui-recommendations-card, .poly-card, .ui-search-result, a[href*="mercadolibre"], a[href*="mercadolivre"]');
                        for (let card of cards) {
                            const tEl = card.querySelector('.ui-recommendations-card__title, .poly-component__title, h2, h3, p');
                            const pEl = card.querySelector('.andes-money-amount__fraction');
                            const sEl = card.querySelector('.ui-recommendations-card__seller, .poly-component__seller, span.poly-component__seller');
                            const imgEl = card.querySelector('img');
                            const href = card.tagName === 'A' ? card.href : (card.querySelector('a') ? card.querySelector('a').href : '');

                            if (href && (tEl || pEl)) {
                                const cleanHref = href.split('#')[0];
                                if (!seen.has(cleanHref)) {
                                    seen.add(cleanHref);
                                    discovered.push({
                                        title: tEl ? tEl.innerText.trim() : 'Mercado Libre Listing',
                                        price_raw: pEl ? pEl.innerText.trim() : '',
                                        seller: sEl ? sEl.innerText.trim().replace(/^Por\\s+/i, '') : '',
                                        url: href,
                                        image_url: imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '',
                                        network_type: secType
                                    });
                                }
                            }
                        }
                    }
                    return discovered;
                }
            """

            for step in range(8):
                if time.time() - start_scan > max_scan_duration:
                    break
                try:
                    page.evaluate(f"window.scrollBy(0, {(step + 1) * 500});")
                except Exception:
                    pass
                time.sleep(0.35)

                try:
                    current_data = page.evaluate(extract_script)
                except Exception:
                    current_data = []

                if len(current_data) > last_count:
                    last_count = len(current_data)
                    last_change_time = time.time()
                    carousels_data = current_data
                elif last_count > 0 and (time.time() - last_change_time >= idle_threshold):
                    break

            if not carousels_data:
                try:
                    carousels_data = page.evaluate(extract_script)
                except Exception:
                    pass

            try:
                page.close()
            except Exception:
                pass
            self.close()

            for d in carousels_data:
                c_url = d.get("url", "")
                c_id = self._extract_item_id(c_url)
                p_disp, p_usd = self._convert_price_to_usd(d.get("price_raw", ""), currency)
                s_name = d.get("seller") or "Mercado Libre Merchant"

                results.append({
                    "brand": "",
                    "product_type": "",
                    "title": d.get("title", ""),
                    "item_id": c_id,
                    "price": p_disp,
                    "price_usd": p_usd,
                    "seller": s_name,
                    "location": country,
                    "seller_origin": country,
                    "image_url": d.get("image_url", ""),
                    "url": c_url,
                    "marketplace": f"Mercado Libre ({country})",
                    "condition": d.get("network_type", "Connected Listing"),
                    "similarity": "Carousel Asset",
                    "match_type": d.get("network_type", "Connected Listing"),
                })

        except Exception as e:
            logger.debug(f"Error finding connected network for Mercado Libre item {item_url}: {e}")
        finally:
            self.close()

        return results
