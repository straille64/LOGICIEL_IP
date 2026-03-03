# V2 — Onglet Modbus TCP/RTU : Design Document

**Date :** 2026-03-03
**Auteur :** Claude (session brainstorming)
**Statut :** Validé

---

## Contexte

V1 est complète (configuration IP, profils, scanner réseau). V2 ajoute un onglet de
diagnostic et communication Modbus inspiré de KScada Modbus Doctor. Objectif : permettre
de lire et écrire des registres Modbus sur des équipements industriels (automates, variateurs)
via TCP ou RTU/Serial, avec un affichage flexible des valeurs.

---

## Décisions d'Architecture

### Librairie : pymodbus 3.12.1

- 2 600 GitHub stars, release février 2026, Python 3.14 compatible
- Supporte TCP, RTU (serial), ASCII, RTU-over-TCP dans une seule lib
- API sync suffisante pour ce cas d'usage desktop
- `pip install pymodbus pyserial`

### Structure fichiers

```
core/modbus.py          # ModbusClient + format_register_value()
                        # Zéro import tkinter
modules/tab_modbus.py   # TabModbus(ttk.Frame)
                        # Zéro logique système
tests/test_modbus.py    # Tests unitaires mockés (aucun matériel requis)
```

La séparation `core/` vs `modules/` est strictement respectée (même convention que V1).

### Profils d'appareils

Reporté en V2.1. V2.0 ne sauvegarde pas de configuration.

---

## Layout UI (style KScada Modbus Doctor)

```
╔══════════════════════════════════════════════════════════════╗
║ [TCP/IP ▾] [127.0.0.1:502          ]  [▶ CONNEXION] [■ DÉC] ║  ← Barre connexion
╠══════════════════════════════════════════════════════════════╣
║ N° Esclave [ 1 ]  Registre [ 1200 ]  Longueur [ 12 ]        ║  ← Paramètres requête
║ Type [ FC3 - Lire Holding registers         ▾ ]              ║
║ Mode [ DÉCIMAL ▾ ]                                           ║
╠═══════════════════╦══════════════════════════════════════════╣
║ [ LECTURE       ] ║  N° Registre  │  Valeur                  ║
║ [ ECRITURE      ] ╠═══════════════╪═════════════════════════╣
║ ─────────────     ║     1200      │  0                       ║
║ ☐ Reconnexion     ║     1201      │  0                       ║
║ ☐ Cyclique  [..] ║     1202      │  0                       ║
║ [ ARRET CYCLE   ] ║     1203      │  0                       ║
║ ─────────────     ║     ...       │  ...                     ║
║ ☐ Inv. Octets     ╠═══════════════╧═════════════════════════╣
║ ☐ Inv. Mots       ║ ⚠ Erreur : Exception 0x02 - Adresse     ║
║ ☐ Non signé       ║   illégale   (vide si succès)            ║
║ ─────────────     ╚══════════════════════════════════════════╣
║ [ Mot 16 bits ▾ ] ║                                          ║
╠═══════════════════╧══════════════════════════════════════════╣
║ Statut : Connecté à 127.0.0.1:502                            ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Function Codes supportés

| FC | Libellé | Opération | LECTURE | ECRITURE |
|----|---------|-----------|---------|----------|
| FC1 | Lire Coils | Bits R/W | ✓ | ✓ (via FC5/FC15) |
| FC2 | Lire Entrées Discrètes | Bits RO | ✓ | — |
| FC3 | Lire Holding Registers | Mots R/W | ✓ | ✓ (via FC6/FC16) |
| FC4 | Lire Input Registers | Mots RO | ✓ | — |
| FC5 | Écrire 1 Coil | — | — | ✓ |
| FC6 | Écrire 1 Registre | — | — | ✓ |
| FC15 | Écrire Multiple Coils | — | — | ✓ |
| FC16 | Écrire Multiple Registres | — | — | ✓ |

Règle UI :
- FC1-FC4 → LECTURE actif ; ECRITURE actif si type R/W
- FC5/FC6/FC15/FC16 → LECTURE désactivé ; ECRITURE actif

---

## Modes d'Affichage (left panel)

| Clé interne | Libellé affiché | Description |
|-------------|-----------------|-------------|
| `uint16` | Mot 16 bits | Entier non signé 0–65535 (défaut) |
| `int16` | Signé 16 bits | Entier signé −32768 à +32767 |
| `float32` | Float 32 bits (2 reg) | IEEE 754, registres N + N+1 |
| `uint32` | Entier 32 bits (2 reg) | Uint32 sur 2 registres |
| `int32` | Signé 32 bits (2 reg) | Int32 sur 2 registres |
| `bin` | Binaire | 16 bits ex. "1100001001110001" |
| `ascii` | ASCII | 2 caractères ex. "Âq" |

Les modes "2 reg" consomment 2 registres consécutifs par ligne affichée.

Mode (top bar) = base numérique : DÉCIMAL, HEX, BINAIRE (s'applique aux entiers uniquement).

---

## Transport : Barre Connexion

**TCP/IP :**
- Host : IP ou hostname
- Port : 502 (défaut)
- Timeout : 3s (non exposé en UI V2)

**RTU/Serial :**
- Port COM (ex. COM3)
- Baudrate : 9600 / 19200 / 38400 / 57600 / 115200
- Parité : N / E / O
- Bits de données : 7 / 8
- Bits de stop : 1 / 2
- Timeout : 1s (non exposé en UI V2)

Sélecteur [TCP/IP ▾] → changer le transport affiche les bons champs.

---

## Polling Cyclique

- Checkbox "Cyclique" + bouton [...] pour configurer l'intervalle
- Intervalles disponibles : 100 ms, 500 ms, 1 s, 2 s, 5 s, 10 s
- Bouton "ARRET CYCLE" stoppe la boucle
- Implémentation : `threading.Event` + `threading.Thread(daemon=True)` + `self.after()`
  (même pattern que `modules/tab_scanner.py`)

---

## Reconnexion Auto

- Si coché : en cas d'erreur de lecture/écriture, tenter `mc.disconnect()` puis `mc.connect_xxx()`
  avant de relever l'erreur à l'UI
- Intervalle de tentative : 3s (fixe)

---

## Interface `core/modbus.py`

```python
class ModbusClient:
    def connect_tcp(host: str, port: int = 502, timeout: float = 3.0) -> None
    def connect_rtu(port: str, baudrate: int = 9600, parity: str = "N",
                    bytesize: int = 8, stopbits: int = 1, timeout: float = 1.0) -> None
    def disconnect() -> None
    @property is_connected: bool

    def read_coils(slave_id, address, count) -> list[bool]           # FC1
    def read_discrete_inputs(slave_id, address, count) -> list[bool] # FC2
    def read_holding_registers(slave_id, address, count) -> list[int]# FC3
    def read_input_registers(slave_id, address, count) -> list[int]  # FC4
    def write_coil(slave_id, address, value: bool) -> None           # FC5
    def write_register(slave_id, address, value: int) -> None        # FC6
    def write_coils(slave_id, address, values: list[bool]) -> None   # FC15
    def write_registers(slave_id, address, values: list[int]) -> None# FC16

def format_register_value(
    raw: int | list[int],
    display_mode: str,
    num_base: str = "dec",
    swap_bytes: bool = False,
    swap_words: bool = False,
    unsigned: bool = True
) -> str
```

Toutes les méthodes lèvent `pymodbus.exceptions.ConnectionException` ou
`pymodbus.exceptions.ModbusException` en cas d'erreur.

---

## Patterns réutilisés (V1)

| Pattern | Source |
|---------|--------|
| `threading.Event` + daemon thread + `self.after()` | `modules/tab_scanner.py:50-80` |
| `ttk.Panedwindow(HORIZONTAL)` layout | `modules/tab_config.py:60-85` |
| `Messagebox.show_error()` | `modules/tab_config.py` |
| `ttk.Treeview` colonnes | `modules/tab_scanner.py:35-50` |

---

## Périmètre V2.0 / Hors périmètre

| Fonctionnalité | V2.0 | Plus tard |
|----------------|------|-----------|
| Modbus TCP | ✓ | |
| Modbus RTU/Serial | ✓ | |
| FC1–FC16 | ✓ | |
| Tous modes d'affichage | ✓ | |
| Polling cyclique | ✓ | |
| Reconnexion auto | ✓ | |
| Inversion octets/mots | ✓ | |
| Profils appareils (save/load) | | V2.1 |
| Graphique temps réel | | V2.2 |
| Scanner d'esclaves (ID 1–247) | | V2.2 |
| Mode Espion RTU (passif) | | V3 |
