"""
Artemis Engine — Platform Enforcement Automation & Legal Notice Dispatcher.
Handles generating structured platform notices, batch evidence payloads, and driving
assisted browser portal automation with human-in-the-loop safety.
"""

import os
import sys
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional

class ArtemisEngine:
    def __init__(self, data_store=None):
        from artemis_data_store import ArtemisDataStore
        self.data_store = data_store or ArtemisDataStore()

    def generate_notice_text(self, platform: str, brand_name: str, items: List[Dict[str, Any]]) -> str:
        """Generate formal legal notice text formatted with rights holder info and item listings."""
        rights = self.data_store.get_brand_rights(brand_name) or {}
        rights_holder = rights.get("rights_holder", f"{brand_name} Intellectual Property Holding")
        company_addr = rights.get("company_address", "Corporate Headquarters on Record")
        phone = rights.get("phone_number", "Phone on Record")
        agent = rights.get("authorized_agent", "Authorized Brand Protection Representative")
        email = rights.get("contact_email", "ip-compliance@brandprotection.com")
        tm_regs = ", ".join(rights.get("trademark_regs", [])) or "Registered with USPTO and International Registries"
        cr_regs = ", ".join(rights.get("copyright_regs", [])) or "None specified"
        loa_doc = os.path.basename(rights.get("loa_path", "")) if rights.get("loa_path") else "On File with Designated Representative"
        statement = rights.get("statement", "The listed items display unauthorized reproductions of protected intellectual property.")
        now_str = datetime.now().strftime("%B %d, %Y")

        lines = [
            f"FORMAL NOTICE OF INTELLECTUAL PROPERTY INFRINGEMENT",
            f"Date: {now_str}",
            f"Target Platform: {platform}",
            f"Target Brand / Trademark: {brand_name}",
            f"Rights Owner / Legal Entity: {rights_holder}",
            f"Corporate Address: {company_addr}",
            f"Contact Telephone: {phone}",
            f"Authorized Enforcement Agent: {agent}",
            f"Notice Contact Email: {email}",
            f"Trademark Registration Numbers: {tm_regs}",
            f"Copyright Registration Numbers: {cr_regs}",
            f"Letter of Authorization (LOA): {loa_doc}",
            "",
            "=" * 70,
            "STATEMENT OF AUTHORITY & INFRINGEMENT DECLARATION",
            "=" * 70,
            f"I, the undersigned, declare under penalty of perjury that I am authorized to act",
            f"on behalf of {rights_holder}, the owner of certain intellectual property rights.",
            "",
            statement,
            "",
            "=" * 70,
            f"INFRINGING LISTINGS CATALOG ({len(items)} Items)",
            "=" * 70
        ]

        for idx, it in enumerate(items, 1):
            item_id = it.get("item_id", "N/A")
            seller = it.get("seller", "Unknown Merchant")
            price = it.get("price", "N/A")
            title = it.get("title", "Untitled")
            url = it.get("url", "")
            lines.append(f"[{idx}] Item ID: {item_id} | Merchant: {seller} | Price: {price}")
            lines.append(f"    Title: {title}")
            if url:
                lines.append(f"    Direct URL: {url}")
            lines.append("")

        lines.extend([
            "=" * 70,
            "GOOD FAITH & TRUTHFULNESS CERTIFICATION",
            "=" * 70,
            "I have a good faith belief that the use of the material in the manner complained",
            "of is not authorized by the intellectual property owner, its agent, or the law.",
            "",
            "The information in this notification is accurate, and under penalty of perjury, I am",
            f"authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.",
            "",
            f"Respectfully Submitted,",
            f"{agent}",
            f"For and on behalf of {rights_holder}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ])

        return "\n".join(lines)

    def export_batch_csv(self, items: List[Dict[str, Any]], output_path: str) -> str:
        """Export a batch of infringing items to a clean CSV formatted for marketplace upload."""
        fieldnames = ["Item ID", "Platform", "Brand", "Seller / Merchant", "Price", "Listing Title", "Product URL", "Queued At"]
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for it in items:
                writer.writerow({
                    "Item ID": it.get("item_id", ""),
                    "Platform": it.get("platform", ""),
                    "Brand": it.get("brand", ""),
                    "Seller / Merchant": it.get("seller", ""),
                    "Price": it.get("price", ""),
                    "Listing Title": it.get("title", ""),
                    "Product URL": it.get("url", ""),
                    "Queued At": it.get("queued_at", "")
                })
        return output_path

    def launch_assisted_portal_session(self, platform: str, items: List[Dict[str, Any]], on_status=None) -> bool:
        """Launch an interactive browser session to the designated platform enforcement portal,
        copying relevant Item IDs / ASINs to the system clipboard for immediate pasting."""
        portal_configs = self.data_store.get_portal_configs()
        config = portal_configs.get(platform, {})
        portal_url = config.get("portal_url", "")

        if not portal_url:
            if on_status:
                on_status(f"⚠️ No portal URL configured for {platform}.")
            return False

        # Gather item IDs for clipboard paste
        id_list = [str(it.get("item_id", "")).strip() for it in items if it.get("item_id")]
        formatted_ids = "\n".join(id_list)

        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(formatted_ids)
            r.update()
            r.destroy()
        except Exception:
            pass

        import webbrowser
        try:
            webbrowser.open_new_tab(portal_url)
            if on_status:
                on_status(f"🚀 Launched {platform} portal. {len(id_list)} Item IDs copied to clipboard.")
            return True
        except Exception as e:
            if on_status:
                on_status(f"❌ Failed to launch browser: {e}")
            return False
