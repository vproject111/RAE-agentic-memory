"""
Entry point for RAE-Lite Executable.
Starts the FastAPI server and opens the browser.
"""
import os
import sys
import webbrowser
import uvicorn
import multiprocessing
from pathlib import Path

# Add project root to sys.path to ensure imports work in dev mode
# In frozen mode (PyInstaller), sys.path is handled differently
if getattr(sys, 'frozen', False):
    # Running in a bundle
    base_dir = sys._MEIPASS
else:
    # Running in a normal Python environment
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(base_dir, "..", "..")) # project root
    sys.path.insert(0, os.path.join(base_dir, "..", "..", "rae-core"))
    sys.path.insert(0, os.path.join(base_dir, "..", "..", "rae-lite"))

from rae_lite.server_enhanced import app

import socket

def find_free_port(start_port=8000, max_attempts=100):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Try to bind (more reliable than connect_ex for finding free ports)
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free ports found in range {start_port}-{start_port + max_attempts}")

def main():
    # PyInstaller multiprocessing fix for Windows
    multiprocessing.freeze_support()
    
    host = "127.0.0.1"
    try:
        port = find_free_port()
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return

    print(f"🚀 RAE-Lite Starting on http://{host}:{port}")
    print("📂 Mode: OneDir (Portable)")
    
    # Open browser after a slight delay or immediately
    # Note: simple open here, uvicorn blocks.
    webbrowser.open(f"http://{host}:{port}")
    
    # Run Server
    # We pass 'app' directly. In some frozen configs, string import "rae_lite..." is safer
    # but direct object works if imports are resolved.
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
