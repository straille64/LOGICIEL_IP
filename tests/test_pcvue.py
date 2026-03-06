"""tests/test_pcvue.py — Tests unitaires de core/pcvue.py."""
import pytest
from core.pcvue import (
    generer_table_variables,
    traiter_donnees_entree,
    get_max_quantite,
)


# ─── get_max_quantite ─────────────────────────────────────────────────────────

def test_max_mot_standard():
    assert get_max_quantite("MOT", "Word I") == 128

def test_max_mot_information():
    assert get_max_quantite("MOT", "Information") == 5535

def test_max_mot_command():
    assert get_max_quantite("MOT", "Command") == 5535

def test_max_reel():
    assert get_max_quantite("REEL", "Real I LMsb") == 64

def test_max_bit():
    assert get_max_quantite("BIT", "Bit I") == 2048


# ─── generer_table_variables — DOUBLE MOT ─────────────────────────────────────

def test_gen_double_mot_adresses():
    rows = generer_table_variables("DOUBLE MOT", "DWord I LMsb", 14408, 3)
    assert [r["adresse"] for r in rows] == [
        "DWord I LMsb 14408",
        "DWord I LMsb 14410",
        "DWord I LMsb 14412",
    ]

def test_gen_double_mot_offsets():
    rows = generer_table_variables("DOUBLE MOT", "DWord I LMsb", 0, 3)
    assert [r["index_offset"] for r in rows] == [
        "0 - (0 / 0)",
        "1 - (4 / 0)",
        "2 - (8 / 0)",
    ]


# ─── generer_table_variables — REEL ───────────────────────────────────────────

def test_gen_reel_adresses():
    rows = generer_table_variables("REEL", "Real I/O LMsb", 100, 2)
    assert rows[0]["adresse"] == "Real I/O LMsb 00100"
    assert rows[1]["adresse"] == "Real I/O LMsb 00102"


# ─── generer_table_variables — MOT ────────────────────────────────────────────

def test_gen_mot_adresses():
    rows = generer_table_variables("MOT", "Word I", 1000, 3)
    assert [r["adresse"] for r in rows] == [
        "Word I 01000",
        "Word I 01001",
        "Word I 01002",
    ]

def test_gen_mot_offsets():
    rows = generer_table_variables("MOT", "Word I", 0, 3)
    assert [r["index_offset"] for r in rows] == [
        "0 - (0 / 0)",
        "1 - (2 / 0)",
        "2 - (4 / 0)",
    ]


# ─── generer_table_variables — OCTET ──────────────────────────────────────────

def test_gen_octet_adresses():
    rows = generer_table_variables("OCTET", "Byte I LMsb", 500, 3)
    assert rows[0]["adresse"] == "Byte I LMsb 00500"
    assert rows[2]["adresse"] == "Byte I LMsb 00502"

def test_gen_octet_offsets():
    rows = generer_table_variables("OCTET", "Byte I LMsb", 0, 3)
    assert rows[1]["index_offset"] == "1 - (1 / 0)"


# ─── generer_table_variables — BIT WordBit ────────────────────────────────────

def test_gen_bit_wordbit_adresses():
    rows = generer_table_variables("BIT", "WordBit I LM", 1500, 20)
    # Index 0–15 → mot 1500
    assert rows[0]["adresse"]  == "WordBit I LM 01500.0"
    assert rows[15]["adresse"] == "WordBit I LM 01500.15"
    # Index 16 → mot 1501
    assert rows[16]["adresse"] == "WordBit I LM 01501.0"

def test_gen_bit_wordbit_offsets():
    rows = generer_table_variables("BIT", "WordBit I LM", 1500, 20)
    # Index 8 → octet 1, bit 0
    assert rows[8]["index_offset"] == "8 - (1 / 0)"
    # Index 9 → octet 1, bit 1
    assert rows[9]["index_offset"] == "9 - (1 / 1)"


# ─── generer_table_variables — BIT direct ─────────────────────────────────────

def test_gen_bit_direct_adresses():
    rows = generer_table_variables("BIT", "Bit I", 200, 3)
    assert rows[0]["adresse"] == "Bit I 00200"
    assert rows[2]["adresse"] == "Bit I 00202"

def test_gen_bit_direct_offsets():
    rows = generer_table_variables("BIT", "Bit I", 0, 10)
    assert rows[7]["index_offset"] == "7 - (0 / 7)"
    assert rows[8]["index_offset"] == "8 - (1 / 0)"


# ─── generer_table_variables — format inconnu ─────────────────────────────────

def test_gen_format_inconnu():
    with pytest.raises(ValueError):
        generer_table_variables("INCONNU", "xxx", 0, 1)


# ─── traiter_donnees_entree ────────────────────────────────────────────────────

SAMPLE_CSV = (
    "FRAME,,,,,MA_TRAME,,,10,,,Real I/O LMsb,14408\n"
    "FRAME,,,,,AUTRE,,,5,,,Word I,1000\n"
)

def test_traiter_compte_trames():
    # colonnes 0=FRAME, 5=nom, 8=quantite, 10=adresse, 11=syntaxe
    csv_line = "FRAME,,,,, MA_TRAME,,,10,,14408,Real I/O LMsb\n"
    trames = traiter_donnees_entree(csv_line)
    assert len(trames) == 1

def test_traiter_ligne_non_frame_ignoree():
    texte = "HEADER,a,b\nFRAME,,,,, T1,,,5,,100,Word I\n"
    trames = traiter_donnees_entree(texte)
    assert len(trames) == 1
    assert trames[0]["format_trame"] == "MOT"

def test_traiter_syntaxe_inconnue_ignoree():
    texte = "FRAME,,,,, T1,,,5,,100,SYNTAXE_INCONNUE\n"
    trames = traiter_donnees_entree(texte)
    assert trames == []
