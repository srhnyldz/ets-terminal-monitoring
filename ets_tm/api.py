from typing import Any, Dict, List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .repo import FileRepository
from .services import MonitoringService
from . import app_io
from pydantic import BaseModel

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

class ServerModel(BaseModel):
    group: Optional[str] = None
    name: str
    host: str
    service: str
    port: int


class SettingsModel(BaseModel):
    refresh_interval: float
    ping_timeout: float
    port_timeout: float
    live_fullscreen: bool
    refresh_per_second: int
    prefer_system_ping: bool
    max_concurrent_checks: int
    retry_attempts: int
    retry_base_delay: float
    page_size: int


class StatsEntryModel(BaseModel):
    ok: int = 0
    fail: int = 0


class LogBucket(BaseModel):
    up: int
    down: int
    avg_ping: Optional[float] = None
    uptime: Optional[float] = None


class ServerCheckResult(BaseModel):
    rtt: Optional[float]
    port_open: bool


class VersionInfo(BaseModel):
    app: str
    version: str


def _validate_server(s: Dict[str, Any]) -> Dict[str, Any]:
    return ServerModel(**s).dict()


def _validate_settings(s: Dict[str, Any]) -> Dict[str, Any]:
    return SettingsModel(**s).dict()


repo = FileRepository(
    SERVERS_FILE,
    BACKUP_FILE,
    STATS_FILE,
    SETTINGS_FILE,
    server_validator=_validate_server,
    settings_validator=_validate_settings,
)

app = FastAPI(title="ETS Terminal Monitoring API", version="2.6.5")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/servers", response_model=List[ServerModel])
def list_servers() -> List[Dict[str, Any]]:
    return repo.get_servers()


@app.post("/servers", response_model=ServerModel)
def add_server(server: ServerModel) -> Dict[str, Any]:
    servers = repo.get_servers()
    servers.append(server.dict())
    repo.save_servers(servers)
    return server.dict()


@app.put("/servers/{index}", response_model=ServerModel)
def update_server(index: int, server: ServerModel) -> Dict[str, Any]:
    servers = repo.get_servers()
    if index < 0 or index >= len(servers):
        raise HTTPException(status_code=404, detail="not found")
    servers[index] = server.dict()
    repo.save_servers(servers)
    return servers[index]


@app.delete("/servers/{index}", response_model=ServerModel)
def delete_server(index: int) -> Dict[str, Any]:
    servers = repo.get_servers()
    if index < 0 or index >= len(servers):
        raise HTTPException(status_code=404, detail="not found")
    deleted = servers.pop(index)
    repo.save_servers(servers)
    return deleted


@app.get("/settings", response_model=SettingsModel)
def get_settings() -> Dict[str, Any]:
    return repo.get_settings(DEFAULTS)


@app.put("/settings", response_model=SettingsModel)
def set_settings(payload: SettingsModel) -> Dict[str, Any]:
    repo.save_settings(payload.dict())
    return repo.get_settings(DEFAULTS)


@app.get("/stats", response_model=Dict[str, StatsEntryModel])
def get_stats() -> Dict[str, Dict[str, int]]:
    return repo.get_stats()


@app.get("/logs/summary", response_model=Dict[str, LogBucket])
def get_log_summary() -> Dict[str, Dict[str, Optional[float]]]:
    return app_io.read_log_summary(LOG_FILE)


@app.get("/servers/{index}/check", response_model=ServerCheckResult)
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


@app.get("/version", response_model=VersionInfo)
def version() -> Dict[str, str]:
    return {"app": "ETS Terminal Monitoring API", "version": "2.6.5"}