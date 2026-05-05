import time
from bs4 import BeautifulSoup
import requests
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict
import pandas as pd
from urllib.parse import urljoin
import logging

import undetected_chromedriver as uc
import chromedriver_autoinstaller as chromedriver
chromedriver.install()

errors = []
data = []

uniqueIdentity = 'AR1350'
region = 'North America'
jurisdiction = 'US'
category = 'Disaster Prevention/Hazardous Substances Reporting'
title = 'Rhode Island Hazardous Substances Right-to-Know Act (R.I. Gen. Laws 28-21). Hazardous Substance List (May 2016)'
casKeyValue = "C.A.S."

def get_user_agent():
    options = uc.ChromeOptions()
    options.add_argument(f"--headless=new")
    driver = uc.Chrome(options=options)
    driver.get("https://www.example.com")
    user_agent = driver.execute_script("return navigator.userAgent;")
    driver.close()
    driver.quit()

    return user_agent.replace("Headless","")

user_agent = get_user_agent()

check = 0
while check < 5:
    try:
        options = uc.ChromeOptions()

        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-popup-blocking')
        options.add_argument(f'--user-agent={user_agent}')

        driver = uc.Chrome(options=options)

        check = 5
    except:
        if not check < 4:
            message = "An error occurred in the Selenium driver."
            errors.append(message)
        check += 1

def get_html_with_dynamic_cookies(url):
    try:
        driver.get(url)
        print("🌐 Waiting for Cloudflare challenge...")

        time.sleep(5)

        count = 0
        max_count = 40

        while count < max_count:
            if BeautifulSoup(driver.page_source, "html.parser").find("article", class_="qh__teaser-notification"):
                break
            time.sleep(5)
            count += 1

        if "Just a moment..." in driver.page_source:
            print("❌ Still blocked by Cloudflare.")
            return None

        print("✅ Cloudflare bypassed successfully.")
        html = driver.page_source
        return html

    except Exception as e:
        log_error(f"Error in get_html_with_dynamic_cookies: {e}")
        return None

def get_pdf_with_dynamic_cookies(url):
    try:
        driver.get(url)
        print("🌐 Waiting for Cloudflare challenge...")
        time.sleep(10)

        if "Just a moment..." in driver.page_source:
            print("❌ Still blocked by Cloudflare.")
            return None

        print("✅ Cloudflare bypassed successfully.")

        pdf_url = driver.current_url

        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": "https://dlt.ri.gov/regulation-and-safety/occupational-safety",
            "Accept": "application/pdf",
            "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        response = session.get(pdf_url, headers=headers, allow_redirects=True)
        response.raise_for_status()
        return response

    except Exception as e:
        log_error(f"Error in get_pdf_with_dynamic_cookies: {e}")
        return None

    finally:
        try:
            driver.close()
            driver.quit()
        except Exception as e:
            log_error(f"Error while quitting Chrome driver: {e}")

def log_error(message):
    errors.append(message)

def get_all_links(url):
    return [url]

def extract_links(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            links.append((text, href))
        return links
    except Exception as e:
        log_error(f"Error in extract_links: {e}")
        return []

def find_cas_link(links, base_url):
    try:
        for text, href in links:
            if text == "by CAS Number" or "HazardousCAS" in href:
                cas_link = urljoin(base_url, href)
                return cas_link
        return None
    except Exception as e:
        log_error(f"Error in find_cas_link: {e}")
        return None

logging.getLogger("pdfminer").setLevel(logging.ERROR)

def extract_hazardous_data(pdf_url):
    try:
        chemicals_seen = set()
        chemical_records = []

        header_skipped = False
        data_started = False
        response = get_pdf_with_dynamic_cookies(pdf_url)
        if not response or not response.content:
            raise Exception("Failed to fetch PDF")

        with pdfplumber.open(BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split('\n')

                for line in lines:
                    if "===== Page" in line or "RHODE ISLAND HAZARDOUS SUBSTANCE LIST" in line:
                        continue

                    if "Source: T - ACGIH F - NFPA49 C - IARC" in line:
                        data_started = True
                        continue

                    if "C. A. S. Order" in line or "C.A.S." in line:
                        continue

                    if not data_started or not line.strip():
                        continue

                    parts = line.split()

                    cas = None
                    flags = {'ACGIH': None, 'NFPA': None, 'IARC': None}
                    chemical_parts = []

                    if parts and re.match(r'\d{2,7}-\d{2}-\d', parts[0]):
                        cas = parts[0]
                        parts = parts[1:]

                    for part in parts:
                        if part == 'T':
                            flags['ACGIH'] = 'T'
                        elif part == 'F':
                            flags['NFPA'] = 'F'
                        elif part == 'C':
                            flags['IARC'] = 'C'
                        else:
                            chemical_parts.append(part)

                    chemical_name = ' '.join(chemical_parts).strip()

                    if chemical_name and chemical_name not in chemicals_seen:
                        record = {
                            "CHEMICAL NAME": chemical_name,
                            "C.A.S.": cas,
                            "ACGIH": flags['ACGIH'],
                            "NFPA": flags['NFPA'],
                            "IARC": flags['IARC']
                        }
                        chemical_records.append(record)
                        chemicals_seen.add(chemical_name)

        return chemical_records
    except Exception as e:
        log_error(f"Error in extract_hazardous_data: {e}")
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

        base_url = "https://dlt.ri.gov/regulation-and-safety/occupational-safety"
        for link in get_all_links(base_url):
            soup = get_html_with_dynamic_cookies(link)
            if soup:
                pdf_url = extract_links(soup)
                cas_key_pdf_href = find_cas_link(pdf_url, base_url)
                print(cas_key_pdf_href)

                pdf_content_extraction = extract_hazardous_data(cas_key_pdf_href)
                data.extend(pdf_content_extraction)

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

