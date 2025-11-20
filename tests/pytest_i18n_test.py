import importlib


def _reload_monitor():
    import monitor
    importlib.reload(monitor)
    return monitor


def test_t_en_menu_title():
    m = _reload_monitor()
    m.set_language("en")
    assert m.t("menu.title") == "=== Main Menu ==="


def test_t_tr_menu_title():
    m = _reload_monitor()
    m.set_language("tr")
    assert m.t("menu.title") == "=== Ana Menü ==="


def test_t_fallback_key():
    m = _reload_monitor()
    m.set_language("en")
    assert m.t("nonexistent.key") == "nonexistent.key"