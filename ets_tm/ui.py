from typing import Any, Dict, List, Optional, Callable
import asyncio
from datetime import datetime
import time
from rich.table import Table
from rich import box


def build_table(
    servers: List[Dict[str, Any]],
    stats: Dict[str, Dict[str, int]],
    t: Callable[[str], str],
    app_state: Any,
    ping_host: Callable[[str], Optional[float]],
    check_port: Callable[[str, int, float], bool],
    port_timeout: float,
    max_concurrent: int,
    retry_attempts: int,
    retry_base_delay: float,
    server_key: Callable[[Dict[str, Any]], str],
    update_and_get_uptime: Callable[[Dict[str, Dict[str, int]], str, bool], Optional[float]],
    log_status: Callable[[Dict[str, Any], bool, Optional[float], Optional[float]], None],
    app_name: str,
    app_url: str,
) -> Table:
    title = (
        f"{app_name}  |  {app_url}  |  "
        f"{t('table.last_update')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    table = Table(
        title=title,
        box=box.ROUNDED,
        expand=True,
        style="bright_white on rgb(12,16,24)",
        title_style="bold white",
    )

    table.add_column(t("table.group"), justify="left", style="cyan", no_wrap=True)
    table.add_column(t("table.name"), justify="left", style="white")
    table.add_column(t("table.host"), justify="left", style="bright_blue")
    table.add_column(t("table.service"), justify="center", style="magenta")
    table.add_column(t("table.port"), justify="right", style="magenta")
    table.add_column(t("table.ping_ms"), justify="right", style="yellow")
    table.add_column(t("table.uptime"), justify="right", style="green")
    table.add_column(t("table.status"), justify="center", style="bold")

    if getattr(app_state, "current_group_filter", None):
        servers = [
            s for s in servers if s.get("group", t("general.default_group")) == app_state.current_group_filter
        ]
    filter_note = (
        f" | {t('filter.caption')}: {app_state.current_group_filter}" if getattr(app_state, "current_group_filter", None) else ""
    )
    table.caption = (
        f"{t('shortcuts')}: q {t('shortcut.quit')}, n {t('shortcut.add')}, s {t('shortcut.settings')}, l {t('shortcut.list')}, e {t('shortcut.edit')}, g {t('shortcut.filter')}, a {t('shortcut.clear_filter')}{filter_note}"
    )

    async def _check_one(s):
        host = s.get("host", "")
        port = int(s.get("port", 0))
        def _retry_ping():
            for i in range(max(1, retry_attempts)):
                r = ping_host(host)
                if r is not None:
                    return r
                time.sleep(retry_base_delay * (2 ** i))
            return None

        def _retry_port():
            if port <= 0:
                return False
            for i in range(max(1, retry_attempts)):
                ok = check_port(host, port, port_timeout)
                if ok:
                    return True
                time.sleep(retry_base_delay * (2 ** i))
            return False

        ping_task = asyncio.to_thread(_retry_ping)
        port_task = asyncio.to_thread(_retry_port)
        rtt, port_ok = await asyncio.gather(ping_task, port_task)
        return (s, rtt, bool(port_ok))

    async def _gather_batched(items, batch_size: int):
        out = []
        for i in range(0, len(items), max(1, batch_size)):
            batch = items[i:i+batch_size]
            res = await asyncio.gather(*(_check_one(s) for s in batch))
            out.extend(res)
        return out

    results = asyncio.run(_gather_batched(servers, max_concurrent))

    for srv, rtt, port_ok in results:
        name = srv.get("name", "")
        host = srv.get("host", "")
        group = srv.get("group", t("general.default_group"))
        service_name = srv.get("service", t("service.unknown"))
        service_key = f"service.{service_name}"
        _svc = t(service_key)
        service = service_name if _svc == service_key else _svc
        port = int(srv.get("port", 0))

        is_up = port_ok
        key = server_key(srv)
        uptime = update_and_get_uptime(stats, key, is_up)
        log_status(srv, is_up, rtt, uptime)

        status_text = t("status.online") if is_up else t("status.offline")
        ping_text = "-" if rtt is None else f"{rtt:6.1f}"
        uptime_text = "-" if uptime is None else f"{uptime:5.1f}%"

        table.add_row(
            group,
            name,
            host,
            service,
            str(port),
            ping_text,
            uptime_text,
            status_text,
        )

    return table