import base64
import os
from lxml import etree
from datetime import datetime, timezone

def build_artifact_xml(pdf_path, shared_aid, last_th_id):
    """
    Encodes the PDF and maps the AID and TH_ID to the specific 
    Artifact XML format provided in Art_57221.xml.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    # Base64 Encoding of the PDF
    with open(pdf_path, "rb") as f:
        file_data = f.read()
        encoded_pdf = base64.b64encode(file_data).decode('utf-8')
        file_length = len(file_data)

    pdf_filename = os.path.basename(pdf_path)
    # Modern UTC timestamp
    now_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    author_id = "e49e3fe0-e6b2-4f1f-9090-d1676f522fea" 
    
    root = etree.Element("artifact")
    
    # 1. ArtifactID - Matches the AID from Transaction History
    etree.SubElement(root, "ArtifactID").text = shared_aid
    
    # 2. LastChange Block
    last_change = etree.SubElement(root, "LastChange")
    etree.SubElement(last_change, "Created").text = now_ts
    etree.SubElement(last_change, "Author").text = author_id
    etree.SubElement(last_change, "Updated").text = now_ts
    etree.SubElement(last_change, "LastModifier").text = author_id
    
    # 3. AttachedTo Block - Uses the ID from the final TH API response
    attached_to_block = etree.SubElement(root, "AttachedTo")
    etree.SubElement(attached_to_block, "AttachedTo").text = last_th_id
    etree.SubElement(attached_to_block, "AttachedToDisplay").text = last_th_id
    etree.SubElement(attached_to_block, "AttachedToType").text = "PAPER_TRANSACTION_HISTORY"
    
    # 4. Metadata Tags
    etree.SubElement(root, "datePosted").text = now_ts
    etree.SubElement(root, "Filename").text = pdf_filename
    etree.SubElement(root, "MimeType").text = "application/pdf"
    etree.SubElement(root, "Length").text = str(file_length)
    
    # 5. Description
    description_text = f"Scanned Transaction History Paper File: name={pdf_filename}, size={file_length}, user={author_id}, dateTime={now_ts}"
    etree.SubElement(root, "Description").text = description_text
    
    # 6. Artifact64 (The encoded version of the PDF)
    etree.SubElement(root, "Artifact64").text = encoded_pdf
    
    # 7. Deleted Status
    etree.SubElement(root, "Deleted").text = "false"

    # Returns XML with the required static declaration and standalone="yes"
    return etree.tostring(
        root, 
        xml_declaration=True, 
        encoding="UTF-8", 
        standalone="yes", 
        pretty_print=True
    ).decode('utf-8')

# --- TEST BLOCK FOR STANDALONE EXECUTION ---
if __name__ == "__main__":
    # Update these values to test with a real file in your ./PDF folder
    TEST_PDF_NAME = "4cab9320-7284-4199-adcb-61e6767cdb97TRACELINK SCANS 10-30-2024_SANDOZ_492704_13.pdf" 
    TEST_PDF_PATH = os.path.join("./PDF", TEST_PDF_NAME)
    MOCK_AID = "test-uuid-shared-aid-12345"
    MOCK_TH_ID = "api-response-th-id-67890"

    try:
        print(f"--- Testing Artifact XML Generation for: {TEST_PDF_NAME} ---")
        xml_output = build_artifact_xml(TEST_PDF_PATH, MOCK_AID, MOCK_TH_ID)
        print(xml_output)
    except FileNotFoundError as e:
        print(f"Error: {e}. Please ensure the file exists in the ./PDF directory.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")