import os
import json
import logging
import csv
import io
import time
try:
    import fcntl  # type: ignore
    HAS_FCNTL = True
except Exception:
    HAS_FCNTL = False
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Callable, Optional
import tempfile


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


def _atomic_write_text(path: str, text: str) -> None:
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def save_servers(path: str, backup_path: str, servers: List[Dict[str, Any]]) -> None:
    content = "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in servers)
    _atomic_write_text(path, content)
    try:
        _atomic_write_text(backup_path, content)
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
    _atomic_write_text(path, json.dumps(stats, ensure_ascii=False, indent=2))


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
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


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


_LOGGERS: Dict[str, logging.Logger] = {}


def get_logger(path: str, max_bytes: int = 1048576, backup_count: int = 3) -> logging.Logger:
    logger = _LOGGERS.get(path)
    if logger:
        return logger
    logger = logging.getLogger(f"ets_tm.log.{path}")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    _LOGGERS[path] = logger
    return logger


def _acquire_lock(path: str):
    lock_path = path + ".lock"
    if HAS_FCNTL:
        f = open(lock_path, "w")
        fcntl.flock(f, fcntl.LOCK_EX)
        return ("fcntl", f, lock_path)
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            return ("excl", fd, lock_path)
        except FileExistsError:
            time.sleep(0.05)


def _release_lock(tok) -> None:
    kind, obj, lock_path = tok
    if kind == "fcntl":
        try:
            fcntl.flock(obj, fcntl.LOCK_UN)
        finally:
            obj.close()
    else:
        try:
            os.close(obj)
        finally:
            try:
                os.unlink(lock_path)
            except Exception:
                pass


def append_log_line(path: str, line: str, ensure_header: bool = True) -> None:
    tok = _acquire_lock(path)
    try:
        if ensure_header:
            ensure_log_header(path)
        logger = get_logger(path)
        if line.endswith("\n"):
            line = line[:-1]
        logger.info(line)
    finally:
        _release_lock(tok)


def append_log_row(path: str, row: List[str], ensure_header: bool = True) -> None:
    tok = _acquire_lock(path)
    try:
        if ensure_header:
            ensure_log_header(path)
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(row)
        line = buf.getvalue().rstrip("\n")
        logger = get_logger(path)
        logger.info(line)
    finally:
        _release_lock(tok)