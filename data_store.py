import json
import os
import sys
import shutil
import re
import time
from datetime import datetime

def get_base_dir():
    """Return persistent user AppData directory to guarantee user configurations are never wiped by updates."""
    appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    user_dir = os.path.join(appdata, "Apollo_Brand_Intelligence")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

DATA_FILE = os.path.join(get_base_dir(), "data.json")

DEFAULT_DATA = {
    "settings": {},
    "brands": {
        "Toyota": {
            "subs": {
                "Lexus": ["ES", "RX", "GX", "IS", "LS"]
            },
            "models": ["Camry", "Corolla", "Tacoma", "Tundra", "RAV4",
                       "Highlander", "4Runner", "Prius", "Supra", "Avalon"]
        },
        "General Motors": {
            "subs": {
                "Chevrolet": ["Corvette", "Camaro", "Silverado", "Blazer", "Malibu", "Tahoe", "Suburban"],
                "GMC":       ["Sierra", "Canyon", "Yukon", "Terrain", "Acadia", "Envoy"],
                "Buick":     ["Enclave", "Encore", "Envision", "LaCrosse"],
                "Cadillac":  ["Escalade", "CT5", "CT4", "XT5", "XT6"]
            },
            "models": []
        },
        "Subaru": {
            "subs": {},
            "models": ["Outback", "Forester", "Impreza", "WRX", "Legacy",
                       "Ascent", "Crosstrek", "BRZ", "Solterra"]
        },
        "Hyundai": {
            "subs": {
                "Kia": ["Sportage", "Sorento", "Telluride", "Stinger",
                        "Soul", "Forte", "K5", "Carnival"],
                "Genesis": ["G70", "G80", "G90", "GV70", "GV80"]
            },
            "models": ["Elantra", "Sonata", "Tucson", "Santa Fe",
                       "Palisade", "Kona", "Veloster", "Ioniq"]
        },
        "Nike": {
            "subs": {
                "Jordan": ["Retro 1", "Retro 4", "Retro 11", "Spizike", "Jumpman"],
                "Nike SB": ["Dunk Low", "Dunk High", "Stefan Janoski", "Travis Scott"],
                "Sportswear": ["Tech Fleece", "Club Fleece", "Windrunner", "Center Swoosh"]
            },
            "models": ["Dunk Low", "Air Force 1", "Air Max 90", "Air Max 95", "Air Max Plus TN",
                       "Tech Fleece Hoodie", "Tech Fleece Joggers", "VaporMax", "Cortez", "Blazer Mid", "Vintage Sweatshirt"]
        }
    },
    "exclusions": [
        "Toyota", "Honda", "Ford", "Chevrolet", "Dodge", "Jeep",
        "Nissan", "Mazda", "Mitsubishi", "Volkswagen", "BMW",
        "Mercedes", "Audi", "Hyundai", "Kia", "Subaru",
        "aftermarket", "compatible", "fits"
    ]
}


class DataStore:
    def __init__(self):
        # Initial migration: check if local directory data.json exists and migrate to AppData
        if not os.path.exists(DATA_FILE):
            local_src = os.path.join(os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__), "data.json")
            if os.path.exists(local_src):
                try:
                    shutil.copyfile(local_src, DATA_FILE)
                except Exception:
                    pass

        if os.path.exists(DATA_FILE):
            loaded = None
            for attempt in range(3):
                try:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    break
                except Exception:
                    time.sleep(0.05)
            self._data = loaded if isinstance(loaded, dict) else DEFAULT_DATA

            # migrate old format if needed
            for brand, val in self._data.get("brands", {}).items():
                if not isinstance(val, dict):
                    self._data["brands"][brand] = {"subs": {}, "models": []}
                else:
                    val.setdefault("subs", {})
                    val.setdefault("models", [])
        else:
            self._data = DEFAULT_DATA
            self._save()

    def _save(self):
        tmp_file = f"{DATA_FILE}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, DATA_FILE)
        except Exception:
            try:
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    @property
    def data(self):
        return self._data

    # ── settings ──────────────────────────────────────────────────────────────
    def get_setting(self, key, default=""):
        return self._data.get("settings", {}).get(key, default)

    def set_setting(self, key, value):
        self._data.setdefault("settings", {})[key] = value
        self._save()

    def is_wick_unlocked(self) -> bool:
        return bool(self.get_setting("unlocked_wick", False))

    def unlock_wick(self):
        self.set_setting("unlocked_wick", True)

    def is_brundo_unlocked(self) -> bool:
        return bool(self.get_setting("unlocked_brundo", False))

    def unlock_brundo(self):
        self.set_setting("unlocked_brundo", True)

    def is_fir_unlocked(self) -> bool:
        return bool(self.get_setting("unlocked_fir", False))

    def unlock_fir(self):
        self.set_setting("unlocked_fir", True)

    def is_cowboys_unlocked(self) -> bool:
        return bool(self.get_setting("unlocked_cowboys", False))

    def unlock_cowboys(self):
        self.set_setting("unlocked_cowboys", True)

    # ── brands ────────────────────────────────────────────────────────────────
    def get_brands(self):
        return self._data.get("brands", {})

    def get_all_brands(self):
        return list(self._data.get("brands", {}).keys())

    def add_parent_brand(self, name):
        if name not in self._data["brands"]:
            self._data["brands"][name] = {"subs": {}, "models": [], "inclusions": []}
            self._save()

    def get_brand_inclusions(self, brand_name: str) -> list[str]:
        """Return mandatory brand-specific inclusion terms."""
        brand_data = self._data.get("brands", {}).get(brand_name, {})
        return list(brand_data.get("inclusions", []))

    def set_brand_inclusions(self, brand_name: str, inclusions: list[str]):
        """Persist mandatory brand-specific inclusion terms."""
        if brand_name in self._data.get("brands", {}):
            clean_inc = [str(x).strip() for x in inclusions if str(x).strip()]
            self._data["brands"][brand_name]["inclusions"] = clean_inc
            self._save()

    def update_brand_entry(self, old_name: str, new_name: str, models: list[str] = None, inclusions: list[str] = None):
        """Update brand name, models list, and mandatory inclusion keywords in a single atomic action."""
        if old_name not in self._data.get("brands", {}):
            return
        b_data = self._data["brands"].pop(old_name)
        if models is not None:
            b_data["models"] = [str(m).strip() for m in models if str(m).strip()]
        if inclusions is not None:
            b_data["inclusions"] = [str(inc).strip() for inc in inclusions if str(inc).strip()]
        target_name = new_name.strip() or old_name
        self._data["brands"][target_name] = b_data
        self._save()

    def add_sub_brand(self, parent, name):
        if parent in self._data["brands"]:
            self._data["brands"][parent]["subs"].setdefault(name, [])
            self._save()

    def add_model(self, parent, sub, model):
        try:
            subs = self._data["brands"][parent]["subs"]
            if sub in subs:
                if model not in subs[sub]:
                    subs[sub].append(model)
            else:
                models = self._data["brands"][parent].setdefault("models", [])
                if model not in models:
                    models.append(model)
            self._save()
        except KeyError:
            pass

    def remove_brand_item(self, name):
        """Remove a brand/sub/model by name (searches all levels)."""
        brands = self._data["brands"]
        if name in brands:
            del brands[name]
            self._save()
            return
        for parent, data in brands.items():
            if name in data.get("subs", {}):
                del data["subs"][name]
                self._save()
                return
            if name in data.get("models", []):
                data["models"].remove(name)
                self._save()
                return
            for sub, models in data.get("subs", {}).items():
                if name in models:
                    models.remove(name)
                    self._save()
                    return

    def remove_multiple_brands(self, names: list[str]):
        """Remove multiple brand items in one save operation."""
        for name in names:
            self.remove_brand_item(name)

    def purge_all_brands(self):
        """Permanently purge all brands, sub-brands, models, and inclusions from the Brand Registry."""
        self._data["brands"] = {}
        self._save()

    def reorder_parent_brands(self, new_order: list[str]):
        """Persist new parent brand ordering."""
        new_brands = {}
        for k in new_order:
            if k in self._data["brands"]:
                new_brands[k] = self._data["brands"][k]
        for k, v in self._data["brands"].items():
            if k not in new_brands:
                new_brands[k] = v
        self._data["brands"] = new_brands
        self._save()

    def reorder_models(self, parent_name: str, sub_name: str, new_models: list[str]):
        """Persist new model ordering for a parent or sub-brand."""
        if parent_name in self._data["brands"]:
            if sub_name and sub_name in self._data["brands"][parent_name].get("subs", {}):
                self._data["brands"][parent_name]["subs"][sub_name] = new_models
            else:
                self._data["brands"][parent_name]["models"] = new_models
            self._save()

    def reorder_subs(self, parent_name: str, new_subs: list[str]):
        """Persist new sub-brand ordering under a parent brand."""
        if parent_name in self._data["brands"]:
            existing_subs = self._data["brands"][parent_name].get("subs", {})
            new_sub_dict = {}
            for s in new_subs:
                if s in existing_subs:
                    new_sub_dict[s] = existing_subs[s]
            for s, v in existing_subs.items():
                if s not in new_sub_dict:
                    new_sub_dict[s] = v
            self._data["brands"][parent_name]["subs"] = new_sub_dict
            self._save()

    def get_terms_for_brand(self, brand_name):
        """Return the brand name + all its models as search terms."""
        brands = self._data["brands"]
        terms = [brand_name]
        if brand_name in brands:
            terms.extend(brands[brand_name].get("models", []))
            for sub, models in brands[brand_name].get("subs", {}).items():
                terms.append(sub)
                terms.extend(models)
            return terms
        for parent, data in brands.items():
            if brand_name in data.get("subs", {}):
                terms.extend(data["subs"][brand_name])
                return terms
        return terms

    # ── exclusions ────────────────────────────────────────────────────────────
    def get_exclusions(self):
        return self._data.get("exclusions", [])

    get_generic_exclusions = get_exclusions

    def add_exclusion(self, term):
        if term not in self._data["exclusions"]:
            self._data["exclusions"].append(term)
            self._save()

    def remove_exclusion(self, term):
        if term in self._data["exclusions"]:
            self._data["exclusions"].remove(term)
            self._save()

    # ── Dossier Staging Vault Persistence ──────────────────────────────────────
    def get_staged_dossier(self) -> list:
        """Retrieve staged dossier listings from persistent storage."""
        return list(self._data.get("staged_dossier", []))

    def save_staged_dossier(self, items: list):
        """Persist staged dossier listings to disk."""
        self._data["staged_dossier"] = list(items) if items else []
        self._save()

    def clear_staged_dossier(self):
        """Clear persisted staged dossier."""
        self._data["staged_dossier"] = []
        self._save()

    # ── presets / portfolio bundles ───────────────────────────────────────────
    def get_presets(self):
        default_presets = {
            "🏢 Dub's Automotive Portfolio (Toyota, GM, Subaru, Hyundai/Kia)": [
                "Toyota", "Lexus", "General Motors", "Chevrolet", "ACDelco", "Subaru", "Hyundai", "Kia"
            ],
            "🏁 Toyota & Lexus Full Sweep": [
                "Toyota", "Lexus"
            ],
            "💎 GM & ACDelco Big 4 (Chevy, GMC, Buick, Cadillac, ACDelco)": [
                "General Motors", "Chevrolet", "GMC", "Buick", "Cadillac", "ACDelco"
            ],
            "🔥 MOPAR & Honda Suite (Dodge, Jeep, Honda, Acura)": [
                "Dodge", "Jeep", "Chrysler", "RAM", "Honda", "Acura"
            ],
            "🌐 Complete All-Brands Store Sweep": list(self.get_brands().keys())
        }
        presets = self._data.setdefault("presets", default_presets)
        return presets

    def save_preset(self, name, preset_payload):
        """Save a portfolio preset. Accepts either a list of brands or a full snapshot dict."""
        presets = self.get_presets()
        if isinstance(preset_payload, dict):
            presets[name] = {
                "brands": list(preset_payload.get("brands", [])),
                "generic_excludes": list(preset_payload.get("generic_excludes", [])),
                "custom_includes": list(preset_payload.get("custom_includes", [])),
                "condition": preset_payload.get("condition", "all")
            }
        else:
            presets[name] = list(preset_payload)
        self._data["presets"] = presets
        self._save()

    def delete_preset(self, name):
        presets = self.get_presets()
        if name in presets:
            del presets[name]
            self._data["presets"] = presets
            self._save()

    # ── Enforcement & Recidivism Registry (A2C2 / Brand Protection) ──────────
    def get_enforcement_registry(self):
        return self._data.setdefault("enforcement_registry", {})

    def record_enforcement_scan(self, seller_or_store: str, items: list, brand_name: str = ""):
        """Record harvested results for a seller into the permanent enforcement registry."""
        if not seller_or_store or not seller_or_store.strip():
            return
        seller = seller_or_store.strip()
        reg = self.get_enforcement_registry()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        entry = reg.setdefault(seller, {
            "seller_handle": seller,
            "first_detected": now_str,
            "last_scanned": now_str,
            "total_infringements": 0,
            "total_clean_items": 0,
            "total_value": 0.0,
            "total_listings": 0,
            "items": [],
            "brands_targeted": [],
            "product_types": [],
            "locations": [],
            "country": "Unresolved",
            "threat_badge": "",
            "risk_tier": "Low",
            "historical_scan_count": 0,
            "strike_history": []
        })

        entry["last_scanned"] = now_str
        entry["historical_scan_count"] = entry.get("historical_scan_count", 0) + 1

        if brand_name and brand_name not in entry.get("brands_targeted", []):
            entry.setdefault("brands_targeted", []).append(brand_name)

        existing_items = entry.setdefault("items", [])
        existing_ids = {it.get("item_id") for it in existing_items if it.get("item_id")}
        
        entry_brands = set(entry.get("brands_targeted", []))
        entry_pts = set(entry.get("product_types", []))
        entry_locs = set(entry.get("locations", []))
        
        try:
            current_total_value = float(entry.get("total_value", 0.0) or 0.0)
        except (ValueError, TypeError):
            current_total_value = 0.0

        flagged_items = []
        for itm in items:
            raw_score = itm.get("threat_score", 0)
            try:
                t_score = float(raw_score) if raw_score not in (None, "", "None", "N/A") else 0.0
            except (ValueError, TypeError):
                t_score = 0.0

            is_cf = (
                itm.get("high_risk") or 
                itm.get("counterfeit") or 
                itm.get("visual_counterfeit") or
                t_score >= 70.0 or 
                any(kw in str(itm.get("threat_badge", "")).lower() for kw in ("counterfeit", "syndicate", "flagged", "3pl", "high"))
            )
            if is_cf:
                entry["total_infringements"] = entry.get("total_infringements", 0) + 1
                flagged_items.append({
                    "item_id": itm.get("item_id"),
                    "title": itm.get("title"),
                    "price": itm.get("price"),
                    "threat_score": t_score,
                    "threat_badge": itm.get("threat_badge", ""),
                    "timestamp": now_str
                })
            else:
                entry["total_clean_items"] = entry.get("total_clean_items", 0) + 1

            # Aggregate item cards, prices, and locations
            iid = itm.get("item_id")
            if iid and iid not in existing_ids:
                existing_ids.add(iid)
                existing_items.append(dict(itm))
                
                # Parse numeric price
                p_str = str(itm.get("price", "0"))
                m_p = re.search(r"[\d,]+(?:\.\d+)?", p_str)
                if m_p:
                    try:
                        p_val = float(m_p.group(0).replace(",", ""))
                        current_total_value += p_val
                    except Exception:
                        pass

            b = itm.get("brand")
            if b and b not in ("Unknown", ""): entry_brands.add(b)
            pt = itm.get("product_type")
            if pt and pt not in ("Accessories", ""): entry_pts.add(pt)
            loc = itm.get("location")
            if loc: entry_locs.add(loc)
            
            orig = itm.get("seller_origin") or itm.get("country")
            if orig and orig != "Unknown" and (not entry.get("country") or entry.get("country") == "Unresolved"):
                entry["country"] = orig
            tb = itm.get("threat_badge")
            if tb and not entry.get("threat_badge"):
                entry["threat_badge"] = tb

        entry["total_value"] = round(current_total_value, 2)
        entry["total_listings"] = len(existing_items)
        entry["brands_targeted"] = sorted(list(entry_brands))
        entry["product_types"] = sorted(list(entry_pts))
        entry["locations"] = sorted(list(entry_locs))

        total_bad = entry.get("total_infringements", 0)
        total_good = entry.get("total_clean_items", 0)
        total_all = total_bad + total_good

        if total_bad >= 20 or (total_all > 0 and (total_bad / total_all) >= 0.5 and total_bad >= 5):
            entry["risk_tier"] = "🚨 Critical Recidivist (Syndicate)"
        elif total_bad >= 5:
            entry["risk_tier"] = "⚠ High Risk (Repeat Offender)"
        elif total_bad >= 1:
            entry["risk_tier"] = "🟡 Moderate (Flagged)"
        else:
            entry["risk_tier"] = "🟢 Clean / Low"

        if flagged_items:
            entry.setdefault("strike_history", []).append({
                "scan_date": now_str,
                "flagged_count": len(flagged_items),
                "sample_items": flagged_items[:5]
            })

        self._save()

    def save_enforcement_registry(self, reg_dict: dict):
        """Persist updated enforcement registry dictionary."""
        self._data["enforcement_registry"] = reg_dict
        self._save()

    def delete_registry_entry(self, seller_handle: str):
        """Remove a seller record from the enforcement registry."""
        if not seller_handle:
            return
        reg = self.get_enforcement_registry()
        clean = seller_handle.strip()
        if clean in reg:
            del reg[clean]
            self._save()
        else:
            # Also check case-insensitive match
            for k in list(reg.keys()):
                if k.lower() == clean.lower():
                    del reg[k]
                    self._save()
                    break

    def clear_enforcement_registry(self):
        """Clear all records in the enforcement registry."""
        self._data["enforcement_registry"] = {}
        self._save()

    def get_seller_intel(self, seller_handle: str) -> dict:
        """Retrieve cached threat intel profile for a seller."""
        intel_cache = self._data.setdefault("seller_intel_cache", {})
        return intel_cache.get(seller_handle.strip(), {})

    def set_seller_intel(self, seller_handle: str, country: str, member_since: str = ""):
        """Cache resolved location & age for a seller handle."""
        if not seller_handle or not seller_handle.strip():
            return
        intel_cache = self._data.setdefault("seller_intel_cache", {})
        intel_cache[seller_handle.strip()] = {
            "country": country,
            "member_since": member_since,
            "resolved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save()

    COUNTRY_FLAGS = {
        "china": "🇨🇳", "cn": "🇨🇳", "hong kong": "🇭🇰", "hk": "🇭🇰",
        "united states": "🇺🇸", "us": "🇺🇸", "usa": "🇺🇸",
        "united kingdom": "🇬🇧", "uk": "🇬🇧", "gb": "🇬🇧",
        "france": "🇫🇷", "fr": "🇫🇷",
        "germany": "🇩🇪", "de": "🇩🇪",
        "spain": "🇪🇸", "es": "🇪🇸",
        "italy": "🇮🇹", "it": "🇮🇹",
        "poland": "🇵🇱", "pl": "🇵🇱",
        "mexico": "🇲🇽", "mx": "🇲🇽",
        "brazil": "🇧🇷", "br": "🇧🇷",
        "argentina": "🇦🇷", "ar": "🇦🇷",
        "colombia": "🇨🇴", "co": "🇨🇴",
        "chile": "🇨🇱", "cl": "🇨🇱",
        "peru": "🇵🇪", "pe": "🇵🇪",
        "netherlands": "🇳🇱", "nl": "🇳🇱",
        "belgium": "🇧🇪", "be": "🇧🇪",
        "japan": "🇯🇵", "jp": "🇯🇵",
        "canada": "🇨🇦", "ca": "🇨🇦",
        "australia": "🇦🇺", "au": "🇦🇺",
        "turkey": "🇹🇷", "tr": "🇹🇷",
        "vietnam": "🇻🇳", "vn": "🇻🇳",
        "taiwan": "🇹🇼", "tw": "🇹🇼",
        "thailand": "🇹🇭", "th": "🇹🇭",
        "india": "🇮🇳", "in": "🇮🇳",
    }

    def compute_threat_assessment(self, origin: str, location: str = "", seller_name: str = "") -> dict:
        """
        Compute high-risk cross-border threat badge, burner handle identification, and 3PL hub assessment.
        """
        orig_clean = str(origin or "").strip().lower()
        loc_clean = str(location or "").strip().lower()
        s_name = str(seller_name or "").strip()

        # Burner / disposable machine-generated handle detection (e.g. F20250910190122, ELITEELITE20220923105415, NASCIMENTOANDRE20231123084227)
        is_burner_handle = False
        if s_name and s_name not in ("Mercado Libre Seller", "Unknown", "Unresolved") and not s_name.startswith("MeLi_Seller_"):
            digit_count = sum(c.isdigit() for c in s_name)
            is_burner_handle = bool(
                re.search(r'\d{8,}$', s_name) or
                re.search(r'(?:201\d|202\d|203\d)(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{2,}', s_name) or
                re.search(r'^[a-zA-Z]{1,6}\d{6,}$', s_name) or
                re.search(r'^(?:user|usuario|vendedor|cliente)[_\d-]+$', s_name.lower()) or
                (len(s_name) >= 8 and digit_count >= 6 and (digit_count / len(s_name)) >= 0.45)
            )

        # Foreign high-risk manufacturing / counterfeit syndication hubs
        is_foreign_risk = any(k in orig_clean for k in (
            "china", "cn", "hong kong", "hk", "shenzhen", "guangdong", "zhejiang", "yiwu", "beijing", "shanghai",
            "india", "delhi", "mumbai", "jaipur", "bangalore", "pakistan", "vietnam", "thailand", "taiwan"
        )) or any(k in loc_clean for k in (
            "china", "hong kong", "shenzhen", "guangdong", "yiwu", "beijing", "shanghai", "india", "pakistan"
        ))

        # Domestic delivery & 3PL fulfillment warehouse indicators
        is_domestic_delivery = bool(re.search(
            r'\b(united states|usa|us|california|ca|nj|new jersey|tx|texas|ky|kentucky|uk|united kingdom|germany|de|france|fr|spain|es|italy|it|poland|pl)\b',
            loc_clean
        ))

        is_3pl = is_foreign_risk and is_domestic_delivery

        country_resolved = "Unknown"
        # Prioritize registered origin over item shipping location
        for cname in self.COUNTRY_FLAGS.keys():
            if re.search(r'\b' + re.escape(cname) + r'\b', orig_clean):
                country_resolved = cname.title()
                break
        if country_resolved == "Unknown":
            for cname in self.COUNTRY_FLAGS.keys():
                if re.search(r'\b' + re.escape(cname) + r'\b', loc_clean):
                    country_resolved = cname.title()
                    break

        badge = "❓ Unresolved"
        is_high = False

        if is_burner_handle:
            badge = "🚩 Suspicious Burner Handle"
            is_high = True
        elif is_3pl:
            badge = "🚨 Foreign Drop-Ship Hub"
            is_high = True
        elif is_foreign_risk:
            badge = "⚠ Cross-Border Direct"
            is_high = True
        elif any(c in orig_clean for c in ("mexico", "brazil", "argentina", "colombia", "chile", "peru")):
            badge = "🌎 Latin America Hub"
            is_high = False
        elif any(c in orig_clean for c in ("united kingdom", "uk", "france", "germany", "spain", "italy", "poland", "netherlands", "belgium")):
            badge = "🇪🇺 European Direct"
            is_high = False
        elif bool(re.search(r'\b(united states|usa|us)\b', orig_clean)):
            badge = "🇺🇸 Domestic Verified"
            is_high = False
        elif orig_clean and orig_clean not in ("unknown", "unresolved", ""):
            badge = f"🌍 {country_resolved}"
            is_high = False
        elif loc_clean:
            badge = "❓ Warehouse (Unresolved Origin)"
            is_high = False

        return {
            "country": country_resolved if country_resolved != "Unknown" else (origin or "Unresolved"),
            "badge": badge,
            "is_high_risk": is_high,
            "is_3pl_hub": is_3pl,
            "is_burner_handle": is_burner_handle
        }

    # ── Universal Compatibility Fluff & Multi-Brand Spam Detection ─────────────
    COMPETING_CAR_BRANDS = [
        "toyota", "lexus", "scion", "honda", "acura", "ford", "lincoln",
        "chevrolet", "chevy", "gmc", "cadillac", "buick", "dodge", "ram", "chrysler", "jeep",
        "nissan", "infiniti", "subaru", "hyundai", "kia", "genesis",
        "mazda", "mitsubishi", "volkswagen", "vw", "audi", "porsche",
        "bmw", "mercedes", "benz", "volvo", "land rover", "jaguar"
    ]

    HIGH_RISK_COMPONENTS = [
        "spark plug", "ignition coil", "oil filter", "air filter", "cabin filter",
        "emblem", "badge", "grille logo", "center cap", "wheel cap", "hubcap",
        "key fob", "remote key", "smart key", "key case",
        "oxygen sensor", "o2 sensor", "mass air flow", "maf sensor", "fuel injector", "fuel pump",
        "trd", "hellcat", "mopar", "denso", "brembo", "motorcraft", "acdelco"
    ]

    UNIVERSAL_FLUFF_CATEGORIES = [
        "seat cover", "seat cushion", "floor mat", "trunk mat", "cargo liner",
        "phone holder", "phone mount", "cup holder",
        "windshield sunshade", "sun shade", "sunshade", "car cover", "sunstrip",
        "wiper blade", "wiper refill", "wiper arm",
        "steering wheel cover", "steering wheel wrap",
        "led strip", "interior ambient light", "underglow",
        "air freshener", "diffuser", "perfume",
        "door edge guard", "anti-collision strip", "bumper guard",
        "obd2 scanner", "diagnostic tool", "code reader",
        "blind spot mirror", "trash can", "organizer bag"
    ]

    def is_universal_fluff(self, title: str, product_type: str = "") -> tuple[bool, str]:
        """
        Evaluate if listing is non-enforceable universal accessory fluff or multi-brand title spam.
        CRITICAL: Never suppresses high-risk counterfeit components (plugs, coils, filters, emblems, fobs).
        Returns (is_fluff: bool, reason: str).
        """
        if not title:
            return False, ""
        t_low = title.lower()

        # 1. High-Risk Component Exemption (NEVER SUPPRESS!)
        for comp in self.HIGH_RISK_COMPONENTS:
            if re.search(r'\b' + re.escape(comp) + r'\b', t_low):
                return False, ""

        # 2. Multi-Brand Title Spam (3+ competing car brands in title)
        brand_hits = [b for b in self.COMPETING_CAR_BRANDS if re.search(r'\b' + re.escape(b) + r'\b', t_low)]
        if len(set(brand_hits)) >= 3:
            top_3 = sorted(set(brand_hits))[:3]
            return True, f"Multi-Brand Spam ({len(set(brand_hits))} brands: {', '.join(top_3)})"

        # 3. Compatibility Keyword + Universal Fluff Category
        has_compat = bool(re.search(r'\b(fits|for|compatible with|replacement for|suitable for|pour|para|für|adaptable a)\b', t_low))
        for fluff_cat in self.UNIVERSAL_FLUFF_CATEGORIES:
            if re.search(r'\b' + re.escape(fluff_cat) + r's?\b', t_low):
                if has_compat:
                    return True, f"Universal Compatibility ({fluff_cat.title()})"
                if product_type and fluff_cat in product_type.lower():
                    return True, f"Universal Fluff ({fluff_cat.title()})"

        return False, ""

    def get_column_visibility(self) -> dict:
        """Get column visibility configuration, defaulting to all visible except thumbnail."""
        defaults = {
            "brand": True,
            "product_type": True,
            "title": True,
            "item_id": True,
            "price": True,
            "seller": True,
            "seller_origin": True,
            "threat_badge": True,
            "location": True,
            "thumbnail": False,
            "url": True
        }
        saved = self._data.setdefault("settings", {}).get("column_visibility", {})
        merged = defaults.copy()
        merged.update(saved)
        return merged

    def set_column_visibility(self, visibility_dict: dict):
        """Persist column visibility dictionary."""
        self._data.setdefault("settings", {})["column_visibility"] = visibility_dict
        self._save()

    def set_single_column_visibility(self, col: str, visible: bool):
        """Update single column visibility state."""
        current = self.get_column_visibility()
        current[col] = bool(visible)
        self.set_column_visibility(current)

    def get_show_analyst_hints(self) -> bool:
        """Check if analyst hover onboarding tooltips are enabled."""
        return self._data.setdefault("settings", {}).get("show_analyst_hints", True)

    def set_show_analyst_hints(self, enabled: bool):
        """Set analyst hover onboarding tooltips setting."""
        self._data.setdefault("settings", {})["show_analyst_hints"] = bool(enabled)
        self._save()

    # ── authorized dealer whitelist ───────────────────────────────────────────
    def get_whitelist(self) -> dict:
        """Get dictionary of all whitelisted sellers/dealers."""
        return self._data.setdefault("whitelist", {})

    def is_seller_whitelisted(self, seller_handle: str, marketplace: str = "") -> bool:
        """Check if seller handle is on authorized dealer whitelist, respecting marketplace scope."""
        if not seller_handle:
            return False
        clean = str(seller_handle).strip().lower()
        mp_clean = str(marketplace).strip().lower()
        wl = self.get_whitelist()
        for k, v in wl.items():
            if str(k).strip().lower() == clean:
                target_mp = str(v.get("marketplace", "All Marketplaces")).lower()
                if "all" in target_mp or not mp_clean or target_mp in mp_clean or mp_clean in target_mp:
                    return True
        return False

    def add_to_whitelist(self, seller_handle: str, brand: str = "General", dealer_name: str = "", notes: str = "", marketplace: str = "All Marketplaces"):
        """Add or update an authorized dealer on the whitelist."""
        if not seller_handle:
            return
        clean = str(seller_handle).strip()
        wl = self.get_whitelist()
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        orig_date = wl.get(clean, {}).get("date_added") or wl.get(clean, {}).get("added_at") or now_str

        wl[clean] = {
            "brand": brand or "General",
            "dealer_name": dealer_name or "Authorized Dealership",
            "notes": notes or "",
            "marketplace": marketplace or "All Marketplaces",
            "date_added": orig_date,
            "date_updated": now_str
        }
        self._save()

    def remove_from_whitelist(self, seller_handle: str):
        """Remove a seller from the authorized dealer whitelist."""
        if not seller_handle:
            return
        clean = str(seller_handle).strip().lower()
        wl = self.get_whitelist()
        found_key = None
        for k in wl.keys():
            if str(k).strip().lower() == clean:
                found_key = k
                break
        if found_key and found_key in wl:
            del wl[found_key]
            self._save()

    def get_document_intel_presets(self) -> dict:
        """Return editable document and technical standards presets."""
        defaults = {
            "vehicle_manuals": [
                "service manual", "workshop manual", "wiring diagram",
                "electrical schematic", "repair guide", "factory manual",
                "ECU pinout", "shop manual"
            ],
            "oem_standards": [
                "GMW", "GMW*", "material specification",
                "engineering standard", "test procedure", "WSS-M", "MS-"
            ],
            "benign_exclusions": [
                "10-K", "annual report", "investor presentation",
                "quarterly earnings", "proxy statement", "sustainability report",
                "gamer", "gaming", "workspace", "podcast", "music",
                "casio", "g-shock", "watch", "bezel", "strap"
            ]
        }
        return self._data.get("document_intel", defaults)

    def set_document_intel_presets(self, presets: dict):
        """Update and persist editable document intelligence presets."""
        self._data["document_intel"] = presets
        self._save()

    def get_product_taxonomy(self) -> dict:
        """Return editable product type taxonomy organized by industry."""
        return self._data.get("product_taxonomy", DEFAULT_PRODUCT_TAXONOMY)

    def set_product_taxonomy(self, taxonomy: dict):
        """Persist custom product type taxonomy organized by industry."""
        self._data["product_taxonomy"] = taxonomy
        self._save()

    def reset_product_taxonomy(self) -> dict:
        """Reset product type taxonomy back to factory defaults."""
        self._data["product_taxonomy"] = json.loads(json.dumps(DEFAULT_PRODUCT_TAXONOMY))
        self._save()
        return self._data["product_taxonomy"]

    # ══════════════════════════════════════════════════════════════════════════
    #  CRASH RESILIENCY & LIVE SESSION AUTOSAVE
    # ══════════════════════════════════════════════════════════════════════════
    def get_session_file_path(self) -> str:
        """Return the absolute path to the live autosave session file."""
        return os.path.join(get_base_dir(), "active_session.json")

    def save_active_session(self, results: list, query: str = "", brand: str = "", market: str = "", extra_meta: dict = None) -> bool:
        """Atomically persist current working session to disk to prevent data loss on crash."""
        if not results:
            self.clear_active_session()
            return True
        session_file = self.get_session_file_path()
        tmp_file = session_file + f".tmp.{os.getpid()}"
        payload = {
            "saved_at": datetime.now().isoformat(),
            "query": query,
            "brand": brand,
            "market": market,
            "count": len(results),
            "meta": extra_meta or {},
            "results": results
        }
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(tmp_file, session_file)
            return True
        except Exception:
            try:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            except Exception:
                pass
            return False

    def get_active_session(self) -> dict:
        """Retrieve previously crashed or active un-cleared session if available."""
        session_file = self.get_session_file_path()
        if not os.path.exists(session_file):
            return None
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("results") and isinstance(data["results"], list) and len(data["results"]) > 0:
                return data
        except Exception:
            pass
        return None

    def clear_active_session(self):
        """Clear active session file when user explicitly resets or cleans the results table."""
        session_file = self.get_session_file_path()
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
        except Exception:
            pass


DEFAULT_PRODUCT_TAXONOMY = {
    "🚗 Automotive & Powersports": {
        "Spark Plugs": ["spark plug", "sparkplug", "iridium", "platinum plug"],
        "Headlights / Lamps": ["headlight", "headlamp", "tail light", "fog light", "lamp assembly", "led headlight", "turn signal"],
        "Brake Pads / Rotors": ["brake pad", "brake rotor", "caliper", "brake shoe", "brake disc", "brake kit"],
        "Oil / Fuel Filters": ["oil filter", "fuel filter", "air filter", "cabin filter", "oil strainer"],
        "Ignition Coils": ["ignition coil", "coil pack", "coil-on-plug", "spark coil"],
        "Emblems / Badges": ["emblem", "badge", "logo", "grille emblem", "trunk emblem", "hood ornament", "nameplate"],
        "Key Fobs / Cases": ["key fob", "remote key", "smart key", "key shell", "key case", "transponder key"],
        "Water / Fuel Pumps": ["water pump", "coolant pump", "fuel pump", "high pressure fuel pump"],
        "Oxygen & Air Sensors": ["oxygen sensor", "o2 sensor", "lambda sensor", "maf sensor", "mass air flow", "map sensor"],
        "Turbochargers & Boost": ["turbocharger", "turbo", "wastegate", "blow off valve", "intercooler"],
        "Suspension & Steering": ["control arm", "ball joint", "tie rod", "sway bar", "strut assembly", "shock absorber"]
    },
    "👕 Apparel & Fashion Merch": {
        "T-Shirts & Tops": ["t-shirt", "tee shirt", "tshirt", "graphic tee", "tank top", "crop top", "v-neck"],
        "Hoodies & Sweatshirts": ["hoodie", "sweatshirt", "pullover", "crewneck", "fleece", "sweater"],
        "Hats & Caps": ["hat", "cap", "snapback", "dad hat", "beanie", "trucker hat", "bucket hat", "visor"],
        "Jackets & Outerwear": ["jacket", "coat", "windbreaker", "bomber jacket", "parka", "vest"],
        "Pants & Leggings": ["leggings", "joggers", "sweatpants", "pants", "shorts", "trousers"],
        "Footwear & Shoes": ["shoes", "sneakers", "boots", "slides", "sandals", "loafers", "kicks"],
        "Bags & Backpacks": ["backpack", "tote bag", "duffle bag", "fanny pack", "messenger bag", "crossbody bag", "wallet", "purse"],
        "Jewelry & Watches": ["watch", "bracelet", "necklace", "ring", "earrings", "pendant", "chain", "bezel", "watch glass"]
    },
    "🛠 Tools & Industrial Hardware": {
        "Power Tools": ["cordless drill", "impact driver", "angle grinder", "circular saw", "reciprocating saw", "rotary tool"],
        "Hand Tools": ["wrench", "socket set", "pliers", "screwdriver", "hammer", "ratchet", "hex key", "allen wrench"],
        "Blades & Drill Bits": ["saw blade", "drill bit", "router bit", "carbide blade", "diamond blade"],
        "Measuring & Levels": ["tape measure", "laser level", "caliper", "multimeter", "micrometer"],
        "Hardware & Fasteners": ["screws", "bolts", "nuts", "anchors", "rivets", "washers", "clamps"]
    },
    "🏠 Appliances, Home & Living": {
        "Drinkware & Mugs": ["mug", "coffee mug", "tumbler", "travel mug", "water bottle", "flask", "glassware"],
        "Wall Art & Posters": ["poster", "canvas print", "wall art", "metal print", "art print", "tapestry", "framed print"],
        "Bedding & Pillows": ["pillow", "throw pillow", "cushion", "blanket", "throw blanket", "duvet cover"],
        "Phone Cases & Tech": ["phone case", "iphone case", "samsung case", "airpods case", "laptop sleeve", "mousepad", "desk mat"],
        "Stickers & Decals": ["sticker", "decal", "vinyl sticker", "bumper sticker", "die cut sticker"],
        "Kitchen Appliances": ["air fryer", "blender", "coffee maker", "toaster", "food processor", "microwave"]
    },
    "💊 Pharmaceuticals & Veterinary": {
        "Dewormers & Parasiticides": ["safeguard", "dewormer", "antiparasitario", "ivermectin", "suspension", "paste", "drench", "anthelmintic", "fenbendazole"],
        "Flea, Tick & Pest": ["flea", "tick", "frontline", "bravecto", "seresto", "nexgard", "simparica"],
        "Supplements & Vitamins": ["supplement", "vitamins", "probiotic", "omega 3", "joint support"]
    },
    "📱 Electronics, Audio & Computing": {
        "Headphones & Audio": ["headphones", "earbuds", "wireless earbuds", "bluetooth speaker", "soundbar", "microphone"],
        "Chargers & Power": ["charger", "fast charger", "usb-c cable", "power bank", "magsafe", "charging station"],
        "Computer Components": ["graphics card", "gpu", "cpu", "motherboard", "ram memory", "ssd drive", "power supply"]
    }
}

