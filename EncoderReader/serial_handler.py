"""
Serial communication handler for ESP32 encoder data.
"""
import threading
import time
import serial
import serial.tools.list_ports
from typing import Callable, Optional, List


class SerialThread(threading.Thread):
    """Thread for handling serial communication with ESP32."""
    
    def __init__(self, port: str, baudrate: int = 115200, 
                 line_callback: Optional[Callable[[str], None]] = None):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.line_callback = line_callback
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.stop_event = threading.Event()
    
    def connect(self) -> bool:
        """Establish serial connection."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1.0
            )
            return True
        except Exception as e:
            print(f"Serial connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection."""
        self.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None
    
    def start_reading(self):
        """Start the serial reading thread."""
        if not self.running:
            self.running = True
            self.stop_event.clear()
            self.start()
    
    def stop(self):
        """Stop the serial reading thread."""
        self.running = False
        self.stop_event.set()
        if self.is_alive():
            self.join(timeout=2.0)
    
    def run(self):
        """Main thread loop for reading serial data."""
        buffer = ""
        while self.running and not self.stop_event.is_set():
            if not self.ser or not self.ser.is_open:
                time.sleep(0.1)
                continue
            
            try:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer += chunk
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line and self.line_callback:
                            self.line_callback(line)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Serial read error: {e}")
                time.sleep(0.1)
    
    def send_command(self, command: str) -> bool:
        """Send a command to the ESP32."""
        if not self.ser or not self.ser.is_open:
            return False
        try:
            self.ser.write(f"{command}\n".encode())
            self.ser.flush()
            return True
        except Exception as e:
            print(f"Serial write error: {e}")
            return False


def get_available_ports() -> List[str]:
    """Get list of available serial ports."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


def find_esp32_port() -> Optional[str]:
    """Try to automatically detect ESP32 port."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Look for common ESP32 identifiers
        if any(keyword in port.description.lower() for keyword in 
               ['esp32', 'silicon labs', 'cp210', 'ch340', 'usb serial']):
            return port.device
    return None
