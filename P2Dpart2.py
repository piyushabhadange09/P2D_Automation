import pandas as pd
import subprocess
import os
import sys
import time

def fetch_files_with_delay(excel_filename):
    """
    Reads 'Key' values from Excel and executes the S3Encrypter script directly.
    """
    # Directory paths
    output_dir = '/site/services/home/kpathak/S3Encryption/DocDirectoryOutput/'
    excel_path = os.path.join(output_dir, excel_filename)

    if not os.path.exists(excel_path):
        print(f"Error: Excel file not found at {excel_path}")
        return

    try:
        # Load the Excel file containing extracted Key values
        df = pd.read_excel(excel_path)
        
        if 'Key' not in df.columns:
            print("Error: 'Key' column not found in the Excel file.")
            return

        # Get unique keys
        keys = df['Key'].dropna().unique()
        total_keys = len(keys)
        print(f"Found {total_keys} keys. Starting download process...")

        for index, key in enumerate(keys, 1):
            # Construct the direct command using the script path and parameters
            # We use 'Document/{key}' as the target path
            command = f"./bin/S3Encrypter.sh --bucket static --get Document/{key}"
            
            print(f"[{index}/{total_keys}] Running: {command}")

            try:
                # Run the command. stdin=subprocess.DEVNULL prevents the script 
                # from hanging or stopping early by blocking input requests.
                subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    stdin=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError as e:
                print(f"Error for key {key}: Script exited with status {e.returncode}")

            # 1-second delay between executions
            if index < total_keys:
                time.sleep(1)

        print("\nAll files processed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_s3.py <excel_filename>")
    else:
        fetch_files_with_delay(sys.argv[1])