import os
import json
from typing import Any, Dict, List, Callable, Optional


def load_servers(path: str, backup_path: str, validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    servers: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return servers

    errors = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if validator:
                    obj = validator(obj)
                servers.append(obj)
            except json.JSONDecodeError:
                errors += 1
    if errors and not servers and os.path.exists(backup_path):
        try:
            with open(backup_path, "r", encoding="utf-8") as bf, open(path, "w", encoding="utf-8") as cf:
                cf.write(bf.read())
            with open(path, "r", encoding="utf-8") as f:
                servers = []
                for l in f:
                    l = l.strip()
                    if not l:
                        continue
                    try:
                        obj = json.loads(l)
                        if validator:
                            obj = validator(obj)
                        servers.append(obj)
                    except Exception:
                        pass
        except Exception:
            pass
    return servers


def save_servers(path: str, backup_path: str, servers: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for srv in servers:
            f.write(json.dumps(srv, ensure_ascii=False) + "\n")
    try:
        with open(backup_path, "w", encoding="utf-8") as f:
            for srv in servers:
                f.write(json.dumps(srv, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load_stats(path: str) -> Dict[str, Dict[str, int]]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_stats(path: str, stats: Dict[str, Dict[str, int]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def load_settings(path: str, defaults: Dict[str, Any], validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> Dict[str, Any]:
    if not os.path.exists(path):
        save_settings(path, defaults, validator)
        return defaults.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if validator:
                data = validator(data)
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        save_settings(path, defaults, validator)
        return defaults.copy()


def save_settings(path: str, settings: Dict[str, Any], validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> None:
    payload = validator(settings) if validator else settings
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def ensure_log_header(path: str) -> None:
    header = "date;group;name;host;service;port;status;ping;uptime\n"
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            first = f.readline()
        if not first.startswith("date;"):
            with open(path, "r+", encoding="utf-8") as f:
                content = f.read()
                f.seek(0)
                f.write(header)
                f.write(content)
    except Exception:
        pass


def append_log_line(path: str, line: str, ensure_header: bool = True) -> None:
    if ensure_header:
        ensure_log_header(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)