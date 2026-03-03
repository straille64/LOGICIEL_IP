"""modules/tab_modbus.py — Onglet Modbus TCP/RTU (style KScada Modbus Doctor)."""
import threading
import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox, Querybox

from pymodbus.exceptions import ConnectionException, ModbusException

from core.modbus import ModbusClient, format_register_value


# ─── Constantes ──────────────────────────────────────────────────────────────

FC_OPTIONS = [
    ("FC1  — Lire Coils (bits R/W)",             "fc1",  "read",  "coil"),
    ("FC2  — Lire Entrées Discrètes (bits RO)",   "fc2",  "read",  "coil"),
    ("FC3  — Lire Holding Registers (mots R/W)",  "fc3",  "read",  "reg"),
    ("FC4  — Lire Input Registers (mots RO)",     "fc4",  "read",  "reg"),
    ("FC5  — Écrire 1 Coil",                      "fc5",  "write", "coil"),
    ("FC6  — Écrire 1 Registre",                  "fc6",  "write", "reg"),
    ("FC15 — Écrire Multiple Coils",              "fc15", "write", "coil"),
    ("FC16 — Écrire Multiple Registres",          "fc16", "write", "reg"),
]
FC_LABELS  = [f[0] for f in FC_OPTIONS]
FC_KEYS    = {f[0]: f[1] for f in FC_OPTIONS}
FC_DIR     = {f[0]: f[2] for f in FC_OPTIONS}
FC_TYPE    = {f[0]: f[3] for f in FC_OPTIONS}

DISPLAY_MODES = [
    ("Mot 16 bits",            "uint16"),
    ("Signé 16 bits",          "int16"),
    ("Float 32 bits (2 reg)",  "float32"),
    ("Entier 32 bits (2 reg)", "uint32"),
    ("Signé 32 bits (2 reg)",  "int32"),
    ("Binaire",                "bin"),
    ("ASCII",                  "ascii"),
]
DISPLAY_LABELS = [d[0] for d in DISPLAY_MODES]
DISPLAY_KEY    = {d[0]: d[1] for d in DISPLAY_MODES}

NUM_BASES  = ["DÉCIMAL", "HEX", "BINAIRE"]
BAUDRATES  = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
PARITIES   = ["N", "E", "O"]
BYTESIZES  = [7, 8]
STOPBITS   = [1, 2]
INTERVALS  = [
    ("100 ms", 0.1), ("500 ms", 0.5), ("1 s", 1.0),
    ("2 s", 2.0),   ("5 s", 5.0),    ("10 s", 10.0),
]


class TabModbus(ttk.Frame):
    """Onglet Modbus TCP/RTU — lecture/écriture de registres."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.mc = ModbusClient()
        self._stop_event = threading.Event()
        self._poll_thread = None
        self._cyclic_interval = 1.0

        self._build()

    # ═════════════════════════════════════════════════════════════════════════
    # CONSTRUCTION UI
    # ═════════════════════════════════════════════════════════════════════════

    def _build(self):
        self._build_connection_bar()
        self._build_params_bar()
        self._build_main_area()
        self._build_status_bar()
        self._on_transport_change()
        self._on_fc_change()

    # ─── Barre connexion ─────────────────────────────────────────────────────

    def _build_connection_bar(self):
        bar = ttk.Frame(self, padding=(6, 4))
        bar.pack(fill=X)

        self.transport_var = tk.StringVar(value="TCP/IP")
        ttk.Combobox(
            bar, textvariable=self.transport_var,
            values=["TCP/IP", "RTU/Serial"],
            state="readonly", width=12,
        ).pack(side=LEFT, padx=(0, 4))
        self.transport_var.trace_add("write", lambda *_: self._on_transport_change())

        # Champs TCP
        self._tcp_frame = ttk.Frame(bar)
        self._tcp_frame.pack(side=LEFT)
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="502")
        ttk.Entry(self._tcp_frame, textvariable=self.host_var, width=16).pack(side=LEFT, padx=1)
        ttk.Label(self._tcp_frame, text=":").pack(side=LEFT)
        ttk.Entry(self._tcp_frame, textvariable=self.port_var, width=6).pack(side=LEFT, padx=1)

        # Champs RTU
        self._rtu_frame = ttk.Frame(bar)
        self.com_var      = tk.StringVar(value="COM1")
        self.baud_var     = tk.StringVar(value="9600")
        self.parity_var   = tk.StringVar(value="N")
        self.bytesize_var = tk.StringVar(value="8")
        self.stopbits_var = tk.StringVar(value="1")
        ttk.Label(self._rtu_frame, text="Port:").pack(side=LEFT, padx=(0, 1))
        ttk.Entry(self._rtu_frame, textvariable=self.com_var, width=7).pack(side=LEFT, padx=1)
        ttk.Label(self._rtu_frame, text="Baud:").pack(side=LEFT, padx=(4, 1))
        ttk.Combobox(self._rtu_frame, textvariable=self.baud_var,
                     values=[str(b) for b in BAUDRATES], state="readonly", width=7
                     ).pack(side=LEFT, padx=1)
        ttk.Combobox(self._rtu_frame, textvariable=self.parity_var,
                     values=PARITIES, state="readonly", width=3
                     ).pack(side=LEFT, padx=1)
        ttk.Combobox(self._rtu_frame, textvariable=self.bytesize_var,
                     values=[str(b) for b in BYTESIZES], state="readonly", width=2
                     ).pack(side=LEFT, padx=1)
        ttk.Combobox(self._rtu_frame, textvariable=self.stopbits_var,
                     values=[str(s) for s in STOPBITS], state="readonly", width=2
                     ).pack(side=LEFT, padx=1)

        # Boutons
        self.btn_connect = ttk.Button(
            bar, text="▶ CONNEXION", bootstyle=SUCCESS,
            command=self._do_connect,
        )
        self.btn_connect.pack(side=LEFT, padx=(8, 2))

        self.btn_disconnect = ttk.Button(
            bar, text="■ DÉCONNEXION", bootstyle=DANGER,
            command=self._do_disconnect, state=DISABLED,
        )
        self.btn_disconnect.pack(side=LEFT, padx=2)

    def _on_transport_change(self):
        if self.transport_var.get() == "TCP/IP":
            self._rtu_frame.pack_forget()
            self._tcp_frame.pack(side=LEFT)
        else:
            self._tcp_frame.pack_forget()
            self._rtu_frame.pack(side=LEFT)

    # ─── Barre paramètres ────────────────────────────────────────────────────

    def _build_params_bar(self):
        bar = ttk.Frame(self, padding=(6, 2))
        bar.pack(fill=X)

        self.slave_var   = tk.StringVar(value="1")
        self.address_var = tk.StringVar(value="0")
        self.length_var  = tk.StringVar(value="10")

        for label, var, width in [
            ("N° Esclave", self.slave_var, 5),
            ("Registre",   self.address_var, 7),
            ("Longueur",   self.length_var, 5),
        ]:
            ttk.Label(bar, text=label).pack(side=LEFT, padx=(4, 1))
            ttk.Entry(bar, textvariable=var, width=width).pack(side=LEFT, padx=(0, 4))

        self.fc_var = tk.StringVar(value=FC_LABELS[2])
        ttk.Label(bar, text="Type").pack(side=LEFT, padx=(4, 1))
        self.fc_combo = ttk.Combobox(
            bar, textvariable=self.fc_var, values=FC_LABELS,
            state="readonly", width=40,
        )
        self.fc_combo.pack(side=LEFT, padx=(0, 4))
        self.fc_var.trace_add("write", lambda *_: self._on_fc_change())

        self.nummode_var = tk.StringVar(value="DÉCIMAL")
        ttk.Label(bar, text="Mode").pack(side=LEFT, padx=(4, 1))
        ttk.Combobox(
            bar, textvariable=self.nummode_var, values=NUM_BASES,
            state="readonly", width=9,
        ).pack(side=LEFT)

    def _on_fc_change(self):
        fc_label  = self.fc_var.get()
        direction = FC_DIR.get(fc_label, "read")
        if direction == "write":
            self.btn_lecture.config(state=DISABLED)
            self.btn_ecriture.config(state=NORMAL)
        else:
            self.btn_lecture.config(state=NORMAL)
            # FC2 et FC4 sont read-only
            if fc_label.startswith("FC2") or fc_label.startswith("FC4"):
                self.btn_ecriture.config(state=DISABLED)
            else:
                self.btn_ecriture.config(state=NORMAL)

    # ─── Zone principale ──────────────────────────────────────────────────────

    def _build_main_area(self):
        paned = ttk.Panedwindow(self, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=4, pady=2)

        left = ttk.Frame(paned, width=185)
        left.pack_propagate(False)
        paned.add(left, weight=0)
        self._build_left_panel(left)

        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self._build_right_panel(right)

    def _build_left_panel(self, parent):
        self.btn_lecture = ttk.Button(
            parent, text="  LECTURE  ", bootstyle=PRIMARY,
            command=self._start_read_with_cyclic, width=18,
        )
        self.btn_lecture.pack(fill=X, padx=6, pady=(8, 2))

        self.btn_ecriture = ttk.Button(
            parent, text="  ECRITURE  ", bootstyle=SECONDARY,
            command=self._start_write, width=18,
        )
        self.btn_ecriture.pack(fill=X, padx=6, pady=2)

        ttk.Separator(parent, orient=HORIZONTAL).pack(fill=X, padx=6, pady=6)

        self.auto_reconnect_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="Reconnexion auto",
                        variable=self.auto_reconnect_var).pack(anchor=W, padx=8)

        row = ttk.Frame(parent)
        row.pack(fill=X, padx=8, pady=2)
        self.cyclic_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Cyclique", variable=self.cyclic_var).pack(side=LEFT)
        ttk.Button(row, text="...", width=3,
                   command=self._config_interval, bootstyle=SECONDARY
                   ).pack(side=LEFT, padx=4)

        self.btn_stop_cyclic = ttk.Button(
            parent, text="ARRET CYCLE", bootstyle=WARNING,
            command=self._stop_cyclic, state=DISABLED, width=18,
        )
        self.btn_stop_cyclic.pack(fill=X, padx=6, pady=2)

        ttk.Separator(parent, orient=HORIZONTAL).pack(fill=X, padx=6, pady=6)

        self.swap_bytes_var = tk.BooleanVar(value=False)
        self.swap_words_var = tk.BooleanVar(value=False)
        self.unsigned_var   = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="Inversion Octets",
                        variable=self.swap_bytes_var).pack(anchor=W, padx=8)
        ttk.Checkbutton(parent, text="Inversion Mots",
                        variable=self.swap_words_var).pack(anchor=W, padx=8)
        ttk.Checkbutton(parent, text="Non signé",
                        variable=self.unsigned_var).pack(anchor=W, padx=8)

        ttk.Separator(parent, orient=HORIZONTAL).pack(fill=X, padx=6, pady=6)

        ttk.Label(parent, text="Mode d'affichage :").pack(anchor=W, padx=8)
        self.display_var = tk.StringVar(value=DISPLAY_LABELS[0])
        ttk.Combobox(
            parent, textvariable=self.display_var,
            values=DISPLAY_LABELS, state="readonly", width=18,
        ).pack(padx=6, pady=2)

    def _build_right_panel(self, parent):
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=BOTH, expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("reg", "val"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("reg", text="N° Registre")
        self.tree.heading("val", text="Valeur")
        self.tree.column("reg", width=130, anchor=CENTER)
        self.tree.column("val", width=200, anchor=W)

        vsb = ttk.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        err_frame = ttk.LabelFrame(parent, text="Erreur", padding=4)
        err_frame.pack(fill=X, padx=2, pady=(2, 0))
        self.error_var = tk.StringVar(value="")
        ttk.Label(
            err_frame, textvariable=self.error_var,
            bootstyle=DANGER, wraplength=400,
        ).pack(anchor=W)

    # ─── Barre statut ─────────────────────────────────────────────────────────

    def _build_status_bar(self):
        ttk.Separator(self, orient=HORIZONTAL).pack(fill=X, side=BOTTOM)
        bar = ttk.Frame(self, padding=(6, 2))
        bar.pack(fill=X, side=BOTTOM)
        self.status_var = tk.StringVar(value="Statut : Déconnecté")
        ttk.Label(bar, textvariable=self.status_var, anchor=W).pack(side=LEFT)

    # ═════════════════════════════════════════════════════════════════════════
    # CONNEXION / DÉCONNEXION
    # ═════════════════════════════════════════════════════════════════════════

    def _do_connect(self):
        self.btn_connect.config(state=DISABLED)
        self.error_var.set("")

        def _task():
            try:
                transport = self.transport_var.get()
                if transport == "TCP/IP":
                    host = self.host_var.get().strip()
                    port = int(self.port_var.get().strip() or "502")
                    self.mc.connect_tcp(host, port)
                    self.after(0, lambda: self._set_status(
                        f"Connecté à {host}:{port}", connected=True))
                else:
                    com  = self.com_var.get().strip()
                    baud = int(self.baud_var.get())
                    par  = self.parity_var.get()
                    bits = int(self.bytesize_var.get())
                    stop = int(self.stopbits_var.get())
                    self.mc.connect_rtu(com, baud, par, bits, stop)
                    self.after(0, lambda: self._set_status(
                        f"Connecté à {com} @ {baud} {par}{bits}{stop}", connected=True))
            except Exception as exc:
                self.after(0, lambda e=str(exc): self._on_connect_error(e))

        threading.Thread(target=_task, daemon=True).start()

    def _do_disconnect(self):
        self._stop_cyclic()
        self.mc.disconnect()
        self._set_status("Déconnecté", connected=False)

    def _set_status(self, msg: str, connected: bool):
        self.status_var.set(f"Statut : {msg}")
        self.btn_connect.config(state=DISABLED if connected else NORMAL)
        self.btn_disconnect.config(state=NORMAL if connected else DISABLED)

    def _on_connect_error(self, msg: str):
        self.btn_connect.config(state=NORMAL)
        self.error_var.set(f"Connexion impossible : {msg}")
        self.status_var.set("Statut : Erreur de connexion")

    # ═════════════════════════════════════════════════════════════════════════
    # LECTURE
    # ═════════════════════════════════════════════════════════════════════════

    def _get_params(self):
        slave   = int(self.slave_var.get())
        address = int(self.address_var.get())
        length  = int(self.length_var.get())
        return slave, address, length

    def _start_read_with_cyclic(self):
        self._start_read()
        if self.cyclic_var.get() and not self._stop_event.is_set():
            self._stop_event.clear()
            self._poll_thread = threading.Thread(
                target=self._poll_loop, daemon=True
            )
            self._poll_thread.start()
            self.btn_stop_cyclic.config(state=NORMAL)

    def _start_read(self):
        if not self.mc.is_connected:
            self.error_var.set("Non connecté.")
            return
        try:
            slave, address, length = self._get_params()
        except ValueError as e:
            self.error_var.set(f"Paramètre invalide : {e}")
            return
        self.error_var.set("")
        threading.Thread(
            target=self._do_read, args=(slave, address, length), daemon=True
        ).start()

    def _do_read(self, slave: int, address: int, length: int):
        fc_label = self.fc_var.get()
        fc_key   = FC_KEYS.get(fc_label, "fc3")
        try:
            values = self._call_read(fc_key, slave, address, length)
            self.after(0, lambda v=values, a=address: self._populate_table(a, v))
        except (ConnectionException, ModbusException, Exception) as exc:
            self.after(0, lambda e=str(exc): self.error_var.set(str(e)))
            if self.auto_reconnect_var.get():
                self._try_reconnect()

    def _call_read(self, fc_key: str, slave: int, address: int, count: int):
        match fc_key:
            case "fc1": return self.mc.read_coils(slave, address, count)
            case "fc2": return self.mc.read_discrete_inputs(slave, address, count)
            case "fc3": return self.mc.read_holding_registers(slave, address, count)
            case "fc4": return self.mc.read_input_registers(slave, address, count)
            case _:     raise ValueError(f"FC de lecture inconnu : {fc_key}")

    def _populate_table(self, base_address: int, values: list):
        self.tree.delete(*self.tree.get_children())
        display_mode = DISPLAY_KEY.get(self.display_var.get(), "uint16")
        num_base     = {"DÉCIMAL": "dec", "HEX": "hex", "BINAIRE": "bin"}.get(
            self.nummode_var.get(), "dec")
        swap_bytes = self.swap_bytes_var.get()
        swap_words = self.swap_words_var.get()
        unsigned   = self.unsigned_var.get()

        step = 2 if display_mode in ("float32", "uint32", "int32") else 1
        i = 0
        while i < len(values):
            reg_addr = base_address + i
            raw = values[i:i + step] if step == 2 else values[i]
            formatted = format_register_value(
                raw, display_mode, num_base, swap_bytes, swap_words, unsigned
            )
            self.tree.insert("", END, values=(reg_addr, formatted))
            i += step

    # ═════════════════════════════════════════════════════════════════════════
    # ÉCRITURE
    # ═════════════════════════════════════════════════════════════════════════

    def _start_write(self):
        if not self.mc.is_connected:
            self.error_var.set("Non connecté.")
            return
        try:
            slave, address, length = self._get_params()
        except ValueError as e:
            self.error_var.set(f"Paramètre invalide : {e}")
            return

        fc_label = self.fc_var.get()
        fc_key   = FC_KEYS.get(fc_label, "fc6")
        fc_type  = FC_TYPE.get(fc_label, "reg")

        if fc_key in ("fc5", "fc6"):
            prompt = ("Valeur (0 = False, 1 = True) :" if fc_type == "coil"
                      else "Valeur (entier 16 bits, 0–65535) :")
            raw_val = Querybox.get_string(prompt, title="Écriture", parent=self)
            if raw_val is None:
                return
            try:
                value = bool(int(raw_val.strip())) if fc_type == "coil" else int(raw_val.strip())
            except ValueError:
                self.error_var.set("Valeur invalide.")
                return
            self.error_var.set("")
            threading.Thread(
                target=self._do_write_single, args=(fc_key, slave, address, value),
                daemon=True
            ).start()
        else:
            prompt = (f"Valeurs ({length} coils, ex: 1,0,1) :" if fc_type == "coil"
                      else f"Valeurs ({length} registres, ex: 100,200,300) :")
            raw_val = Querybox.get_string(prompt, title="Écriture multiple", parent=self)
            if raw_val is None:
                return
            try:
                parts = [v.strip() for v in raw_val.split(",")]
                values = ([bool(int(p)) for p in parts] if fc_type == "coil"
                          else [int(p) for p in parts])
            except ValueError:
                self.error_var.set("Valeurs invalides — entiers séparés par des virgules.")
                return
            self.error_var.set("")
            threading.Thread(
                target=self._do_write_multiple, args=(fc_key, slave, address, values),
                daemon=True
            ).start()

    def _do_write_single(self, fc_key: str, slave: int, address: int, value):
        try:
            if fc_key == "fc5":
                self.mc.write_coil(slave, address, value)
            elif fc_key == "fc6":
                self.mc.write_register(slave, address, value)
            self.after(0, lambda: self.error_var.set(""))
        except Exception as exc:
            self.after(0, lambda e=str(exc): self.error_var.set(str(e)))

    def _do_write_multiple(self, fc_key: str, slave: int, address: int, values: list):
        try:
            if fc_key == "fc15":
                self.mc.write_coils(slave, address, values)
            elif fc_key == "fc16":
                self.mc.write_registers(slave, address, values)
            self.after(0, lambda: self.error_var.set(""))
        except Exception as exc:
            self.after(0, lambda e=str(exc): self.error_var.set(str(e)))

    # ═════════════════════════════════════════════════════════════════════════
    # POLLING CYCLIQUE
    # ═════════════════════════════════════════════════════════════════════════

    def _config_interval(self):
        labels  = [iv[0] for iv in INTERVALS]
        current = next((iv[0] for iv in INTERVALS if iv[1] == self._cyclic_interval),
                       labels[2])
        choice = Querybox.get_string(
            f"Intervalle cyclique\n({', '.join(labels)}) :",
            title="Configuration intervalle",
            initialvalue=current,
            parent=self,
        )
        if choice is None:
            return
        mapping = {iv[0]: iv[1] for iv in INTERVALS}
        if choice in mapping:
            self._cyclic_interval = mapping[choice]
        else:
            try:
                self._cyclic_interval = float(choice)
            except ValueError:
                pass

    def _poll_loop(self):
        while not self._stop_event.wait(timeout=self._cyclic_interval):
            if not self.mc.is_connected:
                break
            try:
                slave, address, length = self._get_params()
            except ValueError:
                break
            fc_label = self.fc_var.get()
            fc_key   = FC_KEYS.get(fc_label, "fc3")
            try:
                values = self._call_read(fc_key, slave, address, length)
                self.after(0, lambda v=values, a=address: self._populate_table(a, v))
            except Exception as exc:
                self.after(0, lambda e=str(exc): self.error_var.set(str(e)))
                if self.auto_reconnect_var.get():
                    self._try_reconnect()
        self.after(0, lambda: self.btn_stop_cyclic.config(state=DISABLED))

    def _stop_cyclic(self):
        self._stop_event.set()
        self.btn_stop_cyclic.config(state=DISABLED)

    # ─── Reconnexion auto ────────────────────────────────────────────────────

    def _try_reconnect(self):
        try:
            self.mc.disconnect()
            if self.transport_var.get() == "TCP/IP":
                self.mc.connect_tcp(
                    self.host_var.get().strip(),
                    int(self.port_var.get().strip() or "502"),
                )
            else:
                self.mc.connect_rtu(
                    self.com_var.get().strip(),
                    int(self.baud_var.get()),
                    self.parity_var.get(),
                    int(self.bytesize_var.get()),
                    int(self.stopbits_var.get()),
                )
        except Exception:
            pass
