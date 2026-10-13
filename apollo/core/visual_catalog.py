# visual_catalog.py
# Apollo Dual-Sided Visual Packaging & Threat Intelligence Catalog
# High-Speed Perceptual Hashing (pHash) with Multi-Hash Threat Clustering

import os
import json
import uuid
import math
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Optional
from PIL import Image

logger = logging.getLogger("Apollo.VisualCatalog")

def compute_phash(image: Image.Image, hash_size: int = 8, highfreq_factor: int = 4) -> str:
    """
    Compute a 64-bit perceptual hash (pHash) using discrete cosine transform (DCT).
    Immune to resizing, minor color shifts, compression artifacts, and light watermarks.
    """
    try:
        img_size = hash_size * highfreq_factor
        img = image.convert("L").resize((img_size, img_size), Image.Resampling.BILINEAR)
        pixels = list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())

        # 1D DCT on rows
        row_dct = []
        for y in range(img_size):
            row = pixels[y * img_size : (y + 1) * img_size]
            row_res = []
            for u in range(img_size):
                sum_val = sum(row[x] * math.cos((2 * x + 1) * u * math.pi / (2 * img_size)) for x in range(img_size))
                alpha = 1.0 / math.sqrt(img_size) if u == 0 else math.sqrt(2.0 / img_size)
                row_res.append(alpha * sum_val)
            row_dct.append(row_res)

        # 1D DCT on columns (sample lowest frequency coefficients)
        dct = []
        for u in range(hash_size):
            for v in range(hash_size):
                sum_val = sum(row_dct[y][v] * math.cos((2 * y + 1) * u * math.pi / (2 * img_size)) for y in range(img_size))
                alpha = 1.0 / math.sqrt(img_size) if u == 0 else math.sqrt(2.0 / img_size)
                dct.append(alpha * sum_val)

        sub_dct = dct[1:]
        if not sub_dct:
            return "0" * 16
        median = sorted(sub_dct)[len(sub_dct) // 2]
        bit_str = "".join("1" if val > median else "0" for val in dct)
        return f"{int(bit_str, 2):016x}"
    except Exception as e:
        logger.error(f"Error computing pHash: {e}")
        return ""

def hamming_distance(hex1: str, hex2: str) -> int:
    """Calculate Hamming bit difference between two 64-bit hexadecimal hashes (0 to 64)."""
    try:
        val1 = int(hex1, 16)
        val2 = int(hex2, 16)
        return bin(val1 ^ val2).count("1")
    except Exception:
        return 64

class VisualCatalogManager:
    """
    Manages persistent storage and matching for:
    1. Green Catalog: Known Benign Packaging (e.g. Denso Aftermarket Blue Box)
    2. Red Catalog: Known Counterfeit Stock Photos & Infringing Packaging
    Supports Multi-Hash Threat Asset Clusters (merging multiple photo variants/angles into one entity).
    """
    def __init__(self, base_dir: Optional[str] = None):
        if not base_dir:
            appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            base_dir = os.path.join(appdata, "Apollo_Visual_Catalog")
        self.base_dir = base_dir
        self.thumbs_dir = os.path.join(self.base_dir, "thumbs")
        self.catalog_file = os.path.join(self.base_dir, "visual_catalog.json")
        os.makedirs(self.thumbs_dir, exist_ok=True)
        self.match_threshold: int = 6
        try:
            from data_store import DataStore
            ds = DataStore()
            self.match_threshold = int(ds.get_setting("visual_match_threshold", 6))
        except Exception:
            pass
        self.entries: List[Dict] = self._load_catalog()

    def get_all_entries(self) -> List[Dict]:
        """Return all catalog entries."""
        return list(self.entries)

    def list_entries(self, entry_type: Optional[str] = None) -> List[Dict]:
        """Return catalog entries, optionally filtered by 'benign' or 'counterfeit'."""
        if entry_type and entry_type.lower() != "all":
            return [e for e in self.entries if e.get("type") == entry_type]
        return list(self.entries)

    def get_entries_by_type(self, entry_type: str) -> List[Dict]:
        """Alias for list_entries with entry_type filter."""
        return self.list_entries(entry_type=entry_type)

    def _load_catalog(self) -> List[Dict]:
        if os.path.exists(self.catalog_file):
            try:
                with open(self.catalog_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Normalize entries for cluster support
                    for item in data:
                        if "hashes" not in item and "hash" in item:
                            item["hashes"] = [item["hash"]]
                        if "variants" not in item:
                            item["variants"] = [{
                                "id": item.get("id"),
                                "hash": item.get("hash", ""),
                                "thumb_path": item.get("thumb_path", ""),
                                "source_url": item.get("source_url", ""),
                                "label": item.get("label", "")
                            }]
                    return data
            except Exception as e:
                logger.error(f"Error loading visual catalog: {e}")
        return []

    def _save_catalog(self):
        try:
            with open(self.catalog_file, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving visual catalog: {e}")

    def add_entry(self, img_pil: Image.Image, entry_type: str = "benign", label: str = "", source_url: str = "", notes: str = "") -> Optional[Dict]:
        """
        Add a new image entry to the visual catalog with thumbnail and pHash.
        entry_type: 'benign' or 'counterfeit'
        """
        if not img_pil:
            return None

        h = compute_phash(img_pil)
        if not h:
            return None

        entry_id = str(uuid.uuid4())[:8]
        thumb_name = f"{entry_type}_{entry_id}.png"
        thumb_path = os.path.join(self.thumbs_dir, thumb_name)

        # Save thumbnail (max 96x96)
        try:
            thumb = img_pil.copy()
            thumb.thumbnail((96, 96), Image.Resampling.LANCZOS)
            thumb.save(thumb_path, format="PNG")
        except Exception as e:
            logger.warning(f"Error saving thumbnail: {e}")
            thumb_path = ""

        default_lbl = "Known Benign Packaging" if entry_type == "benign" else "Known Counterfeit Photo"
        final_label = label.strip() if label.strip() else default_lbl

        entry = {
            "id": entry_id,
            "hash": h,
            "hashes": [h],
            "variants": [{
                "id": entry_id,
                "hash": h,
                "thumb_path": thumb_path,
                "source_url": source_url,
                "label": final_label
            }],
            "type": entry_type, # 'benign' or 'counterfeit'
            "label": final_label,
            "thumb_path": thumb_path,
            "source_url": source_url,
            "notes": notes,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "match_count": 0
        }
        self.entries.append(entry)
        self._save_catalog()
        return entry

    def merge_entries(self, entry_ids: List[str], unified_label: str = "", unified_type: Optional[str] = None) -> Optional[Dict]:
        """
        Merge multiple visual catalog entries into a single Unified Multi-Hash Threat Cluster.
        Combines all pHashes and variant thumbnails under one master entity.
        """
        if not entry_ids or len(entry_ids) < 2:
            return None

        to_merge = [e for e in self.entries if e.get("id") in entry_ids]
        if len(to_merge) < 2:
            return None

        primary = to_merge[0]
        final_type = unified_type or primary.get("type", "counterfeit")
        final_label = unified_label.strip() if unified_label.strip() else primary.get("label", "Threat Asset Cluster")

        all_hashes = []
        all_variants = []
        seen_hashes = set()

        seen_thumbs = set()
        for item in to_merge:
            item_variants = item.get("variants", [])
            if item_variants:
                for v in item_variants:
                    vh = v.get("hash", "")
                    tp = v.get("thumb_path") or v.get("source_url", "")
                    if vh and vh not in all_hashes:
                        all_hashes.append(vh)
                    if tp not in seen_thumbs or not tp:
                        if tp: seen_thumbs.add(tp)
                        all_variants.append(v)
            else:
                h = item.get("hash", "")
                tp = item.get("thumb_path") or item.get("source_url", "")
                if h and h not in all_hashes:
                    all_hashes.append(h)
                if tp not in seen_thumbs or not tp:
                    if tp: seen_thumbs.add(tp)
                    all_variants.append({
                        "id": item.get("id"),
                        "hash": h,
                        "thumb_path": item.get("thumb_path", ""),
                        "source_url": item.get("source_url", ""),
                        "label": item.get("label", "")
                    })

        cluster_id = str(uuid.uuid4())[:8]
        master_entry = {
            "id": cluster_id,
            "hash": all_hashes[0] if all_hashes else primary.get("hash", ""),
            "hashes": all_hashes,
            "variants": all_variants,
            "type": final_type,
            "label": final_label,
            "thumb_path": primary.get("thumb_path", ""),
            "source_url": primary.get("source_url", ""),
            "notes": f"Unified Threat Cluster ({len(all_variants)} linked photo variants)",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "match_count": sum(e.get("match_count", 0) for e in to_merge)
        }

        # Remove merged entries and add master cluster
        self.entries = [e for e in self.entries if e.get("id") not in entry_ids]
        self.entries.append(master_entry)
        self._save_catalog()
        return master_entry

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry and its thumbnails from the visual catalog."""
        orig_len = len(self.entries)
        to_del = [e for e in self.entries if e.get("id") == entry_id]
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        if len(self.entries) < orig_len:
            for d in to_del:
                tp = d.get("thumb_path", "")
                if tp and os.path.exists(tp):
                    try: os.remove(tp)
                    except Exception: pass
                for v in d.get("variants", []):
                    vtp = v.get("thumb_path", "")
                    if vtp and os.path.exists(vtp) and vtp != tp:
                        try: os.remove(vtp)
                        except Exception: pass
            self._save_catalog()
            return True
        return False

    def purge_all_entries(self, entry_type: Optional[str] = None) -> int:
        """Purge all entries (or filtered by type) and permanently clean thumbnail files from disk."""
        if entry_type and entry_type.lower() != "all":
            to_remove = [e for e in self.entries if e.get("type") == entry_type]
            self.entries = [e for e in self.entries if e.get("type") != entry_type]
        else:
            to_remove = list(self.entries)
            self.entries = []

        count = len(to_remove)
        for e in to_remove:
            tp = e.get("thumb_path", "")
            if tp and os.path.exists(tp):
                try: os.remove(tp)
                except Exception: pass
            for v in e.get("variants", []):
                vtp = v.get("thumb_path", "")
                if vtp and os.path.exists(vtp):
                    try: os.remove(vtp)
                    except Exception: pass

        self._save_catalog()
        logger.info(f"Purged {count} entries from visual catalog (type filter: {entry_type})")
        return count

    def match_image(self, target: Image.Image, max_distance: Optional[int] = None) -> Optional[Dict]:
        """
        Match a target PIL Image against the visual catalog.
        Tests against ALL hashes in every cluster entry.
        Returns match dict if Hamming distance <= max_distance (or self.match_threshold), else None.
        """
        if not target or not self.entries:
            return None

        effective_dist = max_distance if max_distance is not None else getattr(self, "match_threshold", 6)
        t_hash = compute_phash(target)
        if not t_hash:
            return None

        best_match = None
        min_dist = 65

        for entry in self.entries:
            hashes_to_check = entry.get("hashes") or [entry.get("hash", "")]
            for e_hash in hashes_to_check:
                if not e_hash:
                    continue
                dist = hamming_distance(t_hash, e_hash)
                if dist <= effective_dist and dist < min_dist:
                    min_dist = dist
                    sim_pct = max(0, int((1.0 - (dist / 64.0)) * 100))
                    best_match = {
                        "id": entry.get("id"),
                        "type": entry.get("type"),
                        "label": entry.get("label"),
                        "distance": dist,
                        "similarity_pct": sim_pct,
                        "thumb_path": entry.get("thumb_path"),
                        "variant_count": len(entry.get("variants", [])) or 1
                    }

        if best_match:
            for entry in self.entries:
                if entry.get("id") == best_match["id"]:
                    entry["match_count"] = entry.get("match_count", 0) + 1
                    break
            self._save_catalog()

        return best_match
