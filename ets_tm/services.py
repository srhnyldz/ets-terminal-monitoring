from typing import Any, Dict, Optional, Tuple
from .core import ping_host as core_ping_host, check_port as core_check_port


class MonitoringService:
    def __init__(self, ping_timeout: float, port_timeout: float, prefer_system_ping: bool) -> None:
        self.ping_timeout = ping_timeout
        self.port_timeout = port_timeout
        self.prefer_system_ping = prefer_system_ping

    def ping_host(self, host: str) -> Optional[float]:
        return core_ping_host(host, timeout=self.ping_timeout, prefer_system_ping=self.prefer_system_ping)

    def check_port(self, host: str, port: int) -> bool:
        return core_check_port(host, port, timeout=self.port_timeout)

    def evaluate(self, server: Dict[str, Any]) -> Tuple[Optional[float], bool]:
        host = str(server.get("host", ""))
        port = int(server.get("port", 0))
        rtt = self.ping_host(host)
        is_open = self.check_port(host, port) if port > 0 else False
        return (rtt, is_open)


# GroupService removed due to unused status in current CLI flows