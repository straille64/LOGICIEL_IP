import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from modules.tab_config import TabConfig
from modules.tab_scanner import TabScanner


class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly", title="LOGICIEL IP", size=(900, 700))
        self.resizable(True, True)
        self._build_tabs()

    def _build_tabs(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)

        tab_cfg = TabConfig(notebook)
        notebook.add(tab_cfg, text="  Configuration & Outils  ")

        tab_scan = TabScanner(notebook)
        notebook.add(tab_scan, text="  Scanner Réseau  ")


if __name__ == "__main__":
    app = App()
    app.mainloop()
