# main.py
import os
import sys

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from core.admin import is_admin, restart_as_admin
from modules.tab_config import TabConfig
from modules.tab_scanner import TabScanner
from modules.tab_modbus import TabModbus
from modules.tab_pcvue import TabPCVue


def _resource(rel_path: str) -> str:
    """Résout un chemin relatif — compatible mode dev et PyInstaller."""
    base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base, rel_path)


def _load_icon(rel_path: str, size: tuple = (22, 22)):
    """Charge une image PNG et retourne un PhotoImage redimensionné."""
    try:
        img = Image.open(_resource(rel_path)).convert('RGBA').resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly", title="MultiTools Z", size=(900, 700))
        self.resizable(True, True)
        self._load_icons()
        self._set_window_icon()
        self._build_tabs()
        self._build_status_bar()

    def _load_icons(self):
        self._tab_icons = [
            _load_icon("icones/Configuration & Outils.png"),
            _load_icon("icones/Scanner R\u00e9seau.png"),
            _load_icon("icones/Modbus.png"),
            _load_icon("icones/Pcvue trames.png"),
        ]

    def _set_window_icon(self):
        try:
            logo = Image.open(_resource("icones/Logo \u2014 MultiTools Z.png")).convert('RGBA')
            self._logo_icon = ImageTk.PhotoImage(logo.resize((64, 64), Image.LANCZOS))
            self.iconphoto(True, self._logo_icon)
        except Exception:
            pass

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=5, pady=(5, 0))

        tab_cfg = TabConfig(self.notebook)
        self.notebook.add(tab_cfg, text="  Configuration & Outils  ",
                          image=self._tab_icons[0], compound=LEFT)

        tab_scan = TabScanner(self.notebook)
        self.notebook.add(tab_scan, text="  Scanner Réseau  ",
                          image=self._tab_icons[1], compound=LEFT)

        tab_modbus = TabModbus(self.notebook)
        self.notebook.add(tab_modbus, text="  Modbus  ",
                          image=self._tab_icons[2], compound=LEFT)

        tab_pcvue = TabPCVue(self.notebook)
        self.notebook.add(tab_pcvue, text="  Pcvue trames  ",
                          image=self._tab_icons[3], compound=LEFT)

    def _build_status_bar(self):
        bar = ttk.Frame(self, bootstyle=DARK)
        bar.pack(fill=X, side=BOTTOM, padx=0, pady=0)

        if is_admin():
            ttk.Label(bar, text="  [ADMIN]  ", bootstyle=SUCCESS).pack(side=RIGHT, padx=(0, 5))
        else:
            ttk.Label(bar, text="  [Utilisateur standard]  ", bootstyle=WARNING).pack(side=RIGHT, padx=(0, 5))
            ttk.Button(
                bar,
                text="Redémarrer en Administrateur",
                command=restart_as_admin,
                bootstyle=WARNING,
            ).pack(side=RIGHT, padx=(0, 3))


if __name__ == "__main__":
    app = App()
    app.mainloop()
