# ESP32-S3 Encoder Reader - Modular Structure

This project has been refactored into a modular structure for better maintainability and understanding.

## File Structure

```
ArduinoEncoderSketch/
├── EncoderReader.ino    # Main application file
├── config.h             # Configuration constants
├── encoder.h/.cpp       # Quadrature encoder functionality
├── loadcell.h/.cpp      # HX711 load cell functionality  
├── commands.h/.cpp      # Serial command processing
├── display.h/.cpp       # Output formatting and display
└── README_Structure.md  # This file
```

## Module Descriptions

### `config.h`
- Contains all configuration constants
- Pin definitions for encoder and load cell
- Timing parameters and filter coefficients
- Easy to modify settings in one place

### `encoder.h/.cpp`
- Handles quadrature encoder functionality
- Interrupt service routines for A/B/Z channels
- Position tracking and speed calculations
- EMA filtering for smooth velocity readings

### `loadcell.h/.cpp` 
- HX711 load cell interface
- Non-blocking sampling with averaging
- Calibration and tare functionality
- IIR filtering for stable force readings

### `commands.h/.cpp`
- Serial command processing
- Handles TARE, CAL, RAW, SCALE commands
- Clean separation of command parsing from execution

### `display.h/.cpp`
- Output formatting functions
- Status messages and data display
- Separates presentation from data processing

### `EncoderReader.ino`
- Main application coordination
- System initialization
- Main loop coordination
- Clean, readable flow

## Benefits of This Structure

1. **Maintainability**: Each module has a single responsibility
2. **Readability**: Much easier to understand individual components
3. **Testability**: Modules can be tested independently
4. **Reusability**: Modules can be reused in other projects
5. **Debugging**: Issues can be isolated to specific modules
6. **Collaboration**: Multiple developers can work on different modules

## Usage

The functionality remains exactly the same as the original monolithic code:
- Encoder position and speed measurement
- Load cell force measurement
- Serial commands: TARE, CAL <kg>, RAW, SCALE
- Real-time data output

## Hardware Connections

- **Encoder**: A=GPIO16, B=GPIO17, Z=GPIO18 (optional)
- **Load Cell (HX711)**: DOUT=GPIO40, SCK=GPIO41
- **Power**: External 4.7kΩ pull-ups to 3.3V for encoder signals

## Compilation

This modular structure compiles exactly like the original single file - Arduino IDE automatically includes all .h/.cpp files in the sketch folder.
