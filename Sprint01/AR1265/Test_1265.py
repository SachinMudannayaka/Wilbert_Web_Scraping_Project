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
import AR1265 as ar1265
import pdfplumber


from AR1265 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,get_pdf_url_from_site,get_all_extracted_data_pdf)
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",    
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",    
    "Cache-Control": "no-cache",    
    "Pragma": "no-cache",    
    "Priority": "u=0, i",    
    "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',    
    "Sec-Ch-Ua-Arch": '"x86"',    
    "Sec-Ch-Ua-Bitness": '"64"',    
    "Sec-Ch-Ua-Full-Version": '"134.0.6998.89"',    
    "Sec-Ch-Ua-Full-Version-List": '"Chromium";v="134.0.6998.89", "Not:A-Brand";v="24.0.0.0", "Google Chrome";v="134.0.6998.89"',    
    "Sec-Ch-Ua-Mobile": "?0",    
    "Sec-Ch-Ua-Model": '""',    
    "Sec-Ch-Ua-Platform": '"Windows"',    
    "Sec-Ch-Ua-Platform-Version": '"15.0.0"',    
    "Sec-Fetch-Dest": "document",    
    "Sec-Fetch-Mode": "navigate",    
    "Sec-Fetch-Site": "none",    
    "Sec-Fetch-User": "?1",    
    "Upgrade-Insecure-Requests": "1",    
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}
HTML_CONTENT = "<html><body><h1>Test Page</h1></body></html>"
class Test_AR1265(unittest.TestCase):

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

    
    @patch("AR1265.log_error")
    @patch("AR1265.get_fresh_cookies")  
    @patch("AR1265.session.get") 
    @patch("AR1265.headers", {}) 
    def test_get_soup_success(self, mock_get, mock_cookies, mock_log):
        mock_cookies.return_value = {'cookie': 'value'}
        
        mock_response = Mock()
        mock_response.text = HTML_CONTENT
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        from AR1265 import getSoup 
        result = getSoup("http://example.com")

        self.assertIsInstance(result, BeautifulSoup)
        self.assertIn("Test Page", result.text)

    @patch("AR1265.log_error")
    @patch("AR1265.get_fresh_cookies")
    def test_get_soup_no_cookies(self, mock_cookies, mock_log):
        mock_cookies.return_value = None
        from AR1265 import getSoup
        result = getSoup("http://example.com")
        self.assertIsNone(result)
        mock_log.assert_called_with("No cookies obtained for the session")

    @patch("AR1265.log_error")
    @patch("AR1265.get_fresh_cookies")
    @patch("AR1265.session.get")
    @patch("AR1265.headers", {})
    def test_get_soup_blocked_by_imperva(self, mock_get, mock_cookies, mock_log):
        mock_cookies.return_value = {'cookie': 'value'}
        mock_response = Mock()
        mock_response.text = "Incapsula: Access Denied"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        from AR1265 import getSoup
        result = getSoup("http://example.com")
        self.assertIsNone(result)
        mock_log.assert_called()
        self.assertIn("Blocked by Imperva", mock_log.call_args[0][0])  

    def test_valid_appendix_link_found(self):
        html = """
        <html>
            <body>
                <table class="vc-table-plugin-theme-classic">
                    <tr><td><a href="/pdfs/appendix-a.pdf">Appendix A</a></td></tr>
                </table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = get_pdf_url_from_site(soup)
        self.assertEqual(result, "https://dep.nj.gov/pdfs/appendix-a.pdf")

    def test_no_soup_provided(self):
        with self.assertRaises(ValueError) as cm:
            get_pdf_url_from_site(None)
        self.assertEqual(str(cm.exception), "No soup object provided")

    def test_table_not_found(self):
        html = "<html><body><p>No table here</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        with self.assertRaises(ValueError) as cm:
            get_pdf_url_from_site(soup)
        self.assertEqual(str(cm.exception), "Target table not found")

    def test_appendix_a_link_not_found(self):
        html = """
        <html>
            <body>
                <table class="vc-table-plugin-theme-classic">
                    <tr><td><a href="/pdfs/appendix-b.pdf">Appendix B</a></td></tr>
                </table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        with self.assertRaises(ValueError) as cm:
            get_pdf_url_from_site(soup)
        self.assertEqual(str(cm.exception), "Appendix A link not found")  

    @patch("AR1265.get_fresh_cookies")
    @patch("AR1265.session.get")
    def test_fail_no_cookies(self, mock_get, mock_cookies):
        mock_cookies.return_value = None
        mock_response = Mock()
        mock_response.content = b"PDF content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            get_all_extracted_data_pdf("http://example.com/fail.pdf")

        self.assertTrue("Failed to get cookies" in str(cm.exception) or "has no attribute" in str(cm.exception))


if __name__ == '__main__':
    unittest.main()        