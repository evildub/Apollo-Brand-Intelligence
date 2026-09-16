# visual_harvester.py
# Apollo High-Speed Parallel Visual Clone & Threat Dredge Engine

import os
import io
import re
import logging
import urllib.request
import urllib.parse
import concurrent.futures
from typing import List, Dict, Optional
from PIL import Image
from visual_catalog import compute_phash, hamming_distance

logger = logging.getLogger("Apollo.VisualHarvester")

class VisualHarvester:
    """
    High-Speed Reverse Visual Threat Dredge Engine.
    Queries marketplace candidates and mathematically validates each listing's
    photo in parallel via 35 concurrent worker threads using 64-bit DCT pHash.
    """
    def __init__(self, scraper=None, vinted_scraper=None, meli_scraper=None, ali_scraper=None, wish_scraper=None, temu_scraper=None, tiktok_scraper=None, printerval_scraper=None, redbubble_scraper=None):
        self.scraper = scraper
        self.vinted_scraper = vinted_scraper
        self.meli_scraper = meli_scraper
        self.ali_scraper = ali_scraper
        self.wish_scraper = wish_scraper
        self.temu_scraper = temu_scraper
        self.tiktok_scraper = tiktok_scraper
        self.printerval_scraper = printerval_scraper
        self.redbubble_scraper = redbubble_scraper

    def search_by_image(self, image_source, label: str = "", marketplace: str = "eBay",
                        region: Optional[str] = None,
                        max_distance: int = 18, max_results: int = 50, log_callback=None) -> List[Dict]:
        """
        Search for marketplace listings matching the target photo.
        Strictly filters out any candidate whose image pHash does not match within max_distance.
        """
        def _log(msg):
            if log_callback:
                try: log_callback(msg)
                except Exception: pass
            else:
                logger.info(msg)

        # 1. Load target image and compute its pHash
        target_pil = None
        if isinstance(image_source, Image.Image):
            target_pil = image_source
        elif isinstance(image_source, str):
            if os.path.exists(image_source):
                try:
                    target_pil = Image.open(image_source).convert("RGBA")
                except Exception as e:
                    _log(f"Error loading reference image: {e}")
            elif image_source.startswith("http"):
                try:
                    req = urllib.request.Request(image_source, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        target_pil = Image.open(io.BytesIO(r.read())).convert("RGBA")
                except Exception as e:
                    _log(f"Error downloading reference image: {e}")

        if not target_pil:
            _log("❌ Could not load target image for visual comparison.")
            return []

        target_phash = compute_phash(target_pil)
        if not target_phash:
            _log("❌ Failed to compute pHash for target image.")
            return []

        _log(f"📸 Reference pHash: {target_phash} (Tolerance: <={max_distance})")

        # 2. Extract targeted terms from label / part numbers
        query_terms = []
        part_nums = re.findall(r'[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+|\b\d{6,12}\b', label)
        if part_nums:
            query_terms.extend(part_nums)

        clean_label = re.sub(r'[^a-zA-Z0-9\s\-]', '', label).strip()
        words = [w for w in clean_label.split() if len(w) >= 3 and w.lower() not in ("genuine", "original", "oem", "brand", "packaging", "photo", "known", "counterfeit", "benign", "selected", "listing", "visual", "reference", "entry")]
        if words:
            query_terms.append(" ".join(words[:4]))

        if not query_terms:
            if clean_label and len(clean_label) >= 3:
                query_terms = [clean_label[:35]]
            else:
                query_terms = ["Toyota OEM", "Denso", "Spark Plug"]

        mkt_name = marketplace or "eBay"
        loc_str = f" [{region}]" if region else ""
        _log(f"🔍 Harvesting {mkt_name}{loc_str} candidates for '{', '.join(query_terms)}'...")

        # 3. Harvest candidate listings via Appropriate Scraper
        candidates = []
        for q in query_terms[:2]:
            try:
                if "Vinted" in mkt_name and self.vinted_scraper:
                    reg_code = region or "UK"
                    if any(all_w in str(reg_code).lower() for all_w in ("all", "global", "europe")):
                        items = self.vinted_scraper.search_multi_region("", brand_terms=[q], max_pages_per_region=1, log_callback=log_callback)
                    else:
                        items = self.vinted_scraper.scrape_store("", brand_terms=[q], max_pages=2, region_code=reg_code, log_callback=log_callback)
                elif "Mercado" in mkt_name and self.meli_scraper:
                    meli_c = region or "Mexico"
                    items = self.meli_scraper.scrape_store("", brand_terms=[q], max_pages=2, country_name=meli_c, log_callback=log_callback)
                elif "AliExpress" in mkt_name and self.ali_scraper:
                    items = self.ali_scraper.scrape_store("", brand_terms=[q], max_pages=2, log_callback=log_callback)
                elif "Wish" in mkt_name and self.wish_scraper:
                    items = self.wish_scraper.scrape_store("", brand_terms=[q], max_pages=2, log_callback=log_callback)
                elif "Temu" in mkt_name and self.temu_scraper:
                    items = self.temu_scraper.scrape_store("", brand_terms=[q], max_pages=2, log_callback=log_callback)
                elif "Redbubble" in mkt_name and self.redbubble_scraper:
                    items = self.redbubble_scraper.search(q, max_items=50)
                elif "Printerval" in mkt_name and self.printerval_scraper:
                    items = self.printerval_scraper.search(q, max_items=50)
                elif "TikTok" in mkt_name and self.tiktok_scraper:
                    items = self.tiktok_scraper.search("", q, [])
                elif self.scraper:
                    items = self.scraper.search("", q, [], condition="all")
                else:
                    items = []
                candidates.extend(items)
            except Exception as e:
                _log(f"{mkt_name} scraper notice on '{q}': {e}")

        _log(f"⚡ High-Speed Parallel Scan: Analyzing {len(candidates)} {mkt_name} candidates across 35 worker threads...")

        # 4. Parallel pHash Verification on candidates
        verified_matches = []
        seen_ids = set()
        unique_candidates = []
        for cand in candidates:
            item_id = cand.get("item_id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_candidates.append(cand)

        def _verify_worker(cand):
            img_url = cand.get("image_url", "")
            if not img_url:
                return None
            try:
                req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    cand_pil = Image.open(io.BytesIO(r.read())).convert("RGBA")
                cand_phash = compute_phash(cand_pil)
                if not cand_phash:
                    return None

                dist = hamming_distance(target_phash, cand_phash)
                if dist <= max_distance:
                    sim_pct = max(0, int((1.0 - (dist / 64.0)) * 100))
                    if dist <= 6:
                        match_label = f"🎯 Exact Match ({sim_pct}%)"
                        badge_label = f"🚨 Exact Clone ({sim_pct}%)"
                    elif dist <= 12:
                        match_label = f"🖼 Visual Clone ({sim_pct}%)"
                        badge_label = f"🚨 Visual Clone ({sim_pct}%)"
                    else:
                        match_label = f"🔍 Possible Match ({sim_pct}%)"
                        badge_label = f"🔍 Visual Candidate ({sim_pct}%)"

                    cand["similarity"] = match_label
                    cand["match_type"] = match_label
                    cand["threat_badge"] = badge_label
                    cand["threat_score"] = max(cand.get("threat_score", 0), 95 if dist <= 12 else 75)
                    cand["visual_counterfeit"] = True if dist <= 12 else False
                    cand["distance"] = dist
                    cand["sim_pct"] = sim_pct
                    cand["condition"] = f"📸 Visual Match (Dist {dist})"
                    return (cand, dist, sim_pct)
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=35) as executor:
            futures = [executor.submit(_verify_worker, c) for c in unique_candidates]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    res = fut.result()
                    if res:
                        cand, dist, sim_pct = res
                        verified_matches.append(cand)
                        _log(f"  🎯 [MATCH FOUND] {cand.get('title', '')[:42]} | pHash Dist: {dist} ({sim_pct}% match)")
                except Exception:
                    pass

        # Sort matches by similarity (lowest distance first)
        verified_matches.sort(key=lambda x: x.get("distance", 999))

        # 5. Parallel Seller Handle & Origin Enrichment for Discovered Clones
        if verified_matches:
            _log(f"🏪 Enriching real seller handles & origin intel for {len(verified_matches)} visual clone(s)...")
            def _enrich_single_match(m):
                item_url = m.get("url") or (f"https://www.ebay.com/itm/{m.get('item_id', '')}" if m.get("item_id") else "")
                seller_curr = m.get("seller", "")
                if item_url and (not seller_curr or seller_curr in ("eBay Merchant", "Unknown", "Resolving...", "")):
                    try:
                        import batch_importer
                        res = batch_importer.fetch_single_listing(item_url, headless=True)
                        if res:
                            if res.get("seller") and res.get("seller") not in ("Unknown", "eBay Merchant"):
                                m["seller"] = res["seller"]
                            if res.get("price") and res.get("price") not in ("$0.00", ""):
                                m["price"] = res["price"]
                            if res.get("location") and res.get("location") not in ("Unknown", ""):
                                m["location"] = res["location"]
                            if res.get("title") and not res.get("title").startswith("Imported Listing"):
                                m["title"] = res["title"]
                    except Exception as e:
                        logger.debug(f"Visual clone seller enrichment error: {e}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(verified_matches))) as enrich_exec:
                list(enrich_exec.map(_enrich_single_match, verified_matches))

        _log(f"✅ High-Speed Dredge Complete: Found {len(verified_matches)} verified photo clone(s) with resolved merchant profiles.")
        return verified_matches
