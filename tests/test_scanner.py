# tests/test_scanner.py
import pytest
from unittest.mock import patch
from core.scanner import ping_host, generate_ip_range


def test_generate_ip_range():
    ips = generate_ip_range("192.168.1.1", "192.168.1.5")
    assert ips == [
        "192.168.1.1", "192.168.1.2", "192.168.1.3",
        "192.168.1.4", "192.168.1.5"
    ]


def test_generate_ip_range_same():
    ips = generate_ip_range("10.0.0.1", "10.0.0.1")
    assert ips == ["10.0.0.1"]


def test_generate_ip_range_cross_octet():
    ips = generate_ip_range("192.168.0.254", "192.168.1.1")
    assert "192.168.0.254" in ips
    assert "192.168.0.255" in ips
    assert "192.168.1.0" in ips
    assert "192.168.1.1" in ips


@patch("core.scanner.subprocess.run")
def test_ping_host_alive(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Minimum = 2ms"
    result = ping_host("192.168.1.1", timeout_ms=500)
    assert result["alive"] is True
    assert result["ip"] == "192.168.1.1"


@patch("core.scanner.subprocess.run")
def test_ping_host_dead(mock_run):
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = ""
    result = ping_host("192.168.1.99", timeout_ms=500)
    assert result["alive"] is False
