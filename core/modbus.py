"""core/modbus.py — Wrapper synchrone pymodbus. Zéro import tkinter."""
import struct
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ConnectionException, ModbusException


class ModbusClient:
    """Client Modbus TCP ou RTU/Serial.

    Usage:
        mc = ModbusClient()
        mc.connect_tcp("192.168.1.10", 502)
        values = mc.read_holding_registers(slave_id=1, address=0, count=10)
        mc.disconnect()
    """

    def __init__(self):
        self._client = None

    # ─── Connexion ──────────────────────────────────────────────────────────

    def connect_tcp(self, host: str, port: int = 502, timeout: float = 3.0) -> None:
        """Connecte en Modbus TCP. Lève ConnectionException si échec."""
        self._client = ModbusTcpClient(host, port=port, timeout=timeout)
        if not self._client.connect():
            self._client = None
            raise ConnectionException(f"Impossible de se connecter à {host}:{port}")

    def connect_rtu(
        self,
        port: str,
        baudrate: int = 9600,
        parity: str = "N",
        bytesize: int = 8,
        stopbits: int = 1,
        timeout: float = 1.0,
    ) -> None:
        """Connecte en Modbus RTU via port série. Lève ConnectionException si échec."""
        self._client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            bytesize=bytesize,
            stopbits=stopbits,
            timeout=timeout,
        )
        if not self._client.connect():
            self._client = None
            raise ConnectionException(f"Impossible d'ouvrir le port {port}")

    def disconnect(self) -> None:
        """Déconnecte et libère le client."""
        if self._client:
            self._client.close()
            self._client = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.connected

    # ─── Vérification interne ───────────────────────────────────────────────

    def _check(self) -> None:
        if not self._client:
            raise ConnectionException("Non connecté")

    def _check_error(self, response, label: str) -> None:
        if response.isError():
            raise ModbusException(f"{label} : {response}")

    # ─── Lecture (FC1–FC4) ──────────────────────────────────────────────────

    def read_coils(self, slave_id: int, address: int, count: int) -> list:
        """FC1 — Lit des coils (bits R/W). Retourne list[bool]."""
        self._check()
        rr = self._client.read_coils(address, count, slave=slave_id)
        self._check_error(rr, "FC1 read_coils")
        return list(rr.bits[:count])

    def read_discrete_inputs(self, slave_id: int, address: int, count: int) -> list:
        """FC2 — Lit des entrées discrètes (bits RO). Retourne list[bool]."""
        self._check()
        rr = self._client.read_discrete_inputs(address, count, slave=slave_id)
        self._check_error(rr, "FC2 read_discrete_inputs")
        return list(rr.bits[:count])

    def read_holding_registers(self, slave_id: int, address: int, count: int) -> list:
        """FC3 — Lit des holding registers (mots R/W). Retourne list[int]."""
        self._check()
        rr = self._client.read_holding_registers(address, count, slave=slave_id)
        self._check_error(rr, "FC3 read_holding_registers")
        return list(rr.registers)

    def read_input_registers(self, slave_id: int, address: int, count: int) -> list:
        """FC4 — Lit des input registers (mots RO). Retourne list[int]."""
        self._check()
        rr = self._client.read_input_registers(address, count, slave=slave_id)
        self._check_error(rr, "FC4 read_input_registers")
        return list(rr.registers)

    # ─── Écriture (FC5, FC6, FC15, FC16) ────────────────────────────────────

    def write_coil(self, slave_id: int, address: int, value: bool) -> None:
        """FC5 — Écrit 1 coil."""
        self._check()
        rr = self._client.write_coil(address, value, slave=slave_id)
        self._check_error(rr, "FC5 write_coil")

    def write_register(self, slave_id: int, address: int, value: int) -> None:
        """FC6 — Écrit 1 registre (16 bits)."""
        self._check()
        rr = self._client.write_register(address, value, slave=slave_id)
        self._check_error(rr, "FC6 write_register")

    def write_coils(self, slave_id: int, address: int, values: list) -> None:
        """FC15 — Écrit plusieurs coils. values: list[bool]."""
        self._check()
        rr = self._client.write_coils(address, values, slave=slave_id)
        self._check_error(rr, "FC15 write_coils")

    def write_registers(self, slave_id: int, address: int, values: list) -> None:
        """FC16 — Écrit plusieurs registres. values: list[int]."""
        self._check()
        rr = self._client.write_registers(address, values, slave=slave_id)
        self._check_error(rr, "FC16 write_registers")


# ─── Utilitaire de formatage ─────────────────────────────────────────────────

def format_register_value(
    raw,
    display_mode: str,
    num_base: str = "dec",
    swap_bytes: bool = False,
    swap_words: bool = False,
    unsigned: bool = True,
) -> str:
    """Formate une valeur brute Modbus selon le mode d'affichage.

    Args:
        raw: int (1 registre) ou list[int] (>=2 registres pour float32/int32/uint32)
        display_mode: "uint16" | "int16" | "float32" | "uint32" | "int32" | "bin" | "ascii"
        num_base: "dec" | "hex" | "bin" (s'applique uniquement aux entiers)
        swap_bytes: inverser les octets dans chaque mot 16 bits
        swap_words: inverser l'ordre des deux mots pour les formats 32 bits
        unsigned: si True, int16 traité comme uint16
    """
    if isinstance(raw, (list, tuple)):
        r0 = int(raw[0]) if len(raw) > 0 else 0
        r1 = int(raw[1]) if len(raw) > 1 else 0
    else:
        r0 = int(raw)
        r1 = 0

    if swap_bytes:
        r0 = ((r0 & 0xFF) << 8) | ((r0 >> 8) & 0xFF)
        r1 = ((r1 & 0xFF) << 8) | ((r1 >> 8) & 0xFF)

    def _int_fmt(val: int) -> str:
        if num_base == "hex":
            return f"0x{val:X}"
        if num_base == "bin":
            return f"{val:016b}"
        return str(val)

    match display_mode:
        case "uint16":
            return _int_fmt(r0 & 0xFFFF)

        case "int16":
            v = r0 & 0xFFFF
            if v >= 0x8000:
                v -= 0x10000
            return _int_fmt(v) if num_base != "hex" else f"0x{r0 & 0xFFFF:X}"

        case "float32":
            if swap_words:
                combined = ((r1 & 0xFFFF) << 16) | (r0 & 0xFFFF)
            else:
                combined = ((r0 & 0xFFFF) << 16) | (r1 & 0xFFFF)
            try:
                value = struct.unpack(">f", combined.to_bytes(4, "big"))[0]
                return f"{value:.4f}"
            except Exception:
                return "NaN"

        case "uint32":
            if swap_words:
                combined = ((r1 & 0xFFFF) << 16) | (r0 & 0xFFFF)
            else:
                combined = ((r0 & 0xFFFF) << 16) | (r1 & 0xFFFF)
            return _int_fmt(combined)

        case "int32":
            if swap_words:
                combined = ((r1 & 0xFFFF) << 16) | (r0 & 0xFFFF)
            else:
                combined = ((r0 & 0xFFFF) << 16) | (r1 & 0xFFFF)
            if combined >= 0x80000000:
                combined -= 0x100000000
            return str(combined)

        case "bin":
            return f"{r0 & 0xFFFF:016b}"

        case "ascii":
            high = (r0 >> 8) & 0xFF
            low = r0 & 0xFF
            return "".join(chr(b) if 32 <= b < 127 else "." for b in [high, low])

        case _:
            return str(r0)
