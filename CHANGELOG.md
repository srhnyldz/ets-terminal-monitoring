# Changelog

## v2.0.6 — 2025-11-20

- Established basic tests using `unittest` (`tests/`)
- Created package directory `ets_tm` and cleaned import paths
- Verified IO/UI/Core via unit tests and discovery
- Version bumped to 2.0.6

## v2.0.5 — 2025-11-20

- Introduced minimal dependency injection (wiring) via `bootstrap()`
- `monitor.py` resolves UI/core/IO via injected dependencies
- Keeps loose coupling across modules; app remains functional
- Version bumped to 2.0.5

## v2.0.4 — 2025-11-20

- Moved terminal UI to `ui.py` module
- `build_table` injected with core and IO dependencies
- Menu flows hooked via handler injection (preparation)
- Version bumped to 2.0.4

## v2.0.3 — 2025-11-20

- Moved core functions to `core.py`: `ping_host`, `check_port`
- Introduced simple policy interfaces: `PingPolicy`, `PortPolicy`
- `monitor.py` uses core abstractions; functionality preserved
- Version bumped to 2.0.3

## v2.0.2 — 2025-11-20

- Moved file I/O and logging to `app_io.py` module
- Adapted `monitor.py` to use IO abstractions
- Ensured log header handling via IO layer
- Version bumped to 2.0.2

## v2.0.1 — 2025-11-20

- Optional domain models with validation: `ServerModel`, `SettingsModel`
- Adapters integrated into load/save without breaking dict usage
- Application remains functional

## v2.0.0 — 2025-11-20

- Introduced `AppState` and removed global state usage
- Prepared transition skeleton while keeping the app functional
- Version bumped to 2.0.0

## v1.1.0 — 2025-11-20

- Group filter in monitor view with shortcuts (`g` to set, `a` to clear)
- Last action note shown in main menu
- Log file header added (`date;group;name;host;service;port;status;ping;uptime`)
- Improved input validation messages (choices and port range)
- Automatic restore from `servers.bak` if `servers.txt` is corrupted
- Version bumped to 1.1.0

## v1.0 — 2025-11-20

- Initial public release
- Live monitoring table with color status and uptime
- Ping via `ping3` with automatic fallback to system `ping`
- Persistent settings in `config.json`
- Settings menu to edit refresh interval, ping/port timeouts, fullscreen, refresh rate, system ping preference
- Keyboard shortcuts in monitor view: `q` quit, `n` add server, `s` settings, `l` list servers, `e` edit/delete server
- Multi-language support (English default, Turkish selectable via `--lang tr` or positional `tr`)
- All runtime files stored relative to application directory
- Version reporting via `--version`