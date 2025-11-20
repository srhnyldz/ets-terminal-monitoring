import pytest
from ets_tm.core import PingPolicy, PortPolicy
import ets_tm.core as core_mod


def test_parse_rtt_valid():
    pol = PingPolicy()
    out = "64 bytes from 8.8.8.8: icmp_seq=0 ttl=57 time=23.4 ms"
    assert pol.parse_rtt(out) == pytest.approx(23.4, rel=0.01)


def test_parse_rtt_invalid():
    pol = PingPolicy()
    out = "no time here"
    assert pol.parse_rtt(out) is None


class _DummyConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_port_is_open_true(monkeypatch):
    monkeypatch.setattr(core_mod, "socket", core_mod.socket)

    def _fake_create_connection(addr, timeout):
        return _DummyConn()

    monkeypatch.setattr(core_mod.socket, "create_connection", _fake_create_connection)
    pol = PortPolicy()
    assert pol.is_open("example.com", 80, 0.1) is True


def test_port_is_open_false(monkeypatch):
    monkeypatch.setattr(core_mod, "socket", core_mod.socket)

    def _raise_os_error(addr, timeout):
        raise OSError("connection failed")

    monkeypatch.setattr(core_mod.socket, "create_connection", _raise_os_error)
    pol = PortPolicy()
    assert pol.is_open("example.com", 80, 0.1) is False