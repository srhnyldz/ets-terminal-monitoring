from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
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

    for srv in servers:
        name = srv.get("name", "")
        host = srv.get("host", "")
        group = srv.get("group", t("general.default_group"))
        service = srv.get("service", t("service.unknown"))
        port = int(srv.get("port", 0))

        rtt = ping_host(host)
        port_ok = check_port(host, port, port_timeout) if port > 0 else False
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