"""tests/test_dialog_detail.py — Tests unitaires des calculs de RegisterDetailDialog."""
import struct
import pytest
from modules.dialog_register_detail import decode_registers, fmt_bin_byte, fmt_ascii_byte, fmt_reel32


# ─── decode_registers ─────────────────────────────────────────────────────────

def test_decode_no_swap():
    # w0=0x1234, w1=0x5678 → combined=0x12345678
    # b3=0x12=18, b2=0x34=52, b1=0x56=86, b0=0x78=120
    assert decode_registers(0x1234, 0x5678) == (0x12, 0x34, 0x56, 0x78)

def test_decode_swap_words():
    # swap_words : hi=w1, lo=w0 → combined=0x56781234
    assert decode_registers(0x1234, 0x5678, swap_words=True) == (0x56, 0x78, 0x12, 0x34)

def test_decode_swap_bytes():
    # swap_bytes : échange b3↔b2 et b1↔b0
    # sans swap: (0x12, 0x34, 0x56, 0x78) → avec: (0x34, 0x12, 0x78, 0x56)
    assert decode_registers(0x1234, 0x5678, swap_bytes=True) == (0x34, 0x12, 0x78, 0x56)

def test_decode_both_swaps():
    b3, b2, b1, b0 = decode_registers(0x1234, 0x5678, swap_words=True, swap_bytes=True)
    # swap_words → (0x56, 0x78, 0x12, 0x34), swap_bytes → (0x78, 0x56, 0x34, 0x12)
    assert (b3, b2, b1, b0) == (0x78, 0x56, 0x34, 0x12)


# ─── Helpers de formatage ─────────────────────────────────────────────────────

def test_fmt_bin_byte():
    assert fmt_bin_byte(0b10110010) == "10110010"
    assert fmt_bin_byte(0) == "00000000"
    assert fmt_bin_byte(255) == "11111111"

def test_fmt_ascii_byte_printable():
    assert fmt_ascii_byte(ord("A")) == "A"
    assert fmt_ascii_byte(ord(" ")) == " "

def test_fmt_ascii_byte_non_printable():
    assert fmt_ascii_byte(0) == "."
    assert fmt_ascii_byte(31) == "."
    assert fmt_ascii_byte(127) == "."

def test_fmt_reel32():
    # IEEE 754 : 0x3F800000 = 1.0
    result = fmt_reel32(0x3F80, 0x0000)
    assert result == "1.0"

def test_fmt_reel32_nan():
    # Valeur qui génère NaN → retourne quelque chose contenant "N"
    result = fmt_reel32(0x7FC0, 0x0000)
    assert "N" in result.upper()


from modules.dialog_register_detail import (
    parse_bin_byte, parse_octet, parse_mot16, parse_mot32, parse_reel32_to_words
)

def test_parse_bin_byte_valid():
    assert parse_bin_byte("10110010") == 178

def test_parse_bin_byte_zero():
    assert parse_bin_byte("00000000") == 0

def test_parse_bin_byte_invalid():
    with pytest.raises(ValueError):
        parse_bin_byte("xyz")

def test_parse_octet_decimal():
    assert parse_octet("255") == 255

def test_parse_octet_hex():
    assert parse_octet("0xFF") == 255

def test_parse_octet_out_of_range():
    with pytest.raises(ValueError):
        parse_octet("300")

def test_parse_mot16():
    assert parse_mot16("0x1234") == 0x1234

def test_parse_mot16_negative_raises():
    with pytest.raises(ValueError):
        parse_mot16("-1")

def test_parse_mot32_split():
    val = parse_mot32("0x12345678")
    assert (val >> 16) == 0x1234
    assert (val & 0xFFFF) == 0x5678

def test_parse_reel32_to_words():
    w0, w1 = parse_reel32_to_words("1.0")
    assert w0 == 0x3F80
    assert w1 == 0x0000
