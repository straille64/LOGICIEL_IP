# core/network.py
import subprocess
import psutil
import socket


def list_interfaces() -> list[dict]:
    """Retourne les interfaces réseau actives avec leur IP."""
    interfaces = []
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    for name, addr_list in addrs.items():
        if name not in stats or not stats[name].isup:
            continue
        ip = ""
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                ip = addr.address
                break
        interfaces.append({"name": name, "ip": ip})
    return interfaces


def get_interface_config(iface_name: str) -> dict:
    """Retourne la config IP complète d'une interface."""
    addrs = psutil.net_if_addrs().get(iface_name, [])
    result = {"ip": "", "mask": "", "gateway": "", "dns1": "", "dns2": ""}
    for addr in addrs:
        if addr.family == socket.AF_INET:
            result["ip"] = addr.address
            result["mask"] = addr.netmask or ""
    try:
        out = subprocess.run(
            ["netsh", "interface", "ip", "show", "config", f"name={iface_name}"],
            capture_output=True, text=True, encoding="cp850"
        ).stdout
        for line in out.splitlines():
            if "Default Gateway" in line or "Passerelle" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    result["gateway"] = parts[1].strip()
            if "DNS" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    val = parts[1].strip()
                    if val and val[0].isdigit():
                        if not result["dns1"]:
                            result["dns1"] = val
                        elif not result["dns2"]:
                            result["dns2"] = val
    except Exception:
        pass
    return result


def apply_static_ip(iface_name: str, ip: str, mask: str, gateway: str) -> None:
    """Applique une IP statique. Requiert droits admin."""
    cmd = (
        f"netsh interface ip set address"
        f' name="{iface_name}" source=static'
        f" addr={ip} mask={mask} gateway={gateway}"
    )
    subprocess.run(cmd, check=True, capture_output=True, shell=True)


def apply_dns(iface_name: str, dns1: str, dns2: str = "") -> None:
    """Configure les serveurs DNS. Requiert droits admin."""
    cmd1 = (
        f"netsh interface ip set dns"
        f' name="{iface_name}" source=static addr={dns1}'
    )
    subprocess.run(cmd1, check=True, capture_output=True, shell=True)
    if dns2:
        cmd2 = (
            f"netsh interface ip add dns"
            f' name="{iface_name}" addr={dns2} index=2'
        )
        subprocess.run(cmd2, check=True, capture_output=True, shell=True)


def apply_dhcp(iface_name: str) -> None:
    """Passe l'interface en DHCP. Requiert droits admin."""
    cmd1 = f'netsh interface ip set address name="{iface_name}" source=dhcp'
    subprocess.run(cmd1, check=True, capture_output=True, shell=True)
    cmd2 = f'netsh interface ip set dns name="{iface_name}" source=dhcp'
    subprocess.run(cmd2, check=True, capture_output=True, shell=True)


def run_ipconfig() -> str:
    """Retourne la sortie de ipconfig /all."""
    result = subprocess.run(
        ["ipconfig", "/all"], capture_output=True, text=True, encoding="cp850"
    )
    return result.stdout
