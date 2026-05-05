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
import AR0989


from AR0989 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}
class Test_AR0989(unittest.TestCase):

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

    def setUp(self):
        self.sample_html = """
        <table id="tb1">
            <tr><th>Header1</th><th>Header2</th></tr>
            <tr>
                <td><a href="link1">Order1</a></td>
                <td>Substance1</td>
            </tr>
            <tr>
                <td>Order2</td>
                <td>Substance2</td>
            </tr>
        </table>
        """
        self.soup = BeautifulSoup(self.sample_html, 'html.parser')
        self.base_url = 'http://base.com/path/'
        self.chem_list = [
            {'order_no': '1', 'substance_name': 'Test1', 'href': 'http://test1.com'},
            {'order_no': '2', 'substance_name': 'Test2', 'href': 'http://test2.com'}
        ]

    @patch('AR0989.requests.get')
    def test_get_soup_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response
        
        result = AR0989.getSoup('http://test.com')
        
        self.assertIsInstance(result, BeautifulSoup)
        self.assertEqual(result.text, 'Test')

    @patch('AR0989.getSoup')
    def test_main_soup_extraction_valid(self, mock_get_soup):
        mock_get_soup.return_value = BeautifulSoup('<html></html>', 'html.parser')
        result = AR0989.main_soup_exctraction('http://valid.com')
        self.assertIsInstance(result, BeautifulSoup)

    @patch('AR0989.getSoup')
    def test_iterate_all_chems_comprehensive(self, mock_get_soup):
        """Test chemical data extraction with multiple scenarios"""

        mock_html = """
        <table id="tb1">
            <!-- Should be skipped (label row) -->
            <tr><td class="label">Header</td><td></td><td></td><td></td></tr>
            
            <!-- Valid data row (4 cells) -->
            <tr>
                <td>1</td>
                <td>111-11-1</td>
                <td>MITI-001</td>
                <td>Chemical A</td>
            </tr>
            
            <!-- Should be processed (exactly 4 cells) -->
            <tr>
                <td>2</td>
                <td>222-22-2</td>
                <td>MITI-002</td>
                <td>Chemical B</td>
            </tr>
            
            <!-- Should be skipped (only 3 cells) -->
            <tr>
                <td>3</td>
                <td>333-33-3</td>
                <td>MITI-003</td>
            </tr>
            
            <!-- Should be skipped (label row) -->
            <tr><td class="label">Footer</td><td></td><td></td><td></td></tr>
        </table>
        """
        mock_get_soup.return_value = BeautifulSoup(mock_html, 'html.parser')


        chem_list = [
            {
                'order_no': 'ORDER-123',
                'substance_name': 'MAIN SUBSTANCE',
                'href': 'http://example.com/chem1'
            },
            {
                'order_no': 'ORDER-456',
                'substance_name': 'SECONDARY SUBSTANCE', 
                'href': 'http://example.com/chem2'
            }
        ]

        results = AR0989.iterate_all_chems(chem_list)

        self.assertEqual(len(results), 4)
        
        self.assertEqual(results[0]['no'], 'ORDER-123')
        self.assertEqual(results[0]['class_Ⅱ_specified_chemical_substance_name'], 'MAIN SUBSTANCE')
        self.assertEqual(results[0]['cas_rn'], '111-11-1')
        self.assertEqual(results[0]['miti_number'], 'MITI-001')
          
        self.assertEqual(results[3]['no'], 'ORDER-456')
        self.assertEqual(results[3]['class_Ⅱ_specified_chemical_substance_name'], 'SECONDARY SUBSTANCE')
        self.assertEqual(results[3]['cas_rn'], '222-22-2')
        self.assertEqual(results[3]['miti_number'], 'MITI-002')


        self.assertTrue(all(len(chem) == 4 for chem in results))
        self.assertTrue(all(chem['cas_rn'] in ('111-11-1', '222-22-2') for chem in results))



    @patch('AR0989.getSoup')
    def test_valid_chemical_processing_single_result(self, mock_get_soup):
        detail_html = """
        <table id="tb1">
            <tr><td>1</td><td>123-45-6</td><td>MITI-001</td><td>Chemical Name</td></tr>
        </table>
        """
        mock_get_soup.return_value = BeautifulSoup(detail_html, 'html.parser')
        
        result = AR0989.iterate_all_chems(self.chem_list)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0]['cas_rn'], '123-45-6')
        self.assertEqual(result[0]['no'], '1')
        self.assertEqual(result[1]['cas_rn'], '123-45-6')
        self.assertEqual(result[1]['no'], '2')

    @patch('AR0989.getSoup')
    def test_valid_chemical_processing_different_results(self, mock_get_soup):

        def side_effect(url):
            order_no = '1' if 'test1.com' in url else '2'
            cas = '123-45-6' if order_no == '1' else '456-78-9'
            html = f"""
            <table id="tb1">
                <tr><td>{order_no}</td><td>{cas}</td><td>MITI-00{order_no}</td><td>Chemical {order_no}</td></tr>
            </table>
            """
            return BeautifulSoup(html, 'html.parser')
        
        mock_get_soup.side_effect = side_effect
        
        result = AR0989.iterate_all_chems(self.chem_list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['cas_rn'], '123-45-6')
        self.assertEqual(result[0]['no'], '1')
        self.assertEqual(result[1]['cas_rn'], '456-78-9')
        self.assertEqual(result[1]['no'], '2')      

if __name__ == '__main__':
    unittest.main()        