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
import AR0533
from AR0533 import (
    full_soup_main,
    first_table_data,
    third_table_data,
    fourth_table_data,
    errors,
    log_error
)
from AR0533 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,getSoup,get_all_links)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

class Test_AR0488(unittest.TestCase):

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

    @patch('AR0533.requests.get')
    def test_getSoup_success(self, mock_get):
        
        mock_response = Mock()
        mock_response.content = '<html><body><div>Test</div></body></html>'
        mock_get.return_value = mock_response

        url = 'http://fakeurl.com'
        soup = AR0533.getSoup(url)
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.find('div').text, 'Test')
        mock_get.assert_called_once_with(url, headers=AR0533.headers)

    def test_get_all_links_returns_url(self):
        url = 'http://example.com'
        links = AR0533.get_all_links(url)
        self.assertEqual(links, [url])

    def test_parse_first_table(self):
        
        html = '''
        <div class="gpotbl_div">
            <table class="gpo_table">
                <caption>Organic Peroxide Table</caption>
                <tbody>
                    <tr>
                        <th>Header1</th><th>Header2</th><th>Header3</th><th>Header4</th>
                        <th>Header5</th><th>Header6</th><th>Header7</th><th>Header8</th>
                        <th>Header9</th><th>Header10</th><th>Header11</th>
                    </tr>
                    <tr>
                        <td>TechName1</td><td>ID1</td><td>10%</td><td>5%</td><td>5%</td><td>0%</td><td>80%</td>
                        <td>Packed</td><td>20</td><td>30</td><td>Note1</td>
                    </tr>
                </tbody>
            </table>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        data = AR0533.parse_first_table(soup)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['Technical name'], 'TechName1')
        self.assertEqual(data[0]['ID No.'], 'ID1')
        self.assertEqual(data[0]['Concentration (mass %)'], '10%')

    def test_parse_third_table(self):
      html = '''
      <div class="gpotbl_div"></div>
      <div class="gpotbl_div"></div>
      <div class="gpotbl_div">
          <table class="gpo_table">
              <tbody>
                  <tr>
                      <td>UN1001</td><td>Peroxide A</td><td>IBC Type 1</td><td>50</td><td>10°C</td><td>15°C</td>
                  </tr>
                  <tr>
                      <td></td><td>Compound B</td><td>IBC Type 2</td><td>30</td><td>5°C</td><td>10°C</td>
                  </tr>
              </tbody>
          </table>
      </div>
      '''
      soup = BeautifulSoup(html, 'html.parser')
      data = AR0533.parse_third_table(soup)
      self.assertEqual(len(data), 2)
      self.assertEqual(data[0]['UN No.'], 'UN1001')
      self.assertEqual(data[1]['UN No.'], 'UN1001')  
      self.assertEqual(data[1]['Organic peroxide'], 'Compound B')

    def test_parse_fourth_table(self):
        html = '''
        <div class="gpotbl_div"></div>
        <div class="gpotbl_div"></div>
        <div class="gpotbl_div"></div>
        <div class="gpotbl_div">
            <table class="gpo_table">
                <tbody>
                    <tr>
                        <td>UN2001</td><td>Hazard A</td><td>1.5</td><td>2.0</td><td>Req 1</td><td>Req 2</td><td>Limit 1</td><td>Control Temp 1</td><td>Emergency Temp 1</td>
                    </tr>
                    <tr>
                        <td></td><td>Hazard B</td><td>1.2</td><td>1.8</td><td>Req 3</td><td>Req 4</td><td>Limit 2</td><td>Control Temp 2</td><td>Emergency Temp 2</td>
                    </tr>
                </tbody>
            </table>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        data = AR0533.parse_fourth_table(soup)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['UN No.'], 'UN2001')
        self.assertEqual(data[1]['UN No.'], 'UN2001') 

    @patch('AR0533.parse_first_table')
    @patch('AR0533.parse_third_table')
    @patch('AR0533.parse_fourth_table')
    def test_full_soup_main(self, mock_fourth, mock_third, mock_first):
        
        mock_first.return_value = [{'foo': 'bar'}]
        mock_third.return_value = [{'baz': 'qux'}]
        mock_fourth.return_value = [{'quux': 'corge'}]

        
        AR0533.first_table_data.clear()
        AR0533.third_table_data.clear()
        AR0533.fourth_table_data.clear()

        dummy_soup = BeautifulSoup('<html></html>', 'html.parser')
        AR0533.full_soup_main(dummy_soup)

        
        self.assertIn({'foo': 'bar'}, AR0533.first_table_data)
        self.assertIn({'baz': 'qux'}, AR0533.third_table_data)
        self.assertIn({'quux': 'corge'}, AR0533.fourth_table_data)

if __name__ == '__main__':
    unittest.main()        