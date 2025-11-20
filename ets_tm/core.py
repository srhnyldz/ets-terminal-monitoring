import re
import subprocess
import socket
from typing import Optional


class PingPolicy:
    def parse_rtt(self, output: str) -> Optional[float]:
        m = re.search(r"time[=<]\s*([\d\.]+)\s*ms", output)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
        return None


class PortPolicy:
    def is_open(self, host: str, port: int, timeout: float) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False


def ping_host(host: str, timeout: float, prefer_system_ping: bool, policy: Optional[PingPolicy] = None) -> Optional[float]:
    pol = policy or PingPolicy()
    if prefer_system_ping:
        try:
            proc = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=timeout + 1)
            if proc.returncode == 0:
                out = proc.stdout or proc.stderr
                r = pol.parse_rtt(out)
                if r is not None:
                    return r
        except Exception:
            pass
    try:
        from ping3 import ping as _ping
        rtt = _ping(host, timeout=timeout, unit="ms", privileged=False)
        if rtt is not None:
            return float(rtt)
    except Exception:
        pass
    try:
        proc = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=timeout + 1)
        if proc.returncode != 0:
            return None
        out = proc.stdout or proc.stderr
        r = pol.parse_rtt(out)
        if r is not None:
            return r
        return None
    except Exception:
        return None


def check_port(host: str, port: int, timeout: float, policy: Optional[PortPolicy] = None) -> bool:
    pol = policy or PortPolicy()
    return pol.is_open(host, port, timeout)