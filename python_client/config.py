# Configuration constants for the Encoder GUI application

# UI refresh and performance settings
UI_REFRESH_MS = 100         # GUI update interval in milliseconds
MAX_PLOT_POINTS = 4000      # Maximum points to display on plot
DECIMATE_TARGET = 4000      # Target points when decimating large datasets

# Serial communication settings
DEFAULT_BAUD_RATE = 115200  # Default serial port baud rate
SERIAL_TIMEOUT = 0.2        # Serial read timeout in seconds

# GUI dimensions and formatting
TABLE_HEIGHT = 25           # Height of the data table in rows
FORCE_FONT_SIZE = 16        # Font size for force display
PLOT_FIGURE_SIZE = (5, 4)   # Plot figure size (width, height)
PLOT_DPI = 100             # Plot resolution

# Export settings
DEFAULT_EXPORT_EXTENSION = ".xlsx"
EXCEL_SHEET_NAME = "Data"

# Port refresh interval
PORT_REFRESH_INTERVAL_MS = 2000  # How often to refresh COM port list
