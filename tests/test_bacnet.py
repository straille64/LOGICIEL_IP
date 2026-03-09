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


def test_get_object_list():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app

        def fake_read(query):
            if "objectList" in query:
                return [("analogInput", 1), ("binaryOutput", 1)]
            if "analogInput" in query and "objectName" in query:
                return "Température"
            if "binaryOutput" in query and "objectName" in query:
                return "Pompe"
            return ""
        mock_app.read.side_effect = fake_read

        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "Siemens", "CTR-101")
        objects = client.get_object_list(device)

        assert len(objects) == 2
        assert objects[0].object_type == "analogInput"
        assert objects[0].instance == 1
        assert objects[0].name == "Température"
        assert objects[1].object_type == "binaryOutput"
        assert objects[1].name == "Pompe"


def test_get_object_list_not_connected_raises():
    client = BACnetClient()
    device = DeviceInfo(101, "192.168.1.10", "", "")
    with pytest.raises(BACnetConnectionError):
        client.get_object_list(device)


def test_read_present_value():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        def fake_read(query):
            if "presentValue" in query:   return 21.5
            if "units" in query:          return "degreesCelsius"
            if "reliability" in query:    return "noFaultDetected"
            return None
        mock_app.read.side_effect = fake_read
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")
        value, unit, reliability = client.read_present_value(device, obj)
        assert value == 21.5
        assert unit == "degreesCelsius"
        assert reliability == "noFaultDetected"


def test_read_present_value_not_connected_raises():
    client = BACnetClient()
    device = DeviceInfo(101, "192.168.1.10", "", "")
    obj = ObjectRef("analogInput", 1, "Temp")
    with pytest.raises(BACnetConnectionError):
        client.read_present_value(device, obj)


def test_read_all_properties():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        mock_app.readMultiple.return_value = {
            "presentValue": 21.5,
            "objectName": "Température",
            "units": "degreesCelsius",
        }
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")
        props = client.read_all_properties(device, obj)
        assert props["presentValue"] == 21.5
        assert props["objectName"] == "Température"


def test_write_present_value():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogValue", 1, "Consigne")
        client.write_present_value(device, obj, 22.5, priority=8)
        mock_app.write.assert_called_once_with(
            "192.168.1.10 analogValue 1 presentValue 22.5 - 8"
        )


def test_write_present_value_raises_on_error():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        mock_app.write.side_effect = Exception("WriteAccessDenied")
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")
        with pytest.raises(BACnetWriteError):
            client.write_present_value(device, obj, 21.0)


def test_subscribe_cov_returns_id():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        mock_app.subscribe_cov.return_value = 42
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")
        sub_id = client.subscribe_cov(device, obj, callback=lambda v: None)
        assert isinstance(sub_id, int)


def test_unsubscribe_cov_not_connected_is_silent():
    client = BACnetClient()
    # Ne doit pas lever d'exception
    client.unsubscribe_cov(42)
