# RAE – Path Portability Refactor Specification [DEPRECATED]

> **NOTE:** The `core/paths.py` module has been removed in favor of `rae-core` logic or local path resolution. This document remains for historical context.

## Goal
Refactor the entire RAE codebase so that it does not contain any hardcoded absolute filesystem paths, especially paths like:
`/home/grzegorz-lesniowski/cloud/RAE-agentic-memory`

After this refactor, the project must run correctly on any machine, in Docker, and in CI, without modifying the source code.

## Core Rule (Non-Negotiable)
No absolute filesystem paths are allowed anywhere in the codebase.
All paths must be:
*   relative to a single `PROJECT_ROOT`
*   resolved dynamically at runtime
*   configurable via environment variables

## Architecture

### 1. Single Source of Truth for Paths
Module: `core/paths.py`

Responsibilities:
*   Determine `PROJECT_ROOT`
*   Define all logical directories used by the system
*   Ensure directories exist at runtime

Implementation Pattern:
```python
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_ROOT = Path(__file__).resolve().parents[1] # Adjust parents count based on file location

PROJECT_ROOT = Path(
    os.getenv("RAE_PROJECT_ROOT", DEFAULT_ROOT)
).resolve()

DATA_DIR = PROJECT_ROOT / "data"
MEMORY_DIR = DATA_DIR / "memory"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"

# Ensure directories exist
for directory in (DATA_DIR, MEMORY_DIR, CACHE_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
```

### 2. Mandatory Usage Across Codebase
All filesystem access MUST:
*   import paths from `core.paths`
*   use `pathlib.Path`
*   avoid string concatenation for paths

❌ **Forbidden:**
```python
"/home/username/project/data/file.json"
os.path.join("/home", "user", ...)
```

✅ **Required:**
```python
from core.paths import MEMORY_DIR

file_path = MEMORY_DIR / "episodic.json"
```

### 3. Environment Variable Support
Supported variable: `RAE_PROJECT_ROOT`

Enables:
*   Docker compatibility
*   CI compatibility
*   Local overrides without code changes

## Docker Compatibility Requirement
The code MUST work correctly with:
```yaml
volumes:
  - .:/app
environment:
  - RAE_PROJECT_ROOT=/app
```
No code changes should be required for Docker execution.
