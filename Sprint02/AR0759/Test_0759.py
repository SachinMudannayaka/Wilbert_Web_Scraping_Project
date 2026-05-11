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


from AR0759 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,getSoup,extract_chemical_data)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

class Test_AR0759(unittest.TestCase):

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

    @patch('AR0759.requests.get')
    def test_get_soup_success(self, mock_get):
        html = '<html><body><h1>Test</h1></body></html>'
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = getSoup("http://example.com")
        self.assertIsInstance(result, BeautifulSoup)
        self.assertEqual(result.h1.text, "Test")

    @patch('AR0759.requests.get')
    @patch('AR0759.log_error')
    def test_get_soup_failure(self, mock_log_error, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = getSoup("http://badurl.com")
        self.assertIsNone(result)
        mock_log_error.assert_called_once()


    def test_single_chemical_with_valid_paragraph(self):
        html = """
        <div class="section">
            <h4 class="in-front">73.2329 Guanine.</h4>
            <p class="indent-1">
                <span class="paragraph-hierarchy">(a)</span>
                <em class="paragraph-heading">Identity and specifications.</em>
                (a) Identity and specifications. (a) Identity and specifications.
                <a href="/current/title-21/section-73.1329">Link</a>
            </p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_chemical_data(soup)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['chemical_name'], "73.2329 Guanine.")
        self.assertEqual(result[0]['description'][0]['section'], "a")
        self.assertEqual(result[0]['description'][0]['title'], "Identity and specifications")
        self.assertIn("Identity and specifications", result[0]['description'][0]['text'])
        self.assertEqual(result[0]['description'][0]['hyperlinks'], ["https://www.ecfr.gov/current/title-21/section-73.1329"])

    def test_paragraph_with_citation_is_skipped(self):
        html = """
        <div class="section">
            <h4>Some Chemical</h4>
            <p class="indent-1 citation">This is a citation and should be skipped.</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_chemical_data(soup)
        self.assertEqual(len(result), 0)

    def test_missing_h4_results_in_no_chemical_name(self):
        html = """
        <div class="section">
            <p class="indent-1">
                <span class="paragraph-hierarchy">(b)</span>
                <em class="paragraph-heading">Usage.</em>
                This describes usage.
            </p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_chemical_data(soup)
        self.assertEqual(len(result), 0) 

    def test_no_paragraphs_results_in_no_description(self):
        html = """
        <div class="section">
            <h4>Some Chemical</h4>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_chemical_data(soup)
        self.assertEqual(len(result), 0)

    def test_hyperlink_relative_to_federalregister(self):
        html = """
        <div class="section">
            <h4>Color Additive</h4>
            <p class="indent-1">
                <span class="paragraph-hierarchy">(c)</span>
                <em class="paragraph-heading">References.</em>
                (c) References are provided.
                <a href="/some/path">Reference Link</a>
            </p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_chemical_data(soup)
        self.assertEqual(result[0]['description'][0]['hyperlinks'][0], "https://www.federalregister.gov/some/path")

if __name__ == '__main__':
    unittest.main()