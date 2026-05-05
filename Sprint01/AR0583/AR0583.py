import requests
from bs4 import BeautifulSoup, Tag, NavigableString
import common
import re
import pandas as pd
import ssl
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin
from typing import List, Dict

errors = []
data = []

uniqueIdentity = 'AR0583'
region = 'North America'
jurisdiction = "US"
category = 'Release/Spill Reporting'
title = 'EPA. Chlorophenols (EPCRA 313 Guidance Document - List of Toxic Chemicals Within the Chlorophenols Category as amended through February 2019)'
casKeyValue = "CASRN"

class UnsafeTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "host": "ordspub.epa.gov",
    "pragma": "no-cache",
    "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}

session = requests.Session()
session.mount("https://", UnsafeTLSAdapter())

def get_json(url, headers=None):
    try:
        print("⏳ Please wait, content is loading...")
        response = session.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"⚠️ Failed to retrieve JSON: {url} [status code: {response.status_code}]")

        print("✅ Status code 200 received. Procedure continues")

        try:
            return response.json()
        except ValueError:
            raise Exception("❌ Failed to parse response as JSON")

    except requests.exceptions.RequestException as e:
        raise Exception(f"⚠️ Request error while accessing {url}: {e}")
    
def log_error(message):
    errors.append(message)

def get_all_links(url):
    try:
        All_links = [url]
        return All_links
    except Exception as error:
        print("❌ Unable to retrieve content.")
        log_error("Unable to retrieve content.")
        return []

def extract_chlorophenols_table_from_json_body(json_data: Dict) -> List[Dict[str, str]]:
    """
    Extracts chlorophenol chemical data from a JSON 'body' field containing HTML table.

    Returns:
        List[Dict[str, str]]: List of dictionaries with 'Name', 'CASRN', 'Category'.
    """
    try:
        html_content = json_data.get("body", "")
        if not html_content:
            raise ValueError("Missing 'body' or it's empty in JSON data.")

        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        if not table:
            raise ValueError("No <table> found in the provided HTML.")

        rows = table.find_all("tr")
        if not rows:
            raise ValueError("No rows (<tr>) found in the table.")

        superscript_map = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")

        def get_text_with_unicode_sup(cell):
            result = ''
            for item in cell.children:
                if isinstance(item, NavigableString):
                    result += item.strip()
                elif isinstance(item, Tag):
                    if item.name == "sup":
                        result += item.get_text(strip=True).translate(superscript_map)
                    else:
                        result += item.get_text(strip=True)
            return result.strip()

        results = []
        current_category = None

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) == 1 and cells[0].has_attr("colspan"):
                current_category = cells[0].get_text(strip=True)
            elif len(cells) == 2:
                name = get_text_with_unicode_sup(cells[0])
                casrn = get_text_with_unicode_sup(cells[1])
                if current_category:
                    results.append({
                        "Name": name,
                        "CASRN": casrn,
                        "Category": current_category
                    })

        if not results:
            raise ValueError("No chemical entries extracted from table.")

        return results

    except Exception as e:
        log_error(f"Error in extract_chlorophenols_table_from_json_body: {str(e)}")
        raise    

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)

        url = "https://guideme.epa.gov/ords/guideme_ext/guideme_ext/guideme/gme_doc/gd/chlorophenols_4/13016363828033"
        All_links = get_all_links(url)

        for index, url in enumerate(All_links):
            try:
                print(f"🔗 Processing link {index+1}...")
                json_content = get_json(url, headers=headers)
                extracted = extract_chlorophenols_table_from_json_body(json_content)
                data.extend(extracted)
            except Exception as error:
                print("❌ There is an error with the link")
                log_error(f"An error has been encountered: {error}")
                return

    except Exception as error:
        print("❌ Unable to retrieve content.")
        log_error(f"An error has been encountered: {error}")
        return

    finally:
        try:
            create_final_json_file(data)
        except Exception as error:
            print("❌ An error occurred while generating the JSON file")
            log_error(f"An error has been encountered: {error}")
            return

if __name__ == "__main__":
    main()

    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {error}")
