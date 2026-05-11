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


from AR0572 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,download_file,extract_suspected_carcinogens)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

class Test_AR0572(unittest.TestCase):

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

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("requests.get")
    def test_download_with_provided_filename(self, mock_get, mock_makedirs, mock_file):
        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_response.headers = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_file("http://example.com/file.xlsx", "/tmp", "myfile.xlsx")
        self.assertEqual(result, os.path.join("/tmp", "myfile.xlsx"))
        mock_file().write.assert_called_once_with(b"file content")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("requests.get")
    def test_download_with_filename_from_content_disposition(self, mock_get, mock_makedirs, mock_file):
        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_response.headers = {"Content-Disposition": 'attachment; filename="report.xlsx"'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_file("http://example.com/download", "/tmp", None)
        self.assertEqual(result, os.path.join("/tmp", "report.xlsx"))
        mock_file().write.assert_called_once_with(b"file content")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("requests.get")
    def test_download_with_default_filename(self, mock_get, mock_makedirs, mock_file):
        mock_response = MagicMock()
        mock_response.content = b"file content"
        mock_response.headers = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_file("http://example.com/file", "/tmp", None)
        self.assertEqual(result, os.path.join("/tmp", "downloaded_file.xlsx"))
        mock_file().write.assert_called_once_with(b"file content")

    @patch("requests.get")
    def test_download_request_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
        result = download_file("http://example.com/file", "/tmp", "file.xlsx")
        self.assertIsNone(result)

    @patch("requests.get")
    def test_download_unexpected_exception(self, mock_get):
        mock_get.side_effect = Exception("Unexpected crash")
        result = download_file("http://example.com/file", "/tmp", "file.xlsx")
        self.assertIsNone(result)

    @patch("AR0572.pdfplumber.open")
    def test_extract_valid_substances(self, mock_pdf_open):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "SOME HEADER\n"
            "INDUSTRIAL MATERIALS OR OPERATIONS SUSPECTED\n"
            "--------------------------------------------\n"
            "1. Benzene\n"
            "2. Vinyl chloride\n"
            "3. Formaldehyde\n"
            "4. Asbestos\n"
            "5. Arsenic\n"
            "6. Chromium VI\n"
            "7. Cadmium\n"
            "8. Nickel compounds\n"
            "9. Ethylene oxide\n"
            "10. Diesel exhaust\n"
            "11. Silica (crystalline)"
        )
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = extract_suspected_carcinogens("dummy.pdf")
        self.assertEqual(len(result), 11)
        self.assertEqual(result[0], {"substance_name": "1. Benzene"})
        self.assertEqual(result[-1], {"substance_name": "11. Silica (crystalline)"})

    @patch("AR0572.pdfplumber.open")
    def test_no_matching_text_found(self, mock_pdf_open):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Some unrelated content"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = extract_suspected_carcinogens("dummy.pdf")
        self.assertEqual(result, [])

    @patch("AR0572.pdfplumber.open")
    def test_page_with_no_text(self, mock_pdf_open):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = extract_suspected_carcinogens("dummy.pdf")
        self.assertEqual(result, [])

    @patch("AR0572.pdfplumber.open", side_effect=Exception("File corrupted"))
    def test_pdf_processing_exception(self, mock_pdf_open):
        result = extract_suspected_carcinogens("corrupt.pdf")
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()