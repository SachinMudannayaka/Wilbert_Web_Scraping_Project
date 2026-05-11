import requests
from bs4 import BeautifulSoup
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict,Union
import pandas as pd

errors = []
data = []

uniqueIdentity = 'AR1766'
region = 'North America'
jurisdiction = 'US'
category = 'Cosmetics/Personal Care'
title = 'USA. Special Requirements for Specific Human Drugs. FDA (21 CFR 250) (April 8, 2004)'
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


def extract_ecfr_structure(html_content):
    result = []

    try:
        subparts = html_content.find_all("div", class_="subpart")
    except Exception:
        subparts = []

    for subpart in subparts:
        try:
            subpart_title_tag = subpart.find("h2")
            subpart_title = subpart_title_tag.get_text(strip=True) if subpart_title_tag else "Untitled Subpart"
        except Exception:
            subpart_title = "Untitled Subpart"

        sections = []
        try:
            section_tags = subpart.find_all("div", class_="section")
        except Exception:
            section_tags = []

        for section in section_tags:
            try:
                section_title_tag = section.find("h4")
                section_title = section_title_tag.get_text(strip=True) if section_title_tag else "Untitled Section"
            except Exception:
                section_title = "Untitled Section"

            description = []
            try:
                paragraphs = section.find_all("p")
            except Exception:
                paragraphs = []

            for p in paragraphs:
                try:
                    text_content = p.get_text(strip=True)
                    label_match = re.match(r'\s*\((\w+(\)\(\w+\))?)\)', text_content)
                    if label_match:
                        label = f"({label_match.group(1)})"
                        original_text = p.get_text()
                        text = original_text.replace(label, "", 1).strip()
                        description.append({"label": label, "text": text})
                except Exception:
                    continue

            sections.append({
                "section_with_title": section_title,
                "description": description
            })

        result.append({
            "sub_part": subpart_title,
            "sections": sections
        })

    return result

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)
       
        url_base = "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-250"
        for link in get_all_links(url_base):
            soup = getSoup(link)
            if soup:
                web_page_data = extract_ecfr_structure(soup)
              

    except Exception as e:
        log_error(f"General error in main: {e}")
    finally:
        try:
            create_final_json_file(web_page_data)
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
