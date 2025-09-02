"""
Data visualization components for encoder GUI.
"""
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
from typing import List
from data_models import EncoderSample, DataBuffer


class EncoderPlot:
    """Real-time plot for encoder data visualization."""
    
    def __init__(self, parent_frame: tk.Frame):
        # Create matplotlib figure
        self.fig = Figure(figsize=(8, 4), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Encoder Position (pulses)")
        self.ax.grid(True, alpha=0.3)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Plot configuration
        self.max_points = 4000
        self.decimate_target = 1000
    
    def update_plot(self, buffer: DataBuffer):
        """Update the plot with new data from buffer."""
        samples = buffer.get_recent_samples(self.max_points)
        if not samples:
            return
        
        # Filter samples that have position data
        pos_samples = [s for s in samples if s.pos is not None]
        
        if not pos_samples:
            return
        
        # Decimate data if too many points
        if len(pos_samples) > self.decimate_target:
            step = len(pos_samples) // self.decimate_target
            pos_samples = pos_samples[::step]
        
        times = []
        positions = []
        
        # Extract times and positions
        for sample in pos_samples:
            times.append(sample.time_ms / 1000.0)  # Convert to seconds for plot
            try:
                position = int(sample.pos)
                positions.append(position)
            except (ValueError, TypeError):
                positions.append(0)  # Default on parse error
        
        if not times or not positions:
            return
            
        self.ax.clear()
        self.ax.plot(times, positions, 'b-', linewidth=1.0, alpha=0.8)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Encoder Position (pulses)")
        self.ax.grid(True, alpha=0.3)
        
        # Auto-scale with some padding
        if times and positions:
            self.ax.set_xlim(min(times), max(times))
            pos_range = max(positions) - min(positions)
            if pos_range > 0:
                padding = pos_range * 0.1
                self.ax.set_ylim(min(positions) - padding, max(positions) + padding)
        
        self.canvas.draw()


class DataTable:
    """Table widget for displaying encoder data."""
    
    def __init__(self, parent_frame: tk.Frame):
        # Create treeview for data display
        columns = ("Time (ms)", "Pos", "CPS", "RPM")
        self.tree = ttk.Treeview(parent_frame, columns=columns, show="headings", height=10)
        
        # Configure columns
        self.tree.heading("Time (ms)", text="Time (ms)")
        self.tree.heading("Pos", text="Pos")
        self.tree.heading("CPS", text="CPS")
        self.tree.heading("RPM", text="RPM")
        
        self.tree.column("Time (ms)", width=100, anchor="center")
        self.tree.column("Pos", width=80, anchor="center")
        self.tree.column("CPS", width=80, anchor="center")
        self.tree.column("RPM", width=80, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.max_rows = 100  # Back to normal since we're not duplicating rows
    
    def update_table(self, buffer: DataBuffer):
        """Update table with recent data from buffer."""
        recent_samples = buffer.get_recent_samples(self.max_rows)
        
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add new rows (most recent first)
        for sample in reversed(recent_samples):
            self.tree.insert("", 0, values=(
                f"{sample.time_ms:.1f}",
                sample.pos if sample.pos else "",
                sample.cps if sample.cps else "",
                sample.rpm if sample.rpm else ""
            ))
    
    def clear(self):
        """Clear all table data."""
        for item in self.tree.get_children():
            self.tree.delete(item)
