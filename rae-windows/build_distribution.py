"""
Build Script for RAE-Lite (OneDir Mode).
Run this on the target OS (Windows) to generate the folder.
"""
import PyInstaller.__main__
import os
import shutil
from pathlib import Path

# Clean previous build
if Path("dist").exists():
    shutil.rmtree("dist")
if Path("build").exists():
    shutil.rmtree("build")

# Paths
current_dir = Path(__file__).parent.resolve()
project_root = current_dir.parent

# Define inclusions
# 1. Static UI files
add_data = [
    (str(current_dir / "rae_lite" / "ui" / "static"), "rae_lite/ui/static")
]

# 2. Hidden imports (FastAPI/Uvicorn/SQLAlchemy/Pydantic often need help)
hidden_imports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "email.mime.multipart",
    "email.mime.text",
    "email.mime.base",
    "watchdog.observers.read_directory_changes",
    "watchdog.observers.winapi",
    "sqlite3",
    "rae_core",
    "rae_adapters",
    "rae_lite"
]

print("📦 Building RAE-Lite (OneDir)...")

PyInstaller.__main__.run([
    str(current_dir / 'rae_lite' / 'main_exe.py'), # CORRECTED PATH
    '--name=RAE-Lite',                       # Name of executable
    '--onedir',                              # Directory based (faster startup than --onefile)
    '--clean',                               # Clean cache
    '--noconfirm',                           # Overwrite output
    '--console',                             # Keep console for debug logs (remove for silent)
    # '--windowed',                          # Uncomment for production (hides console)
    
    # Python Paths (Crucial for rae-core resolution)
    f'--paths={project_root}',
    f'--paths={project_root}/rae-core',
    f'--paths={project_root}/rae-lite',
    
    # Data & Imports
    *[f'--add-data={src}{os.pathsep}{dest}' for src, dest in add_data],
    *[f'--hidden-import={mod}' for mod in hidden_imports],
])

print("✅ Build Complete.")
print(f"📂 Output: {current_dir / 'dist' / 'RAE-Lite'}")
print("👉 Run 'RAE-Lite.exe' inside that folder.")
