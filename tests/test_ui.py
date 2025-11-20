import unittest
from ets_tm.ui import build_table


class DummyState:
    current_group_filter = None


def t(k, **kwargs):
    return {
        "table.last_update": "Last Update",
        "table.group": "Group",
        "table.name": "Name",
        "table.host": "Host / IP",
        "table.service": "Service",
        "table.port": "Port",
        "table.ping_ms": "Ping (ms)",
        "table.uptime": "Uptime",
        "table.status": "Status",
        "general.default_group": "General",
        "service.unknown": "Unknown",
        "shortcuts": "Shortcuts",
        "shortcut.quit": "quit",
        "shortcut.add": "add",
        "shortcut.settings": "settings",
        "shortcut.list": "list",
        "shortcut.edit": "edit",
        "shortcut.filter": "filter",
        "shortcut.clear_filter": "clear filter",
        "status.online": "ONLINE",
        "status.offline": "OFFLINE",
        "filter.caption": "filter",
        "search.caption": "search",
        "service_filter.caption": "service",
        "summary.title": "Summary",
        "summary.1h": "1h",
        "summary.24h": "24h",
        "summary.up": "up",
        "summary.down": "down",
        "summary.avg_ping": "avg",
        "summary.uptime": "uptime",
        "shortcut.search": "search",
        "shortcut.clear_search": "clear search",
        "shortcut.service_filter": "service filter",
        "shortcut.clear_service_filter": "clear service filter",
    }.get(k, k)


def ping_host(host):
    return 10.0


def check_port(host, port, timeout):
    return True


def server_key(srv):
    return f"{srv.get('host')}:{srv.get('port')}:{srv.get('service')}"


def update_and_get_uptime(stats, key, is_up):
    return 100.0


def log_status(srv, is_up, rtt, uptime):
    pass


def get_summary_metrics():
    return {
        "1h": {"up": 1, "down": 0, "avg_ping": 10.0, "uptime": 100.0},
        "24h": {"up": 1, "down": 0, "avg_ping": 10.0, "uptime": 100.0},
    }


class TestUI(unittest.TestCase):
    def test_build_table_structure(self):
        servers = [{"name": "srv1", "host": "1.1.1.1", "group": "General", "service": "HTTP", "port": 80}]
        stats = {}
        table = build_table(
            servers,
            stats,
            t,
            DummyState(),
            ping_host,
            check_port,
            1.0,
            5,
            10,
            2,
            0.1,
            server_key,
            update_and_get_uptime,
            log_status,
            get_summary_metrics,
            "ETS TM",
            "example.com",
        )
        self.assertEqual(len(table.columns), 8)
        self.assertGreaterEqual(len(table.rows), 1)


if __name__ == "__main__":
    unittest.main()