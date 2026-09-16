import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from collections import defaultdict


# ── Required column layout ────────────────────────────────────────────────────
# A  = Title
# B  = URL
# C  = Thumbnail (image URL)
# D  = (blank spacer)
# E  = Item ID
# F  = (blank)
# G  = (blank)
# H  = Marketplace
# I  = (blank)
# J  = Seller Name
# K  = (blank)
# L  = (blank)
# M  = Brand
# N  = Price   ← extra, added at end of required cols

HEADERS = {
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

HEADER_FILL  = PatternFill("solid", fgColor="2B2D42")
HEADER_FONT  = Font(bold=True, color="FFFFFF", name="Segoe UI", size=10)

def normalize_marketplace_code(mkt: str) -> str:
    """
    Ensure enterprise marketplace codes strictly adhere to client intake formatting and Genesis specifications.
    Strips all icons/emojis, whitespace, and normalizes canonical domain names (e.g. ebay.com, redbubble.com, printerval.com).
    """
    if not mkt:
        return MARKETPLACE

    raw_str = str(mkt).strip()
    # Remove leading/trailing emojis and non-alphanumeric symbols
    clean = re.sub(r'^[^\w\.\-]+|[^\w\.\-]+$', '', raw_str).strip()
    m = clean.lower()

    # 1. eBay & Regional Variations
    if any(k in m for k in ("cafr.ebay.ca", "cafr", "ca_fr", "canada (french)", "canada french", "ebay.ca (french)", "ebay.ca/cafr")):
        return "ebay.ca - cafr"
    if "ebay.co.uk" in m or ("uk" in m and "ebay" in m):
        return "ebay.co.uk"
    if "ebay.de" in m or ("germany" in m and "ebay" in m):
        return "ebay.de"
    if "ebay.ca" in m:
        return "ebay.ca"
    if "ebay.fr" in m:
        return "ebay.fr"
    if "ebay.it" in m:
        return "ebay.it"
    if "ebay.es" in m:
        return "ebay.es"
    if "ebay.com.au" in m or ("australia" in m and "ebay" in m):
        return "ebay.com.au"
    if "ebay.nl" in m:
        return "ebay.nl"
    if "ebay.pl" in m:
        return "ebay.pl"
    if "ebay.ch" in m:
        return "ebay.ch"
    if "ebay.at" in m:
        return "ebay.at"
    if "ebay.ie" in m:
        return "ebay.ie"
    if "ebay" in m:
        return "ebay.com"

    # 2. POD Platforms
    if "redbubble" in m:
        return "redbubble.com"
    if "printerval" in m:
        return "printerval.com"

    # 3. Global Retail & Social Marketplaces
    if "tiktok" in m:
        return "shop.tiktok.com"
    if "aliexpress" in m or m == "ali":
        return "aliexpress.com"
    if "wish" in m:
        return "wish.com"
    if "temu" in m:
        return "temu.com"
    if "scribd" in m:
        return "scribd.com"

    # 4. ManoMano Locales
    if "manomano" in m:
        if "es" in m or "spain" in m:
            return "manomano.es"
        if "de" in m or "germany" in m:
            return "manomano.de"
        if "it" in m or "italy" in m:
            return "manomano.it"
        if "uk" in m or "co.uk" in m:
            return "manomano.co.uk"
        return "manomano.fr"

    # 5. Vinted Locales
    if "vinted" in m:
        if "fr" in m or "france" in m:
            return "vinted.fr"
        if "de" in m or "germany" in m:
            return "vinted.de"
        if "es" in m or "spain" in m:
            return "vinted.es"
        if "it" in m or "italy" in m:
            return "vinted.it"
        if "pl" in m or "poland" in m:
            return "vinted.pl"
        if "com" in m or "us" in m:
            return "vinted.com"
        return "vinted.co.uk"

    # 6. Mercado Libre Regional Domains
    if any(k in m for k in ("mercadolibre", "mercadolivre", "mercado", "meli")):
        if any(k in m for k in ("brazil", "brasil", "livre", "mlb", ".com.br")):
            return "mercadolivre.com.br"
        if any(k in m for k in ("argentina", "mla", ".com.ar")):
            return "mercadolibre.com.ar"
        if any(k in m for k in ("colombia", "mco", ".com.co")):
            return "mercadolibre.com.co"
        if any(k in m for k in ("chile", "mlc", ".cl")):
            return "mercadolibre.cl"
        if any(k in m for k in ("peru", "mpe", ".com.pe")):
            return "mercadolibre.com.pe"
        if any(k in m for k in ("uruguay", "mlu", ".com.uy")):
            return "mercadolibre.com.uy"
        return "listado.mercadolibre.com.mx"

    if "." in clean:
        return clean.lower()
    return f"{clean.lower()}.com" if clean else MARKETPLACE
ROW_FILL_A   = PatternFill("solid", fgColor="F8F8F2")
ROW_FILL_B   = PatternFill("solid", fgColor="EEEEEE")
BORDER_SIDE  = Side(style="thin", color="CCCCCC")
THIN_BORDER  = Border(bottom=BORDER_SIDE)

COL_WIDTHS = {
    "A": 55,   # Title
    "B": 50,   # URL
    "C": 45,   # Thumbnail
    "E": 16,   # Item ID
    "H": 14,   # Marketplace
    "J": 22,   # Seller
    "M": 18,   # Brand
    "N": 12,   # Price
    "O": 24,   # Item Location
    "P": 22,   # Product Type
    "Q": 22,   # Seller Origin
    "R": 38,   # Threat Assessment
}

MARKETPLACE = "ebay.com"


class ExcelExporter:
    def export(self, results: list[dict], filepath: str):
        """
        Export results to Excel.
        Tab 1: Master (All Results) containing 100% of harvested listings.
        Tabs 2+: Dedicated sheets per brand (grouped by item['brand']).
        """
        wb = openpyxl.Workbook()
        wb.properties.creator = "Jerry Seidenstucker"
        wb.properties.title = "Apollo Enforcement Harvester Report"
        wb.properties.description = "Generated by Apollo Brand Intelligence (Created by Jerry Seidenstucker)"
        wb.remove(wb.active)   # remove default sheet

        # 1. Tab 1: Master Sheet (All Listings)
        ws_all = wb.create_sheet(title="All Results")
        self._write_sheet(ws_all, results, "All Results", is_master=True)

        # 2. Tabs 2+: Dedicated Brand Tabs
        by_brand = defaultdict(list)
        for item in results:
            b = item.get("brand", "Unassigned")
            if not b or b == "Unknown":
                b = "Unassigned"
            by_brand[b].append(item)

        for brand, items in by_brand.items():
            ws = wb.create_sheet(title=self._safe_sheet_name(brand))
            self._write_sheet(ws, items, brand, is_master=False)

        wb.save(filepath)
        return len(results)

    export_results = export

    # ── sheet writer ──────────────────────────────────────────────────────────
    def _write_sheet(self, ws, items: list[dict], brand: str, is_master: bool = False):
        ws.views.sheetView[0].showGridLines = True
        # header row
        for col_letter, header_text in HEADERS.items():
            col_idx = openpyxl.utils.column_index_from_string(col_letter)
            cell = ws.cell(row=1, column=col_idx, value=header_text)
            cell.font  = HEADER_FONT
            cell.fill  = HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[1].height = 20

        # data rows (start at row 2)
        for row_num, item in enumerate(items, start=2):
            fill = ROW_FILL_A if row_num % 2 == 0 else ROW_FILL_B

            def cell(col_letter, value):
                idx  = openpyxl.utils.column_index_from_string(col_letter)
                c    = ws.cell(row=row_num, column=idx, value=value)
                c.fill = fill
                c.alignment = Alignment(vertical="center", wrap_text=False)
                c.border = THIN_BORDER
                return c

            title_cell = cell("A", item.get("title", ""))
            title_cell.font = Font(name="Segoe UI", size=9)

            url = item.get("url", "")
            url_cell = cell("B", url)
            if url:
                url_cell.hyperlink = url
                url_cell.font = Font(color="0563C1", underline="single",
                                     name="Segoe UI", size=9)
            else:
                url_cell.font = Font(name="Segoe UI", size=9)

            img_url = item.get("image_url", "")
            img_cell = cell("C", img_url)
            if img_url:
                img_cell.hyperlink = img_url
                img_cell.font = Font(color="0563C1", underline="single",
                                     name="Segoe UI", size=9)
            else:
                img_cell.font = Font(name="Segoe UI", size=9)

            cell("D", "")
            cell("E", item.get("item_id", "")).font = Font(name="Segoe UI", size=9)
            cell("F", "")
            cell("G", "")
            cell("H", normalize_marketplace_code(item.get("marketplace", MARKETPLACE))).font = Font(name="Segoe UI", size=9)
            cell("I", "")
            cell("J", item.get("seller", "")).font = Font(name="Segoe UI", size=9)
            cell("K", "")
            cell("L", "")
            cell("M", item.get("brand") or (brand if brand != "All Results" else "Unassigned")).font = Font(name="Segoe UI", size=9)
            cell("N", item.get("price", "")).font = Font(name="Segoe UI", size=9)
            cell("O", item.get("location", "")).font = Font(name="Segoe UI", size=9)
            cell("P", item.get("product_type", "")).font = Font(name="Segoe UI", size=9)
            cell("Q", item.get("seller_origin", item.get("country", ""))).font = Font(name="Segoe UI", size=9)
            cell("R", item.get("threat_badge", item.get("threat_intel", ""))).font = Font(name="Segoe UI", size=9)

        # column widths
        for col_letter, width in COL_WIDTHS.items():
            ws.column_dimensions[col_letter].width = width

        # freeze header row
        ws.freeze_panes = "A2"

        # auto-filter
        ws.auto_filter.ref = f"A1:R1"

    def _safe_sheet_name(self, name: str) -> str:
        """Excel sheet names max 31 chars, no special chars."""
        invalid = r'\/?*[]:'
        for ch in invalid:
            name = name.replace(ch, "_")
        return name[:31]

    def export_a2c2_dossier(self, registry_dict: dict, file_path: str):
        """Export an executive A2C2 / Brand Protection Master Store & Recidivism Dossier."""
        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "A2C2 Store Recidivism"
        ws_summary.views.sheetView[0].showGridLines = True

        headers = [
            "Seller / Store Name",
            "Offense Status",
            "Infringing Brands",
            "Product Types",
            "Total Infringing Listings",
            "Total Market Value ($ USD)",
            "Registered Origin",
            "Known 3PL Locations",
            "Cross-Border Threat Assessment",
            "First Detected",
            "Last Scanned",
            "Scan Count"
        ]

        ws_summary.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws_summary.cell(row=1, column=col_num)
            cell.fill = PatternFill("solid", fgColor="1E293B")
            cell.font = Font(bold=True, color="FFFFFF", name="Segoe UI", size=10)
            cell.alignment = Alignment(horizontal="center" if col_num in (2, 5, 6, 12) else "left", vertical="center")

        row_idx = 2
        for seller, data in sorted(registry_dict.items(), key=lambda x: x[1].get("total_value", 0.0), reverse=True):
            scans = data.get("scan_count", 1)
            status = "🚨 REPEAT OFFENDER" if scans > 1 or data.get("total_listings", 0) > 10 else "⚠ FIRST STRIKE"
            brands = ", ".join(data.get("brands", []))
            pts = ", ".join(data.get("product_types", []))
            locs = ", ".join(data.get("locations", []))
            listings_count = data.get("total_listings", len(data.get("items", [])))
            total_val = f"${data.get('total_value', 0.0):,.2f}"
            origin = data.get("country") or data.get("seller_origin") or "Unresolved"
            threat = data.get("threat_badge") or data.get("threat_assessment") or ("🚨 OFFSHORE SMOKESCREEN" if "China" in origin else "Monitored")

            row_data = [
                seller,
                status,
                brands,
                pts,
                listings_count,
                total_val,
                origin,
                locs,
                threat,
                data.get("first_seen", ""),
                data.get("last_scanned", ""),
                scans
            ]
            ws_summary.append(row_data)

            fill = ROW_FILL_A if row_idx % 2 == 0 else ROW_FILL_B
            for col_num in range(1, len(headers) + 1):
                c = ws_summary.cell(row=row_idx, column=col_num)
                c.fill = fill
                c.font = Font(name="Segoe UI", size=9, bold=(col_num == 2 and "REPEAT" in status))
                c.border = THIN_BORDER
                if col_num == 2 and "REPEAT" in status:
                    c.font = Font(name="Segoe UI", size=9, bold=True, color="B91C1C")
                if col_num in (2, 5, 6, 12):
                    c.alignment = Alignment(horizontal="center" if col_num in (2, 12) else "right")
            row_idx += 1

        summary_widths = [24, 20, 26, 24, 22, 24, 20, 26, 32, 18, 18, 12]
        for idx, w in enumerate(summary_widths, 1):
            ws_summary.column_dimensions[get_column_letter(idx)].width = w
        ws_summary.freeze_panes = "A2"
        ws_summary.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

        all_items = []
        for seller, data in registry_dict.items():
            for it in data.get("items", []):
                all_items.append(it)

        if all_items:
            ws_items = wb.create_sheet(title="All Captured Listings")
            ws_items.views.sheetView[0].showGridLines = True
            item_headers = ["Seller", "Brand", "Product Type", "Item ID", "Title", "Price", "Seller Origin", "Location", "Threat Assessment", "Listing URL", "Scanned At"]
            ws_items.append(item_headers)
            for col_num in range(1, len(item_headers) + 1):
                cell = ws_items.cell(row=1, column=col_num)
                cell.fill = PatternFill("solid", fgColor="334155")
                cell.font = Font(bold=True, color="FFFFFF", name="Segoe UI", size=10)

            for i_idx, it in enumerate(all_items, start=2):
                orig_val = it.get("seller_origin") or it.get("country") or ""
                threat_val = it.get("threat_badge") or it.get("threat_intel") or ""
                ws_items.append([
                    it.get("seller", ""),
                    it.get("brand", ""),
                    it.get("product_type", ""),
                    it.get("item_id", ""),
                    it.get("title", ""),
                    it.get("price", ""),
                    orig_val,
                    it.get("location", ""),
                    threat_val,
                    it.get("url", ""),
                    it.get("scanned_at", "")
                ])
                fill = ROW_FILL_A if i_idx % 2 == 0 else ROW_FILL_B
                for col_num in range(1, len(item_headers) + 1):
                    c = ws_items.cell(row=i_idx, column=col_num)
                    c.fill = fill
                    c.font = Font(name="Segoe UI", size=9)
                    c.border = THIN_BORDER

            item_widths = [18, 16, 20, 16, 45, 12, 18, 22, 30, 45, 18]
            for idx, w in enumerate(item_widths, 1):
                ws_items.column_dimensions[get_column_letter(idx)].width = w
            ws_items.freeze_panes = "A2"
            ws_items.auto_filter.ref = f"A1:{get_column_letter(len(item_headers))}1"

        wb.save(file_path)

    def export_multi_locale(self, results: list[dict], selected_locales: list[dict], file_path: str):
        """
        Export multi-locale projections formatted strictly to the 18-Column Genesis Upload Specification
        with Thumbnail in Col C and extended locale metadata starting in Column S.
        Tab 1: All Results (Master Multi-Locale Sheet)
        Tabs 2+: Dedicated sheets per brand
        """
        import re
        projected_rows = []
        for it in results:
            item_id = str(it.get("item_id", "")).strip()
            if not item_id:
                m = re.search(r"/itm/(\d+)", it.get("url", ""))
                if m:
                    item_id = m.group(1)
                else:
                    continue

            for loc in selected_locales:
                domain = loc.get("domain", "ebay.com")
                country = loc.get("name", "United States")
                flag = loc.get("flag", "🌍")
                region = loc.get("region", "Global")
                
                is_meli_item = "mercadolibre" in it.get("marketplace", "").lower() or "mercadolivre" in it.get("marketplace", "").lower() or item_id.startswith("ML")
                if is_meli_item:
                    if domain.startswith("http"):
                        locale_url = f"{domain}/articulo/{item_id}"
                    elif "listado" in domain or "lista" in domain:
                        locale_url = f"https://{domain}/{item_id}"
                    else:
                        locale_url = f"https://www.{domain}/articulo/{item_id}"
                elif domain == "cafr.ebay.ca":
                    locale_url = f"https://{domain}/itm/{item_id}"
                else:
                    locale_url = f"https://www.{domain}/itm/{item_id}"

                row_item = dict(it)
                row_item["item_id"] = item_id
                row_item["locale_url"] = locale_url
                row_item["locale_domain"] = normalize_marketplace_code(domain)
                row_item["locale_country"] = f"{flag} {country}"
                row_item["locale_region"] = region
                projected_rows.append(row_item)

        wb = openpyxl.Workbook()
        wb.properties.creator = "Jerry Seidenstucker"
        wb.properties.title = "Apollo Global Multi-Locale Enforcement Pack"
        wb.properties.description = "Generated by Apollo Brand Intelligence (Created by Jerry Seidenstucker)"
        wb.remove(wb.active)

        # 1. Master Tab (All Results)
        ws_all = wb.create_sheet(title="All Results")
        self._write_multi_locale_sheet(ws_all, projected_rows)

        # 2. Dedicated Brand Tabs
        by_brand = defaultdict(list)
        for r in projected_rows:
            b = r.get("brand", "Unassigned")
            if not b or b == "Unknown":
                b = "Unassigned"
            by_brand[b].append(r)

        for brand, items in by_brand.items():
            ws_b = wb.create_sheet(title=self._safe_sheet_name(brand))
            self._write_multi_locale_sheet(ws_b, items)

        wb.save(file_path)
        return len(projected_rows)

    def _write_multi_locale_sheet(self, ws, items: list[dict]):
        """Helper to write multi-locale rows into a worksheet with canonical Genesis styling."""
        ws.views.sheetView[0].showGridLines = True

        headers_map = {
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
            "S": "Locale Country",
            "T": "Locale Domain",
            "U": "Region"
        }

        # Write Header Row
        for col_letter, header_text in headers_map.items():
            col_idx = openpyxl.utils.column_index_from_string(col_letter)
            cell = ws.cell(row=1, column=col_idx, value=header_text)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[1].height = 22

        for row_idx, it in enumerate(items, start=2):
            fill = ROW_FILL_A if row_idx % 2 == 0 else ROW_FILL_B

            def set_cell(col_letter, val):
                idx = openpyxl.utils.column_index_from_string(col_letter)
                c = ws.cell(row=row_idx, column=idx, value=val)
                c.fill = fill
                c.alignment = Alignment(vertical="center", wrap_text=False)
                c.border = THIN_BORDER
                c.font = Font(name="Segoe UI", size=9)
                return c

            set_cell("A", it.get("title", ""))

            loc_url = it.get("locale_url") or it.get("url", "")
            url_cell = set_cell("B", loc_url)
            if loc_url:
                url_cell.hyperlink = loc_url
                url_cell.font = Font(color="0563C1", underline="single", name="Segoe UI", size=9)

            img_url = it.get("image_url", "")
            img_cell = set_cell("C", img_url)
            if img_url:
                img_cell.hyperlink = img_url
                img_cell.font = Font(color="0563C1", underline="single", name="Segoe UI", size=9)

            set_cell("D", "")
            set_cell("E", it.get("item_id", ""))
            set_cell("F", "")
            set_cell("G", "")
            set_cell("H", it.get("locale_domain") or normalize_marketplace_code(it.get("marketplace", MARKETPLACE)))
            set_cell("I", "")
            set_cell("J", it.get("seller", ""))
            set_cell("K", "")
            set_cell("L", "")
            set_cell("M", it.get("brand", ""))
            set_cell("N", it.get("price", ""))
            set_cell("O", it.get("location", ""))
            set_cell("P", it.get("product_type", ""))
            set_cell("Q", it.get("seller_origin", it.get("country", "")))
            set_cell("R", it.get("threat_badge", it.get("threat_intel", "")))
            set_cell("S", it.get("locale_country", ""))
            set_cell("T", it.get("locale_domain", ""))
            set_cell("U", it.get("locale_region", ""))

        col_widths = {
            "A": 55, "B": 50, "C": 45, "D": 4, "E": 16, "F": 4, "G": 4,
            "H": 18, "I": 4, "J": 22, "K": 4, "L": 4, "M": 18, "N": 12,
            "O": 24, "P": 20, "Q": 20, "R": 30, "S": 22, "T": 18, "U": 16
        }
        for col_letter, width in col_widths.items():
            ws.column_dimensions[col_letter].width = width

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = "A1:U1"

