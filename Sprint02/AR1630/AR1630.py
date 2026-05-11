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

uniqueIdentity = 'AR1630'
region = 'North America'
jurisdiction = 'US'
category = 'Testing / Risk Assessment / HPV'
title = 'TSCA Section 4(f) Priority Risk Review Chemicals'
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


def extract_high_chemical_table_data(soup, base_url):
    try:
        table = soup.find("table", class_="datatable")
        if not table:
            raise ValueError("Data table with class 'datatable' not found")

        tbody = table.find("tbody")
        if not tbody:
            raise ValueError("No <tbody> found in the table")

        rows = tbody.find_all("tr")
        high_prio_data = []

        for row_index, row in enumerate(rows, start=1):
            try:
                cols = row.find_all("td")
                if len(cols) != 7:
                    continue

                chem_name_tag = cols[0].find("a")
                chemical_name = chem_name_tag.get_text(strip=True) if chem_name_tag else cols[0].get_text(strip=True)
                chemical_name_url = (
                    urljoin(base_url, chem_name_tag['href'])
                    if chem_name_tag and chem_name_tag.get("href")
                    else None
                )

                casrn = cols[1].get_text(strip=True)
                chemical_group = cols[2].get_text(strip=True)
                date_initiated = cols[3].get_text(strip=True)

                docket_links = []
                docket_texts = []
                for link in cols[4].find_all("a"):
                    try:
                        href = link.get("href")
                        if href:
                            full_url = urljoin(base_url, href)
                            docket_links.append(full_url)
                            docket_texts.append(link.get_text(strip=True))
                    except Exception as e:
                        print(f"[Row {row_index}] Error processing docket link: {e}")

                status = cols[5].get_text(strip=True)

                try:
                    contact_html = cols[6].decode_contents().strip()
                    contact_text = BeautifulSoup(contact_html, 'html.parser').get_text(separator="\n", strip=True)
                except Exception as e:
                    contact_text = ""
                    print(f"[Row {row_index}] Error parsing agency contact: {e}")

                high_prio_data.append({
                    "chemical_name": chemical_name,
                    "chemical_name_url": chemical_name_url,
                    "casrn": casrn,
                    "chemical_group": chemical_group,
                    "date_initiated": date_initiated,
                    "docket_numbers": docket_texts,
                    "docket_links": docket_links,
                    "status": status,
                    "agency_contact": contact_text
                })

            except Exception as e:
                print(f"[Row {row_index}] Error processing row: {e}")

        return high_prio_data
    
    except Exception as e:
        print(f"Error extracting high priority chemical data: {e}")
        return []

def extract_low_priority_chemicals(soup, base_url):
    try:
        table = soup.find("table", {"id": "datatablelow"})
        if not table:
            raise ValueError("Table with id 'datatablelow' not found.")

        tbody = table.find("tbody")
        if not tbody:
            raise ValueError("No <tbody> found in the table with id 'datatablelow'.")

        low_prio_data = []
        rows = tbody.find_all("tr")

        for row_index, row in enumerate(rows, start=1):
            try:
                cols = row.find_all("td")
                if len(cols) != 5:
                    continue 

                chemical_name = cols[0].get_text(strip=True)
                cas = cols[1].get_text(strip=True)

                docket_link_tag = cols[2].find("a")
                docket_number = (
                    docket_link_tag.get_text(strip=True) if docket_link_tag else None
                )
                docket_url = (
                    urljoin(base_url, docket_link_tag["href"])
                    if docket_link_tag and docket_link_tag.get("href")
                    else None
                )

                status = cols[3].get_text(strip=True)

                try:
                    contact_html = cols[4].decode_contents()
                    contact_text = BeautifulSoup(
                        contact_html, "html.parser"
                    ).get_text(separator="\n", strip=True)
                except Exception as e:
                    contact_text = ""
                    print(f"[Row {row_index}] Error parsing contact info: {e}")

                low_prio_data.append({
                    "chemical_name": chemical_name,
                    "cas": cas,
                    "docket_number": docket_number,
                    "docket_url": docket_url,
                    "status": status,
                    "agency_contact": contact_text
                })

            except Exception as e:
                print(f"[Row {row_index}] Error processing row: {e}")

        return low_prio_data

    except Exception as e:
        print(f"Error extracting low priority chemicals: {e}")
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
    except Exception as e:
        log_error(f"Error deleting today's files: {e}")
        return

    base_url_01 = "https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/ongoing-and-completed-chemical-risk-evaluations-under"
    try:
        for link in get_all_links(base_url_01):
            try:
                high_soup = getSoup(link)
                if high_soup:
                    try:
                        high_prio_data = extract_high_chemical_table_data(high_soup, base_url_01)
                    except Exception as e:
                        log_error(f"Error extracting high-priority chemical data from {link}: {e}")
            except Exception as e:
                log_error(f"Error fetching soup from {link}: {e}")
    except Exception as e:
        log_error(f"Error processing high-priority base URL ({base_url_01}): {e}")

    base_url_02 = "https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/low-priority-substances-under-tsca"
    try:
        for link in get_all_links(base_url_02):
            try:
                low_soup = getSoup(link)
                if low_soup:
                    try:
                        low_prio_data = extract_low_priority_chemicals(low_soup, base_url_02)
                    except Exception as e:
                        log_error(f"Error extracting low-priority chemical data from {link}: {e}")
            except Exception as e:
                log_error(f"Error fetching soup from {link}: {e}")
    except Exception as e:
        log_error(f"Error processing low-priority base URL ({base_url_02}): {e}")

    finally:
        try:
            create_final_json_file(high_prio_data, "casrn")
            create_final_json_file(low_prio_data, "cas")
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
