import requests
from bs4 import BeautifulSoup
import common
from io import BytesIO
import re
from typing import List, Dict
import pandas as pd
import os
from datetime import datetime
from urllib.parse import urlsplit, unquote
from urllib.parse import urljoin
import xlrd


errors = []
data = []

uniqueIdentity = 'AR0841'
region = 'Middle East and Africa'
jurisdiction = 'GCC'
category = 'Cosmetics/Personal Care'
title = 'GCC. List of Restricted Substances in Cosmetic Products, Annex III (GSO 1943, July 2021)'
casKeyValue = "CAS_Number"
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

def clean_cell(cell):
    if isinstance(cell, float) and cell.is_integer():
        return int(cell)
    return cell

def extract_excel_data(download_path):
    try:
        book = xlrd.open_workbook(download_path, ignore_workbook_corruption=True)
        sheet = book.sheet_by_index(0)

        all_rows = [sheet.row_values(i) for i in range(sheet.nrows)]

        row7 = all_rows[6]
        row8 = all_rows[7]

        headers = []
        valid_indices = []

        for i, (main, sub) in enumerate(zip(row7, row8)):
            main_clean = str(main).strip().replace('\n', ' ')
            sub_clean = str(sub).strip().replace('\n', ' ')

            if main_clean and sub_clean:
                header = f"{main_clean} - {sub_clean}"
            elif sub_clean:
                header = sub_clean
            elif main_clean:
                header = main_clean
            else:
                header = None

            if header:
                headers.append(header)
                valid_indices.append(i)

        def clean_cell(cell):
            if isinstance(cell, float) and cell.is_integer():
                return int(cell)
            return cell

        data_rows = [
            [clean_cell(row[i]) for i in valid_indices]
            for row in all_rows[8:]
        ]

        df = pd.DataFrame(data_rows, columns=headers)
        df.dropna(axis=0, how='all', inplace=True)

        return df

    except Exception as e:
        print(f"❌ Failed to read Excel file: {e}")
        return pd.DataFrame()
    

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
            excel_url = "https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/III/export-xls"
            target_directory = folder_path
            download_file(excel_url, target_directory,"COSING_Annex_III_v2.xls")

            try:
                list_info_path = os.path.join(folder_path,"COSING_Annex_III_v2.xls")
                print(f"😊 Capturing data from LIST OF SUBSTANCES… please wait ⏳")
                first_table_data = extract_excel_data(list_info_path)
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
            print(f"✅ {len(first_table_data)} ROWS AFFECTED LIST_OF_SUBSTANCES")          
        
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
