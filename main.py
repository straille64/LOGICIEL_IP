# main.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from core.admin import is_admin, restart_as_admin
from modules.tab_config import TabConfig
from modules.tab_scanner import TabScanner
from modules.tab_modbus import TabModbus


class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly", title="LOGICIEL IP", size=(900, 700))
        self.resizable(True, True)
        self._build_tabs()
        self._build_status_bar()

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=5, pady=(5, 0))

        tab_cfg = TabConfig(self.notebook)
        self.notebook.add(tab_cfg, text="  Configuration & Outils  ")

        tab_scan = TabScanner(self.notebook)
        self.notebook.add(tab_scan, text="  Scanner Réseau  ")

        tab_modbus = TabModbus(self.notebook)
        self.notebook.add(tab_modbus, text="  Modbus  ")

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
