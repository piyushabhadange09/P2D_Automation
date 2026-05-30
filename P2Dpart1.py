import xml.etree.ElementTree as ET
import pandas as pd
import os
import sys

def extract_xml_to_excel(input_xml_name, output_excel_name):
    """
    Extracts data from the 'Upload Paper Here' directory in a specific XML.
    """
    # The directory path on your Linux server
    base_path = '/site/services/home/kpathak/S3Encryption/DocDirectory/'
    output_path = '/site/services/home/kpathak/S3Encryption/DocDirectoryOutput/'
    
    xml_full_path = os.path.join(base_path, input_xml_name)
    excel_full_path = os.path.join(output_path, output_excel_name)

    if not os.path.exists(xml_full_path):
        print(f"Error: XML file not found at {xml_full_path}")
        sys.exit(1)

    try:
        # Load and parse the XML
        tree = ET.parse(xml_full_path)
        root = tree.getroot()
        data = []

        # Find the 'Upload Paper Here' directory and its files
        search_query = ".//Children[DirectoryName='Upload Paper Here']/Files"
        
        for file_node in root.findall(search_query):
            key_val = file_node.findtext('Key')
            desc_val = file_node.findtext('Description')
            
            if key_val and desc_val:
                data.append({
                    'Key': key_val,
                    'Description': desc_val,
                    'Concat Name': f"{key_val}{desc_val}" # Concatenates Key and Description values
                })

        if data:
            df = pd.DataFrame(data)
            # Writing to Excel file with 3 columns
            df.to_excel(excel_full_path, index=False)
            print(f"Success! Extracted {len(data)} items to: {excel_full_path}")
        else:
            print(f"No files found in 'Upload Paper Here' directory in {input_xml_name}.")

    except Exception as e:
        print(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    # Check if the correct number of arguments are passed
    if len(sys.argv) != 3:
        print("Usage: python3 extract_data.py <input_xml_file> <output_excel_file>")
        print("Example: python3 extract_data.py 0466df10-999a-4a61-8c69-97347ba43bfb.xml Results.xlsx")
    else:
        # Pass the command line arguments to the function
        extract_xml_to_excel(sys.argv[1], sys.argv[2])