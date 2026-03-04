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
