import json
import logging
import re
import pandas as pd
from datetime import datetime, timezone
from lxml import etree

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def normalize_string(text):
    """Replaces all special characters with spaces and normalizes whitespace."""
    if not text: return ""
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(text))
    return " ".join(clean.lower().split())

def get_alternate_name_tiered(search_value, excel_path='Alternative Names.xlsx'):
    """
    Applies the 5-tier search logic against the Excel file's 'Primary name' column.
    Returns the 'Alt name' if found, otherwise returns the original search_value.
    """
    try:
        df = pd.read_excel(excel_path)
        df.columns = [str(c).strip() for c in df.columns]
        if 'Primary name' not in df.columns or 'Alt name' not in df.columns:
            return search_value

        df['Primary name_norm'] = df['Primary name'].apply(normalize_string)
        df['Alt name'] = df['Alt name'].astype(str).str.strip()
        norm_val = normalize_string(search_value)
        
        # Tier 1: Exact/Normalized Match
        match = df[df['Primary name_norm'] == norm_val]
        if not match.empty: return match.iloc[0]['Alt name']

        # Tier 3: Merged Match
        merged_val = re.sub(r'\s+', '', norm_val)
        match = df[df['Primary name_norm'].str.replace(r'\s+', '', regex=True) == merged_val]
        if not match.empty: return match.iloc[0]['Alt name']

        # Tier 4: Reduction Match
        words = norm_val.split()
        if len(words) > 1:
            for i in range(len(words) - 1, 0, -1):
                phrase = " ".join(words[:i])
                match = df[df['Primary name_norm'].str.contains(rf'\b{re.escape(phrase)}\b', na=False)]
                if not match.empty: return match.iloc[0]['Alt name']

        # Tier 5: Anchor Match
        if words:
            match = df[df['Primary name_norm'].str.startswith(words[0], na=False)]
            if not match.empty: return match.iloc[0]['Alt name']
            
        return search_value
    except Exception as e:
        logger.warning(f"Excel lookup error: {e}")
        return search_value

def universal_recursive_search(search_value, partners_list, xml_tag_to_search):
    """
    Tiered search logic: First searches Alternative Names.xlsx using 5 tiers, 
    then uses the result to search the XML list using 5 tiers.
    """
    target_search_value = get_alternate_name_tiered(search_value)
    
    def search_xml(val):
        norm_search = normalize_string(val)
        if not norm_search: return None
        
        # Tier 1 & 2: Exact & Normalized Whole Value Match
        for p in partners_list:
            tags = p.xpath(f".//{xml_tag_to_search}/text()")
            for t in tags:
                if norm_search == normalize_string(t):
                    return p

        # Tier 3: Merged Match
        merged_name = re.sub(r'\s+', '', norm_search)
        for p in partners_list:
            tags = p.xpath(f".//{xml_tag_to_search}/text()")
            for t in tags:
                if merged_name == re.sub(r'\s+', '', normalize_string(t)):
                    return p

        # Tier 4: Reduction Match
        words = norm_search.split()
        if len(words) > 1:
            for i in range(len(words) - 1, 0, -1):
                phrase = " ".join(words[:i])
                phrase_esc = re.escape(phrase)
                for p in partners_list:
                    tags = p.xpath(f".//{xml_tag_to_search}/text()")
                    for t in tags:
                        if re.search(rf'\b{phrase_esc}\b', normalize_string(t)):
                            return p

        # Tier 5: Anchor Search
        if words:
            for p in partners_list:
                tags = p.xpath(f".//{xml_tag_to_search}/text()")
                for t in tags:
                    if normalize_string(t).startswith(words[0]):
                        return p
        return None

    return search_xml(target_search_value)

def format_to_iso_timestamp(date_str):
    if not date_str: return ""
    formats = ["%d-%b-%Y", "%m/%d/%Y", "%Y-%m-%d", "%d %b %Y", "%m-%d-%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError: continue
    return date_str[:10] + "T00:00:00.000Z"

def get_ndc_search_variants(raw_ndc):
    clean = re.sub(r'[-\s]', '', str(raw_ndc))
    variants = []
    def f542(n): return f"{n[:5]}-{n[5:9]}-{n[9:]}"
    if len(clean) == 11:
        variants.extend([clean, f542(clean)])
    elif len(clean) == 10:
        v1, v2, v3 = "0"+clean, clean[:5]+"0"+clean[5:], clean[:9]+"0"+clean[9:]
        variants.extend([v1, f542(v1), v2, f542(v2), v3, f542(v3)])
    elif len(clean) == 9:
        v9 = "00" + clean
        variants.extend([v9, f542(v9)])
    else:
        variants.append(clean)
    return variants

def validate_ndc_with_fallback(raw_ndc, p_md, rb_md):
    variants = get_ndc_search_variants(raw_ndc)
    for v in variants:
        if len(p_md.xpath(f"//Entries/ItemCodes[normalize-space(Identifier)='{v}']")) > 0:
            return re.sub(r'-', '', v)
    for v in variants:
        if len(rb_md.xpath(f"//pi[normalize-space(p)='{v}']")) > 0:
            return re.sub(r'-', '', v)
    raise ValueError(f"NDC {raw_ndc} lookup failed.")

def build_tx_xml_from_data(gemini, c_md, p_md, rb_md):
    # Load Subscriber criteria XML
    p_crit = etree.parse('Getpartnersbyowningcompanywithcriteria.txt')
    NS_MAP = {'ns2': "urn:tracelink:infoexchange", 'ns3': "urn:tracelink:transactionhistory"}
    root = etree.Element("{urn:tracelink:transactionhistory}TransactionExchange", nsmap=NS_MAP)
    
    etree.SubElement(root, "CompanyID").text = "a0f0e427-d4e4-410f-ac7a-c304a20c64de"
    etree.SubElement(root, "ServiceID").text = "e468b292-53ed-49bf-9df0-dde8dcdbbd10"
    
    sub_val = gemini.get("Transfer From", "").strip()
    sub_target = universal_recursive_search(sub_val, p_crit.xpath("//ServicePartner"), "AlternateCompanyName")
    if sub_target is not None:
        etree.SubElement(root, "SubscriberID").text = sub_target.findtext("MatchedCompanyLocationIDs").split(',')[0].strip()

    etree.SubElement(root, "CompanyLocationID").text = "f42c7ad8-b8b5-49e7-af5b-ca36e7efea18"
    etree.SubElement(root, "TxType").text = "RECEIPT"
    dn = str(gemini.get("Delivery Number"))
    etree.SubElement(root, "DN").text = dn
    etree.SubElement(root, "ShipDate").text = format_to_iso_timestamp(gemini.get('Shipment Date'))
    etree.SubElement(root, "IDS").text = f"Delivery:{dn}"

    # Collect all product data first to group them in the XML
    prod_list = gemini.get("Product details", [])
    total_qty = 0
    collected_ndcs = []
    collected_lots = []

    for item in prod_list:
        for p_key, p_val in item.items():
            try:
                v_ndc = validate_ndc_with_fallback(p_val.get("NDC"), p_md, rb_md)
                collected_ndcs.append(f"NDC542|{v_ndc}")
                collected_lots.append(p_val.get("Lot Number"))
                total_qty += int(p_val.get("Quantity", 0))
            except ValueError:
                # Skip this specific product and continue to the next one
                continue

    # Requirement: At least 1 searched NDC is required for TE creation
    if not collected_ndcs:
        raise ValueError(f"NDC lookup failed for all products in DN {dn}.")

    # Requirement: All NDCList grouped together, followed by all LotList
    for ndc in collected_ndcs:
        etree.SubElement(root, "NDCList").text = ndc
    for lot in collected_lots:
        etree.SubElement(root, "LotList").text = lot

    etree.SubElement(root, "Qty").text = str(total_qty)

    sender_raw = gemini.get("Transfer From", "").strip()
    s_target = universal_recursive_search(sender_raw, c_md.xpath("//Partners"), "businessName")
    if s_target is None: raise ValueError(f"Sender lookup failed for: {sender_raw}")
    s_id = s_target.xpath("./CompanyIdentifiers[1]/Identifier/text()")[0]
    etree.SubElement(root, "SenderID").text = s_id
    etree.SubElement(root, "SenderName").text = s_target.findtext("businessName")

    is_drop, recip_raw = gemini.get("Drop Shipment", "No"), gemini.get("Sold To", "").strip()
    partners = c_md.xpath("//Partners")
    recip_target = None

    if is_drop == "No":
        recip = {"id": "1100007476668", "bn": "BriovaRx", "idt": "GLN", "s1": "53 Darling Ave", "c": "South Portland", "st": "ME", "pc": "04106", "co": "US"}
    else:
        if "mckesson" in recip_raw.lower():
            recip_target = next((p for p in partners if (p.findtext("businessName") or "").strip().lower() == "mckesson pharma"), None)
        if recip_target is None:
            recip_target = universal_recursive_search(recip_raw, partners, "businessName")
        
        if recip_target is None: raise ValueError(f"Recipient lookup failed for: {recip_raw}")
        r_idnt = recip_target.xpath("./CompanyIdentifiers[1]")[0]
        r_addr = recip_target.find("MasterDataAddress")
        recip = {"id": r_idnt.findtext("Identifier"), "bn": recip_target.findtext("businessName"), "idt": r_idnt.findtext("IdentifierType"),
                 "s1": r_addr.findtext("address1"), "c": r_addr.findtext("city"), "st": r_addr.findtext("state"), "pc": r_addr.findtext("postalcode"), "co": r_addr.findtext("country")}

    etree.SubElement(root, "RecipientID").text = recip['id']
    etree.SubElement(root, "RecipientName").text = recip['bn']

    s_addr = s_target.find("MasterDataAddress")
    s_from = etree.SubElement(root, "shipFromLocation")
    for k, v in [("ID", s_id), ("IDT", s_target.xpath("./CompanyIdentifiers[1]/IdentifierType/text()")[0]), ("BN", s_target.findtext("businessName")), ("S1", s_addr.findtext("address1")), 
                 ("C", s_addr.findtext("city")), ("State", s_addr.findtext("state")), ("PC", s_addr.findtext("postalcode")), ("Country", s_addr.findtext("country"))]:
        etree.SubElement(s_from, k).text = v

    s_to = etree.SubElement(root, "shipToLocation")
    for k, v in [("ID", recip['id']), ("IDT", recip['idt']), ("BN", recip['bn']), ("S1", recip['s1']), ("C", recip['c']), ("State", recip['st']), ("PC", recip['pc']), ("Country", recip['co'])]:
        etree.SubElement(s_to, k).text = v

    for k, v in [("IsFromPaper", "true"), ("IsFullyReceived", "false"), ("State", "ACTIVE"), ("IsSerialized", "false")]:
        etree.SubElement(root, k).text = v

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes", pretty_print=True).decode('utf-8')

if __name__ == "__main__":
    try:
        # For testing, ensure these files exist in your directory
        with open('Samplegeminioutput.txt', 'r') as f:
            data = json.load(f)
            entry = data[0] if isinstance(data, list) else data
        c_md, p_md, rb_md = etree.parse('BRIOVARX_CompanyPartnerMD.xml'), etree.parse('BRIOVARX_ProductMD.xml'), etree.parse('Redbook_20250403.xml')
        print(build_tx_xml_from_data(entry, c_md, p_md, rb_md))
    except Exception as e: print(f"Independent Run Error: {e}")