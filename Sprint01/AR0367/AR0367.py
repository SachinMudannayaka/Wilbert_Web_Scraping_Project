import requests
from bs4 import BeautifulSoup
import common
import re
import pandas as pd

errors = []
data = []

uniqueIdentity = 'AR0367'
region = 'North America'
jurisdiction = 'CA'
category = 'Workplace Safety (OELs, BELs, GLP)'
title = 'Canada. Ontario OELs (Reg. 833, Control of Exposure to Biological or Chemical Agents, as amended through 4 January 2020)'
casKeyValue = "Agent_[CAS No.]"

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
    return response.json()

def log_error(message):
    errors.append(message)

def get_all_links(url):
    try:
        All_links = [url]
        return All_links
    except Exception as error:
        print("❌ Unable to retrieve content.")
        log_error("Unable to retrieve content.")
        return 

def extracting_table(soup):
    try:
        current_soup = BeautifulSoup(soup, "html.parser")
        all_chem = current_soup.find("table", class_="MsoNormalTable").find_all("tr")

        for row_index, i in enumerate(all_chem[1:], start=1): 
            try:
                listing = i.find_all("td")[0].text
                french_listing_equivalent = i.find_all("td")[1].text
                CAS_No = i.find_all("td")[2].text
                TWA = i.find_all("td")[3].text
                STEL = i.find_all("td")[4].text
                notations = i.find_all("td")[5].text

                data.append({
                    "Listing": listing,
                    "FLE": french_listing_equivalent,
                    "Agent_[CAS No.]": CAS_No,
                    "TWA": TWA,
                    "STEL": STEL,
                    "NOTATION": notations
                })
            except Exception as error:
                log_error(f"❌ Error processing row {row_index}: {error}")
    except Exception as error:
        log_error(f"❌ Error parsing table: {error}")

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)
        part = ""
        class_of_part = ""

        url = "https://www.ontario.ca/laws/api/v2/legislation/en/doc-search/regulation/900833"
        All_links = get_all_links(url)

        for index, url in enumerate(All_links):
            try:
                soup = getSoup(url)["content"]
                print(f"🔗 Processing link {index+1}...")
                extracting_table(soup)
            except Exception as error:
                print("❌ There is an error with the link")
                log_error(f"An error has been encountered: {error}")
                return
    except Exception as error:
        print("❌ Unable to retrieve content.")
        log_error(f"An error has been encountered: {error}")
        return
    finally:
        try:
            create_final_json_file(data)
        except Exception as error:
            print("❌ An error occurred while generating the JSON file")
            log_error(f"An error has been encountered: {error}")
            return

if __name__ == "__main__":
    main()

    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {error}")
