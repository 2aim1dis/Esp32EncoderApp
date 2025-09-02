"""
Data parsing utilities for ESP32 encoder output.
Handles parsing of position, force, and other sensor data.
"""

import time
from typing import Optional, Tuple
from data_models import Sample


class DataParser:
    """Parses incoming serial data from ESP32."""
    
    def __init__(self):
        self.current_force = 0.0
        self.force_timestamp = 0.0
        
    def parse_line(self, line: str) -> Tuple[Optional[int], Optional[float]]:
        """
        Parse a line of data from ESP32.
        
        Args:
            line: Raw line from serial port
            
        Returns:
            Tuple of (pulse_count, force_value) or (None, None) if parse failed
        """
        line = line.strip()
        low = line.lower()
        
        # Handle force-only lines
        if self._is_force_only_line(low):
            force = self._extract_force_value(line)
            if force is not None:
                self.current_force = force
                self.force_timestamp = time.time()
            return None, force
            
        # Handle encoder position lines
        if line.startswith("Pos="):
            pulse_count = self._extract_pulse_count(line)
            force = self._extract_force_from_pos_line(line)
            
            if force is not None:
                self.current_force = force
                self.force_timestamp = time.time()
            else:
                # Use current force value if no force in this line
                force = self.current_force
                
            return pulse_count, force
            
        return None, None
        
    def _is_force_only_line(self, line_lower: str) -> bool:
        """Check if line contains only force data."""
        force_indicators = ["force=", "weight=", "load="]
        return (any(line_lower.startswith(indicator) for indicator in force_indicators) 
                and not line_lower.startswith("pos="))
                
    def _extract_force_value(self, line: str) -> Optional[float]:
        """Extract force value from a line."""
        try:
            # Split on '=' and get the value part
            parts = line.split('=', 1)
            if len(parts) < 2:
                return None
                
            value_str = parts[1].strip()
            
            # Remove 'kg' suffix if present
            if value_str.lower().endswith('kg'):
                value_str = value_str[:-2].strip()
                
            return float(value_str)
        except (ValueError, IndexError):
            return None
            
    def _extract_pulse_count(self, line: str) -> Optional[int]:
        """Extract pulse count from position line."""
        try:
            # Find the first word after "Pos="
            base = line.split()[0]  # "Pos=12345"
            pulse_str = base.split('=')[1]
            return int(pulse_str)
        except (ValueError, IndexError):
            return None
            
    def _extract_force_from_pos_line(self, line: str) -> Optional[float]:
        """Extract force value from a position line if present."""
        low = line.lower()
        if "force=" not in low:
            return None
            
        try:
            # Find the token that starts with "force="
            tokens = [token for token in line.split() if token.lower().startswith("force=")]
            if not tokens:
                return None
                
            force_token = tokens[0]
            force_value = force_token.split('=')[1]
            
            # Remove 'kg' suffix if present
            if force_value.lower().endswith('kg'):
                force_value = force_value[:-2]
                
            return float(force_value)
        except (ValueError, IndexError):
            return None
            
    def get_current_force(self) -> float:
        """Get the most recent force reading."""
        return self.current_force
