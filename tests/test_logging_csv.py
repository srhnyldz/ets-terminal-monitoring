import unittest
import tempfile
import os
from ets_tm.app_io import append_log_row, ensure_log_header


class TestLoggingCSV(unittest.TestCase):
    def test_append_log_row_creates_csv_line(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "monitor.log")
            ensure_log_header(p)
            row = [
                "2025-11-20T12:00:00",
                "General",
                "srv1",
                "1.1.1.1",
                "HTTP",
                "80",
                "UP",
                "10.5",
                "99.99",
            ]
            append_log_row(p, row)
            with open(p, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertTrue(lines[0].startswith("date;"))
            self.assertEqual(lines[1].split(";")[0], "2025-11-20T12:00:00")
            self.assertEqual(lines[1].split(";")[1], "General")


if __name__ == "__main__":
    unittest.main()