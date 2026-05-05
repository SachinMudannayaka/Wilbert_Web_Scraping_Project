import re
import time
import random
import io
from io import BytesIO
from typing import List, Dict
from urllib.parse import urljoin

import requests
import pdfplumber
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup, NavigableString

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import common

errors = []
data = []

uniqueIdentity = 'AR1265'
region = 'North America'
jurisdiction = 'US'
category = 'PFAS'
title = 'New Jersey Discharge Tax List of Hazardous Substances (App. A to N.J.A.C. 7:1E as amended through 1 June 2020)'
casKeyValue = "CAS"

def get_fresh_cookies():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        target_url = "https://dep.nj.gov/brp/dphs/"
        driver.get(target_url)
        time.sleep(5)
        
        selenium_cookies = driver.get_cookies()
        cookies_dict = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
        
        return cookies_dict
    except Exception as e:
        raise Exception(f"Error getting cookies: {str(e)}")
    finally:
        if 'driver' in locals():
            try:
                driver.quit()
            except Exception as e:
                log_error(f"Error closing driver: {str(e)}")

session = requests.Session()
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

def get_all_links(url):
    try:
        return [url]
    except Exception as e:
        log_error(f"Error in get_all_links: {str(e)}")
        return []

def getSoup(url):
    try:
        cookies = get_fresh_cookies()
        if not cookies:
            log_error("No cookies obtained for the session")
            return None
            
        response = session.get(url, headers=headers, cookies=cookies, timeout=30)
        response.raise_for_status()
        
        if "Incapsula" in response.text:
            raise Exception("Blocked by Imperva security")
            
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        log_error(f"Request error getting soup from {url}: {str(e)}")
    except Exception as e:
        log_error(f"Unexpected error getting soup from {url}: {str(e)}")
    return None

def log_error(message):
    try:
        errors.append(message)
        print(f"ERROR: {message}")
    except Exception as e:
        print(f"CRITICAL ERROR IN LOGGING: {str(e)} - Original message: {message}")

def get_pdf_url_from_site(soup):
    try:
        if not soup:
            raise ValueError("No soup object provided")
            
        table = soup.find("table", class_="vc-table-plugin-theme-classic")
        if not table:
            raise ValueError("Target table not found")

        for link in table.find_all("a", href=True):
            if "Appendix A" in link.get_text(strip=True):
                pdf_url = urljoin("https://dep.nj.gov", link["href"])
                if not pdf_url:
                    raise ValueError("Failed to construct PDF URL")
                return pdf_url

        raise ValueError("Appendix A link not found")
    except ValueError as e:
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error extracting PDF URL: {str(e)}")

def get_all_extracted_data_pdf(pdf_url):
    chemicals = []
    try:
        cookies = get_fresh_cookies()
        if not cookies:
            raise Exception("Failed to get cookies for PDF download")
            
        response = session.get(pdf_url, headers=headers, cookies=cookies, timeout=60)
        response.raise_for_status()
        
        if not response.content:
            raise ValueError("Empty PDF content received")
        
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            if not pdf.pages:
                raise ValueError("No pages found in PDF")
                
            print(f"Processing PDF with {len(pdf.pages)} pages...\n")
            
            for page_num in range(1, 54):
                try:
                    if page_num >= len(pdf.pages):
                        break
                        
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    
                    if not text:
                        continue
                        
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line or line.startswith("This is a courtesy copy") or line.startswith("N.J.A.C."):
                            continue
                        
                        match = re.match(r'^(.+?)\s+(\d{2,7}-\d{2}-\d|\*{3,5})$', line)
                        if match:
                            name = match.group(1).strip()
                            cas = match.group(2).strip()
                            chemicals.append({
                                "Name": name,
                                "CAS": None if cas == '*****' else cas
                            })
                except Exception as e:
                    log_error(f"Error processing page {page_num}: {str(e)}")
                    continue
    
            for page_num in range(54, len(pdf.pages)):
                try:
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    
                    if not text:
                        continue
                        
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line or line.startswith("This is a courtesy copy") or line.startswith("N.J.A.C.") or line.startswith("APPENDIX A"):
                            continue
                        
                        match = re.match(r'^(\d{2,7}-\d{2}-\d|\*{3,5})\s+(.+)$', line)
                        if not match:
                            match = re.match(r'^([*\d -]+)\s{2,}(.*)$', line)
                        
                        if match:
                            cas = match.group(1).strip()
                            name = match.group(2).strip()
                            chemicals.append({
                                "Name": name,
                                "CAS": None if cas == '*****' else cas
                            })
                except Exception as e:
                    log_error(f"Error processing page {page_num}: {str(e)}")
                    continue
    
    except pdfplumber.PDFSyntaxError as e:
        raise Exception(f"Invalid PDF file: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error downloading PDF: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error processing PDF: {str(e)}")
    
    try:
        seen = set()
        unique_chemicals = []
        for chem in chemicals:
            try:
                key = tuple(sorted(chem.items()))
                if key not in seen:
                    seen.add(key)
                    unique_chemicals.append(chem)
            except Exception as e:
                log_error(f"Error processing chemical entry: {str(e)} - Entry: {chem}")
                continue
                
        unique_chemicals.sort(key=lambda x: x["Name"].lower() if x["Name"] else "")
        return unique_chemicals
    except Exception as e:
        raise Exception(f"Error deduplicating chemicals: {str(e)}")

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
            log_error(f"Error cleaning old files: {str(e)}")
        
        base_url = "https://dep.nj.gov/brp/dphs/"
        
        soup = getSoup(base_url)
        if not soup:
            raise Exception("Failed to get page content")
        
        pdf_url = get_pdf_url_from_site(soup)
        if not pdf_url:
            raise Exception("Failed to find PDF URL")
        
        all_extracted_data_pdf = get_all_extracted_data_pdf(pdf_url)
        if not all_extracted_data_pdf:
            log_error("No data extracted from PDF")
        else:
            data.extend(all_extracted_data_pdf)
        
    except Exception as e:
        log_error(f"Main execution error: {str(e)}")

    finally:
        try:
            if data or errors:
                create_final_json_file(data)
            else:
                log_error("No data or errors to save")
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")
    else:
        print("\n✅ No errors encountered during execution")


if __name__ == "__main__":
    main()