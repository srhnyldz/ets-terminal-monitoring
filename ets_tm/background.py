import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from .repo import FileRepository
from .services import MonitoringService
from . import app_io


def _server_key(srv: Dict[str, Any]) -> str:
    return f"{srv.get('host','')}:{srv.get('port','')}:{srv.get('service','')}"


def _update_and_get_uptime(stats: Dict[str, Dict[str, int]], key: str, is_up: bool) -> Optional[float]:
    s = stats.setdefault(key, {"ok": 0, "fail": 0})
    if is_up:
        s["ok"] += 1
    else:
        s["fail"] += 1
    total = s["ok"] + s["fail"]
    if total == 0:
        return None
    return (s["ok"] / total) * 100.0


class BackgroundMonitor:
    def __init__(
        self,
        repo: FileRepository,
        svc: MonitoringService,
        log_path: str,
        refresh_interval: float,
        max_concurrent: int,
        retry_attempts: int,
        retry_base_delay: float,
    ) -> None:
        self.repo = repo
        self.svc = svc
        self.log_path = log_path
        self.refresh_interval = max(0.5, float(refresh_interval))
        self.max_concurrent = max(1, int(max_concurrent))
        self.retry_attempts = max(1, int(retry_attempts))
        self.retry_base_delay = float(retry_base_delay)
        self._running = False

    async def _check_one(self, srv: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[float], bool]:
        host = str(srv.get("host", ""))
        port = int(srv.get("port", 0))

        def _retry_ping():
            for i in range(self.retry_attempts):
                r = self.svc.ping_host(host)
                if r is not None:
                    return r
                time.sleep(self.retry_base_delay * (2 ** i))
            return None

        def _retry_port():
            if port <= 0:
                return False
            for i in range(self.retry_attempts):
                ok = self.svc.check_port(host, port)
                if ok:
                    return True
                time.sleep(self.retry_base_delay * (2 ** i))
            return False

        ping_task = asyncio.to_thread(_retry_ping)
        port_task = asyncio.to_thread(_retry_port)
        rtt, port_ok = await asyncio.gather(ping_task, port_task)
        return (srv, rtt, bool(port_ok))

    async def _gather_batched(self, items: List[Dict[str, Any]], batch_size: int):
        out = []
        for i in range(0, len(items), max(1, batch_size)):
            batch = items[i:i + batch_size]
            res = await asyncio.gather(*(self._check_one(s) for s in batch))
            out.extend(res)
        return out

    def run_once(self) -> None:
        servers = self.repo.get_servers()
        if not servers:
            return
        stats = self.repo.get_stats()
        results = asyncio.run(self._gather_batched(servers, self.max_concurrent))
        for srv, rtt, port_ok in results:
            uptime = _update_and_get_uptime(stats, _server_key(srv), port_ok)
            status_str = "UP" if port_ok else "DOWN"
            ping_str = "-" if rtt is None else f"{rtt:.1f}"
            row = [
                time.strftime("%Y-%m-%dT%H:%M:%S"),
                str(srv.get("group", "General")),
                str(srv.get("name", "")),
                str(srv.get("host", "")),
                str(srv.get("service", "")),
                str(int(srv.get("port", 0)) or 0),
                status_str,
                ping_str,
                "-" if uptime is None else f"{uptime:.2f}",
            ]
            app_io.append_log_row(self.log_path, row, ensure_header=True)
        self.repo.save_stats(stats)

    def run_forever(self, stop_after_cycles: Optional[int] = None) -> None:
        self._running = True
        cycles = 0
        try:
            while self._running:
                self.run_once()
                cycles += 1
                if stop_after_cycles and cycles >= stop_after_cycles:
                    break
                time.sleep(self.refresh_interval)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False