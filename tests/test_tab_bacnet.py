"""Smoke tests pour TabBACnet — vérifie que l'UI se construit sans erreur."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture()
def root():
    import ttkbootstrap as ttk
    r = ttk.Window(themename="darkly")
    yield r
    r.destroy()


def test_tab_bacnet_builds(root):
    from modules.tab_bacnet import TabBACnet
    tab = TabBACnet(root)
    assert tab.winfo_exists()


def test_tab_bacnet_has_client(root):
    from modules.tab_bacnet import TabBACnet
    from core.bacnet import BACnetClient
    tab = TabBACnet(root)
    assert isinstance(tab.client, BACnetClient)


def test_tab_bacnet_initial_status(root):
    from modules.tab_bacnet import TabBACnet
    tab = TabBACnet(root)
    assert tab._var_status.get() == "Non connecté"


def test_bacnet_object_dialog_builds(root):
    from modules.dialog_bacnet_obj import BACnetObjectDialog
    props = {"presentValue": 21.5, "objectName": "Test", "units": "degreesCelsius"}
    dlg = BACnetObjectDialog(root, "Test Object", props)
    assert dlg.winfo_exists()
    dlg.destroy()
