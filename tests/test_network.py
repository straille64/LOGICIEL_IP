# tests/test_network.py
import pytest
from unittest.mock import patch, MagicMock
from core.network import list_interfaces, get_interface_config, apply_static_ip, apply_dhcp


def test_list_interfaces_returns_list():
    result = list_interfaces()
    assert isinstance(result, list)
    assert len(result) > 0


def test_list_interfaces_have_name_and_ip():
    result = list_interfaces()
    for iface in result:
        assert "name" in iface
        assert "ip" in iface


@patch("core.network.subprocess.run")
def test_apply_static_ip_calls_netsh(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    apply_static_ip("Ethernet", "192.168.1.50", "255.255.255.0", "192.168.1.1")
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "netsh" in cmd
    assert "192.168.1.50" in cmd


@patch("core.network.subprocess.run")
def test_apply_dhcp_calls_netsh(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    apply_dhcp("Ethernet")
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "dhcp" in cmd.lower()


@patch("core.network.subprocess.run")
def test_apply_dhcp_already_active_does_not_raise(mock_run):
    """returncode=1 (already DHCP) must not raise."""
    mock_run.return_value = MagicMock(returncode=1)
    apply_dhcp("Ethernet")   # must NOT raise
    assert mock_run.call_count == 2  # both address and dns commands must still run
