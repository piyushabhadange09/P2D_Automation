import requests
import os
import urllib3

# Suppress insecure request warnings (equivalent to -k in curl)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
PW_FILE_PATH = os.path.expanduser('~/.sysadmin.pw')
BASE_URL = "https://localhost:5000/transactionhistory/v1/putthhistorypaper" 
USERNAME = "sysadmin@tracelink.com"
LOG_FILE = "api_response.xml"

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
    xml_payload = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<ns2:PaperTransactionHistory xmlns:ns2="urn:tracelink:transactionhistory">
<TranasactionHistory>
  <CompanyID>a0f0e427-d4e4-410f-ac7a-c304a20c64de</CompanyID>
  <CompanyLocationID>f42c7ad8-b8b5-49e7-af5b-ca36e7efea18</CompanyLocationID>
  <SubscriberID>f42c7ad8-b8b5-49e7-af5b-ca36e7efea18</SubscriberID>
  <ServiceID>e468b292-53ed-49bf-9df0-dde8dcdbbd10</ServiceID>
  <State>ACTIVE</State>
  <DeliveryNumber>400607</DeliveryNumber>
  <AID>9ea07ebc-67b2-49dd-ad97-36f8f5a839ea</AID>
  <Txns>
    <TxnDate>2023-09-26T00:00:00.000Z</TxnDate>
    <SrtDt>2023-09-26T00:00:00.000Z</SrtDt>
    <ShipDate>2023-09-26T00:00:00.000Z</ShipDate>
    <TxType>RECEIPT</TxType>
    <Qty>3</Qty>
    <TxFrom>
      <ID>00184TRLK</ID>
      <IDT>HIN</IDT>
      <DSCSABR>IndirectSupplier</DSCSABR>
      <BN>Bayer AG</BN>
      <S1>Kaiser-Wilhelm-Allee 1</S1>
      <C>Leverkusen</C>
      <State>NW</State>
      <PC>51373</PC>
      <Country>DE</Country>
    </TxFrom>
    <TxTo>
      <ID>1100007476668</ID>
      <IDT>GLN</IDT>
      <BN>BriovaRx</BN>
      <S1>53 Darling Ave</S1>
      <C>South Portland</C>
      <State>ME</State>
      <PC>04106</PC>
      <Country>US</Country>
    </TxTo>
    <ProductOrigin>IndirectPurchase</ProductOrigin>
  </Txns>
  <TS>false</TS>
  <IsFromPaper>true</IsFromPaper>
  <PI>
    <NDC>50419039501</NDC>
    <NDCType>NDC542</NDCType>
    <Lot>2148729</Lot>
    <ExpDate>2026-01-31</ExpDate>
    <ProdName>NUBEQA</ProdName>
    <ProdStrength>300 MG</ProdStrength>
    <Dosage>Tablet</Dosage>
    <ContainerSz>120</ContainerSz>
    <Manufacturer>Bayer</Manufacturer>
  </PI>
  <CD>2026-04-15T11:02:04.417Z</CD>
  <CUID>e49e3fe0-e6b2-4f1f-9090-d1676f522fea</CUID>
</TranasactionHistory>
</ns2:PaperTransactionHistory>"""



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