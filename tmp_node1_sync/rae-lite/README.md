# RAE-Lite

Local-first AI Memory Desktop App.

## Features

- **Local-first**: All data stored locally in SQLite
- **System tray**: Runs in background with tray icon
- **HTTP API**: Local FastAPI server on http://localhost:8765
- **Zero dependencies**: No Docker, no PostgreSQL, no cloud
- **Powered by RAE-Core**: 4-layer memory architecture

## Installation

```bash
pip install -e .
```

## Usage

Run from command line:

```bash
rae-lite
```

Or run the Python module:

```bash
python -m rae_lite.main
```

## API Endpoints

Once running, access the API at:

- Dashboard: http://localhost:8765/docs
- Health: http://localhost:8765/health
- Store memory: POST http://localhost:8765/memories
- Query memories: POST http://localhost:8765/memories/query
- Statistics: GET http://localhost:8765/statistics

## Data Storage

All data is stored in:
- Linux/Mac: `~/.rae-lite/data/`
- Windows: `C:\Users\<username>\.rae-lite\data\`

## System Tray

Right-click the tray icon to:
- Open Dashboard (in browser)
- Open Data Folder
- View About
- Quit

## Development

Install in development mode:

```bash
pip install -e ".[dev]"
```

## Building Standalone Executable

See Phase 3 Week 9 instructions for PyInstaller build.

## License

Same as RAE-agentic-memory project.
