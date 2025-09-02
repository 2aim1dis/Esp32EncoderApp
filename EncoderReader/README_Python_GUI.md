# ESP32 Encoder Python GUI - Modular Version

A modular Python GUI application for monitoring ESP32 encoder data in real-time.

## Features

- **Real-time ESP32 monitoring**: Parse and display measurements in organized columns
- **Modular architecture**: Separated components for easy maintenance
- **Data visualization**: Real-time plotting of encoder position data
- **Column-based display**: Table shows Time (ms), Pos, CPS, RPM in separate columns
- **Raw number values**: Clean display of exact values from ESP32
- **Serial communication**: Robust ESP32 communication handling
- **Data export**: Export column data to Excel or CSV formats
- **Zero position control**: Send zero command to ESP32

## File Structure

```
encoder_gui_modular.py    # Main GUI application
data_models.py           # Data structures and buffer management
serial_handler.py        # Serial communication with ESP32
visualization.py         # Plot and table components
requirements.txt         # Python dependencies
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python encoder_gui_modular.py
   ```

## Usage

1. **Connect to ESP32:**
   - Select the COM port from the dropdown
   - Click "Refresh" to update available ports
   - Click "Connect" to establish connection

2. **Start monitoring:**
   - Click "Start" to begin data acquisition
   - Real-time data will appear in the plot and table

3. **Control encoder:**
   - "Zero Position" - Send zero command to ESP32
   - "Clear Data" - Clear captured data from GUI
   - "Export Data" - Save column data to Excel/CSV file

## Data Format

The GUI parses ESP32 output in the format:
```
Pos=12345 CPS=123.45 RPM=456.78
```

The table displays data in columns:
- **Time (ms)**: Timestamp in milliseconds from start of data collection
- **Pos**: Position value (raw number from ESP32)
- **CPS**: Counts per second value (raw number from ESP32)
- **RPM**: Revolutions per minute value (raw number from ESP32)

Example table display:
```
Time (ms) | Pos   | CPS    | RPM
----------|-------|--------|--------
1250.5    | 12345 | 123.45 | 456.78
1350.2    | 12346 | 124.12 | 457.22
1450.8    | 12347 | 125.67 | 458.89
```

## Modular Components

### data_models.py
- `EncoderSample`: Data structure for complete measurement set (Time, Pos, CPS, RPM)
- `DataBuffer`: Buffer management for column-based measurement data

### serial_handler.py
- `SerialThread`: Threaded serial communication
- Port detection and management functions

### visualization.py
- `EncoderPlot`: Real-time matplotlib plotting (uses Pos column data)
- `DataTable`: Column-based measurement display with timestamps

### encoder_gui_modular.py
- Main application class integrating all components
- GUI layout and event handling

## Advantages of Modular Design

1. **Maintainability**: Each component has a single responsibility
2. **Reusability**: Components can be used in other projects
3. **Testing**: Individual components can be tested separately
4. **Extensibility**: Easy to add new features or modify existing ones
5. **Readability**: Code is organized and easier to understand

## Troubleshooting

- **No data received**: Check ESP32 serial output format
- **Connection issues**: Verify COM port and cable connection
- **Performance**: Reduce refresh rate if GUI becomes slow
