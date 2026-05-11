import requests
from bs4 import BeautifulSoup
import common
import io
from io import BytesIO
import pdfplumber
import re
from typing import List, Dict
import pandas as pd

errors = []
data = []

uniqueIdentity = 'AR0848'
region = 'Western Europe'
jurisdiction = 'DE'
category = 'Disaster Prevention/Hazardous Substances Reporting'
title = 'Germany.Foreign Trade Ordinance (AWV), Energetic materials, (Annex I, Part1(A), Item 0008), as amended by Bundesanzeiger (Banz) AT 07.09.2021 V1'
casKeyValue = "CAS_No"

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
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

def get_value(all_entries, val_1, ame, val_2, val_3, val_4):
    if not ("Anmerkung" in val_3 or "Anmerkung" in val_4):
        match_1 = re.search(r"\(CAS-Nr\.\s*(\d+-\d+-\d+)\)", val_2)
        match_2 = re.search(r"\(CAS-Nr\.\s*(\d+-\d+-\d+)\)", val_3)
        match_3 = re.search(r"\(CAS-Nr\.\s*(\d+-\d+-\d+)\)", val_4)

        cas = ""
        if match_1:
            cas = match_1.group(1)
            val_2 = re.sub(r"\(CAS-Nr\.\s*\d+-\d+-\d+\)", "", val_2).replace(" ,", ",")
        elif match_2:
            cas = match_2.group(1)
            val_3 = re.sub(r"\(CAS-Nr\.\s*\d+-\d+-\d+\)", "", val_3).strip().replace(" ,", ",")
        elif match_3:
            cas = match_3.group(1)
            val_4 = re.sub(r"\(CAS-Nr\.\s*\d+-\d+-\d+\)", "", val_4).strip().replace(" ,", ",")

        entry = {
            "CAS No": cas,
            "Type of Substance": val_1,
            "Anmerkung": ame,
            "Name of Substances": val_2,
            "Name of Substances - Sub list I": val_3,
            "Name of Substances - Sub list II": val_4,
        }
        all_entries.append(entry)

def extract_substance_data():
    url = "https://www.gesetze-im-internet.de/awv_2013/anlage_1.html"
    soup = getSoup(url)
    all_entries = []

    section_tag = soup.find("dt", string="0008").find_next_sibling("dd")
    section_tag_1 = section_tag.find("span", string="Technische Anmerkungen:").find_parent("div").find_next_sibling("div")

    type_of_substance = []
    sub_tag = section_tag_1.find("dt")
    type_of_substance.append(sub_tag)
    type_of_substance.extend(sub_tag.find_next_siblings("dt"))

    for sin_sub in type_of_substance:
        div_tag_1 = sin_sub.find_next_sibling("dd").find("div")
        substance_name = sin_sub.get_text() + div_tag_1.find(string=True)

        if substance_name == "g)„Vorprodukte“ wie folgt: ":
            div_tag_1 = div_tag_1.find_next_sibling("div")

        chem_name_tag = div_tag_1.find("dt")
        name_of_substance = [chem_name_tag]
        name_of_substance.extend(chem_name_tag.find_next_siblings("dt"))

        for sin_chem in name_of_substance:
            div_tag_2 = sin_chem.find_next_sibling("dd").find("div")
            chem_name = sin_chem.get_text() + div_tag_2.find(string=True)

            if div_tag_2.find("dt"):
                chem_name_tag_1 = div_tag_2.find("dt")
                name_of_substance_1 = [chem_name_tag_1]
                name_of_substance_1.extend(chem_name_tag_1.find_next_siblings("dt"))

                for chem_sub in name_of_substance_1:
                    div_tag_3 = chem_sub.find_next_sibling("dd").find("div")
                    sub_1 = chem_sub.get_text() + div_tag_3.find(string=True)

                    if div_tag_3.find("dt"):
                        chem_name_tag_2 = div_tag_3.find("dt")
                        name_of_substance_2 = [chem_name_tag_2]
                        name_of_substance_2.extend(chem_name_tag_2.find_next_siblings("dt"))

                        for sub_chem in name_of_substance_2:
                            div_tag_4 = sub_chem.find_next_sibling("dd").find("div")
                            sub_2 = sub_chem.get_text() + div_tag_4.find(string=True)
                            get_value(all_entries, substance_name, "", chem_name, sub_1, sub_2)
                    else:
                        get_value(all_entries, substance_name, "", chem_name, sub_1, "")
            else:
                get_value(all_entries, substance_name, "", chem_name, "", "")

    pre_note_tag = section_tag_1.find_next_sibling("div")
    all_note_tag = pre_note_tag.find_all("span", string=re.compile("Anmerkung "))

    for sin_note_tag in all_note_tag:
        note_name = sin_note_tag.get_text()
        note_div_tag = sin_note_tag.find_parent("dt").find_next_sibling("dd").find("div")
        sub_note_name = note_div_tag.find("span").get_text()
        all_dt_tag = note_div_tag.find_all("dt")

        if all_dt_tag:
            for sin_dt_tag in all_dt_tag:
                sub_note_name_2 = sin_dt_tag.get_text() + " " + sin_dt_tag.find_next_sibling("dd").find("div").get_text()
                get_value(all_entries, "", note_name, sub_note_name, sub_note_name_2, "")
        else:
            get_value(all_entries, "", note_name, sub_note_name, "", "")

    return all_entries

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(uniqueIdentity, region, jurisdiction, category, title, errors, df_filtered,
                               common.returnJsonPath(uniqueIdentity), casKeyValue)
    print("✅ Work done!")

def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)
        data = extract_substance_data()
    except Exception as e:
        log_error(f"General error in main: {e}")
        data = []

    finally:
        try:
            create_final_json_file(data)
            print(f'🙂 {len(data)} Rows Affected')
        except Exception as error:
            log_error(f"Fatal error in JSON generation: {error}")

    if errors:
        print("\n⚠️ Errors encountered:")
        for err in errors:
            print(f"- {err}")


if __name__ == "__main__":
    main()
