from typing import TypedDict, Optional, Dict, Any


class Server(TypedDict, total=False):
    group: Optional[str]
    name: str
    host: str
    service: str
    port: int


class Settings(TypedDict, total=False):
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


class StatsEntry(TypedDict, total=False):
    ok: int
    fail: int


Stats = Dict[str, StatsEntry]