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


from AR0260 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,getSoup,extract_lista_e_section,extract_plants_list,extract_addendum_items)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

class Test_AR0260(unittest.TestCase):

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


    @patch('AR0260.requests.get')
    def test_get_soup_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><p>Test</p></body></html>'
        mock_get.return_value = mock_response

        soup = getSoup('http://example.com')
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.p.text, 'Test')

    @patch('AR0260.requests.get')
    @patch('AR0260.log_error')
    def test_get_soup_failure(self, mock_log_error, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException('Error')

        soup = getSoup('http://example.com')
        self.assertIsNone(soup)
        mock_log_error.assert_called_once()

    @patch('AR0260.log_error')
    def test_valid_extraction(self, mock_log_error):
        html = '''
        <html>
            <body>
                <div><b>LISTA - E</b></div>
                <div>Item 1</div>
                <div>Item 2</div>
                <div><b>LISTA - F</b></div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_lista_e_section(soup)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].text.strip(), 'Item 1')
        self.assertEqual(result[1].text.strip(), 'Item 2')

    @patch('AR0260.log_error')
    def test_no_start_marker(self, mock_log_error):
        html = '''
        <html><body><div><b>LISTA - X</b></div></body></html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_lista_e_section(soup)
        self.assertIsNone(result)

    @patch('AR0260.log_error')
    def test_no_end_marker(self, mock_log_error):
        html = '''
        <html><body><div><b>LISTA - E</b></div><div>Item</div></body></html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_lista_e_section(soup)
        self.assertIsNone(result)

    @patch('AR0260.log_error')
    def test_exception_handling(self, mock_log_error):
        result = extract_lista_e_section(None)
        self.assertIsNone(result)
        mock_log_error.assert_called_once()

    @patch('AR0260.extract_lista_e_section')
    def test_extract_valid_plants(self, mock_extract):
        html = '''
        <p>1. Cannabis sativa</p>
        <p>2. Papaver somniferum</p>
        <p>ADENDO: extra info</p>
        <p>3. Should not appear</p>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        mock_extract.return_value = soup.find_all('p')

        result = extract_plants_list(soup)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['Number'], '1')
        self.assertEqual(result[0]['Name_of_the_plant'], 'Cannabis sativa')
        self.assertEqual(result[1]['Number'], '2')
        self.assertEqual(result[1]['Name_of_the_plant'], 'Papaver somniferum')

    @patch('AR0260.extract_lista_e_section')
    def test_no_match_format(self, mock_extract):
        html = '''
        <p>Invalid line without number</p>
        <p>Another invalid entry</p>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        mock_extract.return_value = soup.find_all('p')

        result = extract_plants_list(soup)
        self.assertEqual(result, [])

    @patch('AR0260.extract_lista_e_section')
    def test_non_paragraph_elements(self, mock_extract):
        html = '''
        <div>1. Not a paragraph</div>
        <span>2. Still not a paragraph</span>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        mock_extract.return_value = soup.find_all(['div', 'span'])

        result = extract_plants_list(soup)
        self.assertEqual(result, [])

    @patch('AR0260.extract_lista_e_section', return_value=None)
    def test_none_section(self, mock_extract):
        soup = BeautifulSoup('<html></html>', 'html.parser')
        result = extract_plants_list(soup)
        self.assertEqual(result, [])

    @patch('AR0260.log_error')
    def test_exception_handling(self, mock_log_error):
        result = extract_plants_list(None)
        self.assertEqual(result, [])
        mock_log_error.assert_called_once()


    @patch('AR0260.extract_lista_e_section')
    def test_extract_addendum_items(self, mock_extract):
        html = '''
        <p>ADENDO:</p>
        <p>1) Item with plain text</p>
        <p>2) Item with <a href="#">link</a>inside</p>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        mock_extract.return_value = soup.find_all('p')

        result = extract_addendum_items(soup)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['Number'], '1')
        self.assertEqual(result[0]['Description'], '1) Item with plain text')
        self.assertEqual(result[1]['Number'], '2')
        self.assertEqual(result[1]['Description'], '2) Item with linkinside')

    @patch('AR0260.extract_lista_e_section')
    def test_no_addendo_found(self, mock_extract):
        html = '''
        <p>1) Item with no addendo header</p>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        mock_extract.return_value = soup.find_all('p')

        result = extract_addendum_items(soup)
        self.assertEqual(result, [])

    @patch('AR0260.extract_lista_e_section')
    def test_invalid_format(self, mock_extract):
        html = '''
        <p>ADENDO:</p>
        <p>Missing number and paren</p>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        mock_extract.return_value = soup.find_all('p')

        result = extract_addendum_items(soup)
        self.assertEqual(result, [])

    @patch('AR0260.extract_lista_e_section', return_value=None)
    def test_none_section(self, mock_extract):
        soup = BeautifulSoup('<html></html>', 'html.parser')
        result = extract_addendum_items(soup)
        self.assertEqual(result, [])

    @patch('AR0260.log_error')
    def test_exception_handling(self, mock_log_error):
        result = extract_addendum_items(None)
        self.assertEqual(result, [])
        mock_log_error.assert_called_once()


if __name__ == '__main__':
    unittest.main()