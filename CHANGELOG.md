# Changelog

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