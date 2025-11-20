# ETS Terminal Monitoring

English

- Overview: A terminal-based server monitoring tool. Displays group, name, host/IP, service, port, ping RTT, uptime, and status with a live updating Rich table.
- Version: v2.1.9

Features

- Live monitoring table with color status and uptime
- Ping via `ping3` with automatic fallback to system `ping`
- Configurable refresh interval, timeouts, fullscreen, refresh rate, system ping preference
- Persistent settings in `config.json` and server list in `servers.txt`
- Optional schema validation for Server and Settings via `pydantic`
- Keyboard shortcuts in monitor view: `q` quit, `n` add, `s` settings, `l` list, `e` edit
- Multi-language (default English, Turkish via CLI)
- State managed via `AppState` (global state removed)
- I/O operations abstracted to `app_io.py` (logs, settings, servers, stats)
- Core functions moved to `core.py` (`ping_host`, `check_port`); simple policies
- Terminal UI functions moved to `ui.py`; `build_table` uses injected deps
- Minimal dependency injection and wiring via `bootstrap()` in the app
- Package modules under `ets_tm/` with cleaned imports
- Basic unit tests with `unittest` (`tests/`)
- PyTest skeleton with initial tests (ping/port, i18n)
- Python logging integration with rotation (`RotatingFileHandler`) for `monitor.log`
- Log rows written using Python `csv` module (standardized fields)
- Atomic file writes for save operations (temp + `os.replace`)
 - File locking for log appends and atomic saves (`*.lock`)
 - Migration notes: modules under `ets_tm/`, imports updated; CLI unchanged

Requirements

- Python 3.9+
- Packages: `rich`, `ping3`, `pydantic` (optional)

Installation

- Create virtual environment
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Install dependencies
  - `python -m pip install rich ping3 pydantic`

Usage

- Start app
  - `python monitor.py`
- Turkish language
  - `python monitor.py --lang tr` or `python monitor.py tr`
- Show version
  - `python monitor.py --version`
 - CLI flags
   - `python monitor.py --add` (add server flow)
   - `python monitor.py --list` (list saved servers)
   - `python monitor.py --edit` (edit/delete flow)
   - `python monitor.py --group-filter Web` (set group filter and start monitoring)
   - `python monitor.py --clear-filter` (clear group filter and start monitoring)

Settings

- Open: Main Menu → Settings or press `s` in monitor view
- Stored in `config.json` at project root
- Keys: `refresh_interval`, `ping_timeout`, `port_timeout`, `live_fullscreen`, `refresh_per_second`, `prefer_system_ping`
- Code references: `monitor.py:133-146` for settings I/O, `monitor.py:147-153` for runtime values

Shortcuts

- In monitor view: `q` quit, `n` add server, `s` settings, `l` list, `e` edit/delete
- Caption localized under the table

Internationalization

- Language files: `lang/en.json`, `lang/tr.json`
- Loader and translation function: `monitor.py:160-178`
- CLI language: `--lang tr` or positional `tr`: `monitor.py:768-795`

Data Files

- Servers list: `servers.txt` (one JSON per line)
- Stats: `server_stats.json`
- Logs: `monitor.log` (header: `date;group;name;host;service;port;status;ping;uptime`)
- Settings: `config.json`

Development

- Run with virtualenv active
- All runtime files are saved relative to the application directory: `monitor.py:40-45`
- Optional: enable pre-commit hooks (format/lint)
  - `python -m pip install pre-commit ruff black`
  - `pre-commit install`
  - `pre-commit run --all-files`
- Optional: run static type analysis (mypy)
  - `python -m pip install mypy`
- `mypy . --config-file mypy.ini`

- Optional: run PyTest
  - `python -m pip install pytest`
  - `python -m pytest -q`

Türkçe

- Genel Bakış: Terminal tabanlı izleme aracı. Grup, ad, host/IP, servis, port, ping RTT, uptime ve durum bilgilerini canlı tabloda gösterir.
- Sürüm: v2.1.9

Özellikler

- Renkli durum ve uptime ile canlı izleme tablosu
- `ping3` ile ping, başarısızsa sistem `ping` düşüşü
- Ayarlanabilir güncelleme sıklığı, zaman aşımı, tam ekran, yenileme hızı, sistem ping tercihi
- `config.json` ayarları ve `servers.txt` sunucu listesi kalıcı
- `pydantic` ile sunucu ve ayarlar için opsiyonel şema doğrulama
- İzleme ekranı kısayolları: `q` çıkış, `n` yeni, `s` ayarlar, `l` liste, `e` düzenle
- Çoklu dil (varsayılan İngilizce, CLI ile Türkçe)
- Durum yönetimi `AppState` ile, global durum kaldırıldı
- I/O işlemleri `app_io.py` modülüne taşındı (log, ayarlar, sunucular, istatistik)
- Çekirdek fonksiyonlar `core.py`’ye taşındı (`ping_host`, `check_port`); basit politikalar
- Terminal UI fonksiyonları `ui.py`’ye taşındı; `build_table` bağımlılık enjeksiyonu kullanır
- Uygulama içinde `bootstrap()` ile minimal bağımlılık enjeksiyonu ve wiring
- Modüller `ets_tm/` altında paketlendi; import yolları temizlendi
- Temel birim testleri `unittest` ile (`tests/`)
 - PyTest iskeleti ve ilk testler (ping/port, i18n)
- `monitor.log` için Python logging entegrasyonu ve rotasyon (`RotatingFileHandler`)
- Log satırları Python `csv` modülü ile yazılır (standardize alanlar)
- Kaydetme işlemlerinde atomik yazım (temp + `os.replace`)
 - Log eklemelerinde ve kaydetmelerde dosya kilidi (`*.lock`)
 - Göç notları: modüller `ets_tm/` altında, importlar güncel; CLI değişmedi

Gereksinimler

- Python 3.9+
- Paketler: `rich`, `ping3`, `pydantic` (opsiyonel)

Kurulum

- Sanal ortam oluştur
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Bağımlılıkları yükle
  - `python -m pip install rich ping3 pydantic`

Kullanım

- Uygulamayı başlat
  - `python monitor.py`
- Türkçe dil
  - `python monitor.py --lang tr` veya `python monitor.py tr`
- Sürümü göster
  - `python monitor.py --version`

- CLI bayrakları
  - `python monitor.py --add` (sunucu ekleme akışı)
  - `python monitor.py --list` (kayıtlı sunucuları listele)
  - `python monitor.py --edit` (düzenle/sil akışı)
  - `python monitor.py --group-filter Web` (grup filtresi ayarla ve izlemeyi başlat)
  - `python monitor.py --clear-filter` (grup filtresini temizle ve izlemeyi başlat)

Ayarlar

- Aç: Ana Menü → Ayarlar veya izleme ekranında `s`
- Proje kökünde `config.json` içinde saklanır
- Anahtarlar: `refresh_interval`, `ping_timeout`, `port_timeout`, `live_fullscreen`, `refresh_per_second`, `prefer_system_ping`
- Kod referansları: Ayar I/O `monitor.py:133-146`, çalışma değerleri `monitor.py:147-153`

Kısayollar

- İzleme ekranında: `q` çıkış, `n` yeni sunucu, `s` ayarlar, `l` liste, `e` düzenle/sil
- Tablo altında lokalize açıklama

Çoklu Dil

- Dil dosyaları: `lang/en.json`, `lang/tr.json`
- Yükleme ve çeviri fonksiyonu: `monitor.py:160-178`
- CLI dil: `--lang tr` veya konumsal `tr`: `monitor.py:768-795`

Veri Dosyaları

- Sunucular: `servers.txt` (satır başına JSON)
- İstatistik: `server_stats.json`
- Log: `monitor.log` (başlık: `date;group;name;host;service;port;status;ping;uptime`)
- Ayarlar: `config.json`

Geliştirme

- Sanal ortam aktifken çalıştırın
- Tüm çalışma dosyaları uygulama dizinine yazılır: `monitor.py:40-45`
- Opsiyonel: pre-commit kancalarını etkinleştir (format/lint)
  - `python -m pip install pre-commit ruff black`
  - `pre-commit install`
  - `pre-commit run --all-files`
- Opsiyonel: statik tip analizi (mypy)
  - `python -m pip install mypy`
  - `mypy . --config-file mypy.ini`