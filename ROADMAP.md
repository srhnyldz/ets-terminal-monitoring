# /Users/serhanyildiz/development-script/ets-terminal-monitoring/ROADMAP.md

# ETS Terminal Monitoring — Roadmap

Amaçlar
- Kullanıcı deneyimi, güvenilirlik ve bakım kolaylığını artırmak
- Üretim ortamına uygun kalite standartları, test ve otomasyon

Sürüm Planı (Daha İnce Parçalar)

v2.0.0 — AppState ve Geçiş İskeleti
- Global durumun `AppState`e taşınması (uygulama çalışır durumda kalır)
- Eski fonksiyonlar için geçici adapter katmanı

v2.0.1 — Domain Katmanı
- `Server`, `Settings` modelleri (pydantic ile)
- Eski kullanım için dönüştürücüler (uygulama çalışır)

v2.0.2 — IO Katmanı
- Dosya I/O ve log operasyonlarının `io` modülüne taşınması
- `ensure_log_header` ve `log_status` adaptasyonu

v2.0.3 — Core Katmanı
- `ping_host`, `check_port` çekirdeğe taşınması
- Hata ve timeout politikaları için arayüzler

v2.0.4 — UI Katmanı
- Terminal UI fonksiyonlarının `ui` modülüne ayrılması
- `build_table` ve menü akışlarının injection ile bağlanması

v2.0.5 — Bağımlılık Enjeksiyonu
- Modüller arası gevşek bağ ve wiring
- Minimal bootstrapping; uygulama çalışır

v2.0.6 — Test ve Paket Organizasyonu
- Modül test kapsamı; temel entegrasyon testleri
- Paket dizin yapısı ve import yollarının temizlenmesi

v2.0.7 — Doküman ve Göç
- Göç kılavuzu ve refaktör dokümantasyonu
- CHANGELOG güncellemeleri

v2.1.x — Kalite Temeli ve Log Altyapısı (küçük adımlar)
- v2.1.0: Pre-commit yapılandırması (`black`, `ruff`) ve temel kurallar
- v2.1.1: Statik tip analizi (`mypy`) ve ilk tip düzeltmeleri
- v2.1.2: Python `logging` entegrasyonu, `RotatingFileHandler` ile rotasyon
- v2.1.3: Log yazımı için `csv` modülü kullanımı ve alan doğrulama
- v2.1.4: Atomik dosya yazımı (temp + `os.replace`), hata kurtarma
- v2.1.5: Dosya kilidi (lock) eklenmesi; yarış koşullarını engelleme
- v2.1.6: `pydantic` modelleri (Server, Settings) ve şema doğrulama
- v2.1.7: `pytest` iskeleti ve ilk birim testleri (ping/port, i18n)
- v2.1.8: CLI bayrakları (`--add`, `--list`, `--edit`, `--group-filter`, `--clear-filter`)
- v2.1.9: İ18n eksik alanların tamamlama ve servis adlarının i18n görünümü
- v2.1.10: Doküman güncellemeleri (README kısa notlar, CHANGELOG sürümler)

v2.2.x — Performans ve İzleme İyileştirmeleri
- v2.2.0: `asyncio` ile ping/port kontrollerinde eşzamanlılık
- v2.2.1: Rate limiting; yoğun sorgulamalarda kısıtlama
- v2.2.2: Backoff/retry politikaları; geçici hatalarda toparlanma
- v2.2.3: Tablo sayfalama; büyük listelerde gezinme
- v2.2.4: Tablo sıralama; sütun bazlı sort
- v2.2.5: Özet metrikler (1h/24h up/down, avg ping, uptime %)

v2.3.x — Veri Yönetimi ve Göç
- v2.3.0: Sunucu listesinin JSON/CSV import/export komutları
- v2.3.1: Artımlı yedekleme; geri yükleme komutu
- v2.3.2: Log migrasyon aracı; Türkçe başlığı İngilizceye otomatik çevirme

v2.4.x — Paketleme ve Dağıtım
- v2.4.0: `pyproject.toml` ve wheel paketleme
- v2.4.1: PyPI yayın ve kurulum yönergeleri
- v2.4.2: Docker imajı (alpine) ve basit çalıştırma komutu
- v2.4.3: Non-interactive CLI modları; otomasyon dostu akış

v2.5.x — CI/CD ve Sürüm Otomasyonu
- v2.5.0: GitHub Actions — lint+test pipeline
- v2.5.1: Build ve paket artifact’larının otomatik üretimi
- v2.5.2: Release otomasyonu — versiyon artırma, tag ve yayın

v2.6.x — Güvenlik Sertleştirme
- v2.6.0: Hostname/IP ve port girdi doğrulamaları
- v2.6.1: `ping` fallback güvenli parametre kontrolü
- v2.6.2: Dosya izinleri ve gizlilik (config/log)

v2.7.x — UX ve İ18n Geliştirmeleri
- v2.7.0: Rich tema iyileştirmeleri
- v2.7.1: Tablo arama ve gelişmiş filtreleme
- v2.7.2: Grup yönetimi menüsü ve toplu işlemler
- v2.7.3: Yeni dil ekleme süreci ve kılavuzu

v2.8.0 — Plugin Mimarisi
- Servis kontrol eklentileri altyapısı
- Genişletilebilir servis kayıt/keşif sistemi

Riskler ve Bağımlılıklar
- OS bağımlılıkları: Sistem `ping` erişimi ve izinleri
- Performans: `asyncio` paralelleştirme ile dosya I/O ve log yazım koordinasyonu
- Paketleme: PyPI yayın süreçleri ve isim çatışmaları

Başarı Kriterleri
- Tüm sürümlerde `pytest` yeşil, `ruff`/`black` temiz, `mypy` hatasız
- Loglar İngilizce başlık ve alanlarla standardize
- Kullanıcı iş akışları CLI bayrakları ile menüsüz tamamlanabilir