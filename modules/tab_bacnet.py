"""modules/tab_bacnet.py — Onglet BACnet/IP (style BACEye)."""
import threading

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from core.bacnet import BACnetClient, BACnetConnectionError, BACnetTimeoutError


class TabBACnet(ttk.Frame):
    """Onglet BACnet/IP — découverte, lecture/écriture, polling, COV."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.client = BACnetClient()
        self._stop_event = threading.Event()
        self._poll_thread = None
        self._cyclic_interval = 1.0
        self._cov_subs: dict[str, int] = {}  # "type:inst" → subscription_id

        self._build()

    # ═══════════════════════════════════════════════════════════════════════
    # CONSTRUCTION UI
    # ═══════════════════════════════════════════════════════════════════════

    def _build(self):
        self._build_network_bar()
        self._build_main_area()
        self._build_status_bar()

    def _build_network_bar(self):
        bar = ttk.Frame(self, bootstyle=DARK)
        bar.pack(fill=X, padx=5, pady=(5, 2))

        ttk.Label(bar, text="IP locale :").pack(side=LEFT, padx=(5, 2))
        self._var_ip = ttk.StringVar(value="192.168.1.100/24")
        ttk.Entry(bar, textvariable=self._var_ip, width=18).pack(side=LEFT)

        ttk.Label(bar, text="  BBMD :").pack(side=LEFT, padx=(10, 2))
        self._var_bbmd = ttk.StringVar(value="")
        ttk.Entry(bar, textvariable=self._var_bbmd, width=15).pack(side=LEFT)

        ttk.Label(bar, text="TTL :").pack(side=LEFT, padx=(8, 2))
        self._var_ttl = ttk.StringVar(value="900")
        ttk.Entry(bar, textvariable=self._var_ttl, width=6).pack(side=LEFT)

        ttk.Button(bar, text="▶ CONNEXION",   bootstyle=SUCCESS,
                   command=self._btn_connect).pack(side=LEFT, padx=(12, 2))
        ttk.Button(bar, text="🔍 WHO-IS",     bootstyle=INFO,
                   command=self._btn_whois).pack(side=LEFT, padx=2)
        ttk.Button(bar, text="■ DÉCONNEXION", bootstyle=DANGER,
                   command=self._btn_disconnect).pack(side=LEFT, padx=2)

    def _build_main_area(self):
        pane = ttk.Panedwindow(self, orient=HORIZONTAL)
        pane.pack(fill=BOTH, expand=True, padx=5, pady=2)
        self._build_tree_panel(pane)
        self._build_detail_panel(pane)

    def _build_tree_panel(self, pane):
        frame = ttk.Frame(pane)
        pane.add(frame, weight=1)

        self._tree = ttk.Treeview(frame, show="tree", selectmode="browse")
        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self._tree.bind("<<TreeviewOpen>>", self._on_device_expand)
        self._tree.bind("<<TreeviewSelect>>", self._on_object_select)

    def _build_detail_panel(self, pane):
        frame = ttk.Frame(pane)
        pane.add(frame, weight=3)

        cols = ("name", "type", "value", "reliability", "unit")
        self._detail_tree = ttk.Treeview(
            frame, columns=cols, show="headings", selectmode="browse"
        )
        headers = [("name", "Object Name", 200), ("type", "Type", 130),
                   ("value", "Present Value", 120), ("reliability", "Reliability", 110),
                   ("unit", "Unité", 120)]
        for col, label, width in headers:
            self._detail_tree.heading(col, text=label)
            self._detail_tree.column(col, width=width, minwidth=60)

        vsb2 = ttk.Scrollbar(frame, orient=VERTICAL,
                              command=self._detail_tree.yview)
        self._detail_tree.configure(yscrollcommand=vsb2.set)
        self._detail_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb2.pack(side=RIGHT, fill=Y)

        action_bar = ttk.Frame(frame)
        action_bar.pack(fill=X, padx=2, pady=2)
        ttk.Button(action_bar, text="📋 Détails complets",
                   command=self._btn_details).pack(side=LEFT, padx=2)
        ttk.Button(action_bar, text="✏ Écrire valeur",
                   command=self._btn_write).pack(side=LEFT, padx=2)

        self._var_cov = ttk.BooleanVar(value=False)
        ttk.Checkbutton(action_bar, text="COV",
                        variable=self._var_cov,
                        command=self._on_cov_toggle).pack(side=LEFT, padx=8)

        self._var_poll = ttk.BooleanVar(value=False)
        ttk.Checkbutton(action_bar, text="Polling",
                        variable=self._var_poll,
                        command=self._on_poll_toggle).pack(side=LEFT, padx=2)

        INTERVALS = [("500 ms", 0.5), ("1 s", 1.0), ("2 s", 2.0),
                     ("5 s", 5.0), ("10 s", 10.0), ("30 s", 30.0)]
        self._var_interval = ttk.StringVar(value="1 s")
        cb = ttk.Combobox(action_bar, textvariable=self._var_interval,
                          values=[i[0] for i in INTERVALS], width=7,
                          state="readonly")
        cb.pack(side=LEFT)
        cb.bind("<<ComboboxSelected>>",
                lambda e: self._update_interval(INTERVALS))
        self._interval_map = {i[0]: i[1] for i in INTERVALS}

    def _build_status_bar(self):
        bar = ttk.Frame(self, bootstyle=DARK)
        bar.pack(fill=X, side=BOTTOM, padx=0)
        self._var_status = ttk.StringVar(value="Non connecté")
        ttk.Label(bar, textvariable=self._var_status,
                  bootstyle=SECONDARY).pack(side=LEFT, padx=5, pady=2)

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _set_status(self, msg: str):
        self._var_status.set(msg)

    def _update_interval(self, intervals):
        key = self._var_interval.get()
        self._cyclic_interval = self._interval_map.get(key, 1.0)

    # ═══════════════════════════════════════════════════════════════════════
    # CALLBACKS — stubs (implémentés dans les tâches suivantes)
    # ═══════════════════════════════════════════════════════════════════════

    def _btn_connect(self):       pass
    def _btn_disconnect(self):    pass
    def _btn_whois(self):         pass
    def _on_device_expand(self, e): pass
    def _on_object_select(self, e): pass
    def _btn_details(self):       pass
    def _btn_write(self):         pass
    def _on_cov_toggle(self):     pass
    def _on_poll_toggle(self):    pass
