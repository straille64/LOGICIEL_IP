"""core/bacnet.py — Client BACnet/IP encapsulant BAC0. Zéro import tkinter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import BAC0 as BAC0  # import module-level pour permettre le mock


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


# ─── Client BACnet/IP ─────────────────────────────────────────────────────────

class BACnetClient:
    """Client BACnet/IP — encapsule BAC0, synchrone, thread-safe."""

    def __init__(self):
        self._app = None  # instance BAC0 active

    def connect(self, local_ip: str, bbmd_address: str | None = None,
                bbmd_ttl: int = 900) -> None:
        """Démarre l'application BACnet/IP locale.

        Args:
            local_ip: IP et masque CIDR, ex. "192.168.1.100/24".
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
