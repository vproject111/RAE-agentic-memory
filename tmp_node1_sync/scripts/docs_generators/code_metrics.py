#!/usr/bin/env python3
"""
Code Metrics Generator
Generates code complexity and quality metrics.
"""

import subprocess
from datetime import datetime
from pathlib import Path


def run_command(cmd):
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def generate_code_metrics():
    """
    Generate code metrics documentation.

    Exports:
    - docs/.auto-generated/metrics/complexity.md
    - docs/.auto-generated/metrics/dependencies.md
    """
    output_dir = Path("docs/.auto-generated/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Count lines of code
    py_files = len(list(Path("apps").rglob("*.py")))
    py_lines = run_command(
        "find apps -name '*.py' -exec wc -l {} + | tail -1 | awk '{print $1}'"
    )

    # TODO: Add radon for cyclomatic complexity
    # TODO: Add lizard for code analysis

    complexity_md = f"""# Code Complexity Metrics

**Auto-Generated** from static analysis tools

**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

| Metric | Value |
|--------|-------|
| **Python Files** | {py_files} |
| **Lines of Code** | {py_lines if py_lines else "N/A"} |
| **Test Files** | {len(list(Path("apps").rglob("test_*.py")))} |
| **Average Complexity** | To be implemented (radon) |

## Complexity by Module

To be implemented:
- Cyclomatic complexity (radon)
- Maintainability index
- Halstead metrics
- Code duplication (pylint)

## Installation

To generate full metrics, install:
```bash
pip install radon lizard
```

---

**Note:** Full metrics generation will be implemented in future iteration.
"""

    complexity_path = output_dir / "complexity.md"
    with open(complexity_path, "w") as f:
        f.write(complexity_md)

    # Dependencies
    dependencies_md = f"""# Dependencies Overview

**Auto-Generated** from requirements files

**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Core Dependencies

See `apps/memory_api/requirements.txt` for complete list.

### Key Libraries
- **FastAPI**: Web framework
- **PostgreSQL/asyncpg**: Database
- **Qdrant**: Vector store
- **Redis**: Cache
- **LangChain**: LLM integration

## Development Dependencies

See `requirements-dev.txt`.

---

**Note:** Dependency graph visualization will be added in future iteration.
"""

    deps_path = output_dir / "dependencies.md"
    with open(deps_path, "w") as f:
        f.write(dependencies_md)

    print(f"✅ Generated code metrics in {output_dir}")


if __name__ == "__main__":
    generate_code_metrics()
