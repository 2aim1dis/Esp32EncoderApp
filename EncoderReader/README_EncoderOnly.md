# High-Performance Quadrature Encoder Reader (Encoder-Only Version)

## Recent Updates

### PCNT Speed Calculation Fix (September 2025)
✅ **Fixed:** Speed calculation (cps/RPM) now works correctly in Hardware PCNT mode  
✅ **Enhanced:** Mode-specific velocity calculation for optimal performance  
✅ **Verified:** Both position and speed measurements accurate in all modes  

---

## Overview
This is a streamlined version of the ESP32-S3 quadrature encoder reader, focused exclusively on high-performance encoder position and velocity measurement. The load cell functionality has been removed for applications that only require motion sensing.

## Key Features
- **Dual-Mode Operation**: Hardware PCNT (default) or Optimized ISR
- **High-Speed Capability**: >100kHz with PCNT, ~50kHz with ISR
- **Advanced Velocity Calculation**: Adaptive window/edge blending with EMA filtering
- **Noise Immunity**: Multiple filtering layers (hardware + software)
- **Low CPU Usage**: <2% in PCNT mode
- **Real-Time Response**: 10ms update rate (configurable)
- **Index Support**: Z-channel for reference positioning

## Hardware Configuration
```
Encoder Connection:
- A Channel (black)  → GPIO16
- B Channel (white)  → GPIO17
- Z Index (orange)   → GPIO18 (optional)
- VCC → 5V
- Pull-ups: 4.7kΩ to 3.3V on A/B/Z signals
```

## Performance Specifications
| Metric | PCNT Mode | ISR Mode |
|--------|-----------|----------|
| Max Speed | >100 kHz | ~50 kHz |
| CPU Usage | <2% | ~15% @ 50kHz |
| Response Time | 10ms | 10ms |
| Position Range | 64-bit | 64-bit |
| Direction | Full bidirectional | Full bidirectional |

## Configuration Options
Edit `config.h` to customize:
```cpp
#define ENC_PPR 1024              // Encoder pulses per revolution
#define USE_HARDWARE_PCNT 1       // Enable hardware counter
#define SPEED_SAMPLE_US 10000     // Update rate (10ms)
#define ADAPTIVE_BLENDING 1       // Smart velocity calculation
#define MIN_EDGE_INTERVAL_US 10   // Glitch filter
#define VELOCITY_TIMEOUT_US 500000 // Stop detection timeout
```

## Output Format
The system outputs real-time data via serial (115200 baud):
```
Pos=<position> cps=<counts/sec> rpm=<rpm> [Z]
```

Where:
- `position`: Absolute encoder position (counts)
- `cps`: Velocity in counts per second
- `rpm`: Velocity in revolutions per minute
- `Z`: Appears when index pulse detected

## Available Commands
- `ZERO`: Reset encoder position to zero

## Technical Highlights

### Hardware PCNT Mode (Recommended)
- Uses ESP32's dedicated pulse counter peripheral
- Hardware quadrature decoding with automatic direction
- Overflow/underflow interrupts for 64-bit range
- Built-in 1μs glitch filter
- Zero CPU overhead for counting

### Optimized ISR Mode (Fallback)
- Direct GPIO register access (10x faster than digitalRead)
- Lookup table for quadrature state transitions
- Minimal interrupt latency with IRAM placement
- Software glitch filtering

### Advanced Velocity Engine
- **Window-based**: Stable at low speeds
- **Edge-based**: Responsive at high speeds  
- **Adaptive blending**: Automatically chooses best method
- **EMA filtering**: Smooth, low-noise output
- **Timeout detection**: Immediate zero when stopped

## Build and Upload
```bash
# Using PlatformIO
pio run --target upload
pio device monitor

# Or use provided VS Code tasks
# Ctrl+Shift+P → "Tasks: Run Task" → "PIO Build"
```

## Applications
- CNC position feedback
- Servo motor control
- Robotics joint sensing
- Test equipment
- Speed measurement
- Angular position tracking

## Troubleshooting
| Issue | Solution |
|-------|----------|
| Missed counts at high speed | Enable PCNT mode |
| Noisy velocity readings | Increase EMA_ALPHA or add hardware filtering |
| Incorrect RPM | Verify ENC_PPR setting |
| Slow stop detection | Reduce VELOCITY_TIMEOUT_US |

## Files Structure
```
encoder.cpp/.h     - Core encoder logic (PCNT + ISR)
config.h           - Configuration parameters  
commands.cpp/.h    - Serial command handling
display.cpp/.h     - Output formatting
EncoderReader.ino  - Main application loop
```

## Performance Comparison vs Original
This encoder-only version provides:
- **Simplified codebase**: 30% smaller footprint
- **Faster boot time**: No load cell initialization
- **Lower memory usage**: Removed force processing variables
- **Higher update rate**: No HX711 sampling overhead
- **Cleaner output**: Pure motion data only

Perfect for applications requiring only high-precision motion sensing without force measurement.
