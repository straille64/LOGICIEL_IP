# LOGICIEL_IP V1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a standalone Windows `.exe` for network configuration and diagnostics with a modular tabbed GUI.

**Architecture:** tkinter + ttkbootstrap window with a `ttk.Notebook` tab system. Each tab is an autonomous `ttk.Frame` class in `modules/`. All system/network operations live in `core/` (no UI imports) and run in background threads to keep the UI responsive.

**Tech Stack:** Python 3.11+, ttkbootstrap, psutil, PyInstaller, pytest, unittest.mock

---

## Pre-requisites

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install ttkbootstrap psutil pyinstaller pytest
```

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `main.py`
- Create: `core/__init__.py`
- Create: `modules/__init__.py`
- Create: `tests/__init__.py`
- Create: `profiles/` (empty folder — add `.gitkeep`)
- Create: `assets/` (empty folder — add `.gitkeep`)

**Step 1: Create requirements.txt**

```
ttkbootstrap>=1.10.1
psutil>=5.9.0
pyinstaller>=6.0.0
pytest>=7.4.0
```

**Step 2: Create empty init files and folders**

```bash
touch core/__init__.py modules/__init__.py tests/__init__.py
mkdir profiles assets
touch profiles/.gitkeep assets/.gitkeep
```

**Step 3: Create main.py skeleton**

```python
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
```

**Step 4: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold project structure"
```

---

### Task 2: core/profiles.py

**Files:**
- Create: `core/profiles.py`
- Create: `tests/test_profiles.py`

**Step 1: Write failing tests**

```python
# tests/test_profiles.py
import json
import os
import pytest
from core.profiles import ProfileManager


@pytest.fixture
def manager(tmp_path):
    return ProfileManager(profiles_dir=str(tmp_path))


def test_save_and_load_profile(manager):
    data = {"ip": "192.168.1.10", "mask": "255.255.255.0",
            "gateway": "192.168.1.1", "dns1": "8.8.8.8", "dns2": "8.8.4.4"}
    manager.save("Client_Test", data)
    result = manager.load("Client_Test")
    assert result == data


def test_list_profiles(manager):
    manager.save("Prof_A", {"ip": "10.0.0.1", "mask": "", "gateway": "", "dns1": "", "dns2": ""})
    manager.save("Prof_B", {"ip": "10.0.0.2", "mask": "", "gateway": "", "dns1": "", "dns2": ""})
    assert set(manager.list_profiles()) == {"Prof_A", "Prof_B"}


def test_delete_profile(manager):
    manager.save("ToDelete", {"ip": "1.1.1.1", "mask": "", "gateway": "", "dns1": "", "dns2": ""})
    manager.delete("ToDelete")
    assert "ToDelete" not in manager.list_profiles()


def test_load_nonexistent_raises(manager):
    with pytest.raises(FileNotFoundError):
        manager.load("DoesNotExist")
```

**Step 2: Run to confirm failure**

```bash
pytest tests/test_profiles.py -v
```
Expected: 4 errors — `ModuleNotFoundError: core.profiles`

**Step 3: Implement core/profiles.py**

```python
# core/profiles.py
import json
import os


class ProfileManager:
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.profiles_dir, f"{name}.json")

    def save(self, name: str, data: dict) -> None:
        with open(self._path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, name: str) -> dict:
        path = self._path(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Profil '{name}' introuvable.")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def list_profiles(self) -> list[str]:
        return [f[:-5] for f in os.listdir(self.profiles_dir) if f.endswith(".json")]

    def delete(self, name: str) -> None:
        path = self._path(name)
        if os.path.exists(path):
            os.remove(path)
```

**Step 4: Run tests**

```bash
pytest tests/test_profiles.py -v
```
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add core/profiles.py tests/test_profiles.py
git commit -m "feat: add profile save/load manager"
```

---

### Task 3: core/network.py

**Files:**
- Create: `core/network.py`
- Create: `tests/test_network.py`

**Step 1: Write failing tests**

```python
# tests/test_network.py
import pytest
from unittest.mock import patch, MagicMock
from core.network import list_interfaces, get_interface_config, apply_static_ip, apply_dhcp


def test_list_interfaces_returns_list():
    result = list_interfaces()
    assert isinstance(result, list)
    assert len(result) > 0  # au moins une interface sur toute machine Windows


def test_list_interfaces_have_name_and_ip():
    result = list_interfaces()
    for iface in result:
        assert "name" in iface
        assert "ip" in iface


@patch("core.network.subprocess.run")
def test_apply_static_ip_calls_netsh(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    apply_static_ip("Ethernet", "192.168.1.50", "255.255.255.0", "192.168.1.1")
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "netsh" in cmd
    assert "192.168.1.50" in cmd


@patch("core.network.subprocess.run")
def test_apply_dhcp_calls_netsh(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    apply_dhcp("Ethernet")
    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "dhcp" in cmd.lower()
```

**Step 2: Run to confirm failure**

```bash
pytest tests/test_network.py -v
```
Expected: errors — `ModuleNotFoundError: core.network`

**Step 3: Implement core/network.py**

```python
# core/network.py
import subprocess
import psutil
import socket


def list_interfaces() -> list[dict]:
    """Retourne les interfaces réseau actives avec leur IP."""
    interfaces = []
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    for name, addr_list in addrs.items():
        if name not in stats or not stats[name].isup:
            continue
        ip = ""
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                ip = addr.address
                break
        interfaces.append({"name": name, "ip": ip})
    return interfaces


def get_interface_config(iface_name: str) -> dict:
    """Retourne la config IP complète d'une interface."""
    addrs = psutil.net_if_addrs().get(iface_name, [])
    result = {"ip": "", "mask": "", "gateway": "", "dns1": "", "dns2": ""}
    for addr in addrs:
        if addr.family == socket.AF_INET:
            result["ip"] = addr.address
            result["mask"] = addr.netmask or ""
    # Passerelle via route table
    gateways = psutil.net_if_stats()
    try:
        gws = psutil.net_if_addrs()
        import subprocess as sp
        out = sp.run(["netsh", "interface", "ip", "show", "config", f"name={iface_name}"],
                     capture_output=True, text=True).stdout
        for line in out.splitlines():
            if "Default Gateway" in line or "Passerelle" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    result["gateway"] = parts[1].strip()
            if "DNS" in line and not result["dns1"]:
                parts = line.split(":")
                if len(parts) > 1:
                    val = parts[1].strip()
                    if val and val[0].isdigit():
                        if not result["dns1"]:
                            result["dns1"] = val
                        elif not result["dns2"]:
                            result["dns2"] = val
    except Exception:
        pass
    return result


def apply_static_ip(iface_name: str, ip: str, mask: str, gateway: str) -> None:
    """Applique une IP statique. Requiert droits admin."""
    subprocess.run(
        ["netsh", "interface", "ip", "set", "address",
         f"name={iface_name}", "source=static",
         f"addr={ip}", f"mask={mask}", f"gateway={gateway}"],
        check=True, capture_output=True
    )


def apply_dns(iface_name: str, dns1: str, dns2: str = "") -> None:
    """Configure les serveurs DNS. Requiert droits admin."""
    subprocess.run(
        ["netsh", "interface", "ip", "set", "dns",
         f"name={iface_name}", "source=static", f"addr={dns1}"],
        check=True, capture_output=True
    )
    if dns2:
        subprocess.run(
            ["netsh", "interface", "ip", "add", "dns",
             f"name={iface_name}", f"addr={dns2}", "index=2"],
            check=True, capture_output=True
        )


def apply_dhcp(iface_name: str) -> None:
    """Passe l'interface en DHCP. Requiert droits admin."""
    subprocess.run(
        ["netsh", "interface", "ip", "set", "address",
         f"name={iface_name}", "source=dhcp"],
        check=True, capture_output=True
    )
    subprocess.run(
        ["netsh", "interface", "ip", "set", "dns",
         f"name={iface_name}", "source=dhcp"],
        check=True, capture_output=True
    )


def run_ipconfig() -> str:
    """Retourne la sortie de ipconfig /all."""
    result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, encoding="cp850")
    return result.stdout
```

**Step 4: Run tests**

```bash
pytest tests/test_network.py -v
```
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add core/network.py tests/test_network.py
git commit -m "feat: add network interface management"
```

---

### Task 4: core/scanner.py

**Files:**
- Create: `core/scanner.py`
- Create: `tests/test_scanner.py`

**Step 1: Write failing tests**

```python
# tests/test_scanner.py
import pytest
from unittest.mock import patch
from core.scanner import ping_host, generate_ip_range


def test_generate_ip_range():
    ips = generate_ip_range("192.168.1.1", "192.168.1.5")
    assert ips == [
        "192.168.1.1", "192.168.1.2", "192.168.1.3",
        "192.168.1.4", "192.168.1.5"
    ]


def test_generate_ip_range_same():
    ips = generate_ip_range("10.0.0.1", "10.0.0.1")
    assert ips == ["10.0.0.1"]


def test_generate_ip_range_cross_octet():
    ips = generate_ip_range("192.168.0.254", "192.168.1.1")
    assert "192.168.0.254" in ips
    assert "192.168.0.255" in ips
    assert "192.168.1.0" in ips
    assert "192.168.1.1" in ips


@patch("core.scanner.subprocess.run")
def test_ping_host_alive(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Minimum = 2ms"
    result = ping_host("192.168.1.1", timeout_ms=500)
    assert result["alive"] is True
    assert result["ip"] == "192.168.1.1"


@patch("core.scanner.subprocess.run")
def test_ping_host_dead(mock_run):
    mock_run.return_value.returncode = 1
    mock_run.return_value.stdout = ""
    result = ping_host("192.168.1.99", timeout_ms=500)
    assert result["alive"] is False
```

**Step 2: Run to confirm failure**

```bash
pytest tests/test_scanner.py -v
```
Expected: errors — `ModuleNotFoundError: core.scanner`

**Step 3: Implement core/scanner.py**

```python
# core/scanner.py
import subprocess
import socket
import re
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable


def generate_ip_range(start_ip: str, end_ip: str) -> list[str]:
    """Génère la liste des IPs entre start et end inclus."""
    start = int(ipaddress.ip_address(start_ip))
    end = int(ipaddress.ip_address(end_ip))
    return [str(ipaddress.ip_address(i)) for i in range(start, end + 1)]


def ping_host(ip: str, timeout_ms: int = 500) -> dict:
    """Ping une IP. Retourne {'ip', 'alive', 'rtt_ms', 'hostname'}."""
    result = {"ip": ip, "alive": False, "rtt_ms": None, "hostname": ""}
    try:
        proc = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), ip],
            capture_output=True, text=True, timeout=(timeout_ms / 1000) + 2
        )
        if proc.returncode == 0:
            result["alive"] = True
            match = re.search(r"Minimum\s*=\s*(\d+)ms|temps[=<](\d+)\s*ms", proc.stdout, re.IGNORECASE)
            if match:
                val = match.group(1) or match.group(2)
                result["rtt_ms"] = int(val)
            try:
                result["hostname"] = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                result["hostname"] = ""
    except subprocess.TimeoutExpired:
        pass
    return result


def scan_range(
    start_ip: str,
    end_ip: str,
    timeout_ms: int = 500,
    max_threads: int = 50,
    progress_callback: Callable[[int, int], None] | None = None,
    stop_event=None
) -> list[dict]:
    """Scan une plage IP en parallèle. Appelle progress_callback(done, total) à chaque résultat."""
    ips = generate_ip_range(start_ip, end_ip)
    total = len(ips)
    results = []
    done = 0

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(ping_host, ip, timeout_ms): ip for ip in ips}
        for future in as_completed(futures):
            if stop_event and stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                break
            result = future.result()
            results.append(result)
            done += 1
            if progress_callback:
                progress_callback(done, total)

    return sorted(results, key=lambda r: [int(x) for x in r["ip"].split(".")])
```

**Step 4: Run tests**

```bash
pytest tests/test_scanner.py -v
```
Expected: 5 PASSED

**Step 5: Commit**

```bash
git add core/scanner.py tests/test_scanner.py
git commit -m "feat: add IP range scanner with threading"
```

---

### Task 5: modules/tab_config.py

**Files:**
- Create: `modules/tab_config.py`

> Pas de tests unitaires automatisés pour l'UI — test manuel décrit en fin de tâche.

**Step 1: Créer tab_config.py**

```python
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
```

**Step 2: Test manuel**

```bash
python main.py
```
Vérifier :
- [ ] Dropdown liste les interfaces réseau
- [ ] Clic Rafraîchir recharge la liste
- [ ] Champs IP se remplissent au changement d'interface
- [ ] Radio DHCP désactive les champs
- [ ] Bouton ipconfig /all affiche la sortie
- [ ] Bouton CMD Admin ouvre une fenêtre cmd
- [ ] Sauvegarder crée un fichier dans `profiles/`
- [ ] Charger remplit les champs
- [ ] Supprimer retire le profil du dropdown

**Step 3: Commit**

```bash
git add modules/tab_config.py
git commit -m "feat: add configuration tab with profiles and tools"
```

---

### Task 6: modules/tab_scanner.py

**Files:**
- Create: `modules/tab_scanner.py`

**Step 1: Créer tab_scanner.py**

```python
# modules/tab_scanner.py
import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tableview import Tableview
from datetime import datetime
import csv
import os

from core.scanner import scan_range, ping_host


class TabScanner(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._scan_stop = threading.Event()
        self._ping_stop = threading.Event()
        self._build()

    def _build(self):
        # ── SCAN DE PLAGE ──────────────────────────────────────
        scan_frame = ttk.LabelFrame(self, text="Scan de plage IP", padding=10)
        scan_frame.pack(fill=X, padx=10, pady=(10, 5))

        row1 = ttk.Frame(scan_frame)
        row1.pack(fill=X, pady=(0, 5))
        ttk.Label(row1, text="De :").pack(side=LEFT)
        self.scan_start = ttk.Entry(row1, width=16)
        self.scan_start.insert(0, "192.168.1.1")
        self.scan_start.pack(side=LEFT, padx=5)
        ttk.Label(row1, text="À :").pack(side=LEFT)
        self.scan_end = ttk.Entry(row1, width=16)
        self.scan_end.insert(0, "192.168.1.254")
        self.scan_end.pack(side=LEFT, padx=5)
        ttk.Label(row1, text="Timeout (ms) :").pack(side=LEFT, padx=(10, 0))
        self.scan_timeout = ttk.Spinbox(row1, from_=100, to=5000, increment=100, width=7)
        self.scan_timeout.set(500)
        self.scan_timeout.pack(side=LEFT, padx=5)
        ttk.Label(row1, text="Threads :").pack(side=LEFT)
        self.scan_threads = ttk.Spinbox(row1, from_=1, to=200, increment=10, width=6)
        self.scan_threads.set(50)
        self.scan_threads.pack(side=LEFT, padx=5)

        row2 = ttk.Frame(scan_frame)
        row2.pack(fill=X)
        self.btn_scan_start = ttk.Button(row2, text="▶ Lancer", command=self._start_scan, bootstyle=SUCCESS)
        self.btn_scan_start.pack(side=LEFT, padx=(0, 5))
        self.btn_scan_stop = ttk.Button(row2, text="■ Stop", command=self._stop_scan, bootstyle=DANGER, state=DISABLED)
        self.btn_scan_stop.pack(side=LEFT, padx=(0, 10))
        self.scan_status = ttk.Label(row2, text="")
        self.scan_status.pack(side=LEFT)

        self.scan_progress = ttk.Progressbar(scan_frame, mode="determinate")
        self.scan_progress.pack(fill=X, pady=(5, 0))

        # Tableau résultats
        cols = [
            {"text": "Adresse IP", "stretch": False, "width": 130},
            {"text": "Nom d'hôte", "stretch": True},
            {"text": "Statut", "stretch": False, "width": 80},
            {"text": "RTT (ms)", "stretch": False, "width": 80},
        ]
        self.table = Tableview(scan_frame, coldata=cols, rowdata=[], paginate=False,
                               bootstyle=INFO, stripecolor=None, height=8)
        self.table.pack(fill=BOTH, expand=True, pady=(5, 0))

        export_row = ttk.Frame(scan_frame)
        export_row.pack(fill=X, pady=(5, 0))
        ttk.Button(export_row, text="Exporter CSV", command=self._export_csv, bootstyle=SECONDARY).pack(side=LEFT, padx=(0, 5))
        self.scan_count = ttk.Label(export_row, text="")
        self.scan_count.pack(side=LEFT)

        # ── PING CONTINU ───────────────────────────────────────
        ping_frame = ttk.LabelFrame(self, text="Ping continu", padding=10)
        ping_frame.pack(fill=BOTH, expand=True, padx=10, pady=(5, 10))

        ping_row = ttk.Frame(ping_frame)
        ping_row.pack(fill=X, pady=(0, 5))
        ttk.Label(ping_row, text="Cible :").pack(side=LEFT)
        self.ping_target = ttk.Entry(ping_row, width=20)
        self.ping_target.insert(0, "192.168.1.1")
        self.ping_target.pack(side=LEFT, padx=5)
        ttk.Label(ping_row, text="Intervalle :").pack(side=LEFT)
        self.ping_interval = ttk.Combobox(ping_row, values=["1s", "2s", "5s"], width=5, state="readonly")
        self.ping_interval.current(0)
        self.ping_interval.pack(side=LEFT, padx=5)
        self.btn_ping_start = ttk.Button(ping_row, text="▶ Démarrer", command=self._start_ping, bootstyle=SUCCESS)
        self.btn_ping_start.pack(side=LEFT, padx=(10, 5))
        self.btn_ping_stop = ttk.Button(ping_row, text="■ Stop", command=self._stop_ping, bootstyle=DANGER, state=DISABLED)
        self.btn_ping_stop.pack(side=LEFT, padx=(0, 5))
        ttk.Button(ping_row, text="💾 Sauvegarder log", command=self._save_ping_log, bootstyle=SECONDARY).pack(side=LEFT, padx=5)

        self.ping_text = tk.Text(ping_frame, height=8, font=("Consolas", 9), state=DISABLED)
        scroll = ttk.Scrollbar(ping_frame, command=self.ping_text.yview)
        self.ping_text.configure(yscrollcommand=scroll.set)
        self.ping_text.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        stats_row = ttk.Frame(ping_frame)
        stats_row.pack(fill=X, pady=(5, 0))
        self.ping_stats = ttk.Label(stats_row, text="Envoyés: 0  Reçus: 0  Perdus: 0  Perte: 0%")
        self.ping_stats.pack(side=LEFT)
        self._ping_sent = self._ping_recv = self._ping_lost = 0

    # ── SCAN ─────────────────────────────────────────────────────────────────

    def _start_scan(self):
        self._scan_stop.clear()
        self.table.delete_rows()
        self.scan_progress["value"] = 0
        self.scan_count.configure(text="")
        self.btn_scan_start.configure(state=DISABLED)
        self.btn_scan_stop.configure(state=NORMAL)

        start = self.scan_start.get().strip()
        end = self.scan_end.get().strip()
        timeout = int(self.scan_timeout.get())
        threads = int(self.scan_threads.get())

        self._scan_results = []

        def _progress(done, total):
            pct = int(done / total * 100)
            self.after(0, lambda: self.scan_progress.configure(value=pct))
            self.after(0, lambda: self.scan_status.configure(text=f"{done}/{total}"))

        def _run():
            results = scan_range(start, end, timeout, threads, _progress, self._scan_stop)
            self._scan_results = results
            self.after(0, self._populate_table)

        threading.Thread(target=_run, daemon=True).start()

    def _stop_scan(self):
        self._scan_stop.set()
        self.btn_scan_start.configure(state=NORMAL)
        self.btn_scan_stop.configure(state=DISABLED)

    def _populate_table(self):
        alive = [r for r in self._scan_results if r["alive"]]
        for r in self._scan_results:
            status = "● EN" if r["alive"] else "○ OFF"
            rtt = str(r["rtt_ms"]) if r["rtt_ms"] is not None else "—"
            self.table.insert_row("end", [r["ip"], r["hostname"], status, rtt])
        self.table.load_table_data()
        self.scan_count.configure(text=f"{len(alive)} actifs / {len(self._scan_results)} scannés")
        self.btn_scan_start.configure(state=NORMAL)
        self.btn_scan_stop.configure(state=DISABLED)

    def _export_csv(self):
        if not self._scan_results:
            return
        path = os.path.join(os.getcwd(), f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ip", "hostname", "alive", "rtt_ms"])
            writer.writeheader()
            writer.writerows(self._scan_results)

    # ── PING CONTINU ─────────────────────────────────────────────────────────

    def _start_ping(self):
        self._ping_stop.clear()
        self._ping_sent = self._ping_recv = self._ping_lost = 0
        self.ping_text.configure(state=NORMAL)
        self.ping_text.delete("1.0", tk.END)
        self.ping_text.configure(state=DISABLED)
        self.btn_ping_start.configure(state=DISABLED)
        self.btn_ping_stop.configure(state=NORMAL)

        target = self.ping_target.get().strip()
        interval = int(self.ping_interval.get().replace("s", ""))

        def _run():
            import time
            while not self._ping_stop.is_set():
                result = ping_host(target, timeout_ms=1000)
                ts = datetime.now().strftime("%H:%M:%S")
                self._ping_sent += 1
                if result["alive"]:
                    self._ping_recv += 1
                    line = f"{ts}  {target}  ●  RTT: {result['rtt_ms']}ms\n"
                else:
                    self._ping_lost += 1
                    line = f"{ts}  {target}  ○  Timeout\n"
                pct = round(self._ping_lost / self._ping_sent * 100, 1)
                stats = f"Envoyés: {self._ping_sent}  Reçus: {self._ping_recv}  Perdus: {self._ping_lost}  Perte: {pct}%"
                self.after(0, lambda l=line, s=stats: self._append_ping(l, s))
                self._ping_stop.wait(timeout=interval)

        threading.Thread(target=_run, daemon=True).start()

    def _append_ping(self, line: str, stats: str):
        self.ping_text.configure(state=NORMAL)
        self.ping_text.insert(tk.END, line)
        self.ping_text.see(tk.END)
        self.ping_text.configure(state=DISABLED)
        self.ping_stats.configure(text=stats)

    def _stop_ping(self):
        self._ping_stop.set()
        self.btn_ping_start.configure(state=NORMAL)
        self.btn_ping_stop.configure(state=DISABLED)

    def _save_ping_log(self):
        content = self.ping_text.get("1.0", tk.END)
        path = os.path.join(os.getcwd(), f"ping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
```

**Step 2: Test manuel**

```bash
python main.py
```
Vérifier :
- [ ] Onglet Scanner Réseau s'affiche
- [ ] Lancer scan → barre de progression avance
- [ ] Tableau se remplit avec IP + statut
- [ ] Stop interrompt le scan
- [ ] Export CSV crée un fichier
- [ ] Ping continu affiche les lignes horodatées
- [ ] Compteurs Envoyés/Reçus/Perdus se mettent à jour
- [ ] Stop ping arrête la boucle
- [ ] Sauvegarder log crée un .txt

**Step 3: Commit**

```bash
git add modules/tab_scanner.py
git commit -m "feat: add network scanner and continuous ping tab"
```

---

### Task 7: UAC manifest + build PyInstaller

**Files:**
- Create: `app.manifest`
- Create: `build.spec`

**Step 1: Créer le manifest UAC**

```xml
<!-- app.manifest -->
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>
```

**Step 2: Créer build.spec**

```python
# build.spec
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('profiles', 'profiles'), ('assets', 'assets')],
    hiddenimports=['ttkbootstrap', 'psutil'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='LOGICIEL_IP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    manifest='app.manifest',
    icon='assets/icon.ico' if __import__('os').path.exists('assets/icon.ico') else None,
)
```

**Step 3: Build l'exe**

```bash
pyinstaller build.spec --clean
```
L'exe sera dans `dist/LOGICIEL_IP.exe`

**Step 4: Test manuel**

- Lancer `dist/LOGICIEL_IP.exe` → UAC demande l'élévation
- Vérifier que les 2 onglets fonctionnent
- Vérifier que les profils sont créés dans le dossier de l'exe

**Step 5: Commit final V1**

```bash
git add app.manifest build.spec
git commit -m "feat: add UAC manifest and PyInstaller build config"
git tag v1.0.0
```

---

## Résumé des commandes de dev

```bash
# Lancer en dev
python main.py

# Tests unitaires
pytest tests/ -v

# Tests avec couverture
pytest tests/ -v --tb=short

# Build exe
pyinstaller build.spec --clean
```

## Dépendances V1

```
ttkbootstrap>=1.10.1
psutil>=5.9.0
pyinstaller>=6.0.0
pytest>=7.4.0
```
