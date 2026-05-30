import pandas as pd
import requests
import os
import sys
import time
import urllib3

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
BASE_DIRECTORY = '/site/services/home/kpathak/S3Encryption/ATS-23134/DocDirectoryOutput'
PW_FILE_PATH = os.path.expanduser('~/.sysadmin.pw')
BASE_URL = "https://localhost:5000/document/v2/movedoc"
USERNAME = "sysadmin@tracelink.com"

def get_password():
    """Reads the password from the hidden sysadmin file."""
    try:
        with open(PW_FILE_PATH, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: Password file not found at {PW_FILE_PATH}")
        return None

def process_moves(file_name):
    full_path = os.path.join(BASE_DIRECTORY, file_name)
    pw = get_password()
    if not pw: return

    try:
        df = pd.read_excel(full_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    success_count = 0
    failure_count = 0
    skipped_count = 0

    print(f"--- Starting Process for: {file_name} ---")
    
    for index, row in df.iterrows():
        try:
            process_id = row['ProcesslinkId']
            key_id = row['Key']
            target_id = row['Target folder']

            # --- SKIP LOGIC START ---
            # Checks if value is NaN, None, or an empty string/whitespace
            if pd.isna(target_id) or str(target_id).strip() == "":
                print(f"[SKIPPED] Row {index+1}: Missing 'Target folder' value.")
                skipped_count += 1
                continue 
            # --- SKIP LOGIC END ---

            url = f"{BASE_URL}/{process_id}/{key_id}/{target_id}"

            response = requests.get(
                url, 
                auth=(USERNAME, pw), 
                verify=False
            )
            
            duration = response.elapsed.total_seconds()

            if response.status_code == 200:
                print(f"[SUCCESS] Row {index+1}: Key {key_id} | Time: {duration:.3f}s")
                success_count += 1
            else:
                print(f"[FAILED ] Row {index+1}: Status {response.status_code} | Time: {duration:.3f}s")
                failure_count += 1
            
        except Exception as e:
            print(f"[ERROR  ] Row {index+1}: {e}")
            failure_count += 1

    print("-" * 30)
    print(f"Process Complete for {file_name}.")
    print(f"Total Successes: {success_count}")
    print(f"Total Failures:  {failure_count}")
    print(f"Total Skipped:   {skipped_count}")
    print("-" * 30)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        process_moves(sys.argv[1])
    else:
        print("Usage: python script_name.py your_excel_file.xlsx")