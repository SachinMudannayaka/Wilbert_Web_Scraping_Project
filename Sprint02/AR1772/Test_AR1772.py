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
import AR1772

from AR1772 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,download_file,read_epa_excel_data)

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

class Test_AR1772(unittest.TestCase):

    @staticmethod
    def find_latest_folder():
        main(True)
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
        latest_folder = Test_AR1772.find_latest_folder()
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



    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("requests.get")
    def test_successful_download_with_filename(self, mock_get, mock_makedirs, mock_file):
        mock_response = MagicMock()
        mock_response.content = b"test content"
        mock_response.headers = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        file_path = download_file("http://example.com/file.xlsx", "/tmp", "test.xlsx")
        self.assertEqual(file_path, os.path.join("/tmp", "test.xlsx"))
        mock_file().write.assert_called_once_with(b"test content")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("requests.get")
    def test_successful_download_with_content_disposition(self, mock_get, mock_makedirs, mock_file):
        mock_response = MagicMock()
        mock_response.content = b"test content"
        mock_response.headers = {
            "Content-Disposition": 'attachment; filename="downloaded.xlsx"'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        file_path = download_file("http://example.com/download", "/tmp", None)
        self.assertEqual(file_path, os.path.join("/tmp", "downloaded.xlsx"))
        mock_file().write.assert_called_once_with(b"test content")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("requests.get")
    def test_successful_download_without_filename_and_content_disposition(self, mock_get, mock_makedirs, mock_file):
        mock_response = MagicMock()
        mock_response.content = b"test content"
        mock_response.headers = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        file_path = download_file("http://example.com/fallback.xlsx", "/tmp", None)
        self.assertEqual(file_path, os.path.join("/tmp", "downloaded_file.xlsx"))
        mock_file().write.assert_called_once_with(b"test content")

    @patch("requests.get")
    def test_request_exception(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        result = download_file("http://example.com/fail.xlsx", "/tmp", "fail.xlsx")
        self.assertIsNone(result)


    @patch("AR1772.pd.read_excel")
    def test_successful_read(self, mock_read_excel):
        data = pd.DataFrame([
            {"Col1": "A", "Col2": 1},
            {"Col1": "B", "Col2": 2}
        ])
        mock_read_excel.return_value = data

        result = read_epa_excel_data("path/to/file.xlsx", "TestFile.xlsx")
        expected = [
            {"Col1": "A", "Col2": 1, "File Name": "TestFile.xlsx"},
            {"Col1": "B", "Col2": 2, "File Name": "TestFile.xlsx"}
        ]
        self.assertEqual(result, expected)

    @patch("AR1772.log_error")
    @patch("AR1772.pd.read_excel", side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_read_excel, mock_log_error):
        result = read_epa_excel_data("missing.xlsx", "MissingFile.xlsx")
        self.assertEqual(result, [])
        mock_log_error.assert_called_once_with("File not found: missing.xlsx")

    @patch("AR1772.log_error")
    @patch("AR1772.pd.read_excel")
    def test_empty_excel_file(self, mock_read_excel, mock_log_error):
        empty_df = pd.DataFrame()
        mock_read_excel.return_value = empty_df

        result = read_epa_excel_data("empty.xlsx", "EmptyFile.xlsx")
        self.assertEqual(result, [])
        mock_log_error.assert_called_once_with("Data error: EmptyFile.xlsx Excel file is empty.")

    @patch("AR1772.log_error")
    @patch("AR1772.pd.read_excel", side_effect=Exception("Unexpected"))
    def test_unexpected_exception(self, mock_read_excel, mock_log_error):
        result = read_epa_excel_data("crash.xlsx", "CrashFile.xlsx")
        self.assertEqual(result, [])
        mock_log_error.assert_called_once_with("Unexpected error: Unexpected")


if __name__ == '__main__':
    unittest.main()