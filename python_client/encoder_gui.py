import threading
import time
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

# UI / performance constants
UI_REFRESH_MS = 100
MAX_PLOT_POINTS = 4000
DECIMATE_TARGET = 4000


@dataclass
class Sample:
    t: float
    pulses: int
    delta: int
    force: Optional[float] = None


@dataclass
class DataBuffer:
    samples: List[Sample] = field(default_factory=list)
    last_pulses: Optional[int] = None
    start_time: Optional[float] = None

    def add(self, pulses: int, force: Optional[float] = None) -> Sample:
        now = time.perf_counter()
        if self.start_time is None:
            self.start_time = now
        rel_t = now - self.start_time
        if self.last_pulses is None:
            delta = 0
        else:
            delta = pulses - self.last_pulses
        self.last_pulses = pulses
        s = Sample(rel_t, pulses, delta, force)
        self.samples.append(s)
        return s

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

        # State
        self.selected_port = tk.StringVar()
        self.connection_state = tk.BooleanVar(value=False)
        self.running = tk.BooleanVar(value=False)
        self.autoscroll = tk.BooleanVar(value=True)

        # Data
        self.buffer = DataBuffer()
        self.current_force = 0.0
        self.force_timestamp = 0.0

        # Threads
        self.serial_thread: Optional[SerialReader] = None
        self.serial_stop = threading.Event()
        self.mutex = threading.Lock()

        self._build_ui()
        self._schedule_port_refresh()
        self._schedule_table_refresh()

    # UI construction
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

        self.btn_tare = ttk.Button(toolbar, text="Set Zero", command=self.send_tare, state=tk.DISABLED)
        self.btn_tare.pack(side=tk.LEFT, padx=4)

        ttk.Checkbutton(toolbar, text="Auto Scroll", variable=self.autoscroll).pack(side=tk.LEFT, padx=(12,4))

        # Force display
        force_box = ttk.LabelFrame(self.root, text="Current Force", padding=6)
        force_box.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(2,4))
        self.force_box_label = ttk.Label(force_box, text="0.000 kg", font=("Segoe UI", 16, "bold"))
        self.force_box_label.pack(side=tk.LEFT, padx=4)

        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # Table
        table_frame = ttk.Frame(main)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        columns = ("time_ms", "pulses", "delta", "force")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=25)
        for cid, title, w in (("time_ms","Time (ms)",90),("pulses","Pulses",80),("delta","Delta",70),("force","Force (kg)",90)):
            self.tree.heading(cid, text=title)
            self.tree.column(cid, width=w, anchor=tk.E)
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

    # Connection logic
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
            self.btn_tare.config(state=tk.NORMAL)
            self.status_label.config(text=f"Connected: {port}")
        else:
            self.serial_stop.set()
            self.connection_state.set(False)
            self.running.set(False)
            self.btn_connect.config(text="Connect")
            self.btn_run.config(text="Start", state=tk.DISABLED)
            self.btn_clear.config(state=tk.DISABLED)
            self.btn_export.config(state=tk.DISABLED)
            self.btn_tare.config(state=tk.DISABLED)
            self.status_label.config(text="Disconnected")

    def toggle_run(self):
        if not self.running.get():
            self.send_tare(auto=True)
            self.running.set(True)
            self.btn_run.config(text="Stop")
            self.btn_clear.config(state=tk.NORMAL)
            self.btn_export.config(state=tk.NORMAL)
            self.status_label.config(text="Running")
        else:
            self.running.set(False)
            self.btn_run.config(text="Start")
            self.status_label.config(text="Paused")

    def send_tare(self, auto: bool=False):
        if not self.connection_state.get():
            return
        try:
            if self.serial_thread and self.serial_thread.ser:
                self.serial_thread.ser.write(b"TARE\n")
                self.serial_thread.ser.flush()
                if not auto:
                    self.status_label.config(text="TARE sent")
        except Exception as e:
            if not auto:
                messagebox.showerror("TARE", f"Failed: {e}")

    # Actions
    def clear_data(self):
        if not messagebox.askyesno("Erase", "Clear all captured data?"):
            return
        with self.mutex:
            self.buffer.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
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
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
        if not path:
            return
        with self.mutex:
            rows = [{"time_s": s.t, "pulses": s.pulses, "delta": s.delta, "force_kg": s.force if s.force is not None else ""} for s in self.buffer.samples]
        df = pd.DataFrame(rows)
        try:
            with pd.ExcelWriter(path, engine='openpyxl') as w:
                df.to_excel(w, index=False, sheet_name='Data')
            messagebox.showinfo("Export", f"Exported {len(df)} rows to {path}")
        except Exception as e:
            messagebox.showerror("Export", f"Failed: {e}")

    # Serial line parsing
    def _on_serial_line(self, line: str):
        if not self.running.get():
            return
        low = line.lower().strip()
        # Force only
        if (low.startswith("force=") or low.startswith("weight=") or low.startswith("load=")) and not low.startswith("pos="):
            try:
                val = line.split('=')[1]
                if val.lower().endswith('kg'):
                    val = val[:-2]
                f = float(val)
                with self.mutex:
                    self.current_force = f
                    self.force_timestamp = time.time()
            except Exception:
                pass
            self.force_box_label.config(text=f"{self.current_force:.3f} kg")
            return
        # Encoder line
        if line.startswith("Pos="):
            try:
                base = line.split()[0]
                pulses = int(base.split('=')[1])
            except Exception:
                return
            force_val = None
            if "force=" in low:
                try:
                    token = [p for p in line.split() if p.lower().startswith("force=")]
                    if token:
                        fv = token[0].split('=')[1]
                        if fv.lower().endswith('kg'):
                            fv = fv[:-2]
                        force_val = float(fv)
                        with self.mutex:
                            self.current_force = force_val
                            self.force_timestamp = time.time()
                except Exception:
                    pass
            if force_val is None:
                force_val = self.current_force
            with self.mutex:
                self.buffer.add(pulses, force_val)
            self.force_box_label.config(text=f"{self.current_force:.3f} kg")

    # Periodic tasks
    def _schedule_port_refresh(self):
        self._refresh_ports()
        self.root.after(2000, self._schedule_port_refresh)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        existing = set(self.port_combo['values']) if self.port_combo['values'] else set()
        cur = set(ports)
        if cur != existing:
            self.port_combo['values'] = ports
            if self.selected_port.get() not in ports:
                self.selected_port.set(ports[0] if ports else "")

    def _schedule_table_refresh(self):
        self._update_table_and_plot()
        self.root.after(UI_REFRESH_MS, self._schedule_table_refresh)

    def _update_table_and_plot(self):
        with self.mutex:
            data = list(self.buffer.samples)
        if not data:
            return
        existing = len(self.tree.get_children())
        new_items = data[existing:]
        last_id = None
        if new_items:
            for s in new_items:
                fv = f"{s.force:.3f}" if s.force is not None else ""
                last_id = self.tree.insert("", tk.END, values=(f"{s.t*1000:.1f}", s.pulses, s.delta, fv))
            if self.autoscroll.get() and last_id is not None:
                self.tree.see(last_id)
        total = len(data)
        if total > MAX_PLOT_POINTS * 2:
            step = max(1, total // DECIMATE_TARGET)
            subset = data[::step]
        else:
            subset = data[-MAX_PLOT_POINTS:]
        times = [s.t for s in subset]
        pulses = [s.pulses for s in subset]
        if not times:
            return
        self.line_plot.set_data(times, pulses)
        self.ax.set_xlim(times[0], times[-1])
        ymin = min(pulses)
        ymax = max(pulses)
        if ymin == ymax:
            ymax = ymin + 1
        self.ax.set_ylim(ymin, ymax)
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
