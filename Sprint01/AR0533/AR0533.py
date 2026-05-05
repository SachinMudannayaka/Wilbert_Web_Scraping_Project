import requests
from bs4 import BeautifulSoup
import common
import pandas as pd

errors = []
data = []

first_table_data = []
third_table_data = []
fourth_table_data = []

uniqueIdentity = 'AR0533'
region = 'North America'
jurisdiction = 'US'
category = 'Transportation'
title = 'DOT. Organic Peroxides Authorized for Transportation (49 CFR 173.225; as amended through 26 July 2022)'
casKeyValue = ""

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Priority": "u=0, i",
    "Sec-Ch-Ua": "\"Not/A)Brand\";v=\"8\", \"Chromium\";v=\"126\", \"Google Chrome\";v=\"126\"",
    "Sec-Ch-Ua-Arch": "\"x86\"",
    "Sec-Ch-Ua-Bitness": "\"64\"",
    "Sec-Ch-Ua-Full-Version": "\"126.0.6478.127\"",
    "Sec-Ch-Ua-Full-Version-List": "\"Not/A)Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"126.0.6478.127\", \"Google Chrome\";v=\"126.0.6478.127\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Model": "\"\"",
    "Sec-Ch-Ua-Platform": "\"Windows\"",
    "Sec-Ch-Ua-Platform-Version": "\"15.0.0\"",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

def getSoup(url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

def log_error(message):
    errors.append(message)

def get_all_links(url):
    try:
        return [url]
    except Exception as error:
        log_error("Unable to retrieve content.")
        return []


def parse_first_table(soup):
    table_data = []
    try:
        div = soup.find_all("div", class_="gpotbl_div")[0]
    except Exception as e:
        log_error(f"First div not found: {e}")
        return table_data
    
    target_table = None
    for table in div.find_all("table", class_="gpo_table"):
        caption = table.find("caption")
        if caption and "Organic Peroxide Table" in caption.get_text():
            target_table = table
            break
    if not target_table:
        log_error("Target table not found in first div")
        return table_data

    columns = [
        "Technical name", "ID No.", "Concentration (mass %)",
        "Diluent (mass %) A", "Diluent (mass %) B", "Diluent (mass %) I",
        "Water (mass %)", "Packing method", "Temperature (°C) Control",
        "Temperature (°C) Emergency", "Notes"
    ]
    try:
        rows = target_table.find("tbody").find_all("tr")
    except Exception as e:
        log_error(f"Error finding rows in first table: {e}")
        return table_data

    for row in rows[1:]:
        try:
            cells = row.find_all("td")
            if len(cells) != 11:
                continue
            row_data = [cell.get_text(strip=True) or None for cell in cells]
            row_dict = dict(zip(columns, row_data))
            table_data.append(row_dict)
        except Exception as e:
            log_error(f"Row error in first table: {e}")
    return table_data

def parse_third_table(soup):
    table_data = []
    try:
        div = soup.find_all("div", class_="gpotbl_div")[2]
    except Exception as e:
        log_error(f"Third div not found: {e}")
        return table_data

    table = div.find("table", class_="gpo_table")
    if not table:
        log_error("Table not found in third div")
        return table_data
    
    current_un_no = None
    try:
        rows = table.find("tbody").find_all("tr")
    except Exception as e:
        log_error(f"Error finding rows in third table: {e}")
        return table_data

    for row in rows:
        try:
            cells = row.find_all("td")
            if not cells or len(cells) < 6:
                continue
            un_no = cells[0].get_text(strip=True)
            organic_peroxide = cells[1].get_text(strip=True)
            type_of_ibc = cells[2].get_text(strip=True)
            max_quantity = cells[3].get_text(strip=True)
            control_temp = cells[4].get_text(strip=True)
            emergency_temp = cells[5].get_text(strip=True)
            if un_no:
                current_un_no = un_no
            if organic_peroxide.upper().startswith("ORGANIC PEROXIDE"):
                continue
            if un_no and not (organic_peroxide or type_of_ibc or max_quantity or control_temp or emergency_temp):
                continue
            table_data.append({
                "UN No.": current_un_no,
                "Organic peroxide": organic_peroxide or None,
                "Type of IBC": type_of_ibc or None,
                "Maximum quantity (liters)": max_quantity or None,
                "Control temperature": control_temp or None,
                "Emergency temperature": emergency_temp or None,
            })
        except Exception as e:
            log_error(f"Row error in third table: {e}")
    return table_data

def parse_fourth_table(soup):
    table_data = []
    try:
        div = soup.find_all("div", class_="gpotbl_div")[3]
    except Exception as e:
        log_error(f"Fourth div not found: {e}")
        return table_data

    table = div.find("table", class_="gpo_table")
    if not table:
        log_error("Table not found in fourth div")
        return table_data
    
    current_un_no = None
    try:
        rows = table.find("tbody").find_all("tr")
    except Exception as e:
        log_error(f"Error finding rows in fourth table: {e}")
        return table_data

    for row in rows:
        try:
            cells = row.find_all("td")
            if len(cells) != 9:
                continue
            un_no = cells[0].get_text(strip=True)
            hazardous_material = cells[1].get_text(strip=True)
            min_test_pressure = cells[2].get_text(strip=True)
            shell_thickness = cells[3].get_text(strip=True)
            bottom_opening = cells[4].get_text(strip=True)
            pressure_relief = cells[5].get_text(strip=True)
            filling_limits = cells[6].get_text(strip=True)
            control_temp = cells[7].get_text(strip=True)
            emergency_temp = cells[8].get_text(strip=True)
            if un_no:
                current_un_no = un_no
                if hazardous_material.upper().startswith("ORGANIC PEROXIDE"):
                    continue
            if un_no and not any([hazardous_material, min_test_pressure, shell_thickness,
                                  bottom_opening, pressure_relief, filling_limits,
                                  control_temp, emergency_temp]):
                continue
            table_data.append({
                "UN No.": current_un_no,
                "Hazardous material": hazardous_material or None,
                "Minimum test pressure (bar)": min_test_pressure or None,
                "Minimum shell thickness (mm-reference steel)": shell_thickness or None,
                "Bottom opening requirements": bottom_opening or None,
                "Pressure-relief requirements": pressure_relief or None,
                "Filling limits": filling_limits or None,
                "Control temperature": control_temp or None,
                "Emergency temperature": emergency_temp or None
            })
        except Exception as e:
            log_error(f"Row error in fourth table: {e}")
    return table_data

def full_soup_main(soup):
    try:
        first = parse_first_table(soup)
        third = parse_third_table(soup)
        fourth = parse_fourth_table(soup)
        
        first_table_data.extend(first)
        third_table_data.extend(third)
        fourth_table_data.extend(fourth)
    except Exception as e:
        log_error(f"Error in full_soup_main: {e}")

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)
        url = "https://www.ecfr.gov/current/title-49/subtitle-B/chapter-I/subchapter-C/part-173/subpart-E/section-173.225"
        All_links = get_all_links(url)
        for index, url in enumerate(All_links):
            try:
                soup = getSoup(url)
                print(f"🔗 Processing link {index+1}...")
                full_soup_main(soup)
            except Exception as error:
                log_error(f"An error has been encountered while processing link {url}: {error}")
    except Exception as error:
        log_error(f"An error has been encountered: {error}")
    finally:
        try:
            data.extend(first_table_data)
            data.extend(third_table_data)
            data.extend(fourth_table_data)
            create_final_json_file(data)
        except Exception as error:
            log_error(f"An error occurred while generating the JSON file: {error}")

if __name__ == "__main__":
    main()
    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {error}")
