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


from AR0450 import (main,log_error, create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,getSoup,download_pdf,extract_prohibited_ingredients)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

class Test_AR0450(unittest.TestCase):

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
            UniqueIdentity=uniqueIdentity,
            region=region,
            jurisdiction=jurisdiction,
            category=category,
            title=title,
            errors=errors,
            data=expected_data,
            jsonPath=expected_json_path,
            casKeyValue=casKeyValue
        )

        actual_saved_data = mock_save_output_to_json.call_args.kwargs['data']
        self.assertTrue(
            actual_saved_data.equals(expected_data)
        )


    def setUp(self):
        from AR0450 import errors
        errors.clear()

    @patch('AR0450.requests.get')
    def test_get_soup_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html><body><h1>Test</h1></body></html>'
        mock_get.return_value = mock_response

        soup = getSoup('https://example.com')
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.find('h1').text, 'Test')

    @patch('AR0450.requests.get')
    def test_get_soup_failure(self, mock_get):
        from AR0450 import errors
        mock_get.side_effect = requests.exceptions.Timeout("Timeout error")

        soup = getSoup('https://example.com/fail')
        self.assertIsNone(soup)
        self.assertTrue(any("Timeout error" in e for e in errors))

    @patch('AR0450.requests.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_pdf_success(self, mock_file, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'PDF content bytes'
        mock_requests_get.return_value = mock_response

        result = download_pdf('http://example.com/file.pdf', 'save_path.pdf')
        self.assertTrue(result)
        mock_requests_get.assert_called_once()
        mock_file.assert_called_once_with('save_path.pdf', 'wb')
        mock_file().write.assert_called_once_with(b'PDF content bytes')

    @patch('AR0450.requests.get')
    def test_download_pdf_failure(self, mock_requests_get):
        from AR0450 import errors
        errors.clear()

        mock_requests_get.side_effect = Exception("Download error")

        result = download_pdf('http://example.com/file.pdf', 'save_path.pdf')
        self.assertFalse(result)
        self.assertTrue(any("Download error" in e for e in errors))

    @patch('AR0450.pdfplumber.open')
    def test_extract_prohibited_ingredients_basic(self, mock_pdf_open):
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.page_number = 11
        mock_page1.extract_text.return_value = (
            "化妆品禁用原料目录 表\n"
            "注（1）：Some description 1\n"
            "1. Note one\n"
            "2、Note two\n"
            "3) Note three\n"
        )
        mock_page1.extract_tables.return_value = [
            [
                ["序号", "中文名称", "英文名称"],
                ["1", "名称一", "English Name One CAS No. 123-45-6"],
                ["2", "名称二", "English Name Two CAS No. 789-01-2"],
                ["", "", ""]
            ]
        ]

        mock_pdf.pages = [mock_page1]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = extract_prohibited_ingredients("dummy_path.pdf")

        self.assertTrue(any(r.get("序号") == "1" for r in result))
        self.assertTrue(any(r.get("CAS_No") == "123-45-6" for r in result))
        self.assertTrue(any("注释 (Notes)" in r for r in result))
        self.assertTrue(any("描述 (Description)" in r for r in result))

if __name__ == '__main__':
    unittest.main()