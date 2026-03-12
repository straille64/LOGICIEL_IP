"""modules/dialog_bacnet_obj.py — Popup toutes propriétés d'un objet BACnet."""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class BACnetObjectDialog(ttk.Toplevel):
    """Affiche toutes les propriétés d'un objet BACnet (ReadPropertyMultiple)."""

    def __init__(self, master, obj_name: str, properties: dict):
        super().__init__(master)
        self.title(f"Propriétés — {obj_name}")
        self.resizable(True, True)
        self.geometry("520x480")
        self._build(obj_name, properties)
        self.grab_set()

    def _build(self, obj_name: str, properties: dict):
        ttk.Label(self, text=obj_name, font=("", 11, "bold"),
                  bootstyle=INFO).pack(anchor=W, padx=10, pady=(8, 2))

        frame = ttk.Frame(self)
        frame.pack(fill=BOTH, expand=True, padx=8, pady=4)

        tree = ttk.Treeview(frame, columns=("prop", "value"),
                            show="headings", selectmode="none")
        tree.heading("prop",  text="Propriété")
        tree.heading("value", text="Valeur")
        tree.column("prop",  width=200, minwidth=120)
        tree.column("value", width=280, minwidth=100)

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        for prop, value in sorted(properties.items()):
            tree.insert("", END, values=(prop, str(value)))

        ttk.Button(self, text="Fermer", bootstyle=SECONDARY,
                   command=self.destroy).pack(pady=6)
