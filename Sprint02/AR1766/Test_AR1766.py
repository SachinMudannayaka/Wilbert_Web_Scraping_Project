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


from AR1766 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,getSoup,extract_ecfr_structure)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

class Test_AR1766(unittest.TestCase):

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

    @patch('AR1766.requests.get')
    def test_get_soup_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><p>Test</p></body></html>'
        mock_get.return_value = mock_response

        soup = getSoup('http://example.com')
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.p.text, 'Test')

    @patch('AR1766.requests.get')
    @patch('AR1766.log_error')
    def test_get_soup_failure(self, mock_log_error, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException('Error')

        result = getSoup('http://example.com')
        self.assertIsNone(result)
        mock_log_error.assert_called_once()


    def test_extract_complete_structure(self):
        html = '''
        <div class="subpart">
            <h2>Subpart A</h2>
            <div class="section">
                <h4>§ 250.10 Section Title</h4>
                <p>(a) Paragraph one text.</p>
                <p>(b)(1) Paragraph two text.</p>
                <p>Not labeled paragraph.</p>
            </div>
            <div class="section">
                <h4>§ 250.20 Another Section</h4>
                <p>(a) Another paragraph.</p>
            </div>
        </div>
        <div class="subpart">
            <h2>Subpart B</h2>
            <div class="section">
                <h4>§ 250.30 Section Title B</h4>
                <p>(a) Text B1.</p>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_ecfr_structure(soup)
    
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['sub_part'], 'Subpart A')
        self.assertEqual(len(result[0]['sections']), 2)
        self.assertEqual(result[0]['sections'][0]['section_with_title'], '§ 250.10 Section Title')
        self.assertEqual(result[0]['sections'][0]['description'][0]['label'], '(a)')
        self.assertEqual(result[0]['sections'][0]['description'][0]['text'], 'Paragraph one text.')
        self.assertEqual(result[0]['sections'][0]['description'][1]['label'], '(b)')
        self.assertEqual(result[0]['sections'][0]['description'][1]['text'], '(1) Paragraph two text.')
        self.assertEqual(result[0]['sections'][1]['section_with_title'], '§ 250.20 Another Section')
        self.assertEqual(result[1]['sub_part'], 'Subpart B')
        self.assertEqual(len(result[1]['sections']), 1)
        self.assertEqual(result[1]['sections'][0]['section_with_title'], '§ 250.30 Section Title B')
        self.assertEqual(result[1]['sections'][0]['description'][0]['label'], '(a)')
        self.assertEqual(result[1]['sections'][0]['description'][0]['text'], 'Text B1.')

    def test_empty_html(self):
        soup = BeautifulSoup('', 'html.parser')
        result = extract_ecfr_structure(soup)
        self.assertEqual(result, [])

    def test_missing_titles(self):
        html = '''
        <div class="subpart">
            <div class="section">
                <p>(a) Text without titles.</p>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_ecfr_structure(soup)
        self.assertEqual(result[0]['sub_part'], 'Untitled Subpart')
        self.assertEqual(result[0]['sections'][0]['section_with_title'], 'Untitled Section')
        self.assertEqual(result[0]['sections'][0]['description'][0]['label'], '(a)')
        self.assertEqual(result[0]['sections'][0]['description'][0]['text'], 'Text without titles.')

    def test_paragraphs_without_labels(self):
        html = '''
        <div class="subpart">
            <h2>Subpart X</h2>
            <div class="section">
                <h4>Section X</h4>
                <p>No label here.</p>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_ecfr_structure(soup)
        self.assertEqual(result[0]['sub_part'], 'Subpart X')
        self.assertEqual(result[0]['sections'][0]['section_with_title'], 'Section X')
        self.assertEqual(result[0]['sections'][0]['description'], [])
        
if __name__ == '__main__':
    unittest.main()