import requests
from bs4 import BeautifulSoup
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict
import pandas as pd
from urllib.parse import urljoin

errors = []
data = []

uniqueIdentity = 'AR0177'
region = 'Asia Pacific'
jurisdiction = 'AU'
category = 'Testing / Risk Assessment / HPV'
title = 'Australia. High Volume Industrial Chemicals (HVIC) (The 2006 List, as published on Feb 2009)'
casKeyValue = "CAS_No"

headers = {  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",    "Cache-Control": "no-cache",    "Pragma": "no-cache",    "Priority": "u=0, i",    "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',    "Sec-Ch-Ua-Arch": '"x86"',    "Sec-Ch-Ua-Bitness": '"64"',    "Sec-Ch-Ua-Full-Version": '"134.0.6998.89"',    "Sec-Ch-Ua-Full-Version-List": '"Chromium";v="134.0.6998.89", "Not:A-Brand";v="24.0.0.0", "Google Chrome";v="134.0.6998.89"',    "Sec-Ch-Ua-Mobile": "?0",    "Sec-Ch-Ua-Model": '""',    "Sec-Ch-Ua-Platform": '"Windows"',    "Sec-Ch-Ua-Platform-Version": '"15.0.0"',    "Sec-Fetch-Dest": "document",    "Sec-Fetch-Mode": "navigate",    "Sec-Fetch-Site": "none",    "Sec-Fetch-User": "?1",    "Upgrade-Insecure-Requests": "1",    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://www.industrialchemicals.gov.au/search-inventory",
}
 

def log_error(message):
    errors.append(message)

def getSoup(url):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred while fetching {url}: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request error occurred while fetching {url}: {req_err}")
        return None
    except Exception as e:
        log_error(f"Unexpected error occurred while fetching {url}: {e}")
        return None
    else:
        try:
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            log_error(f"Failed to parse HTML from URL {url}: {e}")
            return None

def get_all_links(url):
    return [url]

def get_search_inventory_link(html_content, base_url):
    try:
        nav_div = html_content.find("div", id="homepage-nav")
        if not nav_div:
            return None

        li_tag = nav_div.find("li", class_="aicis_inventory")
        if not li_tag:
            return None

        a_tag = li_tag.find("a")
        if a_tag and a_tag.has_attr("href"):
            inventory_link = urljoin(base_url, a_tag["href"])
            return inventory_link
        else:
            return None

    except Exception as e:
        log_error(f"Error extracting inventory link: {e}")
        return None

def find_download_inventory_link(html, base_url):
    try:
        input_tag = html.find('input', {'id': 'downloadInventoryId'})
        if input_tag and input_tag.get('value'):
            dynamic_id = input_tag['value']
            download_url = f"{base_url}/_entity/annotation/{dynamic_id}"
            print("Dynamic download link:", download_url)
            return download_url
        else:
            print("Download ID not found.")
            return None
    except Exception as e:
        log_error(f"Error finding download inventory link: {e}")
        return None

def get_excel_data_as_list(url_of_excel):
    try:
        response = requests.get(url_of_excel)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while downloading Excel: {http_err}")
        return []
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred while downloading Excel: {req_err}")
        return []
    except Exception as e:
        print(f"Unexpected error occurred while downloading Excel: {e}")
        return []
    else:
        try:
            df = pd.read_excel(BytesIO(response.content), header=1)
            df.dropna(how='all', inplace=True)
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"Error processing Excel content: {e}")
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

        base_url = "https://services.industrialchemicals.gov.au/"
        for link in get_all_links(base_url):
            try:
                soup = getSoup(link)
                if not soup:
                    raise ValueError(f"Failed to parse base link: {link}")

                try:
                    inventry_link = get_search_inventory_link(soup, base_url)
                    if not inventry_link:
                        raise ValueError(f"Inventory search link not found for base link: {link}")

                    try:
                        soup_of_inventory = getSoup(inventry_link)
                        if not soup_of_inventory:
                            raise ValueError(f"Failed to parse inventory link page: {inventry_link}")

                        try:
                            inventory_download_link_excel = find_download_inventory_link(soup_of_inventory, base_url)
                            if not inventory_download_link_excel:
                                raise ValueError(f"Inventory download link not found for URL: {inventry_link}")

                            try:
                                data_records_excel = get_excel_data_as_list(inventory_download_link_excel)
                                print(f"Successfully Scraprd {len(data_records_excel)} Records✅")
                                data.extend(data_records_excel)
                            except Exception as e:
                                log_error(f"Error reading Excel from link: {inventory_download_link_excel} - {e}")

                        except Exception as e:
                            log_error(str(e))

                    except Exception as e:
                        log_error(str(e))

                except Exception as e:
                    log_error(str(e))

            except Exception as e:
                log_error(str(e))

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
    