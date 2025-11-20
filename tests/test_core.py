import unittest
from ets_tm.core import PingPolicy


class TestCore(unittest.TestCase):
    def test_parse_rtt_valid(self):
        pol = PingPolicy()
        out = "64 bytes from 8.8.8.8: icmp_seq=0 ttl=57 time=23.4 ms"
        self.assertAlmostEqual(pol.parse_rtt(out), 23.4, places=1)

    def test_parse_rtt_invalid(self):
        pol = PingPolicy()
        out = "no time here"
        self.assertIsNone(pol.parse_rtt(out))


if __name__ == "__main__":
    unittest.main()