"""core/pcvue.py — Logique pure du générateur de trames PCVue (sans tkinter)."""
import csv
import io

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FORMAT_SYNTAXES = {
    "DOUBLE MOT": [
        "DWord I LMsb", "DWord I/O LMsb",
        "DWord I MLsb", "DWord I/O MLsb",
        "DW Extd I LM", "DW Extd I/O LM", "DW Extd I ML",
    ],
    "REEL": [
        "Real I LMsb",  "Real I/O LMsb",
        "Real I MLsb",  "Real I/O MLsb",
        "Rl Extd I LM", "Rl Extd I/O LM", "Rl Extd I ML",
    ],
    "MOT": [
        "Word I", "Word I/O",
        "W Extd I", "W Extd I/O",
        "Information", "Command",
    ],
    "OCTET": [
        "Byte I LMsb",   "Byte I/O LMsb",
        "By Extd I LM",  "By Extd I/O LM",
        "Byte I MLsb",   "Byte I/O MLsb",
        "By Extd I ML",
    ],
    "BIT": [
        "Bit I", "Bit I/O",
        "Bi Extd I", "Bi Extd I/O",
        "WordBit I LM", "WordBit I/O LM", "WordBit I ML",
    ],
}

FORMAT_MAX = {
    "DOUBLE MOT": 64,
    "REEL":       64,
    "MOT":       128,
    "OCTET":     256,
    "BIT":      2048,
}

FORMAT_UNIT_LABELS = {
    "DOUBLE MOT": "DOUBLE MOTs",
    "REEL":       "REELs",
    "MOT":        "MOTs",
    "OCTET":      "OCTETs",
    "BIT":        "BITs",
}

# MOT — Information et Command ont un max différent
MOT_HIGH_MAX_SYNTAXES = {"Information", "Command"}

# BIT — syntaxes utilisant la notation adresse.bit
BIT_WORDBIT_SYNTAXES = {"WordBit I LM", "WordBit I/O LM", "WordBit I ML"}

FORMATS = ["BIT", "OCTET", "MOT", "REEL", "DOUBLE MOT"]

# Lookup inversé : syntaxe → format_trame
SYNTAXE_TO_FORMAT: dict = {
    s: fmt
    for fmt, syntaxes in FORMAT_SYNTAXES.items()
    for s in syntaxes
}


# ---------------------------------------------------------------------------
# Logique métier
# ---------------------------------------------------------------------------

def get_max_quantite(format_trame: str, syntaxe: str) -> int:
    """Retourne la quantité maximale permise pour un format + syntaxe donnés."""
    if format_trame == "MOT" and syntaxe in MOT_HIGH_MAX_SYNTAXES:
        return 5535
    return FORMAT_MAX[format_trame]


def generer_table_variables(
    format_trame: str,
    syntaxe: str,
    adresse_debut: int,
    quantite: int,
) -> list:
    """Génère la table de variables PCVue.

    Retourne une liste de dicts : {'adresse': str, 'variable': str, 'index_offset': str}
    """
    if format_trame in ("DOUBLE MOT", "REEL"):
        return _gen_32bit(syntaxe, adresse_debut, quantite)
    elif format_trame == "MOT":
        return _gen_mot(syntaxe, adresse_debut, quantite)
    elif format_trame == "OCTET":
        return _gen_octet(syntaxe, adresse_debut, quantite)
    elif format_trame == "BIT":
        if syntaxe in BIT_WORDBIT_SYNTAXES:
            return _gen_bit_wordbit(syntaxe, adresse_debut, quantite)
        else:
            return _gen_bit_direct(syntaxe, adresse_debut, quantite)
    else:
        raise ValueError(f"Format de trame inconnu : '{format_trame}'")


def traiter_donnees_entree(source: str, est_fichier: bool = False) -> list:
    """Lit et parse une source de données contenant des lignes FRAME.

    Args:
        source:      chemin fichier (est_fichier=True) ou texte brut (collé)
        est_fichier: True si source est un chemin vers un .txt / .dat

    Returns:
        Liste de dicts {'nom', 'syntaxe', 'format_trame', 'adresse_debut', 'quantite'}
    """
    if est_fichier:
        texte = None
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                with open(source, encoding=enc) as f:
                    texte = f.read()
                break
            except (UnicodeDecodeError, OSError):
                continue
        if texte is None:
            raise OSError(f"Impossible de lire le fichier : {source}")
    else:
        texte = source

    sep = _detect_sep(texte)
    trames = []
    for cols in csv.reader(io.StringIO(texte), delimiter=sep):
        trame = _parse_frame_line(cols)
        if trame:
            trames.append(trame)
    return trames


# ---------------------------------------------------------------------------
# Fonctions internes
# ---------------------------------------------------------------------------

def _gen_32bit(syntaxe: str, adresse_debut: int, quantite: int) -> list:
    rows = []
    for index in range(quantite):
        addr = adresse_debut + index * 2
        rows.append({
            "adresse":      f"{syntaxe} {addr:05d}",
            "variable":     "",
            "index_offset": f"{index} - ({index * 4} / 0)",
        })
    return rows


def _gen_mot(syntaxe: str, adresse_debut: int, quantite: int) -> list:
    rows = []
    for index in range(quantite):
        addr = adresse_debut + index
        rows.append({
            "adresse":      f"{syntaxe} {addr:05d}",
            "variable":     "",
            "index_offset": f"{index} - ({index * 2} / 0)",
        })
    return rows


def _gen_octet(syntaxe: str, adresse_debut: int, quantite: int) -> list:
    rows = []
    for index in range(quantite):
        addr = adresse_debut + index
        rows.append({
            "adresse":      f"{syntaxe} {addr:05d}",
            "variable":     "",
            "index_offset": f"{index} - ({index} / 0)",
        })
    return rows


def _gen_bit_wordbit(syntaxe: str, adresse_debut: int, quantite: int) -> list:
    rows = []
    for index in range(quantite):
        word_addr       = adresse_debut + (index // 16)
        bit_within_word = index % 16
        offset_octet    = index // 8
        offset_bit      = index % 8
        rows.append({
            "adresse":      f"{syntaxe} {word_addr:05d}.{bit_within_word}",
            "variable":     "",
            "index_offset": f"{index} - ({offset_octet} / {offset_bit})",
        })
    return rows


def _gen_bit_direct(syntaxe: str, adresse_debut: int, quantite: int) -> list:
    rows = []
    for index in range(quantite):
        addr         = adresse_debut + index
        offset_octet = index // 8
        offset_bit   = index % 8
        rows.append({
            "adresse":      f"{syntaxe} {addr:05d}",
            "variable":     "",
            "index_offset": f"{index} - ({offset_octet} / {offset_bit})",
        })
    return rows


def _detect_sep(texte: str) -> str:
    for line in texte.splitlines():
        line = line.strip()
        if line:
            counts = {",": line.count(","), ";": line.count(";"), "\t": line.count("\t")}
            return max(counts, key=counts.get)
    return ","


def _parse_frame_line(cols: list) -> dict | None:
    if len(cols) < 12 or cols[0].strip() != "FRAME":
        return None
    nom     = cols[5].strip()
    syntaxe = cols[11].strip()
    fmt     = SYNTAXE_TO_FORMAT.get(syntaxe)
    if fmt is None:
        return None
    try:
        quantite      = int(cols[8].strip())
        adresse_debut = int(cols[10].strip())
    except (ValueError, IndexError):
        return None
    if quantite <= 0 or adresse_debut < 0:
        return None
    return {"nom": nom, "syntaxe": syntaxe, "format_trame": fmt,
            "adresse_debut": adresse_debut, "quantite": quantite}
