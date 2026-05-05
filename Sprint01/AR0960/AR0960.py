import pandas as pd
import requests
from io import StringIO
import requests
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import common

errors = []
data = []

uniqueIdentity = 'AR0960'
region = 'North America'
jurisdiction = 'US'
category = 'Pesticides / Biocides'
title = 'Inert (other) Ingredients in Pesticide Products, FMA Fragrance Ingredient Database (26 December 2023)'
casKeyValue = ""

class UnsafeTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)
headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "host": "ordspub.epa.gov",
    "pragma": "no-cache",
    "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}   
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

session = requests.Session()
session.mount("https://", UnsafeTLSAdapter())

def download_csv_and_parse_with_unsafe_tls(session, url, headers):
    try:
        response = session.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()

        try:
            csv_text = response.content.decode("utf-8")
        except UnicodeDecodeError:
            csv_text = response.content.decode("latin1")

        df = pd.read_csv(StringIO(csv_text))
        second_col_name = df.columns[1]
        return df,second_col_name
    
    except Exception as e:
        raise Exception(f"❌ Failed to download or parse CSV: {e}")
    
def append_csv_data_to_global_data(df):
    global data
    for _, row in df.iterrows():
        data.append(row.to_dict())


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

        url = "https://ordspub.epa.gov/ords/pesticides/f?p=INERTFINDER:16:"
        All_links = get_all_links(url)

        if not All_links:
            raise Exception("No links found to process.")

        for index, url in enumerate(All_links):
            try:
                df, second_col_name = download_csv_and_parse_with_unsafe_tls(session, url, headers)
                print(f"🔗 Processing link {index+1}...")
                print("✅ CSV loaded successfully!")

                append_csv_data_to_global_data(df)
                global casKeyValue
                casKeyValue = second_col_name.replace(" ", "_")
                print(type(casKeyValue))

            except Exception as error:
                print(f"❌ There is an error with link {index+1}: {error}")
                log_error(f"An error has been encountered in link {index+1}: {error}")
                continue  

    except Exception as error:
        print("❌ Unable to retrieve content in main.")
        log_error(f"An error occurred in main setup: {error}")
        return

    finally:
        try: 
            create_final_json_file(data)    
        except Exception as error:
            print("❌ An error occurred while generating the JSON file")
            log_error(f"An error has been encountered during JSON creation: {error}")
            return

        
if __name__ == "__main__":
    main()

    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {error}")
    
