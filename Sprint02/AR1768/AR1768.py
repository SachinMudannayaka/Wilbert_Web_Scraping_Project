import requests
from bs4 import BeautifulSoup
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict
import pandas as pd

errors = []
data = []

uniqueIdentity = 'AR1768'
region = 'Global Inventories'
jurisdiction = 'US'
category = 'New Chemical Notification'
title = 'USA. List of Inactive Substances on the Toxic Substances Control Act (TSCA) Chemical Substances Inventory (as amended through 23 May 2024)'
casKeyValue = "CAS_#"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br"
}

def log_error(message):
    errors.append(message)

def get_all_links(url):
    return [url]

def read_epa_excel_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        excel_data = pd.read_excel(BytesIO(response.content), engine='openpyxl')
        if excel_data.empty:
            raise ValueError("Excel file is empty.")

        records = excel_data.to_dict(orient='records')
        return records

    except requests.exceptions.RequestException as e:
        log_error(f"Request error: {e}")
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
        try:
            common.deleteTodayFiles(uniqueIdentity)
        except Exception as e:
            log_error(f"Error deleting today's files: {e}")
        
        try:
            base_url = "https://cdxapps.epa.gov/oms-substance-registry-services/api/substance-lists/export/listInfo/502"
            excel_sheet_data = read_epa_excel_data(base_url)
        except Exception as e:
            log_error(f"Error reading Excel data: {e}")
            excel_sheet_data = []

        try:
            print(f"{len(excel_sheet_data)} ROWS AFFECTED ✅")
            data.extend(excel_sheet_data)
        except Exception as e:
            log_error(f"Error while processing Excel data: {e}")

    except Exception as e:
        log_error(f"General error in main: {e}")

    finally:
        try:
            create_final_json_file(data)
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()


