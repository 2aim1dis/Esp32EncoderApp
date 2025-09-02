"""
Main GUI application for ESP32 encoder monitoring.
Modular design with separate components for data handling, visualization, and communication.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from typing import Optional

from data_models import DataBuffer
from serial_handler import SerialThread, get_available_ports, find_esp32_port
from visualization import EncoderPlot, DataTable


class EncoderGUI:
    """Main GUI application for encoder monitoring."""
    
    def __init__(self):
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("ESP32 Encoder Monitor")
        self.root.geometry("1000x700")
        
        # Data management
        self.buffer = DataBuffer()
        self.mutex = threading.Lock()
        
        # Communication
        self.serial_thread: Optional[SerialThread] = None
        self.connection_state = tk.BooleanVar(value=False)
        self.running = tk.BooleanVar(value=False)
        
        # Create GUI components
        self._create_widgets()
        self._setup_periodic_tasks()
        
        # Try to auto-detect ESP32 port
        auto_port = find_esp32_port()
        if auto_port:
            self.port_var.set(auto_port)
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Connection frame
        conn_frame = ttk.LabelFrame(main_frame, text="Connection", padding="5")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=(0, 5))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=15)
        self.port_combo.grid(row=0, column=1, padx=(0, 10))
        
        self.btn_refresh = ttk.Button(conn_frame, text="Refresh", command=self._refresh_ports)
        self.btn_refresh.grid(row=0, column=2, padx=(0, 10))
        
        self.btn_connect = ttk.Button(conn_frame, text="Connect", command=self._toggle_connection)
        self.btn_connect.grid(row=0, column=3, padx=(0, 10))
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected")
        self.status_label.grid(row=0, column=4, padx=(10, 0))
        
        # Control frame
        ctrl_frame = ttk.LabelFrame(main_frame, text="Control", padding="5")
        ctrl_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        self.btn_run = ttk.Button(ctrl_frame, text="Start", command=self._toggle_run, state=tk.DISABLED)
        self.btn_run.grid(row=0, column=0, padx=(0, 10))
        
        self.btn_zero = ttk.Button(ctrl_frame, text="Zero Position", command=self._send_zero, state=tk.DISABLED)
        self.btn_zero.grid(row=0, column=1, padx=(0, 10))
        
        self.btn_clear = ttk.Button(ctrl_frame, text="Clear Data", command=self._clear_data, state=tk.DISABLED)
        self.btn_clear.grid(row=0, column=2, padx=(0, 10))
        
        self.btn_export = ttk.Button(ctrl_frame, text="Export Data", command=self._export_data, state=tk.DISABLED)
        self.btn_export.grid(row=0, column=3, padx=(0, 10))
        
        # Data visualization frame
        viz_frame = ttk.LabelFrame(main_frame, text="Real-time Data", padding="5")
        viz_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        main_frame.rowconfigure(2, weight=1)
        
        # Create plot and table
        plot_frame = ttk.Frame(viz_frame)
        plot_frame.pack(side="top", fill="both", expand=True, pady=(0, 10))
        
        table_frame = ttk.Frame(viz_frame)
        table_frame.pack(side="bottom", fill="x")
        
        self.plot = EncoderPlot(plot_frame)
        self.table = DataTable(table_frame)
        
        # Initialize port list
        self._refresh_ports()
    
    def _refresh_ports(self):
        """Refresh the list of available serial ports."""
        ports = get_available_ports()
        self.port_combo['values'] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])
    
    def _toggle_connection(self):
        """Toggle serial connection."""
        if not self.connection_state.get():
            port = self.port_var.get()
            if not port:
                messagebox.showerror("Error", "Please select a port")
                return
            
            # Create and start serial thread
            self.serial_thread = SerialThread(port, line_callback=self._on_serial_line)
            if self.serial_thread.connect():
                self.serial_thread.start_reading()
                self.connection_state.set(True)
                self.btn_connect.config(text="Disconnect")
                self.btn_run.config(state=tk.NORMAL)
                self.btn_zero.config(state=tk.NORMAL)
                self.status_label.config(text=f"Connected: {port}")
            else:
                messagebox.showerror("Error", f"Failed to connect to {port}")
                self.serial_thread = None
        else:
            # Disconnect
            if self.serial_thread:
                self.serial_thread.disconnect()
                self.serial_thread = None
            self.connection_state.set(False)
            self.running.set(False)
            self.btn_connect.config(text="Connect")
            self.btn_run.config(text="Start", state=tk.DISABLED)
            self.btn_zero.config(state=tk.DISABLED)
            self.btn_clear.config(state=tk.DISABLED)
            self.btn_export.config(state=tk.DISABLED)
            self.status_label.config(text="Disconnected")
    
    def _toggle_run(self):
        """Toggle data acquisition."""
        if not self.running.get():
            self.running.set(True)
            self.btn_run.config(text="Stop")
            self.btn_clear.config(state=tk.NORMAL)
            self.btn_export.config(state=tk.NORMAL)
            self.status_label.config(text="Running")
        else:
            self.running.set(False)
            self.btn_run.config(text="Start")
            self.status_label.config(text="Connected")
    
    def _send_zero(self):
        """Send zero position command to ESP32."""
        if self.serial_thread:
            if self.serial_thread.send_command("zero"):
                self.status_label.config(text="Zero position sent")
            else:
                messagebox.showerror("Error", "Failed to send zero command")
    
    def _clear_data(self):
        """Clear all captured data."""
        if not messagebox.askyesno("Clear Data", "Clear all captured data?"):
            return
        
        with self.mutex:
            self.buffer.clear()
        self.table.clear()
        self.plot.update_plot(self.buffer)
        self.status_label.config(text="Data cleared")
    
    def _export_data(self):
        """Export data to Excel file."""
        if not self.buffer.samples:
            messagebox.showwarning("Export", "No data to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
        )
        if not filename:
            return
        
        try:
            with self.mutex:
                data = [
                    {
                        "Time (ms)": f"{sample.time_ms:.3f}",  # Αλλάζω από .1f σε .3f
                        "Pos": sample.pos if sample.pos else "",
                        "CPS": sample.cps if sample.cps else "",
                        "RPM": sample.rpm if sample.rpm else ""
                    }
                    for sample in self.buffer.samples
                ]
            
            df = pd.DataFrame(data)
            if filename.endswith('.xlsx'):
                df.to_excel(filename, index=False)
            else:
                df.to_csv(filename, index=False)
            
            messagebox.showinfo("Export", f"Exported {len(data)} samples to {filename}")
            self.status_label.config(text=f"Data exported ({len(data)} samples)")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {e}")
    
    def _on_serial_line(self, line: str):
        """Process incoming serial data line."""
        if not self.running.get():
            return
        
        # Store the raw ESP32 output line
        line = line.strip()
        if line:  # Only process non-empty lines
            with self.mutex:
                self.buffer.add(line)
    
    def _setup_periodic_tasks(self):
        """Setup periodic GUI updates."""
        def update_displays():
            if self.running.get():
                with self.mutex:
                    self.table.update_table(self.buffer)
                    self.plot.update_plot(self.buffer)
            
            # Schedule next update
            self.root.after(10, update_displays)  # 10ms refresh rate (100 Hz)
        
        # Start periodic updates
        self.root.after(10, update_displays)
    
    def run(self):
        """Start the GUI application."""
        try:
            self.root.mainloop()
        finally:
            # Cleanup on exit
            if self.serial_thread:
                self.serial_thread.disconnect()


if __name__ == "__main__":
    app = EncoderGUI()
    app.run()
