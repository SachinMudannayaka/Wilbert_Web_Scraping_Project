import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import pdfplumber
import re
import os
import common
from datetime import datetime

uniqueIdentity = "AR0450"
region = "Asia Pacific"
jurisdiction = "CN"
category = "Cosmetics/Personal Care"
title = "China. Prohibited Chemical Substances in Cosmetics (Safety and Technical Standards for Cosmetics, Ch. 2, Table 1; NMPA No. 2023-41, 28 August 2023)"
casKeyValue = "CAS_No"
date_str = datetime.now().strftime("%m%d%Y")
folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")
if not os.path.exists(folder_path):
    os.makedirs(folder_path)
 
errors = []
data = []

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

def log_error(message):
    errors.append(message)
    
def getSoup(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        errors.append(f"Error fetching {url}: {str(e)}")
        return None

def download_pdf(pdf_url, save_path):
    try:
        print(f"⬇️ Downloading PDF from: {pdf_url}")
        response = requests.get(pdf_url, headers=headers, timeout=20)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ PDF saved to: {save_path}")
        return True
    except Exception as e:
        errors.append(f"PDF download failed: {str(e)}")
        return False

def extract_prohibited_ingredients(pdf_path):
    extracted_rows = []
    notes_lookup = {}
    general_notes = []
    table_title_found = False

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_num = page.page_number
            if page_num < 11 or page_num > 91:
                continue

            print(f"🔍 Processing page {page_num}...")
            text = page.extract_text() or ""

            note_blocks = re.findall(r"(注（\d+）[:：])([\s\S]*?)(?=注（\d+）[:：]|$)", text)
            for note_header, note_body in note_blocks:
                note_num = note_header.strip()
                note_desc = re.sub(r"\s*\d{1,3}$", "", note_body.replace("\n", "").strip())
                general_notes.append({
                    "注释 (Notes)": note_num,
                    "描述 (Description)": note_desc
                })

            lines = text.split("\n")
            for line in lines:
                match = re.match(r"^(\d+)[.、)]\s*(.*)", line.strip())
                if match:
                    note_num = match.group(1).strip()
                    note_desc = match.group(2).strip()
                    notes_lookup[note_num] = note_desc

            if not table_title_found and "化妆品禁用原料目录" in text and "表" in text:
                table_title_found = True
                print(f"✅ Found table title on page {page_num}")

            if table_title_found:
                tables = page.extract_tables()
                for table in tables:
                    if not table or not table[0]:
                        continue

                    headers = [h.strip() if h else "" for h in table[0]]
                    if "序号" in headers and "中文名称" in headers and "英文名称" in headers:
                        idx_序号 = headers.index("序号")
                        idx_中文 = headers.index("中文名称")
                        idx_英文 = headers.index("英文名称")

                        for row in table[1:]:
                            if len(row) < 3:
                                continue

                            序号 = (row[idx_序号] or "").strip()
                            中文名称 = (row[idx_中文] or "").strip()
                            英文名称 = (row[idx_英文] or "").strip()

                            note_text = notes_lookup.get(序号, "")
                            note_num = 序号 if note_text else ""

                            base_row = {
                                "序号": 序号,
                                "中文名称": 中文名称,
                                "英文名称": 英文名称,
                                "CAS_No": re.search(r"CAS No\. ([\d\-]+)", 英文名称).group(1) if re.search(r"CAS No\. ([\d\-]+)", 英文名称) else "",
                                "注释 (Notes)": note_num,
                                "描述 (Description)": note_text
                            }

                            extracted_rows.append(base_row)

    return extracted_rows + general_notes

def create_final_json_file(data):
    df_filtered = pd.DataFrame(data)
    df_filtered = common.clean_newlines_in_dataframe(df_filtered)
    common.save_output_to_json(
        UniqueIdentity=uniqueIdentity,
        region=region,
        jurisdiction=jurisdiction,
        category=category,
        title=title,
        errors=errors,
        data=df_filtered,
        jsonPath=common.returnJsonPath(uniqueIdentity),
        casKeyValue=casKeyValue
    )
    print("✅ JSON file saved successfully!")

def main():
    try:
          
        common.deleteTodayFiles(uniqueIdentity)

        pdf_url = "https://www.nifdc.org.cn/directory/web/nifdc/infoAttach/dcb0dc40-b6c9-4cad-87ed-be3db0c32ad7.pdf"
        pdf_path = os.path.join(folder_path, f"{uniqueIdentity}_nifdc.pdf")

        if not download_pdf(pdf_url, pdf_path):
            return

        extracted_data = extract_prohibited_ingredients(pdf_path)

        if not extracted_data:
            print("⚠️ No data rows extracted from table.")
        else:
            data.extend(extracted_data)

    except Exception as error:
        print("❌ An error occurred during processing.")
        errors.append(f"Unhandled error in main: {str(error)}")
    finally:
        try:
            if data:
                create_final_json_file(data)
            else:
                print("⚠️ No data to save.")
        except Exception as error:
            print("❌ An error occurred while saving JSON.")
            errors.append(f"JSON save failed: {str(error)}")

if __name__ == "__main__":
    main()

    if errors:
        print("\n❗ Errors encountered:")
        for error in errors:
            print(f"- {error}")