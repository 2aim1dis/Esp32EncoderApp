# Μάθημα: Κατανοώντας το data_models.py - Data Structures & Memory Management

## Περιεχόμενα
1. [Data Modeling Principles](#1-data-modeling-principles)
2. [Sample Class Analysis](#2-sample-class-analysis)
3. [DataBuffer Class Architecture](#3-databuffer-class-architecture)
4. [Threading Safety Strategies](#4-threading-safety-strategies)
5. [Performance Optimization](#5-performance-optimization)
6. [Memory Management](#6-memory-management)
7. [Real-time Data Processing](#7-real-time-data-processing)
8. [Professional Design Patterns](#8-professional-design-patterns)

---

## 1. Data Modeling Principles

### Python Dataclass Architecture

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Sample:
    t: float                               # Time stamp (relative seconds)
    pulses: int                           # Encoder pulse count
    delta: int                            # Pulse change since last sample
    force: Optional[float] = None         # Force measurement (kg)
```

**Why Dataclass Instead of Regular Class?**

```python
# ❌ Traditional Class Approach (verbose, error-prone):
class Sample:
    def __init__(self, t: float, pulses: int, delta: int, force: float = None):
        self.t = t
        self.pulses = pulses
        self.delta = delta
        self.force = force
    
    def __repr__(self):
        return f"Sample(t={self.t}, pulses={self.pulses}, delta={self.delta}, force={self.force})"
    
    def __eq__(self, other):
        if not isinstance(other, Sample):
            return False
        return (self.t == other.t and self.pulses == other.pulses and 
                self.delta == other.delta and self.force == other.force)

# ✅ Dataclass Approach (concise, automatic features):
@dataclass
class Sample:
    t: float
    pulses: int
    delta: int
    force: Optional[float] = None
    
    # Automatically generates:
    # - __init__()
    # - __repr__()
    # - __eq__()
    # - Type hints enforcement
    # - Default value handling
```

**Dataclass Benefits:**

```
┌─────────────────────────────────────────────────────────────┐
│                 DATACLASS ADVANTAGES                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔧 AUTOMATIC CODE GENERATION                                │
│  • __init__(): Constructor with type checking               │
│  • __repr__(): String representation for debugging          │
│  • __eq__(): Equality comparison                            │
│                                                             │
│  📝 TYPE SAFETY                                              │
│  • Type hints enforced at runtime (with proper tools)       │
│  • IDE support for autocompletion and error detection       │
│  • Clear interface documentation                            │
│                                                             │
│  🏭 IMMUTABILITY OPTIONS                                     │
│  • frozen=True makes instances immutable                     │
│  • Prevents accidental data corruption                      │
│  • Thread-safe by design when frozen                        │
│                                                             │
│  🚀 PERFORMANCE                                              │
│  • __slots__ support for memory efficiency                  │
│  • Faster attribute access                                  │
│  • Reduced memory footprint                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Sample Class Analysis

### Data Structure Design

```python
@dataclass
class Sample:
    t: float                               # Time: Relative timestamp in seconds
    pulses: int                           # Pulses: Absolute encoder position  
    delta: int                            # Delta: Pulse change (velocity indicator)
    force: Optional[float] = None         # Force: Associated force measurement
```

**Field Analysis & Engineering Rationale:**

### 2.1 Time Field (`t: float`)

```python
# Time representation strategy:
t: float    # Relative seconds from start (e.g., 0.0, 0.01, 0.02...)
```

**Why Relative Time Instead of Absolute?**

```python
# ❌ Absolute timestamp approach:
import time
absolute_time = time.time()  # e.g., 1735123456.789
# Problems:
# • Large numbers: 1735123456.789 vs 0.001
# • Precision loss in calculations
# • Export files with unnecessarily long timestamps
# • Difficult to read and analyze

# ✅ Relative timestamp approach:  
start_time = time.perf_counter()
relative_time = time.perf_counter() - start_time  # e.g., 0.001, 0.002...
# Benefits:
# • Compact, readable values
# • High precision calculations  
# • Easy time difference calculations
# • Clean export data format
```

**Time Precision Requirements:**
```python
# ESP32 sample rate: 100 Hz = 0.01 second intervals
# Required precision: 0.001 seconds (1ms)
# Python float precision: ~15 decimal digits
# Adequate for hours of data: 3600.000 seconds (still high precision)

# Time calculations example:
sample_interval = 0.01  # 10ms
duration_1_hour = 3600.0
samples_per_hour = duration_1_hour / sample_interval  # 360,000 samples
precision_needed = 0.001  # 1ms accuracy
# float64 can represent this precisely for days of continuous operation
```

### 2.2 Pulses Field (`pulses: int`)

```python
pulses: int    # Absolute encoder position (cumulative count)
```

**Pulse Count Architecture:**
```python
# Encoder pulse counting strategy:
# ESP32 outputs: "Pos=12345" (absolute position)
# Not: relative increments

# Benefits of absolute position:
# ✅ Simple synchronization - any missed samples don't compound errors
# ✅ Easy position tracking - current position always known  
# ✅ Velocity calculation - delta = new_pos - old_pos
# ✅ Position reset capability - TARE command sets to zero

# Data range planning:
encoder_ppr = 2048        # Pulses per revolution (Omron E6B2-CWZ6C)
max_rpm = 6000           # Maximum expected RPM
max_pulses_per_minute = max_rpm * encoder_ppr  # 12,288,000
max_pulses_per_hour = max_pulses_per_minute * 60  # 737,280,000

# Python int range: practically unlimited (32-bit+ systems)
# No overflow concerns even for continuous operation
```

### 2.3 Delta Field (`delta: int`)

```python
delta: int     # Velocity indicator: pulses_current - pulses_previous
```

**Delta Calculation Strategy:**
```python
# Velocity calculation method:
def calculate_delta(current_pulses: int, previous_pulses: int) -> int:
    """Calculate pulse change (velocity indicator)."""
    return current_pulses - previous_pulses

# Example sequence:
samples = [
    Sample(t=0.00, pulses=1000, delta=0),     # First sample, no delta
    Sample(t=0.01, pulses=1010, delta=10),    # +10 pulses in 10ms  
    Sample(t=0.02, pulses=1025, delta=15),    # +15 pulses in 10ms
    Sample(t=0.03, pulses=1020, delta=-5),    # -5 pulses (reverse)
]

# Velocity interpretation:
# delta > 0: Forward rotation
# delta < 0: Reverse rotation  
# delta = 0: No movement
# |delta|: Speed magnitude
```

**Delta vs Velocity Conversion:**
```python
def delta_to_rpm(delta: int, time_interval: float, encoder_ppr: int) -> float:
    """Convert pulse delta to RPM."""
    pulses_per_second = delta / time_interval
    revolutions_per_second = pulses_per_second / encoder_ppr
    rpm = revolutions_per_second * 60
    return rpm

# Example with our data:
time_interval = 0.01  # 10ms sample interval
encoder_ppr = 2048    # Omron E6B2-CWZ6C specifications
delta = 10           # 10 pulses change

rpm = delta_to_rpm(delta, time_interval, encoder_ppr)
# Result: 2.93 RPM (very slow, suitable for precise measurement)
```

### 2.4 Force Field (`force: Optional[float] = None`)

```python
force: Optional[float] = None    # Force measurement in kg
```

**Optional Force Design Rationale:**

```python
# Why Optional[float]?

# Scenario 1: Encoder-only mode
sample_encoder_only = Sample(t=1.0, pulses=1000, delta=10, force=None)
# System operates without force sensor
# force=None indicates no force data available

# Scenario 2: Integrated encoder + force
sample_with_force = Sample(t=1.0, pulses=1000, delta=10, force=2.543)  
# Combined position and force measurement
# Full system capabilities

# Scenario 3: Missing force data
sample_missed_force = Sample(t=1.0, pulses=1000, delta=10, force=None)
# Network packet loss or sensor malfunction
# Position data preserved, force marked as unavailable
```

**Force Data Processing:**
```python
def process_force_data(samples: List[Sample]) -> dict:
    """Process force data with None-safe operations."""
    
    # Filter valid force readings
    valid_forces = [s.force for s in samples if s.force is not None]
    
    if not valid_forces:
        return {"status": "no_force_data"}
    
    return {
        "status": "force_available",
        "count": len(valid_forces),
        "min_force": min(valid_forces),
        "max_force": max(valid_forces),
        "avg_force": sum(valid_forces) / len(valid_forces),
        "coverage": len(valid_forces) / len(samples) * 100  # Percentage
    }

# Usage example:
samples = [
    Sample(t=0.0, pulses=1000, delta=0, force=1.5),
    Sample(t=0.1, pulses=1010, delta=10, force=None),  # Missing force
    Sample(t=0.2, pulses=1020, delta=10, force=2.1),
]

stats = process_force_data(samples)
# Result: {"status": "force_available", "coverage": 66.7, ...}
```

---

## 3. DataBuffer Class Architecture

### Buffer Management Design

```python
@dataclass
class DataBuffer:
    samples: List[Sample] = field(default_factory=list)
    last_pulses: Optional[int] = None
    start_time: Optional[float] = None
```

**Why field(default_factory=list)?**

```python
# ❌ DANGEROUS - Mutable Default Argument:
@dataclass
class DataBuffer:
    samples: List[Sample] = []  # SHARED between ALL instances!

# Problem demonstration:
buffer1 = DataBuffer()
buffer2 = DataBuffer()
buffer1.samples.append(sample)
print(len(buffer2.samples))  # 1 - UNEXPECTED! Shared reference

# ✅ SAFE - Factory Function:
@dataclass  
class DataBuffer:
    samples: List[Sample] = field(default_factory=list)

# Each instance gets its own list:
buffer1 = DataBuffer()
buffer2 = DataBuffer()  
buffer1.samples.append(sample)
print(len(buffer2.samples))  # 0 - CORRECT! Independent instances
```

**Buffer State Management:**
```python
# State tracking rationale:
class DataBuffer:
    samples: List[Sample]           # Core data storage
    last_pulses: Optional[int]      # Delta calculation state
    start_time: Optional[float]     # Relative time reference
    
# State lifecycle:
# 1. Initial: samples=[], last_pulses=None, start_time=None
# 2. First sample: Set start_time, last_pulses, delta=0
# 3. Subsequent: Calculate delta from last_pulses
# 4. Reset: Clear all state, return to initial
```

### 3.1 Add Method Implementation

```python
def add(self, pulses: int, force: Optional[float] = None) -> Sample:
    """Add new measurement to buffer with automatic timestamp and delta calculation."""
    
    # High-precision timestamp
    now = time.perf_counter()
    
    # Initialize timing reference on first sample
    if self.start_time is None:
        self.start_time = now
    
    # Calculate relative time
    rel_t = now - self.start_time
    
    # Calculate delta (velocity indicator)
    if self.last_pulses is None:
        delta = 0  # First sample has no reference
    else:
        delta = pulses - self.last_pulses
    
    # Update state
    self.last_pulses = pulses
    
    # Create and store sample
    s = Sample(rel_t, pulses, delta, force)
    self.samples.append(s)
    
    return s
```

**Method Design Analysis:**

```python
# Performance characteristics:
def add(self, pulses: int, force: Optional[float] = None) -> Sample:
    # Time complexity: O(1) - constant time operations
    # Memory complexity: O(1) - single sample allocation
    # Thread safety: Not inherently thread-safe (requires external locking)
    
# Timing precision analysis:
time.perf_counter()  # Benefits:
# ✅ Monotonic - never goes backward
# ✅ High precision - nanosecond resolution on most systems
# ✅ Best for measuring elapsed time
# ❌ Alternative time.time() can jump (NTP adjustments, leap seconds)

# State management strategy:
# Essential state: start_time, last_pulses
# Derived data: rel_t, delta (calculated each call)
# Persistent data: samples list (grows over time)
```

**Usage Pattern Example:**
```python
# Typical usage sequence:
buffer = DataBuffer()

# Simulate incoming encoder data:
buffer.add(pulses=1000, force=1.2)  # t≈0.000, delta=0
time.sleep(0.01)
buffer.add(pulses=1010, force=1.3)  # t≈0.010, delta=10
time.sleep(0.01)  
buffer.add(pulses=1025, force=1.1)  # t≈0.020, delta=15

# Results:
for sample in buffer.samples:
    print(f"t={sample.t:.3f}, pulses={sample.pulses}, delta={sample.delta}")
# Output:
# t=0.000, pulses=1000, delta=0
# t=0.010, pulses=1010, delta=10
# t=0.020, pulses=1025, delta=15
```

### 3.2 Clear Method Implementation

```python
def clear(self):
    """Reset buffer to initial empty state."""
    self.samples.clear()
    self.last_pulses = None
    self.start_time = None
```

**Reset Strategy Analysis:**
```python
# Complete state reset approach:
def clear(self):
    # 1. Clear data storage
    self.samples.clear()  # Removes all samples, frees memory
    
    # 2. Reset calculation state  
    self.last_pulses = None  # Next delta will be 0
    
    # 3. Reset timing reference
    self.start_time = None   # Next add() will establish new start time

# Why complete reset?
# ✅ Clean slate - no residual state from previous session
# ✅ Memory efficiency - frees all sample memory
# ✅ Prevents state corruption - eliminates timing discontinuities
# ✅ Thread safety - atomic state reset (with external locking)
```

**Memory Management:**
```python
# Memory behavior analysis:
buffer = DataBuffer()

# Add 100,000 samples (≈1000 seconds at 100Hz):
for i in range(100_000):
    buffer.add(pulses=i, force=1.0)

# Memory usage before clear:
sample_size = 32  # bytes (estimate for Sample instance)
memory_used = len(buffer.samples) * sample_size  # ≈3.2 MB

# After clear():
buffer.clear()
memory_used_after = 0  # All samples garbage collected

# Benefits:
# ✅ Immediate memory reclamation
# ✅ No memory leaks
# ✅ Prepares for new session
```

---

## 4. Threading Safety Strategies

### Thread Safety Analysis

```python
# DataBuffer is NOT inherently thread-safe:
class DataBuffer:
    def add(self, pulses: int, force: Optional[float] = None) -> Sample:
        # RACE CONDITIONS possible:
        # 1. Multiple threads calling add() simultaneously
        # 2. One thread calling add() while another calls clear()
        # 3. GUI thread reading samples while data thread adds
```

**Thread Safety Implementation:**
```python
# ✅ SAFE - External Locking Strategy (used in GUI):
import threading

class EncoderGUI:
    def __init__(self):
        self.buffer = DataBuffer()
        self.mutex = threading.Lock()  # Protects buffer access
    
    def _on_serial_line(self, line: str):
        # Serial thread adds data
        pulses = extract_pulses(line)
        force = extract_force(line)
        
        with self.mutex:  # Critical section
            self.buffer.add(pulses, force)
    
    def _update_table_and_plot(self):
        # GUI thread reads data
        with self.mutex:  # Critical section
            data = list(self.buffer.samples)  # Copy for safe access
        
        # Process data outside lock (no blocking)
        update_ui(data)
    
    def clear_data(self):
        # UI thread clears data
        with self.mutex:  # Critical section
            self.buffer.clear()
```

**Alternative Thread-Safe Design:**
```python
# ✅ ALTERNATIVE - Built-in Thread Safety:
import threading
from dataclasses import dataclass, field
from typing import List
import time

@dataclass
class ThreadSafeDataBuffer:
    samples: List[Sample] = field(default_factory=list)
    last_pulses: Optional[int] = None
    start_time: Optional[float] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def add(self, pulses: int, force: Optional[float] = None) -> Sample:
        """Thread-safe add method."""
        with self._lock:
            now = time.perf_counter()
            if self.start_time is None:
                self.start_time = now
            rel_t = now - self.start_time
            
            delta = 0 if self.last_pulses is None else pulses - self.last_pulses
            self.last_pulses = pulses
            
            s = Sample(rel_t, pulses, delta, force)
            self.samples.append(s)
            return s
    
    def get_samples_copy(self) -> List[Sample]:
        """Thread-safe sample access."""
        with self._lock:
            return list(self.samples)
    
    def clear(self):
        """Thread-safe clear method."""
        with self._lock:
            self.samples.clear()
            self.last_pulses = None
            self.start_time = None

# Usage (no external locking needed):
buffer = ThreadSafeDataBuffer()

# Multiple threads can safely call:
buffer.add(pulses=1000, force=1.5)  # Thread 1
samples = buffer.get_samples_copy()  # Thread 2 
buffer.clear()                       # Thread 3
```

---

## 5. Performance Optimization

### Memory Growth Analysis

```python
# Memory usage calculation:
def calculate_memory_usage(sample_count: int) -> dict:
    """Calculate estimated memory usage for given sample count."""
    
    # Sample memory breakdown:
    sample_base_size = 28  # Base Python object overhead
    float_size = 8         # t: float (64-bit)
    int_size = 8           # pulses: int (64-bit on most systems)  
    int_size = 8           # delta: int
    optional_float = 8     # force: Optional[float]
    
    bytes_per_sample = sample_base_size + float_size + int_size * 2 + optional_float
    # Total: ≈60 bytes per sample (conservative estimate)
    
    total_bytes = sample_count * bytes_per_sample
    
    return {
        "samples": sample_count,
        "bytes_per_sample": bytes_per_sample,
        "total_bytes": total_bytes,
        "total_mb": total_bytes / (1024 * 1024),
        "list_overhead": sample_count * 8  # Python list pointer overhead
    }

# Memory usage examples:
usage_1k = calculate_memory_usage(1_000)      # 1 second @ 1kHz
usage_10k = calculate_memory_usage(10_000)    # 10 seconds @ 1kHz  
usage_100k = calculate_memory_usage(100_000)  # 100 seconds @ 1kHz
usage_1M = calculate_memory_usage(1_000_000)  # 1000 seconds @ 1kHz

print(f"1K samples: {usage_1k['total_mb']:.1f} MB")    # ≈0.06 MB
print(f"10K samples: {usage_10k['total_mb']:.1f} MB")  # ≈0.6 MB
print(f"100K samples: {usage_100k['total_mb']:.1f} MB") # ≈6 MB
print(f"1M samples: {usage_1M['total_mb']:.1f} MB")    # ≈60 MB
```

### Performance Optimization Strategies

```python
# Strategy 1: Memory-conscious sample limits
MAX_SAMPLES = 100_000  # ≈6MB memory limit

def add_with_limit(buffer: DataBuffer, pulses: int, force: Optional[float] = None):
    """Add sample with automatic memory management."""
    sample = buffer.add(pulses, force)
    
    # Remove old samples if limit exceeded
    if len(buffer.samples) > MAX_SAMPLES:
        # Remove oldest 10% to avoid frequent trimming
        trim_count = MAX_SAMPLES // 10
        buffer.samples = buffer.samples[trim_count:]
    
    return sample

# Strategy 2: Sample decimation for long runs
def decimate_buffer(buffer: DataBuffer, target_count: int = 10_000):
    """Reduce sample count while preserving trends."""
    if len(buffer.samples) <= target_count:
        return
    
    # Keep every Nth sample
    step = len(buffer.samples) // target_count
    buffer.samples = buffer.samples[::step]

# Strategy 3: Time-based cleanup  
def cleanup_old_samples(buffer: DataBuffer, max_age_seconds: float = 3600):
    """Remove samples older than specified age."""
    if not buffer.samples:
        return
    
    current_time = buffer.samples[-1].t  # Latest sample time
    cutoff_time = current_time - max_age_seconds
    
    # Find first sample to keep
    keep_index = 0
    for i, sample in enumerate(buffer.samples):
        if sample.t >= cutoff_time:
            keep_index = i
            break
    
    # Remove old samples
    if keep_index > 0:
        buffer.samples = buffer.samples[keep_index:]
```

---

## 6. Memory Management

### Efficient Data Access Patterns

```python
# ✅ EFFICIENT - Copy for External Access:
def get_recent_samples(buffer: DataBuffer, count: int) -> List[Sample]:
    """Get recent samples efficiently."""
    with buffer_lock:  # Thread safety
        return buffer.samples[-count:] if buffer.samples else []

# ❌ INEFFICIENT - Direct Reference Sharing:
def get_all_samples_reference(buffer: DataBuffer) -> List[Sample]:
    """DANGEROUS - Returns mutable reference."""
    return buffer.samples  # External code can modify buffer!

# ✅ EFFICIENT - Iterator Pattern for Large Data:
def iterate_samples_by_time(buffer: DataBuffer, start_time: float, end_time: float):
    """Memory-efficient time-range iteration."""
    for sample in buffer.samples:
        if start_time <= sample.t <= end_time:
            yield sample
        elif sample.t > end_time:
            break  # Samples are time-ordered, can stop early

# Usage:
for sample in iterate_samples_by_time(buffer, 10.0, 20.0):
    process_sample(sample)  # Process one sample at a time, low memory usage
```

### Memory Pool Optimization (Advanced)

```python
# Advanced: Pre-allocated memory pools for high-frequency applications
from typing import Deque
from collections import deque

class MemoryEfficientBuffer:
    """Buffer using circular buffer for fixed memory usage."""
    
    def __init__(self, max_samples: int = 10_000):
        self.max_samples = max_samples
        self.samples: Deque[Sample] = deque(maxlen=max_samples)
        self.last_pulses: Optional[int] = None
        self.start_time: Optional[float] = None
    
    def add(self, pulses: int, force: Optional[float] = None) -> Sample:
        """Add sample with automatic old sample eviction."""
        now = time.perf_counter()
        if self.start_time is None:
            self.start_time = now
        
        rel_t = now - self.start_time
        delta = 0 if self.last_pulses is None else pulses - self.last_pulses
        self.last_pulses = pulses
        
        sample = Sample(rel_t, pulses, delta, force)
        
        # deque automatically evicts oldest when maxlen exceeded
        self.samples.append(sample)
        
        return sample
    
    def memory_usage(self) -> dict:
        """Get current memory statistics."""
        return {
            "current_samples": len(self.samples),
            "max_samples": self.max_samples,
            "memory_efficiency": len(self.samples) / self.max_samples * 100,
            "estimated_bytes": len(self.samples) * 60  # 60 bytes per sample estimate
        }

# Benefits:
# ✅ Fixed memory usage - never exceeds max_samples
# ✅ Automatic old data cleanup
# ✅ O(1) append and pop operations  
# ✅ Thread-safe with external locking
```

---

## 7. Real-time Data Processing

### High-Frequency Data Ingestion

```python
# Real-time processing considerations:
class HighPerformanceBuffer:
    """Optimized buffer for high-frequency data acquisition."""
    
    def __init__(self, initial_capacity: int = 10_000):
        # Pre-allocate list capacity to avoid frequent reallocations
        self.samples: List[Sample] = []
        self.samples.reserve(initial_capacity)  # Hypothetical - Python lists auto-resize
        
        self.last_pulses: Optional[int] = None
        self.start_time: Optional[float] = None
        
        # Performance monitoring
        self.add_count = 0
        self.last_performance_check = time.perf_counter()
    
    def add(self, pulses: int, force: Optional[float] = None) -> Sample:
        """High-performance add with monitoring."""
        now = time.perf_counter()
        
        # Fast path for timing
        if self.start_time is None:
            self.start_time = now
            rel_t = 0.0
        else:
            rel_t = now - self.start_time
        
        # Fast delta calculation
        if self.last_pulses is None:
            delta = 0
        else:
            delta = pulses - self.last_pulses
        self.last_pulses = pulses
        
        # Create sample (optimized constructor usage)
        sample = Sample(rel_t, pulses, delta, force)
        self.samples.append(sample)
        
        # Performance monitoring
        self.add_count += 1
        if self.add_count % 1000 == 0:  # Check every 1000 samples
            self._check_performance(now)
        
        return sample
    
    def _check_performance(self, current_time: float):
        """Monitor data ingestion performance."""
        time_elapsed = current_time - self.last_performance_check
        sample_rate = 1000 / time_elapsed if time_elapsed > 0 else 0
        
        print(f"Sample rate: {sample_rate:.1f} Hz, Total samples: {len(self.samples)}")
        
        self.last_performance_check = current_time

# Performance characteristics:
# Expected: 100-1000 Hz sustained ingestion
# Memory: Efficient list operations
# Timing: perf_counter() precision ≈1 microsecond
# Thread safety: Requires external synchronization
```

### Streaming Data Export

```python
# Streaming export for long-running sessions:
def export_stream_to_csv(buffer: DataBuffer, filename: str, batch_size: int = 1000):
    """Export data in batches to handle large datasets."""
    
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        
        # Write header
        writer.writerow(['time_s', 'pulses', 'delta', 'force_kg'])
        
        # Write data in batches
        for i in range(0, len(buffer.samples), batch_size):
            batch = buffer.samples[i:i + batch_size]
            
            for sample in batch:
                force_str = f"{sample.force:.3f}" if sample.force is not None else ""
                writer.writerow([f"{sample.t:.3f}", sample.pulses, sample.delta, force_str])
            
            # Yield control to other threads periodically
            if i % (batch_size * 10) == 0:
                time.sleep(0.001)  # 1ms pause every 10,000 samples
    
    return True

# Benefits:
# ✅ Handles gigabytes of data without memory issues
# ✅ Provides progress feedback opportunities
# ✅ Doesn't block UI for long periods
# ✅ Can be cancelled mid-export
```

---

## 8. Professional Design Patterns

### Factory Pattern for Sample Creation

```python
# Advanced: Factory pattern for different sample types
class SampleFactory:
    """Factory for creating different types of samples."""
    
    @staticmethod
    def create_encoder_sample(timestamp: float, pulses: int, delta: int) -> Sample:
        """Create encoder-only sample."""
        return Sample(t=timestamp, pulses=pulses, delta=delta, force=None)
    
    @staticmethod  
    def create_force_sample(timestamp: float, pulses: int, delta: int, force: float) -> Sample:
        """Create sample with force data."""
        return Sample(t=timestamp, pulses=pulses, delta=delta, force=force)
    
    @staticmethod
    def create_from_serial_line(line: str, reference_time: float, last_pulses: Optional[int]) -> Optional[Sample]:
        """Create sample by parsing ESP32 serial output."""
        try:
            # Parse ESP32 format: "Pos=1234 cps=56.7 rpm=890.1 Z"
            if not line.startswith("Pos="):
                return None
            
            # Extract pulse count
            parts = line.split()
            pos_part = parts[0]
            pulses = int(pos_part.split('=')[1])
            
            # Calculate delta
            delta = 0 if last_pulses is None else pulses - last_pulses
            
            # Extract force if present
            force = None
            for part in parts:
                if part.lower().startswith("force="):
                    force_str = part.split('=')[1].replace('kg', '')
                    force = float(force_str)
                    break
            
            # Create appropriate sample type
            timestamp = time.perf_counter() - reference_time
            return Sample(t=timestamp, pulses=pulses, delta=delta, force=force)
            
        except (ValueError, IndexError):
            return None

# Usage:
factory = SampleFactory()
sample = factory.create_from_serial_line("Pos=1234 cps=56.7 force=2.34kg", start_time, last_pos)
```

### Builder Pattern for Complex Configuration

```python
# Advanced: Builder pattern for buffer configuration
class DataBufferBuilder:
    """Builder for configuring DataBuffer with advanced options."""
    
    def __init__(self):
        self.max_samples = None
        self.auto_decimate = False
        self.decimate_ratio = 0.1
        self.performance_monitoring = False
        self.export_format = "excel"
    
    def with_max_samples(self, max_samples: int):
        """Set maximum sample count with auto-cleanup."""
        self.max_samples = max_samples
        return self
    
    def with_auto_decimation(self, ratio: float = 0.1):
        """Enable automatic decimation when buffer fills."""
        self.auto_decimate = True
        self.decimate_ratio = ratio
        return self
    
    def with_performance_monitoring(self):
        """Enable performance tracking."""
        self.performance_monitoring = True
        return self
    
    def build(self) -> 'ConfiguredDataBuffer':
        """Build configured buffer."""
        return ConfiguredDataBuffer(
            max_samples=self.max_samples,
            auto_decimate=self.auto_decimate,
            decimate_ratio=self.decimate_ratio,
            performance_monitoring=self.performance_monitoring
        )

# Usage:
buffer = (DataBufferBuilder()
          .with_max_samples(50_000)
          .with_auto_decimation(0.2)
          .with_performance_monitoring()
          .build())
```

---

## Συμπέρασμα: Professional Data Architecture

Το **data_models.py** module αποδεικνύει τις αρχές **modern Python data modeling**:

### 🎯 **Data Structure Excellence**
- **Dataclass power** - Automatic code generation με type safety
- **Memory efficiency** - Optimized field layout και smart defaults  
- **Type safety** - Optional types για robust data handling
- **Performance focus** - O(1) operations και memory-conscious design

### ⚡ **Real-time Data Processing**
- **High-frequency ingestion** - 100-1000 Hz sustained data rates
- **Thread safety awareness** - Design που supports concurrent access
- **Memory management** - Efficient growth και cleanup strategies
- **Performance monitoring** - Built-in metrics για optimization

### 📊 **Professional Design Patterns**
- **Separation of concerns** - Data structure ≠ Data processing
- **Factory methods** - Flexible sample creation strategies  
- **Builder patterns** - Complex configuration management
- **Streaming processing** - Handle large datasets efficiently

### 🛡️ **Production-Ready Features**
- **Error handling** - Graceful degradation με Optional types
- **State management** - Clean initialization και reset capabilities
- **Memory bounds** - Predictable memory usage characteristics
- **Extensibility** - Easy to add new fields και functionality

**Το data_models.py είναι ένα excellent foundation για high-performance real-time data acquisition systems - simple interface που encapsulates sophisticated memory management και thread safety considerations.** 🎉

**Key Insight:** Proper data modeling είναι η cornerstone για scalable, maintainable, και high-performance applications! 🚀
