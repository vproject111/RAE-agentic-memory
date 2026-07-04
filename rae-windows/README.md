# RAE-Windows (Universal Node)

This directory contains the source code and build tools for the Windows Desktop version of RAE.

**Codename:** RAE-Lite (Universal Node)
**Target:** Windows 10/11 (Portable .exe)

## Structure

- **`rae_lite/`**: The Python source code (FastAPI, Service, Ingestor).
- **`build_distribution.py`**: Script to build the `.exe` file.
- **`requirements-lite.txt`**: Python dependencies.

## How to Build (On Windows)

1.  **Install Python 3.11+**
2.  **Install Dependencies:**
    ```cmd
    pip install -r requirements-lite.txt
    pip install pyinstaller
    ```
3.  **Run Build Script:**
    ```cmd
    python build_distribution.py
    ```
4.  **Output:**
    The executable will be in `dist/RAE-Lite/RAE-Lite.exe`.

## Features

- **Universal Ingestor:** PDF, DOCX, ODT, TXT, Logs.
- **Email Connector:** Imports `.eml` files as Restricted/Confidential.
- **Math Layer:** Uses `rae-core` for advanced ranking (Recency, Importance, Resonance).
- **Offline First:** Uses SQLite and Local Vectors (no Docker required).