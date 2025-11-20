import unittest
import tempfile
import os
from ets_tm.app_io import ensure_log_header


class TestAppIO(unittest.TestCase):
    def test_ensure_log_header_on_new_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "monitor.log")
            ensure_log_header(p)
            with open(p, "r", encoding="utf-8") as f:
                first = f.readline()
            self.assertTrue(first.startswith("date;"))


if __name__ == "__main__":
    unittest.main()