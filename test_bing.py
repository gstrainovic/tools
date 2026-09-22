import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("bing", Path(__file__).with_name("bing.py"))
bing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bing)


class ReplaceUrls(unittest.TestCase):
    def test_ersetzt_nur_exakte_treffer(self):
        self.assertEqual(bing.replace_urls(["https://wartungsheft.ch/google", "https://wartungsheft.ch/betrieb"],
                                           "https://wartungsheft.ch/google", "https://wartungsheft.ch/bing"),
                         ["https://wartungsheft.ch/bing", "https://wartungsheft.ch/betrieb"])

    def test_google_privat_bleibt_bei_google_regel(self):
        self.assertEqual(bing.replace_urls(["https://wartungsheft.ch/google-privat"],
                                           "https://wartungsheft.ch/google", "https://wartungsheft.ch/bing"),
                         ["https://wartungsheft.ch/google-privat"])


class Config(unittest.TestCase):
    def test_liest_toml(self):
        path = Path(self.id().replace(".", "_") + ".toml")
        path.write_text('developer_token = "T"\ncustomer_id = 1\naccount_id = 2\n')
        try:
            self.assertEqual(bing.load_config(path), {"developer_token": "T", "customer_id": 1, "account_id": 2})
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
