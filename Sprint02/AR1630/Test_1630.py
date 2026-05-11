import unittest
import pandas as pd
import os
from unittest.mock import patch, MagicMock,mock_open
from bs4 import BeautifulSoup
from datetime import datetime
import os
import glob
import json
import random
from unittest.mock import patch, Mock
import AR1630
from urllib.parse import urljoin
from contextlib import redirect_stdout
import io
from AR1630 import (log_error,create_final_json_file,getSoup,main,
                    errors,uniqueIdentity,region,jurisdiction,category,title,casKeyValue,extract_low_priority_chemicals,extract_high_chemical_table_data)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

class Test_AR1630(unittest.TestCase):

    @staticmethod
    def find_latest_folder():
        main()
        folder_path = "out"
        subfolders = [f for f in glob.glob(os.path.join(folder_path, "*")) if os.path.isdir(f)]

        if not subfolders:
            print("No subfolders found in the 'out' directory.")
            return None

        latest_folder = max(subfolders, key=os.path.getmtime)
        print(f"The latest folder is: {latest_folder}")
        return latest_folder

    @staticmethod
    def find_all_json_files():
        latest_folder = Test_AR1630.find_latest_folder()
        if not latest_folder:
            return []

        json_files = glob.glob(os.path.join(latest_folder, "*.json"))
        if json_files:
            print(f"Found JSON files: {json_files}")
            return json_files
        else:
            print("No JSON files found in the latest folder.")
            return []

    @classmethod
    def setUpClass(cls):
        cls.test_json_paths = sorted(glob.glob("test_*.json")) 
        cls.current_json_paths = sorted(cls.find_all_json_files()) 


        if not cls.current_json_paths or not cls.test_json_paths:
            raise FileNotFoundError("No JSON files found for comparison.")

        cls.test_json_data_dic = {}
        for index, test_path in enumerate(cls.test_json_paths, start=1):
            with open(test_path, "r", encoding="utf-8") as test_f:
                tkey = f"test_json_data_{index}"  
                cls.test_json_data_dic[tkey] = json.load(test_f) 


        cls.current_json_data_dic = {}
        for index, json_path in enumerate(cls.current_json_paths, start=1):
            with open(json_path, "r", encoding="utf-8") as actual_f:
                cls.current_json_data_dic[f"current_json_data_{index}"] = json.load(actual_f)


    def test_01_json_required_keys(self):
        required_keys = {"UniqueIdentity", "region", "Jurisdiction", "category", "title", "casKey", "dateAndTime", "errors", "data"}
        for json_data in self.current_json_data_dic.values():
            self.assertTrue(required_keys.issubset(json_data.keys()))

    def test_02_json_key_data_types(self):
        for json_data in self.current_json_data_dic.values():
            self.assertIsInstance(json_data["UniqueIdentity"], str)
            self.assertIsInstance(json_data["region"], str)
            self.assertIsInstance(json_data["Jurisdiction"], str)
            self.assertIsInstance(json_data["category"], str)
            self.assertIsInstance(json_data["title"], str)
            self.assertIsInstance(json_data["casKey"], (str, type(None)))
            self.assertIsInstance(json_data["errors"], list)
            self.assertIsInstance(json_data["data"], list)

    def test_03_json_column_and_row_consistency(self):
        for json_data in self.current_json_data_dic.values():
            first_row_keys = set(json_data["data"][0].keys())
            for row in json_data["data"]:
                self.assertEqual(set(row.keys()), first_row_keys)

    def test_04_json_column_name_and_count(self):
        for index, (json_key, json_data) in enumerate(self.current_json_data_dic.items(), start=1):
            test_key = f"test_json_data_{index}"

            if test_key in self.test_json_data_dic:
                with self.subTest(json_file=index):

                    actual_column_count = len(json_data["data"][0].keys())
                    test_column_count = len(self.test_json_data_dic[test_key]["data"][0].keys())
                    self.assertEqual(test_column_count, actual_column_count)
                    self.assertEqual(self.test_json_data_dic[test_key]["data"][0].keys(), json_data["data"][0].keys())

    def test_05_json_meta_content(self):
        for index, (json_key, json_data) in enumerate(self.current_json_data_dic.items(), start=1):
            test_key = f"test_json_data_{index}"
            if test_key in self.test_json_data_dic:
                with self.subTest(json_file=index):
                    self.assertEqual(json_data["title"], self.test_json_data_dic[test_key]["title"])
                    self.assertEqual(json_data["UniqueIdentity"], self.test_json_data_dic[test_key]["UniqueIdentity"])
                    self.assertEqual(json_data["region"], self.test_json_data_dic[test_key]["region"])
                    self.assertEqual(json_data["Jurisdiction"], self.test_json_data_dic[test_key]["Jurisdiction"])
                    self.assertEqual(json_data["category"], self.test_json_data_dic[test_key]["category"])
                    self.assertEqual(json_data["casKey"], self.test_json_data_dic[test_key]["casKey"])
                    datetime.strptime(json_data["dateAndTime"], "%Y-%m-%d %H:%M:%S")

    def test_06_json_data_content(self):
        for index, (json_key, json_data) in enumerate(self.current_json_data_dic.items(), start=1):
            test_key = f"test_json_data_{index}"
            if test_key in self.test_json_data_dic:
                with self.subTest(json_file=index):
                    current_all_sha_hashes = [item["sha_hash"] for item in json_data["data"]]
                    sample_size = min(10, len(current_all_sha_hashes))
                    sampled_sha_hashes = random.sample(current_all_sha_hashes, sample_size)
                    test_sha_hashes = {item["sha_hash"] for item in self.test_json_data_dic[test_key]["data"]}

                    for current_sha_hash in sampled_sha_hashes:
                        self.assertIn(current_sha_hash, test_sha_hashes,
                                      f"SHA hash {current_sha_hash} not found in test JSON data")    

    @patch("AR1630.requests.get")
    def test_getSoup_success(self, mock_get):
        html = "<html><body><h1>Hello</h1></body></html>"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        soup = getSoup("https://example.com")
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertEqual(soup.h1.text, "Hello")

    @patch("AR1630.requests.get")
    def test_getSoup_failure(self, mock_get):
        mock_get.side_effect = Exception("Connection error")

        soup = getSoup("https://example.com")
        self.assertIsNone(soup)

    def setUp(self):
        self.base_url = "https://example.com"

    def test_extract_high_chemical_table_data_success(self):
        html = """
        <table class="datatable">
            <tbody>
                <tr>
                    <td><a href="/chem/abc">Chemical ABC</a></td>
                    <td>123-45-6</td>
                    <td>Group A</td>
                    <td>2023-01-01</td>
                    <td><a href="/docket/001">Docket001</a></td>
                    <td>Active</td>
                    <td>John Smith<br>john@example.com</td>
                </tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = extract_high_chemical_table_data(soup, self.base_url)
        expected = [{
            "chemical_name": "Chemical ABC",
            "chemical_name_url": urljoin(self.base_url, "/chem/abc"),
            "casrn": "123-45-6",
            "chemical_group": "Group A",
            "date_initiated": "2023-01-01",
            "docket_numbers": ["Docket001"],
            "docket_links": [urljoin(self.base_url, "/docket/001")],
            "status": "Active",
            "agency_contact": "John Smith\njohn@example.com"
        }]
        self.assertEqual(result, expected)

    def test_extract_low_priority_chemicals_success(self):
        html = """
        <table id="datatablelow">
            <tbody>
                <tr>
                    <td>Chemical XYZ</td>
                    <td>789-01-2</td>
                    <td><a href="/docket/xyz">DocketXYZ</a></td>
                    <td>Pending</td>
                    <td>Jane Doe<br>jane@example.com</td>
                </tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = extract_low_priority_chemicals(soup, self.base_url)
        expected = [{
            "chemical_name": "Chemical XYZ",
            "cas": "789-01-2",
            "docket_number": "DocketXYZ",
            "docket_url": urljoin(self.base_url, "/docket/xyz"),
            "status": "Pending",
            "agency_contact": "Jane Doe\njane@example.com"
        }]
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()                        