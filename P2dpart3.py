import pandas as pd
import xml.etree.ElementTree as ET
import base64
import os
import sys

def process_xml_to_files(excel_filename):
    # Define paths
    base_dir = '/site/services/home/kpathak/S3Encryption/ATS-23134'
    excel_path = os.path.join(base_dir, 'DocDirectoryOutput', excel_filename)
    xml_dir = os.path.join(base_dir, 'Document')
    # Unified output directory
    output_dir = os.path.join(base_dir, 'TransformedOutput')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # 1. Read the Excel mapping
        df = pd.read_excel(excel_path)
        
        print(f"Starting transformation for {len(df)} files...")

        for index, row in df.iterrows():
            key = str(row['Key'])
            concat_name = str(row['Concat Name']) # e.g., "image1.png" or "doc1.pdf"
            
            xml_file_path = os.path.join(xml_dir, key)

            if not os.path.exists(xml_file_path):
                print(f"Skipping: XML file '{key}' not found.")
                continue

            try:
                # 2. Parse the XML to find the Base64 string
                tree = ET.parse(xml_file_path)
                root = tree.getroot()

                # Extract the encoded string from the <Document64> tag
                base64_content = root.findtext('Document64')

                if base64_content:
                    # 3. Decode the Base64 string into raw bytes
                    file_data = base64.b64decode(base64_content)

                    # 4. Save using the 'Concat Name' (preserves .pdf, .png, .jpg)
                    output_file_path = os.path.join(output_dir, concat_name)
                    
                    with open(output_file_path, 'wb') as f:
                        f.write(file_data)
                    
                    print(f"Successfully created: {concat_name}")
                else:
                    print(f"Error: <Document64> tag empty in {key}")

            except Exception as e:
                print(f"Failed to process {key}: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <excel_filename>")
    else:
        process_xml_to_files(sys.argv[1])