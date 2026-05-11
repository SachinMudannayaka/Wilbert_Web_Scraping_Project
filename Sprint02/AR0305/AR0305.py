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
import os

errors = []
data = []

uniqueIdentity = 'AR0305'
region = 'North America'
jurisdiction = 'CA'
category = 'Environment'
title = 'Canada. Toronto Municipal Code. Environmental Reporting and Disclosure Bylaw Schedule A to Ch. 423 Priority Substances (as amended through 15 June 2011)'
casKeyValue = "CAS_No.b"

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

def get_municipal_code_link(html,base_url):
    try:
        link_tag = html.find("a", string="Municipal Code")
        if link_tag and link_tag.has_attr('href'):
            link_of_municipal_code = urljoin(base_url,link_tag['href'])
            return link_of_municipal_code
        raise ValueError("❌ 'Municipal Code' link not found or missing 'href'.")
    except Exception as e:
        log_error(f"❗ Error extracting Municipal Code link: {e}")
        raise RuntimeError(f"❗ Error extracting Municipal Code link: {e}")

def find_exact_pdf_link(soup, chapter_text = "Chapter 423"):
    try:
        a_tag = soup.find("a", string=chapter_text)
        if not a_tag:
            raise ValueError(f"❌ Could not find chapter link with text '{chapter_text}'")

        tr_tag = a_tag.find_parent("tr")
        if not tr_tag:
            raise ValueError("❌ Could not locate parent <tr>")
        
        tds = tr_tag.find_all("td")
        return a_tag["href"].strip()
    except Exception as e:
        log_error(f"❗ Error during extraction: {e}")
        raise RuntimeError(f"❗ Error during extraction: {e}")
        
def extract_table_from_pdf(pdf_path):
    data_pdf = []

    if pdf_path.lower().startswith("http://") or pdf_path.lower().startswith("https://"):
        response = requests.get(pdf_path)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)
    elif os.path.isfile(pdf_path):
        pdf_file = pdf_path
    else:
        raise ValueError("Invalid PDF path or URL provided.")

    with pdfplumber.open(pdf_file) as pdf:
        if len(pdf.pages) >= 8:
            page = pdf.pages[7]
            table = page.extract_table()

            if table:
                headers = ["Chemical Name", "CAS No.b", "Mass Reporting Threshold", "Concentration Threshold"]

                for row in table[2:]:
                    if len(row) != 4:
                        continue

                    chemical_name = row[0].strip()
                    if chemical_name.upper().startswith("GROUP"):
                        continue

                    cleaned_row = [
                        '' if cell.strip() == '-' else cell.replace('\n', '').replace('\r', '').strip()
                        for cell in row
                    ]
                    data_pdf.append(dict(zip(headers, cleaned_row)))
            else:
                print("No table found on page 8.")
        else:
            print("Page 8 does not exist in the PDF.")

    return data_pdf

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)
        
        base_url = "https://www.toronto.ca/legdocs/bylaws/lawhome.htm"
        for link in get_all_links(base_url):
            try:
                soup = getSoup(link)
                if not soup:
                    log_error(f"Failed to parse soup from: {link}")
                    continue

                try:
                    municipal_code_get_link = get_municipal_code_link(soup, base_url)
                    soup_municipal_code = getSoup(municipal_code_get_link)
                    if not soup_municipal_code:
                        log_error(f"Failed to parse municipal code soup from: {municipal_code_get_link}")
                        continue

                    try:
                        link_of_exact_pdf = find_exact_pdf_link(soup_municipal_code)
                        data_pdf_s = extract_table_from_pdf(link_of_exact_pdf)
                        data.extend(data_pdf_s)
                    except Exception as e:
                        log_error(f"Error extracting PDF from: {municipal_code_get_link} | {e}")
                        continue

                except Exception as e:
                    log_error(f"Error processing municipal code link from: {link} | {e}")
                    continue

            except Exception as e:
                log_error(f"Error processing link: {link} | {e}")
                continue

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
