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
from urllib.parse import urljoin
import AR0305

from AR0305 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}
class Test_AR0305(unittest.TestCase):

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

    @patch('AR0305.requests.get')
    def test_getSoup_success(self, mock_get):
        html_content = "<html><body><h1>Hello</h1></body></html>"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        soup = AR0305.getSoup("http://example.com")
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.h1.text, "Hello")

    @patch('AR0305.requests.get')
    @patch('AR0305.log_error')
    def test_getSoup_failure(self, mock_log_error, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 error")
        mock_get.return_value = mock_response

        soup = AR0305.getSoup("http://bad-url.com")
        self.assertIsNone(soup)
        mock_log_error.assert_called_once()

    def setUp(self):
        self.base_url = "http://example.com"

    @patch('AR0305.log_error')
    def test_get_municipal_code_link_success(self, mock_log_error):
        html_content = '''
            <html>
                <body>
                    <a href="/codes/municipal">Municipal Code</a>
                </body>
            </html>'''
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = AR0305.get_municipal_code_link(soup, self.base_url)
        expected_url = urljoin(self.base_url, "/codes/municipal")
        self.assertEqual(result, expected_url)
        mock_log_error.assert_not_called()

    @patch('AR0305.log_error')
    def test_get_municipal_code_link_no_href(self, mock_log_error):
        html_content = '''
            <html>
                <body>
                    <a>Municipal Code</a>
                </body>
            </html>'''
        soup = BeautifulSoup(html_content, 'html.parser')

        with self.assertRaises(RuntimeError) as context:
            AR0305.get_municipal_code_link(soup, self.base_url)
        
        self.assertIn("Error extracting Municipal Code link", str(context.exception))
        mock_log_error.assert_called_once()

    @patch('AR0305.log_error')
    def test_get_municipal_code_link_no_link(self, mock_log_error):
        html_content = '<html><body><p>No relevant link here</p></body></html>'
        soup = BeautifulSoup(html_content, 'html.parser')

        with self.assertRaises(RuntimeError) as context:
            AR0305.get_municipal_code_link(soup, self.base_url)
        
        self.assertIn("Error extracting Municipal Code link", str(context.exception))
        mock_log_error.assert_called_once()

    @patch('AR0305.log_error')
    def test_find_exact_pdf_link_success(self, mock_log_error):
        html_content = '''
        <table>
            <tr>
                <td><a href="/files/chapter423.pdf">Chapter 423</a></td>
                <td>Other info</td>
            </tr>
        </table>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        result = AR0305.find_exact_pdf_link(soup, chapter_text="Chapter 423")
        self.assertEqual(result, "/files/chapter423.pdf")
        mock_log_error.assert_not_called()

    @patch('AR0305.log_error')
    def test_find_exact_pdf_link_no_a_tag(self, mock_log_error):
        html_content = '''
        <table>
            <tr>
                <td><a href="/files/chapter424.pdf">Chapter 424</a></td>
            </tr>
        </table>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')

        with self.assertRaises(RuntimeError) as cm:
            AR0305.find_exact_pdf_link(soup, chapter_text="Chapter 423")

        self.assertIn("Could not find chapter link with text", str(cm.exception))
        mock_log_error.assert_called_once()

    @patch('AR0305.log_error')
    def test_find_exact_pdf_link_no_tr_tag(self, mock_log_error):
        html_content = '''
        <div>
            <a href="/files/chapter423.pdf">Chapter 423</a>
        </div>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')

        with self.assertRaises(RuntimeError) as cm:
            AR0305.find_exact_pdf_link(soup, chapter_text="Chapter 423")

        self.assertIn("Could not locate parent <tr>", str(cm.exception))
        mock_log_error.assert_called_once()

    @patch('AR0305.requests.get')
    @patch('AR0305.pdfplumber.open')
    def test_extract_table_from_pdf_url_success(self, mock_pdf_open, mock_requests_get):
        mock_response = MagicMock()
        mock_response.content = b'%PDF-1.4 fake pdf content'
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(8)]
        mock_page.extract_table.return_value = [
            ["Header1", "Header2", "Header3", "Header4"],
            ["Subheader1", "Subheader2", "Subheader3", "Subheader4"],
            ["ChemicalA", "123-45-6", "10", "5"],
            ["GROUP something", "000-00-0", "-", "-"],
            ["ChemicalB", "-", "20", "10"],
        ]
        mock_pdf.pages[7] = mock_page
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = AR0305.extract_table_from_pdf("https://fakeurl.com/fake.pdf")

        expected = [
            {
                "Chemical Name": "ChemicalA",
                "CAS No.b": "123-45-6",
                "Mass Reporting Threshold": "10",
                "Concentration Threshold": "5",
            },
            {
                "Chemical Name": "ChemicalB",
                "CAS No.b": "",
                "Mass Reporting Threshold": "20",
                "Concentration Threshold": "10",
            },
        ]

        self.assertEqual(result, expected)
        mock_requests_get.assert_called_once_with("https://fakeurl.com/fake.pdf")
        mock_response.raise_for_status.assert_called_once()

    @patch('AR0305.os.path.isfile')
    @patch('AR0305.pdfplumber.open')
    def test_extract_table_from_pdf_local_file_success(self, mock_pdf_open, mock_isfile):
        mock_isfile.return_value = True

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(8)]
        mock_page.extract_table.return_value = [
            ["H1", "H2", "H3", "H4"],
            ["SH1", "SH2", "SH3", "SH4"],
            ["ChemX", "111-11-1", "15", "7"],
        ]
        mock_pdf.pages[7] = mock_page
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = AR0305.extract_table_from_pdf("fake_local_path.pdf")

        expected = [{
            "Chemical Name": "ChemX",
            "CAS No.b": "111-11-1",
            "Mass Reporting Threshold": "15",
            "Concentration Threshold": "7",
        }]

        self.assertEqual(result, expected)
        mock_isfile.assert_called_once_with("fake_local_path.pdf")

    def test_extract_table_from_pdf_invalid_path(self):
        with self.assertRaises(ValueError):
            AR0305.extract_table_from_pdf("not_a_url_or_file")

    @patch('AR0305.os.path.isfile')
    @patch('AR0305.pdfplumber.open')
    def test_extract_table_from_pdf_less_than_8_pages(self, mock_pdf_open, mock_isfile):
        mock_isfile.return_value = True

        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(5)]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = AR0305.extract_table_from_pdf("fake_local_path.pdf")
        self.assertEqual(result, [])

    @patch('AR0305.os.path.isfile')
    @patch('AR0305.pdfplumber.open')
    def test_extract_table_from_pdf_no_table_on_page8(self, mock_pdf_open, mock_isfile):
        mock_isfile.return_value = True

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(8)]
        mock_page.extract_table.return_value = None
        mock_pdf.pages[7] = mock_page
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        result = AR0305.extract_table_from_pdf("fake_local_path.pdf")
        self.assertEqual(result, [])        

if __name__ == '__main__':
    unittest.main()        