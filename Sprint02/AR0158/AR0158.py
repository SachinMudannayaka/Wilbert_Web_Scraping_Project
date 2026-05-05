import os
import re
from bs4 import BeautifulSoup
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed
import cloudscraper
import camelot
import common

uniqueIdentity = "AR0158"
region = "Asia Pacific"
jurisdiction = "APAC"
category = "Cosmetics/Personal Care"
title = "ASEAN. Restricted Cosmetic Ingredients (ASEAN Cosmetics Directive, Annex III, Part 1, as revised through 38th ACC meeting, December 2023)"
casKeyValue = "Substance/CAS_No(19)"

out_dir = "out1"
pdf_path = os.path.join(out_dir, "New.pdf")

headers = {
    "User-Agent": "Mozilla/5.0"
}
scraper = cloudscraper.create_scraper()

def log_error(message):
    print(f"❌ {message}")
    errors.append(message)

errors = []
data = []

os.makedirs(out_dir, exist_ok=True)


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def download_pdf(url, path):
    r = scraper.get(url, headers=headers, stream=True, timeout=120)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"✅ Downloaded PDF to {path}")


def get_latest_pdf_url():
    search_page = "https://www.hsa.gov.sg/cosmetic-products/asean-cosmetic-directive"
    try:
        print(f"🌐 Scraping for latest PDF link from {search_page}")
        res = scraper.get(search_page, headers=headers, timeout=60)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        link = soup.find(
            "a",
            href=re.compile(r"annexes-of-the-asean-cosmetic-directive-\(updated-july25\).pdf", re.I),
            title="Annexes of the ASEAN Cosmetic Directive"
        )
        if link and link.get("href"):
            href = link["href"]
            return href if href.startswith("http") else "https://www.hsa.gov.sg" + href

        raise Exception("No matching Annexes PDF link found.")

    except Exception as e:
        errors.append(f"❌ Failed to retrieve latest PDF URL: {e}")
        return None

def insert_line_breaks(text):
    
    text = re.sub(r"\s*(?=CAS\s+No)", r"\n", text)

    
    text = re.sub(r"\s*(?=\([a-z]\))", r"\n", text)

    
    text = re.sub(r'\n+', '\n', text)

    return text.strip()


def extract_with_camelot(pdf_path, start_page=103, end_page=256):
    extracted = []

    header_mapping = {
        "Column_0": "Ref No ACD # (EU #)",
        "Column_1": "Substance/CAS_No(19)",
        "Column_2": "Restrictions - Field of application and/or use",
        "Column_3": "Restrictions - Maximum authorised concentration in the ready for use preparation",
        "Column_4": "Restrictions - Other limitations and requirements",
        "Column_5": "Conditions of use and warning labels"
    }

    known_headers = {
        "Ref No ACD # (EU #)",
        "Substance/CAS No(19)",
        "Restrictions",
        "Field of application and/or use",
        "Maximum authorised concentration in the ready for use preparation",
        "Other limitations and requirements",
        "Conditions of use and warning which must be printed on the labels"
    }

    column_letters = {"A", "B", "C", "D", "E", "F"}

    try:
        tables = camelot.read_pdf(
            filepath=pdf_path,
            pages=f"{start_page}-{end_page}",
            flavor="lattice",
            strip_text="\n",
            line_scale=40
        )
        print(f"📊 Camelot found {tables.n} tables in pages {start_page}–{end_page}")

        for t in tables:
            df = t.df
            df.columns = [f"Column_{i}" for i in range(len(df.columns))]
            df = df.replace(r'\n', ' ', regex=True)
            df = df.applymap(lambda x: re.sub(r"\s+", " ", x.strip()))

            df = df.rename(columns=lambda c: header_mapping.get(c, c))

            for _, row in df.iterrows():
                row_dict = row.to_dict()
                values = [v.strip() for v in row_dict.values()]

                if all(v == "" for v in values):
                    continue

                if any(v in known_headers for v in values):
                    continue

                if sum(1 for v in values if v in column_letters) >= len(values) - 1:
                    continue

                for key in row_dict:
                    row_dict[key] = insert_line_breaks(row_dict[key])

                extracted.append(row_dict)

    except Exception as e:
        errors.append(f"❌ Camelot extraction failed (pages {start_page}-{end_page}): {e}")

    return extracted


def create_final_json(data):
    if not data:
        print("⚠️ No data to save!")
        errors.append("❌ No data extracted from specified table range.")
        return

    df = pd.DataFrame(data).fillna("").astype(str)
    df.columns = [c.replace(" ", "_") for c in df.columns]
    df = common.clean_newlines_in_dataframe(df)

    common.save_output_to_json(
        UniqueIdentity=uniqueIdentity,
        region=region,
        jurisdiction=jurisdiction,
        category=category,
        title=title,
        errors=errors,
        data=df,
        jsonPath=common.returnJsonPath(uniqueIdentity),
        casKeyValue=casKeyValue
    )
    print("✅ JSON saved successfully!")


def main():
    try:
        common.deleteTodayFiles(uniqueIdentity)

        pdf_url = get_latest_pdf_url()
        if not pdf_url:
            raise Exception("Could not fetch the PDF URL dynamically.")

        print(f"📥 Downloading PDF from {pdf_url}")
        download_pdf(pdf_url, pdf_path)

        print(f"📄 Extracting detailed table data from pages 103–256...")
        global data
        data = extract_with_camelot(pdf_path, start_page=103, end_page=256)

        print(f"✅ Extracted {len(data)} entries.")
        create_final_json(data)

    except Exception as e:
        errors.append(f"❌ Exception in main(): {e}")

    finally:
        if errors:
            print("\n❗ Errors encountered:")
            for err in errors:
                print(f"- {err}")
        else:
            print("✅ Script completed without critical errors.")


if __name__ == "__main__":
    main()
