import json
import os
import shutil
import requests
import urllib3
from datetime import datetime
from lxml import etree

import P2Dpart8 as th_gen
import P2Dpart9 as tx_gen
import P2Dpart10 as art_gen

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
URL_TE = "https://localhost:5000/transactionhistory/v1/puttexchange"
URL_TH = "https://localhost:5000/transactionhistory/v1/putthhistorypaper"
URL_ART = "https://localhost:5000/artifact/v1/put"
USERNAME = "sysadmin@tracelink.com"
PW_FILE = os.path.expanduser('~/.sysadmin.pw')

# Requirement: Headers from working P2Dpart7.py
HEADERS = {
    "Content-Type": "application/xml",
    "Accept": "application/xml"
}

def get_id_from_response(response_text):
    """Parses the XML response to extract the <ID> tag."""
    try:
        root = etree.fromstring(response_text.encode('utf-8'))
        return root.findtext(".//ID") or "N/A"
    except: return "FAILED"

def validate_entry(entry):
    """Performs null checks on mandatory JSON fields."""
    missing = [k for k in ["Transfer From", "Transaction Date", "Delivery Number", "PDF Name"] if not entry.get(k)]
    for prod in entry.get("Product details", []):
        for p_val in prod.values():
            for f in ["Quantity","NDC"]:
                if not p_val.get(f): missing.append(f)
    return list(set(missing))

def main():
    if not os.path.exists(PW_FILE): 
        print(f"Password file missing: {PW_FILE}")
        return
        
    pw = open(PW_FILE).read().strip()
    today_str = datetime.now().strftime("%Y%m%d")
    
    input_dir = "./Input"
    pdf_dir = "./PDF"
    output_today = os.path.join("./Output", today_str)
    done_today = os.path.join("./Done", today_str)

    if not os.path.exists(input_dir):
        print(f"Input directory not found: {input_dir}")
        return

    files_to_process = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not files_to_process:
        print("No .txt files found in the Input folder. Exiting flow.")
        return

    os.makedirs(output_today, exist_ok=True)
    os.makedirs(done_today, exist_ok=True)

    c_md = etree.parse('BRIOVARX_CompanyPartnerMD.xml')
    p_md = etree.parse('BRIOVARX_ProductMD.xml')
    rb_md = etree.parse('Redbook_20250403.xml')

    for txt_file in files_to_process:
        input_file_path = os.path.join(input_dir, txt_file)
        log_path = os.path.join(output_today, f"LOG_{txt_file}")
        
        with open(input_file_path, 'r') as f, open(log_path, 'w') as log:
            # Helper to log to file and print to console
            def log_and_print(message):
                log.write(message)
                print(message.strip())

            try:
                data = json.load(f)
                entries = data if isinstance(data, list) else [data]
                
                for entry in entries:
                    dn = entry.get("Delivery Number", "N/A")
                    pdf = entry.get("PDF Name", "N/A")
                    pg = entry.get("Page Number", "N/A")
                    stat = entry.get("Status", "")
                    prefix = f"DN: {dn} | PDF: {pdf} | PG: {pg}"
                    
                    if stat in ['Needs Additional Information', 'Missing TS', 'Skipped']:
                        log_and_print(f"{prefix} | SKIPPED: Status '{stat}'\n")
                        continue

                    missing_fields = validate_entry(entry)
                    if missing_fields:
                        log_and_print(f"{prefix} | DISCARDED: Missing fields {missing_fields}\n")
                        continue

                    # CHECK FOR PDF EXISTENCE BEFORE API CALLS
                    pdf_full_path = os.path.join(pdf_dir, pdf)
                    if not os.path.exists(pdf_full_path):
                        log_and_print(f"{prefix} | DISCARDED: PDF file not found at {pdf_full_path}. Skipping all API calls.\n")
                        continue

                    try:
                        aid = th_gen.generate_secure_uuid()
                        
                        # 1. TE API Call
                        try:
                            tx_xml = tx_gen.build_tx_xml_from_data(entry, c_md, p_md, rb_md)
                            tx_res = requests.put(URL_TE, data=tx_xml, headers=HEADERS, auth=(USERNAME, pw), verify=False)
                            te_id = get_id_from_response(tx_res.text)
                            
                            if not tx_res.ok:
                                log_and_print(f"{prefix} | STEP: TE API | FAILED: {tx_res.status_code} | RESPONSE: {tx_res.text}\n")
                                continue
                            log_and_print(f"{prefix} | STEP: TE API | SUCCESS | ID: {te_id}\n")
                        except ValueError as e:
                            log_and_print(f"{prefix} | STEP: TE API | SKIPPED: {str(e)}\n")
                            continue

                        # 2. TH API Calls
                        th_ids = []
                        for prod in entry.get("Product details", []):
                            for k, v in prod.items():
                                try:
                                    th_xml = th_gen.build_th_xml(k, v, entry, c_md, p_md, rb_md, aid)
                                    th_res = requests.put(URL_TH, data=th_xml, headers=HEADERS, auth=(USERNAME, pw), verify=False)
                                    
                                    if th_res.ok:
                                        current_th_id = get_id_from_response(th_res.text)
                                        th_ids.append(current_th_id)
                                        log_and_print(f"{prefix} | STEP: TH API ({k}) | SUCCESS | ID: {current_th_id}\n")
                                    else:
                                        log_and_print(f"{prefix} | STEP: TH API ({k}) | FAILED: {th_res.status_code} | RESPONSE: {th_res.text}\n")
                                except ValueError as e:
                                    log_and_print(f"{prefix} | STEP: TH API ({k}) | SKIPPED: {str(e)}\n")

                        # 3. Artifact API Call
                        if th_ids:
                            art_xml = art_gen.build_artifact_xml(pdf_full_path, aid, th_ids[-1])
                            art_res = requests.put(URL_ART, data=art_xml, headers=HEADERS, auth=(USERNAME, pw), verify=False)
                            art_id = get_id_from_response(art_res.text)
                            
                            if not art_res.ok:
                                log_and_print(f"{prefix} | STEP: ART API | FAILED: {art_res.status_code} | RESPONSE: {art_res.text}\n")
                                continue
                            
                            log_and_print(f"{prefix} | STEP: ART API | SUCCESS | ID: {art_id}\n")
                            log_and_print(f"{prefix} | FINAL STATUS: ALL APIS PROCESSED\n\n")
                        else:
                            log_and_print(f"{prefix} | FINAL STATUS: DISCARDED (No successful THs created)\n\n")

                    except Exception as e:
                        log_and_print(f"{prefix} | CRITICAL ERROR during processing: {str(e)}\n\n")
            except Exception as e:
                log_and_print(f"FILE LEVEL ERROR in {txt_file}: {str(e)}\n")
        
        # This moves the file from ./Input to ./Done/[Date]/ without creating an "Input" subfolder
        shutil.move(input_file_path, os.path.join(done_today, txt_file))

if __name__ == "__main__":
    main()