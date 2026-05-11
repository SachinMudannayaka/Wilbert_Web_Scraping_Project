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


uniqueIdentity = 'AR0539'
region = 'North America'
jurisdiction = 'US'
category = 'Controlled Drugs & Precursors'
title = 'Drug Enforcement Administration (DEA). Schedule I Controlled Substances (21 CFR 1308.11, as amended through 29 July 2024)'
casKeyValue = ""

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

def extract_drug_schedule_data(html_content):
    section = html_content.find('div', {'id': '1308.11'})
    
    result = []
    sections = {
        'b': section.find('div', {'id': 'p-1308.11(b)'}),
        'c': section.find('div', {'id': 'p-1308.11(c)'}),
        'd': section.find('div', {'id': 'p-1308.11(d)'}),
        'e': section.find('div', {'id': 'p-1308.11(e)'}),
        'f': section.find('div', {'id': 'p-1308.11(f)'}),
        'g': section.find('div', {'id': 'p-1308.11(g)'}),
        'h': section.find('div', {'id': 'p-1308.11(h)'}),
    }
    
    if sections['h']:
        h1_div = sections['h'].find_next_sibling('div')
        if h1_div:
            sections['h1'] = h1_div
    table_div = section.find('div', class_='table_wrapper')
    if table_div:
        sections['table'] = table_div        

    h_title = None

    for section_name, section_div in sections.items():
        if not section_div:
            continue

        title = section_div.find("p", class_="indent-1").get_text(" ", strip=True) if section_div.find("p", class_="indent-1") else f"{section_name}"

        if section_name == 'h':
            h_title = title
        elif section_name == 'h1' and h_title:
            title = h_title

        tables = section_div.find_all('table', {'class': 'gpo_table'})
        for table in tables: 
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
            
            current_drug = None
            
            for row in rows:
                left = row.find('td', {'class': 'left'})
                right = row.find('td', {'class': 'right'})
                
                if not left or not right:
                    continue
                    
                if left.get_text().strip().startswith('('):
                    if current_drug:
                        result.append(current_drug)
                    
                    text = re.sub(r'\s+', ' ', left.get_text(" ", strip=True))
                    drug_name = re.sub(r'\s*([()\[\]-])\s*', r'\1', text)
                
                    code = ' '.join(right.get_text(separator=' ', strip=True).split())
                    
                    current_drug = {
                        'Title': title,
                        'Drugs_and_other_substances': drug_name,
                        'DEA_Controlled_Substance_Code_Number': code
                    }
                else:
                    if current_drug:
                        trade_names = left.get_text(separator=' ', strip=True)
                        trade_names = re.sub(r'^Some trade or other names:\s*', '', trade_names)
                        trade_names = re.sub(r'^Some trade and other names:\s*', '', trade_names)
                        trade_names = trade_names.strip()
                        
                        if 'Trade_or_other_names' in current_drug:
                            current_drug['Trade_or_other_names'] += '; ' + trade_names
                        else:
                            current_drug['Trade_or_other_names'] = trade_names
            
            if current_drug:
                result.append(current_drug)
    
    return result

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

        base_url_ = "https://www.ecfr.gov/current/title-21/chapter-II/part-1308"
        if base_url_:
            try:
                soup = getSoup(base_url_)
                if soup:
                    try:
                        table_data_list = extract_drug_schedule_data(soup)
                    except Exception as e:
                        log_error(f"Error extracting drug schedule data: {e}")
                else:
                    log_error("Soup object is None.")
            except Exception as e:
                log_error(f"Error fetching soup from URL: {e}")

    except Exception as e:
        log_error(f"Unhandled error in main(): {e}")

    finally:
        try:
            create_final_json_file(table_data_list)
            print(f"✅ {len(table_data_list)} ROWS AFFECTED SHEET")
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
