#!/usr/bin/env python3
"""
Simple launcher for the ESP32 Encoder GUI.
This script ensures all dependencies are available and starts the application.
"""
import sys
import subprocess

def check_requirements():
    """Check if required packages are installed."""
    required = ['pandas', 'serial', 'matplotlib']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Please install with: pip install -r requirements.txt")
        return False
    return True

def main():
    """Main launcher function."""
    print("ESP32 Encoder GUI Launcher")
    print("=" * 30)
    
    if not check_requirements():
        sys.exit(1)
    
    print("Starting GUI application...")
    try:
        from encoder_gui_modular import EncoderGUI
        app = EncoderGUI()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
