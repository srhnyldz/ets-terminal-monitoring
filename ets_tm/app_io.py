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
from datetime import datetime, timezone
import tempfile
import shutil


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


def save_servers(path: str, backup_path: str, servers: List[Dict[str, Any]], validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> None:
    payload = [validator(s) if validator else s for s in servers]
    content = "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in payload)
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


def read_log_summary(path: str, max_backups: int = 3, now_ts: Optional[float] = None) -> Dict[str, Dict[str, Optional[float]]]:
    files = [path] + [f"{path}.{i}" for i in range(1, max_backups + 1)]
    now = datetime.fromtimestamp(now_ts, tz=timezone.utc) if now_ts else datetime.now(tz=timezone.utc)
    def _init_bucket():
        return {
            "up": 0,
            "down": 0,
            "avg_ping": None,
            "uptime": None,
        }
    one_h = _init_bucket()
    day = _init_bucket()

    def _acc(bucket: Dict[str, Optional[float]], status: str, ping_val: Optional[float]):
        if status == "UP":
            bucket["up"] = int(bucket.get("up", 0)) + 1
        elif status == "DOWN":
            bucket["down"] = int(bucket.get("down", 0)) + 1
        # avg ping
        count_key = "_ping_count"
        sum_key = "_ping_sum"
        c = int(bucket.get(count_key, 0))
        s = float(bucket.get(sum_key, 0.0))
        if ping_val is not None:
            c += 1
            s += ping_val
        bucket[count_key] = c
        bucket[sum_key] = s

    for fp in files:
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("date;"):
                        continue
                    parts = line.split(";")
                    if len(parts) < 8:
                        continue
                    dt_str = parts[0]
                    status = parts[6]
                    ping_str = parts[7]
                    try:
                        dt = datetime.fromisoformat(dt_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        continue
                    age = (now - dt).total_seconds()
                    ping_val = None
                    try:
                        if ping_str and ping_str != "-":
                            ping_val = float(ping_str)
                    except Exception:
                        ping_val = None
                    if age <= 3600:
                        _acc(one_h, status, ping_val)
                    if age <= 86400:
                        _acc(day, status, ping_val)
        except Exception:
            continue

    def _finalize(bucket: Dict[str, Optional[float]]):
        up = int(bucket.get("up", 0))
        down = int(bucket.get("down", 0))
        total = up + down
        if total > 0:
            bucket["uptime"] = (up / total) * 100.0
        else:
            bucket["uptime"] = None
        c = int(bucket.get("_ping_count", 0))
        s = float(bucket.get("_ping_sum", 0.0))
        bucket["avg_ping"] = (s / c) if c > 0 else None
        bucket.pop("_ping_count", None)
        bucket.pop("_ping_sum", None)

    _finalize(one_h)
    _finalize(day)
    return {
        "1h": one_h,
        "24h": day,
    }


def export_servers_json(path: str, servers: List[Dict[str, Any]]) -> None:
    content = json.dumps(servers, ensure_ascii=False, indent=2)
    _atomic_write_text(path, content)


def export_servers_csv(path: str, servers: List[Dict[str, Any]]) -> None:
    header = ["name","host","group","service","port"]
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(header)
    for s in servers:
        writer.writerow([
            s.get("name",""),
            s.get("host",""),
            s.get("group",""),
            s.get("service",""),
            int(s.get("port",0)) or 0,
        ])
    _atomic_write_text(path, buf.getvalue())


def import_servers_json(path: str, validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
        out: List[Dict[str, Any]] = []
        for obj in data:
            if not isinstance(obj, dict):
                continue
            out.append(validator(obj) if validator else obj)
        return out
    except Exception:
        # line-delimited JSON fallback
        res: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        res.append(validator(obj) if validator else obj)
                    except Exception:
                        pass
        except Exception:
            return []
        return res


def import_servers_csv(path: str, validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f, delimiter=","))
        if not rows:
            return []
        header = [c.strip().lower() for c in rows[0]]
        idx = {name: i for i, name in enumerate(header)}
        out: List[Dict[str, Any]] = []
        for r in rows[1:]:
            def _get(k):
                j = idx.get(k)
                return r[j].strip() if j is not None and j < len(r) else ""
            obj: Dict[str, Any] = {
                "name": _get("name"),
                "host": _get("host"),
                "group": _get("group"),
                "service": _get("service") or "Custom Port",
                "port": int(_get("port") or "0") or 0,
            }
            out.append(validator(obj) if validator else obj)
        return out
    except Exception:
        return []


def ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def incremental_backup(src_path: str, backups_dir: str, prefix: str = "servers", ts_format: str = "%Y%m%d-%H%M%S", max_count: int = 100) -> Optional[str]:
    if not os.path.exists(src_path):
        return None
    ensure_dir(backups_dir)
    ts = datetime.now().strftime(ts_format)
    name = f"{prefix}-{ts}.txt"
    dst = os.path.join(backups_dir, name)
    try:
        shutil.copyfile(src_path, dst)
    except Exception:
        return None
    try:
        files = sorted([f for f in os.listdir(backups_dir) if f.startswith(prefix + "-") and f.endswith(".txt")])
        while len(files) > max_count:
            oldest = files.pop(0)
            try:
                os.unlink(os.path.join(backups_dir, oldest))
            except Exception:
                break
    except Exception:
        pass
    return dst


def find_latest_backup(backups_dir: str, prefix: str = "servers") -> Optional[str]:
    try:
        files = [f for f in os.listdir(backups_dir) if f.startswith(prefix + "-") and f.endswith(".txt")]
        if not files:
            return None
        files.sort()
        return os.path.join(backups_dir, files[-1])
    except Exception:
        return None


def restore_file_from_backup(target_path: str, backup_file: str) -> bool:
    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            content = f.read()
        _atomic_write_text(target_path, content)
        return True
    except Exception:
        return False