#!/usr/bin/env python3
"""
ESP32 Encoder Monitor GUI - Modular Version

A professional GUI application for monitoring ESP32 quadrature encoder
and load cell data with real-time plotting and data export capabilities.

This modular version splits the original monolithic code into focused
components for better maintainability and understanding.
"""

import threading
import time
import tkinter as tk
from typing import Optional

# Import our modular components
from config import *
from data_models import DataBuffer, Sample
from serial_handler import SerialManager, get_available_ports
from data_parser import DataParser
from gui_components import MainWindow, DialogHelper
from data_export import DataExporter


class EncoderApplication:
    """Main application class that coordinates all components."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        
        # Initialize state variables
        self.selected_port = tk.StringVar()
        self.connection_state = tk.BooleanVar(value=False)
        self.running = tk.BooleanVar(value=False)
        self.autoscroll = tk.BooleanVar(value=True)
        
        # Initialize components
        self.data_buffer = DataBuffer()
        self.serial_manager = SerialManager()
        self.data_parser = DataParser()
        self.main_window = MainWindow(root)
        
        # Thread synchronization
        self.data_mutex = threading.Lock()
        
        # Initialize UI and start periodic tasks
        self._setup_ui()
        self._start_periodic_tasks()
        
    def _setup_ui(self):
        """Initialize the user interface."""
        callbacks = {
            'port_var': self.selected_port,
            'autoscroll_var': self.autoscroll,
            'toggle_connect': self.toggle_connection,
            'toggle_run': self.toggle_running,
            'clear_data': self.clear_data,
            'export_excel': self.export_data,
            'send_tare': self.send_tare_command
        }
        
        self.main_window.build_ui(callbacks)
        
    def _start_periodic_tasks(self):
        """Start periodic background tasks."""
        self._schedule_port_refresh()
        self._schedule_data_refresh()
        
    # Connection Management
    def toggle_connection(self):
        """Toggle serial port connection."""
        if not self.connection_state.get():
            self._connect()
        else:
            self._disconnect()
            
    def _connect(self):
        """Establish serial connection."""
        port = self.selected_port.get()
        if not port:
            DialogHelper.show_warning("Port Selection", "Please select a COM port first")
            return
            
        try:
            self.serial_manager.start_connection(
                port, 
                DEFAULT_BAUD_RATE, 
                self._handle_serial_data
            )
            
            self.connection_state.set(True)
            self.main_window.update_connection_state(True, port)
            
        except Exception as e:
            DialogHelper.show_error("Connection Error", f"Failed to connect: {str(e)}")
            
    def _disconnect(self):
        """Close serial connection."""
        self.serial_manager.stop_connection()
        self.connection_state.set(False)
        self.running.set(False)
        self.main_window.update_connection_state(False)
        self.main_window.update_running_state(False)
        
    # Data Collection Management  
    def toggle_running(self):
        """Toggle data collection."""
        if not self.running.get():
            self._start_data_collection()
        else:
            self._stop_data_collection()
            
    def _start_data_collection(self):
        """Start collecting data."""
        # Auto-tare when starting
        self.send_tare_command(auto=True)
        
        self.running.set(True)
        self.main_window.update_running_state(True)
        
    def _stop_data_collection(self):
        """Stop collecting data."""
        self.running.set(False)
        self.main_window.update_running_state(False)
        
    # Serial Data Handling
    def _handle_serial_data(self, line: str):
        """Process incoming serial data."""
        if not self.running.get():
            return
            
        # Parse the incoming line
        pulse_count, force_value = self.data_parser.parse_line(line)
        
        # Update force display
        current_force = self.data_parser.get_current_force()
        self.main_window.update_force_display(current_force)
        
        # Add sample to buffer if we got pulse data
        if pulse_count is not None:
            with self.data_mutex:
                self.data_buffer.add(pulse_count, force_value)
                
    # Commands
    def send_tare_command(self, auto: bool = False):
        """Send TARE command to ESP32."""
        if not self.connection_state.get():
            return
            
        success = self.serial_manager.send_command("TARE")
        
        if success:
            if not auto:
                self.main_window.update_status("TARE command sent")
        else:
            if not auto:
                DialogHelper.show_error("Command Error", "Failed to send TARE command")
                
    # Data Management
    def clear_data(self):
        """Clear all collected data."""
        if not DialogHelper.ask_yes_no("Clear Data", "Clear all captured data?"):
            return
            
        with self.data_mutex:
            self.data_buffer.clear()
            
        self.main_window.clear_table()
        self.main_window.clear_plot()
        self.main_window.update_status("Data cleared")
        
    def export_data(self):
        """Export data to Excel file."""
        with self.data_mutex:
            samples = self.data_buffer.get_samples_copy()
            
        if not samples:
            DialogHelper.show_info("Export", "No data to export.")
            return
            
        filename = DialogHelper.ask_save_filename(
            DEFAULT_EXPORT_EXTENSION, 
            [("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )
        
        if not filename:
            return
            
        try:
            if filename.lower().endswith('.xlsx'):
                success = DataExporter.export_to_excel(samples, filename)
            else:
                success = DataExporter.export_to_csv(samples, filename)
                
            if success:
                summary = DataExporter.get_export_summary(samples)
                DialogHelper.show_info(
                    "Export Complete", 
                    f"Exported {summary['count']} samples to {filename}"
                )
            else:
                DialogHelper.show_error("Export Error", "Failed to export data")
                
        except Exception as e:
            DialogHelper.show_error("Export Error", f"Export failed: {str(e)}")
            
    # Periodic Tasks
    def _schedule_port_refresh(self):
        """Schedule periodic port list refresh."""
        self._refresh_port_list()
        self.root.after(PORT_REFRESH_INTERVAL_MS, self._schedule_port_refresh)
        
    def _refresh_port_list(self):
        """Refresh the list of available COM ports."""
        try:
            current_ports = get_available_ports()
            current_selection = self.selected_port.get()
            
            self.main_window.update_port_list(current_ports, current_selection)
            
            # Update selection if current port is no longer available
            if current_selection not in current_ports:
                new_selection = current_ports[0] if current_ports else ""
                self.selected_port.set(new_selection)
                
        except Exception:
            pass  # Ignore errors in background task
            
    def _schedule_data_refresh(self):
        """Schedule periodic UI data refresh."""
        self._update_display()
        self.root.after(UI_REFRESH_MS, self._schedule_data_refresh)
        
    def _update_display(self):
        """Update table and plot with new data."""
        with self.data_mutex:
            samples = self.data_buffer.get_samples_copy()
            
        if not samples:
            return
            
        # Update table with new rows
        self._update_table(samples)
        
        # Update plot
        self._update_plot(samples)
        
    def _update_table(self, samples: list[Sample]):
        """Update the data table with new samples."""
        # Get current number of rows in table
        current_rows = len(self.main_window.tree.get_children())
        new_samples = samples[current_rows:]
        
        # Add new rows
        last_item_id = None
        for sample in new_samples:
            force_str = f"{sample.force:.3f}" if sample.force is not None else ""
            row_data = (
                f"{sample.t * 1000:.1f}",  # Time in milliseconds
                sample.pulses,
                sample.delta,
                force_str
            )
            last_item_id = self.main_window.add_table_row(row_data)
            
        # Auto-scroll if enabled
        if self.autoscroll.get() and last_item_id:
            self.main_window.scroll_to_row(last_item_id)
            
    def _update_plot(self, samples: list[Sample]):
        """Update the plot with current data."""
        if not samples:
            return
            
        # Decimate data if too many points
        total_samples = len(samples)
        if total_samples > MAX_PLOT_POINTS * 2:
            step = max(1, total_samples // DECIMATE_TARGET)
            plot_samples = samples[::step]
        else:
            plot_samples = samples[-MAX_PLOT_POINTS:]
            
        if not plot_samples:
            return
            
        # Extract data for plotting
        times = [s.t for s in plot_samples]
        pulses = [s.pulses for s in plot_samples]
        
        # Update plot
        self.main_window.update_plot(times, pulses)
        
    # Application Lifecycle
    def on_closing(self):
        """Handle application closing."""
        self.serial_manager.stop_connection()
        self.root.destroy()


def main():
    """Main application entry point."""
    # Create and configure root window
    root = tk.Tk()
    root.geometry("1000x700")  # Set reasonable default size
    
    # Create application
    app = EncoderApplication(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the GUI event loop
    root.mainloop()


if __name__ == '__main__':
    main()
