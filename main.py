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
from modules.tab_mbus import TabMBus
from modules.tab_pcvue import TabPCVue
from modules.tab_bacnet import TabBACnet


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
            _load_icon("icones/M-Bus.png"),
            _load_icon("icones/Pcvue trames.png"),
            _load_icon("icones/BACnet.png"),   # index 5 — optionnel
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

        self._add_tab(TabConfig(self.notebook),  "  Configuration & Outils  ", 0)
        self._add_tab(TabScanner(self.notebook), "  Scanner Réseau  ",         1)
        self._add_tab(TabModbus(self.notebook),  "  Modbus  ",                 2)
        self._add_tab(TabMBus(self.notebook),    "  M-Bus  ",                  3)
        self._add_tab(TabPCVue(self.notebook),   "  Pcvue trames  ",           4)
        self._add_tab(TabBACnet(self.notebook),  "  BACnet/IP  ",              5)

    def _add_tab(self, frame, text: str, icon_index: int):
        """Ajoute un onglet — l'icône est optionnelle (ignorée si None)."""
        icon = self._tab_icons[icon_index] if icon_index < len(self._tab_icons) else None
        if icon:
            self.notebook.add(frame, text=text, image=icon, compound=LEFT)
        else:
            self.notebook.add(frame, text=text)

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
