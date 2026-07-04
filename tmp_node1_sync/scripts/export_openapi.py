#!/usr/bin/env python3
"""
Export OpenAPI specification from FastAPI app.

Usage:
    python scripts/export_openapi.py --output docs/.auto-generated/api/openapi.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add apps to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def export_openapi_spec(output_path):
    """Export OpenAPI spec from FastAPI app."""
    try:
        from apps.memory_api.main import app

        openapi_schema = app.openapi()

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(openapi_schema, f, indent=2)

        print(f"✅ Exported OpenAPI spec: {output_path}")
        print(f"   Title: {openapi_schema['info']['title']}")
        print(f"   Version: {openapi_schema['info']['version']}")
        print(f"   Paths: {len(openapi_schema['paths'])}")

    except Exception as e:
        print(f"❌ Error exporting OpenAPI spec: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Export OpenAPI specification")
    parser.add_argument(
        "--output",
        default="docs/.auto-generated/api/openapi.json",
        help="Output file path",
    )

    args = parser.parse_args()

    export_openapi_spec(args.output)


if __name__ == "__main__":
    main()
