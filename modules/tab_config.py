# modules/tab_config.py
import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
import subprocess

from core.network import list_interfaces, get_interface_config, apply_static_ip, apply_dhcp, apply_dns, run_ipconfig
from core.profiles import ProfileManager

PROFILES_DIR = "profiles"


class TabConfig(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pm = ProfileManager(PROFILES_DIR)
        self._build()
        self._refresh_interfaces()

    def _build(self):
        # --- Carte réseau ---
        iface_frame = ttk.LabelFrame(self, text="Carte réseau", padding=10)
        iface_frame.pack(fill=X, padx=10, pady=(10, 5))

        self.iface_var = tk.StringVar()
        self.iface_cb = ttk.Combobox(iface_frame, textvariable=self.iface_var, state="readonly", width=40)
        self.iface_cb.pack(side=LEFT, padx=(0, 10))
        self.iface_cb.bind("<<ComboboxSelected>>", self._on_iface_selected)
        ttk.Button(iface_frame, text="↺ Rafraîchir", command=self._refresh_interfaces, bootstyle=SECONDARY).pack(side=LEFT)

        # --- Configuration IP ---
        ip_frame = ttk.LabelFrame(self, text="Configuration IP", padding=10)
        ip_frame.pack(fill=X, padx=10, pady=5)

        self.mode_var = tk.StringVar(value="dhcp")
        ttk.Radiobutton(ip_frame, text="DHCP", variable=self.mode_var, value="dhcp", command=self._toggle_mode).grid(row=0, column=0, sticky=W)
        ttk.Radiobutton(ip_frame, text="Manuel", variable=self.mode_var, value="static", command=self._toggle_mode).grid(row=0, column=1, sticky=W)

        labels = ["Adresse IP", "Masque", "Passerelle", "DNS 1", "DNS 2"]
        self.ip_vars = {}
        self.ip_entries = {}
        for i, label in enumerate(labels):
            key = label.lower().replace(" ", "").replace("é", "e")
            ttk.Label(ip_frame, text=label).grid(row=i+1, column=0, sticky=W, pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(ip_frame, textvariable=var, width=20)
            entry.grid(row=i+1, column=1, sticky=W, padx=(10, 0), pady=2)
            self.ip_vars[key] = var
            self.ip_entries[key] = entry

        ttk.Button(ip_frame, text="Appliquer", command=self._apply_ip, bootstyle=SUCCESS).grid(row=6, column=1, sticky=W, pady=(10, 0))

        # --- Profils ---
        prof_frame = ttk.LabelFrame(self, text="Profils", padding=10)
        prof_frame.pack(fill=X, padx=10, pady=5)

        self.profile_var = tk.StringVar()
        self.profile_cb = ttk.Combobox(prof_frame, textvariable=self.profile_var, width=25)
        self.profile_cb.pack(side=LEFT, padx=(0, 5))
        ttk.Button(prof_frame, text="Charger", command=self._load_profile, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(prof_frame, text="Sauvegarder", command=self._save_profile, bootstyle=PRIMARY).pack(side=LEFT, padx=2)
        ttk.Button(prof_frame, text="Supprimer", command=self._delete_profile, bootstyle=DANGER).pack(side=LEFT, padx=2)

        # --- Outils rapides ---
        tools_frame = ttk.LabelFrame(self, text="Outils rapides", padding=10)
        tools_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        btn_row = ttk.Frame(tools_frame)
        btn_row.pack(fill=X, pady=(0, 5))
        ttk.Button(btn_row, text="ipconfig /all", command=self._run_ipconfig, bootstyle=SECONDARY).pack(side=LEFT, padx=2)
        ttk.Button(btn_row, text="CMD Admin", command=self._open_cmd, bootstyle=WARNING).pack(side=LEFT, padx=2)

        self.output_text = tk.Text(tools_frame, height=10, font=("Consolas", 9), state=DISABLED)
        scroll = ttk.Scrollbar(tools_frame, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scroll.set)
        self.output_text.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        self._refresh_profiles()
        self._toggle_mode()

    def _refresh_interfaces(self):
        ifaces = list_interfaces()
        names = [f"{i['name']}  ({i['ip']})" for i in ifaces]
        self._ifaces_data = ifaces
        self.iface_cb["values"] = names
        if names:
            self.iface_cb.current(0)
            self._on_iface_selected()

    def _on_iface_selected(self, event=None):
        idx = self.iface_cb.current()
        if idx < 0:
            return
        iface_name = self._ifaces_data[idx]["name"]
        config = get_interface_config(iface_name)
        self.ip_vars["adresseip"].set(config.get("ip", ""))
        self.ip_vars["masque"].set(config.get("mask", ""))
        self.ip_vars["passerelle"].set(config.get("gateway", ""))
        self.ip_vars["dns1"].set(config.get("dns1", ""))
        self.ip_vars["dns2"].set(config.get("dns2", ""))

    def _toggle_mode(self):
        state = DISABLED if self.mode_var.get() == "dhcp" else NORMAL
        for entry in self.ip_entries.values():
            entry.configure(state=state)

    def _get_selected_iface(self) -> str | None:
        idx = self.iface_cb.current()
        if idx < 0:
            Messagebox.show_warning("Sélectionnez une carte réseau.", title="Attention")
            return None
        return self._ifaces_data[idx]["name"]

    def _apply_ip(self):
        iface = self._get_selected_iface()
        if not iface:
            return
        try:
            if self.mode_var.get() == "dhcp":
                apply_dhcp(iface)
            else:
                apply_static_ip(
                    iface,
                    self.ip_vars["adresseip"].get(),
                    self.ip_vars["masque"].get(),
                    self.ip_vars["passerelle"].get()
                )
                apply_dns(iface, self.ip_vars["dns1"].get(), self.ip_vars["dns2"].get())
            Messagebox.show_info("Configuration appliquée.", title="Succès")
        except Exception as e:
            Messagebox.show_error(str(e), title="Erreur")

    def _refresh_profiles(self):
        profiles = self.pm.list_profiles()
        self.profile_cb["values"] = sorted(profiles)

    def _load_profile(self):
        name = self.profile_var.get()
        if not name:
            return
        try:
            data = self.pm.load(name)
            self.mode_var.set("static")
            self._toggle_mode()
            self.ip_vars["adresseip"].set(data.get("ip", ""))
            self.ip_vars["masque"].set(data.get("mask", ""))
            self.ip_vars["passerelle"].set(data.get("gateway", ""))
            self.ip_vars["dns1"].set(data.get("dns1", ""))
            self.ip_vars["dns2"].set(data.get("dns2", ""))
        except FileNotFoundError as e:
            Messagebox.show_error(str(e), title="Erreur")

    def _save_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            Messagebox.show_warning("Entrez un nom de profil.", title="Attention")
            return
        data = {
            "ip": self.ip_vars["adresseip"].get(),
            "mask": self.ip_vars["masque"].get(),
            "gateway": self.ip_vars["passerelle"].get(),
            "dns1": self.ip_vars["dns1"].get(),
            "dns2": self.ip_vars["dns2"].get(),
        }
        self.pm.save(name, data)
        self._refresh_profiles()
        Messagebox.show_info(f"Profil '{name}' sauvegardé.", title="Succès")

    def _delete_profile(self):
        name = self.profile_var.get()
        if not name:
            return
        self.pm.delete(name)
        self._refresh_profiles()

    def _run_ipconfig(self):
        def _task():
            output = run_ipconfig()
            self.output_text.configure(state=NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, output)
            self.output_text.configure(state=DISABLED)
        threading.Thread(target=_task, daemon=True).start()

    def _open_cmd(self):
        subprocess.Popen(["cmd.exe"], creationflags=subprocess.CREATE_NEW_CONSOLE)
