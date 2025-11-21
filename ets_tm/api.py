from typing import Any, Dict, List, Optional
from pathlib import Path
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .repo import FileRepository
from .services import MonitoringService
from . import app_io

BASE_DIR = Path(__file__).resolve().parent.parent
SERVERS_FILE = str(BASE_DIR / "servers.txt")
BACKUP_FILE = str(BASE_DIR / "servers.bak")
STATS_FILE = str(BASE_DIR / "server_stats.json")
SETTINGS_FILE = str(BASE_DIR / "config.json")
LOG_FILE = str(BASE_DIR / "monitor.log")

DEFAULTS = {
    "refresh_interval": 2.0,
    "ping_timeout": 1.5,
    "port_timeout": 1.5,
    "live_fullscreen": True,
    "refresh_per_second": 4,
    "prefer_system_ping": False,
    "max_concurrent_checks": 20,
    "page_size": 20,
    "retry_attempts": 3,
    "retry_base_delay": 0.2,
}

repo = FileRepository(
    SERVERS_FILE,
    BACKUP_FILE,
    STATS_FILE,
    SETTINGS_FILE,
)

app = FastAPI(title="ETS Terminal Monitoring API", version="2.6.2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/servers")
def list_servers() -> List[Dict[str, Any]]:
    return repo.get_servers()


@app.post("/servers")
def add_server(server: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    servers = repo.get_servers()
    servers.append(server)
    repo.save_servers(servers)
    return server


@app.put("/servers/{index}")
def update_server(index: int, server: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    servers = repo.get_servers()
    if index < 0 or index >= len(servers):
        raise HTTPException(status_code=404, detail="not found")
    servers[index] = server
    repo.save_servers(servers)
    return server


@app.delete("/servers/{index}")
def delete_server(index: int) -> Dict[str, Any]:
    servers = repo.get_servers()
    if index < 0 or index >= len(servers):
        raise HTTPException(status_code=404, detail="not found")
    deleted = servers.pop(index)
    repo.save_servers(servers)
    return deleted


@app.get("/settings")
def get_settings() -> Dict[str, Any]:
    return repo.get_settings(DEFAULTS)


@app.put("/settings")
def set_settings(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    repo.save_settings(payload)
    return repo.get_settings(DEFAULTS)


@app.get("/stats")
def get_stats() -> Dict[str, Dict[str, int]]:
    return repo.get_stats()


@app.get("/logs/summary")
def get_log_summary() -> Dict[str, Dict[str, Optional[float]]]:
    return app_io.read_log_summary(LOG_FILE)


@app.get("/servers/{index}/check")
def check_server(index: int) -> Dict[str, Any]:
    servers = repo.get_servers()
    if index < 0 or index >= len(servers):
        raise HTTPException(status_code=404, detail="not found")
    s = repo.get_settings(DEFAULTS)
    svc = MonitoringService(
        float(s.get("ping_timeout", 1.5)),
        float(s.get("port_timeout", 1.5)),
        bool(s.get("prefer_system_ping", False)),
    )
    rtt, is_open = svc.evaluate(servers[index])
    return {"rtt": rtt, "port_open": is_open}