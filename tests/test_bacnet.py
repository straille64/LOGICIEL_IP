"""Tests unitaires core/bacnet.py — zéro matériel requis."""
import pytest
from unittest.mock import patch, MagicMock
from core.bacnet import DeviceInfo, ObjectRef
from core.bacnet import BACnetConnectionError, BACnetTimeoutError, BACnetWriteError
from core.bacnet import BACnetClient


def test_device_info_fields():
    d = DeviceInfo(device_id=101, address="192.168.1.10", vendor_name="Siemens", object_name="CTR-101")
    assert d.device_id == 101
    assert d.address == "192.168.1.10"
    assert d.vendor_name == "Siemens"
    assert d.object_name == "CTR-101"


def test_object_ref_fields():
    o = ObjectRef(object_type="analogInput", instance=1, name="Température")
    assert o.object_type == "analogInput"
    assert o.instance == 1
    assert o.name == "Température"


def test_error_hierarchy():
    assert issubclass(BACnetConnectionError, Exception)
    assert issubclass(BACnetTimeoutError, Exception)
    assert issubclass(BACnetWriteError, Exception)


def test_connect_sets_connected():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        client = BACnetClient()
        client.connect(local_ip="192.168.1.100/24")
        assert client.is_connected is True


def test_disconnect_clears_connected():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        client = BACnetClient()
        client.connect(local_ip="192.168.1.100/24")
        client.disconnect()
        assert client.is_connected is False
        mock_app.disconnect.assert_called_once()


def test_connect_with_bbmd():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_bac0.connect.return_value = MagicMock()
        client = BACnetClient()
        client.connect(local_ip="192.168.1.100/24", bbmd_address="10.0.0.1", bbmd_ttl=900)
        mock_bac0.connect.assert_called_once_with(
            ip="192.168.1.100/24",
            bbmdAddress="10.0.0.1",
            bbmdTTL=900,
        )


def test_connect_port_busy_raises():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_bac0.connect.side_effect = OSError("[WinError 10048] Adresse déjà utilisée")
        client = BACnetClient()
        with pytest.raises(BACnetConnectionError, match="47808"):
            client.connect(local_ip="192.168.1.100/24")


def test_who_is_returns_device_list():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        mock_app.whois.return_value = None
        # BAC0.devices : liste de tuples (device_id_str, address_str)
        mock_app.devices = [
            ("101", "192.168.1.10"),
            ("205", "192.168.1.20"),
        ]
        def fake_read(query):
            if "objectName" in query:
                return "CTR-101" if "192.168.1.10" in query else "CTR-205"
            if "vendorName" in query:
                return "Siemens"
            return ""
        mock_app.read.side_effect = fake_read

        client = BACnetClient()
        client.connect("192.168.1.100/24")
        devices = client.who_is(timeout=0.01)  # timeout court pour le test

        assert len(devices) == 2
        assert devices[0].device_id == 101
        assert devices[0].address == "192.168.1.10"
        assert devices[0].object_name == "CTR-101"
        assert devices[1].device_id == 205


def test_who_is_not_connected_raises():
    client = BACnetClient()
    with pytest.raises(BACnetConnectionError):
        client.who_is()
