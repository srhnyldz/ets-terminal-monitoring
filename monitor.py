#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import socket
import time
import subprocess
import re
import sys
import argparse
import select
import termios
import tty
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Type

from ping3 import ping
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box
from ets_tm.core import ping_host as core_ping_host, check_port as core_check_port
from ets_tm.ui import build_table as ui_build_table
import ets_tm.app_io as app_io

console = Console()

# ------- Sabitler ------- #

APP_NAME = "ETS Terminal Monitoring"
APP_URL = "www.etsteknoloji.com.tr"
APP_VERSION = "2.1.4"

class AppState:
    def __init__(self) -> None:
        self.last_action_note: str = ""
        self.current_group_filter: Optional[str] = None

app_state = AppState()

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = str(BASE_DIR / "servers.txt")
STATS_FILE = str(BASE_DIR / "server_stats.json")
LOG_FILE = str(BASE_DIR / "monitor.log")
SETTINGS_FILE = str(BASE_DIR / "config.json")
BACKUP_FILE = str(BASE_DIR / "servers.bak")

try:
    import pydantic  # type: ignore
    HAS_PYDANTIC = True
except Exception:
    HAS_PYDANTIC = False

# Domain models are validated lazily inside helper functions to avoid
# conditional base-class definitions at module scope.

def validate_server_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    if HAS_PYDANTIC:
        try:
            from pydantic import BaseModel as _BModel  # type: ignore
            class _ServerModel(_BModel):  # type: ignore[misc]
                group: Optional[str] = None
                name: str
                host: str
                service: str
                port: int

            m = _ServerModel(**d)  # type: ignore[arg-type]
            return dict(m.__dict__)
        except Exception:
            return d
    return d

def validate_settings_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    if HAS_PYDANTIC:
        try:
            from pydantic import BaseModel as _BModel  # type: ignore
            class _SettingsModel(_BModel):  # type: ignore[misc]
                refresh_interval: float = 2.0
                ping_timeout: float = 1.5
                port_timeout: float = 1.5
                live_fullscreen: bool = True
                refresh_per_second: int = 4
                prefer_system_ping: bool = False

            m = _SettingsModel(**d)  # type: ignore[arg-type]
            return dict(m.__dict__)
        except Exception:
            return d
    return d


SERVICE_CHOICES = {
    "1": ("HTTP", 80),
    "2": ("HTTPS", 443),
    "3": ("POP3", 110),
    "4": ("IMAP", 143),
    "5": ("SMTP", 25),
    "6": ("MySQL", 3306),
    "7": ("FTP", 21),
    "8": ("SSH", 22),
    "9": ("Custom Port", None),
}


# ------- Genel Yardımcılar ------- #

def print_header():
    console.print(f"\n[bold green]{APP_NAME} {t('app.version', version=APP_VERSION)}[/bold green]  -  [cyan]{APP_URL}[/cyan]\n")



def load_servers() -> List[Dict[str, Any]]:
    servers = app_io.load_servers(CONFIG_FILE, BACKUP_FILE, validate_server_dict)
    if not servers and os.path.exists(BACKUP_FILE):
        console.print(f"[yellow]{t('backup.restored')}[/yellow]")
    return servers


def save_servers(servers: List[Dict[str, Any]]) -> None:
    app_io.save_servers(CONFIG_FILE, BACKUP_FILE, servers)


def load_stats() -> Dict[str, Dict[str, int]]:
    return app_io.load_stats(STATS_FILE)


def save_stats(stats: Dict[str, Dict[str, int]]) -> None:
    app_io.save_stats(STATS_FILE, stats)

def load_settings() -> Dict[str, Any]:
    defaults = {
        "refresh_interval": 2.0,
        "ping_timeout": 1.5,
        "port_timeout": 1.5,
        "live_fullscreen": True,
        "refresh_per_second": 4,
        "prefer_system_ping": False,
    }
    return app_io.load_settings(SETTINGS_FILE, defaults, validate_settings_dict)

def save_settings(settings: Dict[str, Any]) -> None:
    app_io.save_settings(SETTINGS_FILE, settings, validate_settings_dict)

settings = load_settings()
REFRESH_INTERVAL = float(settings["refresh_interval"])
PING_TIMEOUT = float(settings["ping_timeout"])
PORT_TIMEOUT = float(settings["port_timeout"])
LIVE_FULLSCREEN = bool(settings["live_fullscreen"])
REFRESH_PER_SECOND = int(settings["refresh_per_second"])
PREFER_SYSTEM_PING = bool(settings["prefer_system_ping"])

LANG_DIR = str(BASE_DIR / "lang")
DEFAULT_LANG = "en"
EN_LANG: Dict[str, str] = {}
LANG: Dict[str, str] = {}

def load_language(code: str) -> Dict[str, str]:
    p = Path(LANG_DIR) / f"{code}.json"
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def set_language(code: str) -> None:
    global EN_LANG, LANG
    EN_LANG = load_language("en")
    LANG = load_language(code) if code and code != "en" else EN_LANG

def t(key: str, **kwargs) -> str:
    s = LANG.get(key, EN_LANG.get(key, key))
    try:
        return s.format(**kwargs)
    except Exception:
        return s


def server_key(srv: Dict[str, Any]) -> str:
    # Uptime istatistiği için anahtar
    return f"{srv.get('host','')}:{srv.get('port','')}:{srv.get('service','')}"


def ping_host(host: str) -> Optional[float]:
    return core_ping_host(host, timeout=PING_TIMEOUT, prefer_system_ping=PREFER_SYSTEM_PING)


def check_port(host: str, port: int, timeout: float = 1.5) -> bool:
    return core_check_port(host, port, timeout=timeout)


def update_and_get_uptime(stats: Dict[str, Dict[str, int]], key: str, is_up: bool) -> Optional[float]:
    s = stats.setdefault(key, {"ok": 0, "fail": 0})
    if is_up:
        s["ok"] += 1
    else:
        s["fail"] += 1

    total = s["ok"] + s["fail"]
    if total == 0:
        return None
    return (s["ok"] / total) * 100.0


def log_status(srv: Dict[str, Any], is_up: bool, rtt: Optional[float], uptime: Optional[float]) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    status_str = "UP" if is_up else "DOWN"
    ping_str = "-" if rtt is None else f"{rtt:.1f}"
    uptime_str = "-" if uptime is None else f"{uptime:.2f}"

    group_out = srv.get("group", "")
    if group_out == t('general.default_group'):
        group_out = "General"
    service_out = srv.get("service", "")
    if service_out == "Özel Port":
        service_out = "Custom Port"

    row = [
        ts,
        group_out,
        srv.get("name", ""),
        srv.get("host", ""),
        service_out,
        str(srv.get("port", "")),
        status_str,
        ping_str,
        uptime_str,
    ]
    app_io.append_log_row(LOG_FILE, row, ensure_header=True)

def ensure_log_header() -> None:
    app_io.ensure_log_header(LOG_FILE)


# ------- Tablo Oluşturma ------- #

def bootstrap() -> Dict[str, Any]:
    return {
        "t": lambda k, **kwargs: t(k, **kwargs),
        "state": app_state,
        "ping_host": ping_host,
        "check_port": lambda h, p, to: check_port(h, p, timeout=to),
        "port_timeout": PORT_TIMEOUT,
        "server_key": server_key,
        "update_and_get_uptime": update_and_get_uptime,
        "log_status": log_status,
        "app_name": APP_NAME,
        "app_url": APP_URL,
        "ui_build_table": ui_build_table,
    }

DEPS: Dict[str, Any] = {}

def build_table(servers: List[Dict[str, Any]], stats: Dict[str, Dict[str, int]]) -> Table:
    deps = DEPS or bootstrap()
    return deps["ui_build_table"](
        servers,
        stats,
        deps["t"],
        deps["state"],
        deps["ping_host"],
        deps["check_port"],
        deps["port_timeout"],
        deps["server_key"],
        deps["update_and_get_uptime"],
        deps["log_status"],
        deps["app_name"],
        deps["app_url"],
    )


# ------- Kullanıcı Etkileşimi: Ekle / Listele / Düzenle-Sil ------- #

def add_server_interactive():
    print_header()
    servers = load_servers()

    console.print(f"[bold cyan]{t('add.title')}[/bold cyan]\n")

    while True:
        name = input(t("add.input_name")).strip()
        if not name:
            console.print(f"[red]{t('error.name_required')}[/red]")
            continue

        host = input(t("add.input_host")).strip()
        if not host:
            console.print(f"[red]{t('error.host_required')}[/red]")
            continue

        group = input(t("add.input_group")).strip()
        if not group:
            group = "Genel"

        console.print(f"\n[bold]{t('add.select_service')}[/bold]")
        for key, (svc_name, default_port) in SERVICE_CHOICES.items():
            if default_port is not None:
                console.print(f"  {key}) {svc_name} (port {default_port})")
            else:
                console.print(f"  {key}) {svc_name}")

        choice = None
        while choice not in SERVICE_CHOICES:
            choice = input(t("add.input_service_choice")).strip()
            if choice not in SERVICE_CHOICES:
                console.print(f"[red]{t('error.choice_range')}[/red]")

        service_name, default_port = SERVICE_CHOICES[choice]

        if default_port is None:  # Özel Port
            while True:
                port_str = input(t("add.input_port")).strip()
                if not port_str.isdigit():
                    console.print(f"[red]{t('error.port_numeric')}[/red]")
                    continue
                port = int(port_str)
                if not (1 <= port <= 65535):
                    console.print(f"[red]{t('error.port_range')}[/red]")
                    continue
                break
        else:
            port = default_port

        server = {
            "name": name,
            "host": host,
            "group": group,
            "service": service_name,
            "port": port,
        }
        servers.append(server)
        save_servers(servers)

        console.print(f"[green]{t('add.added')}[/green] {name} ({host}:{port} - {service_name})\n")
        app_state.last_action_note = f"{t('note.added_server')} {name}"

        again = input(t("add.again")).strip().lower()
        if again not in ("e", "evet", "y", "yes", ""):
            break


def show_servers():
    print_header()
    servers = load_servers()
    if not servers:
        console.print("[yellow]Kayıtlı sunucu yok.[/yellow]\n")
        return

    console.print(f"[bold cyan]{t('list.title')}[/bold cyan]\n")
    for idx, srv in enumerate(servers, start=1):
        console.print(
            f"{idx:2d}) [white]{srv.get('name')}[/white] "
            f"({srv.get('host')} - {srv.get('service')}:{srv.get('port')}) "
            f"[dim][{srv.get('group', 'Genel')}][/dim]"
        )
    console.print("")


def edit_or_delete_server():
    print_header()
    servers = load_servers()
    if not servers:
        console.print(f"[yellow]{t('edit.no_servers')}[/yellow]\n")
        return

    console.print(f"[bold cyan]{t('edit.title')}[/bold cyan]\n")
    for idx, srv in enumerate(servers, start=1):
        console.print(
            f"{idx:2d}) [white]{srv.get('name')}[/white] "
            f"({srv.get('host')} - {srv.get('service')}:{srv.get('port')}) "
            f"[dim][{srv.get('group', 'Genel')}][/dim]"
        )

    choice = input(t("edit.select_index")).strip()
    if not choice:
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(servers)):
        console.print(f"[red]{t('error.index_range', max=len(servers))}[/red]")
        return

    idx = int(choice) - 1
    srv = servers[idx]
    old_key = server_key(srv)

    console.print(
        f"\n{t('edit.selected')}: [white]{srv.get('name')}[/white] "
        f"({srv.get('host')} - {srv.get('service')}:{srv.get('port')})\n"
    )
    console.print(f"1) {t('edit.option_edit')}")
    console.print(f"2) {t('edit.option_delete')}")
    console.print(f"3) {t('edit.option_cancel')}")

    action = input(t("menu.choice_prompt")).strip()

    if action == "2":
        confirm = input(t("edit.confirm_delete")).strip().lower()
        if confirm in ("e", "evet", "y", "yes", ""):
            deleted = servers.pop(idx)
            save_servers(servers)

            # İstatistikten de sil
            stats = load_stats()
            stats.pop(old_key, None)
            save_stats(stats)

            console.print(f"[green]{t('edit.deleted')}[/green] {deleted.get('name')}\n")
            app_state.last_action_note = f"{t('note.deleted_server')} {deleted.get('name')}"
        return

    if action != "1":
        return

    # --- Düzenleme --- #
    console.print(f"\n[bold cyan]{t('edit.editing_title')}[/bold cyan] {t('edit.editing_hint')}\n")

    new_name = input(t("edit.input_name_default", current=srv.get('name'))).strip()
    if new_name:
        srv["name"] = new_name

    new_host = input(t("edit.input_host_default", current=srv.get('host'))).strip()
    if new_host:
        srv["host"] = new_host

    new_group = input(t("edit.input_group_default", current=srv.get('group', t('general.default_group')))).strip()
    if new_group:
        srv["group"] = new_group

    change_service = input(
        t("edit.input_change_service", service=srv.get('service'), port=srv.get('port'))
    ).strip().lower()

    if change_service in ("e", "evet"):
        console.print(f"\n[bold]{t('edit.select_service')}[/bold]")
        for key, (svc_name, default_port) in SERVICE_CHOICES.items():
            if default_port is not None:
                console.print(f"  {key}) {svc_name} (port {default_port})")
            else:
                console.print(f"  {key}) {svc_name}")

        c = None
        while c not in SERVICE_CHOICES:
            c = input(t("add.input_service_choice")).strip()

        service_name, default_port = SERVICE_CHOICES[c]
        if default_port is None:
            while True:
                port_str = input(t("add.input_port")).strip()
                if not port_str.isdigit():
                    console.print(f"[red]{t('error.port_numeric')}[/red]")
                    continue
                port = int(port_str)
                if not (1 <= port <= 65535):
                    console.print(f"[red]{t('error.port_range')}[/red]")
                    continue
                break
        else:
            port = default_port

        srv["service"] = service_name
        srv["port"] = port

    # Kayıt et
    servers[idx] = srv
    save_servers(servers)

    # Servis/host/port değiştiyse eski uptime istatistiğini sıfırla
    new_key = server_key(srv)
    if new_key != old_key:
        stats = load_stats()
        stats.pop(old_key, None)
        save_stats(stats)

    console.print(f"[green]{t('edit.updated')}[/green]\n")
    app_state.last_action_note = f"{t('note.updated_server')} {srv.get('name')}"

def settings_menu():
    while True:
        print_header()
        s = load_settings()
        console.print(f"[bold cyan]{t('settings.title')}[/bold cyan]\n")
        console.print(f"1) {t('settings.refresh_interval')}: {s['refresh_interval']}")
        console.print(f"2) {t('settings.ping_timeout')}: {s['ping_timeout']}")
        console.print(f"3) {t('settings.port_timeout')}: {s['port_timeout']}")
        console.print(f"4) {t('settings.fullscreen')}: {t('general.on') if s['live_fullscreen'] else t('general.off')}")
        console.print(f"5) {t('settings.refresh_hz')}: {s['refresh_per_second']}")
        console.print(f"6) {t('settings.prefer_system_ping')}: {t('general.yes') if s['prefer_system_ping'] else t('general.no')}")
        console.print(f"7) {t('general.back')}")
        choice = input(t("menu.choice_prompt")).strip()
        if choice in ("7", "", None):
            return
        if choice == "1":
            val = input(t("settings.input_refresh_interval")).strip()
            try:
                v = float(val)
                if v <= 0:
                    console.print(f"[red]{t('general.gt_zero')}[/red]")
                    continue
                s["refresh_interval"] = v
                save_settings(s)
                global REFRESH_INTERVAL
                REFRESH_INTERVAL = v
                console.print(f"[green]{t('general.saved')}[/green]\n")
                app_state.last_action_note = t('note.settings_updated')
            except Exception:
                console.print(f"[red]{t('general.invalid_value')}[/red]")
        elif choice == "2":
            val = input(t("settings.input_ping_timeout")).strip()
            try:
                v = float(val)
                if v <= 0:
                    console.print(f"[red]{t('general.gt_zero')}[/red]")
                    continue
                s["ping_timeout"] = v
                save_settings(s)
                global PING_TIMEOUT
                PING_TIMEOUT = v
                console.print(f"[green]{t('general.saved')}[/green]\n")
                app_state.last_action_note = t('note.settings_updated')
            except Exception:
                console.print(f"[red]{t('general.invalid_value')}[/red]")
        elif choice == "3":
            val = input(t("settings.input_port_timeout")).strip()
            try:
                v = float(val)
                if v <= 0:
                    console.print(f"[red]{t('general.gt_zero')}[/red]")
                    continue
                s["port_timeout"] = v
                save_settings(s)
                global PORT_TIMEOUT
                PORT_TIMEOUT = v
                console.print(f"[green]{t('general.saved')}[/green]\n")
                app_state.last_action_note = t('note.settings_updated')
            except Exception:
                console.print(f"[red]{t('general.invalid_value')}[/red]")
        elif choice == "4":
            val = input(t("settings.input_fullscreen")).strip().lower()
            b = val in ("e", "evet", "", "yes", "y")
            s["live_fullscreen"] = b
            save_settings(s)
            global LIVE_FULLSCREEN
            LIVE_FULLSCREEN = b
            console.print(f"[green]{t('general.saved')}[/green]\n")
            app_state.last_action_note = t('note.settings_updated')
        elif choice == "5":
            val = input(t("settings.input_refresh_hz")).strip()
            try:
                v = int(val)
                if v <= 0:
                    console.print(f"[red]{t('general.gt_zero')}[/red]")
                    continue
                s["refresh_per_second"] = v
                save_settings(s)
                global REFRESH_PER_SECOND
                REFRESH_PER_SECOND = v
                console.print(f"[green]{t('general.saved')}[/green]\n")
                app_state.last_action_note = t('note.settings_updated')
            except Exception:
                console.print(f"[red]{t('general.invalid_value')}[/red]")
        elif choice == "6":
            val = input(t("settings.input_prefer_system_ping")).strip().lower()
            b = val in ("e", "evet", "", "yes", "y")
            s["prefer_system_ping"] = b
            save_settings(s)
            global PREFER_SYSTEM_PING
            PREFER_SYSTEM_PING = b
            console.print(f"[green]{t('general.saved')}[/green]\n")
            app_state.last_action_note = t('note.settings_updated')
        else:
            console.print(f"[red]{t('menu.invalid_choice')}[/red]")


# ------- İzleme ------- #

def monitor_servers():
    servers = load_servers()
    if not servers:
        print_header()
        console.print(f"[red]{t('monitor.no_servers')}[/red]\n")
        return

    print_header()
    console.print(f"[green]{t('monitor.starting')}[/green]")
    time.sleep(1)

    stats = load_stats()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        with Live(console=console, refresh_per_second=REFRESH_PER_SECOND, screen=LIVE_FULLSCREEN) as live:
            next_action = None
            next_refresh = time.time()
            while True:
                timeout = max(0.0, next_refresh - time.time())
                rlist, _, _ = select.select([sys.stdin], [], [], timeout)
                if rlist:
                    ch = sys.stdin.read(1)
                    if not ch:
                        continue
                    key = ch.lower()
                    if key == "q":
                        break
                    if key == "n":
                        next_action = "add"
                        break
                    if key == "s":
                        next_action = "settings"
                        break
                    if key == "l":
                        next_action = "list"
                        break
                    if key == "e":
                        next_action = "edit"
                        break
                    if key == "g":
                        next_action = "filter"
                        break
                    if key == "a":
                        next_action = "clear_filter"
                        break
                else:
                    servers = load_servers()
                    table = build_table(servers, stats)
                    live.update(table)
                    next_refresh = time.time() + REFRESH_INTERVAL
        # Restore cooked terminal before interactive prompts
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        termios.tcflush(fd, termios.TCIFLUSH)
        if next_action == "add":
            add_server_interactive()
            monitor_servers()
        elif next_action == "settings":
            settings_menu()
            monitor_servers()
        elif next_action == "list":
            show_servers()
            monitor_servers()
        elif next_action == "edit":
            edit_or_delete_server()
            monitor_servers()
        elif next_action == "filter":
            grp = input(t("filter.input_group")).strip()
            if grp:
                app_state.current_group_filter = grp
                app_state.last_action_note = f"{t('note.filter_set')} {grp}"
            monitor_servers()
        elif next_action == "clear_filter":
            app_state.current_group_filter = None
            app_state.last_action_note = t('note.filter_cleared')
            monitor_servers()
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        save_stats(stats)


# ------- İlk Çalıştırma Kontrolü & Menü ------- #

def first_run_check():
    servers = load_servers()
    if not servers:
        print_header()
        console.print(t('first_run.message'))
        add_server_interactive()


def main_menu():
    first_run_check()

    while True:
        print_header()
        console.print(f"[bold cyan]{t('menu.title')}[/bold cyan]")
        if 'menu.last_action' in EN_LANG and app_state.last_action_note:
            console.print(f"[dim]{t('menu.last_action')}: {app_state.last_action_note}[/dim]")
        console.print(f"1) {t('menu.start_monitoring')}")
        console.print(f"2) {t('menu.add_server')}")
        console.print(f"3) {t('menu.list_servers')}")
        console.print(f"4) {t('menu.edit_delete')}")
        console.print(f"5) {t('menu.settings')}")
        console.print(f"6) {t('menu.exit')}")

        choice = input(t("menu.choice_prompt")).strip()

        if choice == "1":
            monitor_servers()
        elif choice == "2":
            add_server_interactive()
        elif choice == "3":
            show_servers()
        elif choice == "4":
            edit_or_delete_server()
        elif choice == "5":
            settings_menu()
        elif choice == "6":
            console.print(f"[yellow]{t('menu.exiting')}[/yellow]")
            break
        else:
            console.print(f"[red]{t('menu.invalid_choice')}[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("pos_lang", nargs="?", help="language code like 'en' or 'tr'")
    parser.add_argument("--lang", dest="lang", help="language code like 'en' or 'tr'")
    parser.add_argument("--version", "-V", action="store_true", help="print version and exit")
    args = parser.parse_args()
    if args.version:
        print(f"{APP_NAME} v{APP_VERSION}")
        sys.exit(0)
    code = args.lang or args.pos_lang or DEFAULT_LANG
    set_language(code)
    DEPS = bootstrap()
    main_menu()