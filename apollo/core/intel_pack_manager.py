# intel_pack_manager.py
# Apollo Brand Intelligence — Analyst Intelligence Pack (.apollo) Exporter & Importer
# Enables seamless sharing of brand portfolios, exclusion filters, authorized dealer whitelists,
# and visual threat packaging catalogs across analysts and workstations.

import os
import io
import json
import zipfile
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("Apollo.IntelPack")

class IntelPackManager:
    """Handles packaging, export, inspection, and safe merging of .apollo intelligence bundles."""

    @staticmethod
    def export_pack(
        output_filepath: str,
        data_store,
        visual_catalog,
        scope: str = "Full Profile",
        selected_brands: Optional[List[str]] = None,
        author: str = "Apollo Analyst",
        notes: str = ""
    ) -> Dict:
        """
        Export selected intelligence components into a self-contained .apollo (zip) bundle.
        """
        all_brands = data_store.get_brands() if data_store else {}
        all_presets = data_store.get_presets() if data_store else {}
        all_exclusions = data_store.get_generic_exclusions() if data_store else []
        all_whitelist = data_store.get_whitelist() if data_store else {}
        all_visual = visual_catalog.get_all_entries() if visual_catalog else []

        # Filter by selected brand if scoped
        export_brands = {}
        export_presets = {}
        export_whitelist = {}
        export_visual = []

        if scope == "Full Profile" or not selected_brands:
            export_brands = all_brands
            export_presets = all_presets
            export_whitelist = all_whitelist
            export_visual = all_visual
        else:
            sel_lowers = [b.lower().strip() for b in selected_brands]
            # Brands
            for b_name, b_data in all_brands.items():
                if b_name.lower().strip() in sel_lowers:
                    export_brands[b_name] = b_data

            # Presets
            for p_name, p_data in all_presets.items():
                p_brands = p_data.get("brands", [])
                if any(b.lower().strip() in sel_lowers for b in p_brands):
                    export_presets[p_name] = p_data

            # Whitelist
            for w_handle, w_data in all_whitelist.items():
                if str(w_data.get("brand", "")).lower().strip() in sel_lowers:
                    export_whitelist[w_handle] = w_data

            # Visual Catalog
            for v_entry in all_visual:
                v_lbl = str(v_entry.get("label", "")).lower()
                if any(b in v_lbl for b in sel_lowers) or scope == "Visual Library Only":
                    export_visual.append(v_entry)

        # Collect thumbnail image files to bundle
        thumbs_to_pack = {}
        if visual_catalog and hasattr(visual_catalog, "thumbs_dir"):
            v_dir = visual_catalog.thumbs_dir
            for entry in export_visual:
                tp = entry.get("thumb_path", "")
                if tp and os.path.exists(tp):
                    fn = os.path.basename(tp)
                    thumbs_to_pack[fn] = tp
                for v in entry.get("variants", []):
                    vtp = v.get("thumb_path", "")
                    if vtp and os.path.exists(vtp):
                        vfn = os.path.basename(vtp)
                        thumbs_to_pack[vfn] = vtp

        manifest = {
            "format": "apollo_intelligence_pack",
            "version": "1.0",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "author": author,
            "scope": scope,
            "selected_brands": selected_brands or list(export_brands.keys()),
            "notes": notes,
            "counts": {
                "brands": len(export_brands),
                "presets": len(export_presets),
                "exclusions": len(all_exclusions),
                "whitelist_dealers": len(export_whitelist),
                "visual_catalog_entries": len(export_visual),
                "visual_thumbnails": len(thumbs_to_pack)
            }
        }

        # Write zip bundle
        with zipfile.ZipFile(output_filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("brands.json", json.dumps(export_brands, indent=2))
            zf.writestr("presets.json", json.dumps(export_presets, indent=2))
            zf.writestr("exclusions.json", json.dumps(all_exclusions, indent=2))
            zf.writestr("whitelist.json", json.dumps(export_whitelist, indent=2))
            zf.writestr("visual_catalog.json", json.dumps(export_visual, indent=2))

            for fn, src_path in thumbs_to_pack.items():
                try:
                    zf.write(src_path, arcname=f"thumbs/{fn}")
                except Exception as e:
                    logger.debug(f"Failed to bundle thumbnail {fn}: {e}")

        logger.info(f"Exported Apollo Intelligence Pack ({scope}) to {output_filepath}")
        return manifest

    @staticmethod
    def inspect_pack(pack_filepath: str) -> Dict:
        """Read manifest and summary of an .apollo package without importing."""
        if not os.path.exists(pack_filepath) or not zipfile.is_zipfile(pack_filepath):
            raise ValueError("Invalid or corrupted .apollo intelligence package.")

        with zipfile.ZipFile(pack_filepath, "r") as zf:
            if "manifest.json" not in zf.namelist():
                raise ValueError("Package missing manifest.json.")
            raw_man = zf.read("manifest.json").decode("utf-8")
            return json.loads(raw_man)

    @staticmethod
    def import_pack(
        pack_filepath: str,
        data_store,
        visual_catalog,
        merge_mode: str = "merge"  # "merge" or "replace"
    ) -> Dict:
        """
        Import intelligence components from an .apollo bundle into local storage.
        """
        if not os.path.exists(pack_filepath) or not zipfile.is_zipfile(pack_filepath):
            raise ValueError("Invalid or corrupted .apollo intelligence package.")

        manifest = IntelPackManager.inspect_pack(pack_filepath)
        results = {
            "brands_added": 0,
            "presets_added": 0,
            "exclusions_added": 0,
            "whitelist_added": 0,
            "visual_added": 0,
            "thumbnails_extracted": 0
        }

        with zipfile.ZipFile(pack_filepath, "r") as zf:
            names = zf.namelist()

            # 1. Extract Thumbnails
            target_thumbs_dir = visual_catalog.thumbs_dir if visual_catalog and hasattr(visual_catalog, "thumbs_dir") else ""
            if target_thumbs_dir:
                os.makedirs(target_thumbs_dir, exist_ok=True)
                for n in names:
                    if n.startswith("thumbs/") and not n.endswith("/"):
                        fn = os.path.basename(n)
                        dst_fp = os.path.join(target_thumbs_dir, fn)
                        try:
                            with zf.open(n) as src, open(dst_fp, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            results["thumbnails_extracted"] += 1
                        except Exception as e:
                            logger.debug(f"Failed extracting thumb {fn}: {e}")

            # 2. Brands
            if "brands.json" in names and data_store:
                try:
                    pack_brands = json.loads(zf.read("brands.json").decode("utf-8"))
                    if merge_mode == "replace":
                        data_store._data["brands"] = pack_brands
                        results["brands_added"] = len(pack_brands)
                    else:
                        curr_brands = data_store.get_brands()
                        for b_name, b_data in pack_brands.items():
                            if b_name not in curr_brands:
                                curr_brands[b_name] = b_data
                                results["brands_added"] += 1
                            else:
                                # Merge models & sub-brands & inclusion terms
                                existing = curr_brands[b_name]
                                for m in b_data.get("models", []):
                                    if m not in existing.get("models", []):
                                        existing.setdefault("models", []).append(m)
                                for inc in b_data.get("inclusions", []):
                                    if inc not in existing.get("inclusions", []):
                                        existing.setdefault("inclusions", []).append(inc)
                                for sub, sub_m in b_data.get("subs", {}).items():
                                    if sub not in existing.setdefault("subs", {}):
                                        existing["subs"][sub] = sub_m
                                    else:
                                        for sm in sub_m:
                                            if sm not in existing["subs"][sub]:
                                                existing["subs"][sub].append(sm)
                        data_store._data["brands"] = curr_brands
                except Exception as e:
                    logger.error(f"Failed to import brands from pack: {e}")

            # 3. Presets
            if "presets.json" in names and data_store:
                try:
                    pack_presets = json.loads(zf.read("presets.json").decode("utf-8"))
                    curr_presets = data_store.get_presets()
                    if merge_mode == "replace":
                        curr_presets.update(pack_presets)
                        results["presets_added"] = len(pack_presets)
                    else:
                        for p_name, p_data in pack_presets.items():
                            curr_presets[p_name] = p_data
                            results["presets_added"] += 1
                    data_store._data["presets"] = curr_presets
                except Exception as e:
                    logger.error(f"Failed to import presets from pack: {e}")

            # 4. Exclusions
            if "exclusions.json" in names and data_store:
                try:
                    pack_ex = json.loads(zf.read("exclusions.json").decode("utf-8"))
                    curr_ex = set(data_store.get_exclusions())
                    before_len = len(curr_ex)
                    curr_ex.update(pack_ex)
                    data_store._data["exclusions"] = sorted(list(curr_ex))
                    results["exclusions_added"] = len(curr_ex) - before_len
                except Exception as e:
                    logger.error(f"Failed to import exclusions from pack: {e}")

            # 5. Whitelist
            if "whitelist.json" in names and data_store:
                try:
                    pack_wl = json.loads(zf.read("whitelist.json").decode("utf-8"))
                    curr_wl = data_store.get_whitelist()
                    for h, d in pack_wl.items():
                        if h not in curr_wl or merge_mode == "replace":
                            curr_wl[h] = d
                            results["whitelist_added"] += 1
                    data_store._data["whitelist"] = curr_wl
                except Exception as e:
                    logger.error(f"Failed to import whitelist from pack: {e}")

            # Save data_store changes
            if data_store:
                data_store._save()

            # 6. Visual Catalog
            if "visual_catalog.json" in names and visual_catalog:
                pack_vis = json.loads(zf.read("visual_catalog.json").decode("utf-8"))
                curr_entries = visual_catalog.get_all_entries()
                curr_hashes = set()
                for ce in curr_entries:
                    for h in (ce.get("hashes") or [ce.get("hash", "")]):
                        if h: curr_hashes.add(h)

                for ve in pack_vis:
                    vh = ve.get("hash", "")
                    # Adjust thumb path to local directory
                    old_tp = ve.get("thumb_path", "")
                    if old_tp:
                        fn = os.path.basename(old_tp)
                        ve["thumb_path"] = os.path.join(visual_catalog.thumbs_dir, fn)
                    for v in ve.get("variants", []):
                        v_old = v.get("thumb_path", "")
                        if v_old:
                            v_fn = os.path.basename(v_old)
                            v["thumb_path"] = os.path.join(visual_catalog.thumbs_dir, v_fn)

                    if vh not in curr_hashes or merge_mode == "replace":
                        curr_entries.append(ve)
                        curr_hashes.add(vh)
                        results["visual_added"] += 1

                visual_catalog.entries = curr_entries
                visual_catalog._save_catalog()

        logger.info(f"Imported Apollo Intelligence Pack: {results}")
        return {
            "manifest": manifest,
            "results": results
        }
