"""
Data models for the encoder GUI application.
"""
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EncoderSample:
    """Data structure for storing complete encoder reading."""
    time_ms: float           # Time in milliseconds
    pos: Optional[str] = None      # Position value
    cps: Optional[str] = None      # CPS value  
    rpm: Optional[str] = None      # RPM value


@dataclass
class DataBuffer:
    """Buffer for storing encoder samples with raw ESP32 output."""
    samples: List[EncoderSample] = field(default_factory=list)
    start_time: Optional[float] = None

    def add(self, raw_output: str) -> Optional[EncoderSample]:
        """Add a new line from ESP32 and parse it into a complete sample."""
        now = time.perf_counter()
        if self.start_time is None:
            self.start_time = now
        rel_time_ms = (now - self.start_time) * 1000  # Convert to milliseconds
        
        line = raw_output.strip()
        if not line:
            return None
        
        # Parse ESP32 output format: "Pos=12345 CPS=123.45 RPM=456.78"
        pos_val = None
        cps_val = None
        rpm_val = None
        
        parts = line.split()
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.upper()
                if key == 'POS':
                    pos_val = value
                elif key == 'CPS':
                    cps_val = value
                elif key == 'RPM':
                    rpm_val = value
        
        # Only create sample if we have at least one value
        if pos_val or cps_val or rpm_val:
            sample = EncoderSample(rel_time_ms, pos_val, cps_val, rpm_val)
            self.samples.append(sample)
            return sample
        
        return None

    def clear(self):
        """Clear all samples and reset state."""
        self.samples.clear()
        self.start_time = None

    def get_recent_samples(self, max_count: int) -> List[EncoderSample]:
        """Get the most recent samples, limited by count."""
        if len(self.samples) <= max_count:
            return self.samples[:]
        return self.samples[-max_count:]
