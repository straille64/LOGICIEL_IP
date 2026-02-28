# Design Document — LOGICIEL_IP
Date : 2026-02-28

## Contexte

Outil de bureau Windows destiné à un automaticien. Distribué en `.exe` standalone (PyInstaller) à des clients. Architecture modulaire par onglets pour permettre l'ajout de modules sans refactoring du cœur.

## Stack technique

| Composant | Choix |
|-----------|-------|
| Langage | Python (niveau avancé) |
| UI | tkinter + ttkbootstrap |
| Packaging | PyInstaller → `.exe` standalone |
| Config | JSON (profils IP) |
| Threading | `threading` stdlib (opérations réseau non-bloquantes) |
| Élévation admin | Manifest UAC (requis pour modifier IP) |

## Architecture

```
LOGICIEL_IP/
├── main.py                  # Fenêtre principale, chargement dynamique des onglets
├── core/
│   ├── network.py           # Lecture interfaces, apply IP via netsh/WMI
│   ├── profiles.py          # Sauvegarde/chargement profils JSON
│   └── scanner.py           # Ping sweep, résolution hostname, threading
├── modules/
│   ├── tab_config.py        # Onglet Config & Outils
│   ├── tab_scanner.py       # Onglet Scanner + Ping continu
│   ├── tab_modbus.py        # (V2) Modbus TCP/RTU
│   ├── tab_serial.py        # (V2) Serial/COM Monitor
│   ├── tab_mbus.py          # (V3) M-Bus
│   ├── tab_bacnet.py        # (V4) BACnet
│   └── tab_advanced.py      # (V5) OPC-UA, SNMP, Calc subnet, Traceroute, Port Scanner
├── assets/
│   └── icon.ico
├── profiles/                # Profils IP sauvegardés (.json)
├── requirements.txt
└── build.spec               # Config PyInstaller
```

### Principe modulaire

Chaque onglet est une classe héritant de `ttk.Frame`. `main.py` enregistre les tabs via une liste — ajouter un module = créer un fichier dans `modules/` et l'ajouter à la liste dans `main.py`. Aucune modification du cœur requise.

## Roadmap des versions

| Version | Modules |
|---------|---------|
| **V1** | Config IP + Profils + Outils rapides + Scanner réseau + Ping continu |
| **V2** | Modbus TCP/RTU + Serial/COM Monitor |
| **V3** | M-Bus (compteurs énergie/fluides) |
| **V4** | BACnet (automatismes bâtiment) |
| **V5** | OPC-UA Browser + SNMP Discovery + Calc Subnet + Traceroute + Port Scanner |

---

## V1 — Détail des fonctionnalités

### Onglet 1 : Configuration & Outils

**Sélection carte réseau**
- Dropdown listant toutes les interfaces actives (via `psutil` ou `wmi`)
- Bouton Rafraîchir

**Configuration IP**
- Radio DHCP / Manuel
- Champs : IP, Masque, Passerelle, DNS1, DNS2
- Bouton Appliquer → appel `netsh interface ip set address` via `subprocess` (requiert admin)

**Gestion des profils**
- Dropdown des profils sauvegardés
- Boutons : Charger, Sauvegarder (nom libre), Supprimer
- Stockage : `profiles/<nom>.json` avec les 5 champs IP

**Outils rapides**
- Bouton `ipconfig /all` → résultat dans zone texte scrollable
- Bouton `CMD Admin` → ouvre `cmd.exe` avec élévation
- Bouton `Ping...` → ouvre dialogue, lance ping simple vers une IP cible

### Onglet 2 : Scanner Réseau + Ping Continu

**Scan de plage IP**
- Champs plage début/fin, timeout (ms), nombre de threads
- Boutons Lancer / Stop
- Barre de progression
- Tableau : IP, Nom d'hôte (résolution DNS inverse), Statut (●/○), RTT
- Export CSV, Copier sélection

**Ping continu**
- Champ cible IP/hostname, intervalle (1s, 2s, 5s)
- Boutons Démarrer / Stop / Sauvegarder log
- Zone de texte horodatée scrollable (auto-scroll)
- Compteurs : Envoyés / Reçus / Perdus / % perte

---

## V2 — Modbus TCP/RTU + Serial/COM Monitor

### Modbus TCP/RTU (`pymodbus`)
- Connexion TCP (IP + port 502) ou RTU (port COM + baudrate)
- Lecture registres : Coils (0x), Discrete Inputs (1x), Input Registers (3x), Holding Registers (4x)
- Écriture registres holding / coils
- Affichage brut (hex, décimal, binaire)
- Décodage : INT16, UINT16, INT32, UINT32, FLOAT32 (big/little endian)

### Serial/COM Monitor (`pyserial`)
- Sélection port COM + baudrate/parity/stopbits
- Terminal série brut (TX/RX)
- Affichage HEX et ASCII en parallèle
- Envoi manuel de trames hex ou ASCII

---

## V3 — M-Bus (`python-mbus` ou implémentation directe)
- Scan d'esclaves M-Bus sur bus série
- Lecture des données de compteurs (énergie, eau, gaz, chaleur)
- Décodage des Data Records selon norme EN 13757

---

## V4 — BACnet (`BAC0` ou `bacpypes3`)
- Découverte des équipements BACnet sur le réseau (Who-Is / I-Am)
- Lecture des propriétés des objets (Present Value, Object Name, etc.)
- Écriture de propriétés (commande)
- Support BACnet/IP (UDP 47808)

---

## V5 — Outils avancés
- **OPC-UA Browser** (`opcua-asyncio`) : parcourir arborescence, lire nodes
- **SNMP Discovery** (`pysnmp`) : requêtes GET/WALK sur équipements réseau gérés
- **Calc Subnet** : calculateur CIDR, plages, broadcast
- **Traceroute** : visualisation des sauts réseau
- **Port Scanner** : vérification ports industriels (502, 102, 44818, 47808, 4840...)

---

## Dépendances principales par version

| Version | Librairies |
|---------|-----------|
| V1 | `ttkbootstrap`, `psutil`, `pyinstaller` |
| V2 | `pymodbus`, `pyserial` |
| V3 | `python-mbus` (ou implémentation directe RFC) |
| V4 | `BAC0` ou `bacpypes3` |
| V5 | `opcua-asyncio`, `pysnmp` |

## Contraintes techniques

- **Admin obligatoire** pour modifier la config IP → manifest UAC dans le `.exe`
- **Threading** obligatoire pour scan réseau, ping continu, lectures Modbus → jamais d'opération bloquante dans le thread UI
- **Windows uniquement** (`netsh`, WMI) → pas de compatibilité Linux/Mac prévue
- **Exe standalone** → toutes les dépendances bundlées via PyInstaller
