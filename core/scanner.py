# core/scanner.py
import subprocess
import socket
import re
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

# Lazy-initialized MacLookup singleton (loading vendor DB is slow)
_mac_lookup_instance = None


def _mac_lookup():
    global _mac_lookup_instance
    if _mac_lookup_instance is None:
        from mac_vendor_lookup import MacLookup
        _mac_lookup_instance = MacLookup()
    return _mac_lookup_instance


def generate_ip_range(start_ip: str, end_ip: str) -> list[str]:
    """Génère la liste des IPs entre start et end inclus."""
    start = int(ipaddress.ip_address(start_ip))
    end = int(ipaddress.ip_address(end_ip))
    return [str(ipaddress.ip_address(i)) for i in range(start, end + 1)]


def ping_host(ip: str, timeout_ms: int = 500) -> dict:
    """Ping une IP. Retourne {'ip', 'alive', 'rtt_ms', 'hostname', 'mac', 'vendor'}."""
    result = {"ip": ip, "alive": False, "rtt_ms": None,
              "hostname": "", "mac": "", "vendor": ""}
    try:
        proc = subprocess.run(
            f"ping -n 1 -w {timeout_ms} {ip}",
            capture_output=True, text=True,
            timeout=(timeout_ms / 1000) + 2,
            shell=True,
        )
        if proc.returncode == 0:
            result["alive"] = True
            match = re.search(
                r"Minimum\s*=\s*(\d+)ms|temps[=<](\d+)\s*ms",
                proc.stdout, re.IGNORECASE
            )
            if match:
                val = match.group(1) or match.group(2)
                result["rtt_ms"] = int(val)
            try:
                result["hostname"] = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                result["hostname"] = ""
    except subprocess.TimeoutExpired:
        pass
    return result


def get_mac_from_arp(ip: str) -> str:
    """Return MAC address for ip from ARP table, or '' if not found."""
    try:
        proc = subprocess.run(
            f"arp -a {ip}",
            capture_output=True, text=True,
            encoding="cp850", shell=True, timeout=5,
        )
        match = re.search(
            r"([0-9a-f]{2}[:-]){5}[0-9a-f]{2}",
            proc.stdout, re.IGNORECASE
        )
        if match:
            return match.group(0).upper().replace("-", ":")
    except Exception:
        pass
    return ""


def get_vendor(mac: str) -> str:
    """Return vendor name for a MAC prefix, or '' if not found."""
    if not mac:
        return ""
    try:
        return _mac_lookup().lookup(mac)
    except Exception:
        return ""


def scan_range(
    start_ip: str,
    end_ip: str,
    timeout_ms: int = 500,
    max_threads: int = 50,
    progress_callback: Callable[[int, int], None] | None = None,
    stop_event=None,
) -> list[dict]:
    """Scan une plage IP en parallèle. Enrichit les hôtes actifs avec MAC + vendor."""
    ips = generate_ip_range(start_ip, end_ip)
    total = len(ips)
    results = []
    done = 0

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(ping_host, ip, timeout_ms): ip for ip in ips}
        for future in as_completed(futures):
            if stop_event and stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                break
            result = future.result()
            results.append(result)
            done += 1
            if progress_callback:
                progress_callback(done, total)

    results = sorted(results, key=lambda r: [int(x) for x in r["ip"].split(".")])

    # Enrich alive hosts with MAC + vendor (sequential — ARP reads are fast)
    for r in results:
        if r["alive"]:
            r["mac"] = get_mac_from_arp(r["ip"])
            r["vendor"] = get_vendor(r["mac"])

    return results
