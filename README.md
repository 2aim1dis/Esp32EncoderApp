# ESP32-S3 Quadrature Encoder (Omron E6B2-CWZ6C)

High performance, low-latency quadrature encoder reader for ESP32-S3 DevKit (N8R8) capturing A/B/Z from Omron E6B2-CWZ6C.

## Hardware
- Board: ESP32-S3-DevKitC-1 (N8R8)
- Encoder: Omron E6B2-CWZ6C (e.g. 360/600/1024/2048 P/R)
- Connections (use 3.3V logic, open collector -> pull-ups 4.7k to 3V3):
  - A (Black) -> GPIO16
  - B (White) -> GPIO17
  - Z (Orange) -> GPIO18 (optional index)
  - Brown -> +5V external supply
  - Blue  -> GND (shared with ESP32 GND)
  - Shield -> GND (optional)

## Features
- Interrupt driven edge capture on A & B (and optional Z)
- Hardware cycle counter timestamping for precise delta-time
- 32-bit position accumulator with direction
- Optional index reset or latch using Z pulse
- Velocity (counts/sec, rev/sec, RPM) with configurable sample period
- Exponential moving average for stable speed while preserving fast response
- Jitter-resistant by using delta timestamps not fixed polling

## Build
PlatformIO (recommended) or Arduino IDE.

### PlatformIO Quick Start
```
# Install PlatformIO Core if needed
pip install platformio

# Initialize project inside this folder (if not already)
platformio project init --board esp32-s3-devkitc-1

# Build
platformio run

# Upload
platformio run --target upload

# Monitor
platformio device monitor -b 115200
```

## Output
Serial prints position and speed every sample window.

## License
MIT
