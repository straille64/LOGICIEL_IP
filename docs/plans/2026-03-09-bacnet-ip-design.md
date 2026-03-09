# V4 — Onglet BACnet/IP : Design Document

**Date :** 2026-03-09
**Auteur :** Claude (session brainstorming)
**Statut :** Validé

---

## Contexte

V3 (M-Bus) est en cours. V4 ajoute un onglet BACnet/IP inspiré de BACEye, permettant la
découverte dynamique des équipements (Who-Is / I-Am), la navigation dans l'arborescence
Device → Objects → Properties, la lecture/écriture des valeurs, le polling cyclique et
les souscriptions COV.

Cas d'usage cibles :
- **Supervision légère** : découverte, lecture temps réel, écriture de setpoints
- **Commissioning / test** : exploration complète des propriétés, COV, ciblage direct

---

## Décisions d'Architecture

### Librairie : BAC0

- API haut niveau construite sur bacpypes3
- `pip install BAC0`
- Who-Is / I-Am intégré : `app.whois()` → liste de devices
- Lecture one-liner : `app.read('192.168.1.10 analogInput 1 presentValue')`
- COV natif : `app.subscribe_cov(device, obj)`
- Gère asyncio en interne dans un thread → compatible tkinter sans boilerplate
- Support BBMD : `BAC0.connect(ip='...', bbmdAddress='...', bbmdTTL=...)`

Alternatives écartées :
- **bacpypes3 direct** : async/await partout, conflit tkinter, boilerplate 3× plus long
- **bacpypes legacy** : déprécié, incompatible Python 3.12+

### Structure fichiers

```
core/bacnet.py               # BACnetClient — encapsule BAC0, zéro tkinter
modules/tab_bacnet.py        # TabBACnet(ttk.Frame)
modules/dialog_bacnet_obj.py # Popup "Détails complets" (≈ RegisterDetailDialog)
tests/test_bacnet.py         # Tests unitaires mockés BAC0
```

La séparation `core/` vs `modules/` est strictement respectée (même convention que V1–V3).

---

## Layout UI

```
╔══════════════════════════════════════════════════════════════════════════╗
║  IP locale [ 192.168.1.100/24  ]  BBMD [ ________________ ] TTL [  900 ]║
║  [ ▶ CONNEXION ]  [ 🔍 WHO-IS (Scan) ]  [ ■ DÉCONNEXION ]              ║
╠══════════════════╦═══════════════════════════════════════════════════════╣
║                  ║  Object Name        │ Type         │ Present_Value   ║
║ ▼ Device 101     ║ ──────────────────────────────────────────────────── ║
║    AI:1 — Temp   ║  Température Salle  │ Analog Input │ 21.5 °C        ║
║    AI:2 — Hum    ║  Humidité           │ Analog Input │ 58 %           ║
║    BO:1 — Pompe  ║  Pompe ECS          │ Binary Out   │ Active         ║
║    AV:1 — Csg    ║  Consigne CVC       │ Analog Value │ 22.0 °C  [✏]  ║
║                  ║ ──────────────────────────────────────────────────── ║
║ ▶ Device 205     ║  Reliability        │ Status_Flags │ Units          ║
║ ▶ Device 312     ║  No-Fault           │ [0,0,0,0]    │ degrees-celsius║
║                  ╠═══════════════════════════════════════════════════════╣
║                  ║  [ 📋 Détails complets ]  ☐ COV  ☐ Polling [ 1s ▾ ]║
║                  ║  Statut : Connecté — 3 devices trouvés               ║
╚══════════════════╩═══════════════════════════════════════════════════════╝
```

### Zones

| Zone | Rôle |
|------|------|
| **Barre réseau** (haut) | IP locale + masque, adresse BBMD optionnelle, TTL (défaut 900s). Boutons Connexion / Who-Is / Déconnexion |
| **Treeview gauche** | Arbre 2 niveaux : `Device NNN (nom)` → objets `Type:Instance — Nom`. Lazy loading au clic |
| **Tableau propriétés** (droite haut) | 5 colonnes : Object_Name, Type, Present_Value, Reliability, Units. Bouton ✏ sur objets inscriptibles |
| **Barre actions** (droite bas) | Bouton "Détails complets" → popup, checkbox COV, checkbox Polling + combobox intervalle |
| **Barre statut** | Message d'état courant (connexion, erreurs, nb devices) |

### Popup "Détails complets"

Sur le modèle de `RegisterDetailDialog` : tableau scrollable de toutes les propriétés
de l'objet lues via `ReadPropertyMultiple`. Colonnes : Property Name, Value.

---

## Interface `core/bacnet.py`

```python
@dataclass
class DeviceInfo:
    device_id: int
    address: str
    vendor_name: str
    object_name: str

@dataclass
class ObjectRef:
    object_type: str   # ex. "analogInput"
    instance: int
    name: str

class BACnetConnectionError(Exception): ...
class BACnetTimeoutError(Exception): ...
class BACnetWriteError(Exception): ...

class BACnetClient:
    def connect(local_ip: str, bbmd_address: str = None, bbmd_ttl: int = 900) -> None
    def disconnect() -> None
    @property is_connected: bool

    def who_is() -> list[DeviceInfo]
    def get_object_list(device: DeviceInfo) -> list[ObjectRef]

    def read_present_value(device: DeviceInfo, obj: ObjectRef) -> tuple[Any, str, str]
    # retourne (valeur, unité, reliability)

    def read_all_properties(device: DeviceInfo, obj: ObjectRef) -> dict[str, Any]
    # ReadPropertyMultiple — pour le popup Détails

    def write_present_value(device: DeviceInfo, obj: ObjectRef,
                            value: Any, priority: int = 8) -> None

    def subscribe_cov(device: DeviceInfo, obj: ObjectRef,
                      callback: Callable[[Any], None]) -> int  # → subscription_id
    def unsubscribe_cov(subscription_id: int) -> None
```

---

## Flux Threading

```
Thread principal (tkinter)
    │
    ├─ _btn_connect()      ──→  Thread daemon
    │                               BAC0.connect() [bloquant ~2s]
    │                               self.after(0, _on_connected)
    │
    ├─ _btn_whois()        ──→  Thread daemon
    │                               client.who_is() [timeout 3s]
    │                               self.after(0, _populate_tree)
    │
    ├─ _on_device_expand() ──→  Thread daemon
    │                               client.get_object_list()
    │                               self.after(0, _add_object_nodes)
    │
    └─ Polling cyclique    ──→  Thread daemon (threading.Event stop flag)
                                    client.read_present_value() en boucle
                                    self.after(0, _update_row)
```

Même pattern que `tab_scanner.py` et `tab_modbus.py` :
**aucun appel bloquant sur le thread principal**.

---

## Défis Techniques et Solutions

### 1. Port UDP 47808 — conflit

BACnet/IP bind le port UDP 47808. Un seul processus à la fois.

**Solution :** capturer `OSError: [WinError 10048]` → `BACnetConnectionError("Port UDP 47808
déjà utilisé par un autre processus")` → message explicite en barre de statut.

### 2. BAC0 / asyncio — compatibilité tkinter

BAC0 démarre asyncio dans un thread interne. Toutes les méthodes de `BACnetClient` sont
**synchrones** (wrappent les appels BAC0 avec `asyncio.run_coroutine_threadsafe(...).result(timeout=5)`).
L'UI ne voit jamais async/await.

### 3. Lazy loading Treeview

Réseau BACnet peut avoir des devices avec 200+ objets.

**Solution :** Who-Is → nœuds devices uniquement. Clic `▶ Device` → thread → `get_object_list()`
→ enfants. Nœud fantôme `("Chargement...",)` affiché pendant la requête.

### 4. COV vs Polling — coexistence

Tous les équipements ne supportent pas COV.

**Solution :** polling cyclique = mécanisme par défaut. Checkbox COV activée uniquement pour
les types supportés (AI, AO, AV, BI, BO, BV). En cas d'échec `subscribe_cov()` →
bascule silencieuse en polling + log statut.

### 5. Écriture — Priority Array

BACnet gère les écritures via un Priority Array (16 niveaux).

**Solution :** popup d'écriture : champ valeur + sélecteur priorité (1–16, défaut 8).
Pas de gestion de l'Array complet en V4.

### 6. Compatibilité Python 3.14

`netifaces` (dépendance BAC0) est problématique sur Python 3.12+.

**Solution :** utiliser `netifaces2` ou `psutil` pour la détection d'interfaces. À valider
en tout premier lors de l'implémentation.

---

## Périmètre V4 / Hors périmètre

| Fonctionnalité | V4 | Plus tard |
|----------------|-------|-----------|
| Connexion BACnet/IP locale | ✓ | |
| Support BBMD | ✓ | |
| Who-Is / I-Am discovery | ✓ | |
| Lazy loading objects | ✓ | |
| Lecture Present_Value + Reliability + Units | ✓ | |
| Polling cyclique | ✓ | |
| COV (best-effort) | ✓ | |
| Écriture avec priorité | ✓ | |
| Popup Détails (ReadPropertyMultiple) | ✓ | |
| Profils / favoris | | V4.1 |
| BACnet/MSTP (RS-485) | | V4.1 |
| Graphique temps réel | | V4.2 |
| Alarmes / Event enrollment | | V5 |
| Trending / historique | | V5 |

---

## Patterns réutilisés

| Pattern | Source |
|---------|--------|
| `threading.Event` + daemon thread + `self.after()` | `modules/tab_scanner.py` |
| `ttk.PanedWindow(HORIZONTAL)` layout | `modules/tab_config.py` |
| `ttk.Treeview` lazy expand | nouveau (inspiré tab_modbus) |
| Popup détails objet | `modules/dialog_register_detail.py` |
| Messagebox erreurs | `modules/tab_config.py` |
