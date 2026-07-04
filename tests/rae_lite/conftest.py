import sys
from pathlib import Path

# Add rae-windows to sys.path so we can import rae_lite
rae_windows_path = Path(__file__).parent.parent.parent / "rae-windows"
if rae_windows_path.exists() and str(rae_windows_path) not in sys.path:
    sys.path.insert(0, str(rae_windows_path))
