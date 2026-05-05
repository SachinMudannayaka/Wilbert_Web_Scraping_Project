import requests
from bs4 import BeautifulSoup, Tag
import common
from io import BytesIO
import pdfplumber
import re
import warnings
from urllib.parse import urljoin
import pandas as pd

errors = []
data = []

uniqueIdentity = 'AR0989'
region = 'Global Inventories'
jurisdiction = 'JP'
category = 'New Chemical Notification'
title = 'Japan. Class II Specified Chemical Substances (as amended through 12 September 1990)'
casKeyValue = "cas_rn"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
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
    
def main_soup_exctraction(url):
    """
    Extracts BeautifulSoup object from a given URL with proper error handling
    
    Args:
        url (str): URL to fetch and parse
        
    Returns:
        BeautifulSoup: Parsed HTML content or None if failed
        
    Raises:
        ValueError: If URL is empty or None
    """
    if not url:
        raise ValueError("URL cannot be empty or None")
        
    try:
        main_soup = getSoup(url)
        if main_soup is None:
            log_error(f"Failed to get soup from URL: {url}")
        return main_soup
    except Exception as e:
        log_error(f"Unexpected error in main_soup_exctraction for URL {url}: {str(e)}")
        raise

def to_get_main_table_data(main_soup,base_url):
    """
    Extracts table data with id="tb1" from BeautifulSoup object and returns pairs of
    Cabinet Order No. (with href link) and Class II Specified Chemical Substance Name.
    
    Args:
        main_soup (BeautifulSoup): Parsed HTML content
        
    Returns:
        list: A list of dictionaries containing 'order_no', 'href', and 'substance_name'
        
    Raises:
        TypeError: If main_soup is not a BeautifulSoup object
        ValueError: If main_soup is None or table not found
    """
    if main_soup is None:
        raise ValueError("main_soup cannot be None")
    if not isinstance(main_soup, BeautifulSoup):
        raise log_error(TypeError("main_soup must be a BeautifulSoup object"))
    
    try:
        table_data = main_soup.find("table", id="tb1")
        if table_data is None:
            raise log_error(ValueError("Table with id 'tb1' not found"))
    
        rows = table_data.find_all('tr')[1:-1]  
        
        result = []
        for row in rows:
            first_col = row.find('td')
            link = first_col.find('a')
            if link:
                order_no = link.text.strip()
                href = link.get('href', '')
            else:
                order_no = first_col.text.strip()
                href = ''
            
            second_col = row.find_all('td')[1] if len(row.find_all('td')) > 1 else None
            substance_name = second_col.text.strip() if second_col else ''
            
            result.append({
                'order_no': order_no,
                'href': urljoin(base_url,href),
                'substance_name': substance_name
            })
        
        return result
        
    except Exception as e:
        print(f"Error processing table: {str(e)}")
        log_error(f"Error processing table: {str(e)}")
        raise
        
    except Exception as e:
        print(f"Error processing table data: {str(e)}")
        log_error(f"Error processing table data: {str(e)}")
        raise

def iterate_all_chems(chem_list):
    chemicals = []
    """
    Iterates through the list of chemicals and prints href links
    
    Args:
        chem_list (list): List of chemical dictionaries returned by to_get_main_table_data()
    """
    for chemical_ in chem_list:
        inside_table_extraction = getSoup(chemical_['href'])
        table = inside_table_extraction.find('table', {'id': 'tb1'})
    
        if not table:
            raise log_error(ValueError("Table with id='tb1' not found"))
            

        rows = table.find_all('tr')
        for row in rows:
            if row.find('td', {'class': 'label'}):
                continue
                
            cells = row.find_all('td')
            if len(cells) >= 4:
                chemical = {
                    'no': chemical_['order_no'],
                    'class_Ⅱ_specified_chemical_substance_name' : chemical_['substance_name'],
                    'cas_rn': cells[1].get_text(strip=True),
                    'miti_number': cells[2].get_text(strip=True),
                    # 'chemical_substance_name': cells[3].get_text(strip=True),
                   
                }
                chemicals.append(chemical)
        
    return chemicals

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
            log_error(f"Failed to delete previous files: {e}")
            raise 

        url = "https://www.nite.go.jp/chem/jcheck/list6.action?category=212&request_locale=en"

        try:
            main_soup = main_soup_exctraction(url)
            if main_soup is None:
                raise ValueError("Failed to get main page content")
        except Exception as e:
            log_error(f"Main page extraction failed: {e}")
            raise
        try:
            table_soup = to_get_main_table_data(main_soup, url)
            if not table_soup:
                raise ValueError("No data found in main table")
        except Exception as e:
            log_error(f"Main table extraction failed: {e}")
            raise
        try:
            chemical_insider_table = iterate_all_chems(table_soup)
            if not chemical_insider_table:
                raise ValueError("No chemical data extracted from detail pages")
        except Exception as e:
            log_error(f"Chemical detail extraction failed: {e}")
            raise
        try:
            data.extend(chemical_insider_table)
        except Exception as e:
            log_error(f"Failed to combine results: {e}")
            raise

    except Exception as e:
        log_error(f"Critical error in main execution: {e}")

    finally:
        try:
            create_final_json_file(data)
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

if __name__ == "__main__":
    main()
    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {error}")