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

errors = []
data = []

uniqueIdentity = 'AR0759'
region = 'North America'
jurisdiction = 'US'
category = 'Cosmetics/Personal Care'
title = 'FDA. Color additives exempt from certification - Cosmetics (21 CFR 73, Subpart C; as amended by 8 October 2021)'
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

def extract_chemical_data(html_content):
    chemicals = []
    
    sections = html_content.find_all('div', class_='section')
    
    for section in sections:
        chemical_data = {}
        
        h4 = section.find('h4', class_='in-front') or section.find('h4')
        if h4:
            chemical_name = h4.get_text(strip=True)
            chemical_data['chemical_name'] = chemical_name
        
        descriptions = []
        
        paragraphs = section.find_all(
            ['p', 'div'],
            class_=['indent-1', 'indent-2', 'indent-3', 'flush-paragraph-1', 'flush-paragraph']
        )
        
        for para in paragraphs:
            if 'citation' in para.get('class', []):
                continue
            
            section_label = ''
            label_span = para.find('span', class_='paragraph-hierarchy')
            if label_span:
                section_label = re.sub(r'[\(\)]', '', label_span.get_text(strip=True)).strip()
            
            section_title = ''
            title_em = para.find('em', class_='paragraph-heading')
            if title_em:
                section_title = title_em.get_text(strip=True).rstrip('.')
            
            text = para.get_text(separator=' ', strip=True)
            if section_label and text.startswith(f'({section_label})'):
                text = text[len(f'({section_label})'):].strip()
            if section_title and text.startswith(section_title):
                text = text[len(section_title):].strip()

            text = text.replace('\n', ' ').replace('\r', ' ')
            text = re.sub(r'\s+', ' ', text).strip()
            text += '\n'
            
            hyperlinks = []
            for link in para.find_all('a', href=True):
                href = link['href']
                if not href.startswith(('http', 'www.')):
                    if href.startswith('/current/title-21'):
                        href = f'https://www.ecfr.gov{href}'
                    elif href.startswith('/'):
                        href = f'https://www.federalregister.gov{href}'
                hyperlinks.append(href)
            
            if section_label or section_title or text.strip():
                descriptions.append({
                    'section': section_label,
                    'title': section_title,
                    'text': text,
                    'hyperlinks': hyperlinks
                })
        
        if chemical_data.get('chemical_name') and descriptions:
            chemical_data['description'] = descriptions
            chemicals.append(chemical_data)
    
    return chemicals


def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")


def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)
    except Exception as e:
        log_error(f"Error deleting today's files: {e}")

    url1 = "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-73/subpart-C"

    try:
        for link in get_all_links(url1):
            try:
                soup = getSoup(link)
                if soup:
                    site_data = extract_chemical_data(soup)
                    data.extend(site_data)
            except Exception as e:
                log_error(f"Error processing link {link}: {e}")
    except Exception as e:
        log_error(f"Error fetching links from main URL: {e}")

    except Exception as e:
        log_error(f"Error writing data to Excel: {e}")

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
