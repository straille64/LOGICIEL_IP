# modules/tab_config.py
import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox, Querybox
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
        self._refresh_tree()

    # ------------------------------------------------------------------ layout

    def _build(self):
        paned = ttk.PanedWindow(self, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=5, pady=5)

        left = ttk.Frame(paned, width=210)
        paned.add(left, weight=0)

        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self._build_tree(left)
        self._build_form(right)

    # ------------------------------------------------------------------ tree pane

    def _build_tree(self, parent):
        ttk.Label(parent, text="Profils", font=("", 10, "bold")).pack(
            anchor=W, padx=5, pady=(5, 3)
        )

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True, padx=5)

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        scroll = ttk.Scrollbar(tree_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=X, padx=5, pady=(5, 0))
        ttk.Button(btn_frame, text="+ Dossier", command=self._new_folder,
                   bootstyle=SECONDARY).pack(side=LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="Sauvegarder ici", command=self._save_profile,
                   bootstyle=PRIMARY).pack(side=LEFT)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        tree_data = self.pm.list_tree()
        for name in sorted(tree_data.get("", [])):
            self.tree.insert("", "end", iid=f"profile::::{name}", text=f"  {name}")
        for folder in sorted(k for k in tree_data if k):
            f_iid = f"folder::{folder}"
            self.tree.insert("", "end", iid=f_iid, text=f"\U0001f4c1 {folder}", open=True)
            for name in sorted(tree_data[folder]):
                self.tree.insert(f_iid, "end",
                                  iid=f"profile::{folder}::{name}", text=f"  {name}")

    def _on_tree_double_click(self, event):
        iid = self.tree.focus()
        if not iid or not iid.startswith("profile::"):
            return
        parts = iid.split("::")
        if len(parts) < 3:
            return
        folder, name = parts[1], parts[2]
        self._load_profile(name, folder)

    def _on_tree_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.focus(iid)
        menu = tk.Menu(self, tearoff=0)
        if iid and iid.startswith("folder::"):
            folder = iid[len("folder::"):]
            menu.add_command(label="Supprimer le dossier",
                             command=lambda: self._delete_folder(folder))
        elif iid and iid.startswith("profile::"):
            parts = iid.split("::")
            if len(parts) < 3:
                return
            folder, name = parts[1], parts[2]
            menu.add_command(label="Supprimer le profil",
                             command=lambda: self._delete_profile_node(name, folder))
        else:
            menu.add_command(label="Nouveau dossier", command=self._new_folder)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _new_folder(self):
        name = Querybox.get_string("Nom du dossier :", title="Nouveau dossier")
        if name and self._validate_name(name.strip()):
            self.pm.create_folder(name.strip())
            self._refresh_tree()

    def _save_profile(self):
        iid = self.tree.focus()
        folder = ""
        if iid and iid.startswith("folder::"):
            folder = iid[len("folder::"):]
        elif iid and iid.startswith("profile::"):
            folder = iid.split("::")[1]
        name = Querybox.get_string("Nom du profil :", title="Sauvegarder le profil")
        if not name or not self._validate_name(name.strip()):
            return
        data = {
            "ip": self.ip_vars["adresseip"].get(),
            "mask": self.ip_vars["masque"].get(),
            "gateway": self.ip_vars["passerelle"].get(),
            "dns1": self.ip_vars["dns1"].get(),
            "dns2": self.ip_vars["dns2"].get(),
        }
        self.pm.save(name.strip(), data, folder)
        self._refresh_tree()
        Messagebox.show_info(f"Profil '{name.strip()}' sauvegardé.", title="Succès")

    def _load_profile(self, name: str, folder: str = ""):
        try:
            data = self.pm.load(name, folder)
            self.mode_var.set("static")
            self._toggle_mode()
            self.ip_vars["adresseip"].set(data.get("ip", ""))
            self.ip_vars["masque"].set(data.get("mask", ""))
            self.ip_vars["passerelle"].set(data.get("gateway", ""))
            self.ip_vars["dns1"].set(data.get("dns1", ""))
            self.ip_vars["dns2"].set(data.get("dns2", ""))
        except FileNotFoundError as e:
            Messagebox.show_error(str(e), title="Erreur")

    def _delete_profile_node(self, name: str, folder: str = ""):
        if not Messagebox.okcancel(f"Supprimer le profil '{name}' ?", title="Confirmation"):
            return
        self.pm.delete(name, folder)
        self._refresh_tree()

    def _delete_folder(self, folder: str):
        if not Messagebox.okcancel(f"Supprimer le dossier '{folder}' et tous ses profils ?", title="Confirmation"):
            return
        self.pm.delete_folder(folder)
        self._refresh_tree()

    def _validate_name(self, name: str) -> bool:
        """Return True if name is safe for use as a filesystem entry and tree IID."""
        forbidden = set('<>:"/\\|?*')
        if not name or name.strip() != name:
            return False
        if any(c in forbidden for c in name):
            Messagebox.show_warning(
                "Le nom ne doit pas contenir les caractères : < > : \" / \\ | ? *",
                title="Nom invalide"
            )
            return False
        if "::" in name:
            Messagebox.show_warning("Le nom ne doit pas contenir '::'.", title="Nom invalide")
            return False
        return True

    # ------------------------------------------------------------------ form pane

    def _build_form(self, parent):
        iface_frame = ttk.LabelFrame(parent, text="Carte réseau")
        iface_frame.pack(fill=X, padx=5, pady=(5, 5))

        self.iface_var = tk.StringVar()
        self.iface_cb = ttk.Combobox(iface_frame, textvariable=self.iface_var,
                                      state="readonly", width=40)
        self.iface_cb.pack(side=LEFT, padx=(5, 10), pady=5)
        self.iface_cb.bind("<<ComboboxSelected>>", self._on_iface_selected)
        ttk.Button(iface_frame, text="↺ Rafraîchir",
                   command=self._refresh_interfaces,
                   bootstyle=SECONDARY).pack(side=LEFT, pady=5)

        ip_frame = ttk.LabelFrame(parent, text="Configuration IP")
        ip_frame.pack(fill=X, padx=5, pady=5)

        self.mode_var = tk.StringVar(value="dhcp")
        ttk.Radiobutton(ip_frame, text="DHCP", variable=self.mode_var,
                        value="dhcp", command=self._toggle_mode).grid(
            row=0, column=0, sticky=W, padx=5, pady=(5, 2))
        ttk.Radiobutton(ip_frame, text="Manuel", variable=self.mode_var,
                        value="static", command=self._toggle_mode).grid(
            row=0, column=1, sticky=W)

        labels = ["Adresse IP", "Masque", "Passerelle", "DNS 1", "DNS 2"]
        self.ip_vars = {}
        self.ip_entries = {}
        for i, label in enumerate(labels):
            key = label.lower().replace(" ", "").replace("é", "e")
            ttk.Label(ip_frame, text=label).grid(
                row=i + 1, column=0, sticky=W, padx=5, pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(ip_frame, textvariable=var, width=20)
            entry.grid(row=i + 1, column=1, sticky=W, padx=(5, 10), pady=2)
            self.ip_vars[key] = var
            self.ip_entries[key] = entry

        ttk.Button(ip_frame, text="Appliquer", command=self._apply_ip,
                   bootstyle=SUCCESS).grid(
            row=6, column=1, sticky=W, padx=5, pady=(10, 5))

        tools_frame = ttk.LabelFrame(parent, text="Outils rapides")
        tools_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        btn_row = ttk.Frame(tools_frame)
        btn_row.pack(fill=X, pady=(5, 5))
        ttk.Button(btn_row, text="ipconfig /all", command=self._run_ipconfig,
                   bootstyle=SECONDARY).pack(side=LEFT, padx=(5, 3))
        ttk.Button(btn_row, text="CMD Admin", command=self._open_cmd,
                   bootstyle=WARNING).pack(side=LEFT)

        self.output_text = tk.Text(tools_frame, height=10,
                                   font=("Consolas", 9), state=DISABLED)
        scroll = ttk.Scrollbar(tools_frame, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scroll.set)
        self.output_text.pack(side=LEFT, fill=BOTH, expand=True,
                               padx=(5, 0), pady=(0, 5))
        scroll.pack(side=RIGHT, fill=Y, pady=(0, 5))

        self._toggle_mode()

    # ------------------------------------------------------------------ interfaces

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
        config = get_interface_config(self._ifaces_data[idx]["name"])
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
                    self.ip_vars["passerelle"].get(),
                )
                apply_dns(iface, self.ip_vars["dns1"].get(),
                          self.ip_vars["dns2"].get())
            Messagebox.show_info("Configuration appliquée.", title="Succès")
        except Exception as e:
            Messagebox.show_error(str(e), title="Erreur")

    # ------------------------------------------------------------------ tools

    def _run_ipconfig(self):
        def _task():
            output = run_ipconfig()
            self.after(0, lambda: self._display_ipconfig(output))
        threading.Thread(target=_task, daemon=True).start()

    def _display_ipconfig(self, output: str):
        self.output_text.configure(state=NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, output)
        self.output_text.configure(state=DISABLED)

    def _open_cmd(self):
        subprocess.Popen(["cmd.exe"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
