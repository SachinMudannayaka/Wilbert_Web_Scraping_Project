import requests
from bs4 import BeautifulSoup
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict
import pandas as pd
import cloudscraper
import time
import random
from bs4 import NavigableString
import re


errors = []
data = []

uniqueIdentity = 'AR1330'
region = 'North America'
jurisdiction = 'US'
category = 'Workplace Safety (OELs, BELs, GLP)'
title = 'Oregon. Oregon Rules for Air Contaminants, Tables Z-1, Z-2, Z-3 (OAR 437-002-0382; 29 October 2019)'
casKeyValue = ""

SUPERSCRIPTS = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ',
    'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ',
    'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ', 'v': 'ᵛ',
    'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
    'A': 'ᴬ', 'B': 'ᴮ', 'D': 'ᴰ', 'E': 'ᴱ', 'G': 'ᴳ', 'H': 'ᴴ', 'I': 'ᴵ',
    'J': 'ᴶ', 'K': 'ᴷ', 'L': 'ᴸ', 'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ', 'P': 'ᴾ',
    'R': 'ᴿ', 'T': 'ᵀ', 'U': 'ᵁ', 'V': 'ⱽ', 'W': 'ᵂ',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
}

SUBSCRIPTS = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ', 'k': 'ₖ',
    'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ', 'p': 'ₚ', 'r': 'ᵣ',
    's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ', 'v': 'ᵥ', 'x': 'ₓ',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
}

def get_text_with_sup_sub(cell):
    result = ""
    for content in cell.descendants:
        if content.name == "sup":
            result += ''.join(SUPERSCRIPTS.get(c, c) for c in content.get_text())
        elif content.name == "sub":
            result += ''.join(SUBSCRIPTS.get(c, c) for c in content.get_text())
        elif isinstance(content, str):
            if content.parent.name not in ("sup", "sub"):
                result += content

    superscripts = ''.join(SUPERSCRIPTS.values())
    subscripts = ''.join(SUBSCRIPTS.values())
    all_sup_sub = superscripts + subscripts
    pattern = re.compile(r'([' + re.escape(all_sup_sub) + r']+)\([a-zA-Z0-9]+\)')
    result = pattern.sub(r'\1', result)
    return result.strip()

def getSoup(url, timeout=30):
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Priority": "u=0, i",
            "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            "Sec-Ch-Ua-Arch": '"x86"',
            "Sec-Ch-Ua-Bitness": '"64"',
            "Sec-Ch-Ua-Full-Version": '"134.0.6998.89"',
            "Sec-Ch-Ua-Full-Version-List": '"Chromium";v="134.0.6998.89", "Not:A-Brand";v="24.0.0.0", "Google Chrome";v="134.0.6998.89"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Model": '""',
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua-Platform-Version": '"15.0.0"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        response = scraper.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None
    else:
        return BeautifulSoup(response.text, 'html.parser')



def log_error(message):
    errors.append(message)


def get_all_links(url):
    return [url] 

def get_table_from_main_soup_(soup):
    try:
        first_table_div = soup.find("div", class_="table-responsive")
        if first_table_div:
            return first_table_div
        else:
            errors.append("first table div not found")
            return None
    except Exception as e:
        errors.append(f"Error in get_table_from_main_soup_: {str(e)}")
        return None
    
def extract_first_table_data(html_content):
    try:
        table = html_content.find('table', {'id': 'z-1'})
        if not table:
            first_table_data = []
        else:
            first_table_data = []
            rows = table.tbody.find_all('tr')

            current_heading_substance = None
            current_heading_cas = None
            current_heading_acgih = None

            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue

                is_heading_row = 'headingRow' in row.get('class', [])
                is_indent = 'indent' in cells[0].get('class', [])

                substance = get_text_with_sup_sub(cells[0])
                cas_no = get_text_with_sup_sub(cells[1]) if len(cells) > 1 else ''
                osha_ppm = get_text_with_sup_sub(cells[2]) if len(cells) > 2 else ''
                osha_mg = get_text_with_sup_sub(cells[3]) if len(cells) > 3 else ''
                cal_osha = get_text_with_sup_sub(cells[4]) if len(cells) > 4 else ''
                niosh_rel = get_text_with_sup_sub(cells[5]) if len(cells) > 5 else ''

                acgih_link = ''
                if len(cells) > 6:
                    link = cells[6].find('a')
                    if link and link.has_attr('href'):
                        acgih_link = link['href']

                if is_indent and current_heading_substance:
                    substance = f"{current_heading_substance} - {substance}"
                    cas_no = cas_no if cas_no else current_heading_cas
                    if not acgih_link:
                        acgih_link = current_heading_acgih

                if is_heading_row:
                    current_heading_substance = substance
                    current_heading_cas = cas_no
                    current_heading_acgih = acgih_link

                first_table_data.append({
                    'Substance': substance,
                    'CAS No.': cas_no,
                    'Regulatory Limits_OSHA PEL_ppm': osha_ppm,
                    'Regulatory Limits_OSHA PEL_mg/m3': osha_mg,
                    'Regulatory Limits_Cal/OSHA_PEL_8-hour TWA(ST) STEL': cal_osha,
                    'Recommended_limits_NIOSH REL_Up to 10-hour TWA(ST) STEL(C) Ceiling': niosh_rel,
                    'Recommended_limits_ACGIH_Complimentary access on': acgih_link
                })
            return first_table_data
    except Exception as e:
        errors.append(f"Error in extract_first_table_data: {str(e)}")
        return first_table_data

def extract_second_table_data(html_content):
    try:
        table = html_content.find('table', {'id': 'z-2'})
        second_data = []

        if not table:
            return second_data
        else:
            tbody = table.find('tbody')
            if not tbody:
                return second_data
            rows = tbody.find_all('tr')

            for row in rows:
                cols = row.find_all('td')
                if not cols:
                    continue

                def get_link(td):
                    link = td.find('a', href=True)
                    if link:
                        return link['href']
                    return ''
                
                col_texts = []
                for td in cols:
                    colspan = int(td.get("colspan", 1))
                    col_texts.extend([td] * colspan)

                record = {
                    "Regulatory_Limits_OSHA_PELs_Substance":
                        get_text_with_sup_sub(col_texts[0]) if len(col_texts) > 0 else '',
                    "Regulatory_Limits_OSHA_PELs_8-hour_Time_Weighted_Average_(TWA)":
                        get_text_with_sup_sub(col_texts[1]) if len(col_texts) > 1 else '',
                    "Regulatory_Limits_OSHA_PELs_Acceptable_Ceiling_Concentration":
                        get_text_with_sup_sub(col_texts[2]) if len(col_texts) > 2 else '',
                    "Regulatory_Limits_OSHA_PELs_Acceptable_maximum_peak_above_the_acceptable_ceiling_concentration_for_an_8-hr_shift_Concentration":
                        get_text_with_sup_sub(col_texts[3]) if len(col_texts) > 3 else '',
                    "Regulatory_Limits_OSHA_PELs_Acceptable_maximum_peak_above_the_acceptable_ceiling_concentration_for_an_8-hr_shift_Maximum_Duration":
                        get_text_with_sup_sub(col_texts[4]) if len(col_texts) > 4 else '',
                    "Regulatory_Limits_OSHA_PELs_Cal/OSHA_PEL_8-hour_TWA(ST)_STEL(C)_Ceiling":
                        get_text_with_sup_sub(col_texts[5]) if len(col_texts) > 5 else '',
                    "Recommended_Limits_NIOSH_REL_Up_to_10-hour_TWA(ST)_STEL(C)_Ceiling":
                        get_text_with_sup_sub(col_texts[6]) if len(col_texts) > 6 else '',
                    "Recommended_Limits_ACGIH_Complimentary_access_on":
                        get_link(col_texts[-1]) if col_texts else ''
                }

                second_data.append(record)
            return second_data

    except Exception as e:
        errors.append(f"Error in extract_second_table_data: {str(e)}")
        return []

def extract_third_table_data(html_content):
    try:
        table = html_content.find('table', {'id': 'z-3'})
        if not table:
            return pd.DataFrame()
        else:
            third_table_data = []
            rows = table.tbody.find_all('tr') if table.tbody else table.find_all('tr')

            for row in rows:
                if row.find('th'):
                    continue

                cells = row.find_all('td')
                if len(cells) < 1:
                    continue

                row_data = {
                    'Regulatory_Limits_OSHA_PEL_Substance': '',
                    'Regulatory_Limits_OSHA_PEL_mppcf': '',
                    'Regulatory_Limits_OSHA_PEL_mg/m3': '',
                    'Regulatory_Limits_Cal/OSHA_PEL_8-hour_TWA_mg/m3': '',
                    'Recommended_Limits_NIOSH_REL_Up_to_10-hour_TWA_mg/m3': '',
                    'Recommended_Limits_ACGIH_Complimentary_access_on': ''
                }

                row_data['Regulatory_Limits_OSHA_PEL_Substance'] = get_text_with_sup_sub(cells[0])

                if len(cells) == 6:
                    row_data.update({
                        'Regulatory_Limits_OSHA_PEL_mppcf': get_text_with_sup_sub(cells[1]),
                        'Regulatory_Limits_OSHA_PEL_mg/m3': get_text_with_sup_sub(cells[2]),
                        'Regulatory_Limits_Cal/OSHA_PEL_8-hour_TWA_mg/m3': get_text_with_sup_sub(cells[3]),
                        'Recommended_Limits_NIOSH_REL_Up_to_10-hour_TWA_mg/m3': get_text_with_sup_sub(cells[4]),
                        'Recommended_Limits_ACGIH_Complimentary_access_on': cells[5].find('a')['href'] if cells[5].find('a') else ''
                    })
                elif len(cells) == 5:
                    if cells[1].has_attr('colspan'):
                        row_data.update({
                            'Regulatory_Limits_OSHA_PEL_mppcf': '',
                            'Regulatory_Limits_OSHA_PEL_mg/m3': get_text_with_sup_sub(cells[1]),
                            'Regulatory_Limits_Cal/OSHA_PEL_8-hour_TWA_mg/m3': get_text_with_sup_sub(cells[2]),
                            'Recommended_Limits_NIOSH_REL_Up_to_10-hour_TWA_mg/m3': get_text_with_sup_sub(cells[3]),
                            'Recommended_Limits_ACGIH_Complimentary_access_on': cells[4].find('a')['href'] if cells[4].find('a') else ''
                        })
                    else:
                        pass
                elif len(cells) == 4:
                    row_data.update({
                        'Regulatory_Limits_OSHA_PEL_mppcf': '',
                        'Regulatory_Limits_OSHA_PEL_mg/m3': '',
                        'Regulatory_Limits_Cal/OSHA_PEL_8-hour_TWA_mg/m3': get_text_with_sup_sub(cells[1]),
                        'Recommended_Limits_NIOSH_REL_Up_to_10-hour_TWA_mg/m3': get_text_with_sup_sub(cells[2]),
                        'Recommended_Limits_ACGIH_Complimentary_access_on': cells[3].find('a')['href'] if cells[3].find('a') else ''
                    })

                if 'See Annotated Z-1' in str(row):
                    for i in range(1, 5):
                        if i < len(cells):
                            if 'See Annotated Z-1' in cells[i].get_text():
                                if i == 1:
                                    row_data['Regulatory_Limits_OSHA_PEL_mppcf'] = 'See Annotated Z-1'
                                elif i == 2:
                                    row_data['Regulatory_Limits_OSHA_PEL_mg/m3'] = 'See Annotated Z-1'
                                elif i == 3:
                                    row_data['Regulatory_Limits_Cal/OSHA_PEL_8-hour_TWA_mg/m3'] = 'See Annotated Z-1'
                                elif i == 4:
                                    row_data['Recommended_Limits_NIOSH_REL_Up_to_10-hour_TWA_mg/m3'] = 'See Annotated Z-1'

                third_table_data.append(row_data)
            return third_table_data
    except Exception as e:
        errors.append(f"Error in extract_third_table_data: {str(e)}")
        return []

def create_final_json_file(data,casKeyValue):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")


def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)
        data_z1, data_z2, data_z3 = [], [], []

        url1 = "https://www.osha.gov/annotated-pels/table-z-1"
        for link in get_all_links(url1):
            soup = getSoup(link)
            if soup:
                table_div_soup_first = get_table_from_main_soup_(soup)
                if table_div_soup_first:
                    table_of_first = extract_first_table_data(table_div_soup_first)
                    data_z1.extend(table_of_first)
                else:
                    errors.append("First table division soup is None")

        url2 = "https://www.osha.gov/annotated-pels/table-z-2"
        for link in get_all_links(url2):
            soup = getSoup(link)
            if soup:
                table_div_soup_second = get_table_from_main_soup_(soup)
                if table_div_soup_second:
                    table_of_second = extract_second_table_data(table_div_soup_second)
                    data_z2.extend(table_of_second)
                else:
                    errors.append("Second table division soup is None")

        url3 = "https://www.osha.gov/annotated-pels/table-z-3"
        for link in get_all_links(url3):
            soup = getSoup(link)
            if soup:
                table_div_soup_third = get_table_from_main_soup_(soup)
                if table_div_soup_third:
                    table_of_third = extract_third_table_data(table_div_soup_third)
                    data_z3.extend(table_of_third)
                else:
                    errors.append("Third table division soup is None")

    except Exception as e:
        log_error(f"General error in main: {e}")
    finally:
        try:
            create_final_json_file(data_z1,"CAS No.")
            create_final_json_file(data_z2,"")
            create_final_json_file(data_z3,"")
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")



if __name__ == "__main__":
    main()
