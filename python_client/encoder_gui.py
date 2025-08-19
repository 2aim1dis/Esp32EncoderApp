import sys
import threading
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional

import serial
import serial.tools.list_ports
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

SAMPLE_INTERVAL_S = 0.010  # 10 ms table resolution

@dataclass
class Sample:
    t: float
    pulses: int
    delta: int

@dataclass
class DataBuffer:
    samples: List[Sample] = field(default_factory=list)
    last_pulses: Optional[int] = None
    start_time: Optional[float] = None

    def add(self, pulses: int):
        now = time.perf_counter()
        if self.start_time is None:
            self.start_time = now
        rel_t = now - self.start_time
        if self.last_pulses is None:
            delta = 0
        else:
            delta = pulses - self.last_pulses
        self.last_pulses = pulses
        sample = Sample(rel_t, pulses, delta)
        self.samples.append(sample)
        return sample

    def clear(self):
        self.samples.clear()
        self.last_pulses = None
        self.start_time = None

class SerialReader(threading.Thread):
    def __init__(self, port_getter, baud: int, line_callback, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.port_getter = port_getter
        self.baud = baud
        self.line_callback = line_callback
        self.stop_event = stop_event
        self.ser: Optional[serial.Serial] = None

    def run(self):
        while not self.stop_event.is_set():
            port = self.port_getter()
            if not port:
                time.sleep(0.5)
                continue
            try:
                self.ser = serial.Serial(port, self.baud, timeout=0.2)
                self.ser.reset_input_buffer()
                while not self.stop_event.is_set():
                    line = self.ser.readline().decode(errors='ignore').strip()
                    if line:
                        self.line_callback(line)
            except serial.SerialException:
                time.sleep(0.5)
            finally:
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                    self.ser = None

class EncoderGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("ESP32 Encoder Monitor")

        self.selected_port = tk.StringVar()
        self.connection_state = tk.BooleanVar(value=False)
        self.running = tk.BooleanVar(value=False)

        self.buffer = DataBuffer()
        self.last_table_update = 0.0

        self.serial_thread: Optional[SerialReader] = None
        self.serial_stop = threading.Event()
        self.mutex = threading.Lock()

        self._build_ui()
        self._schedule_port_refresh()
        self._schedule_table_refresh()

    # UI Construction
    def _build_ui(self):
        toolbar = ttk.Frame(self.root, padding=4)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="Port:").pack(side=tk.LEFT)
        self.port_combo = ttk.Combobox(toolbar, width=15, textvariable=self.selected_port, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=4)

        self.btn_connect = ttk.Button(toolbar, text="Connect", command=self.toggle_connect)
        self.btn_connect.pack(side=tk.LEFT, padx=4)

        self.btn_run = ttk.Button(toolbar, text="Start", command=self.toggle_run, state=tk.DISABLED)
        self.btn_run.pack(side=tk.LEFT, padx=4)

        self.btn_clear = ttk.Button(toolbar, text="Erase Data", command=self.clear_data, state=tk.DISABLED)
        self.btn_clear.pack(side=tk.LEFT, padx=4)

        self.btn_export = ttk.Button(toolbar, text="Export Excel", command=self.export_excel, state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=4)

        # Main area split
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # Table
        table_frame = ttk.Frame(main)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        columns = ("time_ms", "pulses", "delta")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        self.tree.heading("time_ms", text="Time (ms)")
        self.tree.heading("pulses", text="Pulses")
        self.tree.heading("delta", text="Delta")
        self.tree.column("time_ms", width=90, anchor=tk.E)
        self.tree.column("pulses", width=80, anchor=tk.E)
        self.tree.column("delta", width=70, anchor=tk.E)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Plot
        plot_frame = ttk.Frame(main)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(5,4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Pulses")
        self.line_plot, = self.ax.plot([], [], lw=1.2)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        status = ttk.Frame(self.root, padding=4)
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status, text="Idle")
        self.status_label.pack(side=tk.LEFT)

    # Serial handling
    def toggle_connect(self):
        if not self.connection_state.get():
            port = self.selected_port.get()
            if not port:
                messagebox.showwarning("Port", "Select a COM port first")
                return
            self.serial_stop.clear()
            self.serial_thread = SerialReader(lambda: self.selected_port.get(), 115200, self._on_serial_line, self.serial_stop)
            self.serial_thread.start()
            self.connection_state.set(True)
            self.btn_connect.config(text="Disconnect")
            self.btn_run.config(state=tk.NORMAL)
            self.status_label.config(text=f"Connected: {port}")
        else:
            self.serial_stop.set()
            self.connection_state.set(False)
            self.running.set(False)
            self.btn_connect.config(text="Connect")
            self.btn_run.config(text="Start", state=tk.DISABLED)
            self.btn_clear.config(state=tk.DISABLED)
            self.btn_export.config(state=tk.DISABLED)
            self.status_label.config(text="Disconnected")

    def toggle_run(self):
        if not self.running.get():
            self.running.set(True)
            self.btn_run.config(text="Stop")
            self.btn_clear.config(state=tk.NORMAL)
            self.btn_export.config(state=tk.NORMAL)
            self.status_label.config(text="Running")
        else:
            self.running.set(False)
            self.btn_run.config(text="Start")
            self.status_label.config(text="Paused")

    def clear_data(self):
        if messagebox.askyesno("Erase", "Clear all captured data?"):
            with self.mutex:
                self.buffer.clear()
            for row in self.tree.get_children():
                self.tree.delete(row)
            self.ax.cla()
            self.ax.set_xlabel("Time (s)")
            self.ax.set_ylabel("Pulses")
            self.line_plot, = self.ax.plot([], [], lw=1.2)
            self.canvas.draw_idle()
            self.status_label.config(text="Data cleared")

    def export_excel(self):
        if not self.buffer.samples:
            messagebox.showinfo("Export", "No data to export.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
        if not file_path:
            return
        with self.mutex:
            data = [{"time_s": s.t, "pulses": s.pulses, "delta": s.delta} for s in self.buffer.samples]
        df = pd.DataFrame(data)
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
                # Add a simple chart via pandas/matplotlib export (embedding already in file not trivial with openpyxl alone)
                # For richer Excel chart embedding, xlsxwriter could be used.
                messagebox.showinfo("Export", f"Exported {len(df)} rows to {file_path}")
        except Exception as e:
            messagebox.showerror("Export", f"Failed: {e}")

    def _on_serial_line(self, line: str):
        if not self.running.get():
            return
        # Expected format: Pos=12345 cps=... rpm=...
        if line.startswith("Pos="):
            try:
                # Parse until space or end
                part = line.split()[0]  # Pos=12345
                pulses = int(part.split('=')[1])
            except Exception:
                return
            with self.mutex:
                self.buffer.add(pulses)

    # Periodic tasks
    def _schedule_port_refresh(self):
        self._refresh_ports()
        self.root.after(2000, self._schedule_port_refresh)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        current = set(ports)
        existing = set(self.port_combo['values']) if self.port_combo['values'] else set()
        if current != existing:
            self.port_combo['values'] = ports
            if self.selected_port.get() not in ports:
                if ports:
                    self.selected_port.set(ports[0])
                else:
                    self.selected_port.set("")

    def _schedule_table_refresh(self):
        self._update_table_and_plot()
        self.root.after(int(SAMPLE_INTERVAL_S * 1000), self._schedule_table_refresh)

    def _update_table_and_plot(self):
        with self.mutex:
            data = list(self.buffer.samples)
        if not data:
            return
        # Update table (append new rows since last length)
        existing_rows = len(self.tree.get_children())
        for s in data[existing_rows:]:
            self.tree.insert("", tk.END, values=(f"{s.t*1000:.1f}", s.pulses, s.delta))
        # Update plot
        times = [s.t for s in data]
        pulses = [s.pulses for s in data]
        self.ax.cla()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Pulses")
        self.ax.plot(times, pulses, lw=1.2)
        self.canvas.draw_idle()

    def on_close(self):
        self.serial_stop.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    gui = EncoderGUI(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_close)
    root.mainloop()

if __name__ == '__main__':
    main()
