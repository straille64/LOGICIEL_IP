# modules/tab_scanner.py
import threading
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tableview import Tableview
from datetime import datetime
import csv
import os

from core.scanner import scan_range, ping_host


class TabScanner(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._scan_stop = threading.Event()
        self._ping_stop = threading.Event()
        self._scan_results = []
        self._ping_sent = self._ping_recv = self._ping_lost = 0
        self._build()

    def _build(self):
        # SCAN DE PLAGE
        scan_frame = ttk.LabelFrame(self, text="Scan de plage IP", padding=10)
        scan_frame.pack(fill=X, padx=10, pady=(10, 5))

        row1 = ttk.Frame(scan_frame)
        row1.pack(fill=X, pady=(0, 5))
        ttk.Label(row1, text="De :").pack(side=LEFT)
        self.scan_start = ttk.Entry(row1, width=16)
        self.scan_start.insert(0, "192.168.1.1")
        self.scan_start.pack(side=LEFT, padx=5)
        ttk.Label(row1, text="A :").pack(side=LEFT)
        self.scan_end = ttk.Entry(row1, width=16)
        self.scan_end.insert(0, "192.168.1.254")
        self.scan_end.pack(side=LEFT, padx=5)
        ttk.Label(row1, text="Timeout (ms) :").pack(side=LEFT, padx=(10, 0))
        self.scan_timeout = ttk.Spinbox(row1, from_=100, to=5000, increment=100, width=7)
        self.scan_timeout.set(500)
        self.scan_timeout.pack(side=LEFT, padx=5)
        ttk.Label(row1, text="Threads :").pack(side=LEFT)
        self.scan_threads = ttk.Spinbox(row1, from_=1, to=200, increment=10, width=6)
        self.scan_threads.set(50)
        self.scan_threads.pack(side=LEFT, padx=5)

        row2 = ttk.Frame(scan_frame)
        row2.pack(fill=X)
        self.btn_scan_start = ttk.Button(row2, text="Lancer", command=self._start_scan, bootstyle=SUCCESS)
        self.btn_scan_start.pack(side=LEFT, padx=(0, 5))
        self.btn_scan_stop = ttk.Button(row2, text="Stop", command=self._stop_scan, bootstyle=DANGER, state=DISABLED)
        self.btn_scan_stop.pack(side=LEFT, padx=(0, 10))
        self.scan_status = ttk.Label(row2, text="")
        self.scan_status.pack(side=LEFT)

        self.scan_progress = ttk.Progressbar(scan_frame, mode="determinate")
        self.scan_progress.pack(fill=X, pady=(5, 0))

        cols = [
            {"text": "Adresse IP", "stretch": False, "width": 130},
            {"text": "Nom d'hote", "stretch": True},
            {"text": "Statut", "stretch": False, "width": 80},
            {"text": "RTT (ms)", "stretch": False, "width": 80},
        ]
        self.table = Tableview(scan_frame, coldata=cols, rowdata=[], paginate=False,
                               bootstyle=INFO, stripecolor=None, height=8)
        self.table.pack(fill=BOTH, expand=True, pady=(5, 0))

        export_row = ttk.Frame(scan_frame)
        export_row.pack(fill=X, pady=(5, 0))
        ttk.Button(export_row, text="Exporter CSV", command=self._export_csv, bootstyle=SECONDARY).pack(side=LEFT, padx=(0, 5))
        self.scan_count = ttk.Label(export_row, text="")
        self.scan_count.pack(side=LEFT)

        # PING CONTINU
        ping_frame = ttk.LabelFrame(self, text="Ping continu", padding=10)
        ping_frame.pack(fill=BOTH, expand=True, padx=10, pady=(5, 10))

        ping_row = ttk.Frame(ping_frame)
        ping_row.pack(fill=X, pady=(0, 5))
        ttk.Label(ping_row, text="Cible :").pack(side=LEFT)
        self.ping_target = ttk.Entry(ping_row, width=20)
        self.ping_target.insert(0, "192.168.1.1")
        self.ping_target.pack(side=LEFT, padx=5)
        ttk.Label(ping_row, text="Intervalle :").pack(side=LEFT)
        self.ping_interval = ttk.Combobox(ping_row, values=["1s", "2s", "5s"], width=5, state="readonly")
        self.ping_interval.current(0)
        self.ping_interval.pack(side=LEFT, padx=5)
        self.btn_ping_start = ttk.Button(ping_row, text="Demarrer", command=self._start_ping, bootstyle=SUCCESS)
        self.btn_ping_start.pack(side=LEFT, padx=(10, 5))
        self.btn_ping_stop = ttk.Button(ping_row, text="Stop", command=self._stop_ping, bootstyle=DANGER, state=DISABLED)
        self.btn_ping_stop.pack(side=LEFT, padx=(0, 5))
        ttk.Button(ping_row, text="Sauvegarder log", command=self._save_ping_log, bootstyle=SECONDARY).pack(side=LEFT, padx=5)

        self.ping_text = tk.Text(ping_frame, height=8, font=("Consolas", 9), state=DISABLED)
        scroll = ttk.Scrollbar(ping_frame, command=self.ping_text.yview)
        self.ping_text.configure(yscrollcommand=scroll.set)
        self.ping_text.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        stats_row = ttk.Frame(ping_frame)
        stats_row.pack(fill=X, pady=(5, 0))
        self.ping_stats = ttk.Label(stats_row, text="Envoyes: 0  Recus: 0  Perdus: 0  Perte: 0%")
        self.ping_stats.pack(side=LEFT)

    # SCAN

    def _start_scan(self):
        self._scan_stop.clear()
        self.table.delete_rows()
        self.scan_progress["value"] = 0
        self.scan_count.configure(text="")
        self.btn_scan_start.configure(state=DISABLED)
        self.btn_scan_stop.configure(state=NORMAL)

        start = self.scan_start.get().strip()
        end = self.scan_end.get().strip()
        timeout = int(self.scan_timeout.get())
        threads = int(self.scan_threads.get())
        self._scan_results = []

        def _progress(done, total):
            pct = int(done / total * 100)
            self.after(0, lambda: self.scan_progress.configure(value=pct))
            self.after(0, lambda: self.scan_status.configure(text=f"{done}/{total}"))

        def _run():
            results = scan_range(start, end, timeout, threads, _progress, self._scan_stop)
            self._scan_results = results
            self.after(0, self._populate_table)

        threading.Thread(target=_run, daemon=True).start()

    def _stop_scan(self):
        self._scan_stop.set()
        self.btn_scan_start.configure(state=NORMAL)
        self.btn_scan_stop.configure(state=DISABLED)

    def _populate_table(self):
        alive = [r for r in self._scan_results if r["alive"]]
        for r in self._scan_results:
            status = "EN" if r["alive"] else "OFF"
            rtt = str(r["rtt_ms"]) if r["rtt_ms"] is not None else "-"
            self.table.insert_row("end", [r["ip"], r["hostname"], status, rtt])
        self.table.load_table_data()
        self.scan_count.configure(text=f"{len(alive)} actifs / {len(self._scan_results)} scannes")
        self.btn_scan_start.configure(state=NORMAL)
        self.btn_scan_stop.configure(state=DISABLED)

    def _export_csv(self):
        if not self._scan_results:
            return
        path = os.path.join(os.getcwd(), f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ip", "hostname", "alive", "rtt_ms"])
            writer.writeheader()
            writer.writerows(self._scan_results)

    # PING CONTINU

    def _start_ping(self):
        self._ping_stop.clear()
        self._ping_sent = self._ping_recv = self._ping_lost = 0
        self.ping_text.configure(state=NORMAL)
        self.ping_text.delete("1.0", tk.END)
        self.ping_text.configure(state=DISABLED)
        self.btn_ping_start.configure(state=DISABLED)
        self.btn_ping_stop.configure(state=NORMAL)

        target = self.ping_target.get().strip()
        interval = int(self.ping_interval.get().replace("s", ""))

        def _run():
            while not self._ping_stop.is_set():
                result = ping_host(target, timeout_ms=1000)
                ts = datetime.now().strftime("%H:%M:%S")
                self._ping_sent += 1
                if result["alive"]:
                    self._ping_recv += 1
                    line = f"{ts}  {target}  OK  RTT: {result['rtt_ms']}ms\n"
                else:
                    self._ping_lost += 1
                    line = f"{ts}  {target}  KO  Timeout\n"
                pct = round(self._ping_lost / self._ping_sent * 100, 1)
                stats = f"Envoyes: {self._ping_sent}  Recus: {self._ping_recv}  Perdus: {self._ping_lost}  Perte: {pct}%"
                self.after(0, lambda l=line, s=stats: self._append_ping(l, s))
                self._ping_stop.wait(timeout=interval)

        threading.Thread(target=_run, daemon=True).start()

    def _append_ping(self, line: str, stats: str):
        self.ping_text.configure(state=NORMAL)
        self.ping_text.insert(tk.END, line)
        self.ping_text.see(tk.END)
        self.ping_text.configure(state=DISABLED)
        self.ping_stats.configure(text=stats)

    def _stop_ping(self):
        self._ping_stop.set()
        self.btn_ping_start.configure(state=NORMAL)
        self.btn_ping_stop.configure(state=DISABLED)

    def _save_ping_log(self):
        content = self.ping_text.get("1.0", tk.END)
        path = os.path.join(os.getcwd(), f"ping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
