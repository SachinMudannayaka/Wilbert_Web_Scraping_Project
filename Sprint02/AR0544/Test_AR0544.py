import unittest
import pandas as pd
import os
from unittest.mock import patch, MagicMock,mock_open,call,Mock
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import random
import json
import os
import glob
import AR0544

from AR0544 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,extract_from_pdf_table_two,extract_from_pdf_table_three)

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

class Test_AR1330(unittest.TestCase):

    @staticmethod
    def find_latest_folder():
        main()
        folder_path = "out"
        subfolders = [f for f in glob.glob(os.path.join(folder_path, "*")) if os.path.isdir(f)]

        if not subfolders:
            print("No subfolders found in the 'out' directory.")
            return None

        latest_folder = max(subfolders, key=os.path.getmtime)
        print(f"The latest folder is: {latest_folder}")
        return latest_folder

    @staticmethod
    def find_all_json_files():
        latest_folder = Test_AR1330.find_latest_folder()
        if not latest_folder:
            return []

        json_files = glob.glob(os.path.join(latest_folder, "*.json"))
        if json_files:
            print(f"Found JSON files: {json_files}")
            return json_files
        else:
            print("No JSON files found in the latest folder.")
            return []

    @classmethod
    def setUpClass(cls):
        cls.test_json_paths = sorted(glob.glob("test_*.json")) 
        cls.current_json_paths = sorted(cls.find_all_json_files()) 


        if not cls.current_json_paths or not cls.test_json_paths:
            raise FileNotFoundError("No JSON files found for comparison.")

        cls.test_json_data_dic = {}
        for index, test_path in enumerate(cls.test_json_paths, start=1):
            with open(test_path, "r", encoding="utf-8") as test_f:
                tkey = f"test_json_data_{index}"  
                cls.test_json_data_dic[tkey] = json.load(test_f)  


        cls.current_json_data_dic = {}
        for index, json_path in enumerate(cls.current_json_paths, start=1):
            with open(json_path, "r", encoding="utf-8") as actual_f:
                cls.current_json_data_dic[f"current_json_data_{index}"] = json.load(actual_f)


    def test_01_json_required_keys(self):
        required_keys = {"UniqueIdentity","region","Jurisdiction", "category", "title", "casKey", "dateAndTime", "errors", "data"}
        for json_data in self.current_json_data_dic.values():
            self.assertTrue(required_keys.issubset(json_data.keys()))

    def test_02_json_key_data_types(self):
        for json_data in self.current_json_data_dic.values():
            self.assertIsInstance(json_data["UniqueIdentity"], str)
            self.assertIsInstance(json_data["region"], str)
            self.assertIsInstance(json_data["Jurisdiction"], str)
            self.assertIsInstance(json_data["category"], str)
            self.assertIsInstance(json_data["title"], str)
            self.assertIsInstance(json_data["casKey"], (str, type(None)))
            self.assertIsInstance(json_data["errors"], list)
            self.assertIsInstance(json_data["data"], list)

    def test_03_json_column_and_row_consistency(self):
        for json_data in self.current_json_data_dic.values():
            first_row_keys = set(json_data["data"][0].keys())
            for row in json_data["data"]:
                self.assertEqual(set(row.keys()), first_row_keys)

    def test_04_json_column_name_and_count(self):
        for index, (json_key, json_data) in enumerate(self.current_json_data_dic.items(), start=1):
            test_key = f"test_json_data_{index}"

            if test_key in self.test_json_data_dic:
                with self.subTest(json_file=index):

                    actual_column_count = len(json_data["data"][0].keys())
                    test_column_count = len(self.test_json_data_dic[test_key]["data"][0].keys())
                    self.assertEqual(test_column_count, actual_column_count)
                    self.assertEqual(self.test_json_data_dic[test_key]["data"][0].keys(), json_data["data"][0].keys())

    def test_05_json_meta_content(self):
        for index, (json_key, json_data) in enumerate(self.current_json_data_dic.items(), start=1):
            test_key = f"test_json_data_{index}"
            if test_key in self.test_json_data_dic:
                with self.subTest(json_file=index):
                    self.assertEqual(json_data["title"], self.test_json_data_dic[test_key]["title"])
                    self.assertEqual(json_data["UniqueIdentity"], self.test_json_data_dic[test_key]["UniqueIdentity"])
                    self.assertEqual(json_data["region"], self.test_json_data_dic[test_key]["region"])
                    self.assertEqual(json_data["Jurisdiction"], self.test_json_data_dic[test_key]["Jurisdiction"])
                    self.assertEqual(json_data["category"], self.test_json_data_dic[test_key]["category"])
                    self.assertEqual(json_data["casKey"], self.test_json_data_dic[test_key]["casKey"])
                    datetime.strptime(json_data["dateAndTime"], "%Y-%m-%d %H:%M:%S")

    def test_06_json_data_content(self):
        for index, (json_key, json_data) in enumerate(self.current_json_data_dic.items(), start=1):
            test_key = f"test_json_data_{index}"
            if test_key in self.test_json_data_dic:
                with self.subTest(json_file=index):
                    current_all_sha_hashes = [item["sha_hash"] for item in json_data["data"]]
                    sample_size = min(10, len(current_all_sha_hashes))
                    sampled_sha_hashes = random.sample(current_all_sha_hashes, sample_size)
                    test_sha_hashes = {item["sha_hash"] for item in self.test_json_data_dic[test_key]["data"]}

                    for current_sha_hash in sampled_sha_hashes:
                        self.assertIn(current_sha_hash, test_sha_hashes,
                                      f"SHA hash {current_sha_hash} not found in test JSON data")

    @patch('AR0544.requests.get')
    def test_get_soup_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><p>Hello</p></body></html>'
        mock_get.return_value = mock_response

        from AR0544 import getSoup
        soup = getSoup("http://example.com")
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.p.text, "Hello")

    @patch('AR0544.requests.get')
    @patch('AR0544.log_error')
    def test_get_soup_failure(self, mock_log_error, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        from AR0544 import getSoup
        soup = getSoup("http://example.com")
        self.assertIsNone(soup)
        mock_log_error.assert_called_once()

    @patch('AR0544.requests.get')
    @patch('AR0544.open', new_callable=mock_open)
    @patch('AR0544.os.makedirs')
    def test_download_file_success_with_filename(self, mock_makedirs, mock_open_file, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"file content"
        mock_response.headers = {'Content-Disposition': 'attachment; filename="testfile.pdf"'}
        mock_get.return_value = mock_response

        from AR0544 import download_file
        path = download_file("http://example.com/file", "/testdir")
        self.assertTrue(path.endswith("testfile.pdf"))
        mock_open_file.assert_called_once()
        mock_makedirs.assert_called_once_with("/testdir", exist_ok=True)

    @patch('AR0544.requests.get')
    @patch('AR0544.open', new_callable=mock_open)
    @patch('AR0544.os.makedirs')
    def test_download_file_success_without_content_disposition(self, mock_makedirs, mock_open_file, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"file content"
        mock_response.headers = {}
        mock_get.return_value = mock_response

        from AR0544 import download_file
        path = download_file("http://example.com/file", "/testdir")
        self.assertTrue(path.endswith("downloaded_file.pdf"))
        mock_open_file.assert_called_once()

    @patch('AR0544.requests.get')
    def test_download_file_request_exception(self, mock_get):
        mock_get.side_effect = Exception("Failed")
        from AR0544 import download_file
        result = download_file("http://badurl.com", "/testdir")
        self.assertIsNone(result)


    @patch("pdfplumber.open")
    def test_extract_from_pdf_table_one(self, mock_pdfplumber_open):
        mock_pdf = MagicMock()
        mock_page = MagicMock()

        mock_table_data = [
            ["(1)", "123-45-6", "111-22-3", "Chemical A", "X"],
            ["(2)", "456-78-9", "222-33-4", "Chemical B", ""],
            ["(3)", "alakloor", "333-44-5", "Chemical C", "⁰"],
            ["(4)", "", "444-55-6", "Chemical D", "⁵"],
            ["(5)", "555-66-7", "", "Chemical E", ""],
            ["Bad", "No", "Match", "Row", "Here"]
        ]

        mock_page.extract_tables.return_value = [mock_table_data]
        mock_pdf.pages = [mock_page, mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        from AR0544 import extract_from_pdf_table_one 

        df = extract_from_pdf_table_one("dummy_path.pdf")

        self.assertEqual(len(df), 5)

        self.assertNotIn("alakloor", df["CASi_number1"].str.lower().tolist())


        self.assertIn("123-45-6", df["CASi_number1"].tolist())
        self.assertIn("Chemical A", df["Prioriteetse_aine_nimetus3"].tolist())

    @patch("pdfplumber.open")
    def test_extract_from_pdf_table_two_basic(self, mock_pdf_open):

        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        mock_pdf.pages[2].extract_tables.return_value = [
            [
                ["1", "Substance A", "123-45-6", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7"],
                ["", "Substance B", "ei kohaldata", "0.2", "0.3", "0.4", "0.5", "0.6", "ei kohaldataei kohaldata", ""],
                ["2", "Substance C", "111-22-3", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"],
            ]
        ]

        mock_pdf.pages[3].extract_tables.return_value = []
        mock_pdf.pages[4].extract_tables.return_value = []

        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        df = extract_from_pdf_table_two("dummy.pdf")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("Nr", df.columns)
        self.assertIn("Aine_nimetus15", df.columns)
        self.assertGreaterEqual(len(df), 2)

        self.assertIn("ei kohaldata", df["CASi_number1"].values)

    @patch("pdfplumber.open")
    def test_basic_output(self, mock_pdf_open):
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(7)]

        table_data = [
            ["1", "Metal A", "123-45-6", "0,1"],
            ["Header", "Nimetus", "CAS", "Value"] 
        ]

        mock_pdf.pages[5].extract_tables.return_value = [table_data]
        mock_pdf.pages[6].extract_tables.return_value = []
        for i in range(5):
            mock_pdf.pages[i].extract_tables.return_value = []

        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = extract_from_pdf_table_three("dummy.pdf")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)

if __name__ == '__main__':
    unittest.main()