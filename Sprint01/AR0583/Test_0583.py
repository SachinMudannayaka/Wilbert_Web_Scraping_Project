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
import AR0583


from AR0583 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}
class Test_AR0583(unittest.TestCase):

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


    @patch('AR0583.session.get')
    def test_get_json_success(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"key": "value"}
        mock_get.return_value = mock_resp

        url = "https://fakeurl.com/data"
        result = AR0583.get_json(url)
        self.assertEqual(result, {"key": "value"})
        mock_get.assert_called_once_with(url, headers=None)

    @patch('AR0583.session.get')
    def test_get_json_http_error(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        url = "https://fakeurl.com/data"
        with self.assertRaises(Exception) as context:
            AR0583.get_json(url)
        self.assertIn("Failed to retrieve JSON", str(context.exception))

    @patch('AR0583.session.get')
    def test_get_json_invalid_json(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        url = "https://fakeurl.com/data"
        with self.assertRaises(Exception) as context:
            AR0583.get_json(url)
        self.assertIn("Failed to parse response as JSON", str(context.exception))

    def test_get_all_links_returns_list(self):
        url = "https://example.com"
        result = AR0583.get_all_links(url)
        self.assertIsInstance(result, list)
        self.assertIn(url, result)

    def test_extract_chlorophenols_table_from_json_body_success(self):
        sample_html = """
        <table>
            <tr><td colspan="2">MONOCHLOROPHENOLS</td></tr>
            <tr><td>2-chlorophenol<sup>1</sup></td><td>95-57-8</td></tr>
            <tr><td>3-chlorophenol</td><td>108-43-0</td></tr>
        </table>
        """
        json_data = {"body": sample_html}
        results = AR0583.extract_chlorophenols_table_from_json_body(json_data)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['Name'], "2-chlorophenol¹")
        self.assertEqual(results[0]['CASRN'], "95-57-8")
        self.assertEqual(results[0]['Category'], "MONOCHLOROPHENOLS")

    def test_extract_chlorophenols_table_missing_body(self):
        with self.assertRaises(ValueError) as context:
            AR0583.extract_chlorophenols_table_from_json_body({})
        self.assertIn("Missing 'body'", str(context.exception))

    def test_extract_chlorophenols_table_no_table(self):
        json_data = {"body": "<div>No table here</div>"}
        with self.assertRaises(ValueError) as context:
            AR0583.extract_chlorophenols_table_from_json_body(json_data)
        self.assertIn("No <table> found", str(context.exception))

    def test_extract_chlorophenols_table_empty_rows(self):
        json_data = {"body": "<table></table>"}
        with self.assertRaises(ValueError) as context:
            AR0583.extract_chlorophenols_table_from_json_body(json_data)
        self.assertIn("No rows (<tr>) found", str(context.exception))    

 
if __name__ == '__main__':
    unittest.main()        