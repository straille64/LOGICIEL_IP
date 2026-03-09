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
