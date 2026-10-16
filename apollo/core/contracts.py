"""
apollo/core/contracts.py
────────────────────────
Immutable Data Contracts & Schemas for Apollo Brand Intelligence.
Guarantees zero schema drift between Scraper Sentinel, UI Craftsman,
Export Officer, and Compliance Lead.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List


# Canonical 18-Column Export Headers Contract (Columns A through R)
EXPORT_HEADERS: Dict[str, str] = {
    "A": "Title",
    "B": "URL",
    "C": "Thumbnail",
    "D": "",
    "E": "Item ID",
    "F": "",
    "G": "",
    "H": "Marketplace",
    "I": "",
    "J": "Seller Name",
    "K": "",
    "L": "",
    "M": "Brand",
    "N": "Price",
    "O": "Item Location",
    "P": "Product Type",
    "Q": "Seller Origin (Registered)",
    "R": "Threat Assessment (3PL Hub / Origin)",
}

EXPORT_COLUMNS: List[str] = list(EXPORT_HEADERS.values())


@dataclass
class ListingRecord:
    """
    The canonical data contract for a detected marketplace listing.
    Matches the production dictionary keys used across scrapers, UI Treeview, and ExcelExporter.
    """
    item_id: str
    title: str
    seller: str
    price: str
    marketplace: str
    url: str = ""
    listing_url: str = ""
    image_url: str = ""
    thumbnail: str = ""
    brand: str = ""
    brand_targeted: str = ""
    location: str = ""
    product_type: str = ""
    seller_origin: str = ""
    threat_badge: str = ""
    threat_score: int = 0
    threat_level: str = "LOW"
    infringement_category: str = "Counterfeit / Replica"
    seller_profile_url: str = ""
    date_discovered: str = ""
    status: str = "Active"
    evidence_phash: str = ""
    enforcement_priority: str = "Standard"
    analyst_notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Synchronize canonical and alias fields
        if self.url and not self.listing_url:
            self.listing_url = self.url
        elif self.listing_url and not self.url:
            self.url = self.listing_url

        if self.image_url and not self.thumbnail:
            self.thumbnail = self.image_url
        elif self.thumbnail and not self.image_url:
            self.image_url = self.thumbnail

        if self.brand and not self.brand_targeted:
            self.brand_targeted = self.brand
        elif self.brand_targeted and not self.brand:
            self.brand = self.brand_targeted

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to standardized dictionary format."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListingRecord":
        """Instantiate record from raw dictionary, handling missing optional fields."""
        url_val = str(data.get("url", data.get("listing_url", ""))).strip()
        img_val = str(data.get("image_url", data.get("thumbnail", ""))).strip()
        brand_val = str(data.get("brand", data.get("brand_targeted", ""))).strip()
        return cls(
            item_id=str(data.get("item_id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            seller=str(data.get("seller", "")).strip(),
            price=str(data.get("price", "")).strip(),
            marketplace=str(data.get("marketplace", "")).strip(),
            url=url_val,
            listing_url=url_val,
            image_url=img_val,
            thumbnail=img_val,
            brand=brand_val,
            brand_targeted=brand_val,
            location=str(data.get("location", "")),
            product_type=str(data.get("product_type", "")),
            seller_origin=str(data.get("seller_origin", "")),
            threat_badge=str(data.get("threat_badge", "")),
            threat_score=int(data.get("threat_score", 0) or 0),
            threat_level=str(data.get("threat_level", "LOW")),
            infringement_category=str(data.get("infringement_category", "Counterfeit / Replica")),
            seller_profile_url=str(data.get("seller_profile_url", "")),
            date_discovered=str(data.get("date_discovered", "")),
            status=str(data.get("status", "Active")),
            evidence_phash=str(data.get("evidence_phash", data.get("phash", ""))),
            enforcement_priority=str(data.get("enforcement_priority", "Standard")),
            analyst_notes=str(data.get("analyst_notes", "")),
            metadata=data.get("metadata", {})
        )
