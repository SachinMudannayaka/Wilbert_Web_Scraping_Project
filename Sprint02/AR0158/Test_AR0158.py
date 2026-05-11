import unittest
import pandas as pd
import os
import glob
import json
import random
from unittest.mock import patch
from datetime import datetime

import AR0158
from AR0158 import (
    main, log_error, create_final_json, errors,
    uniqueIdentity, region, jurisdiction, category, title, casKeyValue
)


class Test_AR0158(unittest.TestCase):

    @staticmethod
    def find_json_path():
        folder_path = "out"
        json_files = glob.glob(os.path.join(folder_path, "**", "*.json"), recursive=True)
        return max(json_files, key=os.path.getmtime) if json_files else None

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
        required_keys = {
            "UniqueIdentity", "region", "Jurisdiction",
            "category", "title", "casKey", "dateAndTime", "errors", "data"
        }
        self.assertTrue(required_keys.issubset(set(self.current_json_data.keys())))

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

    def test_04_json_column_name_and_count(self):
        test_keys = self.test_json_data["data"][0].keys()
        current_keys = self.current_json_data["data"][0].keys()
        self.assertEqual(len(test_keys), len(current_keys))
        self.assertEqual(list(test_keys), list(current_keys))

    def test_05_json_meta_content(self):
        self.assertEqual(self.current_json_data["title"], self.test_json_data["title"])
        self.assertEqual(self.current_json_data["UniqueIdentity"], self.test_json_data["UniqueIdentity"])
        self.assertEqual(self.current_json_data["region"], self.test_json_data["region"])
        self.assertEqual(self.current_json_data["Jurisdiction"], self.test_json_data["Jurisdiction"])
        self.assertEqual(self.current_json_data["category"], self.test_json_data["category"])
        self.assertEqual(self.current_json_data["casKey"], self.test_json_data["casKey"])
        datetime.strptime(self.current_json_data["dateAndTime"], "%Y-%m-%d %H:%M:%S") 

    def test_06_json_data_sha_hash_match(self):
        test_sha_hashes = {item["sha_hash"] for item in self.test_json_data["data"]}
        current_sha_hashes = [item["sha_hash"] for item in self.current_json_data["data"]]
        sample_size = min(10, len(current_sha_hashes))
        sampled = random.sample(current_sha_hashes, sample_size)
        for sha in sampled:
            self.assertIn(sha, test_sha_hashes, f"Missing SHA: {sha}")

    def test_07_insert_line_breaks(self):
        input_text = "Some substance CAS No 123-45-6 (a) additional info (b)"
        expected = "Some substance\nCAS No 123-45-6\n(a) additional info\n(b)"
        result = AR0158.insert_line_breaks(input_text)
        self.assertEqual(result, expected)

    @patch("AR0158.scraper.get")
    def test_08_get_latest_pdf_url_failure(self, mock_get):
        mock_get.side_effect = Exception("Network failure")
        result = AR0158.get_latest_pdf_url()
        self.assertIsNone(result)
        self.assertIn("Failed to retrieve latest PDF URL", AR0158.errors[-1])

    def test_09_log_error(self):
        errors.clear()
        msg = "This is a test error"
        log_error(msg)
        self.assertIn(msg, errors)
        self.assertEqual(len(errors), 1)

    @patch("AR0158.scraper.get")
    def test_10_download_pdf_success(self, mock_get):
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def raise_for_status(self): pass
            def iter_content(self, chunk_size=8192):
                return [b'test pdf content']

        mock_get.return_value = MockResponse()

        temp_path = "out1/test_download.pdf"
        if os.path.exists(temp_path):
            os.remove(temp_path)

        AR0158.download_pdf("http://example.com/sample.pdf", temp_path)
        self.assertTrue(os.path.exists(temp_path))

        os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
