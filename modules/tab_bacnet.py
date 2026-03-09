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

    def _btn_connect(self):
        local_ip  = self._var_ip.get().strip()
        bbmd_addr = self._var_bbmd.get().strip() or None
        try:
            ttl = int(self._var_ttl.get())
        except ValueError:
            ttl = 900
        self._set_status("Connexion en cours…")

        def _worker():
            try:
                self.client.connect(local_ip, bbmd_address=bbmd_addr, bbmd_ttl=ttl)
                self.after(0, lambda: self._set_status("Connecté — prêt"))
            except Exception as exc:
                self.after(0, lambda e=exc: self._set_status(f"Erreur : {e}"))
                self.after(0, lambda e=exc: Messagebox.show_error(str(e), "Connexion BACnet"))

        threading.Thread(target=_worker, daemon=True).start()

    def _btn_disconnect(self):
        self._stop_event.set()
        for sub_id in list(self._cov_subs.values()):
            try:
                self.client.unsubscribe_cov(sub_id)
            except Exception:
                pass
        self._cov_subs.clear()
        self.client.disconnect()
        self._tree.delete(*self._tree.get_children())
        self._detail_tree.delete(*self._detail_tree.get_children())
        self._set_status("Déconnecté")

    def _btn_whois(self):
        if not self.client.is_connected:
            Messagebox.show_warning("Connectez-vous d'abord.", "Who-Is")
            return
        self._set_status("Scan Who-Is en cours…")
        self._tree.delete(*self._tree.get_children())

        def _worker():
            try:
                devices = self.client.who_is()
                self.after(0, lambda: self._populate_tree(devices))
            except Exception as exc:
                self.after(0, lambda e=exc: self._set_status(f"Who-Is échoué : {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_tree(self, devices):
        for dev in devices:
            label = f"Device {dev.device_id}  —  {dev.object_name}  [{dev.address}]"
            node = self._tree.insert("", END, iid=f"dev_{dev.device_id}",
                                     text=label, open=False,
                                     values=[dev.address, dev.device_id])
            # Nœud fantôme pour activer le triangle d'expansion
            self._tree.insert(node, END, iid=f"loading_{dev.device_id}",
                              text="Chargement…")
        n = len(devices)
        self._set_status(f"Connecté — {n} device(s) trouvé(s)")

    def _on_device_expand(self, event):
        node_id = self._tree.focus()
        if not node_id.startswith("dev_"):
            return
        children = self._tree.get_children(node_id)
        # Si le seul enfant est le nœud fantôme "loading_", lancer la requête
        if len(children) == 1 and str(children[0]).startswith("loading_"):
            dev_id = int(node_id.split("_")[1])
            address = self._tree.item(node_id, "values")[0]
            from core.bacnet import DeviceInfo
            device = DeviceInfo(dev_id, address, "", "")
            self._load_objects(node_id, device)

    def _load_objects(self, node_id: str, device):
        def _worker():
            try:
                objects = self.client.get_object_list(device)
                self.after(0, lambda: self._add_object_nodes(node_id, objects))
            except Exception as exc:
                self.after(0, lambda e=exc: self._set_status(f"Objets : {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _add_object_nodes(self, node_id: str, objects):
        # Supprimer le nœud fantôme
        for child in self._tree.get_children(node_id):
            self._tree.delete(child)
        for obj in objects:
            label = f"{obj.object_type}:{obj.instance}  —  {obj.name}"
            iid = f"obj_{node_id}_{obj.object_type}_{obj.instance}"
            self._tree.insert(node_id, END, iid=iid, text=label,
                              values=[obj.object_type, obj.instance, obj.name])

    def _on_object_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        node_id = sel[0]
        if not node_id.startswith("obj_"):
            return
        values = self._tree.item(node_id, "values")
        if not values or len(values) < 3:
            return
        obj_type = str(values[0])
        instance = int(values[1])
        name = str(values[2])
        # Remonter au device parent
        parent_id = self._tree.parent(node_id)
        parent_values = self._tree.item(parent_id, "values")
        if not parent_values:
            return
        address = str(parent_values[0])
        dev_id = int(parent_values[1])

        from core.bacnet import DeviceInfo, ObjectRef
        self._selected_device = DeviceInfo(dev_id, address, "", "")
        self._selected_object = ObjectRef(obj_type, instance, name)
        self._refresh_detail()

    def _refresh_detail(self):
        if not hasattr(self, "_selected_device"):
            return

        def _worker():
            try:
                value, unit, reliability = self.client.read_present_value(
                    self._selected_device, self._selected_object
                )
                self.after(0, lambda v=value, u=unit, r=reliability:
                    self._update_detail_row(self._selected_object, v, u, r))
            except Exception as exc:
                self.after(0, lambda e=exc: self._set_status(f"Lecture : {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _update_detail_row(self, obj, value, unit, reliability):
        self._detail_tree.delete(*self._detail_tree.get_children())
        self._detail_tree.insert("", END, values=(
            obj.name, obj.object_type, str(value), reliability, unit
        ))

    def _on_poll_toggle(self):
        if self._var_poll.get():
            self._stop_event.clear()
            self._poll_thread = threading.Thread(
                target=self._poll_loop, daemon=True
            )
            self._poll_thread.start()
        else:
            self._stop_event.set()

    def _poll_loop(self):
        import time
        while not self._stop_event.is_set():
            if hasattr(self, "_selected_device") and self.client.is_connected:
                try:
                    value, unit, reliability = self.client.read_present_value(
                        self._selected_device, self._selected_object
                    )
                    self.after(0, lambda v=value, u=unit, r=reliability:
                        self._update_detail_row(self._selected_object, v, u, r))
                except Exception as exc:
                    self.after(0, lambda e=exc:
                        self._set_status(f"Polling : {e}"))
            self._stop_event.wait(self._cyclic_interval)

    def _btn_details(self):
        if not hasattr(self, "_selected_device"):
            Messagebox.show_warning("Sélectionnez d'abord un objet.", "Détails")
            return
        self._set_status("Lecture des propriétés complètes…")

        def _worker():
            try:
                props = self.client.read_all_properties(
                    self._selected_device, self._selected_object
                )
                self.after(0, lambda: self._open_details_dialog(props))
            except Exception as exc:
                self.after(0, lambda e=exc: Messagebox.show_error(str(e), "Détails"))
                self.after(0, lambda: self._set_status("Prêt"))

        threading.Thread(target=_worker, daemon=True).start()

    def _open_details_dialog(self, props: dict):
        from modules.dialog_bacnet_obj import BACnetObjectDialog
        BACnetObjectDialog(self, self._selected_object.name, props)
        self._set_status("Prêt")

    def _btn_write(self):
        if not hasattr(self, "_selected_object"):
            Messagebox.show_warning("Sélectionnez d'abord un objet.", "Écriture")
            return
        from ttkbootstrap.dialogs import Querybox
        val_str = Querybox.get_string(
            prompt=f"Nouvelle valeur pour {self._selected_object.name} :",
            title="Écrire valeur",
        )
        if val_str is None:
            return
        prio_str = Querybox.get_string(
            prompt="Priorité BACnet (1-16, défaut 8) :",
            title="Priorité",
            initialvalue="8",
        )
        try:
            priority = int(prio_str or "8")
            priority = max(1, min(16, priority))
        except (ValueError, TypeError):
            priority = 8
        try:
            try:
                value = float(val_str)
            except ValueError:
                value = val_str
            self.client.write_present_value(
                self._selected_device, self._selected_object, value, priority
            )
            self._set_status(f"Écriture réussie : {value} (priorité {priority})")
            self._refresh_detail()
        except Exception as exc:
            Messagebox.show_error(str(exc), "Erreur d'écriture")

    def _on_cov_toggle(self):
        if not hasattr(self, "_selected_object"):
            self._var_cov.set(False)
            return
        key = f"{self._selected_object.object_type}:{self._selected_object.instance}"
        if self._var_cov.get():
            def _cov_callback(new_value):
                self.after(0, lambda v=new_value:
                    self._update_detail_row(self._selected_object, v, "", ""))

            def _subscribe():
                try:
                    sub_id = self.client.subscribe_cov(
                        self._selected_device, self._selected_object, _cov_callback
                    )
                    self._cov_subs[key] = sub_id
                    self.after(0, lambda: self._set_status(f"COV actif : {key}"))
                except Exception as exc:
                    # Bascule silencieuse en polling si COV non supporté
                    self.after(0, lambda: self._var_cov.set(False))
                    self.after(0, lambda: self._var_poll.set(True))
                    self.after(0, self._on_poll_toggle)
                    self.after(0, lambda e=exc: self._set_status(
                        f"COV non supporté, polling activé ({e})"
                    ))

            threading.Thread(target=_subscribe, daemon=True).start()
        else:
            if key in self._cov_subs:
                try:
                    self.client.unsubscribe_cov(self._cov_subs.pop(key))
                except Exception:
                    pass
            self._set_status("COV désactivé")
