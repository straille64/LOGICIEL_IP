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

    def who_is(self, timeout: float = 3.0) -> list[DeviceInfo]:
        """Lance un Who-Is broadcast et retourne les devices répondants.

        Args:
            timeout: Durée d'attente des réponses I-Am en secondes.

        Returns:
            Liste de DeviceInfo pour chaque device ayant répondu.

        Raises:
            BACnetConnectionError: Si non connecté.
            BACnetTimeoutError: En cas d'erreur réseau.
        """
        if not self.is_connected:
            raise BACnetConnectionError("Non connecté")
        import time
        try:
            self._app.whois()
            time.sleep(timeout)
            if self._app is None:
                return []
            devices: list[DeviceInfo] = []
            for entry in self._app.devices:
                dev_id = int(entry[0])
                address = str(entry[1])
                try:
                    obj_name = self._app.read(
                        f"{address} device {dev_id} objectName"
                    ) or ""
                except Exception:
                    obj_name = ""
                try:
                    vendor = self._app.read(
                        f"{address} device {dev_id} vendorName"
                    ) or ""
                except Exception:
                    vendor = ""
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

    def read_present_value(self, device: DeviceInfo,
                           obj: ObjectRef) -> tuple[Any, str, str]:
        """Lit presentValue, units et reliability d'un objet.

        Returns:
            Tuple (valeur, unité, reliability).

        Raises:
            BACnetConnectionError: Si non connecté.
            BACnetTimeoutError: En cas d'erreur réseau.
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
            BACnetConnectionError: Si non connecté.
            BACnetTimeoutError: En cas d'erreur réseau.
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

    def write_present_value(self, device: DeviceInfo, obj: ObjectRef,
                            value: Any, priority: int = 8) -> None:
        """Écrit presentValue avec la priorité donnée (1-16, défaut 8).

        Raises:
            BACnetConnectionError: Si non connecté.
            BACnetWriteError: Si l'objet refuse l'écriture.
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
            BACnetConnectionError: Si non connecté.
            BACnetTimeoutError: Si COV non supporté ou timeout.
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
        """Annule une souscription COV. Silencieux si non connecté."""
        if not self.is_connected:
            return
        try:
            self._app.unsubscribe_cov(subscription_id)
        except Exception:
            pass

    def get_object_list(self, device: DeviceInfo) -> list[ObjectRef]:
        """Retourne la liste des objets d'un device via lecture de objectList.

        Raises:
            BACnetConnectionError: Si non connecté.
            BACnetTimeoutError: En cas de timeout ou d'erreur réseau.
        """
        if not self.is_connected:
            raise BACnetConnectionError("Non connecté")
        try:
            obj_list = self._app.read(
                f"{device.address} device {device.device_id} objectList"
            )
            objects: list[ObjectRef] = []
            for item in obj_list:
                obj_type = str(item[0])
                instance = int(item[1])
                try:
                    name = self._app.read(
                        f"{device.address} {obj_type} {instance} objectName"
                    ) or f"{obj_type}:{instance}"
                except Exception:
                    name = f"{obj_type}:{instance}"
                objects.append(ObjectRef(
                    object_type=obj_type,
                    instance=instance,
                    name=name,
                ))
            return objects
        except BACnetConnectionError:
            raise
        except Exception as exc:
            raise BACnetTimeoutError(str(exc)) from exc
