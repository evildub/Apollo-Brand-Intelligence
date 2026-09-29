"""
Artemis Data Store — Independent Persistence Layer for Artemis Rights Engine.
Manages legal brand rights, persistent portal configurations, the active enforcement queue,
and submission audit logs in an isolated artemis_data.json.
"""

import json
import os
import copy
import shutil
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from artemis_bridge import get_artemis_base_dir

ARTEMIS_DATA_FILE = os.path.join(get_artemis_base_dir(), "artemis_data.json")

DEFAULT_ARTEMIS_DATA: Dict[str, Any] = {
    "settings": {
        "theme": "artemis_emerald",
        "default_platform": "Amazon",
        "auto_archive_filed": True,
        "human_in_the_loop_confirm": True
    },
    "brand_rights": {
        "Toyota": {
            "rights_holder": "Toyota Motor Sales, U.S.A., Inc.",
            "company_address": "6565 Headquarters Dr, Plano, TX 75024, USA",
            "phone_number": "+1-800-331-4331",
            "contact_email": "ip.protection@toyota.com",
            "authorized_agent": "Brand Protection & Legal Compliance Division",
            "trademark_regs": ["1,234,567", "2,345,678", "3,456,789"],
            "copyright_regs": ["VA 2-345-678"],
            "loa_path": "",
            "default_claim": "Counterfeit Product / Unauthorized Trademark Reproduction",
            "statement": "The seller is offering products bearing unauthorized reproductions of registered trademarks, likely to cause consumer confusion."
        },
        "General Motors": {
            "rights_holder": "General Motors LLC",
            "company_address": "300 Renaissance Center, Detroit, MI 48265, USA",
            "phone_number": "+1-800-222-1020",
            "contact_email": "brandprotection@gm.com",
            "authorized_agent": "Global Brand Protection Counsel",
            "trademark_regs": ["987,654", "876,543"],
            "copyright_regs": ["TX 8-765-432"],
            "loa_path": "",
            "default_claim": "Unauthorized Use of Registered Trademark & Counterfeiting",
            "statement": "The goods offered for sale reproduce General Motors trademarks without authorization or license."
        }
    },
    "portal_configs": {
        "Amazon": {
            "name": "Amazon Brand Registry",
            "portal_url": "https://brandregistry.amazon.com/brand-protection/report-a-violation",
            "auth_required": True,
            "id_type": "ASIN",
            "batch_limit": 50
        },
        "Walmart": {
            "name": "Walmart Brand Portal",
            "portal_url": "https://brandportal.walmart.com/",
            "auth_required": True,
            "id_type": "Item ID / URL",
            "batch_limit": 100
        },
        "eBay": {
            "name": "eBay VeRO Portal",
            "portal_url": "https://www.ebay.com/help/policies/member-behavior-policies/verified-rights-owner-program-vero?id=4349",
            "auth_required": True,
            "id_type": "Listing ID",
            "batch_limit": 100
        },
        "Redbubble": {
            "name": "Redbubble IP Rights Notice",
            "portal_url": "https://help.redbubble.com/hc/en-us/requests/new?ticket_form_id=360000954531",
            "auth_required": False,
            "id_type": "Work URL",
            "batch_limit": 25
        },
        "Printerval": {
            "name": "Printerval IP Notice",
            "portal_url": "https://printerval.com/contact-us",
            "auth_required": False,
            "id_type": "Product URL",
            "batch_limit": 30
        }
    },
    "enforcement_queue": [],
    "submission_history": []
}

class ArtemisDataStore:
    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or ARTEMIS_DATA_FILE
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self):
        with self._lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, "r", encoding="utf-8") as f:
                        self._data = json.load(f)
                except Exception:
                    self._data = copy.deepcopy(DEFAULT_ARTEMIS_DATA)
            else:
                self._data = copy.deepcopy(DEFAULT_ARTEMIS_DATA)
                self._save_locked()

            # Ensure all core top-level keys exist
            for k, v in DEFAULT_ARTEMIS_DATA.items():
                if k not in self._data:
                    self._data[k] = copy.deepcopy(v)

    def _save_locked(self):
        tmp_file = self.data_file + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, self.data_file)
        except Exception:
            if os.path.exists(tmp_file):
                try: os.remove(tmp_file)
                except Exception: pass

    def save(self):
        with self._lock:
            self._save_locked()

    # ── Settings ─────────────────────────────────────────────────────────────
    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get("settings", {}).get(key, default)

    def set_setting(self, key: str, value: Any):
        with self._lock:
            self._data.setdefault("settings", {})[key] = value
            self._save_locked()

    # ── Brand Rights Registry ────────────────────────────────────────────────
    def get_all_brands(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data.get("brand_rights", {}))

    def get_brand_rights(self, brand_name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._data.get("brand_rights", {}).get(brand_name))

    def set_brand_rights(self, brand_name: str, rights_info: Dict[str, Any]):
        with self._lock:
            self._data.setdefault("brand_rights", {})[brand_name] = rights_info
            self._save_locked()

    def remove_brand_rights(self, brand_name: str):
        with self._lock:
            if brand_name in self._data.get("brand_rights", {}):
                del self._data["brand_rights"][brand_name]
                self._save_locked()

    def store_loa_document(self, brand_name: str, src_path: str) -> str:
        """Safely copy and attach a Letter of Authorization (LOA) document to brand storage."""
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source LOA document does not exist: {src_path}")

        loa_dir = os.path.join(get_artemis_base_dir(), "loa_documents")
        os.makedirs(loa_dir, exist_ok=True)

        _, ext = os.path.splitext(src_path)
        clean_brand = "".join(c for c in brand_name if c.isalnum() or c in ("-", "_")).lower() or "brand"
        dest_filename = f"{clean_brand}_loa_{int(datetime.now().timestamp())}{ext}"
        dest_path = os.path.join(loa_dir, dest_filename)

        shutil.copy2(src_path, dest_path)

        with self._lock:
            if brand_name in self._data.get("brand_rights", {}):
                self._data["brand_rights"][brand_name]["loa_path"] = dest_path
                self._save_locked()

        return dest_path

    # ── Portal Configurations ────────────────────────────────────────────────
    def get_portal_configs(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data.get("portal_configs", {}))

    # ── Active Enforcement Queue ─────────────────────────────────────────────
    def get_enforcement_queue(self) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._data.get("enforcement_queue", []))

    def enqueue_listings(self, listings: List[Dict[str, Any]], source_batch: str = "Manual") -> int:
        """Add listings to the enforcement queue, avoiding duplicates based on item_id and platform."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added_count = 0

        with self._lock:
            queue = self._data.setdefault("enforcement_queue", [])
            existing_signatures = {(item.get("platform", "").lower(), str(item.get("item_id", "")).strip()) for item in queue}

            for it in listings:
                item_id = str(it.get("item_id") or it.get("id") or "").strip()
                platform = it.get("platform") or it.get("marketplace") or "Unknown"
                sig = (platform.lower(), item_id)
                if item_id and sig in existing_signatures:
                    continue

                record = {
                    "queue_id": f"artemis_q_{int(datetime.now().timestamp())}_{added_count}",
                    "item_id": item_id,
                    "title": it.get("title", "Untitled Listing"),
                    "seller": it.get("seller", "Unknown Merchant"),
                    "price": it.get("price", "$0.00"),
                    "platform": platform,
                    "url": it.get("url", ""),
                    "image_url": it.get("image_url") or it.get("thumbnail") or "",
                    "brand": it.get("brand", "Unassigned"),
                    "violation_type": it.get("violation_type", "Trademark Infringement / Counterfeit"),
                    "evidence_note": it.get("evidence_note", ""),
                    "status": "Pending",
                    "source_batch": source_batch,
                    "queued_at": now_str
                }
                queue.append(record)
                existing_signatures.add(sig)
                added_count += 1

            if added_count > 0:
                self._save_locked()

        return added_count

    def update_queue_item_status(self, queue_id: str, new_status: str, notes: str = ""):
        with self._lock:
            queue = self._data.get("enforcement_queue", [])
            for it in queue:
                if it.get("queue_id") == queue_id:
                    it["status"] = new_status
                    if notes:
                        it["status_notes"] = notes
                    self._save_locked()
                    break

    def remove_queue_items(self, queue_ids: List[str]) -> int:
        with self._lock:
            queue = self._data.get("enforcement_queue", [])
            init_len = len(queue)
            self._data["enforcement_queue"] = [it for it in queue if it.get("queue_id") not in queue_ids]
            removed = init_len - len(self._data["enforcement_queue"])
            if removed > 0:
                self._save_locked()
            return removed

    def clear_enforcement_queue(self):
        with self._lock:
            self._data["enforcement_queue"] = []
            self._save_locked()

    # ── Submission History & Audit Log ───────────────────────────────────────
    def log_submission(self, platform: str, brand: str, items: List[Dict[str, Any]], notice_reference: str = "", submission_type: str = "Portal Automation") -> str:
        """Record a completed or attempted submission into the permanent audit log."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry_id = f"sub_{int(datetime.now().timestamp())}_{len(items)}"
        record = {
            "submission_id": entry_id,
            "platform": platform,
            "brand": brand,
            "notice_reference": notice_reference,
            "submission_type": submission_type,
            "total_items": len(items),
            "item_ids": [it.get("item_id") for it in items if it.get("item_id")],
            "items_snapshot": items,
            "submitted_at": now_str,
            "status": "Submitted"
        }
        with self._lock:
            self._data.setdefault("submission_history", []).insert(0, record)
            # Cap history at 1,000 entries
            if len(self._data["submission_history"]) > 1000:
                self._data["submission_history"] = self._data["submission_history"][:1000]
            self._save_locked()
        return entry_id

    def get_submission_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._data.get("submission_history", []))
