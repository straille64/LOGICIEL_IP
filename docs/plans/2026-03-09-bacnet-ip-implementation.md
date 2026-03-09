# BACnet/IP V4 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ajouter un onglet BACnet/IP permettant la découverte Who-Is, la navigation Device→Objects→Properties, la lecture/écriture, le polling cyclique et les souscriptions COV.

**Architecture:** `core/bacnet.py` encapsule BAC0 (zéro tkinter), `modules/tab_bacnet.py` fait l'UI (zéro logique système), `modules/dialog_bacnet_obj.py` gère le popup Détails. Même pattern threading que tab_modbus.py : threads daemon + `self.after(0, cb)`.

**Tech Stack:** BAC0 (>=22.9), bacpypes3, ttkbootstrap, Python 3.14, pytest + unittest.mock

---

## Task 1 : Valider la compatibilité BAC0 + Python 3.14

**Files:**
- Modify: `requirements.txt`

**Step 1 : Installer BAC0 et vérifier l'import**

```bash
C:\Python314\python.exe -m pip install BAC0
```

Attendu : installation sans erreur.

**Step 2 : Tester l'import et détecter le problème netifaces**

```bash
C:\Python314\python.exe -c "import BAC0; print(BAC0.__version__)"
```

Si erreur `ModuleNotFoundError: netifaces` :

```bash
C:\Python314\python.exe -m pip install netifaces2
```

Si erreur `ImportError` sur netifaces2, utiliser psutil (déjà dans requirements.txt) — noter pour adapter `core/bacnet.py`.

**Step 3 : Vérifier l'API minimale**

```bash
C:\Python314\python.exe -c "
import BAC0
print(dir(BAC0))
# Vérifier la présence de : connect, lite, device
"
```

**Step 4 : Ajouter BAC0 à requirements.txt**

Ajouter à la fin de `requirements.txt` :
```
BAC0>=22.9
```

**Step 5 : Commit**

```bash
git add requirements.txt
git commit -m "feat: add BAC0 dependency for BACnet/IP V4"
```

---

## Task 2 : Structures de données et types d'erreurs (`core/bacnet.py`)

**Files:**
- Create: `core/bacnet.py`
- Create: `tests/test_bacnet.py`

**Step 1 : Écrire les tests des dataclasses**

Dans `tests/test_bacnet.py` :

```python
"""Tests unitaires core/bacnet.py — zéro matériel requis."""
from dataclasses import fields
from core.bacnet import DeviceInfo, ObjectRef
from core.bacnet import BACnetConnectionError, BACnetTimeoutError, BACnetWriteError


def test_device_info_fields():
    d = DeviceInfo(device_id=101, address="192.168.1.10", vendor_name="Siemens", object_name="CTR-101")
    assert d.device_id == 101
    assert d.address == "192.168.1.10"
    assert d.vendor_name == "Siemens"
    assert d.object_name == "CTR-101"


def test_object_ref_fields():
    o = ObjectRef(object_type="analogInput", instance=1, name="Température")
    assert o.object_type == "analogInput"
    assert o.instance == 1
    assert o.name == "Température"


def test_error_hierarchy():
    assert issubclass(BACnetConnectionError, Exception)
    assert issubclass(BACnetTimeoutError, Exception)
    assert issubclass(BACnetWriteError, Exception)
```

**Step 2 : Vérifier que les tests échouent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py -v
```

Attendu : `ModuleNotFoundError` ou `ImportError` — core/bacnet.py n'existe pas encore.

**Step 3 : Implémenter les dataclasses et erreurs**

Créer `core/bacnet.py` :

```python
"""core/bacnet.py — Client BACnet/IP encapsulant BAC0. Zéro import tkinter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


# ─── Types de données ─────────────────────────────────────────────────────────

@dataclass
class DeviceInfo:
    """Informations d'un équipement BACnet découvert."""
    device_id: int
    address: str
    vendor_name: str
    object_name: str


@dataclass
class ObjectRef:
    """Référence à un objet BACnet dans un device."""
    object_type: str   # ex. "analogInput", "binaryOutput"
    instance: int
    name: str


# ─── Exceptions ───────────────────────────────────────────────────────────────

class BACnetConnectionError(Exception):
    """Erreur de connexion BACnet (port occupé, réseau inaccessible)."""


class BACnetTimeoutError(Exception):
    """Timeout lors d'une requête BACnet."""


class BACnetWriteError(Exception):
    """Erreur d'écriture (objet non inscriptible, priorité refusée)."""
```

**Step 4 : Vérifier que les tests passent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py -v
```

Attendu : 3 PASSED.

**Step 5 : Commit**

```bash
git add core/bacnet.py tests/test_bacnet.py
git commit -m "feat: add BACnet core data structures and error types"
```

---

## Task 3 : `BACnetClient` — connect / disconnect / is_connected

**Files:**
- Modify: `core/bacnet.py`
- Modify: `tests/test_bacnet.py`

**Step 1 : Écrire les tests**

Ajouter dans `tests/test_bacnet.py` :

```python
from unittest.mock import patch, MagicMock
from core.bacnet import BACnetClient


def test_connect_sets_connected():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        client = BACnetClient()
        client.connect(local_ip="192.168.1.100/24")
        assert client.is_connected is True


def test_disconnect_clears_connected():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        client = BACnetClient()
        client.connect(local_ip="192.168.1.100/24")
        client.disconnect()
        assert client.is_connected is False
        mock_app.disconnect.assert_called_once()


def test_connect_with_bbmd():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_bac0.connect.return_value = MagicMock()
        client = BACnetClient()
        client.connect(local_ip="192.168.1.100/24", bbmd_address="10.0.0.1", bbmd_ttl=900)
        mock_bac0.connect.assert_called_once_with(
            ip="192.168.1.100/24",
            bbmdAddress="10.0.0.1",
            bbmdTTL=900,
        )


def test_connect_port_busy_raises():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_bac0.connect.side_effect = OSError("[WinError 10048] Adresse déjà utilisée")
        client = BACnetClient()
        with pytest.raises(BACnetConnectionError, match="47808"):
            client.connect(local_ip="192.168.1.100/24")
```

Ajouter `import pytest` en haut du fichier de test.

**Step 2 : Vérifier que les tests échouent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py::test_connect_sets_connected -v
```

Attendu : FAILED — `BACnetClient` n'existe pas.

**Step 3 : Implémenter connect/disconnect**

Ajouter dans `core/bacnet.py` après les imports :

```python
import BAC0  # noqa: E402  (import après les dataclasses pour faciliter le mock)


class BACnetClient:
    """Client BACnet/IP — encapsule BAC0, synchrone, thread-safe."""

    def __init__(self):
        self._app = None  # instance BAC0 active

    # ─── Connexion ────────────────────────────────────────────────────────────

    def connect(self, local_ip: str, bbmd_address: str | None = None,
                bbmd_ttl: int = 900) -> None:
        """Démarre l'application BACnet/IP locale.

        Args:
            local_ip: IP et masque CIDR de l'interface locale, ex. "192.168.1.100/24".
            bbmd_address: Adresse IP du BBMD (optionnel).
            bbmd_ttl: TTL d'enregistrement BBMD en secondes (défaut 900).

        Raises:
            BACnetConnectionError: Port UDP 47808 déjà utilisé ou réseau inaccessible.
        """
        kwargs: dict = {"ip": local_ip}
        if bbmd_address:
            kwargs["bbmdAddress"] = bbmd_address
            kwargs["bbmdTTL"] = bbmd_ttl
        try:
            self._app = BAC0.connect(**kwargs)
        except OSError as exc:
            raise BACnetConnectionError(
                f"Impossible de lier le port UDP 47808 : {exc}"
            ) from exc
        except Exception as exc:
            raise BACnetConnectionError(str(exc)) from exc

    def disconnect(self) -> None:
        """Stoppe l'application BACnet/IP."""
        if self._app is not None:
            try:
                self._app.disconnect()
            except Exception:
                pass
            self._app = None

    @property
    def is_connected(self) -> bool:
        return self._app is not None
```

**Step 4 : Vérifier que les tests passent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py -v
```

Attendu : tous PASSED.

**Step 5 : Commit**

```bash
git add core/bacnet.py tests/test_bacnet.py
git commit -m "feat: add BACnetClient connect/disconnect"
```

---

## Task 4 : `who_is()` — découverte des équipements

**Files:**
- Modify: `core/bacnet.py`
- Modify: `tests/test_bacnet.py`

**Step 1 : Écrire le test**

```python
def test_who_is_returns_device_list():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        # BAC0 expose les devices découverts dans app.devices
        # Format : liste de tuples (device_id, address, network_object)
        mock_app.whois.return_value = None  # who_is déclenche la découverte
        mock_app.devices = [
            ("101", "192.168.1.10"),
            ("205", "192.168.1.20"),
        ]
        # Pour chaque device, on lit object_name et vendor_name via read()
        def fake_read(addr_prop):
            if "objectName" in addr_prop:
                return "CTR-101" if "192.168.1.10" in addr_prop else "CTR-205"
            if "vendorName" in addr_prop:
                return "Siemens"
            return ""
        mock_app.read.side_effect = fake_read

        client = BACnetClient()
        client.connect("192.168.1.100/24")
        devices = client.who_is()

        assert len(devices) == 2
        assert devices[0].device_id == 101
        assert devices[0].address == "192.168.1.10"
        assert devices[0].object_name == "CTR-101"
```

**Step 2 : Vérifier que le test échoue**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py::test_who_is_returns_device_list -v
```

Attendu : FAILED.

**Step 3 : Implémenter who_is()**

> **Note importante :** L'API exacte de `app.devices` varie selon la version de BAC0.
> Si `app.devices` est un DataFrame pandas (BAC0 < 22), adapter l'itération.
> Si c'est une liste de tuples ou objets, adapter en conséquence.
> Vérifier avec : `C:\Python314\python.exe -c "import BAC0; b=BAC0.connect('...'); b.whois(); print(type(b.devices), b.devices)"`

Ajouter dans la classe `BACnetClient` :

```python
def who_is(self, timeout: float = 3.0) -> list[DeviceInfo]:
    """Lance un Who-Is broadcast et retourne les devices répondants.

    Raises:
        BACnetConnectionError: Si non connecté.
        BACnetTimeoutError: Si aucune réponse dans le délai.
    """
    if not self.is_connected:
        raise BACnetConnectionError("Non connecté")
    try:
        self._app.whois()
        import time; time.sleep(timeout)  # attente des réponses I-Am
        devices: list[DeviceInfo] = []
        for entry in self._app.devices:
            # entry est typiquement (device_id_str, address_str)
            dev_id = int(entry[0])
            address = str(entry[1])
            try:
                obj_name = self._app.read(
                    f"{address} device {dev_id} objectName"
                ) or ""
                vendor = self._app.read(
                    f"{address} device {dev_id} vendorName"
                ) or ""
            except Exception:
                obj_name, vendor = "", ""
            devices.append(DeviceInfo(
                device_id=dev_id,
                address=address,
                vendor_name=vendor,
                object_name=obj_name,
            ))
        return devices
    except BACnetConnectionError:
        raise
    except Exception as exc:
        raise BACnetTimeoutError(str(exc)) from exc
```

**Step 4 : Vérifier que les tests passent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py -v
```

Attendu : tous PASSED.

**Step 5 : Commit**

```bash
git add core/bacnet.py tests/test_bacnet.py
git commit -m "feat: add BACnetClient.who_is() device discovery"
```

---

## Task 5 : `get_object_list()` — liste des objets d'un device

**Files:**
- Modify: `core/bacnet.py`
- Modify: `tests/test_bacnet.py`

**Step 1 : Écrire le test**

```python
def test_get_object_list():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        # BAC0 retourne la objectList comme une liste de tuples (type, instance)
        mock_app.read.side_effect = lambda q: (
            [("analogInput", 1), ("binaryOutput", 1)]
            if "objectList" in q
            else ("Température" if "1 objectName" in q and "analogInput" in q else "Pompe")
        )
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "Siemens", "CTR-101")
        objects = client.get_object_list(device)
        assert len(objects) == 2
        assert objects[0].object_type == "analogInput"
        assert objects[0].instance == 1
        assert objects[1].object_type == "binaryOutput"
```

**Step 2 : Vérifier que le test échoue**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py::test_get_object_list -v
```

**Step 3 : Implémenter get_object_list()**

```python
def get_object_list(self, device: DeviceInfo) -> list[ObjectRef]:
    """Retourne la liste des objets d'un device via lecture de objectList.

    Raises:
        BACnetConnectionError: Si non connecté.
        BACnetTimeoutError: En cas de timeout.
    """
    if not self.is_connected:
        raise BACnetConnectionError("Non connecté")
    try:
        obj_list = self._app.read(
            f"{device.address} device {device.device_id} objectList"
        )
        objects: list[ObjectRef] = []
        for obj_type, instance in obj_list:
            try:
                name = self._app.read(
                    f"{device.address} {obj_type} {instance} objectName"
                ) or f"{obj_type}:{instance}"
            except Exception:
                name = f"{obj_type}:{instance}"
            objects.append(ObjectRef(
                object_type=str(obj_type),
                instance=int(instance),
                name=name,
            ))
        return objects
    except BACnetConnectionError:
        raise
    except Exception as exc:
        raise BACnetTimeoutError(str(exc)) from exc
```

**Step 4 : Vérifier que les tests passent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py -v
```

**Step 5 : Commit**

```bash
git add core/bacnet.py tests/test_bacnet.py
git commit -m "feat: add BACnetClient.get_object_list()"
```

---

## Task 6 : `read_present_value()` et `read_all_properties()`

**Files:**
- Modify: `core/bacnet.py`
- Modify: `tests/test_bacnet.py`

**Step 1 : Écrire les tests**

```python
def test_read_present_value():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        def fake_read(q):
            if "presentValue" in q:   return 21.5
            if "units" in q:          return "degreesCelsius"
            if "reliability" in q:    return "noFaultDetected"
            return None
        mock_app.read.side_effect = fake_read
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")
        value, unit, reliability = client.read_present_value(device, obj)
        assert value == 21.5
        assert unit == "degreesCelsius"
        assert reliability == "noFaultDetected"


def test_read_all_properties():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        mock_app.readMultiple.return_value = {
            "presentValue": 21.5,
            "objectName": "Température",
            "units": "degreesCelsius",
        }
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")
        props = client.read_all_properties(device, obj)
        assert props["presentValue"] == 21.5
        assert props["objectName"] == "Température"
```

**Step 2 : Vérifier que les tests échouent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py::test_read_present_value tests/test_bacnet.py::test_read_all_properties -v
```

**Step 3 : Implémenter les deux méthodes**

```python
def read_present_value(self, device: DeviceInfo,
                       obj: ObjectRef) -> tuple[Any, str, str]:
    """Lit presentValue, units et reliability d'un objet.

    Returns:
        (valeur, unité, reliability)

    Raises:
        BACnetConnectionError, BACnetTimeoutError
    """
    if not self.is_connected:
        raise BACnetConnectionError("Non connecté")
    addr = device.address
    ot, inst = obj.object_type, obj.instance
    try:
        value = self._app.read(f"{addr} {ot} {inst} presentValue")
        try:
            unit = str(self._app.read(f"{addr} {ot} {inst} units") or "")
        except Exception:
            unit = ""
        try:
            reliability = str(
                self._app.read(f"{addr} {ot} {inst} reliability") or ""
            )
        except Exception:
            reliability = ""
        return value, unit, reliability
    except BACnetConnectionError:
        raise
    except Exception as exc:
        raise BACnetTimeoutError(str(exc)) from exc


def read_all_properties(self, device: DeviceInfo,
                        obj: ObjectRef) -> dict[str, Any]:
    """Lit toutes les propriétés d'un objet via ReadPropertyMultiple.

    Raises:
        BACnetConnectionError, BACnetTimeoutError
    """
    if not self.is_connected:
        raise BACnetConnectionError("Non connecté")
    try:
        result = self._app.readMultiple(
            f"{device.address} {obj.object_type} {obj.instance} all"
        )
        if isinstance(result, dict):
            return result
        # Certaines versions de BAC0 retournent un objet avec attributs
        return {k: getattr(result, k, None) for k in dir(result)
                if not k.startswith("_")}
    except BACnetConnectionError:
        raise
    except Exception as exc:
        raise BACnetTimeoutError(str(exc)) from exc
```

**Step 4 : Vérifier que les tests passent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py -v
```

**Step 5 : Commit**

```bash
git add core/bacnet.py tests/test_bacnet.py
git commit -m "feat: add read_present_value and read_all_properties"
```

---

## Task 7 : `write_present_value()` et `subscribe_cov()`

**Files:**
- Modify: `core/bacnet.py`
- Modify: `tests/test_bacnet.py`

**Step 1 : Écrire les tests**

```python
def test_write_present_value():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogValue", 1, "Consigne")
        client.write_present_value(device, obj, 22.5, priority=8)
        mock_app.write.assert_called_once_with(
            "192.168.1.10 analogValue 1 presentValue 22.5 - 8"
        )


def test_write_present_value_raises_on_error():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        mock_app.write.side_effect = Exception("WriteAccessDenied")
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")  # lecture seule
        with pytest.raises(BACnetWriteError):
            client.write_present_value(device, obj, 21.0)


def test_subscribe_cov_returns_id():
    with patch("core.bacnet.BAC0") as mock_bac0:
        mock_app = MagicMock()
        mock_bac0.connect.return_value = mock_app
        mock_app.subscribe_cov.return_value = 42
        client = BACnetClient()
        client.connect("192.168.1.100/24")
        device = DeviceInfo(101, "192.168.1.10", "", "")
        obj = ObjectRef("analogInput", 1, "Temp")
        sub_id = client.subscribe_cov(device, obj, callback=lambda v: None)
        assert isinstance(sub_id, int)
```

**Step 2 : Vérifier que les tests échouent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py::test_write_present_value tests/test_bacnet.py::test_write_present_value_raises_on_error tests/test_bacnet.py::test_subscribe_cov_returns_id -v
```

**Step 3 : Implémenter write_present_value et subscribe_cov**

```python
def write_present_value(self, device: DeviceInfo, obj: ObjectRef,
                        value: Any, priority: int = 8) -> None:
    """Écrit presentValue avec la priorité donnée (1-16, défaut 8).

    Raises:
        BACnetConnectionError, BACnetWriteError
    """
    if not self.is_connected:
        raise BACnetConnectionError("Non connecté")
    cmd = (f"{device.address} {obj.object_type} {obj.instance} "
           f"presentValue {value} - {priority}")
    try:
        self._app.write(cmd)
    except Exception as exc:
        raise BACnetWriteError(str(exc)) from exc


def subscribe_cov(self, device: DeviceInfo, obj: ObjectRef,
                  callback: Callable[[Any], None]) -> int:
    """Souscrit aux changements de valeur (COV).

    Returns:
        subscription_id à passer à unsubscribe_cov().

    Raises:
        BACnetConnectionError, BACnetTimeoutError si COV non supporté.
    """
    if not self.is_connected:
        raise BACnetConnectionError("Non connecté")
    try:
        sub_id = self._app.subscribe_cov(
            f"{device.address} {obj.object_type} {obj.instance}",
            callback=callback,
        )
        return int(sub_id) if sub_id is not None else id(callback)
    except Exception as exc:
        raise BACnetTimeoutError(
            f"COV non supporté par cet objet : {exc}"
        ) from exc


def unsubscribe_cov(self, subscription_id: int) -> None:
    """Annule une souscription COV."""
    if not self.is_connected:
        return
    try:
        self._app.unsubscribe_cov(subscription_id)
    except Exception:
        pass
```

**Step 4 : Vérifier que les tests passent**

```bash
C:\Python314\python.exe -m pytest tests/test_bacnet.py -v
```

Attendu : tous PASSED.

**Step 5 : Commit**

```bash
git add core/bacnet.py tests/test_bacnet.py
git commit -m "feat: add write_present_value and subscribe/unsubscribe_cov"
```

---

## Task 8 : `TabBACnet` — squelette UI + barre réseau

**Files:**
- Create: `modules/tab_bacnet.py`

**Step 1 : Créer le squelette**

```python
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
        pane = ttk.PanedWindow(self, orient=HORIZONTAL)
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
```

**Step 2 : Enregistrer le tab dans main.py**

Dans `main.py`, ajouter l'import et l'onglet :

```python
# Ligne ~14 — après les autres imports modules :
from modules.tab_bacnet import TabBACnet
```

Dans `_load_icons()`, ajouter un 6ème icône :
```python
_load_icon("icones/BACnet.png"),   # index 5 — créer un PNG 22×22 ou mettre None
```

Dans `_build_tabs()`, ajouter :
```python
self._add_tab(TabBACnet(self.notebook), "  BACnet/IP  ", 5)
```

> Si l'icône BACnet.png n'existe pas, `_add_tab` l'ignore (comportement existant).

**Step 3 : Lancer l'application et vérifier que l'onglet apparaît**

```bash
C:\Python314\python.exe main.py
```

Attendu : onglet "BACnet/IP" visible, UI affichée sans erreur.

**Step 4 : Commit**

```bash
git add modules/tab_bacnet.py main.py
git commit -m "feat: add TabBACnet UI skeleton and register in main"
```

---

## Task 9 : Connexion, déconnexion, Who-Is (logique boutons)

**Files:**
- Modify: `modules/tab_bacnet.py`

**Step 1 : Implémenter _btn_connect**

Remplacer le stub `_btn_connect` :

```python
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
            self.after(0, lambda: self._set_status(f"Erreur : {exc}"))
            self.after(0, lambda: Messagebox.show_error(str(exc), "Connexion BACnet"))

    threading.Thread(target=_worker, daemon=True).start()
```

**Step 2 : Implémenter _btn_disconnect**

```python
def _btn_disconnect(self):
    self._stop_event.set()
    for sub_id in self._cov_subs.values():
        try: self.client.unsubscribe_cov(sub_id)
        except Exception: pass
    self._cov_subs.clear()
    self.client.disconnect()
    self._tree.delete(*self._tree.get_children())
    self._detail_tree.delete(*self._detail_tree.get_children())
    self._set_status("Déconnecté")
```

**Step 3 : Implémenter _btn_whois**

```python
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
            self.after(0, lambda: self._set_status(f"Who-Is échoué : {exc}"))

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
    self._set_status(f"Connecté — {len(devices)} device(s) trouvé(s)")
```

**Step 4 : Tester manuellement**

```bash
C:\Python314\python.exe main.py
```

Cliquer Connexion → Who-Is. Vérifier que les devices apparaissent dans le Treeview.

**Step 5 : Commit**

```bash
git add modules/tab_bacnet.py
git commit -m "feat: implement connect/disconnect/whois in TabBACnet"
```

---

## Task 10 : Lazy loading des objets dans le Treeview

**Files:**
- Modify: `modules/tab_bacnet.py`

**Step 1 : Implémenter _on_device_expand**

Remplacer le stub :

```python
def _on_device_expand(self, event):
    node_id = self._tree.focus()
    if not node_id.startswith("dev_"):
        return
    children = self._tree.get_children(node_id)
    # Si le seul enfant est le nœud fantôme "loading_", lancer la requête
    if len(children) == 1 and str(children[0]).startswith("loading_"):
        dev_id = int(node_id.split("_")[1])
        address = self._tree.item(node_id, "values")[0]
        device = DeviceInfo(dev_id, address, "", "")
        self._load_objects(node_id, device)

def _load_objects(self, node_id: str, device):
    from core.bacnet import DeviceInfo  # import local pour éviter cycle

    def _worker():
        try:
            objects = self.client.get_object_list(device)
            self.after(0, lambda: self._add_object_nodes(node_id, objects))
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"Objets : {exc}"))

    threading.Thread(target=_worker, daemon=True).start()

def _add_object_nodes(self, node_id: str, objects):
    # Supprimer le nœud fantôme
    for child in self._tree.get_children(node_id):
        self._tree.delete(child)
    for obj in objects:
        label = f"{obj.object_type}:{obj.instance}  —  {obj.name}"
        self._tree.insert(node_id, END,
                          iid=f"obj_{node_id}_{obj.object_type}_{obj.instance}",
                          text=label,
                          values=[obj.object_type, obj.instance, obj.name])
```

**Step 2 : Tester manuellement**

Lancer l'appli, connecter, Who-Is, cliquer sur un device pour le déplier.
Attendu : les objets apparaissent après un bref délai de chargement.

**Step 3 : Commit**

```bash
git add modules/tab_bacnet.py
git commit -m "feat: add lazy object loading in BACnet Treeview"
```

---

## Task 11 : Tableau propriétés + polling cyclique

**Files:**
- Modify: `modules/tab_bacnet.py`

**Step 1 : Implémenter _on_object_select**

```python
def _on_object_select(self, event):
    sel = self._tree.selection()
    if not sel:
        return
    node_id = sel[0]
    if not node_id.startswith("obj_"):
        return
    # node_id format : "obj_dev_NNN_type_instance"
    values = self._tree.item(node_id, "values")
    if not values or len(values) < 3:
        return
    obj_type, instance, name = str(values[0]), int(values[1]), str(values[2])
    # Remonter au device parent
    parent_id = self._tree.parent(node_id)
    parent_values = self._tree.item(parent_id, "values")
    if not parent_values:
        return
    address, dev_id = str(parent_values[0]), int(parent_values[1])

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
            self.after(0, lambda: self._update_detail_row(
                self._selected_object, value, unit, reliability
            ))
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"Lecture : {exc}"))

    threading.Thread(target=_worker, daemon=True).start()

def _update_detail_row(self, obj, value, unit, reliability):
    self._detail_tree.delete(*self._detail_tree.get_children())
    self._detail_tree.insert("", END, values=(
        obj.name, obj.object_type, str(value), reliability, unit
    ))
```

**Step 2 : Implémenter _on_poll_toggle**

```python
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
```

**Step 3 : Tester manuellement**

Sélectionner un objet, cocher Polling → vérifier que la valeur se rafraîchit.

**Step 4 : Commit**

```bash
git add modules/tab_bacnet.py
git commit -m "feat: add object selection, detail table and cyclic polling"
```

---

## Task 12 : Écriture de valeur + COV

**Files:**
- Modify: `modules/tab_bacnet.py`

**Step 1 : Implémenter _btn_write**

```python
def _btn_write(self):
    if not hasattr(self, "_selected_object"):
        return
    from ttkbootstrap.dialogs import Querybox
    val_str = Querybox.get_string(
        prompt=f"Nouvelle valeur pour {self._selected_object.name} :",
        title="Écrire valeur",
    )
    if val_str is None:
        return
    # Sélecteur priorité simplifié via Querybox
    prio_str = Querybox.get_string(
        prompt="Priorité BACnet (1-16, défaut 8) :",
        title="Priorité",
        initialvalue="8",
    )
    try:
        priority = int(prio_str or "8")
        priority = max(1, min(16, priority))
    except ValueError:
        priority = 8
    try:
        # Tenter float, puis int, puis string
        try:    value = float(val_str)
        except ValueError: value = val_str
        self.client.write_present_value(
            self._selected_device, self._selected_object, value, priority
        )
        self._set_status(f"Écriture réussie : {value} (priorité {priority})")
        self._refresh_detail()
    except Exception as exc:
        Messagebox.show_error(str(exc), "Erreur d'écriture")
```

**Step 2 : Implémenter _on_cov_toggle**

```python
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
                # Bascule silencieuse en polling
                self.after(0, lambda: self._var_cov.set(False))
                self.after(0, lambda: self._var_poll.set(True))
                self.after(0, self._on_poll_toggle)
                self.after(0, lambda: self._set_status(
                    f"COV non supporté, polling activé ({exc})"
                ))
        threading.Thread(target=_subscribe, daemon=True).start()
    else:
        if key in self._cov_subs:
            try: self.client.unsubscribe_cov(self._cov_subs.pop(key))
            except Exception: pass
        self._set_status("COV désactivé")
```

**Step 3 : Tester manuellement**

Tester l'écriture sur un AV inscriptible. Tester COV sur un AI.

**Step 4 : Commit**

```bash
git add modules/tab_bacnet.py
git commit -m "feat: add write_present_value and COV toggle in TabBACnet"
```

---

## Task 13 : Popup "Détails complets" (`dialog_bacnet_obj.py`)

**Files:**
- Create: `modules/dialog_bacnet_obj.py`
- Modify: `modules/tab_bacnet.py`

**Step 1 : Créer le popup**

```python
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
```

**Step 2 : Connecter à _btn_details dans tab_bacnet.py**

Remplacer le stub `_btn_details` :

```python
def _btn_details(self):
    if not hasattr(self, "_selected_device"):
        return
    self._set_status("Lecture des propriétés complètes…")

    def _worker():
        try:
            props = self.client.read_all_properties(
                self._selected_device, self._selected_object
            )
            self.after(0, lambda: self._open_details_dialog(props))
        except Exception as exc:
            self.after(0, lambda: Messagebox.show_error(str(exc), "Détails"))

    threading.Thread(target=_worker, daemon=True).start()

def _open_details_dialog(self, props: dict):
    from modules.dialog_bacnet_obj import BACnetObjectDialog
    BACnetObjectDialog(self, self._selected_object.name, props)
    self._set_status("Prêt")
```

**Step 3 : Tester manuellement**

Sélectionner un objet, cliquer "Détails complets". Vérifier que le popup s'ouvre avec les propriétés.

**Step 4 : Commit**

```bash
git add modules/dialog_bacnet_obj.py modules/tab_bacnet.py
git commit -m "feat: add BACnetObjectDialog for full property details"
```

---

## Task 14 : Tests unitaires UI (smoke tests TabBACnet)

**Files:**
- Create: `tests/test_tab_bacnet.py`

**Step 1 : Écrire les smoke tests**

```python
"""Smoke tests pour TabBACnet — vérifie que l'UI se construit sans erreur."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture()
def root():
    import ttkbootstrap as ttk
    r = ttk.Window(themename="darkly")
    yield r
    r.destroy()


def test_tab_bacnet_builds(root):
    from modules.tab_bacnet import TabBACnet
    tab = TabBACnet(root)
    assert tab.winfo_exists()


def test_tab_bacnet_has_client(root):
    from modules.tab_bacnet import TabBACnet
    from core.bacnet import BACnetClient
    tab = TabBACnet(root)
    assert isinstance(tab.client, BACnetClient)
```

**Step 2 : Lancer les tests**

```bash
C:\Python314\python.exe -m pytest tests/test_tab_bacnet.py tests/test_bacnet.py -v
```

Attendu : tous PASSED.

**Step 3 : Commit**

```bash
git add tests/test_tab_bacnet.py
git commit -m "test: add smoke tests for TabBACnet"
```

---

## Task 15 : Finalisation — requirements.txt et vérification globale

**Files:**
- Modify: `requirements.txt`

**Step 1 : Vérifier requirements.txt final**

```
ttkbootstrap>=1.10.1
psutil>=5.9.0
pyinstaller>=6.0.0
pytest>=7.4.0
mac-vendor-lookup>=0.1.12

pymodbus>=3.12.0
pyserial>=3.5
pyMeterBus>=0.8.4

BAC0>=22.9
```

**Step 2 : Lancer la suite de tests complète**

```bash
C:\Python314\python.exe -m pytest tests/ -v
```

Attendu : tous PASSED (zéro erreur).

**Step 3 : Lancer l'application**

```bash
C:\Python314\python.exe main.py
```

Vérifier : onglet BACnet/IP visible, connexion, Who-Is, navigation Treeview, lecture, écriture, polling, COV, popup détails.

**Step 4 : Commit final**

```bash
git add requirements.txt
git commit -m "feat: complete BACnet/IP V4 tab — discovery, read/write, polling, COV"
```
