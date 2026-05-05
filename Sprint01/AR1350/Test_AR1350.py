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
import AR1350
from unittest.mock import patch, MagicMock
import undetected_chromedriver as uc
from urllib.parse import urljoin

from AR1350 import (main,log_error,create_final_json_file,errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,get_user_agent,get_html_with_dynamic_cookies)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}
class Test_AR1350(unittest.TestCase):

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
    
    @patch("AR1350.uc.Chrome")
    def test_get_user_agent(self, mock_chrome):
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = "Mozilla/5.0 (Headless Chrome)"

        mock_chrome.return_value = mock_driver
        user_agent = AR1350.get_user_agent()

        mock_chrome.assert_called_once()
        mock_driver.get.assert_called_with("https://www.example.com")
        mock_driver.execute_script.assert_called_once_with("return navigator.userAgent;")
        mock_driver.close.assert_called_once()
        mock_driver.quit.assert_called_once()

        self.assertNotIn("Headless", user_agent)
        self.assertEqual(user_agent, "Mozilla/5.0 ( Chrome)")

    @patch("AR1350.driver")
    @patch("AR1350.time.sleep", return_value=None)
    def test_cloudflare_bypassed_successfully(self, mock_sleep, mock_driver):
        initial_source = "<html><title>Just a moment...</title></html>"
        intermediate_source = "<html><body></body></html>"
        final_source = '<html><article class="qh__teaser-notification">Content</article></html>'

        page_sources = [initial_source] * 2 + [intermediate_source] * 2 + [final_source]

        mock_driver.page_source = initial_source

        def side_effect_get_page_source():
            return page_sources.pop(0) if page_sources else final_source

        type(mock_driver).page_source = property(side_effect_get_page_source)

    
        result = AR1350.get_html_with_dynamic_cookies("https://example.com")

        self.assertIsNotNone(result)
        self.assertIn("qh__teaser-notification", result)

    @patch("AR1350.driver")
    @patch("AR1350.time.sleep", return_value=None)
    def test_cloudflare_blocked(self, mock_sleep, mock_driver):
        mock_driver.page_source = "Just a moment..."

        type(mock_driver).page_source = property(lambda self: "Just a moment...")

        result = AR1350.get_html_with_dynamic_cookies("https://example.com")

        self.assertIsNone(result)

    @patch("AR1350.driver.get", side_effect=Exception("Driver crashed"))
    @patch("AR1350.log_error")
    def test_exception_handling(self, mock_log_error, mock_driver_get):
        result = AR1350.get_html_with_dynamic_cookies("https://example.com")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()

    @patch("AR1350.time.sleep", return_value=None)
    @patch("AR1350.driver")
    def test_cloudflare_bypassed_successfully(self, mock_driver, mock_sleep):

        page_sources = [
            "<html><title>Just a moment...</title></html>",
            "<html><body></body></html>",
            "<html><body></body></html>",
            '<html><article class="qh__teaser-notification">Passed</article></html>'
        ]

        mock_driver.page_source = ""
        mock_driver_instance = MagicMock()
        mock_driver.get = MagicMock()

        def page_source_side_effect():
            return page_sources.pop(0) if page_sources else '<html><article class="qh__teaser-notification">Done</article></html>'

        type(mock_driver).page_source = property(lambda self: page_source_side_effect())

      
        with patch.object(AR1350, 'driver', mock_driver):
            result = AR1350.get_html_with_dynamic_cookies("https://example.com")
            self.assertIsNotNone(result)
            self.assertIn("qh__teaser-notification", result) 


    @patch("AR1350.log_error")
    @patch("AR1350.requests.Session")
    @patch("AR1350.driver")
    @patch("AR1350.time.sleep", return_value=None) 
    def test_successful_pdf_download(self, mock_sleep, mock_driver, mock_session_class, mock_log_error):
   
        mock_driver.page_source = "<html>Not blocked</html>"
        mock_driver.current_url = "https://example.com/fake.pdf"
        mock_driver.get_cookies.return_value = [
            {"name": "cookie1", "value": "value1"},
            {"name": "cookie2", "value": "value2"},
        ]
        mock_driver.execute_script.return_value = "Mozilla/5.0 (TestAgent)"
        mock_driver.get = MagicMock()
        mock_driver.close = MagicMock()
        mock_driver.quit = MagicMock()

     
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

    
        result = AR1350.get_pdf_with_dynamic_cookies("https://example.com/fake.pdf")

    
        mock_driver.get.assert_called_once_with("https://example.com/fake.pdf")
        mock_driver.execute_script.assert_called_once_with("return navigator.userAgent;")
        mock_session.get.assert_called_once_with(
            "https://example.com/fake.pdf",
            headers={
                "User-Agent": "Mozilla/5.0 (TestAgent)",
                "Referer": "https://dlt.ri.gov/regulation-and-safety/occupational-safety",
                "Accept": "application/pdf",
                "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            },
            allow_redirects=True,
        )
        mock_response.raise_for_status.assert_called_once()

        self.assertEqual(result, mock_response)

    @patch("AR1350.log_error")
    @patch("AR1350.driver")
    @patch("AR1350.time.sleep", return_value=None)
    def test_cloudflare_blocked(self, mock_sleep, mock_driver, mock_log_error):

        mock_driver.page_source = "Just a moment..."
        mock_driver.get = MagicMock()
        mock_driver.close = MagicMock()
        mock_driver.quit = MagicMock()

        result = AR1350.get_pdf_with_dynamic_cookies("https://example.com/fake.pdf")

        self.assertIsNone(result)
        mock_driver.get.assert_called_once()
        mock_log_error.assert_not_called()

    @patch("AR1350.log_error")
    @patch("AR1350.driver")
    @patch("AR1350.time.sleep", return_value=None)
    def test_exception_handling(self, mock_sleep, mock_driver, mock_log_error):

        mock_driver.get.side_effect = Exception("Driver crashed")
        mock_driver.close = MagicMock()
        mock_driver.quit = MagicMock()

        result = AR1350.get_pdf_with_dynamic_cookies("https://example.com/fake.pdf")

        self.assertIsNone(result)
        mock_log_error.assert_called_once()   


    def test_extract_links_normal_html(self):
        html = """
        <html>
            <body>
                <a href="https://example.com/page1">Page 1</a>
                <a href="https://example.com/page2">Page 2</a>
                <a href="https://example.com/page3">   Page 3   </a>
            </body>
        </html>
        """
        expected = [
            ("Page 1", "https://example.com/page1"),
            ("Page 2", "https://example.com/page2"),
            ("Page 3", "https://example.com/page3"),
        ]
        result = AR1350.extract_links(html)
        self.assertEqual(result, expected)

    def test_extract_links_no_links(self):
        html = "<html><body><p>No links here</p></body></html>"
        result = AR1350.extract_links(html)
        self.assertEqual(result, [])

    def test_extract_links_none_input(self):

        result = AR1350.extract_links(None)
        self.assertEqual(result, [])

    @patch("AR1350.BeautifulSoup")
    @patch("AR1350.log_error")
    def test_extract_links_exception(self, mock_log_error, mock_bs):
        mock_bs.side_effect = Exception("Parse error")
        result = AR1350.extract_links("<html></html>")
        self.assertEqual(result, [])
        mock_log_error.assert_called_once()

    def test_find_link_by_text(self):
        base_url = "https://example.com/"
        links = [
            ("Some text", "/other"),
            ("by CAS Number", "/cas123"),
            ("Another", "/cas456")
        ]
        expected = urljoin(base_url, "/cas123")
        result = AR1350.find_cas_link(links, base_url)
        self.assertEqual(result, expected)

    def test_find_link_by_href(self):
        base_url = "https://example.com/"
        links = [
            ("Other", "/something"),
            ("No match", "/path/HazardousCAS/abc"),
        ]
        expected = urljoin(base_url, "/path/HazardousCAS/abc")
        result = AR1350.find_cas_link(links, base_url)
        self.assertEqual(result, expected)

    def test_no_match_returns_none(self):
        base_url = "https://example.com/"
        links = [
            ("Other", "/something"),
            ("Nope", "/path/other"),
        ]
        result = AR1350.find_cas_link(links, base_url)
        self.assertIsNone(result)

    @patch("AR1350.log_error")
    def test_exception_handling(self, mock_log_error):
       
        result = AR1350.find_cas_link(None, None)
        self.assertIsNone(result)
        mock_log_error.assert_called_once() 


    @patch("AR1350.log_error")
    @patch("AR1350.get_pdf_with_dynamic_cookies")
    @patch("AR1350.pdfplumber.open")
    def test_extract_hazardous_data_success(self, mock_pdfplumber_open, mock_get_pdf, mock_log_error):
       
        mock_response = MagicMock()
        mock_response.content = b"fake pdf bytes"
        mock_get_pdf.return_value = mock_response

        mock_pdf = MagicMock()
        page1 = MagicMock()

        page1.extract_text.return_value = (
            "===== Page 1 =====\n"
            "RHODE ISLAND HAZARDOUS SUBSTANCE LIST\n"
            "Source: T - ACGIH F - NFPA49 C - IARC\n"
            "C. A. S. Order\n"
            "123-45-6 T F C ChemicalOne\n"
            "789-01-2 F ChemicalTwo\n"
            "ChemicalThree T\n"
            "789-01-2 F ChemicalTwo\n" 
        )
        mock_pdf.pages = [page1]

        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf


        result = AR1350.extract_hazardous_data("https://example.com/fake.pdf")

        expected = [
            {
                "CHEMICAL NAME": "ChemicalOne",
                "C.A.S.": "123-45-6",
                "ACGIH": "T",
                "NFPA": "F",
                "IARC": "C"
            },
            {
                "CHEMICAL NAME": "ChemicalTwo",
                "C.A.S.": "789-01-2",
                "ACGIH": None,
                "NFPA": "F",
                "IARC": None
            },
            {
                "CHEMICAL NAME": "ChemicalThree",
                "C.A.S.": None,
                "ACGIH": "T",
                "NFPA": None,
                "IARC": None
            }
        ]

        self.assertEqual(result, expected)
        mock_log_error.assert_not_called()

    @patch("AR1350.log_error")
    @patch("AR1350.get_pdf_with_dynamic_cookies")
    def test_extract_hazardous_data_pdf_fetch_fail(self, mock_get_pdf, mock_log_error):
        mock_get_pdf.return_value = None 
        result = AR1350.extract_hazardous_data("https://example.com/fake.pdf")
        self.assertEqual(result, [])
        mock_log_error.assert_called_once()

    @patch("AR1350.log_error")
    @patch("AR1350.get_pdf_with_dynamic_cookies")
    @patch("AR1350.pdfplumber.open")
    def test_extract_hazardous_data_exception_in_pdfplumber(self, mock_pdfplumber_open, mock_get_pdf, mock_log_error):
        mock_response = MagicMock()
        mock_response.content = b"fake pdf bytes"
        mock_get_pdf.return_value = mock_response

        mock_pdfplumber_open.side_effect = Exception("PDF open error")

        result = AR1350.extract_hazardous_data("https://example.com/fake.pdf")

        self.assertEqual(result, [])
        mock_log_error.assert_called_once()                        
if __name__ == '__main__':
    unittest.main()