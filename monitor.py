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
from typing import Optional, List, Dict, Any

from ping3 import ping
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box

console = Console()

# ------- Sabitler ------- #

APP_NAME = "ETS Terminal Monitoring"
APP_URL = "www.etsteknoloji.com.tr"
APP_VERSION = "1.0"

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = str(BASE_DIR / "servers.txt")
STATS_FILE = str(BASE_DIR / "server_stats.json")
LOG_FILE = str(BASE_DIR / "monitor.log")
SETTINGS_FILE = str(BASE_DIR / "config.json")


SERVICE_CHOICES = {
    "1": ("HTTP", 80),
    "2": ("HTTPS", 443),
    "3": ("POP3", 110),
    "4": ("IMAP", 143),
    "5": ("SMTP", 25),
    "6": ("MySQL", 3306),
    "7": ("FTP", 21),
    "8": ("SSH", 22),
    "9": ("Özel Port", None),
}


# ------- Genel Yardımcılar ------- #

def print_header():
    console.print(f"\n[bold green]{APP_NAME} {t('app.version', version=APP_VERSION)}[/bold green]  -  [cyan]{APP_URL}[/cyan]\n")


def load_servers() -> List[Dict[str, Any]]:
    servers: List[Dict[str, Any]] = []
    if not os.path.exists(CONFIG_FILE):
        return servers

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                servers.append(json.loads(line))
            except json.JSONDecodeError:
                console.print(f"[red]Uyarı:[/red] Geçersiz satır atlandı: {line}")
    return servers


def save_servers(servers: List[Dict[str, Any]]) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        for srv in servers:
            f.write(json.dumps(srv, ensure_ascii=False) + "\n")


def load_stats() -> Dict[str, Dict[str, int]]:
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_stats(stats: Dict[str, Dict[str, int]]) -> None:
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def load_settings() -> Dict[str, Any]:
    defaults = {
        "refresh_interval": 2.0,
        "ping_timeout": 1.5,
        "port_timeout": 1.5,
        "live_fullscreen": True,
        "refresh_per_second": 4,
        "prefer_system_ping": False,
    }
    if not os.path.exists(SETTINGS_FILE):
        save_settings(defaults)
        return defaults.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        save_settings(defaults)
        return defaults.copy()

def save_settings(settings: Dict[str, Any]) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

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
    if PREFER_SYSTEM_PING:
        try:
            proc = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=PING_TIMEOUT + 1)
            if proc.returncode == 0:
                out = proc.stdout or proc.stderr
                m = re.search(r"time[=<]\s*([\d\.]+)\s*ms", out)
                if m:
                    return float(m.group(1))
        except Exception:
            pass
    try:
        rtt = ping(host, timeout=PING_TIMEOUT, unit="ms", privileged=False)
        if rtt is not None:
            return float(rtt)
    except Exception:
        pass
    try:
        proc = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, timeout=PING_TIMEOUT + 1)
        if proc.returncode != 0:
            return None
        out = proc.stdout or proc.stderr
        m = re.search(r"time[=<]\s*([\d\.]+)\s*ms", out)
        if m:
            return float(m.group(1))
        return None
    except Exception:
        return None


def check_port(host: str, port: int, timeout: float = 1.5) -> bool:
    """TCP portuna bağlanmayı dener. Başarılıysa True, değilse False."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


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

    line = ";".join([
        ts,
        srv.get("group", ""),
        srv.get("name", ""),
        srv.get("host", ""),
        srv.get("service", ""),
        str(srv.get("port", "")),
        status_str,
        ping_str,
        uptime_str,
    ]) + "\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ------- Tablo Oluşturma ------- #

def build_table(servers: List[Dict[str, Any]], stats: Dict[str, Dict[str, int]]) -> Table:
    title = (
        f"{APP_NAME}  |  {APP_URL}  |  "
        f"Son Güncelleme: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

    table.caption = f"{t('shortcuts')}: q {t('shortcut.quit')}, n {t('shortcut.add')}, s {t('shortcut.settings')}, l {t('shortcut.list')}, e {t('shortcut.edit')}"

    for srv in servers:
        name = srv.get("name", "")
        host = srv.get("host", "")
        group = srv.get("group", "Genel")
        service = srv.get("service", "Bilinmiyor")
        port = int(srv.get("port", 0))

        rtt = ping_host(host)
        port_ok = check_port(host, port, timeout=PORT_TIMEOUT) if port > 0 else False
        is_up = port_ok

        key = server_key(srv)
        uptime = update_and_get_uptime(stats, key, is_up)
        log_status(srv, is_up, rtt, uptime)

        if is_up:
            status_text = t("status.online")
        else:
            status_text = t("status.offline")

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


# ------- Kullanıcı Etkileşimi: Ekle / Listele / Düzenle-Sil ------- #

def add_server_interactive():
    print_header()
    servers = load_servers()

    console.print("[bold cyan]Yeni sunucu ekleme[/bold cyan]\n")

    while True:
        name = input("Sunucu adı (ör. hds.forum): ").strip()
        if not name:
            console.print("[red]Ad boş olamaz.[/red]")
            continue

        host = input("Host / IP (ör. 10.10.1.1 veya domain): ").strip()
        if not host:
            console.print("[red]Host/IP boş olamaz.[/red]")
            continue

        group = input("Grup (Web, Cihazlar, DB vb. — boş bırakılırsa 'Genel'): ").strip()
        if not group:
            group = "Genel"

        console.print("\n[bold]Servis tipi seçin:[/bold]")
        for key, (svc_name, default_port) in SERVICE_CHOICES.items():
            if default_port is not None:
                console.print(f"  {key}) {svc_name} (port {default_port})")
            else:
                console.print(f"  {key}) {svc_name}")

        choice = None
        while choice not in SERVICE_CHOICES:
            choice = input("Seçim (1-9): ").strip()

        service_name, default_port = SERVICE_CHOICES[choice]

        if default_port is None:  # Özel Port
            while True:
                port_str = input("Port numarası: ").strip()
                if not port_str.isdigit():
                    console.print("[red]Geçersiz port.[/red]")
                    continue
                port = int(port_str)
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

        console.print(f"[green]Sunucu eklendi:[/green] {name} ({host}:{port} - {service_name})\n")

        again = input("Başka sunucu eklemek ister misiniz? (E/h): ").strip().lower()
        if again not in ("e", "evet", ""):
            break


def show_servers():
    print_header()
    servers = load_servers()
    if not servers:
        console.print("[yellow]Kayıtlı sunucu yok.[/yellow]\n")
        return

    console.print("[bold cyan]Kayıtlı sunucular:[/bold cyan]\n")
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
        console.print("[yellow]Düzenlenecek/silinecek sunucu yok.[/yellow]\n")
        return

    console.print("[bold cyan]Sunucu düzenle / sil[/bold cyan]\n")
    for idx, srv in enumerate(servers, start=1):
        console.print(
            f"{idx:2d}) [white]{srv.get('name')}[/white] "
            f"({srv.get('host')} - {srv.get('service')}:{srv.get('port')}) "
            f"[dim][{srv.get('group', 'Genel')}][/dim]"
        )

    choice = input("\nİşlem yapılacak sunucunun numarası (iptal için boş bırak): ").strip()
    if not choice:
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(servers)):
        console.print("[red]Geçersiz seçim.[/red]")
        return

    idx = int(choice) - 1
    srv = servers[idx]
    old_key = server_key(srv)

    console.print(
        f"\nSeçili: [white]{srv.get('name')}[/white] "
        f"({srv.get('host')} - {srv.get('service')}:{srv.get('port')})\n"
    )
    console.print("1) Düzenle")
    console.print("2) Sil")
    console.print("3) İptal")

    action = input("Seçiminiz: ").strip()

    if action == "2":
        confirm = input("Bu sunucuyu silmek istediğinize emin misiniz? (E/h): ").strip().lower()
        if confirm in ("e", "evet", ""):
            deleted = servers.pop(idx)
            save_servers(servers)

            # İstatistikten de sil
            stats = load_stats()
            stats.pop(old_key, None)
            save_stats(stats)

            console.print(f"[green]Silindi:[/green] {deleted.get('name')}\n")
        return

    if action != "1":
        return

    # --- Düzenleme --- #
    console.print("\n[bold cyan]Düzenleme[/bold cyan] (boş bırakırsanız mevcut değer kalır)\n")

    new_name = input(f"Ad [{srv.get('name')}]: ").strip()
    if new_name:
        srv["name"] = new_name

    new_host = input(f"Host/IP [{srv.get('host')}]: ").strip()
    if new_host:
        srv["host"] = new_host

    new_group = input(f"Grup [{srv.get('group', 'Genel')}]: ").strip()
    if new_group:
        srv["group"] = new_group

    change_service = input(
        f"Servis [{srv.get('service')}:{srv.get('port')}] değiştirilsin mi? (E/h): "
    ).strip().lower()

    if change_service in ("e", "evet"):
        console.print("\n[bold]Yeni servis tipi seçin:[/bold]")
        for key, (svc_name, default_port) in SERVICE_CHOICES.items():
            if default_port is not None:
                console.print(f"  {key}) {svc_name} (port {default_port})")
            else:
                console.print(f"  {key}) {svc_name}")

        c = None
        while c not in SERVICE_CHOICES:
            c = input("Seçim (1-9): ").strip()

        service_name, default_port = SERVICE_CHOICES[c]
        if default_port is None:
            while True:
                port_str = input("Port numarası: ").strip()
                if not port_str.isdigit():
                    console.print("[red]Geçersiz port.[/red]")
                    continue
                port = int(port_str)
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

    console.print("[green]Sunucu güncellendi.[/green]\n")

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
            except Exception:
                console.print(f"[red]{t('general.invalid_value')}[/red]")
        elif choice == "2":
            val = input(t("settings.input_ping_timeout")).strip()
            try:
                v = float(val)
                if v <= 0:
                    console.print("[red]Sıfırdan büyük bir değer girin.[/red]")
                    continue
                s["ping_timeout"] = v
                save_settings(s)
                global PING_TIMEOUT
                PING_TIMEOUT = v
                console.print(f"[green]{t('general.saved')}[/green]\n")
            except Exception:
                console.print(f"[red]{t('general.invalid_value')}[/red]")
        elif choice == "3":
            val = input(t("settings.input_port_timeout")).strip()
            try:
                v = float(val)
                if v <= 0:
                    console.print("[red]Sıfırdan büyük bir değer girin.[/red]")
                    continue
                s["port_timeout"] = v
                save_settings(s)
                global PORT_TIMEOUT
                PORT_TIMEOUT = v
                console.print(f"[green]{t('general.saved')}[/green]\n")
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
        else:
            console.print("[red]Geçersiz seçim.[/red]")


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
        console.print(
            "[bold yellow]İlk kez çalıştırılıyor gibi görünüyor.[/bold yellow]\n"
            "Henüz kayıtlı sunucu yok. Önce birkaç sunucu ekleyelim.\n"
        )
        add_server_interactive()


def main_menu():
    first_run_check()

    while True:
        print_header()
        console.print(f"[bold cyan]{t('menu.title')}[/bold cyan]")
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
    main_menu()