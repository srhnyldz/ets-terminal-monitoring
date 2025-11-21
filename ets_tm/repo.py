from typing import Any, Dict, List, Optional, Callable
from . import app_io


class FileRepository:
    def __init__(
        self,
        servers_path: str,
        backup_path: str,
        stats_path: str,
        settings_path: str,
        server_validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        settings_validator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self.servers_path = servers_path
        self.backup_path = backup_path
        self.stats_path = stats_path
        self.settings_path = settings_path
        self.server_validator = server_validator
        self.settings_validator = settings_validator

    def get_servers(self) -> List[Dict[str, Any]]:
        return app_io.load_servers(self.servers_path, self.backup_path, self.server_validator)

    def save_servers(self, servers: List[Dict[str, Any]]) -> None:
        app_io.save_servers(self.servers_path, self.backup_path, servers, self.server_validator)

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        return app_io.load_stats(self.stats_path)

    def save_stats(self, stats: Dict[str, Dict[str, int]]) -> None:
        app_io.save_stats(self.stats_path, stats)

    def get_settings(self, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        defaults = defaults or {}
        return app_io.load_settings(self.settings_path, defaults, self.settings_validator)

    def save_settings(self, settings: Dict[str, Any]) -> None:
        app_io.save_settings(self.settings_path, settings, self.settings_validator)