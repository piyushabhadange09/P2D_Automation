import requests
import os
import urllib3

# Suppress insecure request warnings (equivalent to -k in curl)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
PW_FILE_PATH = os.path.expanduser('~/.sysadmin.pw')
BASE_URL = "https://localhost:5000/transactionhistory/v1/puttexchange" 
USERNAME = "sysadmin@tracelink.com"
LOG_FILE = "apitransaction_response.xml"

def get_password():
    """Reads the password from the hidden sysadmin file."""
    try:
        with open(PW_FILE_PATH, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: Password file not found at {PW_FILE_PATH}")
        return None

def hit_put_endpoint():
    pw = get_password()
    if not pw: return

    # The XML payload wrapping the transaction history 
    xml_payload = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns3:TransactionExchange xmlns:ns2="urn:tracelink:infoexchange" xmlns:ns3="urn:tracelink:transactionhistory">
    <CompanyID>57add227-8c21-470c-b792-36d8debcca1c</CompanyID>
    <ServiceID>d9e07ef3-15d4-40a4-bb58-cccdd7cbee7d</ServiceID>
    <SubscriberID>8858828b-31b0-4e8f-b01a-daa2c5a49b30</SubscriberID>
    <CompanyLocationID>57add227-8c21-470c-b792-36d8debcca1c</CompanyLocationID>
    <TxType>RECEIPT</TxType>
    <DN>DN132</DN>
    <ShipDate>2026-04-13T00:00:00.000Z</ShipDate>
    <IDS>Delivery:DN132</IDS>
    <NDCList>NDC541|11111-2222-4</NDCList>
    <LotList>2344</LotList>
    <Qty>10</Qty>
    <SenderID>4255363737123</SenderID>
    <SenderName>kaustubh VCMO</SenderName>
    <RecipientID>4255363737123</RecipientID>
    <RecipientName>kaustubh VCMO</RecipientName>
    <shipFromLocation>
        <ID>4255363737123</ID>
        <IDT>GLN</IDT>
        <BN>kaustubh VCMO</BN>
        <S1>Aromatic 1</S1>
        <C>Cincinati</C>
        <State>Bos</State>
        <PC>401501</PC>
        <Country>US</Country>
    </shipFromLocation>
    <shipToLocation>
        <ID>4255363737123</ID>
        <IDT>GLN</IDT>
        <BN>kaustubh VCMO</BN>
        <S1>Aromatic 1</S1>
        <C>Cincinati</C>
        <State>Bos</State>
        <PC>401501</PC>
        <Country>US</Country>
    </shipToLocation>
    <IsFromPaper>true</IsFromPaper>
    <IsFullyReceived>false</IsFullyReceived>
    <State>ACTIVE</State>
    <IsSerialized>false</IsSerialized>
</ns3:TransactionExchange>"""



    headers = {
        "Content-Type": "application/xml",
        "Accept": "application/xml"
    }

    print(f"--- Sending PUT request to: {BASE_URL} ---")
    
    try:
        # We wrap this in a Session or use Request object to inspect what's actually being sent
        session = requests.Session()
        req = requests.Request('PUT', BASE_URL, data=xml_payload, headers=headers, auth=(USERNAME, pw))
        prepared = req.prepare()

        # --- Debug: Inspect the Prepared Request ---
        print("\n--- REQUEST DEBUG START ---")
        print(f"Endpoint: {prepared.url}")
        print(f"Method:   {prepared.method}")
        print(f"Headers:  {prepared.headers}")
        # Note: prepared.body will be the byte-encoded version of your string
        print("--- REQUEST DEBUG END ---\n")

        response = session.send(prepared, verify=False, timeout=15)
        
        print(f"Status Code: {response.status_code}")
        
        # Write response to file
        with open(LOG_FILE, "w") as f:
            f.write(response.text)
        
        if response.status_code == 200:
            print(f"[SUCCESS] Response saved to {LOG_FILE}")
        elif response.status_code == 404:
            print(f"[404 ERROR] The server says this URL does not exist.")
            print(f"Check if 'putthistorypaper' (double 't') is correct in the Java @Path annotation.")
        else:
            print(f"[FAILED] Status {response.status_code}. Check {LOG_FILE}")
            
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

if __name__ == "__main__":
    hit_put_endpoint()