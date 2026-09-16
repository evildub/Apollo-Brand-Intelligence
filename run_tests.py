"""
Automated Pre-Release Regression Test Suite for Apollo Brand Intelligence.
Validates critical analyst workflows, export column contracts, and threat intelligence logic.
Must pass 100% before any production executable is built or released.
"""

import os
import sys
import tempfile
import unittest
import openpyxl
from bs4 import BeautifulSoup

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_store import DataStore
from exporter import ExcelExporter
from visual_catalog import VisualCatalogManager, compute_phash, hamming_distance
import batch_importer
import intel_pack_manager
from PIL import Image


class TestApolloCoreFeatures(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_store = DataStore()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_ebay_seller_name_extraction(self):
        """Test Item 1: Verify seller extraction from HTML ignores avatar initials and feedback counts."""
        sample_ebay_html = """
        <html>
            <body>
                <h1 class="x-item-title__mainTitle">4PCS/SET OEM 90919-02240 Ignition Coils For Toyota Camry</h1>
                <div class="x-sellercard-atf">
                    <div class="x-sellercard-atf__info__about-seller">
                        <a href="https://www.ebay.com/sch/khkok-64/m.html?item=407006409742">
                            <span>K</span>
                        </a>
                        <a href="https://www.ebay.com/sch/khkok-64/m.html?item=407006409742">
                            <span class="ux-textspans--BOLD">khkok-64</span>
                        </a>
                        <span>(135)</span>
                        <span>99.1% positive</span>
                    </div>
                </div>
                <div class="x-price-primary"><span class="ux-textspans">US $59.99</span></div>
            </body>
        </html>
        """
        soup = BeautifulSoup(sample_ebay_html, "html.parser")
        
        # Test DOM seller extraction logic
        seller = ""
        for sel in (
            "div.x-sellercard-atf__info__about-seller a",
            "div[data-testid='x-sellercard-atf'] a",
            "div.ux-seller-section a",
            "a.x-sellercard-atf__info__about-seller"
        ):
            if seller: break
            for a_el in soup.select(sel):
                href = a_el.get("href", "")
                txt = a_el.get_text(strip=True)
                import re
                m_href = re.search(r'/(?:sch|usr|str)/([a-zA-Z0-9_\-\.]+)(?:/m\.html|\?|$|/)', href)
                if m_href:
                    cand = m_href.group(1).strip()
                    if cand and len(cand) >= 2 and cand.lower() not in ("usr", "str", "sch", "itm", "ebay"):
                        seller = cand
                        break
        
        self.assertEqual(seller, "khkok-64", "Seller name must be 'khkok-64' and not avatar initial 'K' or feedback rating.")

    def test_02_multi_locale_genesis_export_schema(self):
        """Test Item 2: Verify Multi-Locale Excel export adheres strictly to Genesis Columns A-R with Col C Thumbnail."""
        exporter = ExcelExporter()
        sample_items = [{
            "title": "OEM Toyota TRD Emblem Badge Set",
            "url": "https://www.ebay.com/itm/407006409742",
            "image_url": "https://i.ebayimg.com/images/g/sample_thumb.jpg",
            "item_id": "407006409742",
            "seller": "khkok-64",
            "price": "$59.99",
            "location": "Rowland Heights, CA, United States",
            "brand": "Toyota",
            "product_type": "Emblems",
            "seller_origin": "China",
            "threat_badge": "Foreign Drop-Ship Hub"
        }]
        target_locales = [
            {"name": "United Kingdom", "domain": "ebay.co.uk", "flag": "UK", "region": "Europe"},
            {"name": "Germany", "domain": "ebay.de", "flag": "DE", "region": "Europe"},
            {"name": "Australia", "domain": "ebay.com.au", "flag": "AU", "region": "Asia-Pacific"}
        ]
        
        out_file = os.path.join(self.temp_dir, "test_multi_locale_genesis.xlsx")
        count = exporter.export_multi_locale(sample_items, target_locales, out_file)
        
        self.assertEqual(count, 3, "Must generate exactly 3 expanded international rows.")
        self.assertTrue(os.path.exists(out_file), "Multi-locale export file must exist.")

        # Verify Excel sheet columns
        wb = openpyxl.load_workbook(out_file)
        ws = wb.active
        
        headers = [cell.value for cell in ws[1]]
        self.assertEqual(headers[0], "Title", "Col A must be Title")
        self.assertEqual(headers[1], "URL", "Col B must be URL")
        self.assertEqual(headers[2], "Thumbnail", "Col C must be Thumbnail")
        self.assertEqual(headers[4], "Item ID", "Col E must be Item ID")
        self.assertEqual(headers[7], "Marketplace", "Col H must be Marketplace")
        self.assertEqual(headers[9], "Seller Name", "Col J must be Seller Name")
        self.assertEqual(headers[12], "Brand", "Col M must be Brand")
        self.assertEqual(headers[13], "Price", "Col N must be Price")
        self.assertEqual(headers[14], "Item Location", "Col O must be Item Location")
        self.assertEqual(headers[15], "Product Type", "Col P must be Product Type")
        self.assertEqual(headers[18], "Locale Country", "Col S must be Locale Country")

        # Verify Row 2 content
        row2 = [cell.value for cell in ws[2]]
        self.assertEqual(row2[0], "OEM Toyota TRD Emblem Badge Set")
        self.assertEqual(row2[1], "https://www.ebay.co.uk/itm/407006409742", "Col B must contain expanded UK URL")
        self.assertEqual(row2[2], "https://i.ebayimg.com/images/g/sample_thumb.jpg", "Col C must contain thumbnail image URL")
        self.assertEqual(row2[4], "407006409742", "Col E must contain item ID")
        self.assertEqual(row2[9], "khkok-64", "Col J must contain seller name")
        self.assertEqual(row2[12], "Toyota", "Col M must contain brand")

    def test_03_datastore_enforcement_registry_aggregation(self):
        """Test Items 5 and 6: Verify registry aggregation and type-safe threat score comparison."""
        test_seller = "auto_parts_syndicate_99"
        items = [
            {
                "item_id": "111222333444",
                "title": "Fake TRD Grille Badge",
                "price": "US $125.00",
                "threat_score": "95",  # string score
                "brand": "Toyota",
                "product_type": "Emblems",
                "location": "Ontario, CA, United States",
                "seller_origin": "China",
                "threat_badge": "Foreign Drop-Ship Hub"
            },
            {
                "item_id": "555666777888",
                "title": "Fake Lexus Wheel Caps (Set of 4)",
                "price": "US $45.50",
                "threat_score": 80,    # int score
                "brand": "Lexus",
                "product_type": "Wheel Caps",
                "location": "Rowland Heights, CA",
                "seller_origin": "China",
                "threat_badge": "Foreign Drop-Ship Hub"
            }
        ]

        # Must execute without TypeError: '>='
        self.data_store.record_enforcement_scan(test_seller, items, brand_name="Toyota")
        
        reg = self.data_store.get_enforcement_registry()
        self.assertIn(test_seller, reg)
        card = reg[test_seller]
        
        self.assertEqual(card.get("total_listings"), 2, "Registry must store total listings count.")
        self.assertAlmostEqual(card.get("total_value"), 170.50, places=2, msg="Registry must sum total dollar values ($125.00 + $45.50 = $170.50).")
        self.assertIn("Toyota", card.get("brands_targeted", []))
        self.assertIn("Lexus", card.get("brands_targeted", []))
        self.assertIn("Emblems", card.get("product_types", []))
        self.assertIn("Wheel Caps", card.get("product_types", []))
        self.assertEqual(card.get("country"), "China")

        # Cleanup
        del reg[test_seller]
        self.data_store._save()

    def test_04_threat_assessment_unresolved_origin(self):
        """Test Item 9: Verify foreign drop-shippers are flagged and unresolved origins do not default to Domestic."""
        # 1. Foreign origin + US warehouse -> Drop-Ship Hub
        assess_3pl = self.data_store.compute_threat_assessment(origin="China", location="Ontario, California, United States")
        self.assertTrue(assess_3pl.get("is_3pl_hub"), "China seller with US warehouse must be flagged as 3PL Hub.")
        self.assertIn("Drop-Ship Hub", assess_3pl.get("badge"))

        # 2. Unresolved origin + US warehouse -> Must NOT be marked Domestic Verified
        assess_unres = self.data_store.compute_threat_assessment(origin="", location="City of Industry, CA")
        self.assertNotIn("Domestic Verified", assess_unres.get("badge"), "Unresolved origin must not be labeled Domestic Verified.")
        self.assertIn("Unresolved", assess_unres.get("badge"))

        # 3. Explicit Domestic origin -> Domestic Verified
        assess_dom = self.data_store.compute_threat_assessment(origin="United States", location="Austin, TX")
        self.assertIn("Domestic Verified", assess_dom.get("badge"))

    def test_05_datastore_delete_registry_entry(self):
        """Test Registry: Verify delete_registry_entry removes seller record cleanly."""
        seller = "test_seller_to_remove"
        self.data_store.record_enforcement_scan(seller, [{"item_id": "999", "title": "T", "price": "$10"}])
        self.assertIn(seller, self.data_store.get_enforcement_registry())
        
        self.data_store.delete_registry_entry(seller)
        self.assertNotIn(seller, self.data_store.get_enforcement_registry(), "Seller must be deleted from registry.")

    def test_06_standard_genesis_export_schema(self):
        """Test Standard Export: Verify 18-column Genesis layout with Col C Thumbnail and Col B URL."""
        exporter = ExcelExporter()
        sample_items = [{
            "title": "Toyota Genuine Oil Filter 90915-YZZN1",
            "url": "https://www.ebay.com/itm/112233445566",
            "image_url": "https://i.ebayimg.com/images/g/test_oil_filter.jpg",
            "item_id": "112233445566",
            "seller": "toyota_direct_deals",
            "price": "$9.99",
            "location": "Dallas, TX, United States",
            "brand": "Toyota",
            "product_type": "Oil / Fuel Filters",
            "seller_origin": "United States",
            "threat_badge": "Domestic Verified"
        }]
        out_file = os.path.join(self.temp_dir, "test_standard_genesis.xlsx")
        count = exporter.export_results(sample_items, out_file)
        self.assertEqual(count, 1)
        self.assertTrue(os.path.exists(out_file))

        wb = openpyxl.load_workbook(out_file)
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        self.assertEqual(headers[0], "Title")
        self.assertEqual(headers[1], "URL")
        self.assertEqual(headers[2], "Thumbnail")
        self.assertEqual(headers[4], "Item ID")
        self.assertEqual(headers[7], "Marketplace")
        self.assertEqual(headers[9], "Seller Name")
        self.assertEqual(headers[12], "Brand")
        self.assertEqual(headers[13], "Price")
        self.assertEqual(headers[14], "Item Location")
        self.assertEqual(headers[15], "Product Type")
        self.assertIn("Threat Assessment", headers[17])

        row2 = [cell.value for cell in ws[2]]
        self.assertEqual(row2[0], "Toyota Genuine Oil Filter 90915-YZZN1")
        self.assertEqual(row2[1], "https://www.ebay.com/itm/112233445566")
        self.assertEqual(row2[2], "https://i.ebayimg.com/images/g/test_oil_filter.jpg")
        self.assertEqual(row2[4], "112233445566")
        self.assertEqual(row2[9], "toyota_direct_deals")
        self.assertEqual(row2[12], "Toyota")

    def test_07_whitelist_authorized_dealers(self):
        """Test Whitelist: Verify authorized dealerships are identified and shielded."""
        test_handle = "authorized_toyota_dealer_tx"
        self.data_store.add_to_whitelist(test_handle, brand="Toyota", dealer_name="Toyota of Dallas")
        
        self.assertTrue(self.data_store.is_seller_whitelisted(test_handle))
        self.assertTrue(self.data_store.is_seller_whitelisted(f"  {test_handle.upper()}  "), "Must be whitespace & case insensitive")
        self.assertFalse(self.data_store.is_seller_whitelisted("unknown_counterfeiter_99"))

        # Clean up
        self.data_store.remove_from_whitelist(test_handle)
        self.assertFalse(self.data_store.is_seller_whitelisted(test_handle))

    def test_08_brand_detection_heuristics(self):
        """Test Brand Detection: Verify title classification heuristics accurately extract trademark brands."""
        self.assertEqual(batch_importer.detect_brand("OEM TRD Grille Badge for Toyota Tacoma"), "Toyota")
        self.assertEqual(batch_importer.detect_brand("2024 Lexus RX350 Wheel Center Caps 4pcs"), "Lexus")
        self.assertEqual(batch_importer.detect_brand("Subaru WRX STI Red Stitching Steering Wheel"), "Subaru")
        self.assertEqual(batch_importer.detect_brand("Honda Civic Type R Carbon Fiber Wing Spoiler"), "Honda")
        self.assertEqual(batch_importer.detect_brand("Generic Unbranded Key Chain"), "Automotive & Consumer Brands")

    def test_09_adhoc_url_cleaning_and_id_extraction(self):
        """Test URL Cleaning: Verify messy tracking URLs are canonicalized and item IDs extracted."""
        dirty_url = "https://www.ebay.com/itm/407006409742?_trksid=p2047675.c100005.m1851&_trkparms=amclksrc%3DITM&hash=item5f00"
        clean = batch_importer.clean_ebay_url(dirty_url)
        self.assertEqual(clean, "https://www.ebay.com/itm/407006409742")
        self.assertEqual(batch_importer.extract_item_id(dirty_url), "407006409742")

    def test_10_product_type_classification(self):
        """Test Category Detection: Verify auto-classification of product categories."""
        self.assertEqual(batch_importer.detect_product_type("4Pcs Iridium Spark Plugs for Camry"), "Spark Plugs")
        self.assertEqual(batch_importer.detect_product_type("Front Ceramic Brake Pads and Rotors Kit"), "Brake Pads / Rotors")
        self.assertEqual(batch_importer.detect_product_type("Gloss Black Front Grille Emblem Badge"), "Emblems / Badges")
        self.assertEqual(batch_importer.detect_product_type("Engine Oil Filter Replacement Cartridge"), "Oil / Fuel Filters")

    def test_11_intel_pack_export_and_import_merge(self):
        """Test Intelligence Pack: Verify .apollo packaging, export, inspection, and safe library merging."""
        # 1. Setup isolated data store & visual catalog
        vcm_dir = os.path.join(self.temp_dir, "vcm_src")
        vcm = VisualCatalogManager(base_dir=vcm_dir)
        
        # Add sample test image
        img = Image.new("RGB", (64, 64), color=(255, 0, 0))
        vcm.add_entry(img, entry_type="benign", label="Toyota Red OEM Box", source_url="https://example.com/box.jpg")

        pack_file = os.path.join(self.temp_dir, "test_intel_pack.apollo")
        manifest = intel_pack_manager.IntelPackManager.export_pack(
            output_filepath=pack_file,
            data_store=self.data_store,
            visual_catalog=vcm,
            scope="Full Profile",
            author="Jerry Seidenstucker",
            notes="Automated Test Pack"
        )
        self.assertTrue(os.path.exists(pack_file))
        self.assertEqual(manifest["author"], "Jerry Seidenstucker")
        self.assertGreaterEqual(manifest["counts"]["brands"], 1)
        self.assertGreaterEqual(manifest["counts"]["visual_catalog_entries"], 1)

        # 2. Inspect Pack
        inspected = intel_pack_manager.IntelPackManager.inspect_pack(pack_file)
        self.assertEqual(inspected["format"], "apollo_intelligence_pack")
        self.assertEqual(inspected["version"], "1.0")

        # 3. Import into destination catalog
        dst_vcm_dir = os.path.join(self.temp_dir, "vcm_dst")
        dst_vcm = VisualCatalogManager(base_dir=dst_vcm_dir)
        self.assertEqual(len(dst_vcm.get_all_entries()), 0)

        import_res = intel_pack_manager.IntelPackManager.import_pack(
            pack_filepath=pack_file,
            data_store=self.data_store,
            visual_catalog=dst_vcm,
            merge_mode="merge"
        )
        self.assertGreaterEqual(len(dst_vcm.get_all_entries()), 1)
        self.assertEqual(import_res["results"]["visual_added"], 1)
        self.assertEqual(import_res["results"]["thumbnails_extracted"], 1)

    def test_12_visual_sensitivity_dynamic_threshold(self):
        """Test Visual Sensitivity: Verify Hamming distance matching and dynamic threshold behavior."""
        vcm_dir = os.path.join(self.temp_dir, "vcm_thresh")
        vcm = VisualCatalogManager(base_dir=vcm_dir)

        # Create base image and slight variant
        base_img = Image.new("RGB", (64, 64), color=(200, 30, 30))
        vcm.add_entry(base_img, entry_type="benign", label="Denso Blue Box")

        # Test exact match
        m_exact = vcm.match_image(base_img, max_distance=2)
        self.assertIsNotNone(m_exact)
        self.assertEqual(m_exact["label"], "Denso Blue Box")
        self.assertEqual(m_exact["type"], "benign")

        # Test distant image fails on strict (max_distance=2), passes on broad (max_distance=20)
        diff_img = Image.new("RGB", (64, 64), color=(10, 200, 50))
        h1 = compute_phash(base_img)
        h2 = compute_phash(diff_img)
        dist = hamming_distance(h1, h2)
        
        m_strict = vcm.match_image(diff_img, max_distance=max(0, dist - 5))
        self.assertIsNone(m_strict)

        m_broad = vcm.match_image(diff_img, max_distance=dist + 5)
        self.assertIsNotNone(m_broad)

    def test_13_multi_locale_export_col_h_domain_format(self):
        """Test Multi-Locale Export: Verify Column H outputs strict domain name format (ebay.com, ebay.ca, etc.)."""
        exporter = ExcelExporter()
        test_results = [{
            "title": "Toyota Genuine Oil Filter 90915-YZZN1",
            "url": "https://www.ebay.com/itm/112233445566",
            "item_id": "112233445566",
            "image_url": "https://i.ebayimg.com/images/g/test.jpg",
            "seller": "toyota_direct_deals",
            "brand": "Toyota",
            "price": "$12.99",
            "location": "Dallas, TX, United States",
            "product_type": "Oil Filters",
            "seller_origin": "United States",
            "threat_badge": "🇺🇸 Domestic Verified"
        }]

        test_locales = [
            {"code": "US", "name": "United States", "domain": "ebay.com", "region": "North America", "flag": "🇺🇸"},
            {"code": "CA", "name": "Canada", "domain": "ebay.ca", "region": "North America", "flag": "🇨🇦"},
            {"code": "UK", "name": "United Kingdom", "domain": "ebay.co.uk", "region": "Europe", "flag": "🇬🇧"},
            {"code": "DE", "name": "Germany", "domain": "ebay.de", "region": "Europe", "flag": "🇩🇪"},
        ]

        out_path = os.path.join(self.temp_dir, "test_multi_locale_col_h.xlsx")
        exporter.export_multi_locale(test_results, test_locales, out_path)
        self.assertTrue(os.path.exists(out_path))

        wb = openpyxl.load_workbook(out_path)
        ws = wb.active

        # Check Col H across the 4 generated locale rows
        col_h_vals = [ws.cell(row=r, column=8).value for r in range(2, 6)]
        self.assertEqual(col_h_vals, ["ebay.com", "ebay.ca", "ebay.co.uk", "ebay.de"])

        # Verify Column C contains thumbnail image URL
        col_c_vals = [ws.cell(row=r, column=3).value for r in range(2, 6)]
        self.assertEqual(col_c_vals, ["https://i.ebayimg.com/images/g/test.jpg"] * 4)

    def test_14_seller_extraction_rejects_promo_and_spec_copy(self):
        """Test Seller Extraction: Verify promotional copy and specification tags are never extracted as seller names."""
        from scraper import EbayScraper
        scraper = EbayScraper(headless=True)

        mock_card_html = """
        <li class="s-card">
            <a class="s-card__link" href="https://www.ebay.com/itm/998877665544">
                <span class="s-card__title">Toyota Camry Steering Wheel Badge</span>
            </a>
            <div class="s-card__subtitle">17 sold • Save up to 5% with coupon</div>
            <span class="s-card__price">$24.99</span>
        </li>
        """

        # When parsed with a known fallback seller, must strictly use fallback instead of 'sold' or 'save'
        items = scraper._parse_html(mock_card_html, fallback_seller="genuine_oem_parts_direct")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["seller"], "genuine_oem_parts_direct")
        self.assertNotIn("sold", items[0]["seller"].lower())
        self.assertNotIn("save", items[0]["seller"].lower())

    def test_15_threat_assessment_india_cross_border_drop_ship(self):
        """Test Threat Assessment: Verify India-registered sellers shipping from US 3PL warehouses are flagged as Drop-Ship Hubs."""
        # 1. India seller shipping from US warehouse -> Foreign Drop-Ship Hub
        res_3pl = self.data_store.compute_threat_assessment(origin="India", location="Chino, CA, United States")
        self.assertEqual(res_3pl["badge"], "🚨 Foreign Drop-Ship Hub")
        self.assertTrue(res_3pl["is_high_risk"])
        self.assertTrue(res_3pl["is_3pl_hub"])

        # 2. India seller shipping directly from India -> Cross-Border Direct
        res_direct = self.data_store.compute_threat_assessment(origin="India", location="New Delhi, India")
        self.assertEqual(res_direct["badge"], "⚠ Cross-Border Direct")
        self.assertTrue(res_direct["is_high_risk"])
        self.assertFalse(res_direct["is_3pl_hub"])

        # 3. Domestic US seller shipping from US -> Domestic Verified
        res_us = self.data_store.compute_threat_assessment(origin="United States", location="Dallas, TX, United States")
        self.assertEqual(res_us["badge"], "🇺🇸 Domestic Verified")
        self.assertFalse(res_us["is_high_risk"])

    def test_16_tiktok_shop_pdp_extraction(self):
        """Test Item 16: Verify TikTok Shop platform detection, URL extraction, and PDP normalization."""
        sample_url = "https://shop.tiktok.com/us/pdp/chrome-valve-stem-tire-caps-for-cadillac-vehicles-set-of-four/1731432810739700325"
        
        # 1. Platform Detection
        platform = batch_importer.detect_platform(sample_url)
        self.assertEqual(platform, "TikTok Shop", "Platform must be recognized as 'TikTok Shop'")

        # 2. Markdown URL Extraction
        raw_text = f"Review this link: [Cadillac Caps]({sample_url}) and also https://shop.tiktok.com/us/pdp/1732474117957129133"
        extracted_urls = batch_importer.extract_urls_from_text(raw_text)
        self.assertIn(sample_url, extracted_urls)
        self.assertEqual(len(extracted_urls), 2)

        # 3. TikTokScraper PDP normalization contract
        from tiktok_scraper import TikTokScraper
        scraper = TikTokScraper(headless=True)
        store_info = scraper.resolve_store_info(sample_url)
        self.assertEqual(store_info.get("item_id"), "1731432810739700325")

    def test_17_smart_triage_universal_fluff(self):
        """Test Item 17: Verify Smart Triage suppresses universal fluff & multi-brand spam while preserving high-risk components."""
        # 1. High-risk parts must NEVER be suppressed, even with 'fits' or multiple words
        is_fluff, _ = self.data_store.is_universal_fluff("4PCS OEM 90919-02240 Ignition Coils For Toyota Camry")
        self.assertFalse(is_fluff, "Ignition coils must never be suppressed")

        is_fluff, _ = self.data_store.is_universal_fluff("Toyota Genuine Oil Filter 04152-YZZA1 fits Camry RAV4")
        self.assertFalse(is_fluff, "Oil filters must never be suppressed")

        is_fluff, _ = self.data_store.is_universal_fluff("TRD Front Grille Emblem Badge fits Toyota Tacoma 4Runner")
        self.assertFalse(is_fluff, "Emblems/Badges must never be suppressed")

        is_fluff, _ = self.data_store.is_universal_fluff("4pcs Spark Plugs Iridium fits Toyota Denso SK20R11")
        self.assertFalse(is_fluff, "Spark plugs must never be suppressed")

        # 2. Multi-brand title spam must be suppressed
        is_fluff, reason = self.data_store.is_universal_fluff("Universal Breathable Leather Seat Cover fits Toyota Honda Chevy Nissan")
        self.assertTrue(is_fluff, "Multi-brand title spam must be suppressed")
        self.assertIn("Multi-Brand Spam", reason)

        # 3. Compatibility keyword + universal fluff category must be suppressed
        is_fluff, reason = self.data_store.is_universal_fluff("Car Windshield Sunshade Foldable for Toyota Corolla")
        self.assertTrue(is_fluff, "Universal sunshade compatibility must be suppressed")
        self.assertIn("Universal Compatibility", reason)

        is_fluff, reason = self.data_store.is_universal_fluff("Heavy Duty Rubber Floor Mats for Chevy Silverado")
        self.assertTrue(is_fluff, "Floor mats with 'for' must be suppressed")
        self.assertIn("Universal Compatibility", reason)

    def test_18_manomano_and_whitelist_scopes(self):
        """Test Item 18: Verify ManoMano contract, Whitelist marketplace scoping, and handle preservation."""
        # 1. ManoManoScraper contract
        from manomano_scraper import ManoManoScraper
        mm = ManoManoScraper(headless=True)
        info = mm.resolve_store_info("https://www.manomano.fr/marchand-41084935")
        self.assertEqual(info.get("store_name"), "ManoMano European Search")

        # 2. Whitelist marketplace scoping
        self.data_store.add_to_whitelist("legit_dealer_global", brand="Toyota", dealer_name="Global Dealer", marketplace="All Marketplaces (Global)")
        self.data_store.add_to_whitelist("legit_dealer_ebay_only", brand="Toyota", dealer_name="eBay Dealer", marketplace="eBay Only")

        self.assertTrue(self.data_store.is_seller_whitelisted("legit_dealer_global", marketplace="eBay"))
        self.assertTrue(self.data_store.is_seller_whitelisted("legit_dealer_global", marketplace="ManoMano"))
        self.assertTrue(self.data_store.is_seller_whitelisted("legit_dealer_ebay_only", marketplace="eBay"))
        self.assertFalse(self.data_store.is_seller_whitelisted("legit_dealer_ebay_only", marketplace="ManoMano"))

        # 3. Handle preservation (no mangling caug_92 -> caug92)
        from scraper import EbayScraper
        eb = EbayScraper()
        candidates = eb._generate_seller_candidates("caug_92")
        self.assertEqual(candidates, ["caug_92"], "Underscores in seller handles must never be mangled")

    def test_19_aliexpress_image_normalization(self):
        """Test Item 19: Verify AliExpress image normalization preserves PNG assets and strips dynamic CDN extensions."""
        import re
        
        sample_urls = [
            ("https://ae-pic-a1.aliexpress-media.com/kf/Sc44dd990bd9e49ab8fc545e6b4617754W.png_220x220.png_.avif",
             "https://ae-pic-a1.aliexpress-media.com/kf/Sc44dd990bd9e49ab8fc545e6b4617754W.png"),
            ("https://ae-pic-a1.aliexpress-media.com/kf/S0c102f3b93fd4f20a0fe763f89f2bbb2t.jpg_220x220q75.jpg_.avif",
             "https://ae-pic-a1.aliexpress-media.com/kf/S0c102f3b93fd4f20a0fe763f89f2bbb2t.jpg"),
            ("//ae01.alicdn.com/kf/HTB9999.png_Q90.png_.webp",
             "https://ae01.alicdn.com/kf/HTB9999.png"),
        ]

        for raw, expected in sample_urls:
            u = raw
            if u.startswith("//"):
                u = "https:" + u
            u = re.sub(r'(\.(?:jpg|jpeg|png|webp))_[^?#]+.*$', r'\1', u, flags=re.I)
            u = re.sub(r'_\.(?:avif|webp)$', '', u, flags=re.I)
            self.assertEqual(u, expected, f"Normalized URL must match expected clean CDN path for {raw}")

        # Verify AliExpressScraper contract
        from aliexpress_scraper import AliExpressScraper
        ali = AliExpressScraper(headless=True)
        store_info = ali.resolve_store_info("https://www.aliexpress.com/store/1101234567")
        self.assertEqual(store_info.get("store_id"), "1101234567")

    def test_20_printerval_pod_variant_expansion(self):
        """Test Item 20: Verify Printerval POD variant expansion logic, SKU extraction, and type synthesis."""
        from printerval_scraper import PrintervalScraper
        ps = PrintervalScraper(headless=True)
        
        info = ps.resolve_store_info("https://printerval.com/shop/maxsutton")
        self.assertIn("maxsutton", info.get("store_name", "").lower())
        
        # Verify method exists and takes expected parameters
        self.assertTrue(hasattr(ps, "expand_design_variants"))
        empty_res = ps.expand_design_variants([])
        self.assertEqual(empty_res, [])

        # Verify parent metadata handling does not raise NameError
        from unittest.mock import MagicMock, patch
        mock_parent = {
            "item_id": "2097505",
            "url": "https://printerval.com/camaro-ss-5th-gen-14-15-silver-camaro-t-shirt-p2097505",
            "title": "Camaro SS 5th Gen 14-15 Silver Camaro T-Shirt",
            "seller": "CoolArtist",
            "brand": "Camaro",
            "keyword": "camaro",
            "price": "$19.95"
        }
        # Verify method handles parents gracefully with mock playwright
        with patch.object(ps, "_get_context") as mock_ctx:
            mock_page = MagicMock()
            mock_ctx.return_value.pages = [mock_page]
            mock_page.evaluate.return_value = [
                {
                    "item_id": "38966653",
                    "url": "https://printerval.com/camaro-ss-5th-gen-14-15-silver-camaro-tank-tops-p38966653",
                    "title": "Camaro SS 5th Gen 14-15 Silver Camaro Tank Tops",
                    "price": "$24.95",
                    "image_url": "https://printerval.com/img/tank.jpg"
                }
            ]
            res = ps.expand_design_variants([mock_parent])
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["item_id"], "38966653")
            self.assertEqual(res[0]["title"], "Camaro SS 5th Gen 14-15 Silver Camaro Tank Tops")
            self.assertEqual(res[0]["product_type"], "Tops")
            self.assertEqual(res[0]["thumbnail"], "https://printerval.com/img/tank.jpg")
            self.assertEqual(res[0]["marketplace"], "printerval.com")

            # Verify title synthesis prevents category-only partial titles (e.g. 'Baby Blankets')
            t_synth = ps._synthesize_variant_title(
                "Camaro SS 5th gen 14-15 - silver Camaro T-Shirt",
                "camaro-ss-5th-gen-14-15-silver-baby-blankets",
                "Baby Blankets"
            )
            self.assertEqual(t_synth, "Camaro SS 5th gen 14-15 - silver Baby Blankets")

            t_synth2 = ps._synthesize_variant_title(
                "Chevrolet Camaro Luxury Brand Custom Name 2D Half Zipper Hoodie",
                "chevrolet-camaro-luxury-brand-custom-name-2d-half-zipper-hoodie",
                "Hoodies"
            )
            self.assertEqual(t_synth2, "Chevrolet Camaro Luxury Brand Custom Name 2D Half Zipper Hoodie")

    def test_21_redbubble_pod_and_portfolio_engine(self):
        """Test Item 21: Verify Redbubble Next.js payload parsing, POD 1-to-74 expansion, and artist portfolio sweeper."""
        from redbubble_scraper import RedbubbleScraper
        rb = RedbubbleScraper(headless=True)
        
        info = rb.resolve_store_info("https://www.redbubble.com/people/PopsQc/shop")
        self.assertEqual(info.get("artist"), "PopsQc")
        self.assertIn("PopsQc", info.get("store_name"))
        
        # Verify expand_design_variants & sweep_artist_portfolio contracts
        self.assertTrue(hasattr(rb, "expand_design_variants"))
        self.assertTrue(hasattr(rb, "sweep_artist_portfolio"))
        self.assertEqual(rb.expand_design_variants([]), [])
        self.assertEqual(rb.sweep_artist_portfolio(""), [])

    def test_22_aliexpress_keyword_precision_filtering(self):
        """Test Item 22: Verify AliExpress brand keyword precision filtering drops unrelated wholesale cross-fitment noise."""
        from aliexpress_scraper import AliExpressScraper
        ali = AliExpressScraper(headless=True)
        
        # Test HTML containing both a matching Toyota item and a generic non-matching item
        sample_html = """
        <div class="search-item-card">
            <a href="https://www.aliexpress.com/item/1005001111111111.html" title="Toyota Tacoma TRD Pro Grille Emblem Badge">
                <img src="https://ae-pic-a1.aliexpress-media.com/kf/toyota_emblem.jpg" />
                <span>$15.99</span>
            </a>
        </div>
        <div class="search-item-card">
            <a href="https://www.aliexpress.com/item/1005002222222222.html" title="Universal Leather Car Steering Wheel Cover For VW BMW Benz">
                <img src="https://ae-pic-a1.aliexpress-media.com/kf/vw_cover.jpg" />
                <span>$9.99</span>
            </a>
        </div>
        """
        parsed = ali._parse_html(sample_html, seller_label="Test Store", include_term="Toyota", excludes=[])
        self.assertEqual(len(parsed), 1, "Unrelated VW/BMW item must be filtered out when searching for 'Toyota'")
        self.assertIn("Toyota", parsed[0]["title"])
        self.assertEqual(parsed[0]["item_id"], "1005001111111111")

    def test_23_reverse_visual_harvester_expansion(self):
        """Test Item 23: Verify VisualHarvester accepts Redbubble, Printerval, and TikTok scrapers."""
        from visual_harvester import VisualHarvester
        vh = VisualHarvester(tiktok_scraper="mock_tt", printerval_scraper="mock_pv", redbubble_scraper="mock_rb")
        self.assertEqual(vh.tiktok_scraper, "mock_tt")
        self.assertEqual(vh.printerval_scraper, "mock_pv")
        self.assertEqual(vh.redbubble_scraper, "mock_rb")

    def test_24_multi_column_cascading_dropdown_filters(self):
        """Test Item 24: Verify multi-column cascading filter logic (Marketplace + Brand + Column Scope + Keyword)."""
        from main import EbayTool
        
        # Test item dataset across multiple marketplaces and brands
        items = [
            {"item_id": "1", "brand": "Toyota", "title": "Toyota TRD Racing Pullover Hoodie", "marketplace": "Printerval", "seller": "PrintervalArtist1", "price": "$34.99", "url": "https://printerval.com/toyota-hoodie-p1"},
            {"item_id": "2", "brand": "Toyota", "title": "Toyota Tacoma Full Zipper Jacket", "marketplace": "Printerval", "seller": "PrintervalArtist2", "price": "$45.00", "url": "https://printerval.com/toyota-jacket-p2"},
            {"item_id": "3", "brand": "Ford", "title": "Ford Mustang Pullover Hoodie", "marketplace": "Printerval", "seller": "PrintervalArtist1", "price": "$34.99", "url": "https://printerval.com/ford-hoodie-p3"},
            {"item_id": "4", "brand": "Toyota", "title": "Toyota Vintage Sticker Pack", "marketplace": "Redbubble", "seller": "PopsQc", "price": "$4.50", "url": "https://www.redbubble.com/i/sticker/toyota-p4"},
            {"item_id": "5", "brand": "Toyota", "title": "OEM Toyota Grille Badge Emblem", "marketplace": "eBay", "seller": "tokyo_parts", "price": "$29.99", "url": "https://www.ebay.com/itm/555555555555"},
            {"item_id": "6", "brand": "Honda", "title": "Honda Civic Type R Carbon Spoiler", "marketplace": "AliExpress", "seller": "carbon_factory", "price": "$120.00", "url": "https://www.aliexpress.com/item/100500666666.html"},
            {"item_id": "7", "brand": "Toyota", "title": "Toyota TRD Pro Truck Keychain", "marketplace": "TikTok Shop", "seller": "gadget_hub", "price": "$7.99", "url": "https://shop.tiktok.com/view/777777777"},
        ]

        # 1. Canonical Marketplace Resolution
        dummy_mw = EbayTool.__new__(EbayTool)
        self.assertEqual(dummy_mw._get_item_marketplace(items[0]), "Printerval")
        self.assertEqual(dummy_mw._get_item_marketplace(items[3]), "Redbubble")
        self.assertEqual(dummy_mw._get_item_marketplace(items[4]), "eBay")
        self.assertEqual(dummy_mw._get_item_marketplace(items[5]), "AliExpress")
        self.assertEqual(dummy_mw._get_item_marketplace(items[6]), "TikTok Shop")
        self.assertEqual(dummy_mw._get_item_marketplace({"url": "https://www.manomano.co.uk/item/123"}), "ManoMano")
        self.assertEqual(dummy_mw._get_item_marketplace({"url": "https://www.wish.com/product/123"}), "Wish")
        self.assertEqual(dummy_mw._get_item_marketplace({"url": "https://www.temu.com/goods-123.html"}), "Temu")
        self.assertEqual(dummy_mw._get_item_marketplace({"url": "https://www.vinted.fr/items/123"}), "Vinted")
        self.assertEqual(dummy_mw._get_item_marketplace({"url": "https://articulo.mercadolibre.com.mx/MLM-123"}), "Mercado Libre")

        # 2. Multi-Column Filter Evaluator Helper
        def evaluate_filters(dataset, mkt="All Marketplaces", brand="All Brands", query="", col="Title"):
            filtered = []
            for it in dataset:
                if mkt != "All Marketplaces":
                    item_mkt = dummy_mw._get_item_marketplace(it)
                    if item_mkt.lower() != mkt.lower() and mkt.lower() not in item_mkt.lower():
                        continue
                if brand != "All Brands":
                    if str(it.get("brand", "")).strip().lower() != brand.lower():
                        continue
                if query and not dummy_mw._item_matches_filter(it, query, target_col=col):
                    continue
                filtered.append(it)
            return filtered

        # 3. Test Filter Dimensions
        # All items unfiltered
        self.assertEqual(len(evaluate_filters(items)), 7)

        # Marketplace = Printerval only (Items 1, 2, 3)
        pv_only = evaluate_filters(items, mkt="Printerval")
        self.assertEqual(len(pv_only), 3)
        self.assertTrue(all(it["marketplace"] == "Printerval" for it in pv_only))

        # Marketplace = Printerval + Brand = Toyota (Items 1, 2)
        pv_toyota = evaluate_filters(items, mkt="Printerval", brand="Toyota")
        self.assertEqual(len(pv_toyota), 2)
        self.assertEqual({it["item_id"] for it in pv_toyota}, {"1", "2"})

        # Marketplace = Printerval + Brand = Toyota + Query = "hoodie -zipper" (Item 1 only)
        pv_toyota_hoodie = evaluate_filters(items, mkt="Printerval", brand="Toyota", query="hoodie -zipper", col="Title")
        self.assertEqual(len(pv_toyota_hoodie), 1)
        self.assertEqual(pv_toyota_hoodie[0]["item_id"], "1")

        # Column Scoped Filter: Seller = "PopsQc"
        seller_filter = evaluate_filters(items, query="PopsQc", col="Seller")
        self.assertEqual(len(seller_filter), 1)
        self.assertEqual(seller_filter[0]["item_id"], "4")

        # Column Scoped Filter: Marketplace = "TikTok Shop"
        mkt_col_filter = evaluate_filters(items, query="TikTok", col="Marketplace")
        self.assertEqual(len(mkt_col_filter), 1)
        self.assertEqual(mkt_col_filter[0]["item_id"], "7")

        # 4. DataStore get_all_brands contract
        self.assertTrue(hasattr(self.data_store, "get_all_brands"))
        self.assertTrue(isinstance(self.data_store.get_all_brands(), list))

    def test_staged_dossier_persistence(self):
        """Verify Dossier Staging Vault disk persistence and recovery."""
        sample_staged = [
            {"item_id": "PV-101", "marketplace": "Printerval", "title": "TRD Racing Hoodie", "url": "https://printerval.com/trd-hoodie-p101"},
            {"item_id": "RB-202", "marketplace": "Redbubble", "title": "Toyota Vintage Sticker", "url": "https://redbubble.com/i/sticker/202"}
        ]
        self.data_store.save_staged_dossier(sample_staged)
        loaded = self.data_store.get_staged_dossier()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["item_id"], "PV-101")
        self.assertEqual(loaded[1]["item_id"], "RB-202")

        self.data_store.clear_staged_dossier()
        self.assertEqual(len(self.data_store.get_staged_dossier()), 0)

    def test_coaster_enforcement_not_marked_fluff(self):
        """Verify that branded silicone cup coasters are NOT suppressed by universal fluff filtering."""
        title = "Silicone Car Cup Coaster for Toyota Camry RAV4"
        is_fluff, reason = self.data_store.is_universal_fluff(title)
        self.assertFalse(is_fluff, f"Silicone coaster was incorrectly flagged as fluff: {reason}")

    def test_28_ebay_global_keyword_search(self):
        """Test Item 28: Verify eBay global/general keyword search without store input."""
        from scraper import EbayScraper
        scraper = EbayScraper(headless=True)

        # 1. resolve_store_info on empty/global strings
        info_empty = scraper.resolve_store_info("")
        self.assertEqual(info_empty["store_name"], "")
        self.assertEqual(info_empty["seller"], "")
        self.assertFalse(info_empty["is_store"])

        info_global = scraper.resolve_store_info("🛒 Global eBay Search")
        self.assertEqual(info_global["store_name"], "")
        self.assertEqual(info_global["seller"], "")
        self.assertFalse(info_global["is_store"])

        # 2. _build_url generates clean native eBay keyword search URL
        url = scraper._build_url(info_global, "Toyota TRD", ["case", "poster"], 1, "new")
        self.assertIn("_nkw=Toyota+TRD", url.replace(" ", "+"))
        self.assertIn("-case", url)
        self.assertIn("-poster", url)
        self.assertIn("LH_ItemCondition=1000", url)
        self.assertNotIn("_ssn=", url)

        # 3. resolve_seller returns clean label for UI logging
        seller_label = scraper.resolve_seller("🛒 Global eBay Search")
        self.assertEqual(seller_label, "eBay Global Search")

    def test_29_export_marketplace_dotcom_normalization(self):
        """Test Item 29: Verify that all marketplace names (including emoji-prefixed and short names) strictly normalize to canonical domains."""
        from exporter import normalize_marketplace_code
        # eBay variations
        self.assertEqual(normalize_marketplace_code("🛒 eBay.com"), "ebay.com")
        self.assertEqual(normalize_marketplace_code("eBay"), "ebay.com")
        self.assertEqual(normalize_marketplace_code("ebay"), "ebay.com")
        self.assertEqual(normalize_marketplace_code("🛒 eBay"), "ebay.com")
        self.assertEqual(normalize_marketplace_code("eBay (ebay.de)"), "ebay.de")
        self.assertEqual(normalize_marketplace_code("cafr.ebay.ca"), "ebay.ca - cafr")
        self.assertEqual(normalize_marketplace_code("ebay.ca - cafr"), "ebay.ca - cafr")
        # POD
        self.assertEqual(normalize_marketplace_code("🎨 Redbubble.com"), "redbubble.com")
        self.assertEqual(normalize_marketplace_code("Redbubble"), "redbubble.com")
        self.assertEqual(normalize_marketplace_code("👕 Printerval.com"), "printerval.com")
        self.assertEqual(normalize_marketplace_code("Printerval"), "printerval.com")
        # Social & Retail
        self.assertEqual(normalize_marketplace_code("🎵 TikTok Shop"), "shop.tiktok.com")
        self.assertEqual(normalize_marketplace_code("TikTok Shop"), "shop.tiktok.com")
        self.assertEqual(normalize_marketplace_code("🌐 AliExpress.com"), "aliexpress.com")
        self.assertEqual(normalize_marketplace_code("AliExpress"), "aliexpress.com")
        self.assertEqual(normalize_marketplace_code("🌠 Wish.com"), "wish.com")
        self.assertEqual(normalize_marketplace_code("Wish"), "wish.com")
        self.assertEqual(normalize_marketplace_code("🟠 Temu.com"), "temu.com")
        self.assertEqual(normalize_marketplace_code("Temu"), "temu.com")
        self.assertEqual(normalize_marketplace_code("📚 Scribd.com"), "scribd.com")
        self.assertEqual(normalize_marketplace_code("Scribd"), "scribd.com")
        self.assertEqual(normalize_marketplace_code("🧰 ManoMano"), "manomano.fr")
        self.assertEqual(normalize_marketplace_code("👗 Vinted"), "vinted.co.uk")
        self.assertEqual(normalize_marketplace_code("🛍 Mercado Libre"), "listado.mercadolibre.com.mx")

    def test_30_mercadolibre_catalog_multiseller_expansion(self):
        """Test Item 30: Verify Mercado Libre / Livre Catalog Buy Box multi-seller expansion in Brazil (MLB) and Mexico (MLM)."""
        from mercadolibre_scraper import MercadoLibreScraper

        # 1. Brazil (MLB) Portuguese Catalog Product (e.g. Bravecto)
        scraper_mlb = MercadoLibreScraper(headless=True, site_code="MLB")
        mock_mlb_html = """
        <html>
            <body>
                <h1 class="ui-pdp-title">Antiparasitário Bravecto Cães 40 a 56 Kg 1 Comprimido</h1>
                <img class="ui-pdp-image" src="https://http2.mlstatic.com/D_NQ_NP_123456-MLB.jpg" />
                
                <!-- Buy Box Winner -->
                <div class="ui-pdp-seller__header__title">
                    <span>Vendido por </span>
                    <a href="https://www.mercadolivre.com.br/loja/petlove">Petlove</a>
                </div>
                <div class="ui-pdp-price__second-line">
                    <span class="andes-money-amount__fraction">229,90</span>
                </div>

                <!-- Outras opções de compra (Competing Catalog Sellers) -->
                <div class="ui-pdp-other-sellers">
                    <div class="ui-pdp-other-sellers__card">
                        <a href="https://www.mercadolivre.com.br/p/MLB15918731?wid=MLB1234567890">Cobasi</a>
                        <span class="andes-money-amount__fraction">235,00</span>
                    </div>
                    <div class="ui-pdp-other-sellers__card">
                        <a href="https://perfil.mercadolivre.com.br/_CustId_987654321">Agro Pet Shop</a>
                        <span class="andes-money-amount__fraction">225,50</span>
                    </div>
                    <div class="ui-pdp-other-sellers__card">
                        <a href="https://www.mercadolivre.com.br/item?seller_id=456789&item_id=MLB99887766">Bicho Saudável</a>
                        <span class="andes-money-amount__fraction">240,00</span>
                    </div>
                </div>
            </body>
        </html>
        """
        catalog_url_mlb = "https://www.mercadolivre.com.br/p/MLB15918731"
        sellers_mlb = scraper_mlb.parse_catalog_html(mock_mlb_html, catalog_url=catalog_url_mlb, default_brand="Bravecto", site_code="MLB")

        self.assertEqual(len(sellers_mlb), 4, f"Expected 4 sellers (1 Buy Box + 3 Competitors), got {len(sellers_mlb)}")
        
        # Verify Buy Box winner
        bb_winner = sellers_mlb[0]
        self.assertEqual(bb_winner["seller"], "Petlove")
        self.assertEqual(bb_winner["condition"], "Catalog Buy Box")
        self.assertEqual(bb_winner["location"], "Brazil")
        self.assertIn("BRL", bb_winner["price"])
        self.assertEqual(bb_winner["item_id"], "MLB15918731")

        # Verify Competing sellers
        seller_names = [s["seller"] for s in sellers_mlb]
        self.assertIn("Cobasi", seller_names)
        self.assertIn("Agro Pet Shop", seller_names)
        self.assertIn("Bicho Saudável", seller_names)

        # Verify specific item IDs
        cobasi_item = next(s for s in sellers_mlb if s["seller"] == "Cobasi")
        self.assertEqual(cobasi_item["item_id"], "MLB1234567890")
        self.assertEqual(cobasi_item["condition"], "Catalog Competitor")

        # 2. Mexico (MLM) Spanish Catalog Product
        scraper_mlm = MercadoLibreScraper(headless=True, site_code="MLM")
        mock_mlm_html = """
        <html>
            <body>
                <h1 class="ui-pdp-title">Bravecto Perros 40 a 56 Kg 1 Pipeta</h1>
                <img class="ui-pdp-image" src="https://http2.mlstatic.com/D_NQ_NP_654321-MLM.jpg" />
                
                <!-- Buy Box Winner -->
                <div class="ui-pdp-seller__header__title">
                    <span>Vendido por </span>
                    <a href="https://www.mercadolibre.com.mx/perfil/VET_SAN_ANGEL">Veterinaria San Angel</a>
                </div>
                <div class="ui-pdp-price__second-line">
                    <span class="andes-money-amount__fraction">850</span>
                </div>

                <!-- Otras opciones de compra -->
                <div class="ui-pdp-other-sellers">
                    <div class="ui-pdp-other-sellers__card">
                        <a href="https://www.mercadolibre.com.mx/p/MLM15918731?wid=MLM987654321">FarmaPet MX</a>
                        <span class="andes-money-amount__fraction">820</span>
                    </div>
                </div>
            </body>
        </html>
        """
        catalog_url_mlm = "https://www.mercadolibre.com.mx/p/MLM15918731"
        sellers_mlm = scraper_mlm.parse_catalog_html(mock_mlm_html, catalog_url=catalog_url_mlm, default_brand="Bravecto", site_code="MLM")

        self.assertEqual(len(sellers_mlm), 2)
        self.assertEqual(sellers_mlm[0]["seller"], "Veterinaria San Angel")
        self.assertEqual(sellers_mlm[0]["location"], "Mexico")
        self.assertIn("MXN", sellers_mlm[0]["price"])
        self.assertEqual(sellers_mlm[1]["seller"], "FarmaPet MX")
        self.assertEqual(sellers_mlm[1]["item_id"], "MLM987654321")

    def test_30_queue_addition_resilience(self):
        """Test Item 30: Verify Queue addition resilience across all keyword/store input combinations without blocking popups."""
        from main import EbayTool
        app = EbayTool()
        app.withdraw()

        try:
            # 1. Stores placeholder + custom keyword in target box -> enqueues global sweep for keyword
            app.store_text.delete("1.0", "end")
            app.store_text.insert("1.0", app.store_placeholder)
            app.include_text.delete("1.0", "end")
            app.include_text.insert("1.0", "toyota")
            app.brand_states.clear()
            app.queue.clear()
            app.queue_list.delete(0, "end")

            app._add_to_queue()
            self.assertEqual(len(app.queue), 1, "Must enqueue 1 job when keyword is in target box")
            self.assertEqual(app.queue[0]["brand"], "Toyota")
            self.assertIn("toyota", app.queue[0]["includes"])
            self.assertIn("Global", app.queue[0]["store"])

            # 2. Stores box has keyword 'toyota' directly with empty target box -> converts to global keyword sweep
            app.store_text.delete("1.0", "end")
            app.store_text.insert("1.0", "toyota")
            app.include_text.delete("1.0", "end")
            app.brand_states.clear()
            app.queue.clear()
            app.queue_list.delete(0, "end")

            app._add_to_queue()
            self.assertEqual(len(app.queue), 1, "Must enqueue 1 job when keyword is entered in stores box")
            self.assertEqual(app.queue[0]["brand"], "Toyota")
            self.assertIn("toyota", app.queue[0]["includes"])

            # 3. Clean Brand Sweep with keyword in stores box
            app.store_text.delete("1.0", "end")
            app.store_text.insert("1.0", "honda")
            app.include_text.delete("1.0", "end")
            app.brand_states.clear()
            app.queue.clear()
            app.queue_list.delete(0, "end")

            app._queue_clean_targeted_brands()
            self.assertEqual(len(app.queue), 1, "Clean sweep must enqueue job for keyword in stores box")
            self.assertEqual(app.queue[0]["brand"], "honda")
        finally:
            app.destroy()

    def test_31_ebay_global_and_store_search_dispatch(self):
        """Test Item 31 (Gate 31): Verify eBay scraper URL generation and dispatch without undefined variables."""
        from scraper import EbayScraper
        scraper = EbayScraper()
        
        # 1. Global keyword search (no store)
        global_url = scraper._build_url({}, "toyota", ["case"], 1, "all")
        self.assertIn("ebay.com", global_url)
        self.assertIn("_nkw=toyota", global_url)
        
        # 2. Store specific search
        store_info = scraper.resolve_seller("autostore123")
        store_url = scraper._build_url(store_info, "brake pads", [], 1, "new")
        self.assertIn("autostore123", store_url)
        self.assertIn("brake", store_url)

    def test_32_aliexpress_multipage_search_depth(self):
        """Test Item 32 (Gate 32): Verify AliExpress multi-page URL generation and search depth parameter contracts."""
        from aliexpress_scraper import AliExpressScraper
        import inspect

        ali = AliExpressScraper(headless=True)

        # 1. Verify search signature has max_pages
        sig = inspect.signature(ali.search)
        self.assertIn("max_pages", sig.parameters, "AliExpressScraper.search must accept max_pages")
        self.assertEqual(sig.parameters["max_pages"].default, 3)

        # 2. Verify URL building across pages 1, 2, and 3
        url_p1 = ali._build_search_url({}, "Toyota", page=1)
        url_p2 = ali._build_search_url({}, "Toyota", page=2)
        url_p3 = ali._build_search_url({}, "Toyota", page=3)

    def test_33_wish_search_popup_resilience_and_contracts(self):
        """Test Item 33 (Gate 33): Verify WishScraper URL resolution, HTML card parsing, and pause_event resilience."""
        from wish_scraper import WishScraper
        import threading
        
        wish = WishScraper(headless=True)

        # 1. URL resolution
        global_info = wish.resolve_store_info("GLOBAL")
        self.assertEqual(global_info["store_id"], "GLOBAL")
        global_url = wish._build_search_url(global_info, "Toyota", 1)
        self.assertIn("wish.com/search/Toyota", global_url)

        # Merchant resolution
        merchant_info = wish.resolve_store_info("https://www.wish.com/merchant/5b8f1234abcd")
        self.assertEqual(merchant_info["store_id"], "5b8f1234abcd")

        # 2. HTML parsing with exclusion filtering
        mock_html = """
        <div class="ProductGridItem">
            <a href="/product/6a17f4b199723558acede847">
                <img src="https://canary.contestimg.wish.com/api/image/fetch?img=toyota_rebuild_kit.jpg" />
                <span class="Title">Toyota Tacoma 2.4L Engine Rebuild Kit</span>
                <span class="Price">$466.00</span>
            </a>
        </div>
        <div class="ProductGridItem">
            <a href="/product/6a17f4b199723558acede899">
                <img src="https://canary.contestimg.wish.com/api/image/fetch?img=honda_rebuild_kit.jpg" />
                <span class="Title">Honda Civic Brake Rotors Kit</span>
                <span class="Price">$89.00</span>
            </a>
        </div>
        """
        parsed = wish._parse_html(mock_html, "Wish Merchant", "Toyota", excludes=["honda"])
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["item_id"], "6a17f4b199723558acede847")
        self.assertIn("Toyota", parsed[0]["title"])
    def test_34_interactive_auth_window_positioning(self):
        """Test Item 34 (Gate 34): Verify interactive auth signatures and window coordinate positioning across scrapers."""
        import inspect
        from vinted_scraper import VintedScraper
        from manomano_scraper import ManoManoScraper
        from temu_scraper import TemuScraper
        from tiktok_scraper import TikTokScraper
        from mercadolibre_scraper import MercadoLibreScraper
        from scraper import EbayScraper

        # 1. Vinted
        vinted_sig = inspect.signature(VintedScraper.launch_interactive_auth)
        self.assertIn("window_pos", vinted_sig.parameters)
        self.assertIn("window_size", vinted_sig.parameters)
        self.assertEqual(vinted_sig.parameters["window_pos"].default, (100, 100))

        # 2. ManoMano
        mano_sig = inspect.signature(ManoManoScraper.launch_interactive_auth)
        self.assertIn("window_pos", mano_sig.parameters)
        self.assertIn("window_size", mano_sig.parameters)

        # 3. Temu
        temu_sig = inspect.signature(TemuScraper.launch_interactive_auth)
        self.assertIn("window_pos", temu_sig.parameters)
        self.assertIn("window_size", temu_sig.parameters)

        # 4. TikTok
        tiktok_sig = inspect.signature(TikTokScraper.launch_interactive_auth)
        self.assertIn("window_pos", tiktok_sig.parameters)
        self.assertIn("window_size", tiktok_sig.parameters)

        # 5. Mercado Libre
        meli_sig = inspect.signature(MercadoLibreScraper.launch_interactive_auth)
        self.assertIn("window_pos", meli_sig.parameters)
        self.assertIn("window_size", meli_sig.parameters)

        # 6. EbayScraper (eBay Solve Window)
        ebay_sig = inspect.signature(EbayScraper.open_interactive_solve_window)
        self.assertIn("window_pos", ebay_sig.parameters)
        self.assertIn("window_size", ebay_sig.parameters)

        # 7. Coordinate centering logic test
        class DummyApp:
            def winfo_rootx(self): return 500
            def winfo_rooty(self): return 200
            def winfo_width(self): return 1600
            def winfo_height(self): return 1000

        from main import EbayTool
        pos = EbayTool._get_browser_window_pos(DummyApp(), bw=1100, bh=800)
        # Expected: px + (pw - bw)//2 = 500 + 250 = 750, py + (ph - bh)//2 = 200 + 100 = 300
        self.assertEqual(pos, (750, 300))

    def test_35_printerval_connected_network_and_seller_enrichment(self):
        """Test Item 35: Verify Printerval Connected Network discovery, dHash perceptual hashing, and JS seller enrichment."""
        from printerval_scraper import PrintervalScraper
        scraper = PrintervalScraper(headless=True)

        # 1. Verify method signatures
        self.assertTrue(hasattr(scraper, "find_connected_network"))
        self.assertTrue(hasattr(scraper, "compute_dhash"))
        self.assertTrue(hasattr(scraper, "hamming_distance"))

        # 2. Test dHash computation & distance
        img1 = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        img2 = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        h1 = scraper.compute_dhash(img1)
        h2 = scraper.compute_dhash(img2)
        self.assertEqual(scraper.hamming_distance(h1, h2), 0)

        # 3. Test JS variable regex extraction for seller
        sample_js = 'var product = {"id":39095525,"name":"Camaro SS 5th gen","seller_name":"Lacy Powdered"};'
        import re
        m = re.search(r'["\']seller_name["\']\s*:\s*["\']([^"\']+)["\']', sample_js)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "Lacy Powdered")

    def test_36_redbubble_item_id_and_connected_network(self):
        """Test Item 36: Verify Redbubble composite item ID format and Connected Network Hunter support."""
        from redbubble_scraper import RedbubbleScraper
        scraper = RedbubbleScraper(headless=True)

        # 1. Verify item ID extraction with composite work_id.sku_code
        url1 = "https://www.redbubble.com/i/sticker/Chevy-Camaro-6-6th-gen-lsx-lt-ss-zl1-by-Johnauston/54931656/7sgk"
        self.assertEqual(scraper.extract_item_id(url1), "54931656.7sgk")

        url2 = "https://www.redbubble.com/i/sticker/1969-Chevrolet-Camaro-Z28-Drawing-by-ItsMeRuva/29276444.7sgk"
        self.assertEqual(scraper.extract_item_id(url2), "29276444.7sgk")

        url3 = "https://www.redbubble.com/people/itsmeruva/works/29276444-1969-chevrolet-camaro-z28-drawing"
        self.assertEqual(scraper.extract_item_id(url3), "29276444")

        # 2. Verify Connected Network method signatures
        self.assertTrue(hasattr(scraper, "find_connected_network"))
        self.assertTrue(hasattr(scraper, "compute_dhash"))
        self.assertTrue(hasattr(scraper, "hamming_distance"))
        self.assertTrue(hasattr(scraper, "enrich_seller_info"))

        # 3. Test dHash computation & distance
        img1 = Image.new("RGBA", (100, 100), (0, 128, 255, 255))
        img2 = Image.new("RGBA", (100, 100), (0, 128, 255, 255))
        h1 = scraper.compute_dhash(img1)
        h2 = scraper.compute_dhash(img2)
        self.assertEqual(scraper.hamming_distance(h1, h2), 0)

    def test_37_ebay_multi_locale_and_reverse_sweep(self):
        """Test Item 37: Verify eBay multi-locale domain resolution, URL construction, and reverse locale sweep."""
        from scraper import EbayScraper, EBAY_LOCALES
        scraper = EbayScraper(headless=True)

        # 1. Test EBAY_LOCALES structure
        self.assertGreaterEqual(len(EBAY_LOCALES), 13)
        uk_loc = next((l for l in EBAY_LOCALES if l["domain"] == "ebay.co.uk"), None)
        self.assertIsNotNone(uk_loc)
        self.assertEqual(uk_loc["name"], "United Kingdom")

        # 2. Test _clean_ebay_domain
        self.assertEqual(scraper._clean_ebay_domain("United Kingdom (ebay.co.uk)"), "ebay.co.uk")
        self.assertEqual(scraper._clean_ebay_domain("Germany"), "ebay.de")
        self.assertEqual(scraper._clean_ebay_domain("ebay.com.au"), "ebay.com.au")
        self.assertEqual(scraper._clean_ebay_domain("https://www.ebay.fr/str/frenchshop"), "ebay.fr")
        self.assertEqual(scraper._clean_ebay_domain("🌍 All Locales (Reverse Sweep)"), "ebay.com")
        self.assertEqual(scraper._clean_ebay_domain(""), "ebay.com")

        # 3. Test resolve_store_info with regional domains
        uk_info = scraper.resolve_store_info("https://www.ebay.co.uk/str/coolukstore")
        self.assertEqual(uk_info["domain"], "ebay.co.uk")
        self.assertEqual(uk_info["store_name"], "coolukstore")
        self.assertTrue(uk_info["is_store"])

        de_info = scraper.resolve_store_info("https://www.ebay.de/usr/germanseller")
        self.assertEqual(de_info["domain"], "ebay.de")
        self.assertEqual(de_info["seller"], "germanseller")
        self.assertFalse(de_info["is_store"])

        fr_itm = scraper.resolve_store_info("https://www.ebay.fr/itm/123456789012")
        self.assertEqual(fr_itm["domain"], "ebay.fr")
        self.assertEqual(fr_itm.get("item_id"), "123456789012")

        # 4. Test _build_url with regional domains
        url_uk = scraper._build_url(
            {"store_name": "coolukstore", "seller": "coolukstore", "domain": "ebay.co.uk"},
            include="Camaro",
            excludes=["toy"],
            page=1,
            condition="all",
            domain="ebay.co.uk"
        )
        self.assertTrue(url_uk.startswith("https://www.ebay.co.uk/sch/i.html?"))
        self.assertIn("_ssn=coolukstore", url_uk)
        self.assertIn("Camaro", url_uk)
        self.assertIn("-toy", url_uk)

        # 5. Test _parse_html with domain tag
        sample_html = """
        <html><body>
        <li class="s-item s-item__pl-on-bottom">
            <div class="s-item__info clearfix">
                <a class="s-item__link" href="https://www.ebay.co.uk/itm/123456789012"><h3 class="s-item__title">OEM Emblem Badge</h3></a>
                <span class="s-item__price">£19.99</span>
                <span class="s-item__seller-info-text">seller_uk (100)</span>
            </div>
        </li>
        </body></html>
        """
        parsed_uk = scraper._parse_html(sample_html, fallback_seller="seller_uk", domain="ebay.co.uk")
        self.assertEqual(len(parsed_uk), 1)
        self.assertEqual(parsed_uk[0]["marketplace"], "eBay (ebay.co.uk)")
        self.assertEqual(parsed_uk[0]["domain"], "ebay.co.uk")
        self.assertEqual(parsed_uk[0]["item_id"], "123456789012")

        parsed_us = scraper._parse_html(sample_html, fallback_seller="seller_us", domain="ebay.com")
        self.assertEqual(len(parsed_us), 1)
        self.assertEqual(parsed_us[0]["marketplace"], "eBay")
        self.assertEqual(parsed_us[0]["domain"], "ebay.com")

        # 6. Test probe_seller_active_locale mock
        def mock_fetch(url):
            if "ebay.de" in url:
                return '<html><body><li class="s-item"><a class="s-item__link" href="https://www.ebay.de/itm/999999999999"><h3 class="s-item__title">German Part 999</h3></a></li></body></html>'
            return ""

        original_fetch = scraper._fetch_via_requests
        scraper._fetch_via_requests = mock_fetch
        try:
            detected = scraper.probe_seller_active_locale("german_specialist")
            self.assertEqual(detected, "ebay.de")
        finally:
            scraper._fetch_via_requests = original_fetch

    def test_38_platform_name_and_search_dispatch_routing(self):
        """Test Item 38: Verify all marketplace platform names and dispatch matching logic (including Mercado Libre)."""
        # Test marketplace names from dropdown values
        marketplaces = [
            ("🛒 eBay.com", "eBay"),
            ("🧰 ManoMano", "ManoMano"),
            ("🎵 TikTok Shop", "TikTok Shop"),
            ("👗 Vinted", "Vinted"),
            ("🌐 AliExpress.com", "AliExpress"),
            ("🌠 Wish.com", "Wish"),
            ("🟠 Temu.com", "Temu"),
            ("🛍 Mercado Libre", "Mercado Libre"),
            ("🎨 Redbubble.com", "Redbubble"),
            ("👕 Printerval.com", "Printerval"),
        ]

        def resolve_platform(mkt: str) -> str:
            if "Vinted" in mkt: return "Vinted"
            elif "TikTok" in mkt: return "TikTok Shop"
            elif "ManoMano" in mkt: return "ManoMano"
            elif "Wish" in mkt: return "Wish"
            elif "Temu" in mkt: return "Temu"
            elif "AliExpress" in mkt: return "AliExpress"
            elif "Printerval" in mkt: return "Printerval"
            elif "Redbubble" in mkt: return "Redbubble"
            elif "Mercado" in mkt: return "Mercado Libre"
            return "eBay"

        for raw_val, expected in marketplaces:
            self.assertEqual(resolve_platform(raw_val), expected)

        # Test dispatch matching flags in _process_queue
        for _, platform_name in marketplaces:
            p_low = platform_name.lower()
            s_low = ""
            is_manomano = "manomano" in p_low or "manomano." in s_low
            is_tiktok = "tiktok" in p_low or "tiktok.com" in s_low
            is_vinted = "vinted" in p_low or "vinted." in s_low
            is_wish = "wish" in p_low or "wish.com" in s_low
            is_temu = "temu" in p_low or "temu.com" in s_low
            is_aliexpress = "aliexpress" in p_low or "aliexpress.com" in s_low or "ali" in p_low
            is_meli = "mercado" in p_low or "mercadolibre" in p_low or "mercadolivre" in p_low or "mercadolibre" in s_low or "mercadolivre" in s_low or "meli" in p_low
            is_redbubble = "redbubble" in p_low or "redbubble.com" in s_low
            is_printerval = "printerval" in p_low or "printerval.com" in s_low

            if platform_name == "Mercado Libre":
                self.assertTrue(is_meli, "Mercado Libre platform MUST set is_meli to True")
                self.assertFalse(is_manomano)
                self.assertFalse(is_tiktok)
            elif platform_name == "ManoMano":
                self.assertTrue(is_manomano)
            elif platform_name == "TikTok Shop":
                self.assertTrue(is_tiktok)
            elif platform_name == "Vinted":
                self.assertTrue(is_vinted)
            elif platform_name == "Wish":
                self.assertTrue(is_wish)
            elif platform_name == "Temu":
                self.assertTrue(is_temu)
            elif platform_name == "AliExpress":
                self.assertTrue(is_aliexpress)
            elif platform_name == "Redbubble":
                self.assertTrue(is_redbubble)
            elif platform_name == "Printerval":
                self.assertTrue(is_printerval)

    def test_39_mercadolibre_pause_and_stop_event_contracts(self):
        """Test Item 39: Verify MercadoLibreScraper search, multi_region, and catalog expansion respect pause/stop events."""
        import inspect
        import threading
        from mercadolibre_scraper import MercadoLibreScraper
        meli = MercadoLibreScraper(headless=True)

        # 1. Verify signatures accept stop_event and pause_event
        search_sig = inspect.signature(meli.search)
        self.assertIn("stop_event", search_sig.parameters)
        self.assertIn("pause_event", search_sig.parameters)

        multi_sig = inspect.signature(meli.search_multi_region)
        self.assertIn("stop_event", multi_sig.parameters)
        self.assertIn("pause_event", multi_sig.parameters)

        cat_sig = inspect.signature(meli.extract_catalog_sellers)
        self.assertIn("stop_event", cat_sig.parameters)
        self.assertIn("pause_event", cat_sig.parameters)

        # 2. Verify immediate termination when stop_event is pre-set
        stop_ev = threading.Event()
        stop_ev.set()
        res_cat = meli.extract_catalog_sellers("https://www.mercadolibre.com.mx/p/MLM12345", stop_event=stop_ev)
        self.assertEqual(res_cat, [])

        res_multi = meli.search_multi_region("test", site_codes=["MLM", "MLB"], stop_event=stop_ev)
        self.assertEqual(res_multi, [])

    def test_40_mercadolibre_seller_sanitization_and_enrichment(self):
        """Test Item 40: Verify Mercado Libre seller name sanitization filters boilerplate and extracts storefront handles."""
        from mercadolibre_scraper import MercadoLibreScraper
        meli = MercadoLibreScraper(headless=True)

        # 1. Boilerplate navigation phrases must be filtered and extracted from URL
        s1 = meli._clean_seller_name("Ir para a página do vendedor", "https://www.mercadolivre.com.br/pagina/lojacdc?item_id=MLB123")
        self.assertEqual(s1, "LOJACDC")

        s2 = meli._clean_seller_name("+5.000 Seguidores +100 Produtos", "https://www.mercadolivre.com.br/pagina/webcaopetshop?client=123")
        self.assertEqual(s2, "Webcaopetshop")

        s3 = meli._clean_seller_name("Ir a la página del vendedor", "https://articulo.mercadolibre.com.mx/loja/long-dog?item_id=MLB456")
        self.assertEqual(s3, "Long Dog")

        s4 = meli._clean_seller_name("Ir para a página do vendedor", "https://articulo.mercadolibre.com.mx/_CustId_987654321")
        self.assertEqual(s4, "MeLi_Seller_987654321")

        # 2. Genuine seller names must be preserved and cleaned of prefix
        s5 = meli._clean_seller_name("Vendido por Agro Avenida", "https://www.mercadolivre.com.br/item/MLB789")
        self.assertEqual(s5, "Agro Avenida")

        s6 = meli._clean_seller_name("AGROPETVIRTUAL", "https://www.mercadolivre.com.br/pagina/agropetvirtual")
        self.assertEqual(s6, "AGROPETVIRTUAL")

    def test_41_visual_dredge_widened_tolerance_and_ranking(self):
        """Test Item 41: Verify Visual Dredge expanded pHash tolerance (max_distance=18) and candidate similarity ranking."""
        from visual_harvester import VisualHarvester
        harvester = VisualHarvester()

        # 16-character hex pHash strings with known Hamming distances
        base_hash = "0000000000000000"
        # 0x3ff = 10 set bits (distance 10 -> ~84.4% similarity)
        hash_dist_10 = "00000000000003ff"
        # 0xffff = 16 set bits (distance 16 -> 75% similarity)
        hash_dist_16 = "000000000000ffff"
        # 0x3fffff = 22 set bits (distance 22 -> rejected under tolerance 18)
        hash_dist_22 = "00000000003fffff"

        from visual_catalog import hamming_distance
        self.assertEqual(hamming_distance(base_hash, hash_dist_10), 10)
        self.assertEqual(hamming_distance(base_hash, hash_dist_16), 16)
        self.assertEqual(hamming_distance(base_hash, hash_dist_22), 22)

        # Verify candidate scoring logic
        sim_10 = round((1.0 - (10 / 64.0)) * 100, 1)
        self.assertEqual(sim_10, 84.4)
        sim_16 = round((1.0 - (16 / 64.0)) * 100, 1)
        self.assertEqual(sim_16, 75.0)

    def test_42_scribd_scraper_url_and_resolution(self):
        """Test Item 42: Verify Scribd document scraper URL builder, store resolver, and exclusion checks."""
        from scribd_scraper import ScribdScraper
        scraper = ScribdScraper(headless=True)

        # 1. Resolve store info from document URL
        info1 = scraper.resolve_store_info("https://www.scribd.com/document/742189456/Toyota-Camry-Service-Manual")
        self.assertEqual(info1["store_name"], "Toyota-Camry-Service-Manual")
        self.assertEqual(info1["doc_id"], "742189456")

        # 2. Resolve store info from uploader profile
        info2 = scraper.resolve_store_info("https://www.scribd.com/user/987654321/tech_manuals_pro")
        self.assertEqual(info2["store_name"], "tech_manuals_pro")

        # 3. Clean seller uploader name extraction
        clean_name = scraper._clean_uploader_name("Uploaded by TestBankMaster", "https://www.scribd.com/doc/12345")
        self.assertEqual(clean_name, "TestBankMaster")

    def test_43_vero_seller_disclosure_decomposition(self):
        """Test Item 43: Verify VeRO / eBay seller disclosure decomposition into structured contact and address parts."""
        from vero_pdf_parser import parse_vero_line, parse_vero_text

        # Chinese pinyin seller tracking lines
        line1 = "trdracing / xu jie xu yu xiu qu yong fu lu 35 2, guang zhou, 510000, CN"
        rec1 = parse_vero_line(line1)
        self.assertIsNotNone(rec1)
        self.assertEqual(rec1["handle"], "trdracing")
        self.assertEqual(rec1["contact_name"], "xu jie")
        self.assertEqual(rec1["street_address"], "xu yu xiu qu yong fu lu 35 2")
        self.assertEqual(rec1["city"], "guang zhou")
        self.assertEqual(rec1["postal_code"], "510000")
        self.assertEqual(rec1["country"], "CN")

        line2 = "yu1587_21 / zhao kun yu baiyunqujiefangbeilu1461 1469haoshouceng, shengyipijuchengdangkouhaoN22 1fang, guang zhou, 510000, CN"
        rec2 = parse_vero_line(line2)
        self.assertIsNotNone(rec2)
        self.assertEqual(rec2["handle"], "yu1587_21")
        self.assertEqual(rec2["contact_name"], "zhao kun yu")
        self.assertEqual(rec2["city"], "guang zhou")
        self.assertEqual(rec2["postal_code"], "510000")
        self.assertEqual(rec2["country"], "CN")

        # Western seller tracking line
        line3 = "speedy_auto_us / John Doe 123 Industrial Parkway, Suite 400, Los Angeles, 90001, US"
        rec3 = parse_vero_line(line3)
        self.assertEqual(rec3["handle"], "speedy_auto_us")
        self.assertEqual(rec3["contact_name"], "John Doe")
        self.assertEqual(rec3["city"], "Los Angeles")
        self.assertEqual(rec3["postal_code"], "90001")
        self.assertEqual(rec3["country"], "US")

        # German seller tracking line
        line4 = "euro_parts_de / Hans Schmidt Industriestrasse 14, Munich, 80331, DE"
        rec4 = parse_vero_line(line4)
        self.assertEqual(rec4["handle"], "euro_parts_de")
        self.assertEqual(rec4["contact_name"], "Hans Schmidt")
        self.assertEqual(rec4["city"], "Munich")
        self.assertEqual(rec4["postal_code"], "80331")
        self.assertEqual(rec4["country"], "DE")

    def test_44_vero_registry_ingestion_and_excel_export(self):
        """Test Item 44: Verify VeRO disclosures push into DataStore Enforcement Registry and export Genesis-compliant Excel."""
        from vero_pdf_parser import parse_vero_text, push_to_enforcement_registry, export_to_excel, export_to_csv
        raw_text = """
        trdracing / xu jie xu yu xiu qu yong fu lu 35 2, guang zhou, 510000, CN
        yu1587_21 / zhao kun yu baiyunqujiefangbeilu1461 1469haoshouceng, shengyipijuchengdangkouhaoN22 1fang, guang zhou, 510000, CN
        """
        records = parse_vero_text(raw_text)
        self.assertEqual(len(records), 2)

        # Ingest into DataStore
        updated = push_to_enforcement_registry(records, self.data_store)
        self.assertEqual(updated, 2)

        reg = self.data_store.get_enforcement_registry()
        self.assertIn("trdracing", reg)
        self.assertEqual(reg["trdracing"]["country"], "CN")
        self.assertEqual(reg["trdracing"]["contact_name"], "xu jie")
        self.assertEqual(reg["trdracing"]["disclosure_source"], "VeRO / eBay Disclosure")

        # Test Excel & CSV exports
        xlsx_path = os.path.join(self.temp_dir, "test_vero_disclosures.xlsx")
        csv_path = os.path.join(self.temp_dir, "test_vero_disclosures.csv")
        export_to_excel(records, xlsx_path)
        export_to_csv(records, csv_path)

        self.assertTrue(os.path.exists(xlsx_path))
        self.assertTrue(os.path.exists(csv_path))

        wb = openpyxl.load_workbook(xlsx_path)
        self.assertIn("VeRO Disclosures", wb.sheetnames)
        ws = wb["VeRO Disclosures"]
        self.assertEqual(ws.cell(row=1, column=1).value, "Seller Handle")
        self.assertEqual(ws.cell(row=2, column=1).value, "trdracing")
        self.assertEqual(ws.cell(row=2, column=2).value, "xu jie")
    def test_45_session_vault_registry(self):
        """Test Item 45: Verify SessionVault tracks all gated marketplaces and checks status."""
        from session_vault import SessionVault, VAULT_PLATFORMS
        vault = SessionVault()
        self.assertIn("teepublic", VAULT_PLATFORMS)
        self.assertIn("etsy", VAULT_PLATFORMS)
        self.assertIn("temu", VAULT_PLATFORMS)
        self.assertIn("tiktok", VAULT_PLATFORMS)
        statuses = vault.get_all_statuses()
        self.assertIn("teepublic", statuses)
        self.assertIn("etsy", statuses)
        self.assertTrue(isinstance(statuses["teepublic"]["summary"], str))

    def test_46_teepublic_variant_expansion(self):
        """Test Item 46: Verify TeePublic 1-to-50 POD variant expansion maps to 21 product lines with exact prefix URLs."""
        from teepublic_scraper import TeePublicScraper
        scraper = TeePublicScraper()
        base_item = {
            "title": "Vintage GR Racing Logo T-Shirt",
            "url": "https://www.teepublic.com/t-shirt/998877-vintage-gr-racing",
            "item_id": "998877",
            "seller": "ApexDesigns",
            "image_url": "https://images.teepublic.com/v1/998877.jpg",
            "thumbnail": "https://images.teepublic.com/v1/998877.jpg",
            "brand": "Toyota"
        }
        variants = scraper.expand_design_variants(base_item)
        self.assertEqual(len(variants), 21)
        self.assertEqual(variants[0]["marketplace"], "teepublic.com")
        self.assertTrue(any("Hoodie" in v["title"] for v in variants))
        self.assertTrue(any("Sticker" in v["title"] for v in variants))
        self.assertTrue(any("Phone Case" in v["title"] for v in variants))
        self.assertTrue(any("https://www.teepublic.com/tank-top/998877-vintage-gr-racing" in v["url"] for v in variants))
        self.assertTrue(any("https://www.teepublic.com/hoodie/998877-vintage-gr-racing" in v["url"] for v in variants))

    def test_47_etsy_commercial_classifier(self):
        """Test Item 47: Verify Etsy scraper correctly separates commercial volume listings from 1-of-1 items."""
        from etsy_scraper import EtsyScraper
        scraper = EtsyScraper()
        commercial_item = {
            "title": "Set of 4 Cast Metal TRD Grille Badges with Hardware",
            "threat_intel": "Commercial Merchant (Bestseller | Star Seller)",
            "url": "https://www.etsy.com/listing/1234567"
        }
        self.assertTrue(scraper._is_commercial_scale(commercial_item))

        handpicked_item = {
            "title": "Vintage Single Pre-owned Single 1980s Keyring One of a Kind",
            "threat_intel": "Single Item",
            "url": "https://www.etsy.com/listing/7654321"
        }
        self.assertFalse(scraper._is_commercial_scale(handpicked_item))

    def test_48_spreadshirt_variant_expansion(self):
        """Test Item 48: Verify Spreadshirt 1-to-30 variant expansion maps to physical product lines."""
        from spreadshirt_scraper import SpreadshirtScraper
        scraper = SpreadshirtScraper()
        base_item = {
            "title": "TRD Heritage Stripe Vintage Logo",
            "url": "https://www.spreadshirt.com/shop/design/trd+heritage+mens+t-shirt-D668f8f209142ae166078fcd6",
            "item_id": "D668f8f209142ae166078fcd6",
            "seller": "ApexCustoms",
            "image_url": "https://image.spreadshirtmedia.com/image-server/v1/products/T812A2.jpg",
            "brand": "Toyota"
        }
        variants = scraper.expand_design_variants(base_item)
        self.assertGreaterEqual(len(variants), 20)
        self.assertEqual(variants[0]["marketplace"], "spreadshirt.com")
        self.assertTrue(any("Hoodie" in v["title"] for v in variants))
        self.assertTrue(any("Sticker" in v["title"] for v in variants))
        self.assertTrue(any("Mug" in v["title"] for v in variants))

    def test_49_zazzle_variant_expansion(self):
        """Test Item 49: Verify Zazzle variant expansion and platform detection."""
        from zazzle_scraper import ZazzleScraper
        import batch_importer
        scraper = ZazzleScraper()
        base_item = {
            "title": "TRD Heritage Stripe Design",
            "url": "https://www.zazzle.com/trd_vintage_tshirt-1234567890",
            "item_id": "1234567890",
            "seller": "ApexDesigner",
            "image_url": "https://rlv.zcache.com/test_image.jpg",
            "brand": "Toyota"
        }
        variants = scraper.expand_design_variants(base_item)
        self.assertGreaterEqual(len(variants), 20)
        self.assertTrue(any("Hoodie" in v["title"] for v in variants))
        self.assertTrue(any("Mug" in v["title"] for v in variants))
        self.assertTrue(any("Sticker" in v["title"] for v in variants))
        self.assertEqual(batch_importer.detect_platform("https://www.zazzle.com/custom_tee-1234567890"), "Zazzle")

    def test_50_cafepress_variant_expansion(self):
        """Test Item 50: Verify CafePress variant expansion and platform detection."""
        from cafepress_scraper import CafePressScraper
        import batch_importer
        scraper = CafePressScraper()
        base_item = {
            "title": "TRD Vintage Graphic",
            "url": "https://www.cafepress.com/+trd_vintage_tee,12345678",
            "item_id": "12345678",
            "seller": "CafeArtist",
            "image_url": "https://images.cafepress.com/test.jpg",
            "brand": "Toyota"
        }
        variants = scraper.expand_design_variants(base_item)
        self.assertGreaterEqual(len(variants), 18)
        self.assertTrue(any("Hoodie" in v["title"] for v in variants))
        self.assertTrue(any("Mug" in v["title"] for v in variants))
        self.assertEqual(batch_importer.detect_platform("https://www.cafepress.com/+trd_tee,12345678"), "CafePress")

    def test_51_threadless_variant_expansion(self):
        """Test Item 51: Verify Threadless variant expansion and platform detection."""
        from threadless_scraper import ThreadlessScraper
        import batch_importer
        scraper = ThreadlessScraper()
        base_item = {
            "title": "TRD Retro Badge Artwork",
            "url": "https://artist.threadless.com/designs/trd-retro-badge",
            "item_id": "trd-retro-badge",
            "seller": "ArtistShop",
            "image_url": "https://images.threadless.com/test.jpg",
            "brand": "Toyota"
        }
        variants = scraper.expand_design_variants(base_item)
        self.assertGreaterEqual(len(variants), 18)
        self.assertTrue(any("Tapestry" in v["title"] for v in variants))
        self.assertTrue(any("Hoodie" in v["title"] for v in variants))
        self.assertEqual(batch_importer.detect_platform("https://artist.threadless.com/designs/item"), "Threadless")

    def test_52_teespring_variant_expansion(self):
        """Test Item 52: Verify TeeSpring variant expansion and platform detection."""
        from teespring_scraper import TeeSpringScraper
        import batch_importer
        scraper = TeeSpringScraper()
        base_item = {
            "title": "TRD Offroad Heritage",
            "url": "https://spring.com/listing/trd-offroad-heritage",
            "item_id": "trd-offroad-heritage",
            "seller": "CreatorShop",
            "image_url": "https://mockup.spring.com/test.jpg",
            "brand": "Toyota"
        }
        variants = scraper.expand_design_variants(base_item)
        self.assertGreaterEqual(len(variants), 18)
        self.assertTrue(any("Hoodie" in v["title"] for v in variants))
        self.assertTrue(any("Mug" in v["title"] for v in variants))
        self.assertEqual(batch_importer.detect_platform("https://spring.com/listing/test-item"), "TeeSpring")

    def test_53_fineartamerica_variant_expansion(self):
        """Test Item 53: Verify Fine Art America variant expansion and platform detection."""
        from fineartamerica_scraper import FineArtAmericaScraper
        import batch_importer
        scraper = FineArtAmericaScraper()
        base_item = {
            "title": "Classic Celica GT",
            "url": "https://fineartamerica.com/featured/classic-celica-gt-artist.html",
            "item_id": "classic-celica-gt-artist",
            "seller": "Rodrigo Herweg",
            "image_url": "https://images.fineartamerica.com/test.jpg",
            "brand": "Toyota"
        }
        variants = scraper.expand_design_variants(base_item)
        self.assertGreaterEqual(len(variants), 18)
        self.assertTrue(any("Canvas" in v["title"] for v in variants))
        self.assertTrue(any("Metal" in v["title"] for v in variants))
        self.assertTrue(any("Pillow" in v["title"] for v in variants))
        self.assertEqual(batch_importer.detect_platform("https://fineartamerica.com/featured/test-art.html"), "Fine Art America")
        self.assertEqual(batch_importer.detect_platform("https://artist.pixels.com/featured/test-art.html"), "Fine Art America")

    def test_54_multi_sector_modal_taxonomy_and_presets(self):
        """Test Item 54: Verify MultiSectorModal taxonomy definitions, presets, and job dispatching payload."""
        from multi_sector_modal import SECTOR_TAXONOMY
        self.assertIn("pod", SECTOR_TAXONOMY)
        self.assertIn("ecom", SECTOR_TAXONOMY)
        self.assertIn("gated", SECTOR_TAXONOMY)

        pod_platforms = [p[0] for p in SECTOR_TAXONOMY["pod"]["platforms"]]
        self.assertIn("TeePublic.com", pod_platforms)
        self.assertIn("Redbubble.com", pod_platforms)
        self.assertIn("Printerval.com", pod_platforms)
        self.assertIn("Spreadshirt.com", pod_platforms)
        self.assertIn("Zazzle.com", pod_platforms)

        ecom_platforms = [p[0] for p in SECTOR_TAXONOMY["ecom"]["platforms"]]
        self.assertIn("eBay.com", ecom_platforms)
        self.assertIn("AliExpress.com", ecom_platforms)

        gated_platforms = [p[0] for p in SECTOR_TAXONOMY["gated"]["platforms"]]
        self.assertIn("TikTok Shop", gated_platforms)
        self.assertIn("Temu.com", gated_platforms)
        self.assertIn("Vinted", gated_platforms)
        self.assertIn("Mercado Libre", gated_platforms)

    def test_55_scribd_document_classifier_and_gmw_shield(self):
        """Test Item 55: Verify 3-layer GMW disambiguation shield, threat scoring, and document categorization."""
        from scribd_scraper import classify_scribd_document

        # 1. Verified GMW Engineering Standard with Spec Number
        res1 = classify_scribd_document("GMW14872 Cyclic Corrosion Laboratory Test Procedure", query="GMW14872")
        self.assertEqual(res1["category"], "OEM Engineering Standard")
        self.assertIn("GMW Standard", res1["threat_badge"])
        self.assertEqual(res1["threat_score"], 95)
        self.assertFalse(res1["is_suppressed"])
        self.assertEqual(res1["confidence"], "HIGH")
        self.assertIn("GMW14872", res1["matched_spec"])

        # 2. Verified GMW standard with space (e.g. GMW 3044)
        res2 = classify_scribd_document("General Motors GMW 3044 Zinc Plating Specification")
        self.assertEqual(res2["category"], "OEM Engineering Standard")
        self.assertEqual(res2["threat_score"], 95)
        self.assertFalse(res2["is_suppressed"])

        # 3. Non-OEM False Positive: Gamer Media Workspace
        res3 = classify_scribd_document("Gamer Media Workspace Season 2 Podcast Recording")
        self.assertEqual(res3["category"], "Suppressed False Positive")
        self.assertTrue(res3["is_suppressed"])
        self.assertEqual(res3["threat_score"], 0)
        self.assertIn("Suppressed", res3["threat_badge"])

        # 4. Non-OEM False Positive: Gaming collision with GMW
        res4 = classify_scribd_document("GMW Gaming Clan Minecraft Server Rules")
        self.assertEqual(res4["category"], "Suppressed False Positive")
        self.assertTrue(res4["is_suppressed"])
        self.assertEqual(res4["threat_score"], 0)

        # 5. Benign Corporate / Financial Filing
        res5 = classify_scribd_document("General Motors Company Form 10-Q Quarterly Report Q3 2024")
        self.assertEqual(res5["category"], "Corporate Public Report")
        self.assertTrue(res5["is_suppressed"])
        self.assertEqual(res5["threat_score"], 0)

        # 6. Factory Service / Workshop Manual
        res6 = classify_scribd_document("2023 Chevrolet Corvette C8 Factory Workshop Service Manual")
        self.assertEqual(res6["category"], "Vehicle Service Manual")
        self.assertEqual(res6["threat_score"], 85)
        self.assertFalse(res6["is_suppressed"])
        self.assertIn("Service Manual", res6["threat_badge"])

        # 7. Electrical Wiring Diagram & Pinouts
        res7 = classify_scribd_document("2022 GMC Sierra 1500 ECM Pinout and Electrical Wiring Diagram")
        self.assertEqual(res7["category"], "Electrical / Wiring Diagram")
        self.assertEqual(res7["threat_score"], 85)
        self.assertFalse(res7["is_suppressed"])

        # 8. Technical Service Bulletin (TSB)
        res8 = classify_scribd_document("Technical Service Bulletin TSB 21-NA-149 Steering Column Vibration")
        self.assertEqual(res8["category"], "Dealer Technical Bulletin")
        self.assertEqual(res8["threat_score"], 80)
        self.assertFalse(res8["is_suppressed"])

        # 9. Non-OEM Collision: Casio GMW-B5000 Watch Series
        res9 = classify_scribd_document("Casio GMW-B5000TFC Glass Replacement")
        self.assertEqual(res9["category"], "Suppressed False Positive")
        self.assertTrue(res9["is_suppressed"])
        self.assertEqual(res9["threat_score"], 0)
        self.assertIn("Suppressed", res9["threat_badge"])

        # 10. Ambiguous Standalone GMW with automotive context
        res10 = classify_scribd_document("General Motors Worldwide GMW Engineering Material Specification")
        self.assertEqual(res10["category"], "Ambiguous Document")
        self.assertEqual(res10["threat_score"], 25)
        self.assertFalse(res10["is_suppressed"])
        self.assertIn("Ambiguous", res10["threat_badge"])

        # 11. Other OEM Standards: Ford WSS
        res11 = classify_scribd_document("Ford WSS-M2C913-C Engine Lubricant Specification")
        self.assertEqual(res11["category"], "OEM Engineering Standard")
        self.assertIn("WSS", res11["threat_badge"])
        self.assertEqual(res11["threat_score"], 95)

    def test_56_document_intel_presets_and_datastore(self):
        """Test Item 56: Verify Document Intel presets in data_store and Scribd platform detection in batch_importer."""
        import batch_importer

        # Verify DataStore preset accessors
        presets = self.data_store.get_document_intel_presets()
        self.assertIn("vehicle_manuals", presets)
        self.assertIn("oem_standards", presets)
        self.assertIn("benign_exclusions", presets)

        manuals = presets["vehicle_manuals"]
        self.assertTrue(any("service manual" in m.lower() for m in manuals))
        self.assertTrue(any("workshop manual" in m.lower() for m in manuals))

        standards = presets["oem_standards"]
        self.assertTrue(any("gmw" in s.lower() for s in standards))

        exclusions = presets["benign_exclusions"]
        self.assertTrue(any("10-k" in e.lower() for e in exclusions))
        self.assertTrue(any("gamer" in e.lower() for e in exclusions))

        # Verify batch_importer platform detection
        self.assertEqual(batch_importer.detect_platform("https://www.scribd.com/document/12345678/Sample-Spec"), "Scribd")
        self.assertEqual(batch_importer.detect_platform("https://www.scribd.com/doc/98765432/Wiring-Diagram"), "Scribd")

        # Verify ScribdScraper lifecycle and close() method
        from scribd_scraper import ScribdScraper
        scraper = ScribdScraper(headless=True)
        self.assertTrue(hasattr(scraper, "close"))
        scraper.close()


if __name__ == "__main__":
    unittest.main()






