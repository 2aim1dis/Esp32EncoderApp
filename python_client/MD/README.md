# Python Encoder GUI

Tkinter-based GUI to acquire encoder position data from the ESP32-S3 firmware over serial and log/plot it.

## Features
- Enumerates COM ports (refresh auto every 2s)
- Connect / Disconnect
- Start / Stop acquisition (does not disconnect)
- Erase Data (clears buffer, plot, table and time zero)
- Export to Excel (.xlsx) with raw samples (time_s, pulses, delta)
- Live table at 10 ms resolution (appends as data arrives)
- Live plot of pulses vs time

## Install Dependencies
Use the project virtual environment or create one:

```
python -m venv .venv
".venv/Scripts/activate"
pip install -r requirements.txt
```

## Run
```
python encoder_gui.py
```

Select port, Connect, then Start. Export when finished.

## Notes
- The ESP32 sketch prints lines beginning with `Pos=`. Adjust parser in `_on_serial_line` if format changes.
- For very long captures you may want to limit stored samples or implement decimation.
