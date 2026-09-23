# syndicate_graph.py
# Apollo Brand Intelligence — Cross-Marketplace Syndicate Hunter & Entity Resolution Engine
# Multi-Factor Forensic Linkage: Visual Image pHash, 3PL Dispatch Hubs, Lexical Name Clustering & Catalog Overlap

import os
import re
import math
import logging
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional, Any
from datetime import datetime

logger = logging.getLogger("Apollo.SyndicateGraph")

# Attempt import of visual_catalog pHash utilities
try:
    from visual_catalog import compute_phash, hamming_distance
except ImportError:
    def hamming_distance(hex1: str, hex2: str) -> int:
        try:
            val1 = int(hex1, 16)
            val2 = int(hex2, 16)
            return bin(val1 ^ val2).count("1")
        except Exception:
            return 64

    def compute_phash(img, hash_size=8, highfreq_factor=4) -> str:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# 1. Forensic Normalization Utilities
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_3PL_HUBS = {
    "walnut": "Walnut, CA (Major 3PL Hub)",
    "rowland heights": "Rowland Heights, CA (Major 3PL Hub)",
    "city of industry": "City of Industry, CA (Major 3PL Hub)",
    "chico": "Chico, CA (Major 3PL Hub)",
    "ontario": "Ontario, CA (Inland Empire 3PL Hub)",
    "san leandro": "San Leandro, CA (Bay Area 3PL Hub)",
    "jamaica": "Jamaica, NY (JFK Airport 3PL Air Hub)",
    "dayton": "Dayton, NJ (Tri-State 3PL Hub)",
    "monroe township": "Monroe Township, NJ (Tri-State 3PL Hub)",
    "edison": "Edison, NJ (Tri-State 3PL Hub)",
    "hebron": "Hebron, KY (CVG Airport 3PL Hub)",
    "plainfield": "Plainfield, IN (Midwest Logistics Hub)",
    "memphis": "Memphis, TN (FedEx Logistics Hub)",
    "louisville": "Louisville, KY (UPS Worldport Hub)",
    "shenzhen": "Shenzhen, Guangdong, China",
    "guangzhou": "Guangzhou, Guangdong, China",
    "dongguan": "Dongguan, Guangdong, China",
    "yizheng": "Yizheng, Jiangsu, China",
    "putian": "Putian, Fujian, China (High-Risk Footwear Hub)",
}

HANDLE_COMMON_AFFIXES = [
    "store", "shop", "direct", "official", "mall", "outlet", "us", "usa", "uk",
    "global", "online", "deals", "discount", "super", "top", "best", "pro",
    "tech", "auto", "parts", "trading", "enterprises", "llc", "corp", "inc"
]


def normalize_seller_name(name: str) -> str:
    """Strip punctuation, digits, whitespace, and generic ecommerce affixes."""
    if not name:
        return ""
    clean = name.strip().lower()
    # Remove standard prefixes/suffixes
    clean = re.sub(r"[_\-\.\s]+", "", clean)
    clean = re.sub(r"\d+$", "", clean)  # trailing numbers like seller99 -> seller
    
    # Strip common affixes
    for affix in HANDLE_COMMON_AFFIXES:
        if clean.endswith(affix) and len(clean) > len(affix) + 3:
            clean = clean[:-len(affix)]
        if clean.startswith(affix) and len(clean) > len(affix) + 3:
            clean = clean[len(affix):]
            
    return clean.strip("_-")


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate token and character-level Jaccard/Levenshtein similarity between two seller handles."""
    if not name1 or not name2:
        return 0.0
    n1 = name1.strip().lower()
    n2 = name2.strip().lower()
    if n1 == n2:
        return 1.0

    # Normalized comparison
    norm1 = normalize_seller_name(n1)
    norm2 = normalize_seller_name(n2)
    if norm1 and norm2 and norm1 == norm2:
        return 0.95

    # Bigram Jaccard similarity
    def get_bigrams(s: str) -> Set[str]:
        return {s[i:i+2] for i in range(len(s) - 1)} if len(s) > 1 else {s}

    bg1 = get_bigrams(n1)
    bg2 = get_bigrams(n2)
    intersection = len(bg1 & bg2)
    union = len(bg1 | bg2)
    if union == 0:
        return 0.0
    return intersection / union


GENERIC_NON_HUBS = {
    "united states", "us", "usa", "u.s.", "u.s.a.", "united kingdom", "uk", "u.k.",
    "china", "canada", "ca", "australia", "au", "germany", "de", "france", "fr",
    "italy", "it", "spain", "es", "mexico", "mx", "brazil", "br", "japan", "jp",
    "korea", "kr", "taiwan", "tw", "hong kong", "hk", "poland", "pl", "netherlands", "nl",
    "north america", "europe", "asia", "global", "worldwide", "international", "unknown",
    "n/a", "none", "all", "default", "null"
}


def normalize_dispatch_hub(location_str: str) -> Tuple[str, bool]:
    """
    Normalize location strings into a standardized Hub identifier.
    Returns (normalized_hub_name, is_known_3pl_hub).
    Filters out broad country names (e.g. 'United States', 'US') which are not dispatch hubs.
    """
    if not location_str:
        return ("", False)

    loc_lower = location_str.strip().lower()
    if loc_lower in GENERIC_NON_HUBS:
        return ("", False)

    # Check known 3PL hubs first
    for key, standardized in KNOWN_3PL_HUBS.items():
        if key in loc_lower:
            return (standardized, True)

    # General cleaning: extract city, state, country if possible
    # Examples: "Walnut, California, United States", "Dayton, New Jersey", "Shenzhen, China"
    parts = [p.strip().title() for p in re.split(r"[,/|;]", location_str) if p.strip()]
    if not parts:
        return ("", False)

    # If only 1 part and it's a generic country, discard
    if len(parts) == 1 and parts[0].lower() in GENERIC_NON_HUBS:
        return ("", False)

    # If ending with a country part, remove country part to keep City/State
    if len(parts) >= 2 and parts[-1].lower() in GENERIC_NON_HUBS:
        cleaned_parts = parts[:-1]
    else:
        cleaned_parts = parts

    if not cleaned_parts or (len(cleaned_parts) == 1 and cleaned_parts[0].lower() in GENERIC_NON_HUBS):
        return ("", False)

    cleaned_hub = ", ".join(cleaned_parts[:2])
    if cleaned_hub.lower() in GENERIC_NON_HUBS:
        return ("", False)

    return (cleaned_hub, False)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Graph Nodes & Edge Definitions
# ─────────────────────────────────────────────────────────────────────────────

class LinkEdge:
    """A weighted evidentiary relationship connecting two seller entities."""
    def __init__(self, source_seller: str, target_seller: str, link_type: str, weight: float, evidence: str):
        self.source_seller = source_seller
        self.target_seller = target_seller
        self.link_type = link_type  # 'VISUAL_HASH', 'DISPATCH_HUB', 'NAME_SIMILARITY', 'CATALOG_OVERLAP'
        self.weight = weight        # 0.0 to 1.0
        self.evidence = evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_seller,
            "target": self.target_seller,
            "type": self.link_type,
            "weight": self.weight,
            "evidence": self.evidence
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Discovered Syndicate Cluster Entity
# ─────────────────────────────────────────────────────────────────────────────

class SyndicateCluster:
    """
    Represents an isolated multi-seller syndicate or threat ring discovered by entity resolution.
    """
    def __init__(self, cluster_id: str):
        self.cluster_id = cluster_id
        self.sellers: Set[str] = set()
        self.seller_details: Dict[str, Dict[str, Any]] = {}
        self.items: List[Dict[str, Any]] = []
        self.edges: List[LinkEdge] = []
        self.shared_phash_map: Dict[str, List[str]] = defaultdict(list)  # phash -> [seller1, seller2...]
        self.shared_hubs: Set[str] = set()
        self.known_3pl_hubs: Set[str] = set()
        self.threat_score: int = 50
        self.confidence_tier: str = "👥 Suspected Network"
        self.evidence_summary: List[str] = []

    def compute_metrics_and_score(self):
        """Calculate threat score (0-100) and confidence tier from evidentiary convergence."""
        score = 40  # base cluster score

        has_visual = False
        has_hub = False
        has_name = False
        has_catalog = False

        for edge in self.edges:
            if edge.link_type == "VISUAL_HASH":
                has_visual = True
            elif edge.link_type == "DISPATCH_HUB":
                has_hub = True
            elif edge.link_type == "NAME_SIMILARITY":
                has_name = True
            elif edge.link_type == "CATALOG_OVERLAP":
                has_catalog = True

        # Evidence accumulation
        if has_visual:
            score += 35
            self.evidence_summary.append("📸 Shared Visual Perceptual Hash (Reusing identical product photos)")
        if has_hub:
            score += 20
            hubs_str = ", ".join(list(self.shared_hubs)[:2])
            self.evidence_summary.append(f"📍 Co-Located Dispatch Hub / Drop-Shipping Facility ({hubs_str})")
        if self.known_3pl_hubs:
            score += 10
            known_str = ", ".join(list(self.known_3pl_hubs)[:2])
            self.evidence_summary.append(f"🏢 High-Risk 3PL Forwarding Hub Identified ({known_str})")
        if has_name:
            score += 15
            self.evidence_summary.append("🔤 Systematic Burner Handle / Lexical Name Variant Pattern")
        if has_catalog:
            score += 10
            self.evidence_summary.append("📦 High Duplicate Catalog / Model Cross-Listing Overlap")

        # Multi-seller volume scale
        if len(self.sellers) >= 4:
            score += 10
        elif len(self.sellers) >= 2:
            score += 5

        self.threat_score = min(99, max(25, score))

        # Determine confidence tier
        if self.threat_score >= 90:
            self.confidence_tier = "🚨 Confirmed Syndicate"
        elif self.threat_score >= 75:
            self.confidence_tier = "⚡ Probable Threat Ring"
        else:
            self.confidence_tier = "👥 Suspected Network"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "threat_score": self.threat_score,
            "confidence_tier": self.confidence_tier,
            "seller_count": len(self.sellers),
            "sellers": list(self.sellers),
            "seller_details": self.seller_details,
            "item_count": len(self.items),
            "shared_hubs": list(self.shared_hubs),
            "known_3pl_hubs": list(self.known_3pl_hubs),
            "evidence_summary": self.evidence_summary,
            "edges": [e.to_dict() for e in self.edges]
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Master Syndicate Hunter & Entity Resolution Engine
# ─────────────────────────────────────────────────────────────────────────────

class SyndicateGraph:
    """
    Cross-Marketplace Entity Resolution Engine.
    Clusters seller entities across 4 evidentiary vectors:
      1. Visual Asset pHash Collisions (Hamming distance <= threshold)
      2. 3PL Fulfillment & Dispatch Location Co-Location
      3. Handle Lexical Pattern / Burner Syntax Matching
      4. Catalog Duplicate Title & Pricing Overlap
    """
    def __init__(self, phash_threshold: int = 6):
        self.phash_threshold = phash_threshold
        self.clusters: List[SyndicateCluster] = []
        self.seller_to_cluster: Dict[str, SyndicateCluster] = {}
        self.raw_items: List[Dict[str, Any]] = []

    def analyze_listings(self, listings: List[Dict[str, Any]]) -> List[SyndicateCluster]:
        """
        Execute full multi-factor entity resolution over an arbitrary list of scraped items.
        Returns a ranked list of detected SyndicateCluster objects sorted by Threat Score.
        """
        self.raw_items = listings or []
        self.clusters = []
        self.seller_to_cluster = {}

        if not self.raw_items:
            return []

        # ── Step A: Group items and metadata by seller ────────────────────────
        seller_items: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        seller_meta: Dict[str, Dict[str, Any]] = {}

        for item in self.raw_items:
            seller = item.get("seller") or "Unknown"
            if not seller or seller.lower() in ("unknown", "n/a", "none", ""):
                continue
            seller_items[seller].append(item)

            if seller not in seller_meta:
                loc_raw = item.get("location") or item.get("origin") or ""
                norm_hub, is_3pl = normalize_dispatch_hub(loc_raw)
                seller_meta[seller] = {
                    "seller": seller,
                    "marketplace": item.get("marketplace") or item.get("source") or "eBay",
                    "origin": item.get("origin") or "N/A",
                    "location": loc_raw,
                    "normalized_hub": norm_hub,
                    "is_3pl": is_3pl,
                    "items": [],
                    "phashes": set()
                }

            # Collect item pHash if available
            phash = item.get("phash") or item.get("image_hash") or ""
            if phash:
                seller_meta[seller]["phashes"].add(phash)

        sellers = list(seller_items.keys())
        if len(sellers) < 2:
            return []

        # ── Step B: Build Disjoint Set (Union-Find) Graph ─────────────────────
        parent = {s: s for s in sellers}

        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        edges_between: List[LinkEdge] = []

        # ── Vector 1: Visual Image pHash Collisions ──────────────────────────
        # Check every pair of sellers for matching image hashes
        seller_hash_tuples: List[Tuple[str, str, Dict[str, Any]]] = []
        for seller, items in seller_items.items():
            for item in items:
                ph = item.get("phash") or item.get("image_hash") or ""
                if ph and len(ph) >= 8:
                    seller_hash_tuples.append((seller, ph, item))

        for idx, (s1, ph1, item1) in enumerate(seller_hash_tuples):
            for s2, ph2, item2 in seller_hash_tuples[idx + 1:]:
                if s1 == s2:
                    continue
                dist = hamming_distance(ph1, ph2)
                if dist <= self.phash_threshold:
                    weight = 1.0 - (dist / float(self.phash_threshold + 1))
                    ev = f"Visual match (Hamming distance {dist} <= {self.phash_threshold}): '{item1.get('title', '')[:30]}...' vs '{item2.get('title', '')[:30]}...'"
                    edges_between.append(LinkEdge(s1, s2, "VISUAL_HASH", weight, ev))
                    union(s1, s2)

        # ── Vector 2: Dispatch Hub & 3PL Warehouse Co-Location ────────────────
        hub_to_sellers: Dict[str, Set[str]] = defaultdict(set)
        for s in sellers:
            hub = seller_meta[s]["normalized_hub"]
            if hub and len(hub) > 3:
                hub_to_sellers[hub].add(s)

        for hub, hub_sellers in hub_to_sellers.items():
            if len(hub_sellers) >= 2:
                s_list = list(hub_sellers)
                for i in range(len(s_list)):
                    for j in range(i + 1, len(s_list)):
                        s1, s2 = s_list[i], s_list[j]
                        is_3pl = seller_meta[s1]["is_3pl"] or seller_meta[s2]["is_3pl"]
                        if is_3pl:
                            w = 0.95
                            ev = f"Co-located high-risk 3PL fulfillment facility: {hub}"
                            edges_between.append(LinkEdge(s1, s2, "DISPATCH_HUB", w, ev))
                            union(s1, s2)
                        else:
                            # General geographic hubs require corroboration (e.g. handle similarity or shared visual asset)
                            sim = calculate_name_similarity(s1, s2)
                            if sim >= 0.55:
                                w = 0.75
                                ev = f"Co-located dispatch hub ({hub}) corroborated by handle pattern ({int(sim*100)}%)"
                                edges_between.append(LinkEdge(s1, s2, "DISPATCH_HUB", w, ev))
                                union(s1, s2)

        # ── Vector 3: Lexical Handle Syntax & Burner Account Patterns ─────────
        for i in range(len(sellers)):
            for j in range(i + 1, len(sellers)):
                s1, s2 = sellers[i], sellers[j]
                sim = calculate_name_similarity(s1, s2)
                if sim >= 0.85:
                    ev = f"Lexical handle correlation ({int(sim*100)}% match): '{s1}' ↔ '{s2}'"
                    edges_between.append(LinkEdge(s1, s2, "NAME_SIMILARITY", sim, ev))
                    union(s1, s2)

        # ── Step C: Form Clusters from Connected Components ──────────────────
        component_sellers: Dict[str, Set[str]] = defaultdict(set)
        for s in sellers:
            root = find(s)
            component_sellers[root].add(s)

        # Filter out single-seller components (we only care about multi-seller networks)
        cluster_idx = 1
        for root, ring_sellers in component_sellers.items():
            if len(ring_sellers) < 2:
                continue

            cluster = SyndicateCluster(f"SYN-{cluster_idx:03d}")
            cluster.sellers = ring_sellers

            for s in ring_sellers:
                cluster.seller_details[s] = seller_meta[s]
                cluster.items.extend(seller_items[s])
                hub = seller_meta[s]["normalized_hub"]
                if hub:
                    cluster.shared_hubs.add(hub)
                if seller_meta[s]["is_3pl"]:
                    cluster.known_3pl_hubs.add(hub)

            # Assign associated edges
            for edge in edges_between:
                if edge.source_seller in ring_sellers and edge.target_seller in ring_sellers:
                    cluster.edges.append(edge)

            cluster.compute_metrics_and_score()
            self.clusters.append(cluster)
            for s in ring_sellers:
                self.seller_to_cluster[s] = cluster

            cluster_idx += 1

        # Sort clusters by threat score descending
        self.clusters.sort(key=lambda c: (c.threat_score, len(c.sellers), len(c.items)), reverse=True)
        return self.clusters

    def find_syndicate_for_seller(self, seller_name: str) -> Optional[SyndicateCluster]:
        """Find the syndicate cluster containing a specific seller, if any."""
        if not seller_name:
            return None
        return self.seller_to_cluster.get(seller_name)

    def export_genesis_records(self) -> List[Dict[str, Any]]:
        """Format discovered syndicates into structured enterprise records for Genesis / Legal export."""
        records = []
        for cluster in self.clusters:
            for s in cluster.sellers:
                meta = cluster.seller_details.get(s, {})
                for item in meta.get("items", []) or [i for i in cluster.items if i.get("seller") == s]:
                    records.append({
                        "Syndicate ID": cluster.cluster_id,
                        "Threat Score": cluster.threat_score,
                        "Confidence Tier": cluster.confidence_tier,
                        "Seller Handle": s,
                        "Marketplace": meta.get("marketplace", "eBay"),
                        "Dispatch Hub": meta.get("normalized_hub", ""),
                        "3PL Hub Flag": "YES" if meta.get("is_3pl") else "NO",
                        "Item Title": item.get("title", ""),
                        "Item ID": item.get("item_id", ""),
                        "Price": item.get("price", ""),
                        "URL": item.get("url", ""),
                        "Evidence Summary": " | ".join(cluster.evidence_summary)
                    })
        return records
