"""
vero_pdf_parser.py
Specialized VeRO & eBay Seller Disclosure Intelligence Harvester & Parser for Apollo.

Features:
- Extracts raw seller tracking text lines from VeRO / eBay PDF disclosure documents or direct text pastes.
- Intelligently decomposes disclosure text lines into structured components:
  * Seller Handle
  * Contact / Legal Name (Chinese Pinyin, Western names, etc.)
  * Street Address / Building / Unit
  * City / Municipal District
  * Postal / Zip Code
  * Country Code (ISO-2) / Region
- Ingests and updates records directly into Apollo's permanent Enforcement Registry (`data_store.py`).
- Generates Genesis-compliant Excel (.xlsx) workbooks and CSV spreadsheets ready for CSM and client intake.
"""

import os
import re
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger("Apollo.VeroParser")

ADDR_SUFFIXES = (
    "qu", "lu", "dao", "jie", "ceng", "fang", "cheng", "road", "street", "st", "rd",
    "ave", "blvd", "way", "lane", "drive", "dr", "court", "ct", "place", "pl",
    "strasse", "straße", "str", "weg", "gasse", "rue", "calle", "via", "corso", "alley"
)

ADDR_KEYWORDS = {
    "room", "suite", "apt", "unit", "building", "district", "qu", "lu", "no", "no.",
    "haus", "bldg", "fl", "floor", "ste", "block", "lot", "dangkouhao"
}


def parse_vero_line(line: str, default_marketplace: str = "eBay") -> Optional[Dict[str, str]]:
    """
    Parse a single VeRO / seller disclosure line into structured 9-column format.
    Extracts Seller Name, Marketplace, Phone, Combined Physical Address, Email,
    Authorization, Partner Type, Tag, and Seller Category.
    Supports both unstructured tracking lines and tab/pipe-delimited Genesis rows.
    """
    if not line or not line.strip():
        return None

    raw = line.strip()

    # Skip header lines
    low_raw = raw.lower()
    if low_raw.startswith("seller name") or low_raw.startswith("seller handle") or low_raw.startswith("seller_name"):
        return None

    # Check for direct tab-separated Genesis/Excel paste (>= 3 columns)
    if "\t" in raw and len(raw.split("\t")) >= 3:
        toks = [t.strip() for t in raw.split("\t")]
        s_name = toks[0]
        s_mkt = toks[1] if len(toks) > 1 and toks[1] else (default_marketplace or "eBay")
        s_phone = toks[2] if len(toks) > 2 else ""
        s_addr = toks[3] if len(toks) > 3 else ""
        s_email = toks[4] if len(toks) > 4 else ""
        s_auth = toks[5] if len(toks) > 5 and toks[5] else "Unauthorized"
        s_ptype = toks[6] if len(toks) > 6 and toks[6] else "3rd-Party Seller"
        s_tag = toks[7] if len(toks) > 7 and toks[7] else "VeRO Disclosed Origin"
        s_cat = toks[8] if len(toks) > 8 and toks[8] else "VeRO Disclosed Seller"

        # Try to extract country and city from physical address if available
        cntry = "Unresolved"
        city = ""
        zip_code = ""
        if s_addr:
            segs = [s.strip() for s in s_addr.split(",") if s.strip()]
            if segs and len(segs[-1]) <= 3:
                cntry = segs[-1].upper()
            elif segs and any(c in segs[-1].upper() for c in ("CHINA", "CN", "US", "USA", "UK", "DE", "FR", "CA", "AU", "IT", "ES")):
                cntry = segs[-1]

        return {
            "seller_name": s_name,
            "marketplace": s_mkt,
            "seller_phone_number": s_phone,
            "phone": s_phone,
            "seller_physical_address": s_addr,
            "physical_address": s_addr,
            "seller_email_address": s_email,
            "email": s_email,
            "authorization": s_auth,
            "partner_type": s_ptype,
            "tag": s_tag,
            "seller_category": s_cat,
            "handle": s_name,
            "contact_name": s_name,
            "street_address": s_addr,
            "city": city,
            "postal_code": zip_code,
            "country": cntry,
            "raw_disclosure": raw,
            "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # 1. Extract Email Address
    email = ""
    email_m = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', raw)
    if email_m:
        email = email_m.group(0).strip()

    # 2. Extract Phone Number (strict word boundaries and explicit keywords or international prefix)
    phone = ""
    phone_m = re.search(r'\b(?:tel|telephone|phone|ph|mobile|cel|cell|contact)[:\s]+([\+0-9\-\.\s\(\)]{7,25})', raw, re.IGNORECASE)
    if phone_m:
        p_cand = phone_m.group(1).strip()
        digits = re.sub(r'\D', '', p_cand)
        if len(digits) >= 7:
            phone = p_cand.rstrip(' ,|;')
    if not phone:
        gen_phone = re.search(r'(\+\d{1,3}[-.\s]?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4})', raw)
        if gen_phone:
            digits = re.sub(r'\D', '', gen_phone.group(1))
            if len(digits) >= 7:
                phone = gen_phone.group(1).strip()

    # 3. Detect Marketplace
    r_low = raw.lower()
    marketplace = default_marketplace or "eBay"
    if "aliexpress" in r_low:
        marketplace = "AliExpress"
    elif "tiktok" in r_low:
        marketplace = "TikTok Shop"
    elif "vinted" in r_low:
        marketplace = "Vinted"
    elif "mercadolibre" in r_low or "mercado" in r_low:
        marketplace = "Mercado Libre"
    elif "amazon" in r_low:
        marketplace = "Amazon"
    elif "temu" in r_low:
        marketplace = "Temu"
    elif "wish" in r_low:
        marketplace = "Wish"
    elif "etsy" in r_low:
        marketplace = "Etsy"
    elif "redbubble" in r_low:
        marketplace = "Redbubble"
    elif "printerval" in r_low:
        marketplace = "Printerval"
    elif "ebay" in r_low:
        marketplace = "eBay"

    # 4. Split Seller Handle from Disclosure Body
    parts = re.split(r'\s+/\s+|\s*\|\s*|\t+|\s*:\s*(?=[a-zA-Z0-9])', raw, maxsplit=1)
    if len(parts) == 2:
        handle = parts[0].strip()
        disclosure = parts[1].strip()
    else:
        tokens = raw.split()
        if len(tokens) >= 2 and ('/' in tokens[0] or '_' in tokens[0] or tokens[0].isalnum()):
            handle = tokens[0].strip('/')
            disclosure = " ".join(tokens[1:]).strip()
        else:
            handle = ""
            disclosure = raw

    # Clean handle
    handle = re.sub(r'^(?:seller|user|handle|id)[:\s]*', '', handle, flags=re.IGNORECASE).strip()

    # Clean metadata segments from address disclosure
    disclosure_clean = re.sub(r'\|\s*(?:phone|tel|mobile|cel|email|mail|contact|tag|category|partner|auth)[^|]+', '', disclosure, flags=re.IGNORECASE)
    if email and email in disclosure_clean:
        disclosure_clean = disclosure_clean.replace(email, '')
    if phone and phone in disclosure_clean:
        disclosure_clean = disclosure_clean.replace(phone, '')
    disclosure_clean = re.sub(r'\b(?:phone|tel|email|mail)[:\s]*', '', disclosure_clean, flags=re.IGNORECASE).strip()
    disclosure_clean = re.sub(r'\|\s*$', '', disclosure_clean).strip()

    # 5. Split comma segments
    comma_segments = [s.strip() for s in disclosure_clean.split(',') if s.strip()]

    country = ""
    postal_code = ""
    city = ""
    contact_name = ""
    street_address = ""

    # Common country identifiers
    country_patterns = r'^(?:CN|US|USA|GB|UK|DE|FR|CA|AU|IT|ES|JP|HK|TW|KR|China|United States|United Kingdom|Germany|France|Canada|Australia|Hong Kong|Italy|Spain|Japan|Taiwan|South Korea)$'

    # Work backwards from the rightmost segments
    rem = list(comma_segments)

    # Detect country in last segment
    if rem:
        last = rem[-1]
        if len(last) <= 3 or re.match(country_patterns, last, re.IGNORECASE) or (len(last) <= 20 and not any(c.isdigit() for c in last)):
            country = rem.pop()

    # Detect Postal Code / State / City from remaining trailing segments
    if rem:
        seg = rem[-1]
        state_zip_m = re.search(r'\b([A-Z]{2})\s+([A-Z0-9\s-]{3,10})$', seg, re.IGNORECASE)
        pure_zip_m = re.match(r'^(?:\d{4,8}(?:-\d{4})?|[A-Z0-9]{2,4}\s?[A-Z0-9]{2,4})$', seg, re.IGNORECASE)

        if state_zip_m:
            postal_code = state_zip_m.group(2).strip()
            leftover = seg[:state_zip_m.start()].strip()
            rem.pop()
            if leftover:
                rem.append(leftover)
        elif pure_zip_m:
            postal_code = rem.pop()

    # Next trailing segment is usually City / District
    if rem and len(rem) >= 2:
        city = rem.pop()
    elif rem and len(rem) == 1 and not city:
        pass

    if city and not postal_code:
        zip_in_city = re.search(r'\b(\d{4,8}(?:-\d{4})?|[A-Z]\d[A-Z]\s?\d[A-Z]\d)\b', city)
        if zip_in_city:
            postal_code = zip_in_city.group(1)
            city = city[:zip_in_city.start()].strip()

    addr_text = ", ".join(rem).strip()

    # 6. Name vs Street Address Extraction
    words = addr_text.split()
    if len(words) >= 4:
        w1_low = words[1].lower()
        w2_low = words[2].lower()

        if re.search(r'\d', w1_low):
            contact_name = words[0]
            street_address = " ".join(words[1:])
        elif (re.search(r'\d', w2_low) or
              any(w2_low.endswith(sfx) for sfx in ADDR_SUFFIXES) or
              w2_low in ADDR_KEYWORDS):
            contact_name = " ".join(words[:2])
            street_address = " ".join(words[2:])
        else:
            w3_low = words[3].lower() if len(words) > 3 else ""
            if (w3_low and (re.search(r'\d', w3_low) or
                any(w3_low.endswith(sfx) for sfx in ADDR_SUFFIXES) or
                w3_low in ADDR_KEYWORDS)):
                contact_name = " ".join(words[:3])
                street_address = " ".join(words[3:])
            else:
                contact_name = " ".join(words[:2])
                street_address = " ".join(words[2:])
    elif len(words) == 3:
        if re.search(r'\d', words[1]):
            contact_name = words[0]
            street_address = " ".join(words[1:])
        elif re.search(r'\d', words[2]) or any(words[2].lower().endswith(sfx) for sfx in ADDR_SUFFIXES):
            contact_name = " ".join(words[:2])
            street_address = words[2]
        else:
            contact_name = " ".join(words[:2])
            street_address = words[2]
    elif len(words) == 2:
        contact_name = words[0]
        street_address = words[1]
    else:
        street_address = addr_text

    norm_country = country.upper() if len(country) <= 3 else country.title()
    addr_parts = [p for p in [street_address, city, postal_code, norm_country] if p]
    physical_address = ", ".join(addr_parts) if addr_parts else disclosure

    seller_name = handle or contact_name or "Unknown Seller"

    return {
        # 9 Target Column alignment
        "seller_name": seller_name,
        "marketplace": marketplace,
        "seller_phone_number": phone,
        "phone": phone,
        "seller_physical_address": physical_address,
        "physical_address": physical_address,
        "seller_email_address": email,
        "email": email,
        "authorization": "Unauthorized",
        "partner_type": "3rd-Party Seller",
        "tag": "VeRO Disclosed Origin",
        "seller_category": "VeRO Disclosed Seller",
        # Decomposition fields
        "handle": handle,
        "contact_name": contact_name,
        "street_address": street_address,
        "city": city,
        "postal_code": postal_code,
        "country": norm_country,
        "raw_disclosure": raw,
        "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def parse_vero_text(raw_text: str, default_marketplace: str = "eBay") -> List[Dict[str, str]]:
    """Parse multi-line string containing VeRO / seller disclosures into 9-column records."""
    results = []
    seen_handles = set()
    if not raw_text:
        return results

    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        rec = parse_vero_line(line, default_marketplace=default_marketplace)
        if rec and rec["handle"]:
            h_key = rec["handle"].lower()
            if h_key not in seen_handles:
                seen_handles.add(h_key)
                results.append(rec)
    return results


def parse_vero_pdf(file_path: str, default_marketplace: str = "eBay") -> List[Dict[str, str]]:
    """Extract text from a VeRO PDF file and parse structured 9-column disclosure records."""
    if not PYPDF_AVAILABLE:
        raise RuntimeError("pypdf is required to read PDF files. Please install pypdf via 'pip install pypdf'.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    reader = PdfReader(file_path)
    full_text = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        full_text.append(txt)

    combined_text = "\n".join(full_text)
    return parse_vero_text(combined_text, default_marketplace=default_marketplace)


def push_to_enforcement_registry(records: List[Dict[str, str]], data_store: Any) -> int:
    """
    Ingest parsed VeRO seller disclosures into Apollo's permanent Enforcement Registry.
    Updates seller metadata, country of origin, contact names, and structured address.
    """
    if not records or not data_store:
        return 0

    reg = data_store.get_enforcement_registry()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_count = 0

    for rec in records:
        h = rec.get("handle") or rec.get("seller_name")
        if not h:
            continue

        entry = reg.setdefault(h, {
            "seller_handle": h,
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
            "threat_badge": "🛡 VeRO Disclosed Origin",
            "risk_tier": "Low",
            "historical_scan_count": 0,
            "strike_history": []
        })

        # Inject / Enrich disclosure intelligence
        if rec.get("contact_name"):
            entry["contact_name"] = rec["contact_name"]
        if rec.get("street_address"):
            entry["street_address"] = rec["street_address"]
        if rec.get("physical_address"):
            entry["physical_address"] = rec["physical_address"]
        if rec.get("phone"):
            entry["phone"] = rec["phone"]
        if rec.get("email"):
            entry["email"] = rec["email"]
        if rec.get("city"):
            entry["city"] = rec["city"]
        if rec.get("postal_code"):
            entry["postal_code"] = rec["postal_code"]
        if rec.get("country") and rec["country"] not in ("", "Unresolved"):
            entry["country"] = rec["country"]
        if rec.get("raw_disclosure"):
            entry["raw_disclosure"] = rec["raw_disclosure"]
        entry["disclosure_source"] = "VeRO / eBay Disclosure"
        entry["last_disclosure_import"] = now_str

        # Update threat badge
        if "CN" in str(entry.get("country", "")).upper() or "CHINA" in str(entry.get("country", "")).upper():
            entry["threat_badge"] = "🇨🇳 Verified Direct China Hub (VeRO)"
        elif not entry.get("threat_badge"):
            entry["threat_badge"] = "🛡 VeRO Disclosed Origin"

        updated_count += 1

    data_store.save_enforcement_registry(reg)
    logger.info(f"Successfully saved {updated_count} VeRO disclosures to Enforcement Registry.")
    return updated_count


def export_to_excel(records: List[Dict[str, str]], filepath: str):
    """
    Export parsed VeRO disclosures to a beautifully formatted Genesis-ready Excel spreadsheet
    with the exact 9 required & optional enforcement columns.
    """
    if not OPENPYXL_AVAILABLE:
        raise RuntimeError("openpyxl is required to export to Excel.")

    wb = openpyxl.Workbook()
    wb.properties.creator = "Jerry Seidenstucker"
    wb.properties.title = "Apollo Seller Intelligence Disclosure Report"
    wb.remove(wb.active)

    ws = wb.create_sheet(title="Seller Intelligence")

    # Header styling
    header_fill = PatternFill("solid", fgColor="0F172A")
    header_font = Font(bold=True, color="FFFFFF", name="Segoe UI", size=10)
    row_fill_a = PatternFill("solid", fgColor="FFFFFF")
    row_fill_b = PatternFill("solid", fgColor="F8FAFC")
    border_side = Side(style="thin", color="E2E8F0")
    thin_border = Border(bottom=border_side, top=border_side, left=border_side, right=border_side)

    headers = [
        "Seller Name",
        "Marketplace",
        "Seller Phone Number",
        "Seller Physical Address",
        "Seller Email Address",
        "Authorization",
        "Partner Type",
        "Tag",
        "Seller Category"
    ]

    for col_num, h_text in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=h_text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[1].height = 24

    for r_idx, rec in enumerate(records, 2):
        row_fill = row_fill_a if r_idx % 2 == 0 else row_fill_b
        row_data = [
            rec.get("seller_name") or rec.get("handle") or rec.get("contact_name", ""),
            rec.get("marketplace", "eBay"),
            rec.get("seller_phone_number") or rec.get("phone", ""),
            rec.get("seller_physical_address") or rec.get("physical_address") or rec.get("street_address", ""),
            rec.get("seller_email_address") or rec.get("email", ""),
            rec.get("authorization", ""),
            rec.get("partner_type", ""),
            rec.get("tag", ""),
            rec.get("seller_category", "")
        ]
        for c_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.fill = row_fill
            cell.font = Font(name="Segoe UI", size=9)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")
        ws.row_dimensions[r_idx].height = 20

    col_widths = [22, 16, 20, 45, 26, 18, 18, 22, 22]
    for idx, width in enumerate(col_widths, 1):
        col_letter = get_column_letter(idx)
        ws.column_dimensions[col_letter].width = width

    ws.freeze_panes = "A2"
    wb.save(filepath)
    logger.info(f"VeRO Excel report exported: {filepath}")


def export_to_csv(records: List[Dict[str, str]], filepath: str):
    """Export parsed disclosures to CSV matching the 9 target columns."""
    headers = [
        "Seller Name",
        "Marketplace",
        "Seller Phone Number",
        "Seller Physical Address",
        "Seller Email Address",
        "Authorization",
        "Partner Type",
        "Tag",
        "Seller Category"
    ]
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for rec in records:
            writer.writerow([
                rec.get("seller_name") or rec.get("handle") or rec.get("contact_name", ""),
                rec.get("marketplace", "eBay"),
                rec.get("seller_phone_number") or rec.get("phone", ""),
                rec.get("seller_physical_address") or rec.get("physical_address") or rec.get("street_address", ""),
                rec.get("seller_email_address") or rec.get("email", ""),
                rec.get("authorization", ""),
                rec.get("partner_type", ""),
                rec.get("tag", ""),
                rec.get("seller_category", "")
            ])
    logger.info(f"VeRO CSV report exported: {filepath}")
