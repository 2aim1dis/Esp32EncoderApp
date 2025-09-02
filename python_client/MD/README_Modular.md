# ESP32 Encoder GUI - Modular Structure

This Python GUI application has been refactored from a monolithic 373-line file into a clean modular structure for better maintainability and understanding.

## File Structure

```
python_client/
├── encoder_gui_modular.py   # Main application (new modular version)
├── encoder_gui.py          # Original monolithic version (backup)
├── config.py               # Configuration constants
├── data_models.py          # Data structures and buffer management
├── serial_handler.py       # Serial communication and port management
├── data_parser.py          # ESP32 data parsing logic
├── gui_components.py       # UI components and window management
├── data_export.py          # Data export functionality
├── requirements.txt        # Python package dependencies
└── README_Modular.md       # This documentation
```

## Module Descriptions

### `config.py`
- Contains all configuration constants
- UI refresh rates, plot settings, serial parameters
- Easy to modify settings in one place

### `data_models.py`
- `Sample` dataclass for individual measurements
- `DataBuffer` class for thread-safe data storage
- Handles timestamps and pulse count deltas

### `serial_handler.py`
- `SerialReader` thread for background serial communication
- `SerialManager` for connection lifecycle management
- Port discovery and command sending

### `data_parser.py`
- `DataParser` class for ESP32 output parsing
- Handles position lines, force-only lines
- Extracts pulse counts and force measurements

### `gui_components.py`
- `MainWindow` class with all UI components
- `DialogHelper` for user interactions
- Separates UI layout from application logic

### `data_export.py`
- `DataExporter` class for file operations
- Excel and CSV export functionality
- Data summary statistics

### `encoder_gui_modular.py`
- `EncoderApplication` main coordinator class
- Integrates all modules together
- Handles application lifecycle and events

## Benefits of This Structure

1. **Single Responsibility**: Each module has one clear purpose
2. **Maintainability**: Easy to modify specific functionality
3. **Testability**: Individual modules can be tested separately
4. **Reusability**: Components can be reused in other projects
5. **Readability**: Much easier to understand and navigate
6. **Extensibility**: Simple to add new features

## Running the Application

### Original Version (Monolithic)
```bash
python encoder_gui.py
```

### New Modular Version  
```bash
python encoder_gui_modular.py
```

Both versions have identical functionality - the modular version is just better organized!

## Features

- **Real-time Data Display**: Position, RPM, and force measurements
- **Live Plotting**: Interactive graphs with automatic scaling
- **Serial Communication**: Connect to ESP32 via COM port
- **Data Export**: Save measurements to Excel or CSV files
- **Command Interface**: Send TARE and calibration commands
- **Auto-scrolling Table**: Optional automatic scrolling to latest data

## Hardware Requirements

- ESP32 with the modular Arduino encoder code
- USB connection to PC
- Quadrature encoder and load cell properly wired
- External pull-ups (4.7kΩ) for encoder signals

## Software Requirements

```
Python 3.8+
tkinter (usually included with Python)
pyserial
pandas  
matplotlib
openpyxl
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                EncoderApplication                           │
│                 (Main Coordinator)                          │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ MainWindow  │ │SerialManager│ │ DataParser  │           │
│ │(GUI Layout) │ │(COM Ports)  │ │(Parse Data) │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ DataBuffer  │ │DataExporter │ │   Config    │           │
│ │(Storage)    │ │(Excel/CSV)  │ │(Settings)   │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

This modular architecture makes the code much more professional and maintainable while preserving all the original functionality! 🚀
