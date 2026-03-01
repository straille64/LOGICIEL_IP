# tests/test_profiles.py
import pytest
from core.profiles import ProfileManager

SAMPLE = {"ip": "192.168.1.10", "mask": "255.255.255.0", "gateway": "192.168.1.1", "dns1": "", "dns2": ""}


# --- existing tests (keep passing) ---

def test_save_and_load_profile(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("test", SAMPLE)
    assert pm.load("test") == SAMPLE

def test_list_profiles(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("a", SAMPLE)
    pm.save("b", SAMPLE)
    assert sorted(pm.list_profiles()) == ["a", "b"]

def test_delete_profile(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("del_me", SAMPLE)
    pm.delete("del_me")
    assert "del_me" not in pm.list_profiles()

def test_load_nonexistent_raises(tmp_path):
    pm = ProfileManager(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        pm.load("ghost")


# --- new folder tests ---

def test_save_and_load_in_folder(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("prof1", SAMPLE, folder="Clients")
    assert pm.load("prof1", folder="Clients") == SAMPLE

def test_list_tree_root_and_folder(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("root_prof", SAMPLE)
    pm.save("client1", SAMPLE, folder="Clients")
    pm.save("client2", SAMPLE, folder="Clients")
    tree = pm.list_tree()
    assert "root_prof" in tree[""]
    assert sorted(tree["Clients"]) == ["client1", "client2"]

def test_create_and_delete_folder(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.create_folder("TestFolder")
    assert "TestFolder" in pm.list_tree()
    pm.delete_folder("TestFolder")
    assert "TestFolder" not in pm.list_tree()

def test_delete_profile_in_folder(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("x", SAMPLE, folder="Bureaux")
    pm.delete("x", folder="Bureaux")
    assert "x" not in pm.list_tree().get("Bureaux", [])

def test_list_profiles_backward_compat(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("root", SAMPLE)
    pm.save("sub", SAMPLE, folder="Folder")
    all_profiles = pm.list_profiles()
    assert "root" in all_profiles
    assert "sub" in all_profiles


# --- rename tests ---

def test_rename_profile(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("ancien", SAMPLE)
    pm.rename("ancien", "nouveau")
    assert pm.load("nouveau") == SAMPLE
    assert not (tmp_path / "ancien.json").exists()

def test_rename_profile_in_folder(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.save("ancien", SAMPLE, folder="Site")
    pm.rename("ancien", "nouveau", folder="Site")
    assert pm.load("nouveau", folder="Site") == SAMPLE
    assert not (tmp_path / "Site" / "ancien.json").exists()

def test_rename_folder(tmp_path):
    pm = ProfileManager(str(tmp_path))
    pm.create_folder("AncienDossier")
    pm.save("p", SAMPLE, folder="AncienDossier")
    pm.rename_folder("AncienDossier", "NouveauDossier")
    assert "NouveauDossier" in pm.list_tree()
    assert "AncienDossier" not in pm.list_tree()
    assert pm.load("p", folder="NouveauDossier") == SAMPLE
