"""Tests unitaires core/bacnet.py — zéro matériel requis."""
import pytest
from core.bacnet import DeviceInfo, ObjectRef
from core.bacnet import BACnetConnectionError, BACnetTimeoutError, BACnetWriteError


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
