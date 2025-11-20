# Changelog

## v2.4.0 — 2025-11-21

- Rich theme improvements in monitor table
  - Minimal double head border and subtle background
  - Bold cyan headers; zebra row styles; dim captions
  - Conditional coloring for ping and uptime cells

## v2.4.1 — 2025-11-21

- Table search and advanced filtering
  - `/` set search query across group/name/host/service, `x` clear
  - `h` set service filter, `z` clear service filter
  - Filter indicators shown in caption
- Version bumped to 2.4.1

## v2.4.2 — 2025-11-21

- Group management menu and bulk operations
  - List groups with counts; rename group
  - Delete group (removes its servers and their stats)
  - Bulk move servers between groups
- Version bumped to 2.4.2

## v2.3.2 — 2025-11-21

- Log migration tool to standardize headers
  - Migrate Turkish header to English in `monitor.log` and rotations
  - CLI: `--migrate-logs`
- Version bumped to 2.3.2

## v2.3.1 — 2025-11-21

- Incremental backups and restore commands
  - Create backups to directory: `--backup-servers [dir]`
  - Restore latest from directory: `--restore-servers-latest [dir]`
  - Restore from specific file: `--restore-servers <file>`
- Automatic incremental backup on every save (add/edit/delete)
- Version bumped to 2.3.1

## v2.3.0 — 2025-11-21

- Import/Export commands for server list
  - Export to JSON/CSV: `--export-json`, `--export-csv`
  - Import from JSON/CSV (replace list): `--import-json`, `--import-csv`
- Version bumped to 2.3.0

## v2.2.5 — 2025-11-21

- Summary metrics in monitor caption
  - 1h/24h windows: up/down counts, average ping, uptime %
  - Aligned two-line comparison for 1h vs 24h
  - Shortcuts moved to a new caption line for readability
- Version bumped to 2.2.5

## v2.2.4 — 2025-11-20

- Column-based sorting in table
- Shortcuts for sorting (<, >, r) and sort indicator in caption
- Version bumped to 2.2.4

## v2.2.3 — 2025-11-20

- Table pagination for large server lists
- Shortcuts for paging ([ and ]) and page indicator
- Configurable `page_size` setting
- Version bumped to 2.2.3

## v2.2.2 — 2025-11-20

- Backoff/retry policies for ping/port checks
- Configurable via settings (`retry_attempts`, `retry_base_delay`)
- Version bumped to 2.2.2

## v2.2.1 — 2025-11-20

- Rate limiting for concurrent checks via `max_concurrent_checks` setting
- Settings menu supports configuring max concurrency
- Version bumped to 2.2.1

## v2.2.0 — 2025-11-20

- Concurrency using `asyncio` for ping/port checks in UI
- Faster updates while preserving existing behavior and logging
- Version bumped to 2.2.0

## v2.1.10 — 2025-11-20

- Documentation updates
  - README: added concise Quick Notes (EN/TR)
  - CHANGELOG: ensured newest version at the top
- Version bumped to 2.1.10

## v2.1.9 — 2025-11-20

- Internationalization improvements
  - Localized service names in UI table and menus
  - Added service translation keys in `lang/en.json` and `lang/tr.json`
- Kept logs standardized in English
- Version bumped to 2.1.9

## v2.1.7 — 2025-11-20

- Added PyTest skeleton with initial tests
  - Core: `PingPolicy.parse_rtt` and `PortPolicy.is_open` via monkeypatch
  - I18n: `t()` with `set_language('en'/'tr')` and fallback behavior
- Documentation updates to include PyTest usage instructions
- Version bumped to 2.1.7

## v2.1.6 — 2025-11-20

- Enabled optional schema validation using `pydantic` for Server and Settings
- Applied validation during load and save (servers persisted via validated payloads)
- Kept `pydantic` optional; app runs without it
- Version bumped to 2.1.6

## v2.1.5 — 2025-11-20

- Added file locking to prevent race conditions during writes
- Locks applied to log appends and atomic saves
- Cross-platform fallback when `fcntl` is unavailable
- Version bumped to 2.1.5

## v2.1.4 — 2025-11-20

- Implemented atomic file writes using temp + `os.replace`
- Applies to servers, stats, and settings save operations
- Basic recovery: original files preserved on write failure
- Version bumped to 2.1.4

## v2.1.3 — 2025-11-20

- Switched log writing to Python `csv` module with field normalization
- `log_status` now emits rows via `append_log_row`
- Rotation preserved through logger integration
- Version bumped to 2.1.3

## v2.1.2 — 2025-11-20

- Integrated Python `logging` with `RotatingFileHandler` for `monitor.log`
- `append_log_line` now writes via logger with rotation
- Ensured header handling remains intact
- Version bumped to 2.1.2

## v2.1.1 — 2025-11-20

- Added static type analysis setup via `mypy` (`mypy.ini`)
- Integrated `mypy` into pre-commit hooks
- Initial type cleanups and annotations retained
- Version bumped to 2.1.1

## v2.1.0 — 2025-11-20

- Added pre-commit configuration with `black` and `ruff`
- Documented setup and usage in README Development section
- Version bumped to 2.1.0

## v2.0.7 — 2025-11-20

- Documentation updates and migration guidance in README
- Confirmed refactor notes and package paths
- Version bumped to 2.0.7

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
