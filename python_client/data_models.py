"""
Data models for the Encoder GUI application.
Handles sample storage and data buffer management.
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Sample:
    """Represents a single measurement sample from the encoder."""
    t: float                    # Timestamp in seconds (relative to start)
    pulses: int                # Encoder pulse count
    delta: int                 # Change in pulses since last sample
    force: Optional[float] = None  # Force measurement in kg (if available)


@dataclass
class DataBuffer:
    """Buffer for storing and managing measurement samples."""
    samples: List[Sample] = field(default_factory=list)
    last_pulses: Optional[int] = None
    start_time: Optional[float] = None

    def add(self, pulses: int, force: Optional[float] = None) -> Sample:
        """
        Add a new sample to the buffer.
        
        Args:
            pulses: Current encoder pulse count
            force: Force measurement in kg (optional)
            
        Returns:
            The created Sample object
        """
        now = time.perf_counter()
        
        # Initialize start time on first sample
        if self.start_time is None:
            self.start_time = now
            
        rel_t = now - self.start_time
        
        # Calculate delta (change in pulses)
        if self.last_pulses is None:
            delta = 0
        else:
            delta = pulses - self.last_pulses
            
        self.last_pulses = pulses
        
        # Create and store sample
        sample = Sample(rel_t, pulses, delta, force)
        self.samples.append(sample)
        
        return sample

    def clear(self):
        """Clear all samples and reset buffer state."""
        self.samples.clear()
        self.last_pulses = None
        self.start_time = None
        
    def get_samples_copy(self) -> List[Sample]:
        """Get a copy of all samples for thread-safe access."""
        return list(self.samples)
        
    def get_sample_count(self) -> int:
        """Get the total number of samples in the buffer."""
        return len(self.samples)
