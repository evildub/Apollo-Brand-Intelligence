"""
apollo/scrapers/registry.py
───────────────────────────
Scraper Registry & Factory.
Centralizes the lifecycle, dependency injection (session vault, headless state),
and discovery of all marketplace scraper engines.
"""

from typing import Dict, Any, Optional


class ScraperRegistry:
    """
    Manages registration, lifecycle, and lookup for all Apollo marketplace scrapers.
    Allows dynamic marketplace expansion without modifying the core UI coordinator.
    """
    def __init__(self, headless: bool = True, session_vault=None):
        self.headless = headless
        self.session_vault = session_vault
        self._instances: Dict[str, Any] = {}

    def get(self, name: str) -> Optional[Any]:
        """Retrieve or lazily instantiate a scraper engine by marketplace name."""
        key = name.lower().strip()
        if key in self._instances:
            return self._instances[key]

        inst = self._create(key)
        if inst:
            self._instances[key] = inst
        return inst

    def set_headless(self, headless: bool):
        """Update headless mode across all instantiated scrapers."""
        self.headless = headless
        for scraper in self._instances.values():
            if hasattr(scraper, "headless"):
                scraper.headless = headless

    def _create(self, key: str) -> Optional[Any]:
        # Lazy imports prevent heavy browser imports at application startup
        if key in ("ebay", "scraper"):
            from apollo.scrapers.engines.scraper import EbayScraper
            return EbayScraper(headless=self.headless)

        if key in ("aliexpress", "aliexpress_scraper"):
            from apollo.scrapers.engines.aliexpress_scraper import AliExpressScraper
            return AliExpressScraper(headless=self.headless)

        if key in ("wish", "wish_scraper"):
            from apollo.scrapers.engines.wish_scraper import WishScraper
            return WishScraper(headless=self.headless)

        if key in ("temu", "temu_scraper"):
            from apollo.scrapers.engines.temu_scraper import TemuScraper
            return TemuScraper(headless=self.headless)

        if key in ("mercadolibre", "mercadolibre_scraper"):
            from apollo.scrapers.engines.mercadolibre_scraper import MercadoLibreScraper
            return MercadoLibreScraper(headless=self.headless)

        if key in ("redbubble", "redbubble_scraper"):
            from apollo.scrapers.engines.redbubble_scraper import RedbubbleScraper
            return RedbubbleScraper(headless=self.headless)

        if key in ("printerval", "printerval_scraper"):
            from apollo.scrapers.engines.printerval_scraper import PrintervalScraper
            return PrintervalScraper(headless=self.headless)

        if key in ("printblur", "printblur_scraper"):
            from apollo.scrapers.engines.printblur_scraper import PrintblurScraper
            return PrintblurScraper(headless=self.headless)

        if key in ("vinted", "vinted_scraper"):
            from apollo.scrapers.engines.vinted_scraper import VintedScraper
            return VintedScraper(headless=self.headless)

        if key in ("tiktok", "tiktok_scraper"):
            from apollo.scrapers.engines.tiktok_scraper import TikTokScraper
            return TikTokScraper(headless=self.headless)

        if key in ("manomano", "manomano_scraper"):
            from apollo.scrapers.engines.manomano_scraper import ManoManoScraper
            return ManoManoScraper(headless=self.headless)

        if key in ("scribd", "scribd_scraper"):
            from apollo.scrapers.engines.scribd_scraper import ScribdScraper
            return ScribdScraper(headless=self.headless)

        if key in ("teepublic", "teepublic_scraper"):
            from apollo.scrapers.engines.teepublic_scraper import TeePublicScraper
            return TeePublicScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("etsy", "etsy_scraper"):
            from apollo.scrapers.engines.etsy_scraper import EtsyScraper
            return EtsyScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("spreadshirt", "spreadshirt_scraper"):
            from apollo.scrapers.engines.spreadshirt_scraper import SpreadshirtScraper
            return SpreadshirtScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("zazzle", "zazzle_scraper"):
            from apollo.scrapers.engines.zazzle_scraper import ZazzleScraper
            return ZazzleScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("cafepress", "cafepress_scraper"):
            from apollo.scrapers.engines.cafepress_scraper import CafePressScraper
            return CafePressScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("threadless", "threadless_scraper"):
            from apollo.scrapers.engines.threadless_scraper import ThreadlessScraper
            return ThreadlessScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("teespring", "teespring_scraper"):
            from apollo.scrapers.engines.teespring_scraper import TeeSpringScraper
            return TeeSpringScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("fineartamerica", "fineartamerica_scraper"):
            from apollo.scrapers.engines.fineartamerica_scraper import FineArtAmericaScraper
            return FineArtAmericaScraper(headless=self.headless, session_vault=self.session_vault)

        if key in ("shopify", "shopify_scraper"):
            from apollo.scrapers.engines.shopify_scraper import ShopifyScraper
            return ShopifyScraper(headless=self.headless)

        return None
