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


from AR0841 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,getSoup,download_file,clean_cell,extract_excel_data)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}
class Test_AR0841(unittest.TestCase):

    @staticmethod
    def find_json_path():

        folder_path = "out"
        json_files = glob.glob(os.path.join(folder_path, "**", "*.json"), recursive=True)
        if json_files:
            latest_file = max(json_files, key=os.path.getmtime)
            return latest_file
        else:
            print("No JSON files found in the folder or its subfolders.")
            return None

    @classmethod
    def setUpClass(cls):

        main()

        cls.test_json_path = "test.json"
        cls.current_json_path = cls.find_json_path()

        with open(cls.test_json_path, "r", encoding="utf-8") as test_f:
            cls.test_json_data = json.load(test_f)

        with open(cls.current_json_path, "r", encoding="utf-8") as actual_f:
            cls.current_json_data = json.load(actual_f)

    def test_01_json_required_keys(self):
        required_keys = {"UniqueIdentity", "region", "Jurisdiction", "category", "title", "casKey", "dateAndTime", "errors", "data"}
        self.assertTrue(required_keys.issubset(self.current_json_data.keys()))

    def test_02_json_key_data_types(self):
        self.assertIsInstance(self.current_json_data["UniqueIdentity"], str)
        self.assertIsInstance(self.current_json_data["region"], str)
        self.assertIsInstance(self.current_json_data["Jurisdiction"], str)
        self.assertIsInstance(self.current_json_data["category"], str)
        self.assertIsInstance(self.current_json_data["title"], str)
        self.assertIsInstance(self.current_json_data["casKey"], (str, type(None)))
        self.assertIsInstance(self.current_json_data["errors"], list)
        self.assertIsInstance(self.current_json_data["data"], list)

    def test_03_json_column_and_row_consistency(self):
        first_row_keys = set(self.current_json_data["data"][0].keys())
        for row in self.current_json_data["data"]:
            self.assertEqual(set(row.keys()), first_row_keys)

    def test_04_json_colunm_name_and_count(self):
       actual_colunm_count = len(self.current_json_data["data"][0].keys())
       test_colunm_count = len(self.test_json_data["data"][0].keys())
       self.assertEqual(test_colunm_count, actual_colunm_count)
       self.assertEqual(self.test_json_data["data"][0].keys(), self.current_json_data["data"][0].keys())

    def test_05_json_meta_content(self):
        self.assertEqual(self.current_json_data["title"], self.test_json_data["title"])
        self.assertEqual(self.current_json_data["UniqueIdentity"], self.test_json_data["UniqueIdentity"])
        self.assertEqual(self.current_json_data["region"], self.test_json_data["region"])
        self.assertEqual(self.current_json_data["Jurisdiction"], self.test_json_data["Jurisdiction"])
        self.assertEqual(self.current_json_data["category"], self.test_json_data["category"])
        self.assertEqual(self.current_json_data["casKey"], self.test_json_data["casKey"])
        datetime.strptime(self.current_json_data["dateAndTime"], "%Y-%m-%d %H:%M:%S")

    def test_06_json_data_content(self):
        current_all_sha_hashes = [item["sha_hash"] for item in self.current_json_data["data"]]
        sample_size = min(10, len(current_all_sha_hashes))
        sampled_sha_hashes = random.sample(current_all_sha_hashes, sample_size)
        test_sha_hashes = {item["sha_hash"] for item in self.test_json_data["data"]}

        for current_sha_hash in sampled_sha_hashes:
            self.assertIn(current_sha_hash, test_sha_hashes, f"SHA hash {current_sha_hash} not found in test JSON data")

    def test_10_log_error(self):
        errors.clear()
        test_message = "This is a test error"

        log_error(test_message)

        self.assertIn(test_message, errors)
        self.assertEqual(len(errors), 1)

    @patch('common.clean_newlines_in_dataframe')
    @patch('common.save_output_to_json')
    @patch('common.returnJsonPath')
    def test_11_create_final_json_file(self, mock_return_json_path, mock_save_output_to_json,
                                    mock_clean_newlines_in_dataframe):

        test_data = [{"key1": "value1", "key2": "value2"}, {"key1": "value3", "key2": "value4"}]

        mock_return_json_path.return_value = "mock_path.json"

        mock_cleaned_df = pd.DataFrame(test_data)
        mock_clean_newlines_in_dataframe.return_value = mock_cleaned_df

        create_final_json_file(test_data)

        mock_clean_newlines_in_dataframe.assert_called_once()
        actual_data = mock_clean_newlines_in_dataframe.call_args[0][0].to_dict(orient='records')

        self.assertEqual(test_data, actual_data)

        mock_return_json_path.assert_called_once_with(uniqueIdentity)

        expected_json_path = "mock_path.json"
        expected_data = mock_cleaned_df
        mock_save_output_to_json.assert_called_once_with(
            uniqueIdentity,
            region,
            jurisdiction,
            category,
            title,
            errors,
            expected_data,
            expected_json_path,
            casKeyValue
        )

        actual_saved_data = mock_save_output_to_json.call_args[0][6]
        self.assertTrue(
            actual_saved_data.equals(expected_data)
        )

    @patch("AR0841.requests.get")
    def test_get_soup_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><title>Test</title></html>"
        mock_get.return_value = mock_response

        soup = getSoup("http://example.com")
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.title.text, "Test")

    @patch("AR0841.requests.get", side_effect=Exception("Connection error"))
    @patch("AR0841.log_error")
    def test_get_soup_failure(self, mock_log_error, mock_get):
        result = getSoup("http://invalid-url.com")
        self.assertIsNone(result)
        mock_log_error.assert_called_once()

    @patch("AR0841.requests.get")
    @patch("AR0841.open", new_callable=mock_open)
    @patch("AR0841.os.makedirs")
    def test_download_file_success(self, mock_makedirs, mock_open_file, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'test content'
        mock_response.headers = {
            'Content-Disposition': 'attachment; filename="testfile.xlsx"'
        }
        mock_requests_get.return_value = mock_response

        file_path = download_file("http://example.com", "downloads")

        self.assertIn("downloads", file_path)
        self.assertIn("testfile.xlsx", file_path)
        mock_makedirs.assert_called_once_with("downloads", exist_ok=True)
        mock_open_file.assert_called_once_with(file_path, 'wb')
        mock_requests_get.assert_called_once()

    @patch("AR0841.requests.get", side_effect=Exception("Download error"))
    @patch("AR0841.os.makedirs")
    def test_download_file_failure(self, mock_makedirs, mock_requests_get):
        result = download_file("http://example.com", "downloads")
        self.assertIsNone(result)

    def test_integer_float(self):
        self.assertEqual(clean_cell(5.0), 5)

    def test_non_integer_float(self):
        self.assertEqual(clean_cell(5.5), 5.5)

    def test_integer(self):
        self.assertEqual(clean_cell(7), 7)

    def test_string(self):
        self.assertEqual(clean_cell("text"), "text")

    def test_none(self):
        self.assertIsNone(clean_cell(None))

    @patch("AR0841.pd.DataFrame")
    @patch("AR0841.xlrd.open_workbook")
    def test_extract_excel_data_success(self, mock_open_workbook, mock_dataframe):
        mock_sheet = MagicMock()
        mock_sheet.nrows = 10
        mock_sheet.row_values.side_effect = [
            ["", "", "", "", ""], 
            ["", "", "", "", ""],  
            ["", "", "", "", ""],    
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["", "", "", "", ""],
            ["Header1", "Header2", "", "", ""],
            ["Sub1", "Sub2", "", "", ""],      
            [1.0, 2.0, "", "", ""],             
            [3.0, 4.0, "", "", ""],             
        ]
        mock_book = MagicMock()
        mock_book.sheet_by_index.return_value = mock_sheet
        mock_open_workbook.return_value = mock_book

        mock_df_instance = MagicMock()
        mock_dataframe.return_value = mock_df_instance

        result = extract_excel_data("dummy_path.xls")

        mock_open_workbook.assert_called_once_with("dummy_path.xls", ignore_workbook_corruption=True)
        mock_book.sheet_by_index.assert_called_once_with(0)
        mock_sheet.row_values.assert_called()
        mock_dataframe.assert_called_once()
        self.assertEqual(result, mock_df_instance)

    @patch("AR0841.xlrd.open_workbook", side_effect=Exception("read error"))
    def test_extract_excel_data_failure(self, mock_open_workbook):
        result = extract_excel_data("bad_path.xls")
        self.assertTrue(isinstance(result, pd.DataFrame))
        self.assertTrue(result.empty)

if __name__ == '__main__':
    unittest.main()