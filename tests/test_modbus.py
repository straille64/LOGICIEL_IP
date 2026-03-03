"""Tests unitaires pour core/modbus.py — aucun matériel Modbus requis (tout est mocké)."""
import struct
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from pymodbus.exceptions import ConnectionException, ModbusException
from core.modbus import ModbusClient, format_register_value


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return ModbusClient()


@pytest.fixture
def connected_client():
    """ModbusClient avec un faux client pymodbus déjà connecté."""
    c = ModbusClient()
    mock_inner = MagicMock()
    type(mock_inner).connected = PropertyMock(return_value=True)
    mock_inner.connect.return_value = True
    c._client = mock_inner
    return c, mock_inner


# ─── Connexion TCP ───────────────────────────────────────────────────────────

@patch("core.modbus.ModbusTcpClient")
def test_connect_tcp_sets_connected(MockTCP):
    instance = MagicMock()
    instance.connect.return_value = True
    type(instance).connected = PropertyMock(return_value=True)
    MockTCP.return_value = instance
    c = ModbusClient()
    c.connect_tcp("127.0.0.1", 502)
    assert c.is_connected


@patch("core.modbus.ModbusTcpClient")
def test_connect_tcp_failure_raises(MockTCP):
    instance = MagicMock()
    instance.connect.return_value = False
    MockTCP.return_value = instance
    c = ModbusClient()
    with pytest.raises(ConnectionException):
        c.connect_tcp("127.0.0.1", 502)


# ─── Connexion RTU ───────────────────────────────────────────────────────────

@patch("core.modbus.ModbusSerialClient")
def test_connect_rtu_sets_connected(MockRTU):
    instance = MagicMock()
    instance.connect.return_value = True
    type(instance).connected = PropertyMock(return_value=True)
    MockRTU.return_value = instance
    c = ModbusClient()
    c.connect_rtu("COM3", 9600)
    assert c.is_connected


# ─── Déconnexion ─────────────────────────────────────────────────────────────

def test_disconnect_clears_client(client):
    mock_inner = MagicMock()
    client._client = mock_inner
    client.disconnect()
    assert client._client is None
    mock_inner.close.assert_called_once()


def test_is_connected_false_when_no_client(client):
    assert not client.is_connected


# ─── Lecture FC3 ─────────────────────────────────────────────────────────────

def test_read_holding_registers_returns_list(connected_client):
    c, mock_inner = connected_client
    resp = MagicMock()
    resp.isError.return_value = False
    resp.registers = [100, 200, 300]
    mock_inner.read_holding_registers.return_value = resp
    result = c.read_holding_registers(1, 0, 3)
    assert result == [100, 200, 300]
    mock_inner.read_holding_registers.assert_called_once_with(0, 3, slave=1)


def test_read_raises_when_not_connected(client):
    with pytest.raises(ConnectionException):
        client.read_holding_registers(1, 0, 10)


# ─── Lecture FC1 ─────────────────────────────────────────────────────────────

def test_read_coils_returns_bool_list(connected_client):
    c, mock_inner = connected_client
    resp = MagicMock()
    resp.isError.return_value = False
    resp.bits = [True, False, True, False, False, False, False, False]
    mock_inner.read_coils.return_value = resp
    result = c.read_coils(1, 0, 3)
    assert result == [True, False, True]


# ─── Écriture FC5 ────────────────────────────────────────────────────────────

def test_write_coil_calls_fc5(connected_client):
    c, mock_inner = connected_client
    resp = MagicMock()
    resp.isError.return_value = False
    mock_inner.write_coil.return_value = resp
    c.write_coil(1, 5, True)
    mock_inner.write_coil.assert_called_once_with(5, True, slave=1)


# ─── Écriture FC6 ────────────────────────────────────────────────────────────

def test_write_register_calls_fc6(connected_client):
    c, mock_inner = connected_client
    resp = MagicMock()
    resp.isError.return_value = False
    mock_inner.write_register.return_value = resp
    c.write_register(1, 10, 1500)
    mock_inner.write_register.assert_called_once_with(10, 1500, slave=1)


# ─── Erreur Modbus remontée ───────────────────────────────────────────────────

def test_read_raises_on_modbus_error(connected_client):
    c, mock_inner = connected_client
    resp = MagicMock()
    resp.isError.return_value = True
    mock_inner.read_holding_registers.return_value = resp
    with pytest.raises(ModbusException):
        c.read_holding_registers(1, 0, 1)


# ─── format_register_value ───────────────────────────────────────────────────

def test_format_uint16():
    assert format_register_value(1450, "uint16") == "1450"


def test_format_int16_negative():
    # 0xFFFF = 65535 unsigned = -1 signed
    assert format_register_value(65535, "int16") == "-1"


def test_format_hex():
    assert format_register_value(255, "uint16", num_base="hex") == "0xFF"


def test_format_bin():
    assert format_register_value(0b1010101010101010, "bin") == "1010101010101010"


def test_format_float32():
    # IEEE 754 float 1.0 = 0x3F800000
    raw = struct.pack(">f", 1.0)
    hi = (raw[0] << 8) | raw[1]   # 0x3F80
    lo = (raw[2] << 8) | raw[3]   # 0x0000
    result = format_register_value([hi, lo], "float32")
    assert float(result) == pytest.approx(1.0, abs=1e-4)


def test_format_ascii():
    # 0x4865 = "He"
    result = format_register_value(0x4865, "ascii")
    assert result == "He"


def test_format_int16_unsigned_flag():
    # unsigned=True → traiter comme uint16, 65535 reste 65535
    assert format_register_value(65535, "int16", unsigned=True) == "65535"


def test_format_int16_bin_negative():
    # num_base="bin" sur valeur négative (int16) → ne doit pas lever ValueError
    # 0xFFFF = -1 en int16, mais en bin doit afficher les bits bruts
    result = format_register_value(65535, "int16", num_base="bin")
    assert result == "1111111111111111"  # 16 bits bruts


def test_format_int32_hex():
    # int32 avec num_base="hex" doit retourner hex
    # 0x00010002 = 65538 en uint32
    result = format_register_value([1, 2], "int32", num_base="hex")
    assert result == "0x10002"
