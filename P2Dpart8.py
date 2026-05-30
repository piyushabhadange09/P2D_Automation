import json
import logging
import re
import uuid
import secrets
from datetime import datetime, timezone
from lxml import etree
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def generate_secure_uuid():
    rb = bytearray(secrets.token_bytes(16))
    rb[6] &= 0x0f; rb[6] |= 0x40; rb[8] &= 0x3f; rb[8] |= 0x80
    return str(uuid.UUID(bytes=bytes(rb)))

def format_to_iso_timestamp(date_str):
    if not date_str: return ""
    formats = ["%d-%b-%Y", "%m/%d/%Y", "%Y-%m-%d", "%d %b %Y", "%m-%d-%Y"]
    for f in formats:
        try:
            dt = datetime.strptime(date_str.strip(), f)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError: continue
    return date_str[:10] + "T00:00:00.000Z"

def format_to_yyyy_mm_dd(date_str):
    if not date_str: return ""
    formats = ["%d-%b-%Y", "%m/%d/%Y", "%Y-%m-%d", "%d %b %Y"]
    for f in formats:
        try: return datetime.strptime(date_str.strip(), f).strftime("%Y-%m-%d")
        except ValueError: continue
    return date_str[:10]

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

def universal_recursive_search(search_value, partners_list, xml_tag_to_search="businessName"):
    """
    Unified 5-tier search: First searches Excel mappings, then searches XML partners.
    """
    target_search_value = get_alternate_name_tiered(search_value)
    
    def search_xml(val):
        norm_search = normalize_string(val)
        if not norm_search: return None
        
        # Tier 1 & 2: Exact & Normalized
        for p in partners_list:
            tags = p.xpath(f".//{xml_tag_to_search}/text()")
            for t in tags:
                if norm_search == normalize_string(t): return p

        # Tier 3: Merged
        merged_name = re.sub(r'\s+', '', norm_search)
        for p in partners_list:
            tags = p.xpath(f".//{xml_tag_to_search}/text()")
            for t in tags:
                if merged_name == re.sub(r'\s+', '', normalize_string(t)): return p

        # Tier 4: Reduction
        words = norm_search.split()
        if len(words) > 1:
            for i in range(len(words) - 1, 0, -1):
                phrase = " ".join(words[:i])
                phrase_esc = re.escape(phrase)
                for p in partners_list:
                    tags = p.xpath(f".//{xml_tag_to_search}/text()")
                    for t in tags:
                        if re.search(rf'\b{phrase_esc}\b', normalize_string(t)): return p

        # Tier 5: Anchor
        if words:
            for p in partners_list:
                tags = p.xpath(f".//{xml_tag_to_search}/text()")
                for t in tags:
                    if normalize_string(t).startswith(words[0]): return p
        return None

    return search_xml(target_search_value)

def get_partner_details(search_value, company_md_xml, step_label, drop_shipment="No"):
    partners = company_md_xml.xpath("//Partners")
    target = None
    
    if step_label == "Step 11" and drop_shipment == "Yes" and "mckesson" in search_value.lower():
        target = next((p for p in partners if (p.findtext("businessName") or "").strip().lower() == "mckesson pharma"), None)
    
    if target is None:
        target = universal_recursive_search(search_value, partners, "businessName")
    
    if target is None: raise ValueError(f"{step_label} lookup failed for: {search_value}")
    
    ident = target.xpath("./CompanyIdentifiers[1]")[0]
    addr = target.find("MasterDataAddress")
    return {
        "id": ident.findtext("Identifier"), 
        "idt": ident.findtext("IdentifierType"), 
        "bn": target.findtext("businessName"), 
        "s1": addr.findtext("address1"), 
        "c": addr.findtext("city"), 
        "st": addr.findtext("state"), 
        "pc": addr.findtext("postalcode"), 
        "country": addr.findtext("country")
    }

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

def find_product_info(raw_ndc, p_md, rb_md):
    variants = get_ndc_search_variants(raw_ndc)
    for v in variants:
        entry = p_md.xpath(f"//Entries/ItemCodes[normalize-space(Identifier)='{v}']/..")
        if entry:
            info = entry[0].find("ItemInfoList")
            return {"ProdName": info.findtext("drugName"), "Dosage": info.findtext("dosageForm"), "ProdStrength": info.findtext("strength"), 
                    "ContainerSz": info.findtext("containerSize"), "Manufacturer": info.findtext("manufacturer"), "MatchedNDC": v.replace('-', '')}
    for v in variants:
        entry = rb_md.xpath(f"//pi[normalize-space(p)='{v}']")
        if entry:
            pi = entry[0]
            return {"ProdName": pi.findtext("n"), "Dosage": pi.findtext("d"), "ProdStrength": pi.findtext("s"), 
                    "ContainerSz": pi.findtext("c"), "Manufacturer": pi.findtext("m"), "MatchedNDC": v.replace('-', '')}
    raise ValueError(f"NDC {raw_ndc} lookup failed.")

def build_th_xml(product_key, product_data, gemini_data, company_md, product_md, redbook_md, shared_aid):
    NS_MAP = {'ns2': "urn:tracelink:transactionhistory"}
    root = etree.Element("{urn:tracelink:transactionhistory}PaperTransactionHistory", nsmap=NS_MAP)
    th_root = etree.SubElement(root, "TranasactionHistory")

    for k, v in [("CompanyID", "a0f0e427-d4e4-410f-ac7a-c304a20c64de"), ("CompanyLocationID", "f42c7ad8-b8b5-49e7-af5b-ca36e7efea18"), 
                 ("SubscriberID", "f42c7ad8-b8b5-49e7-af5b-ca36e7efea18"), ("ServiceID", "e468b292-53ed-49bf-9df0-dde8dcdbbd10"), ("State", "ACTIVE")]:
        etree.SubElement(th_root, k).text = v
    etree.SubElement(th_root, "DeliveryNumber").text = str(gemini_data.get("Delivery Number"))
    etree.SubElement(th_root, "AID").text = shared_aid

    txns = etree.SubElement(th_root, "Txns")
    dt = format_to_iso_timestamp(gemini_data.get('Transaction Date'))
    sdt = format_to_iso_timestamp(gemini_data.get('Shipment Date'))
    etree.SubElement(txns, "TxnDate").text = dt
    etree.SubElement(txns, "SrtDt").text = dt
    etree.SubElement(txns, "ShipDate").text = sdt
    etree.SubElement(txns, "TxType").text = "RECEIPT"
    etree.SubElement(txns, "Qty").text = str(product_data.get("Quantity"))

    f_info = get_partner_details(gemini_data.get("Transfer From"), company_md, "Step 9")
    tx_f = etree.SubElement(txns, "TxFrom")
    for k, v in [("ID", f_info['id']), ("IDT", f_info['idt']), ("DSCSABR", "IndirectSupplier"), ("BN", f_info['bn']), 
                 ("S1", f_info['s1']), ("C", f_info['c']), ("State", f_info['st']), ("PC", f_info['pc']), ("Country", f_info['country'])]:
        etree.SubElement(tx_f, k).text = v

    tx_t = etree.SubElement(txns, "TxTo")
    for k, v in [("ID", "1100007476668"), ("IDT", "GLN"), ("BN", "BriovaRx"), ("S1", "53 Darling Ave"), ("C", "South Portland"), ("State", "ME"), ("PC", "04106"), ("Country", "US")]:
        etree.SubElement(tx_t, k).text = v

    if gemini_data.get("Drop Shipment") == "Yes":
        s_info = get_partner_details(gemini_data.get("Sold To"), company_md, "Step 11", "Yes")
        sold_t = etree.SubElement(txns, "SoldTo")
        for k, v in [("ID", s_info['id']), ("IDT", s_info['idt']), ("BN", s_info['bn']), ("S1", s_info['s1']), ("C", s_info['c']), ("State", s_info['st']), ("PC", s_info['pc']), ("Country", s_info['country'])]:
            etree.SubElement(sold_t, k).text = v

    etree.SubElement(txns, "ProductOrigin").text = "IndirectPurchase"
    etree.SubElement(th_root, "TS").text = "false"
    etree.SubElement(th_root, "IsFromPaper").text = "true"

    p_info = find_product_info(product_data.get("NDC", ""), product_md, redbook_md)
    pi = etree.SubElement(th_root, "PI")
    etree.SubElement(pi, "NDC").text = p_info["MatchedNDC"]
    etree.SubElement(pi, "NDCType").text = "NDC542"
    etree.SubElement(pi, "Lot").text = str(product_data.get("Lot Number"))
    etree.SubElement(pi, "ExpDate").text = format_to_yyyy_mm_dd(product_data.get("Expiration Date"))
    etree.SubElement(pi, "ProdName").text = p_info["ProdName"]
    etree.SubElement(pi, "ProdStrength").text = p_info["ProdStrength"]
    etree.SubElement(pi, "Dosage").text = p_info["Dosage"]
    etree.SubElement(pi, "ContainerSz").text = p_info["ContainerSz"]
    etree.SubElement(pi, "Manufacturer").text = p_info["Manufacturer"]

    etree.SubElement(th_root, "CD").text = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    etree.SubElement(th_root, "CUID").text = "e49e3fe0-e6b2-4f1f-9090-d1676f522fea"

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes", pretty_print=True).decode('utf-8')

if __name__ == "__main__":
    try:
        with open('Samplegeminioutput.txt', 'r') as f:
            data = json.load(f)
            entry = data[0] if isinstance(data, list) else data
        c_md, p_md = etree.parse('BRIOVARX_CompanyPartnerMD.xml'), etree.parse('BRIOVARX_ProductMD.xml')
        rb_md = etree.parse('Redbook_20250403.xml')
        aid = generate_secure_uuid()
        for item in entry.get("Product details", []):
            for k, v in item.items():
                print(f"\n--- TH XML FOR {k} ---\n{build_th_xml(k, v, entry, c_md, p_md, rb_md, aid)}")
    except Exception as e: print(f"Independent Run Error: {e}")