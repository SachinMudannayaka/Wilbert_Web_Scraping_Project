import pdfplumber
import requests
from bs4 import BeautifulSoup
import common
import os
import re
import camelot
import pandas as pd
from datetime import datetime

errors = []
data = []

uniqueIdentity = 'AR0544'
region = 'Central / Eastern Europe'
jurisdiction = 'EE'
category = 'Environment'
title = 'Estonia. Environmental quality limit values for priority substances, priority hazardous substances and certain other pollutants (Reg. No 28/2019, Table to article 3, as amended through Dec. 31, 2021)'
casKeyValue = ""
date_str = datetime.now().strftime("%m%d%Y")
folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

headers = {
    "User-Agent": "Mozilla/5.0",
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

def download_file(url, target_directory, file_name=None):
    try:
        os.makedirs(target_directory, exist_ok=True)
        print(f"⏳ Please wait... downloading file...")

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        if not file_name:
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition and 'filename=' in content_disposition:
                file_name = content_disposition.split('filename=')[1].strip('"')
            else:
                file_name = "downloaded_file.pdf"

        file_path = os.path.join(target_directory, file_name)
        with open(file_path, 'wb') as f:
            f.write(response.content)

        print(f"✅ File successfully downloaded to: {file_path}")
        return file_path

    except requests.exceptions.RequestException as e:
        print(f"🚨 Download failed: {e}")
    except Exception as e:
        print(f"😵 Unexpected error: {e}")
    return None

def extract_from_pdf_table_one(pdf_path):
    records = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[0:2]:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 4:
                        continue

                    number = row[0].strip() if row[0] else ""
                    cas = row[1].strip().replace(" ", "") if row[1] else ""
                    eu = row[2].strip().replace(" ", "") if row[2] else ""
                    name = row[3].strip() if row[3] else ""
                    hazard = row[4].strip() if len(row) > 4 and row[4] else ""

                    if not re.match(r"^\(\d+\)$", number):
                        continue

                    if not re.match(r"^\d{2,7}-\d{2}-\d$", cas) and re.match(r"^\d{2,7}-\d{2}-\d$", eu):
                        name, cas, eu = cas, eu, name

                    hazard = hazard.strip()
                    if not hazard and len(row) > 5:
                        for col in row[5:]:
                            if col and re.search(r"[xX⁰¹²³⁴⁵⁶⁷⁸⁹]", col):
                                hazard = col.strip()
                                break

                    cas = cas if cas else "eikohaldata"
                    eu = eu if eu else "eikohaldata"

                    record = {
                        "Number": number,
                        "CASi_number1": cas,
                        "EÜ_number2": eu,
                        "Prioriteetse_aine_nimetus3": name,
                        "Prioriteetne_ohtlik_aine": hazard 
                    }

                    records.append(record)

    df_final = pd.DataFrame(records)

    df_final = df_final[~df_final["CASi_number1"].str.lower().isin(["alakloor", "antratseen"])]

    df_final = df_final.drop_duplicates(subset=["CASi_number1", "EÜ_number2", "Prioriteetse_aine_nimetus3"])

    return df_final.reset_index(drop=True)

def extract_from_pdf_table_two(pdf_path):
    records = []
    last_number = ""
    first_row_skipped = False

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[2:5]: 
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    if not row or len(row) < 4:
                        continue

                    number = row[0].strip() if row[0] else ""
                    name = row[1].strip() if row[1] else ""
                    cas_raw = row[2].strip() if row[2] else ""

                    if number:
                        last_number = number 
                    else:
                        number = last_number

                    if not name:
                        continue

                    if not first_row_skipped:
                        first_row_skipped = True
                        continue

                    cas_clean = (
                        "ei kohaldata" if "ei kohaldata" in cas_raw.lower()
                        else re.sub(r"[^\d\-]", "", cas_raw)
                    )

                    def get_cell(idx):
                        return row[idx].strip().replace(",", ".") if len(row) > idx and row[idx] else ""

                    sediment_value = get_cell(8)
                    if "ei kohaldataei kohaldata" in sediment_value.replace(" ", ""):
                        sediment_maismaa = "ei kohaldata"
                        sediment_muu = "ei kohaldata"
                    else:
                        sediment_maismaa = sediment_value
                        sediment_muu = get_cell(9) if get_cell(9) else sediment_value

                    records.append({
                        "Nr": number,
                        "Aine_nimetus15": name,
                        "CASi_number1": cas_clean,
                        "Aasta_keskmine_keskkonna_kvaliteedi_piirväärtus2_maismaa_pinnavees3,µg/l": get_cell(3),
                        "Aasta_keskmine_keskkonna_kvaliteedi_piirväärtus2_muus_pinnavees,µg/l": get_cell(4),
                        "Suurim_lubatud_keskkonna_kvaliteedi_piirväärtus4_maismaa_pinnavees3,µg/l": get_cell(5),
                        "Suurim_lubatud_keskkonna_kvaliteedi_piirväärtus4_muus_pinnavees,µg/l": get_cell(6),
                        "Keskkonna_kvaliteedi_piirväärtus_kalades12,µg/kg_koe_märgkaal": get_cell(7),
                        "Keskkonna_kvaliteedi_piirväärtus_põhjasettes(maismaa_pinnavesi3),µg/kg_kuivkaal": sediment_maismaa,
                        "Keskkonna_kvaliteedi_piirväärtus_põhjasettes(muu_pinnavesi),µg/kg_kuivkaal": sediment_muu
                    })

    return pd.DataFrame(records).reset_index(drop=True)

def extract_from_pdf_table_three(pdf_path):
    records = []

    def get_section_by_nr(nr):
        try:
            num = int(re.search(r'\d+', nr).group())
        except:
            return ""

        if 1 <= num <= 6:
            return "METALLID"
        elif 7 <= num <= 15:
            return "ORGAANILISED ÜHENDID"
        elif num == 16:
            return "MUUD ANORGAANILISED ÜHENDID"
        elif 17 <= num <= 23:
            return "TAIMEKAITSEVAHENDID"
        else:
            return ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[5:7]: 
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 4:
                        continue

                    nr = row[0].strip() if row[0] else ""
                    name = row[1].strip() if row[1] else ""
                    cas = row[2].strip().replace(" ", "") if row[2] else ""
                    value = row[3].strip().replace(",", ",") if row[3] else ""

                    if not name or not nr or "nimetus" in name.lower():
                        continue

                    cas_cleaned = (
                        "ei kohaldata"
                        if "ei kohaldata" in cas.lower()
                        else "; ".join([re.sub(r"[^\d\-]", "", part) for part in cas.split(";") if part.strip()])
                    )

                    nr_cleaned = nr if re.match(r"^\(?\d+[a-z]?\)?$", nr) else ""

                    section = get_section_by_nr(nr_cleaned)

                    entry = {
                        "Section": section,
                        "Nr": nr_cleaned,
                        "Aine_nimetus": name,
                        "CASi_number1": cas_cleaned,
                        "Aasta_keskmine_kvaliteedi_piirväärtus_µg/l": value
                    }
                    records.append(entry)

    return records

def create_final_json_file(data, casKeyValue):
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
            log_error(f"Error deleting today's files: {e}")

        try:
            base_url_1 = "https://faolex.fao.org/docs/pdf/est206027.pdf"
            target_directory = folder_path
            download_file(base_url_1, target_directory, "three_tables_.pdf")

            list_info_path = os.path.join(folder_path, 'three_tables_.pdf')

            print(f"😊 Capturing data from first table… please wait ⏳")
            first_table_data = extract_from_pdf_table_one(list_info_path)

            print(f"😊 Capturing data from second table… please wait ⏳")
            second_table_data = extract_from_pdf_table_two(list_info_path)

            print(f"😊 Capturing data from third table… please wait ⏳")
            third_table_data = extract_from_pdf_table_three(list_info_path)

        except Exception as e:
            log_error(f"Error downloading or reading PDF: {e}")

    except Exception as e:
        log_error(f"General error in main: {e}")

    finally:
        try:
            create_final_json_file(first_table_data, "CASi_number1")
            print(f"✅ {len(first_table_data)} ROWS AFFECTED FIRST TABLE")

            create_final_json_file(second_table_data, "CASi_number1")
            print(f"✅ {len(second_table_data)} ROWS AFFECTED SECOND TABLE")

            create_final_json_file(third_table_data, "CASi_number1")
            print(f"✅ {len(third_table_data)} ROWS AFFECTED THIRD TABLE")

        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")

if __name__ == "__main__":
    main()
