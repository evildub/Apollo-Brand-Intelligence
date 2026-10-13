"""
apollo/core/contracts.py
────────────────────────
Immutable Data Contracts & Schemas for Apollo Brand Intelligence.
Guarantees zero schema drift between Scraper Sentinel, UI Craftsman,
Export Officer, and Compliance Lead.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


@dataclass
class ListingRecord:
    """
    The canonical data contract for a detected marketplace listing.
    Every scraper must return listings compatible with this schema.
    """
    item_id: str
    title: str
    seller: str
    price: str
    marketplace: str
    listing_url: str
    threat_score: int = 0
    threat_level: str = "LOW"
    brand_targeted: str = ""
    infringement_category: str = "Counterfeit / Replica"
    seller_profile_url: str = ""
    location: str = ""
    date_discovered: str = ""
    status: str = "Active"
    evidence_phash: str = ""
    image_url: str = ""
    enforcement_priority: str = "Standard"
    analyst_notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to standardized dictionary format."""
        d = asdict(self)
        # Flatten metadata or ensure legacy dictionary compatibility
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListingRecord":
        """Instantiate record from raw dictionary, handling missing optional fields."""
        return cls(
            item_id=str(data.get("item_id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            seller=str(data.get("seller", "")).strip(),
            price=str(data.get("price", "")).strip(),
            marketplace=str(data.get("marketplace", "")).strip(),
            listing_url=str(data.get("listing_url", data.get("url", ""))).strip(),
            threat_score=int(data.get("threat_score", 0) or 0),
            threat_level=str(data.get("threat_level", "LOW")),
            brand_targeted=str(data.get("brand_targeted", data.get("brand", ""))),
            infringement_category=str(data.get("infringement_category", "Counterfeit / Replica")),
            seller_profile_url=str(data.get("seller_profile_url", "")),
            location=str(data.get("location", "")),
            date_discovered=str(data.get("date_discovered", "")),
            status=str(data.get("status", "Active")),
            evidence_phash=str(data.get("evidence_phash", data.get("phash", ""))),
            image_url=str(data.get("image_url", data.get("thumbnail", ""))),
            enforcement_priority=str(data.get("enforcement_priority", "Standard")),
            analyst_notes=str(data.get("analyst_notes", "")),
            metadata=data.get("metadata", {})
        )


# Canonical 18-Column Export Headers Contract
EXPORT_COLUMNS: List[str] = [
    "Item ID",
    "Title",
    "Seller",
    "Price",
    "Marketplace",
    "Threat Score",
    "Threat Level",
    "Brand Targeted",
    "Infringement Category",
    "Listing URL",
    "Seller Profile URL",
    "Location / Origin",
    "Date Discovered",
    "Status",
    "Evidence Hash (pHash)",
    "Image URL",
    "Enforcement Priority",
    "Analyst Notes",
]
