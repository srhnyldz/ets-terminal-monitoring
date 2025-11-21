import unittest
import tempfile
import os
from ets_tm.repo import FileRepository
from ets_tm.services import MonitoringService
from ets_tm.background import BackgroundMonitor


class TestBackground(unittest.TestCase):
    def test_run_once_updates_stats_and_log(self):
        with tempfile.TemporaryDirectory() as d:
            servers_path = os.path.join(d, "servers.txt")
            backup_path = os.path.join(d, "servers.bak")
            stats_path = os.path.join(d, "server_stats.json")
            settings_path = os.path.join(d, "config.json")
            log_path = os.path.join(d, "monitor.log")

            repo = FileRepository(servers_path, backup_path, stats_path, settings_path)
            repo.save_servers([
                {"name": "srv1", "host": "127.0.0.1", "group": "General", "service": "HTTP", "port": 80}
            ])
            repo.save_stats({})
            repo.save_settings({
                "refresh_interval": 0.5,
                "ping_timeout": 0.1,
                "port_timeout": 0.1,
                "prefer_system_ping": False,
                "max_concurrent_checks": 2,
                "retry_attempts": 1,
                "retry_base_delay": 0.01,
                "page_size": 10,
            })

            svc = MonitoringService(0.05, 0.05, False)
            mon = BackgroundMonitor(repo, svc, log_path, 0.2, 2, 1, 0.01)
            mon.run_once()

            stats = repo.get_stats()
            self.assertTrue(len(stats.keys()) >= 1)
            self.assertTrue(os.path.exists(log_path))
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertTrue(lines[0].startswith("date;"))
            self.assertTrue(len(lines) >= 2)


if __name__ == "__main__":
    unittest.main()