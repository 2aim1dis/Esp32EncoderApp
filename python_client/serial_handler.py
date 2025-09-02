"""
Serial communication handler for the Encoder GUI.
Manages connection to ESP32 and data parsing.
"""

import threading
import time
from typing import Optional, Callable
import serial
import serial.tools.list_ports


class SerialReader(threading.Thread):
    """Thread-safe serial port reader for ESP32 communication."""
    
    def __init__(self, port_getter: Callable[[], str], baud: int, 
                 line_callback: Callable[[str], None], stop_event: threading.Event):
        """
        Initialize the serial reader.
        
        Args:
            port_getter: Function that returns the current port name
            baud: Baud rate for serial communication
            line_callback: Function to call when a line is received
            stop_event: Event to signal thread shutdown
        """
        super().__init__(daemon=True)
        self.port_getter = port_getter
        self.baud = baud
        self.line_callback = line_callback
        self.stop_event = stop_event
        self.ser: Optional[serial.Serial] = None

    def run(self):
        """Main thread loop for reading serial data."""
        while not self.stop_event.is_set():
            port = self.port_getter()
            if not port:
                time.sleep(0.5)
                continue
                
            try:
                # Open serial connection
                self.ser = serial.Serial(port, self.baud, timeout=0.2)
                self.ser.reset_input_buffer()
                
                # Read lines until stopped
                while not self.stop_event.is_set():
                    line = self.ser.readline().decode(errors='ignore').strip()
                    if line:
                        self.line_callback(line)
                        
            except serial.SerialException:
                # Connection failed, retry after delay
                time.sleep(0.5)
            finally:
                # Clean up serial connection
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                    self.ser = None

    def send_command(self, command: str) -> bool:
        """
        Send a command to the ESP32.
        
        Args:
            command: Command string to send
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        if not self.ser or not self.ser.is_open:
            return False
            
        try:
            self.ser.write(f"{command}\n".encode())
            self.ser.flush()
            return True
        except Exception:
            return False


class SerialManager:
    """Manages serial port connections and commands."""
    
    def __init__(self):
        self.reader: Optional[SerialReader] = None
        self.stop_event = threading.Event()
        
    def start_connection(self, port: str, baud: int, line_callback: Callable[[str], None]):
        """Start serial connection with specified parameters."""
        self.stop_connection()
        
        self.stop_event.clear()
        self.reader = SerialReader(
            lambda: port, 
            baud, 
            line_callback, 
            self.stop_event
        )
        self.reader.start()
        
    def stop_connection(self):
        """Stop the current serial connection."""
        if self.reader:
            self.stop_event.set()
            self.reader = None
            
    def send_command(self, command: str) -> bool:
        """Send a command through the active connection."""
        if self.reader:
            return self.reader.send_command(command)
        return False
        
    def is_connected(self) -> bool:
        """Check if serial connection is active."""
        return self.reader is not None and not self.stop_event.is_set()


def get_available_ports() -> list[str]:
    """Get list of available COM ports."""
    return [port.device for port in serial.tools.list_ports.comports()]
