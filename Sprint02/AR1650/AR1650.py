import requests
from bs4 import BeautifulSoup
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict
import pandas as pd
import openpyxl
import os
import zipfile
from datetime import datetime

errors = []
data = []

uniqueIdentity = 'AR1650'
region = 'North America'
jurisdiction = 'US'
category = 'Chemicals and Materials'
title = 'TSCA. 2020 Chemical Data Reporting (CDR) Results (as published 25 January 2023)'
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

def get_2020_cdr_excel_link(soup):
    try:
        h2_2020 = None
        for h2 in soup.find_all('h2'):
            if "2020 CDR Data" in h2.get_text():
                h2_2020 = h2
                break
        if not h2_2020:
            return None
        
        li_tag = None
        for li in h2_2020.find_all_next('li'):
            if 'Download the 2020 CDR data' in li.get_text():
                li_tag = li
                break
        if not li_tag:
            return None

        ul_tag = li_tag.find('ul') or li_tag.find_next_sibling('ul')
        if not ul_tag:
            return None

        for a in ul_tag.find_all('a'):
            if 'Excel' in a.get_text() and a.get('href', '').endswith('.zip'):
                href = a['href']
                return 'https://www.epa.gov' + href if href.startswith('/') else href

        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def download_and_extract_excel_zip(url, target_directory):
    try:
        os.makedirs(target_directory, exist_ok=True)

        zip_path = os.path.join(target_directory, 'cdx_data.zip')
        print(f"Please wait a moment… downloading ZIP ⏳")
        response = requests.get(url)
        response.raise_for_status()

        with open(zip_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ ZIP downloaded to: {zip_path}")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_directory)
        print(f"✅ ZIP extracted to: {target_directory}")

        os.remove(zip_path)

        print("✅ Zip removed & Excel files retained.")

    except Exception as e:
        print(f"Error: {e}")

def read_epa_excel_data(source):
    try:
        if source.startswith('http://') or source.startswith('https://'):
            response = requests.get(source)
            response.raise_for_status()
            excel_data = pd.read_excel(BytesIO(response.content), engine='openpyxl')
        else:
            if not os.path.isfile(source):
                raise FileNotFoundError(f"File not found: {source}")
            print("Reading Excel files. Please wait ⏳")
            excel_data = pd.read_excel(source, engine='openpyxl')

        if excel_data.empty:
            raise ValueError("Excel file is empty.")

        records = excel_data.to_dict(orient='records')
        return records

    except requests.exceptions.RequestException as e:
        log_error(f"Request error: {e}")
    except FileNotFoundError as e:
        log_error(f"File error: {e}")
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

def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)

        base_url = "https://www.epa.gov/chemical-data-reporting/access-chemical-data-reporting-data"
        soup = getSoup(base_url)
        if soup:
            try:
                zip_link = get_2020_cdr_excel_link(soup)
                if zip_link:
                    try:
                        target_directory = folder_path
                        download_and_extract_excel_zip(zip_link, target_directory)
                    except Exception as e:
                        log_error(f"Error downloading and extracting zip: {e}")
                    
                    try:
                        con_com_file_path =  os.path.join(folder_path, '2020 CDR Consumer and Commercial Use Information.xlsx')
                        con_com_data = read_epa_excel_data(con_com_file_path)
                    except Exception as e:
                        log_error(f"Error reading Consumer and Commercial Use data: {e}")
                    
                    try:
                        indus_pro_file_path =  os.path.join(folder_path, '2020 CDR Industrial Processing and Use Information.xlsx')
                        indus_pro_data = read_epa_excel_data(indus_pro_file_path)
                    except Exception as e:
                        log_error(f"Error reading Industrial Processing and Use data: {e}")
                    
                    try:
                        manu_impo_file_path =  os.path.join(folder_path, '2020 CDR Manufacture-Import Information.xlsx')
                        manu_impo_data = read_epa_excel_data(manu_impo_file_path)
                    except Exception as e:
                        log_error(f"Error reading Manufacture-Import data: {e}")
                    
                    try:
                        manu_impo_file_path =  os.path.join(folder_path, '2020 CDR Nationally Aggregated Production Volumes.xlsx')
                        nation_agg_data = read_epa_excel_data(manu_impo_file_path)
                    except Exception as e:
                        log_error(f"Error reading Nationally Aggregated Production Volumes data: {e}")
            except Exception as e:
                log_error(f"Error processing zip link or files: {e}")
    except Exception as e:
        log_error(f"General error in main: {e}")
    finally:
        try:
            create_final_json_file(con_com_data)
            print(f"✅ {len(con_com_data)} ROWS AFFECTED")

            create_final_json_file(indus_pro_data)
            print(f"✅ {len(indus_pro_data)} ROWS AFFECTED")

            create_final_json_file(manu_impo_data)
            print(f"✅ {len(manu_impo_data)} ROWS AFFECTED")

            create_final_json_file(nation_agg_data)
            print(f"✅ {len(nation_agg_data)} ROWS AFFECTED")

        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()