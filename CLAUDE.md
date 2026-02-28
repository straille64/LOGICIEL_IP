# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
python main.py

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_profiles.py -v

# Run a single test
pytest tests/test_scanner.py::test_ping_host_alive -v

# Build standalone .exe (output in dist/)
pyinstaller build.spec --clean

# Install dependencies
pip install -r requirements.txt
```

## Architecture

**Separation of concerns is strict:** `core/` has zero UI imports. `modules/` has zero system logic.

```
core/           # Pure business logic — no tkinter imports allowed
  network.py    # list_interfaces(), get_interface_config(), apply_static_ip(),
                # apply_dhcp(), apply_dns(), run_ipconfig() — uses netsh via subprocess
  profiles.py   # ProfileManager: save/load/list/delete JSON profiles in profiles/
  scanner.py    # generate_ip_range(), ping_host(), scan_range() — threaded ping sweep

modules/        # One file per tab — each is a ttk.Frame subclass
  tab_config.py # "Configuration & Outils": IP config, profiles, ipconfig/CMD tools
  tab_scanner.py# "Scanner Réseau" + "Ping continu" in same tab

main.py         # ttkbootstrap Window, instantiates Notebook, registers tabs
profiles/       # User-created JSON profiles (name.json)
```

## Key Conventions

**Threading:** Every network or system call runs in a `threading.Thread(daemon=True)`. Use `self.after(0, callback)` to update UI from background threads — never touch tkinter widgets from a non-main thread.

**Stop events:** Long-running loops (scan, continuous ping) use a `threading.Event` as stop flag. Check `stop_event.is_set()` in loops; call `stop_event.set()` from the Stop button.

**Admin rights:** Modifying IP requires elevation. The UAC manifest (`app.manifest`) requests `requireAdministrator` at exe launch. In dev, run `python main.py` from an admin terminal.

**netsh encoding:** `subprocess.run(["netsh", ...])` output is `cp850` on French Windows. Use `encoding="cp850"` when capturing text output.

**Adding a new module tab:**
1. Create `modules/tab_yourmodule.py` with a class inheriting `ttk.Frame`
2. Import and register it in `main.py` with `notebook.add(...)`

## Versioning Roadmap

| Version | Modules |
|---------|---------|
| V1 | Config IP, Profils, Outils (ipconfig/CMD), Scanner réseau, Ping continu |
| V2 | Modbus TCP/RTU (`pymodbus`), Serial/COM Monitor (`pyserial`) |
| V3 | M-Bus (energy/fluid meters) |
| V4 | BACnet (`BAC0` or `bacpypes3`) |
| V5 | OPC-UA Browser, SNMP Discovery, Calc Subnet, Traceroute, Port Scanner |

## Design Documents

- `docs/plans/2026-02-28-logiciel-ip-design.md` — full project design and rationale
- `docs/plans/2026-02-28-v1-implementation.md` — V1 step-by-step implementation plan
