import requests
from bs4 import BeautifulSoup
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict
import pandas as pd
import os
from datetime import datetime
from urllib.parse import urlsplit, unquote

errors = []
data = []

uniqueIdentity = 'AR0572'
region = 'Middle East and Africa'
jurisdiction = 'EG'
category = 'Workplace Safety (OELs, BELs, GLP)'
title = 'Egypt. OELs. Carcinogens or suspected carcinogens with no threshold limit (prohibited) (Decree No.338, 1995, as amended through Decree No. 710, Annex 8, Table 3, 2012)'
casKeyValue = ""
date_str = datetime.now().strftime("%m%d%Y")
folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br"
}

def log_error(message):
    errors.append(message)

def getSoup(url):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        log_error(f"Failed to fetch or parse URL {url}: {e}")
        return None


def get_all_links(url):
    return [url] 

def download_file(url, target_directory, file_name=None):
    try:
        os.makedirs(target_directory, exist_ok=True)

        print(f"⏳ Please wait... downloading file...")

        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        if not file_name:
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition and 'filename=' in content_disposition:
                file_name = content_disposition.split('filename=')[1].strip('"')
            else:
                file_name = "downloaded_file.xlsx"

        file_path = os.path.join(target_directory, file_name)

        with open(file_path, 'wb') as f:
            f.write(response.content)

        print(f"✅ File successfully downloaded to: {file_path}")
        return file_path

    except requests.exceptions.RequestException as e:
        print(f"🚨 Download failed: {e}")
    except Exception as e:
        print(f"😵 Unexpected error: {e}")

    return None

def extract_suspected_carcinogens(pdf_path):
    """
    Extracts the 11 suspected carcinogenic substances from the specified PDF.
    Returns them in the exact requested format.
    """
    substances = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                if "INDUSTRIAL MATERIALS OR OPERATIONS SUSPECTED" in text:
                    lines = text.split('\n')
                    start_index = None
                    
                    for i, line in enumerate(lines):
                        if "INDUSTRIAL MATERIALS OR OPERATIONS SUSPECTED" in line:
                            start_index = i + 2
                            break
                    
                    if start_index:
                        for line in lines[start_index:start_index+11]:
                            clean_line = line.strip()
                            if clean_line:  
                                substances.append({"substance_name": clean_line})
                        return substances
    
    except Exception as e:
        print(f"Error processing PDF: {e}")
    
    return substances

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main():
    try:
        try:
            common.deleteTodayFiles(uniqueIdentity)
        except Exception as e:
            log_error(f"Error deleting today's files: {e}")

        try:
            base_url_1 = "https://faolex.fao.org/docs/pdf/egy4986E.pdf"
            target_directory = folder_path
            download_file(base_url_1, target_directory,"Industrial_materials_or_operations_Suspected_of_being_Carcinogenic_.pdf")

            try:
                list_info_path = os.path.join(folder_path, 'Industrial_materials_or_operations_Suspected_of_being_Carcinogenic_.pdf')
                print(f"😊 Capturing data from Industrial_materials_or_operations_Suspected_of_being_Carcinogenic… please wait ⏳")
                first_table_data = extract_suspected_carcinogens(list_info_path)
            except Exception as e:
                log_error(f"Error reading Excel data: {e}")
                first_table_data = []

        except Exception as e:
            log_error(f"Error downloading: {e}") 

    except Exception as e:
        log_error(f"General error in main: {e}")

    finally:
        try:
            create_final_json_file(first_table_data)
            print(f"✅ {len(first_table_data)} ROWS AFFECTED FIRST TABLE")          
        
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
