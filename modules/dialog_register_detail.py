"""modules/dialog_register_detail.py — Popup de détails d'un registre Modbus."""
import struct
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


# ─── Fonctions pures (testables sans tkinter) ──────────────────────────────────

def decode_registers(
    w0: int, w1: int,
    swap_words: bool = False,
    swap_bytes: bool = False,
) -> tuple:
    """Décode 2 registres 16 bits en 4 octets (b3, b2, b1, b0).

    b3 = MSB (Octet 3), b0 = LSB (Octet 0).
    swap_words : inverse l'ordre des deux mots avant décodage.
    swap_bytes : échange b3↔b2 et b1↔b0 après décodage.
    """
    hi, lo = (w1, w0) if swap_words else (w0, w1)
    combined = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    b3 = (combined >> 24) & 0xFF
    b2 = (combined >> 16) & 0xFF
    b1 = (combined >>  8) & 0xFF
    b0 =  combined        & 0xFF
    if swap_bytes:
        b3, b2 = b2, b3
        b1, b0 = b0, b1
    return b3, b2, b1, b0


def fmt_bin_byte(b: int) -> str:
    """Retourne la représentation binaire sur 8 bits d'un octet."""
    return f"{b & 0xFF:08b}"


def fmt_ascii_byte(b: int) -> str:
    """Retourne le caractère ASCII ou '.' si non imprimable."""
    return chr(b) if 32 <= b < 127 else "."


def fmt_reel32(w0: int, w1: int) -> str:
    """Décode deux mots 16 bits en flottant IEEE 754 big-endian."""
    combined = ((w0 & 0xFFFF) << 16) | (w1 & 0xFFFF)
    try:
        val = struct.unpack(">f", combined.to_bytes(4, "big"))[0]
        return str(val)
    except Exception:
        return "NaN"




def parse_bin_byte(text: str) -> int:
    """Parse une chaîne binaire 8 bits → int (0-255). Lève ValueError si invalide."""
    val = int(text, 2)
    if not (0 <= val <= 255):
        raise ValueError(f"Hors plage: {val}")
    return val


def parse_octet(text: str) -> int:
    """Parse un texte décimal ou hex (0x..) → int (0-255). Lève ValueError si invalide."""
    val = int(text, 0)
    if not (0 <= val <= 255):
        raise ValueError(f"Hors plage: {val}")
    return val


def parse_mot16(text: str) -> int:
    """Parse décimal ou hex → int (0-65535). Lève ValueError si hors plage."""
    val = int(text, 0)
    if not (0 <= val <= 65535):
        raise ValueError(f"Hors plage: {val}")
    return val


def parse_mot32(text: str) -> int:
    """Parse décimal ou hex → int (0-4294967295). Lève ValueError si hors plage."""
    val = int(text, 0)
    if not (0 <= val <= 0xFFFFFFFF):
        raise ValueError(f"Hors plage: {val}")
    return val


def parse_reel32_to_words(text: str) -> tuple:
    """Parse un float → (word_hi, word_lo) IEEE 754 big-endian. Lève ValueError si invalide."""
    val = float(text)
    raw = struct.pack(">f", val)
    w_hi = (raw[0] << 8) | raw[1]
    w_lo = (raw[2] << 8) | raw[3]
    return w_hi, w_lo


# ─── Dialogue ─────────────────────────────────────────────────────────────────

class RegisterDetailDialog(tk.Toplevel):
    def __init__(self, parent, address: int, w0: int, w1: int):
        super().__init__(parent)
        self.title(f"Détails — N° Registre : {address}")
        self.resizable(False, False)
        self.transient(parent)

        self._address = address
        self._w0 = w0 & 0xFFFF
        self._w1 = w1 & 0xFFFF

        self.hexa_var        = tk.BooleanVar(value=False)
        self.unsigned_var    = tk.BooleanVar(value=False)
        self.swap_bytes_var  = tk.BooleanVar(value=False)
        self.swap_words_var  = tk.BooleanVar(value=False)

        self._cell_vars: dict = {}
        self._bit_vars: list = []

        self._build()
        self._refresh()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px - w // 2}+{py - h // 2}")

        self.grab_set()
        self.wait_window()

    def _build(self):
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill=BOTH, expand=True)
        self._build_bits(outer)
        ttk.Separator(outer, orient=HORIZONTAL).pack(fill=X, pady=6)
        self._build_grid(outer)
        ttk.Separator(outer, orient=HORIZONTAL).pack(fill=X, pady=6)
        self._build_buttons(outer)

    def _build_bits(self, parent):
        frame = ttk.LabelFrame(parent, text=f"Bits — N° Registre : {self._address}")
        frame.pack(fill=X)
        self._bit_vars = [tk.BooleanVar(value=False) for _ in range(32)]
        for row_idx, (start, end) in enumerate([(15, -1), (31, 15)]):
            num_row = ttk.Frame(frame)
            num_row.pack()
            bit_row = ttk.Frame(frame)
            bit_row.pack()
            for col, bit in enumerate(range(start, end, -1)):
                ttk.Label(num_row, text=str(bit), width=3, anchor=CENTER).grid(row=0, column=col)
                cb = ttk.Checkbutton(bit_row, variable=self._bit_vars[bit], state=DISABLED)
                cb.grid(row=0, column=col)

    def _build_grid(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill=X)
        table = ttk.Frame(container)
        table.grid(row=0, column=0, sticky=W)
        headers = ["", "Octet 3", "Octet 2", "Octet 1", "Octet 0"]
        for c, h in enumerate(headers):
            ttk.Label(table, text=h, width=10, anchor=CENTER, bootstyle=PRIMARY).grid(row=0, column=c, padx=1, pady=1)
        row_names = ["Binaire", "Ascii", "Octet", "Mot 16", "Mot 32", "Réel 32"]
        for r, name in enumerate(row_names, start=1):
            ttk.Label(table, text=name, width=10, anchor=W, bootstyle=SECONDARY).grid(row=r, column=0, padx=1, pady=1)
        for key in ("binaire", "ascii", "octet"):
            self._cell_vars[key] = [tk.StringVar(value="") for _ in range(4)]
        row_map = {"binaire": 1, "ascii": 2, "octet": 3}
        for key, row_idx in row_map.items():
            for c, sv in enumerate(self._cell_vars[key], start=1):
                ttk.Label(table, textvariable=sv, width=10, anchor=CENTER, relief="groove").grid(row=row_idx, column=c, padx=1, pady=1)
        self._mot16_vars = [tk.StringVar(value=""), tk.StringVar(value="")]
        ttk.Label(table, textvariable=self._mot16_vars[0], width=21, anchor=CENTER, relief="groove").grid(row=4, column=1, columnspan=2, padx=1, pady=1)
        ttk.Label(table, textvariable=self._mot16_vars[1], width=21, anchor=CENTER, relief="groove").grid(row=4, column=3, columnspan=2, padx=1, pady=1)
        self._mot32_var = tk.StringVar(value="")
        ttk.Label(table, textvariable=self._mot32_var, width=43, anchor=CENTER, relief="groove").grid(row=5, column=1, columnspan=4, padx=1, pady=1)
        self._reel32_var = tk.StringVar(value="")
        ttk.Label(table, textvariable=self._reel32_var, width=43, anchor=CENTER, relief="groove").grid(row=6, column=1, columnspan=4, padx=1, pady=1)
        opts = ttk.LabelFrame(container, text="Options", padding=8)
        opts.grid(row=0, column=1, sticky=N+W, padx=(12, 0))
        for text, var in [
            ("Hexa",         self.hexa_var),
            ("Non signé",    self.unsigned_var),
            ("Inv. Octets",  self.swap_bytes_var),
            ("Inv. Mots",    self.swap_words_var),
        ]:
            ttk.Checkbutton(opts, text=text, variable=var, command=self._refresh).pack(anchor=W, pady=2)

    def _build_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="OK", bootstyle=PRIMARY, command=self.destroy, width=18).pack(side=LEFT, padx=6)
        ttk.Button(btn_frame, text="Annuler", bootstyle=SECONDARY, command=self.destroy, width=18).pack(side=RIGHT, padx=6)

    def _refresh(self):
        sw = self.swap_words_var.get()
        sb = self.swap_bytes_var.get()
        hexa = self.hexa_var.get()
        unsigned = self.unsigned_var.get()
        b3, b2, b1, b0 = decode_registers(self._w0, self._w1, sw, sb)
        bytes_list = [b3, b2, b1, b0]
        for i in range(16):
            self._bit_vars[i].set(bool((self._w0 >> i) & 1))
        for i in range(16):
            self._bit_vars[16 + i].set(bool((self._w1 >> i) & 1))
        for i, sv in enumerate(self._cell_vars["binaire"]):
            sv.set(fmt_bin_byte(bytes_list[i]))
        for i, sv in enumerate(self._cell_vars["ascii"]):
            sv.set(fmt_ascii_byte(bytes_list[i]))
        def _fmt_int(v: int) -> str:
            return f"0x{v:02X}" if hexa else str(v)
        for i, sv in enumerate(self._cell_vars["octet"]):
            sv.set(_fmt_int(bytes_list[i]))
        if sw:
            word_hi, word_lo = self._w1, self._w0
        else:
            word_hi, word_lo = self._w0, self._w1
        def _fmt_word16(w: int) -> str:
            if hexa:
                return f"0x{w & 0xFFFF:04X}"
            if not unsigned and (w & 0x8000):
                return str((w & 0xFFFF) - 0x10000)
            return str(w & 0xFFFF)
        self._mot16_vars[0].set(_fmt_word16(word_hi))
        self._mot16_vars[1].set(_fmt_word16(word_lo))
        combined = ((word_hi & 0xFFFF) << 16) | (word_lo & 0xFFFF)
        if hexa:
            self._mot32_var.set(f"0x{combined:08X}")
        elif not unsigned and (combined & 0x80000000):
            self._mot32_var.set(str(combined - 0x100000000))
        else:
            self._mot32_var.set(str(combined))
        self._reel32_var.set(fmt_reel32(word_hi, word_lo))
