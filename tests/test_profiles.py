# tests/test_profiles.py
import json
import os
import pytest
from core.profiles import ProfileManager


@pytest.fixture
def manager(tmp_path):
    return ProfileManager(profiles_dir=str(tmp_path))


def test_save_and_load_profile(manager):
    data = {"ip": "192.168.1.10", "mask": "255.255.255.0",
            "gateway": "192.168.1.1", "dns1": "8.8.8.8", "dns2": "8.8.4.4"}
    manager.save("Client_Test", data)
    result = manager.load("Client_Test")
    assert result == data


def test_list_profiles(manager):
    manager.save("Prof_A", {"ip": "10.0.0.1", "mask": "", "gateway": "", "dns1": "", "dns2": ""})
    manager.save("Prof_B", {"ip": "10.0.0.2", "mask": "", "gateway": "", "dns1": "", "dns2": ""})
    assert set(manager.list_profiles()) == {"Prof_A", "Prof_B"}


def test_delete_profile(manager):
    manager.save("ToDelete", {"ip": "1.1.1.1", "mask": "", "gateway": "", "dns1": "", "dns2": ""})
    manager.delete("ToDelete")
    assert "ToDelete" not in manager.list_profiles()


def test_load_nonexistent_raises(manager):
    with pytest.raises(FileNotFoundError):
        manager.load("DoesNotExist")
