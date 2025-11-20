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
    page_size: int,
    retry_attempts: int,
    retry_base_delay: float,
    server_key: Callable[[Dict[str, Any]], str],
    update_and_get_uptime: Callable[[Dict[str, Dict[str, int]], str, bool], Optional[float]],
    log_status: Callable[[Dict[str, Any], bool, Optional[float], Optional[float]], None],
    get_summary_metrics: Callable[[], Dict[str, Any]],
    app_name: str,
    app_url: str,
) -> Table:
    title = (
        f"{app_name}  |  {app_url}  |  "
        f"{t('table.last_update')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    table = Table(
        title=title,
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True,
        style="bright_white on rgb(10,14,22)",
        title_style="bold bright_cyan",
        caption_style="dim",
        header_style="bold cyan",
        border_style="bright_black",
        row_styles=["none", "dim"],
        show_header=True,
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
    q = getattr(app_state, "current_search_query", None)
    if q:
        ql = q.lower()
        def _hit(s: Dict[str, Any]) -> bool:
            return (
                ql in str(s.get("group", t("general.default_group"))).lower()
                or ql in str(s.get("name", "")).lower()
                or ql in str(s.get("host", "")).lower()
                or ql in str(s.get("service", "")).lower()
            )
        servers = [s for s in servers if _hit(s)]
    svc_filter = getattr(app_state, "current_service_filter", None)
    if svc_filter:
        servers = [s for s in servers if s.get("service", "") == svc_filter]
    sort_key = getattr(app_state, "current_sort_key", "name")
    sort_desc = bool(getattr(app_state, "sort_desc", False))
    def _srv_sort_value(s: Dict[str, Any]):
        if sort_key == "group":
            return s.get("group", t("general.default_group"))
        if sort_key == "name":
            return s.get("name", "")
        if sort_key == "host":
            return s.get("host", "")
        if sort_key == "service":
            return s.get("service", "")
        if sort_key == "port":
            return int(s.get("port", 0))
        return s.get("name", "")
    servers.sort(key=_srv_sort_value, reverse=sort_desc)
    total = len(servers)
    total_pages = max(1, (total + max(1, page_size) - 1) // max(1, page_size))
    try:
        app_state.current_page = min(max(1, app_state.current_page), total_pages)
    except Exception:
        app_state.current_page = 1
    start = (app_state.current_page - 1) * max(1, page_size)
    end = start + max(1, page_size)
    page_servers = servers[start:end]
    page_note = f" | {t('table.page', page=app_state.current_page, total=total_pages)}" if total_pages > 1 else ""
    filter_note = (
        f" | {t('filter.caption')}: {app_state.current_group_filter}" if getattr(app_state, "current_group_filter", None) else ""
    )
    search_note = (
        f" | {t('search.caption')}: {app_state.current_search_query}" if getattr(app_state, "current_search_query", None) else ""
    )
    svc_note = (
        f" | {t('service_filter.caption')}: {app_state.current_service_filter}" if getattr(app_state, "current_service_filter", None) else ""
    )
    sort_note = f" | {t('table.sort')}: {sort_key} {t('sort.desc') if sort_desc else t('sort.asc')}"
    metrics = get_summary_metrics()
    m1 = metrics.get("1h", {})
    m2 = metrics.get("24h", {})
    def _fmt(v, suf=""):
        return "-" if v is None else (f"{v:.1f}{suf}" if isinstance(v, float) else str(v))
    pref = f"{t('summary.title')}: "
    label_w = max(len(t('summary.1h')), len(t('summary.24h')))
    def _pad(x, w):
        return f"{x:>{w}}"
    def _fmt_int(v):
        return _pad("-" if v is None else str(v), 4)
    def _fmt_avg(v):
        return _pad("-" if v is None else f"{v:.1f} ms", 9)
    def _fmt_pct(v):
        return _pad("-" if v is None else f"{v:.1f} %", 8)
    line1 = (
        f"{pref}{t('summary.1h'):<{label_w}} | {t('summary.up')} {_fmt_int(m1.get('up'))} | {t('summary.down')} {_fmt_int(m1.get('down'))} | {t('summary.avg_ping')} {_fmt_avg(m1.get('avg_ping'))} | {t('summary.uptime')} {_fmt_pct(m1.get('uptime'))}"
    )
    line2 = (
        f"{' ' * len(pref)}{t('summary.24h'):<{label_w}} | {t('summary.up')} {_fmt_int(m2.get('up'))} | {t('summary.down')} {_fmt_int(m2.get('down'))} | {t('summary.avg_ping')} {_fmt_avg(m2.get('avg_ping'))} | {t('summary.uptime')} {_fmt_pct(m2.get('uptime'))}"
    )
    table.caption = (
        f"{line1}\n{line2}\n{t('shortcuts')}: q {t('shortcut.quit')}, n {t('shortcut.add')}, s {t('shortcut.settings')}, l {t('shortcut.list')}, e {t('shortcut.edit')}, g {t('shortcut.filter')}, a {t('shortcut.clear_filter')}, / {t('shortcut.search')}, x {t('shortcut.clear_search')}, h {t('shortcut.service_filter')}, z {t('shortcut.clear_service_filter')}, ] {t('shortcut.next_page')}, [ {t('shortcut.prev_page')}, > {t('shortcut.next_sort')}, < {t('shortcut.prev_sort')}, r {t('shortcut.toggle_sort_order')}{filter_note}{search_note}{svc_note}{page_note}{sort_note}"
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

    results = asyncio.run(_gather_batched(page_servers, max_concurrent))

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
        if rtt is None:
            ping_text = "[dim]-[/dim]"
        else:
            ping_text = (
                f"[green]{rtt:6.1f}[/green]" if rtt < 50.0 else (
                    f"[yellow]{rtt:6.1f}[/yellow]" if rtt < 150.0 else f"[red]{rtt:6.1f}[/red]"
                )
            )
        if uptime is None:
            uptime_text = "[dim]-[/dim]"
        else:
            uptime_text = (
                f"[green]{uptime:5.1f}%[/green]" if uptime >= 99.0 else (
                    f"[yellow]{uptime:5.1f}%[/yellow]" if uptime >= 95.0 else f"[red]{uptime:5.1f}%[/red]"
                )
            )

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