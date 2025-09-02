"""
Enhanced encoder GUI with additional useful features.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from typing import Optional
import json
from datetime import datetime

from data_models import DataBuffer
from serial_handler import SerialThread, get_available_ports, find_esp32_port
from visualization import EncoderPlot, DataTable


class EnhancedEncoderGUI:
    """Enhanced GUI with statistics, settings, and analysis features."""
    
    def __init__(self):
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("ESP32 Encoder Monitor - Enhanced")
        self.root.geometry("1200x800")
        
        # Data management
        self.buffer = DataBuffer()
        self.mutex = threading.Lock()
        
        # Statistics tracking
        self.session_stats = {
            'start_time': None,
            'total_samples': 0,
            'min_pos': None,
            'max_pos': None,
            'total_distance': 0,
            'max_speed': 0
        }
        
        # Communication
        self.serial_thread: Optional[SerialThread] = None
        self.connection_state = tk.BooleanVar(value=False)
        self.running = tk.BooleanVar(value=False)
        
        # Settings
        self.settings = {
            'refresh_rate_ms': 100,
            'max_table_rows': 100,
            'pulses_per_revolution': 1024,  # Configurable
            'auto_save': False,
            'save_interval_min': 5
        }
        
        # Create GUI components
        self._create_widgets()
        self._setup_periodic_tasks()
        self._load_settings()
        
        # Try to auto-detect ESP32 port
        auto_port = find_esp32_port()
        if auto_port:
            self.port_var.set(auto_port)
    
    def _create_widgets(self):
        """Create all GUI widgets with enhanced features."""
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main monitoring tab
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Monitor")
        
        # Statistics tab
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="Statistics")
        
        # Settings tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        
        # Create main monitoring interface
        self._create_main_tab(main_frame)
        
        # Create statistics tab
        self._create_stats_tab(stats_frame)
        
        # Create settings tab
        self._create_settings_tab(settings_frame)
    
    def _create_main_tab(self, parent):
        """Create the main monitoring interface."""
        # Connection frame
        conn_frame = ttk.LabelFrame(parent, text="Connection", padding="5")
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
        
        # Enhanced control frame
        ctrl_frame = ttk.LabelFrame(parent, text="Control", padding="5")
        ctrl_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        self.btn_run = ttk.Button(ctrl_frame, text="Start", command=self._toggle_run, state=tk.DISABLED)
        self.btn_run.grid(row=0, column=0, padx=(0, 10))
        
        self.btn_zero = ttk.Button(ctrl_frame, text="Zero Position", command=self._send_zero, state=tk.DISABLED)
        self.btn_zero.grid(row=0, column=1, padx=(0, 10))
        
        self.btn_clear = ttk.Button(ctrl_frame, text="Clear Data", command=self._clear_data, state=tk.DISABLED)
        self.btn_clear.grid(row=0, column=2, padx=(0, 10))
        
        self.btn_export = ttk.Button(ctrl_frame, text="Export Data", command=self._export_data, state=tk.DISABLED)
        self.btn_export.grid(row=0, column=3, padx=(0, 10))
        
        # Add snapshot button
        self.btn_snapshot = ttk.Button(ctrl_frame, text="Save Snapshot", command=self._save_snapshot, state=tk.DISABLED)
        self.btn_snapshot.grid(row=0, column=4, padx=(0, 10))
        
        # Real-time info frame
        info_frame = ttk.LabelFrame(parent, text="Real-time Info", padding="5")
        info_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Current values display
        ttk.Label(info_frame, text="Position:").grid(row=0, column=0, sticky="w")
        self.current_pos_label = ttk.Label(info_frame, text="--", font=("Arial", 10, "bold"))
        self.current_pos_label.grid(row=0, column=1, sticky="w", padx=(5, 20))
        
        ttk.Label(info_frame, text="Speed (CPS):").grid(row=0, column=2, sticky="w")
        self.current_cps_label = ttk.Label(info_frame, text="--", font=("Arial", 10, "bold"))
        self.current_cps_label.grid(row=0, column=3, sticky="w", padx=(5, 20))
        
        ttk.Label(info_frame, text="RPM:").grid(row=0, column=4, sticky="w")
        self.current_rpm_label = ttk.Label(info_frame, text="--", font=("Arial", 10, "bold"))
        self.current_rpm_label.grid(row=0, column=5, sticky="w", padx=(5, 0))
        
        # Data visualization frame
        viz_frame = ttk.LabelFrame(parent, text="Real-time Data", padding="5")
        viz_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        parent.rowconfigure(3, weight=1)
        
        # Create plot and table
        plot_frame = ttk.Frame(viz_frame)
        plot_frame.pack(side="top", fill="both", expand=True, pady=(0, 10))
        
        table_frame = ttk.Frame(viz_frame)
        table_frame.pack(side="bottom", fill="x")
        
        self.plot = EncoderPlot(plot_frame)
        self.table = DataTable(table_frame)
        
        # Initialize port list
        self._refresh_ports()
    
    def _create_stats_tab(self, parent):
        """Create statistics display tab."""
        stats_main = ttk.Frame(parent, padding="10")
        stats_main.pack(fill="both", expand=True)
        
        # Session statistics
        session_frame = ttk.LabelFrame(stats_main, text="Session Statistics", padding="10")
        session_frame.pack(fill="x", pady=(0, 10))
        
        self.stats_labels = {}
        stats_items = [
            ("Session Duration:", "session_duration"),
            ("Total Samples:", "total_samples"),
            ("Sample Rate:", "sample_rate"),
            ("Min Position:", "min_pos"),
            ("Max Position:", "max_pos"),
            ("Total Distance:", "total_distance"),
            ("Max Speed (CPS):", "max_speed"),
        ]
        
        for i, (label_text, key) in enumerate(stats_items):
            ttk.Label(session_frame, text=label_text).grid(row=i, column=0, sticky="w", pady=2)
            self.stats_labels[key] = ttk.Label(session_frame, text="--", font=("Arial", 10, "bold"))
            self.stats_labels[key].grid(row=i, column=1, sticky="w", padx=(10, 0), pady=2)
        
        # Analysis frame
        analysis_frame = ttk.LabelFrame(stats_main, text="Analysis Tools", padding="10")
        analysis_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(analysis_frame, text="Calculate RPM from Distance", 
                  command=self._analyze_rpm).pack(side="left", padx=(0, 10))
        ttk.Button(analysis_frame, text="Export Statistics", 
                  command=self._export_stats).pack(side="left", padx=(0, 10))
        ttk.Button(analysis_frame, text="Reset Statistics", 
                  command=self._reset_stats).pack(side="left")
    
    def _create_settings_tab(self, parent):
        """Create settings configuration tab."""
        settings_main = ttk.Frame(parent, padding="10")
        settings_main.pack(fill="both", expand=True)
        
        # GUI Settings
        gui_frame = ttk.LabelFrame(settings_main, text="GUI Settings", padding="10")
        gui_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(gui_frame, text="Refresh Rate (ms):").grid(row=0, column=0, sticky="w", pady=2)
        self.refresh_var = tk.IntVar(value=self.settings['refresh_rate_ms'])
        ttk.Scale(gui_frame, from_=50, to=500, variable=self.refresh_var, 
                 orient="horizontal").grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        ttk.Label(gui_frame, text="Max Table Rows:").grid(row=1, column=0, sticky="w", pady=2)
        self.table_rows_var = tk.IntVar(value=self.settings['max_table_rows'])
        ttk.Scale(gui_frame, from_=50, to=500, variable=self.table_rows_var, 
                 orient="horizontal").grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Encoder Settings
        encoder_frame = ttk.LabelFrame(settings_main, text="Encoder Settings", padding="10")
        encoder_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(encoder_frame, text="Pulses per Revolution:").grid(row=0, column=0, sticky="w", pady=2)
        self.ppr_var = tk.IntVar(value=self.settings['pulses_per_revolution'])
        ttk.Entry(encoder_frame, textvariable=self.ppr_var, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        
        # Save settings button
        ttk.Button(settings_main, text="Save Settings", 
                  command=self._save_settings).pack(pady=10)
    
    def _save_snapshot(self):
        """Save current plot as image."""
        if not self.buffer.samples:
            messagebox.showwarning("Snapshot", "No data to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("PDF files", "*.pdf")]
        )
        if filename:
            try:
                self.plot.fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Snapshot", f"Plot saved to {filename}")
            except Exception as e:
                messagebox.showerror("Snapshot Error", f"Failed to save plot: {e}")
    
    def _analyze_rpm(self):
        """Analyze and display RPM calculations."""
        if not self.buffer.samples:
            messagebox.showwarning("Analysis", "No data to analyze")
            return
        
        # Calculate RPM from position changes
        pos_samples = [s for s in self.buffer.samples if s.pos]
        if len(pos_samples) < 2:
            return
        
        ppr = self.ppr_var.get()
        time_diff = (pos_samples[-1].time_ms - pos_samples[0].time_ms) / 1000.0  # seconds
        pos_diff = abs(int(pos_samples[-1].pos) - int(pos_samples[0].pos))
        
        revolutions = pos_diff / ppr
        rpm = (revolutions / time_diff) * 60
        
        messagebox.showinfo("RPM Analysis", 
            f"Analysis Results:\n"
            f"Time Period: {time_diff:.2f} seconds\n"
            f"Position Change: {pos_diff} pulses\n"
            f"Revolutions: {revolutions:.3f}\n"
            f"Calculated RPM: {rpm:.2f}")
    
    def _export_stats(self):
        """Export session statistics."""
        if not self.buffer.samples:
            messagebox.showwarning("Export", "No statistics to export")
            return
        
        stats = self._calculate_stats()
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt")]
        )
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w') as f:
                        json.dump(stats, f, indent=2)
                else:
                    with open(filename, 'w') as f:
                        for key, value in stats.items():
                            f.write(f"{key}: {value}\n")
                messagebox.showinfo("Export", f"Statistics saved to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save statistics: {e}")
    
    def _calculate_stats(self):
        """Calculate comprehensive statistics."""
        if not self.buffer.samples:
            return {}
        
        pos_samples = [s for s in self.buffer.samples if s.pos]
        if not pos_samples:
            return {}
        
        positions = [int(s.pos) for s in pos_samples]
        
        return {
            'session_start': datetime.fromtimestamp(time.time() - self.buffer.samples[-1].time_ms/1000).isoformat(),
            'total_samples': len(self.buffer.samples),
            'position_samples': len(pos_samples),
            'min_position': min(positions),
            'max_position': max(positions),
            'position_range': max(positions) - min(positions),
            'session_duration_seconds': self.buffer.samples[-1].time_ms / 1000,
            'average_sample_rate_hz': len(self.buffer.samples) / (self.buffer.samples[-1].time_ms / 1000),
            'pulses_per_revolution': self.ppr_var.get()
        }
    
    # Add the rest of the methods (connection, data handling, etc.)
    # These would be similar to the original GUI but with enhanced features
    
    def run(self):
        """Start the enhanced GUI application."""
        try:
            self.root.mainloop()
        finally:
            if self.serial_thread:
                self.serial_thread.disconnect()


if __name__ == "__main__":
    app = EnhancedEncoderGUI()
    app.run()
