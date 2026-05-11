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

uniqueIdentity = 'AR0260'
region = 'Latin America'
jurisdiction = 'BR'
category = 'Controlled Drugs & Precursors'
title = 'Brazil. Proscribed Plants and Fungi that can Produce Narcotic and Psychotropic substances (ANVISA Ordinance No. 344/98, Annex I, List E, last updated by RDC No 816 of 15 September 2023'
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

def extract_lista_e_section(soup):
    try:
        start_marker = soup.find('b', string=lambda text: text and 'LISTA - E' in text)
        if not start_marker:
            return None

        end_marker = soup.find('b', string=lambda text: text and 'LISTA - F' in text)
        if not end_marker:
            return None

        section_content = []
        current = start_marker.find_parent().find_next_sibling()

        while current and current != end_marker.find_parent():
            section_content.append(current)
            current = current.find_next_sibling()

        return section_content
    except Exception as e:
        log_error(f"Error in extract_lista_e_section: {e}")
        return None

def extract_plants_list(soup):
    try:
        section = extract_lista_e_section(soup)
        if not section:
            return []

        plants = []
        for element in section:
            if element.name != 'p':
                continue

            text = element.get_text(strip=True)
            if 'ADENDO:' in text:
                break

            match = re.match(r'^(\d+)\.\s*(.*)', text)
            if match:
                plants.append({
                    "Title": "LISTA DE PLANTAS E FUNGOS PROSCRITOS QUE PODEM ORIGINAR SUBSTÂNCIAS ENTORPECENTES E/OU PSICOTRÓPICAS",
                    "Number": match.group(1),
                    "Name_of_the_plant": match.group(2).strip()
                })

        return plants
    except Exception as e:
        log_error(f"Error in extract_plants_list: {e}")
        return []

def extract_addendum_items(soup):
    try:
        section = extract_lista_e_section(soup)
        if not section:
            return []

        addendum_items = []
        in_addendo = False

        for element in section:
            if element.name != 'p':
                continue

            text = element.get_text(strip=True)

            if 'ADENDO:' in text:
                in_addendo = True
                continue

            if in_addendo:
                match = re.match(r'^(\d+)\)\s*(.*)', text)
                if match:
                    number_without_parenthesis = match.group(1)

                    description_parts = []
                    for content in element.contents:
                        if content.name == 'a':
                            description_parts.append(' ' + content.get_text(strip=True))
                        elif isinstance(content, str):
                            description_parts.append(content.strip())
                        else:
                            description_parts.append(content.get_text(strip=True))

                    description = ''.join(description_parts)

                    addendum_items.append({
                        "Title": "ADENDO",
                        "Number": number_without_parenthesis,
                        "Description": description
                    })

        return addendum_items
    except Exception as e:
        log_error(f"Error in extract_addendum_items: {e}")
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

        base_url = "https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirTextoAto&link=S&tipo=RDC&numeroAto=00000974&seqAto=000&valorAno=2025&orgao=RDC/DC/ANVISA/MS&codTipo=&desItem=&desItemFim=&cod_modulo=134&cod_menu=9451"

        soup = getSoup(base_url)
        if not soup:
            log_error(f"Failed to fetch or parse soup for: {base_url}")

        first_table_of_e = extract_plants_list(soup)
        second_table_of_e = extract_addendum_items(soup)

        data.extend(first_table_of_e)
        data.extend(second_table_of_e)

        print("Extraction completed. Total items collected:", len(data))
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
