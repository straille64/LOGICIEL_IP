from unittest.mock import patch, MagicMock
import sys

def test_is_admin_returns_true_when_elevated():
    with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=1):
        from core.admin import is_admin
        assert is_admin() is True

def test_is_admin_returns_false_when_not_elevated():
    with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=0):
        import importlib, core.admin
        importlib.reload(core.admin)
        from core.admin import is_admin
        assert is_admin() is False

def test_is_admin_returns_false_on_exception():
    with patch("ctypes.windll.shell32.IsUserAnAdmin", side_effect=OSError):
        import importlib, core.admin
        importlib.reload(core.admin)
        from core.admin import is_admin
        assert is_admin() is False
