import requests
import os
import urllib3
import logging

# --- Simplified Logging ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
PW_FILE_PATH = os.path.expanduser('~/.sysadmin.pw')
BASE_URL = "https://localhost:5000/artifact/v1/put" 
USERNAME = "sysadmin@tracelink.com"
LOG_FILE = "apiartifact_response.xml"
# The pre-formatted XML file you want to send
INPUT_XML_FILE = "ArtifactBody.xml" 

def get_password():
    try:
        with open(PW_FILE_PATH, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Password file not found at {PW_FILE_PATH}")
        return None

def hit_put_endpoint():
    pw = get_password()
    if not pw: return

    # 1. Read the existing XML file
    if not os.path.exists(INPUT_XML_FILE):
        logger.error(f"Input XML file not found: {INPUT_XML_FILE}")
        return

    try:
        with open(INPUT_XML_FILE, 'r', encoding='utf-8') as f:
            xml_payload = f.read()
        logger.info(f"Loaded XML payload from {INPUT_XML_FILE}")
    except Exception as e:
        logger.error(f"Failed to read XML file: {e}")
        return

    # 2. Setup Headers
    headers = {
        "Content-Type": "application/xml",
        "Accept": "application/xml"
    }

    # 3. Send Request
    logger.info(f"Attempting PUT to {BASE_URL}...")
    try:
        response = requests.put(
            BASE_URL, 
            data=xml_payload.encode('utf-8'), # Ensure it is sent as UTF-8 bytes
            headers=headers, 
            auth=(USERNAME, pw), 
            verify=False, 
            timeout=60
        )
        
        logger.info(f"Response Status: {response.status_code}")
        
        # Save response for review
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            f.write(response.text)
            
        if response.status_code == 200 or response.status_code == 201:
            logger.info("Request Successful.")
        else:
            # Print the server's error message directly to the console
            logger.error(f"Server rejected request with 400. Details: {response.text}")
            
    except Exception as e:
        logger.error(f"Request failed: {e}")

if __name__ == "__main__":
    hit_put_endpoint()