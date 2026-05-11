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

uniqueIdentity = 'AR0741'
region = 'Western Europe'
jurisdiction = 'EU'
category = 'Consumer Products'
title = 'EU. Substances Restricted in Toys, Directive 2009/48/EC, OJ L 170/1, 30 June 2009, last amended by Directive (EU) 2021/903, 4 June 2021'
casKeyValue = ""
date_str = datetime.now().strftime("%m%d%Y")
folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Referer": "https://www.echa.europa.eu/substances-restricted-toys",
    "Origin": "https://www.echa.europa.eu",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
}

payload = {
    "p_p_id": "eucleflegislationlist_WAR_euclefportlet",
    "p_p_lifecycle": "2",
    "p_p_state": "normal",
    "p_p_mode": "view",
    "p_p_resource_id": "exportResults",
    "p_p_cacheability": "cacheLevelPage",
    "_eucleflegislationlist_WAR_euclefportlet_formDate": "1753247909782",
    "_eucleflegislationlist_WAR_euclefportlet_exportColumns": "name,ecNumber,casNumber,fld_pref,fld_cas,fld_euto_appname,fld_euto_expras,fld_euto_contlim,fld_euto_emitlim,fld_euto_rest,fld_euto_sml,fld_euto_notes",
    "_eucleflegislationlist_WAR_euclefportlet_orderByCol": "rmlName",
    "_eucleflegislationlist_WAR_euclefportlet_orderByType": "asc",
    "_eucleflegislationlist_WAR_euclefportlet_searchFormColumns": "",
    "_eucleflegislationlist_WAR_euclefportlet_searchFormElements": "",
    "_eucleflegislationlist_WAR_euclefportlet_substance_identifier_field_key": "",
    "_eucleflegislationlist_WAR_euclefportlet_total": "80",
    "_eucleflegislationlist_WAR_euclefportlet_exportType": "xls"
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

        response = requests.post(url, headers=headers,data=payload, timeout=30)
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

def read_excel_with_custom_headers(file_path):
    try:
        df = pd.read_excel(file_path, header=None)

        df.drop(columns=[3, 4], inplace=True)

        headers = df.iloc[4].tolist()

        data_rows = df.iloc[5:].copy()

        data_rows.columns = headers

        data_rows.dropna(how='all', inplace=True)

        return data_rows.to_dict(orient='records')

    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return []

def create_final_json_file(data,casKeyValue):
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
            base_url = "https://www.echa.europa.eu/web/guest/substances-restricted-toys?p_p_id=eucleflegislationlist_WAR_euclefportlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=exportResults&p_p_cacheability=cacheLevelPage"
            target_directory = folder_path
            download_file(base_url, target_directory,"toy_safety_.xlsx")

            try:
                list_info_path = os.path.join(folder_path, 'toy_safety_.xlsx')
                print(f"😊 Capturing data from toy_safety_.xlsx… please wait ⏳")
                first_table_data = read_excel_with_custom_headers(list_info_path)
            except Exception as e:
                log_error(f"Error reading Excel data: {e}")
                first_table_data = [] 

        except Exception as e:
            log_error(f"Error downloading: {e}") 

    except Exception as e:
        log_error(f"General error in main: {e}")

    finally:
        try:
            create_final_json_file(first_table_data,"CAS_No.")
            print(f"✅ {len(first_table_data)} ROWS AFFECTED TOY SAFETY TABLE")

        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
