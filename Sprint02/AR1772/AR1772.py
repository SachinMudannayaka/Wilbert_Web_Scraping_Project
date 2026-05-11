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


uniqueIdentity = 'AR1772'
region = 'Global Inventories'
jurisdiction = 'US'
category = 'New Chemical Notification'
title = 'USA. TSCA Inventory Synonyms'
casKeyValue = "CAS_#"
date_str = datetime.now().strftime("%m%d%Y")
folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br"
}
check_value = False

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

def download_file(url, target_directory, file_name):
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

def read_epa_excel_data(local_file_path, file_name):
    try:
        excel_data = pd.read_excel(local_file_path, engine='openpyxl')
        if excel_data.empty:
            raise ValueError(f"{file_name} Excel file is empty.")

        records = excel_data.to_dict(orient='records')
        for record in records:
            record["File Name"] = file_name

        return records

    except FileNotFoundError:
        log_error(f"File not found: {local_file_path}")
    except ValueError as e:
        log_error(f"Data error: {e}")
    except Exception as e:
        log_error(f"Unexpected error: {e}")

    return []

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main(check_):
    try:
        try:
            common.deleteTodayFiles(uniqueIdentity)
        except Exception as e:
            log_error(f"Error deleting today's files: {e}")

        try:
            base_url_1 = "https://cdxapps.epa.gov/oms-substance-registry-services/api/substance-lists/export/listInfo/169"
            file_name_info = "LIST INFO"
            target_directory = folder_path
            download_file(base_url_1, target_directory,"LIST_INFO.xlsx")
            try:
                list_info_path = os.path.join(folder_path, 'LIST_INFO.xlsx')
                print(f"😊 Capturing data from {file_name_info}… please wait ⏳")
                first_sheet_data = read_epa_excel_data(list_info_path,file_name_info)
                first_sheet_data = first_sheet_data if not check_ else first_sheet_data[:100]
            except Exception as e:
                log_error(f"Error reading Excel data: {e}")
                first_sheet_data = []

        except Exception as e:
            log_error(f"Error downloading: {e}") 


        try:
            base_url_2 = "https://cdxapps.epa.gov/oms-substance-registry-services/api/substance-lists/export/synonymInfo/169"
            target_directory = folder_path
            download_file(base_url_2, target_directory,"SYNONYM_INFO.xlsx")
            try:
                syno_path = os.path.join(folder_path, 'SYNONYM_INFO.xlsx')
                file_name_syn = "SYNONYM INFO"
                print(f"😊 Capturing data from {file_name_syn}… please wait ⏳")
                second_sheet_data = read_epa_excel_data(syno_path,file_name_syn)
                second_sheet_data = second_sheet_data if not check_ else second_sheet_data[:100]
            except Exception as e:
                log_error(f"Error reading Excel data: {e}")
                second_sheet_data = []
        except Exception as e:
            log_error(f"Error downloading: {e}")      
               
            
    except Exception as e:
        log_error(f"General error in main: {e}")

    finally:
        try:
            create_final_json_file(first_sheet_data)
            print(f"✅ {len(first_sheet_data)} ROWS AFFECTED IN LIST_INFO SHEET")

            create_final_json_file(second_sheet_data)
            print(f"✅ {len(second_sheet_data)} ROWS AFFECTED IN SYNONYM INFO SHEET")
        
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main(check_value)
