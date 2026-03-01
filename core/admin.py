import ctypes
import sys
import os


def is_admin() -> bool:
    """Returns True if the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin() -> None:
    """Relaunch the current process with UAC elevation, then exit.

    Works both in dev (python main.py) and as a frozen .exe.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller .exe
        exe = sys.executable
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe = sys.executable
        script = os.path.abspath(sys.argv[0])
        rest = " ".join(f'"{a}"' for a in sys.argv[1:])
        params = f'"{script}" {rest}'.strip()

    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)
