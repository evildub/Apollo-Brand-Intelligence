"""
Artemis Rights Engine — Dedicated Standalone Test Runner.
Executes fast, isolated unit and integration tests for Artemis components:
- Artemis Bridge (IPC drop-queue, serialization, batch archiving)
- Artemis Data Store (Isolated JSON persistence, brand rights CRUD, LOA storage, queue deduplication)
- Artemis Engine (Legal notice generation with corporate metadata, batch CSV export)
- Apollo-to-Artemis Treeview Item Resolution Regression Test
- Artemis Theme Palette and Style Integrity
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from datetime import datetime

import artemis_bridge
from artemis_data_store import ArtemisDataStore, DEFAULT_ARTEMIS_DATA
from artemis_engine import ArtemisEngine
import artemis


class TestArtemisBridge(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="artemis_bridge_test_")
        self.orig_localappdata = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.test_dir

    def tearDown(self):
        if self.orig_localappdata is not None:
            os.environ["LOCALAPPDATA"] = self.orig_localappdata
        else:
            os.environ.pop("LOCALAPPDATA", None)
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_01_directories_creation(self):
        base_dir = artemis_bridge.get_artemis_base_dir()
        intake_dir = artemis_bridge.get_intake_dir()
        processed_dir = artemis_bridge.get_processed_dir()
        self.assertTrue(os.path.exists(base_dir))
        self.assertTrue(os.path.exists(intake_dir))
        self.assertTrue(os.path.exists(processed_dir))

    def test_02_dispatch_and_ingest_cycle(self):
        sample_listings = [
            {"item_id": "11223344", "title": "Counterfeit Shirt", "platform": "Redbubble", "brand": "Toyota", "price": "$24.99"},
            {"item_id": "55667788", "title": "Fake Emblem", "platform": "Amazon", "brand": "Toyota", "price": "$15.00"}
        ]
        batch_path = artemis_bridge.dispatch_batch_to_artemis(sample_listings, source_batch_name="Test Recon Batch")
        self.assertTrue(os.path.exists(batch_path))

        pending = artemis_bridge.get_pending_artemis_batches()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["total_items"], 2)
        self.assertEqual(pending[0]["batch_name"], "Test Recon Batch")

        artemis_bridge.mark_batch_as_ingested(batch_path)
        self.assertFalse(os.path.exists(batch_path))
        self.assertEqual(len(artemis_bridge.get_pending_artemis_batches()), 0)


class TestArtemisDataStore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="artemis_ds_test_")
        self.data_file = os.path.join(self.test_dir, "artemis_data.json")
        self.orig_localappdata = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.test_dir
        self.ds = ArtemisDataStore(data_file=self.data_file)

    def tearDown(self):
        if self.orig_localappdata is not None:
            os.environ["LOCALAPPDATA"] = self.orig_localappdata
        else:
            os.environ.pop("LOCALAPPDATA", None)
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_01_initialization_defaults(self):
        self.assertTrue(os.path.exists(self.data_file))
        brands = self.ds.get_all_brands()
        self.assertIn("Toyota", brands)
        self.assertIn("General Motors", brands)

    def test_02_queue_enqueue_and_deduplication(self):
        items = [
            {"item_id": "RB1001", "platform": "Redbubble", "title": "Sticker", "price": "$4.50"},
            {"item_id": "RB1001", "platform": "Redbubble", "title": "Duplicate Sticker", "price": "$4.50"},
            {"item_id": "AMZ2002", "platform": "Amazon", "title": "Hoodie", "price": "$49.99"},
        ]
        added = self.ds.enqueue_listings(items, source_batch="Test Ingest")
        self.assertEqual(added, 2)  # Duplicate skipped

        queue = self.ds.get_enforcement_queue()
        self.assertEqual(len(queue), 2)

        # Update status
        qid = queue[0]["queue_id"]
        self.ds.update_queue_item_status(qid, "Filed", notes="Filed via portal")
        updated_queue = self.ds.get_enforcement_queue()
        matched = [it for it in updated_queue if it["queue_id"] == qid][0]
        self.assertEqual(matched["status"], "Filed")
        self.assertEqual(matched.get("status_notes"), "Filed via portal")

        # Remove item
        removed = self.ds.remove_queue_items([qid])
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.ds.get_enforcement_queue()), 1)

    def test_03_brand_rights_crud_and_loa_storage(self):
        # Register new brand with comprehensive fields
        brand_info = {
            "rights_holder": "Acme Global Brands Inc.",
            "company_address": "100 Acme Way, Austin, TX 78701, USA",
            "phone_number": "+1-512-555-0199",
            "contact_email": "legal@acme.com",
            "authorized_agent": "Jane Doe, Lead IP Counsel",
            "trademark_regs": ["5,555,111", "5,555,222"],
            "copyright_regs": ["VA 5-555-333"],
            "loa_path": "",
            "default_claim": "Counterfeit Goods",
            "statement": "Acme owns all trademarks."
        }
        self.ds.set_brand_rights("Acme", brand_info)

        loaded = self.ds.get_brand_rights("Acme")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["company_address"], "100 Acme Way, Austin, TX 78701, USA")
        self.assertEqual(loaded["phone_number"], "+1-512-555-0199")

        # Create mock LOA file and store it
        mock_loa_file = os.path.join(self.test_dir, "acme_letter_of_auth.pdf")
        with open(mock_loa_file, "wb") as f:
            f.write(b"%PDF-1.4 Mock LOA Document")

        stored_dest = self.ds.store_loa_document("Acme", mock_loa_file)
        self.assertTrue(os.path.exists(stored_dest))
        self.assertTrue(stored_dest.endswith(".pdf"))

        updated_acme = self.ds.get_brand_rights("Acme")
        self.assertEqual(updated_acme["loa_path"], stored_dest)

        # Deletion
        self.ds.remove_brand_rights("Acme")
        self.assertIsNone(self.ds.get_brand_rights("Acme"))

    def test_04_submission_history_logging(self):
        sample_items = [
            {"item_id": "TEST_001", "platform": "eBay", "title": "Fake Watch"}
        ]
        sub_id = self.ds.log_submission("eBay", "Rolex", sample_items, notice_reference="VERO-2026-001")
        self.assertTrue(sub_id.startswith("sub_"))

        history = self.ds.get_submission_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["platform"], "eBay")
        self.assertEqual(history[0]["brand"], "Rolex")
        self.assertEqual(history[0]["notice_reference"], "VERO-2026-001")


class TestArtemisEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="artemis_eng_test_")
        self.data_file = os.path.join(self.test_dir, "artemis_data.json")
        self.orig_localappdata = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.test_dir
        self.ds = ArtemisDataStore(data_file=self.data_file)
        self.engine = ArtemisEngine(self.ds)

    def tearDown(self):
        if self.orig_localappdata is not None:
            os.environ["LOCALAPPDATA"] = self.orig_localappdata
        else:
            os.environ.pop("LOCALAPPDATA", None)
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_01_notice_generation_with_full_metadata(self):
        items = [
            {"item_id": "AMZ_999", "seller": "BadSeller123", "price": "$29.99", "title": "Unauthorized Logo Shirt", "url": "https://amazon.com/dp/AMZ_999"}
        ]
        notice = self.engine.generate_notice_text("Amazon", "Toyota", items)
        self.assertIn("FORMAL NOTICE OF INTELLECTUAL PROPERTY INFRINGEMENT", notice)
        self.assertIn("Toyota Motor Sales, U.S.A., Inc.", notice)
        self.assertIn("6565 Headquarters Dr, Plano, TX 75024, USA", notice)
        self.assertIn("+1-800-331-4331", notice)
        self.assertIn("ip.protection@toyota.com", notice)
        self.assertIn("AMZ_999", notice)
        self.assertIn("BadSeller123", notice)
        self.assertIn("https://amazon.com/dp/AMZ_999", notice)

    def test_02_export_batch_csv(self):
        items = [
            {"item_id": "RB_888", "platform": "Redbubble", "brand": "Toyota", "seller": "ArtCopycat", "price": "$18.00", "title": "Car Sticker", "url": "https://redbubble.com/i/RB_888", "queued_at": "2026-09-25 12:00:00"}
        ]
        csv_path = os.path.join(self.test_dir, "batch_export.csv")
        out = self.engine.export_batch_csv(items, csv_path)
        self.assertTrue(os.path.exists(out))
        with open(out, "r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("Item ID,Platform,Brand,Seller / Merchant", content)
        self.assertIn("RB_888,Redbubble,Toyota,ArtCopycat", content)


class TestApolloDispatchRegression(unittest.TestCase):
    def test_item_resolution_with_string_iids(self):
        """Simulate Treeview row resolution when IIDs are arbitrary strings (e.g. 'I001', 'I00B')
        and verify they correctly resolve to listings or reconstruct from values."""
        results = [
            {"item_id": "12345", "brand": "Harley", "product_type": "Shirt", "title": "Harley Tee", "price": "$25", "seller": "BikerShop", "url": "https://redbubble.com/i/12345"},
            {"item_id": "67890", "brand": "Ford", "product_type": "Cap", "title": "Ford Hat", "price": "$15", "seller": "HatStore", "url": "https://ebay.com/itm/67890"}
        ]

        # Scenario: Treeview returns string iids 'I001' and 'I002'
        selected_iids = ["I001", "I002"]
        tree_mock_data = {
            "I001": {
                "values": ["Harley", "Shirt", "Harley Tee", "12345", "$25", "BikerShop", "US", "High Threat", "Texas", "https://img.jpg", "https://redbubble.com/i/12345"]
            },
            "I002": {
                "values": ["Ford", "Cap", "Ford Hat", "67890", "$15", "HatStore", "CN", "Normal", "China", "https://img2.jpg", "https://ebay.com/itm/67890"]
            }
        }

        def mock_get_item_by_tree_id(iid):
            vals = tree_mock_data.get(iid, {}).get("values", [])
            if len(vals) > 3:
                row_item_id = str(vals[3]).strip()
                row_url = str(vals[10] if len(vals) > 10 else "").strip()
                for it in results:
                    if (row_item_id and str(it.get("item_id", "")).strip() == row_item_id) or (row_url and str(it.get("url", "")).strip() == row_url):
                        return it
            return None

        # Execute resolution logic
        target_items = []
        for iid in selected_iids:
            item = mock_get_item_by_tree_id(iid)
            if item:
                target_items.append(item)
            else:
                vals = tree_mock_data.get(iid, {}).get("values", [])
                if len(vals) >= 4:
                    rec_item = {
                        "brand": vals[0],
                        "item_id": vals[3],
                        "title": vals[2],
                        "price": vals[4],
                        "seller": vals[5],
                        "url": vals[10]
                    }
                    target_items.append(rec_item)

        self.assertEqual(len(target_items), 2)
        self.assertEqual(target_items[0]["item_id"], "12345")
        self.assertEqual(target_items[1]["item_id"], "67890")


class TestArtemisThemesAndStyle(unittest.TestCase):
    def test_theme_keys_and_properties(self):
        required_keys = {"bg", "panel", "entry_bg", "text", "subtext", "border", "accent", "btn_normal_bg", "btn_normal_fg"}
        for th_key, th_dict in artemis.ARTEMIS_THEMES.items():
            for req in required_keys:
                self.assertIn(req, th_dict, f"Theme '{th_key}' missing required key '{req}'")
            self.assertTrue(th_dict["bg"].startswith("#"))
            self.assertTrue(th_dict["panel"].startswith("#"))


class TestArtemisSettingsAndGuide(unittest.TestCase):
    def setUp(self):
        self.app = artemis.ArtemisApp()

    def tearDown(self):
        self.app.destroy()

    def test_01_settings_menu_structure(self):
        self.assertTrue(hasattr(self.app, "settings_mb"))
        self.assertTrue(hasattr(self.app, "settings_menu"))
        self.assertTrue(hasattr(self.app, "theme_menu"))
        # Verify theme menu has all 19 themes
        self.assertEqual(self.app.theme_menu.index("end") + 1, len(artemis.ARTEMIS_THEMES))

    def test_02_field_guide_modal_lifecycle(self):
        guide = artemis.ArtemisFieldGuideModal(self.app)
        self.assertTrue(guide.winfo_exists())
        self.assertIn("Field Guide", guide.title())
        guide.destroy()

    def test_03_diagnostics_modal_lifecycle(self):
        from system_diagnostics import SystemDiagnosticsModal
        modal = SystemDiagnosticsModal(parent=self.app)
        self.assertTrue(modal.winfo_exists())
        self.assertIn("Diagnostics", modal.title())
        modal.destroy()


class TestSystemDiagnostics(unittest.TestCase):
    def test_01_runtime_probes(self):
        from system_diagnostics import DiagnosticEngine
        res = DiagnosticEngine.check_runtime_environment()
        self.assertTrue(any(r.name == "Python Environment" and r.status in ("PASS", "WARN") for r in res))
        self.assertTrue(any(r.name == "Operating System & CPU" and r.status == "PASS" for r in res))

    def test_02_visual_probes(self):
        from system_diagnostics import DiagnosticEngine
        res = DiagnosticEngine.check_visual_and_hashing()
        self.assertTrue(any(r.name == "Imaging Subsystem (Pillow)" and r.status == "PASS" for r in res))
        self.assertTrue(any(r.name == "64-bit DCT pHash Algorithm" and r.status == "PASS" for r in res))

    def test_03_storage_and_ipc_probes(self):
        from system_diagnostics import DiagnosticEngine
        s_res = DiagnosticEngine.check_storage_and_databases()
        self.assertTrue(any(r.name == "Local Disk IO Latency" and r.status == "PASS" for r in s_res))
        ipc_res = DiagnosticEngine.check_ipc_bridge()
        self.assertTrue(any(r.name == "Atomic Drop-Queue Protocol" and r.status == "PASS" for r in ipc_res))


if __name__ == "__main__":
    unittest.main(verbosity=2)
