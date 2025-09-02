# Μάθημα: Κατανοώντας το encoder_gui.py - Main Application Architecture

## Περιεχόμενα
1. [Main Application Architecture](#1-main-application-architecture)
2. [EncoderGUI Class Design](#2-encodergui-class-design)
3. [Application State Management](#3-application-state-management)
4. [Serial Communication Integration](#4-serial-communication-integration)
5. [Real-time Data Processing](#5-real-time-data-processing)
6. [User Interface Coordination](#6-user-interface-coordination)
7. [Event Loop Integration](#7-event-loop-integration)
8. [Professional Application Patterns](#8-professional-application-patterns)

---

## 1. Main Application Architecture

### Monolithic vs Modular Design

```python
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
```

**Application Architecture Overview:**
```
┌─────────────────────────────────────────────────────────────┐
│                ENCODER GUI APPLICATION                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   ENCODERGUI    │    │      SUBSYSTEM INTEGRATION      │  │
│  │  (Main Class)   │◄──►│                                 │  │
│  │                 │    │ • Serial communication         │  │
│  │ • State mgmt    │    │ • Data models & buffer         │  │
│  │ • Event coord   │    │ • GUI components                │  │
│  │ • Data flow     │    │ • File I/O operations           │  │
│  │ • Lifecycle     │    │ • Threading coordination        │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
│           │                           ▲                      │
│           ▼                           │                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              RUNTIME COORDINATION                       │  │
│  │                                                         │  │
│  │ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │  │
│  │ │ GUI THREAD   │ │SERIAL THREAD │ │ TIMER CALLBACKS  │  │  │
│  │ │              │ │              │ │                  │  │  │
│  │ │• User events │ │• Port scan   │ │• UI updates      │  │  │
│  │ │• Display     │ │• Data recv   │ │• Port refresh    │  │  │
│  │ │• File ops    │ │• Auto recon  │ │• Plot updates    │  │  │
│  │ └──────────────┘ └──────────────┘ └──────────────────┘  │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Monolithic Design Analysis:**
```python
# Current approach: All functionality in EncoderGUI class
class EncoderGUI:
    def __init__(self):
        # State management
        self.selected_port = tk.StringVar()
        self.connection_state = tk.BooleanVar()
        
        # Data management  
        self.buffer = DataBuffer()
        
        # Threading
        self.serial_thread = None
        
        # UI components (built inline)
        self._build_ui()

# Benefits of monolithic approach:
# ✅ Simple - Everything in one class
# ✅ Fast development - No interface design needed
# ✅ Easy to understand - Linear code flow
# ✅ Good for small applications

# Drawbacks:
# ❌ Hard to test - Tightly coupled components
# ❌ Hard to reuse - GUI and logic mixed
# ❌ Hard to maintain - Large class with many responsibilities
```

---

## 2. EncoderGUI Class Design

### Multi-Responsibility Class Architecture

```python
class EncoderGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("ESP32 Encoder Monitor")

        # State Variables (tkinter variables for UI binding)
        self.selected_port = tk.StringVar()
        self.connection_state = tk.BooleanVar(value=False)
        self.running = tk.BooleanVar(value=False)
        self.autoscroll = tk.BooleanVar(value=True)

        # Data Management
        self.buffer = DataBuffer()
        self.current_force = 0.0
        self.force_timestamp = 0.0

        # Threading Infrastructure
        self.serial_thread: Optional[SerialReader] = None
        self.serial_stop = threading.Event()
        self.mutex = threading.Lock()

        # Initialize subsystems
        self._build_ui()
        self._schedule_port_refresh()
        self._schedule_table_refresh()
```

**Class Responsibility Analysis:**

### 2.1 State Management Responsibilities
```python
# State variables serve multiple purposes:

# 1. UI Binding (tkinter variables automatically update widgets)
self.selected_port = tk.StringVar()
# → Combobox displays and updates this value automatically

# 2. Thread Communication (shared state between threads)
self.connection_state = tk.BooleanVar(value=False)
# → Serial thread can check, UI thread can update

# 3. Application Logic (business rule enforcement)
self.running = tk.BooleanVar(value=False)
# → Controls whether data processing occurs

# Professional state management pattern:
class StateManager:
    """Separate state management for better organization."""
    
    def __init__(self):
        # Connection state
        self.selected_port = tk.StringVar()
        self.connection_state = tk.BooleanVar(value=False)
        self.running = tk.BooleanVar(value=False)
        
        # UI preferences
        self.autoscroll = tk.BooleanVar(value=True)
        
        # Data state
        self.current_force = 0.0
        self.force_timestamp = 0.0
    
    def get_state_dict(self):
        """Get all state variables for UI binding."""
        return {
            'port_var': self.selected_port,
            'connection_var': self.connection_state,
            'running_var': self.running,
            'autoscroll_var': self.autoscroll
        }

# Usage in cleaner architecture:
self.state = StateManager()
self.ui.build_ui(self.state.get_state_dict())
```

### 2.2 Data Management Integration

```python
# Data flow coordination:
self.buffer = DataBuffer()          # Core data storage
self.current_force = 0.0           # Latest force reading  
self.force_timestamp = 0.0         # Force data freshness

# Data processing pipeline:
def _on_serial_line(self, line: str):
    """Process incoming serial data."""
    if not self.running.get():
        return  # Ignore data when not running
        
    # Parse different line types
    if line.startswith("Pos="):
        self._process_encoder_line(line)
    elif line.lower().startswith(("force=", "weight=", "load=")):
        self._process_force_line(line)

def _process_encoder_line(self, line: str):
    """Process encoder position data."""
    try:
        pulses = self._extract_pulses(line)
        force = self._extract_embedded_force(line) or self.current_force
        
        with self.mutex:  # Thread-safe data access
            self.buffer.add(pulses, force)
            
    except Exception as e:
        print(f"Error processing encoder line: {e}")

# Thread safety pattern:
with self.mutex:
    # Critical section - only one thread can access buffer
    self.buffer.add(pulses, force)
    data_copy = list(self.buffer.samples)  # Copy for UI thread
```

---

## 3. Application State Management

### State Transition Coordination

```python
# State machine for connection management:
def toggle_connect(self):
    """Handle connection state transitions."""
    
    if not self.connection_state.get():
        # State: DISCONNECTED → CONNECTING
        port = self.selected_port.get()
        if not port:
            messagebox.showwarning("Port", "Select a COM port first")
            return
            
        # Start serial communication
        self.serial_stop.clear()
        self.serial_thread = SerialReader(
            lambda: self.selected_port.get(), 
            115200, 
            self._on_serial_line, 
            self.serial_stop
        )
        self.serial_thread.start()
        
        # Update state
        self.connection_state.set(True)
        self._update_connection_ui(True, port)
        
    else:
        # State: CONNECTED → DISCONNECTING  
        self.serial_stop.set()
        self.connection_state.set(False)
        self.running.set(False)  # Stop data acquisition
        self._update_connection_ui(False)

def _update_connection_ui(self, connected: bool, port: str = ""):
    """Update UI elements for connection state."""
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
```

**State Transition Diagram:**
```
                 ┌─────────────────┐
                 │  DISCONNECTED   │
                 │                 │
                 │ • Port selection│
                 │ • Connect button│
                 └────────┬────────┘
                          │ Connect clicked
                          ▼
                 ┌─────────────────┐
                 │   CONNECTING    │
                 │                 │
                 │ • Serial thread │
                 │   starting      │
                 └────────┬────────┘
                          │ Connection established
                          ▼
  ┌─────────────────┬─────────────────┐
  │                 │   CONNECTED     │
  │   Disconnect    │                 │◄──┐
  │   clicked       │ • Start/Stop    │   │ Stop clicked
  │                 │ • TARE commands │   │
  │                 │ • Data export   │   │
  └─────────────────┴─────────┬───────────┘
                               │ Start clicked
                               ▼
                  ┌─────────────────┐
                  │ CONNECTED +     │
                  │   RUNNING       │
                  │                 │
                  │ • Data capture  │
                  │ • Real-time UI  │
                  │ • Export ready  │
                  └─────────────────┘
```

### Data Acquisition State Management

```python
def toggle_run(self):
    """Manage data acquisition state transitions."""
    
    if not self.running.get():
        # IDLE → RUNNING
        self.send_tare(auto=True)  # Reset encoder position
        self.running.set(True)
        self._update_running_ui(True)
        
    else:
        # RUNNING → IDLE  
        self.running.set(False)
        self._update_running_ui(False)

def _update_running_ui(self, running: bool):
    """Update UI for data acquisition state."""
    if running:
        self.btn_run.config(text="Stop")
        self.btn_clear.config(state=tk.NORMAL)
        self.btn_export.config(state=tk.NORMAL)
        self.status_label.config(text="Running")
    else:
        self.btn_run.config(text="Start")
        self.status_label.config(text="Paused")

# Professional state validation:
def _validate_state_transition(self, from_state: str, to_state: str) -> bool:
    """Validate state transition is allowed."""
    
    valid_transitions = {
        'DISCONNECTED': ['CONNECTING'],
        'CONNECTING': ['CONNECTED', 'DISCONNECTED'],  # Success or failure
        'CONNECTED': ['RUNNING', 'DISCONNECTED'],
        'RUNNING': ['CONNECTED', 'DISCONNECTED']
    }
    
    return to_state in valid_transitions.get(from_state, [])
```

---

## 4. Serial Communication Integration

### Threading Integration Strategy

```python
# Serial thread management:
def _start_serial_thread(self, port: str):
    """Start serial communication thread."""
    
    self.serial_stop.clear()
    self.serial_thread = SerialReader(
        port_getter=lambda: self.selected_port.get(),  # Dynamic port access
        baud=115200,                                   # Standard ESP32 rate
        line_callback=self._on_serial_line,            # Data processing
        stop_event=self.serial_stop                    # Shutdown coordination
    )
    self.serial_thread.start()

def _on_serial_line(self, line: str):
    """Process incoming serial data (called from serial thread)."""
    
    # Thread safety check
    if not self.running.get():
        return
    
    # Parse line format
    line = line.strip().lower()
    
    # Handle force-only lines
    if self._is_force_only_line(line):
        force = self._extract_force(line)
        if force is not None:
            with self.mutex:
                self.current_force = force
                self.force_timestamp = time.time()
        
        # Update UI (thread-safe tkinter call)
        self.root.after_idle(self._update_force_display, force)
        return
    
    # Handle encoder position lines
    if line.startswith("pos="):
        self._process_position_line(line)

def _update_force_display(self, force: float):
    """Update force display (called from main thread)."""
    self.force_box_label.config(text=f"{force:.3f} kg")
```

**Thread Communication Patterns:**
```python
# Pattern 1: Thread-safe data updates
def _on_serial_line(self, line: str):
    # Running in serial thread
    pulses = extract_pulses(line)
    
    with self.mutex:  # Protect shared data
        self.buffer.add(pulses, self.current_force)
    
    # Schedule UI update on main thread
    self.root.after_idle(self._update_displays)

# Pattern 2: Safe UI updates from background threads
def _update_displays(self):
    # Running in main thread (safe for tkinter)
    with self.mutex:
        data = list(self.buffer.samples)  # Copy data
    
    self._update_table(data)
    self._update_plot(data)

# Pattern 3: Command sending to serial thread
def send_tare(self, auto: bool = False):
    """Send TARE command to ESP32."""
    
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
```

---

## 5. Real-time Data Processing

### High-Frequency Data Handling

```python
# Real-time data processing pipeline:

def _update_table_and_plot(self):
    """Update UI with latest data (called every UI_REFRESH_MS)."""
    
    # Thread-safe data access
    with self.mutex:
        data = list(self.buffer.samples)  # Copy current data
    
    if not data:
        return
    
    # Update table with new rows only
    existing_rows = len(self.tree.get_children())
    new_items = data[existing_rows:]
    
    last_id = None
    if new_items:
        for sample in new_items:
            force_str = f"{sample.force:.3f}" if sample.force is not None else ""
            row_data = (f"{sample.t*1000:.1f}", sample.pulses, sample.delta, force_str)
            last_id = self.tree.insert("", tk.END, values=row_data)
        
        # Auto-scroll to latest data
        if self.autoscroll.get() and last_id is not None:
            self.tree.see(last_id)
    
    # Update plot with decimated data for performance
    self._update_plot_data(data)

def _update_plot_data(self, data: List[Sample]):
    """Update plot with performance optimization."""
    
    total_samples = len(data)
    
    # Decimate data if too many points
    if total_samples > MAX_PLOT_POINTS * 2:
        step = max(1, total_samples // DECIMATE_TARGET)
        plot_data = data[::step]  # Every Nth sample
    else:
        plot_data = data[-MAX_PLOT_POINTS:]  # Last N samples
    
    # Extract plot coordinates
    times = [s.t for s in plot_data]
    pulses = [s.pulses for s in plot_data]
    
    if not times:
        return
    
    # Update plot line (efficient matplotlib update)
    self.line_plot.set_data(times, pulses)
    
    # Adjust axes
    self.ax.set_xlim(times[0], times[-1])
    
    y_min, y_max = min(pulses), max(pulses)
    if y_min == y_max:
        y_max = y_min + 1  # Prevent zero-height plot
    self.ax.set_ylim(y_min, y_max)
    
    # Efficient redraw
    self.canvas.draw_idle()
```

**Performance Optimization Strategy:**
```python
# Data decimation for plot performance:

def calculate_decimation_strategy(total_samples: int) -> dict:
    """Determine optimal data decimation approach."""
    
    if total_samples <= MAX_PLOT_POINTS:
        return {
            'method': 'none',
            'samples_used': total_samples,
            'performance': 'optimal'
        }
    
    elif total_samples <= MAX_PLOT_POINTS * 2:
        return {
            'method': 'recent_window',
            'samples_used': MAX_PLOT_POINTS,
            'samples_shown': total_samples - MAX_PLOT_POINTS,
            'performance': 'good'
        }
    
    else:
        step = max(1, total_samples // DECIMATE_TARGET)
        return {
            'method': 'nth_sample',
            'step_size': step,
            'samples_used': total_samples // step,
            'data_loss': f"{((step-1)/step)*100:.1f}%",
            'performance': 'acceptable'
        }

# Memory usage calculation:
def estimate_memory_usage(sample_count: int) -> dict:
    """Estimate memory usage for given sample count."""
    
    bytes_per_sample = 64  # Conservative estimate
    ui_row_overhead = 100   # TreeView row memory
    plot_point_overhead = 32  # Matplotlib point memory
    
    return {
        'data_memory_mb': (sample_count * bytes_per_sample) / 1024 / 1024,
        'ui_memory_mb': (sample_count * ui_row_overhead) / 1024 / 1024,
        'plot_memory_mb': (sample_count * plot_point_overhead) / 1024 / 1024,
        'total_estimated_mb': (sample_count * (bytes_per_sample + ui_row_overhead + plot_point_overhead)) / 1024 / 1024
    }

# Usage for performance monitoring:
if len(self.buffer.samples) % 1000 == 0:  # Check every 1000 samples
    usage = estimate_memory_usage(len(self.buffer.samples))
    if usage['total_estimated_mb'] > 100:  # Warning at 100MB
        print(f"Memory warning: {usage['total_estimated_mb']:.1f}MB estimated usage")
```

---

## 6. User Interface Coordination

### Event-Driven UI Updates

```python
# UI update scheduling system:
def __init__(self, root: tk.Tk):
    # ... initialization ...
    
    # Schedule periodic updates
    self._schedule_port_refresh()    # Every 2 seconds
    self._schedule_table_refresh()   # Every UI_REFRESH_MS

def _schedule_port_refresh(self):
    """Periodically refresh available COM ports."""
    self._refresh_ports()
    self.root.after(2000, self._schedule_port_refresh)  # 2 second interval

def _schedule_table_refresh(self):
    """Periodically update table and plot."""
    self._update_table_and_plot()
    self.root.after(UI_REFRESH_MS, self._schedule_table_refresh)  # 100ms interval

def _refresh_ports(self):
    """Update COM port list if changed."""
    current_ports = [p.device for p in serial.tools.list_ports.comports()]
    existing_ports = set(self.port_combo['values']) if self.port_combo['values'] else set()
    
    if set(current_ports) != existing_ports:
        # Port list changed
        self.port_combo['values'] = current_ports
        
        # Handle selected port removal
        if self.selected_port.get() not in current_ports:
            self.selected_port.set(current_ports[0] if current_ports else "")
```

**UI Responsiveness Strategy:**
```python
# Prevent UI freezing during long operations:

def export_excel(self):
    """Export data with progress indication."""
    
    if not self.buffer.samples:
        messagebox.showinfo("Export", "No data to export.")
        return
    
    # Get filename from user
    filepath = filedialog.asksaveasfilename(
        defaultextension=".xlsx", 
        filetypes=[("Excel","*.xlsx")]
    )
    
    if not filepath:
        return
    
    # Show progress indication
    self.status_label.config(text="Exporting...")
    self.btn_export.config(state=tk.DISABLED)
    
    # Schedule export on next event loop cycle (allows UI update)
    self.root.after(10, self._perform_export, filepath)

def _perform_export(self, filepath: str):
    """Perform actual export operation."""
    
    try:
        # Thread-safe data copy
        with self.mutex:
            export_data = list(self.buffer.samples)
        
        # Convert to export format
        rows = []
        for sample in export_data:
            row = {
                "time_s": sample.t,
                "pulses": sample.pulses,
                "delta": sample.delta,
                "force_kg": sample.force if sample.force is not None else ""
            }
            rows.append(row)
        
        # Export to Excel
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        
        # Success feedback
        messagebox.showinfo("Export", f"Exported {len(df)} rows to {filepath}")
        
    except Exception as e:
        messagebox.showerror("Export", f"Failed: {e}")
        
    finally:
        # Restore UI state
        self.status_label.config(text="Ready")
        self.btn_export.config(state=tk.NORMAL)
```

---

## 7. Event Loop Integration

### tkinter Event Loop Management

```python
# Application lifecycle management:

def on_close(self):
    """Handle application shutdown gracefully."""
    
    # Stop serial communication
    self.serial_stop.set()
    
    # Wait for threads to finish (with timeout)
    if self.serial_thread and self.serial_thread.is_alive():
        self.serial_thread.join(timeout=1.0)
    
    # Destroy main window
    self.root.destroy()

def main():
    """Application entry point."""
    root = tk.Tk()
    gui = EncoderGUI(root)
    
    # Set up clean shutdown
    root.protocol("WM_DELETE_WINDOW", gui.on_close)
    
    # Start event loop
    root.mainloop()

if __name__ == '__main__':
    main()
```

**Event Loop Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                  TKINTER EVENT LOOP                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                 EVENT QUEUE                             │ │
│  │                                                         │ │
│  │ • User clicks (button, menu)                           │ │
│  │ • Timer events (after, after_idle)                     │ │
│  │ • System events (window close, resize)                 │ │
│  │ • Variable changes (StringVar, BooleanVar)             │ │
│  └─────────────────┬───────────────────────────────────────┘ │
│                    │                                         │
│                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │               EVENT DISPATCHER                          │ │
│  │                                                         │ │
│  │ • Route events to callbacks                             │ │
│  │ • Maintain widget state                                 │ │
│  │ • Handle event priorities                               │ │
│  └─────────────────┬───────────────────────────────────────┘ │
│                    │                                         │
│                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │             APPLICATION HANDLERS                        │ │
│  │                                                         │ │
│  │ • toggle_connect()  → Serial management                 │ │
│  │ • toggle_run()      → Data acquisition                  │ │
│  │ • export_excel()    → File operations                   │ │
│  │ • _update_table()   → UI updates                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Timer-Based Operations

```python
# Professional timer management:

class TimerManager:
    """Manages application timers for coordinated updates."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.active_timers = {}
        
    def start_timer(self, name: str, callback: callable, interval_ms: int):
        """Start a named timer."""
        
        def timer_callback():
            try:
                callback()
            except Exception as e:
                print(f"Timer {name} error: {e}")
            finally:
                # Reschedule timer
                if name in self.active_timers:
                    timer_id = self.root.after(interval_ms, timer_callback)
                    self.active_timers[name] = timer_id
        
        # Start initial timer
        timer_id = self.root.after(interval_ms, timer_callback)
        self.active_timers[name] = timer_id
    
    def stop_timer(self, name: str):
        """Stop a named timer."""
        if name in self.active_timers:
            self.root.after_cancel(self.active_timers[name])
            del self.active_timers[name]
    
    def stop_all_timers(self):
        """Stop all active timers."""
        for timer_id in self.active_timers.values():
            self.root.after_cancel(timer_id)
        self.active_timers.clear()

# Usage in EncoderGUI:
def __init__(self, root):
    # ... initialization ...
    
    self.timers = TimerManager(root)
    
    # Start application timers
    self.timers.start_timer("port_refresh", self._refresh_ports, 2000)
    self.timers.start_timer("ui_update", self._update_table_and_plot, UI_REFRESH_MS)

def on_close(self):
    """Clean shutdown with timer management."""
    self.timers.stop_all_timers()
    self.serial_stop.set()
    self.root.destroy()
```

---

## 8. Professional Application Patterns

### Error Recovery and Resilience

```python
class ResilientEncoderGUI(EncoderGUI):
    """Enhanced GUI with error recovery capabilities."""
    
    def __init__(self, root: tk.Tk):
        super().__init__(root)
        
        # Error tracking
        self.error_count = 0
        self.last_error_time = 0
        self.max_errors_per_minute = 10
        
        # Recovery state
        self.last_known_good_state = None
        
    def safe_execute(self, operation: callable, operation_name: str, *args, **kwargs):
        """Execute operation with error recovery."""
        
        try:
            result = operation(*args, **kwargs)
            self.error_count = max(0, self.error_count - 1)  # Decrease error count on success
            return result
            
        except Exception as e:
            self._handle_operation_error(e, operation_name)
            return None
    
    def _handle_operation_error(self, error: Exception, operation_name: str):
        """Handle operation errors with recovery logic."""
        
        current_time = time.time()
        
        # Rate limiting for error messages
        if current_time - self.last_error_time > 1.0:  # Max 1 error message per second
            print(f"Error in {operation_name}: {error}")
            self.status_label.config(text=f"Error: {operation_name}")
            self.last_error_time = current_time
        
        self.error_count += 1
        
        # Recovery strategies
        if self.error_count > self.max_errors_per_minute:
            self._initiate_recovery_mode()
    
    def _initiate_recovery_mode(self):
        """Enter recovery mode when too many errors occur."""
        
        print("Entering recovery mode due to excessive errors")
        
        # Stop current operations
        if self.running.get():
            self.running.set(False)
        
        if self.connection_state.get():
            self.serial_stop.set()
            self.connection_state.set(False)
        
        # Reset UI state
        self._update_connection_ui(False)
        self._update_running_ui(False)
        
        # Show recovery dialog
        result = messagebox.askyesno(
            "Recovery Mode",
            "Application encountered multiple errors. Reset to defaults?"
        )
        
        if result:
            self._reset_to_defaults()
    
    def _reset_to_defaults(self):
        """Reset application to default state."""
        
        # Clear data
        with self.mutex:
            self.buffer.clear()
        
        # Clear UI
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Reset plot
        self.ax.clear()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Pulses")
        self.line_plot, = self.ax.plot([], [], lw=1.2)
        self.canvas.draw()
        
        # Reset error tracking
        self.error_count = 0
        self.status_label.config(text="Reset to defaults")

# Usage pattern:
def toggle_connect(self):
    """Connection management with error recovery."""
    return self.safe_execute(
        self._toggle_connect_implementation,
        "connection_management"
    )
```

### Configuration Management

```python
class ConfigurableEncoderGUI(EncoderGUI):
    """GUI with external configuration support."""
    
    def __init__(self, root: tk.Tk, config_file: str = "encoder_config.json"):
        self.config_file = config_file
        self.config = self._load_configuration()
        
        super().__init__(root)
        self._apply_configuration()
    
    def _load_configuration(self) -> dict:
        """Load configuration from file."""
        
        default_config = {
            "ui": {
                "refresh_ms": 100,
                "max_plot_points": 4000,
                "table_height": 25,
                "auto_scroll": True
            },
            "serial": {
                "baud_rate": 115200,
                "timeout": 0.2,
                "auto_reconnect": True
            },
            "export": {
                "default_format": "xlsx",
                "precision": 3,
                "include_metadata": True
            },
            "performance": {
                "decimation_threshold": 8000,
                "memory_limit_mb": 100
            }
        }
        
        try:
            with open(self.config_file, 'r') as f:
                user_config = json.load(f)
                # Merge with defaults
                return {**default_config, **user_config}
        except FileNotFoundError:
            return default_config
        except json.JSONDecodeError as e:
            print(f"Config file error: {e}, using defaults")
            return default_config
    
    def _apply_configuration(self):
        """Apply configuration to application."""
        
        # Update UI refresh rate
        self.timers.stop_timer("ui_update")
        self.timers.start_timer(
            "ui_update", 
            self._update_table_and_plot, 
            self.config["ui"]["refresh_ms"]
        )
        
        # Update autoscroll default
        self.autoscroll.set(self.config["ui"]["auto_scroll"])
        
        # Apply performance settings
        global MAX_PLOT_POINTS, DECIMATE_TARGET
        MAX_PLOT_POINTS = self.config["ui"]["max_plot_points"]
        DECIMATE_TARGET = self.config["performance"]["decimation_threshold"]
    
    def save_configuration(self):
        """Save current configuration to file."""
        
        config = {
            "ui": {
                "refresh_ms": UI_REFRESH_MS,
                "max_plot_points": MAX_PLOT_POINTS,
                "auto_scroll": self.autoscroll.get()
            },
            # ... other sections
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save configuration: {e}")

# Advanced: Plugin architecture
class PluginManager:
    """Manages application plugins."""
    
    def __init__(self, gui: EncoderGUI):
        self.gui = gui
        self.plugins = {}
    
    def load_plugin(self, plugin_name: str, plugin_module):
        """Load and initialize a plugin."""
        
        try:
            plugin_instance = plugin_module.Plugin(self.gui)
            plugin_instance.initialize()
            self.plugins[plugin_name] = plugin_instance
            return True
        except Exception as e:
            print(f"Failed to load plugin {plugin_name}: {e}")
            return False
    
    def execute_plugin_hook(self, hook_name: str, *args, **kwargs):
        """Execute plugin hooks."""
        
        for plugin in self.plugins.values():
            if hasattr(plugin, hook_name):
                try:
                    getattr(plugin, hook_name)(*args, **kwargs)
                except Exception as e:
                    print(f"Plugin hook {hook_name} error: {e}")
```

---

## Συμπέρασμα: Professional Application Architecture

Το **encoder_gui.py** module αποδεικνύει τις αρχές **professional desktop application development**:

### 🎯 **Application Architecture Mastery**
- **Central coordination** - Single class που orchestrates όλα τα subsystems
- **State management** - Professional handling των application states
- **Threading integration** - Safe coordination μεταξύ GUI και background threads
- **Event-driven design** - Responsive user interface με real-time updates

### ⚡ **Real-time Performance**
- **High-frequency data** - Efficient handling των 100Hz encoder streams
- **Memory management** - Smart decimation για plot performance
- **UI responsiveness** - Non-blocking operations για smooth user experience
- **Performance monitoring** - Built-in metrics για system optimization

### 📊 **Data Integration Excellence**
- **Multi-source data** - Coordinated encoder και force measurements
- **Thread-safe access** - Proper synchronization για shared data structures
- **Export capabilities** - Professional data output σε standard formats
- **Real-time visualization** - Live plotting με automatic scaling

### 🛡️ **Production Reliability**
- **Error recovery** - Sophisticated handling των communication failures
- **Graceful shutdown** - Clean resource cleanup και thread termination
- **Configuration management** - Flexible application customization
- **Plugin architecture** - Extensible design για future enhancements

**Το encoder_gui.py είναι ένα excellent example του "professional desktop application" - demonstrates advanced GUI programming techniques, real-time data processing, και production-quality error handling που meet industrial standards για measurement και control systems.** 🎉

**Key Insight:** Great application architecture balances simplicity με sophistication, creating systems που are both powerful και maintainable! 🚀
