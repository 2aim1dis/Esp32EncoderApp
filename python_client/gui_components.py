"""
GUI components and widgets for the Encoder GUI application.
Handles the user interface layout and interactions.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from typing import Callable, Optional
from config import *


class MainWindow:
    """Main application window with all GUI components."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("ESP32 Encoder Monitor")
        
        # Initialize GUI components
        self.toolbar = None
        self.port_combo: Optional[ttk.Combobox] = None
        self.tree: Optional[ttk.Treeview] = None
        self.force_box_label: Optional[ttk.Label] = None
        self.status_label: Optional[ttk.Label] = None
        self.fig: Optional[Figure] = None
        self.ax = None
        self.line_plot = None
        self.canvas = None
        
        # Button references
        self.btn_connect: Optional[ttk.Button] = None
        self.btn_run: Optional[ttk.Button] = None
        self.btn_clear: Optional[ttk.Button] = None
        self.btn_export: Optional[ttk.Button] = None
        self.btn_tare: Optional[ttk.Button] = None
        
    def build_ui(self, callbacks: dict):
        """
        Build the complete user interface.
        
        Args:
            callbacks: Dictionary of callback functions for UI events
        """
        self._build_toolbar(callbacks)
        self._build_force_display()
        self._build_main_content(callbacks)
        self._build_status_bar()
        
    def _build_toolbar(self, callbacks: dict):
        """Build the top toolbar with controls."""
        self.toolbar = ttk.Frame(self.root, padding=4)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Port selection
        ttk.Label(self.toolbar, text="Port:").pack(side=tk.LEFT)
        self.port_combo = ttk.Combobox(self.toolbar, width=15, 
                                      textvariable=callbacks['port_var'], 
                                      state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=4)

        # Control buttons
        self.btn_connect = ttk.Button(self.toolbar, text="Connect", 
                                     command=callbacks['toggle_connect'])
        self.btn_connect.pack(side=tk.LEFT, padx=4)

        self.btn_run = ttk.Button(self.toolbar, text="Start", 
                                 command=callbacks['toggle_run'], state=tk.DISABLED)
        self.btn_run.pack(side=tk.LEFT, padx=4)

        self.btn_clear = ttk.Button(self.toolbar, text="Erase Data", 
                                   command=callbacks['clear_data'], state=tk.DISABLED)
        self.btn_clear.pack(side=tk.LEFT, padx=4)

        self.btn_export = ttk.Button(self.toolbar, text="Export Excel", 
                                    command=callbacks['export_excel'], state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=4)

        self.btn_tare = ttk.Button(self.toolbar, text="Set Zero", 
                                  command=callbacks['send_tare'], state=tk.DISABLED)
        self.btn_tare.pack(side=tk.LEFT, padx=4)

        # Auto scroll checkbox
        ttk.Checkbutton(self.toolbar, text="Auto Scroll", 
                       variable=callbacks['autoscroll_var']).pack(side=tk.LEFT, padx=(12,4))

    def _build_force_display(self):
        """Build the force display section."""
        force_box = ttk.LabelFrame(self.root, text="Current Force", padding=6)
        force_box.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(2,4))
        
        self.force_box_label = ttk.Label(force_box, text="0.000 kg", 
                                        font=("Segoe UI", FORCE_FONT_SIZE, "bold"))
        self.force_box_label.pack(side=tk.LEFT, padx=4)

    def _build_main_content(self, callbacks: dict):
        """Build the main content area with table and plot."""
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # Data table
        self._build_data_table(main)
        
        # Plot
        self._build_plot(main)

    def _build_data_table(self, parent: ttk.Frame):
        """Build the data table component."""
        table_frame = ttk.Frame(parent)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Table columns
        columns = ("time_ms", "pulses", "delta", "force")
        self.tree = ttk.Treeview(table_frame, columns=columns, 
                                show="headings", height=TABLE_HEIGHT)
        
        # Configure column headers and widths
        column_configs = [
            ("time_ms", "Time (ms)", 90),
            ("pulses", "Pulses", 80),
            ("delta", "Delta", 70),
            ("force", "Force (kg)", 90)
        ]
        
        for col_id, title, width in column_configs:
            self.tree.heading(col_id, text=title)
            self.tree.column(col_id, width=width, anchor=tk.E)
            
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for table
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_plot(self, parent: ttk.Frame):
        """Build the matplotlib plot component."""
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure
        self.fig = Figure(figsize=PLOT_FIGURE_SIZE, dpi=PLOT_DPI)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Pulses")
        self.line_plot, = self.ax.plot([], [], lw=1.2)
        
        # Embed plot in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_status_bar(self):
        """Build the bottom status bar."""
        status = ttk.Frame(self.root, padding=4)
        status.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(status, text="Idle")
        self.status_label.pack(side=tk.LEFT)

    # UI Update Methods
    def update_port_list(self, ports: list[str], current_port: str):
        """Update the COM port dropdown list."""
        if self.port_combo:
            self.port_combo['values'] = ports

    def update_connection_state(self, connected: bool, port: str = ""):
        """Update UI based on connection state."""
        if connected:
            self.btn_connect.config(text="Disconnect")
            self.btn_run.config(state=tk.NORMAL)
            self.btn_tare.config(state=tk.NORMAL)
            self.status_label.config(text=f"Connected: {port}")
        else:
            self.btn_connect.config(text="Connect")
            self.btn_run.config(text="Start", state=tk.DISABLED)
            self.btn_clear.config(state=tk.DISABLED)
            self.btn_export.config(state=tk.DISABLED)
            self.btn_tare.config(state=tk.DISABLED)
            self.status_label.config(text="Disconnected")

    def update_running_state(self, running: bool):
        """Update UI based on running/stopped state."""
        if running:
            self.btn_run.config(text="Stop")
            self.btn_clear.config(state=tk.NORMAL)
            self.btn_export.config(state=tk.NORMAL)
            self.status_label.config(text="Running")
        else:
            self.btn_run.config(text="Start")
            self.status_label.config(text="Paused")

    def update_force_display(self, force_kg: float):
        """Update the force display."""
        if self.force_box_label:
            self.force_box_label.config(text=f"{force_kg:.3f} kg")

    def update_status(self, status_text: str):
        """Update the status bar text."""
        if self.status_label:
            self.status_label.config(text=status_text)

    def add_table_row(self, sample_data: tuple) -> str:
        """Add a row to the data table and return the item ID."""
        return self.tree.insert("", tk.END, values=sample_data)

    def clear_table(self):
        """Clear all rows from the data table."""
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

    def scroll_to_row(self, item_id: str):
        """Scroll table to show specified row."""
        self.tree.see(item_id)

    def update_plot(self, times: list, values: list):
        """Update the plot with new data."""
        if not times or not self.line_plot:
            return
            
        self.line_plot.set_data(times, values)
        
        # Update axis limits
        self.ax.set_xlim(times[0], times[-1])
        
        ymin, ymax = min(values), max(values)
        if ymin == ymax:
            ymax = ymin + 1
        self.ax.set_ylim(ymin, ymax)
        
        self.canvas.draw_idle()

    def clear_plot(self):
        """Clear the plot and reset axes."""
        self.ax.cla()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Pulses")
        self.line_plot, = self.ax.plot([], [], lw=1.2)
        self.canvas.draw_idle()


class DialogHelper:
    """Helper class for showing dialogs and file operations."""
    
    @staticmethod
    def show_warning(title: str, message: str):
        """Show a warning dialog."""
        messagebox.showwarning(title, message)
        
    @staticmethod
    def show_error(title: str, message: str):
        """Show an error dialog."""
        messagebox.showerror(title, message)
        
    @staticmethod
    def show_info(title: str, message: str):
        """Show an information dialog."""
        messagebox.showinfo(title, message)
        
    @staticmethod
    def ask_yes_no(title: str, message: str) -> bool:
        """Show a yes/no confirmation dialog."""
        return messagebox.askyesno(title, message)
        
    @staticmethod
    def ask_save_filename(default_ext: str = ".xlsx", 
                         filetypes: list = None) -> str:
        """Show a file save dialog."""
        if filetypes is None:
            filetypes = [("Excel", "*.xlsx")]
        return filedialog.asksaveasfilename(
            defaultextension=default_ext, 
            filetypes=filetypes
        )
