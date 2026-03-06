"""modules/tab_pcvue.py — Onglet PCVUE_TRAME_CONVERT (générateur de tables de variables PCVue)."""
import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from core.pcvue import (
    FORMATS, FORMAT_SYNTAXES, FORMAT_UNIT_LABELS,
    BIT_WORDBIT_SYNTAXES, MOT_HIGH_MAX_SYNTAXES,
    get_max_quantite, generer_table_variables, traiter_donnees_entree,
    _detect_sep,
)


class TabPCVue(ttk.Frame):
    """Onglet PCVUE_TRAME_CONVERT — génération de tables de variables Modbus pour PCVue."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._current_syntaxes: list = []
        self._loaded_trames: list = []
        self._syncing: bool = False
        self._zone1_last: str = ""
        self._zone2_last: str = ""

        self._build_variables()
        self._build_layout()
        self._bind_callbacks()
        self._on_format_change()
        self._start_sync_loop()

    # -----------------------------------------------------------------------
    # Variables Tkinter
    # -----------------------------------------------------------------------

    def _build_variables(self):
        self.format_var        = tk.StringVar(value="DOUBLE MOT")
        self.quantite_var      = tk.StringVar(value="32")
        self.adresse_var       = tk.StringVar(value="0")
        self.max_var           = tk.StringVar(value="64")
        self.max_unit_var      = tk.StringVar(value="DOUBLE MOTs")
        self.quantite_unit_var = tk.StringVar(value="DOUBLE MOTs")
        self.trame_selector_var = tk.StringVar()

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_layout(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(self, padding=8)
        left_frame.grid(row=0, column=0, sticky=NS)

        right_frame = ttk.Frame(self, padding=8)
        right_frame.grid(row=0, column=1, sticky=NSEW)
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        self._build_chargement_section(left_frame)
        self._build_address_section(left_frame)
        self._build_right_panel(right_frame)

    def _build_chargement_section(self, parent):
        charg_frame = ttk.LabelFrame(parent, text="Chargement")
        charg_frame.pack(fill=X, pady=(0, 6))

        btn_row = ttk.Frame(charg_frame)
        btn_row.pack(fill=X, pady=(0, 4))
        ttk.Button(
            btn_row, text="Ouvrir (.txt / .dat)...",
            command=self._charger_fichier, bootstyle=SECONDARY,
        ).pack(side=LEFT)
        ttk.Button(
            btn_row, text="Clear",
            command=self._clear_zones, bootstyle=DANGER,
        ).pack(side=RIGHT)
        ttk.Button(
            btn_row, text="Générer",
            command=self._charger_zones, bootstyle=PRIMARY,
        ).pack(side=RIGHT, padx=(0, 4))

        def _make_zone(label, height):
            outer = ttk.LabelFrame(charg_frame, text=label)
            txt = tk.Text(
                outer, height=height, font=("Courier", 8),
                wrap="none", relief="flat", borderwidth=0,
            )
            sb = ttk.Scrollbar(outer, orient=VERTICAL, command=txt.yview)
            txt.configure(yscrollcommand=sb.set)
            txt.pack(side=LEFT, fill=BOTH, expand=True)
            sb.pack(side=RIGHT, fill=Y)
            outer.pack(fill=X, pady=(0, 2))
            return txt

        self.zone1_text = _make_zone("CSV  ( , / ; )", height=6)
        self.zone2_text = _make_zone("Excel  ( \\t )", height=6)

        self.trame_selector_frame = ttk.Frame(charg_frame)
        self.trame_selector_frame.pack(fill=X, pady=(6, 0))
        ttk.Label(self.trame_selector_frame, text="Trame :").pack(side=LEFT)
        self.trame_cb = ttk.Combobox(
            self.trame_selector_frame,
            textvariable=self.trame_selector_var,
            state=DISABLED,
            width=28,
        )
        self.trame_cb.pack(side=LEFT, padx=(6, 0))
        self.trame_count_lbl = ttk.Label(self.trame_selector_frame, text="", bootstyle=SECONDARY)
        self.trame_count_lbl.pack(side=LEFT, padx=(8, 0))

    def _build_address_section(self, parent):
        addr_frame = ttk.LabelFrame(parent, text="Saisie de l'adresse et de la taille")
        addr_frame.pack(fill=X, pady=(0, 6))

        header = ttk.Frame(addr_frame)
        header.pack(fill=X)
        ttk.Label(header, text="Adresse", anchor=W).pack(side=LEFT)
        ttk.Label(header, text="Mode d'accès", anchor=E).pack(side=RIGHT)

        list_frame = ttk.Frame(addr_frame)
        list_frame.pack(fill=X, pady=(2, 6))

        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL)
        self.syntax_listbox = tk.Listbox(
            list_frame,
            selectmode="single",
            width=54,
            height=4,
            yscrollcommand=scrollbar.set,
            exportselection=False,
            font=("Courier", 9),
        )
        scrollbar.config(command=self.syntax_listbox.yview)
        self.syntax_listbox.pack(side=LEFT, fill=X, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        ttk.Separator(addr_frame, orient=HORIZONTAL).pack(fill=X, pady=4)

        bottom_frame = ttk.Frame(addr_frame)
        bottom_frame.pack(fill=X)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=0)

        left_grid = ttk.Frame(bottom_frame)
        left_grid.grid(row=0, column=0, sticky=NW)

        fields = [
            ("Quantité d'informations désirée", self.quantite_var, True,  self.quantite_unit_var),
            ("Maximum permis",                  self.max_var,       False, self.max_unit_var),
            ("Adresse de début",                self.adresse_var,   True,  None),
        ]
        for r, (label_text, var, editable, unit_var) in enumerate(fields):
            ttk.Label(left_grid, text=label_text, anchor=W).grid(
                row=r, column=0, sticky=W, pady=3, padx=(0, 8))
            if editable:
                ttk.Entry(left_grid, textvariable=var, width=8).grid(row=r, column=1, sticky=W)
            else:
                ttk.Label(left_grid, textvariable=var, width=8, anchor=E,
                          bootstyle=SECONDARY).grid(row=r, column=1, sticky=W)
            if unit_var is not None:
                ttk.Label(left_grid, textvariable=unit_var, anchor=W).grid(
                    row=r, column=2, sticky=W, padx=(6, 0))
            else:
                ttk.Label(left_grid, text="Décimal", anchor=W).grid(
                    row=r, column=2, sticky=W, padx=(6, 0))

        right_grid = ttk.Frame(bottom_frame)
        right_grid.grid(row=0, column=1, sticky=NE, padx=(16, 0))

        ttk.Label(right_grid, text="Format de la trame", anchor=W).grid(
            row=0, column=0, sticky=W, pady=(3, 2))
        ttk.Combobox(
            right_grid,
            textvariable=self.format_var,
            values=FORMATS,
            state="readonly",
            width=14,
        ).grid(row=1, column=0, sticky=W)

        ttk.Button(
            right_grid,
            text="Générer",
            command=self.on_generer,
            bootstyle=SUCCESS,
            width=14,
        ).grid(row=2, column=0, sticky=E, pady=(10, 2))

    def _build_right_panel(self, parent):
        result_frame = ttk.LabelFrame(parent, text="Résultat")
        result_frame.grid(row=0, column=0, sticky=NSEW)
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Compact.Treeview", rowheight=18, font=("TkDefaultFont", 9))
        style.configure("Compact.Treeview.Heading", font=("TkDefaultFont", 9, "bold"))

        self.result_tree = ttk.Treeview(
            result_frame,
            columns=("adresse", "index_offset"),
            show="headings",
            style="Compact.Treeview",
        )
        self.result_tree.heading("adresse",      text="Adresse")
        self.result_tree.heading("index_offset", text="Index - (Offset octet / Offset bit)")
        self.result_tree.column("adresse",      width=220, anchor=W, stretch=True)
        self.result_tree.column("index_offset", width=200, anchor=E, stretch=False)

        self.result_tree.tag_configure("evenrow", background="#1e2124")
        self.result_tree.tag_configure("oddrow",  background="#2b3035")

        tree_scroll = ttk.Scrollbar(result_frame, orient=VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=tree_scroll.set)
        self.result_tree.grid(row=0, column=0, sticky=NSEW)
        tree_scroll.grid(row=0, column=1, sticky=NS)

    # -----------------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------------

    def _bind_callbacks(self):
        self.format_var.trace_add("write", lambda *_: self._on_format_change())
        self.syntax_listbox.bind("<<ListboxSelect>>", self._on_syntax_select)
        self.trame_cb.bind("<<ComboboxSelected>>", self._on_trame_select)

    def _on_format_change(self):
        fmt = self.format_var.get()
        if fmt not in FORMAT_SYNTAXES:
            return
        self._current_syntaxes = FORMAT_SYNTAXES[fmt]
        self.syntax_listbox.delete(0, "end")
        for s in self._current_syntaxes:
            mode = "L/E" if "I/O" in s else "L"
            row  = f"{s}  00000    à    {s}  65535    {mode}"
            self.syntax_listbox.insert("end", row)
        self.syntax_listbox.selection_set(0)
        self.syntax_listbox.see(0)
        unit = FORMAT_UNIT_LABELS[fmt]
        self.quantite_unit_var.set(unit)
        self.max_unit_var.set(unit)
        self._update_max()

    def _on_syntax_select(self, event=None):
        self._update_max()

    def _update_max(self):
        fmt    = self.format_var.get()
        syntax = self._get_selected_syntax()
        maxi   = get_max_quantite(fmt, syntax)
        self.max_var.set(str(maxi))

    def _get_selected_syntax(self) -> str:
        sel = self.syntax_listbox.curselection()
        idx = sel[0] if sel else 0
        if idx < len(self._current_syntaxes):
            return self._current_syntaxes[idx]
        return self._current_syntaxes[0] if self._current_syntaxes else ""

    # -----------------------------------------------------------------------
    # Synchronisation bidirectionnelle des zones de texte
    # -----------------------------------------------------------------------

    @staticmethod
    def _csv_to_tsv(text: str) -> str:
        if not text.strip():
            return ""
        sep = _detect_sep(text)
        return text.replace(sep, "\t") if sep != "\t" else text

    @staticmethod
    def _tsv_to_csv(text: str) -> str:
        return text.replace("\t", ",") if text.strip() else ""

    def _start_sync_loop(self):
        self._poll_zones()

    def _poll_zones(self):
        if not self._syncing:
            text1 = self.zone1_text.get("1.0", "end-1c")
            text2 = self.zone2_text.get("1.0", "end-1c")
            if text1 != self._zone1_last:
                self._zone1_last = text1
                converted = self._csv_to_tsv(text1)
                if converted != text2:
                    self._syncing = True
                    self.zone2_text.delete("1.0", "end")
                    self.zone2_text.insert("1.0", converted)
                    self._zone2_last = converted
                    self._syncing = False
            elif text2 != self._zone2_last:
                self._zone2_last = text2
                converted = self._tsv_to_csv(text2)
                if converted != text1:
                    self._syncing = True
                    self.zone1_text.delete("1.0", "end")
                    self.zone1_text.insert("1.0", converted)
                    self._zone1_last = converted
                    self._syncing = False
        self.after(200, self._poll_zones)

    def _clear_zones(self):
        self._syncing = True
        try:
            self.zone1_text.delete("1.0", "end")
            self.zone2_text.delete("1.0", "end")
            self._zone1_last = ""
            self._zone2_last = ""
        finally:
            self._syncing = False

    # -----------------------------------------------------------------------
    # Chargement de données externes
    # -----------------------------------------------------------------------

    def _charger_fichier(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Ouvrir un fichier de trames",
            filetypes=[("Fichiers texte/dat", "*.txt *.dat"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        texte = None
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                with open(path, encoding=enc) as f:
                    texte = f.read()
                break
            except (UnicodeDecodeError, OSError):
                continue
        if texte is None:
            Messagebox.show_error(f"Impossible de lire : {path}", title="Erreur de lecture")
            return
        self.zone1_text.delete("1.0", "end")
        self.zone1_text.insert("1.0", texte.strip())
        self._charger_zones()

    def _charger_zones(self):
        texte = self.zone1_text.get("1.0", "end").strip()
        if not texte:
            tsv = self.zone2_text.get("1.0", "end").strip()
            texte = self._tsv_to_csv(tsv) if tsv else ""
        if not texte:
            Messagebox.show_warning(
                "Collez d'abord des données dans une des zones.",
                title="Zones vides",
            )
            return
        try:
            trames = traiter_donnees_entree(texte, est_fichier=False)
        except Exception as exc:
            Messagebox.show_error(str(exc), title="Erreur de parsing")
            return
        self._appliquer_trames_chargees(trames)

    def _appliquer_trames_chargees(self, trames: list):
        if not trames:
            Messagebox.show_warning(
                "Le fichier ne contient aucune ligne FRAME valide reconnue.",
                title="Aucune trame trouvée",
            )
            return
        self._loaded_trames = trames
        noms = [t["nom"] for t in trames]
        self.trame_cb.configure(values=noms, state="readonly")
        self.trame_selector_var.set(noms[0])
        count = len(trames)
        self.trame_count_lbl.configure(text=f"({count} trame{'s' if count > 1 else ''})")
        self._on_trame_select()

    def _on_trame_select(self, event=None):
        nom   = self.trame_selector_var.get()
        trame = next((t for t in self._loaded_trames if t["nom"] == nom), None)
        if trame is None:
            return
        self.format_var.set(trame["format_trame"])
        try:
            idx = self._current_syntaxes.index(trame["syntaxe"])
            self.syntax_listbox.selection_clear(0, "end")
            self.syntax_listbox.selection_set(idx)
            self.syntax_listbox.see(idx)
            self._update_max()
        except ValueError:
            pass
        self.quantite_var.set(str(trame["quantite"]))
        self.adresse_var.set(str(trame["adresse_debut"]))
        self.on_generer()

    # -----------------------------------------------------------------------
    # Génération
    # -----------------------------------------------------------------------

    def on_generer(self):
        try:
            quantite      = int(self.quantite_var.get())
            adresse_debut = int(self.adresse_var.get())
        except ValueError:
            Messagebox.show_error(
                "La quantité et l'adresse de début doivent être des entiers.",
                title="Erreur de saisie",
            )
            return

        if quantite <= 0:
            Messagebox.show_error("La quantité doit être supérieure à 0.", title="Erreur de saisie")
            return
        if adresse_debut < 0:
            Messagebox.show_error("L'adresse de début doit être >= 0.", title="Erreur de saisie")
            return

        fmt     = self.format_var.get()
        syntaxe = self._get_selected_syntax()
        maxi    = get_max_quantite(fmt, syntaxe)

        if quantite > maxi:
            Messagebox.show_warning(
                f"La quantité saisie ({quantite}) dépasse le maximum permis ({maxi}).\n"
                f"La table sera générée avec {maxi} éléments.",
                title="Quantité réduite",
            )
            quantite = maxi
            self.quantite_var.set(str(maxi))

        rows = generer_table_variables(fmt, syntaxe, adresse_debut, quantite)
        self._populate_table(rows)

    def _populate_table(self, rows: list):
        self.result_tree.delete(*self.result_tree.get_children())
        for i, row in enumerate(rows):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.result_tree.insert(
                "", "end",
                values=(row["adresse"], row["index_offset"]),
                tags=(tag,),
            )
