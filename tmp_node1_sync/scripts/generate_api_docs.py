#!/usr/bin/env python3
"""
Generate API documentation from FastAPI app.

This script:
1. Loads the FastAPI application
2. Exports OpenAPI JSON spec
3. Generates markdown endpoint list
4. Saves to docs/.auto-generated/api/

Usage:
    python scripts/generate_api_docs.py

For pre-commit hook (silent mode):
    python scripts/generate_api_docs.py --quiet
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_openapi_spec(app, output_path: Path):
    """Generate OpenAPI JSON specification."""
    openapi_schema = app.openapi()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    return openapi_schema


def generate_endpoints_markdown(openapi_schema: dict, output_path: Path):
    """Generate markdown file with endpoint list."""

    lines = [
        "# API Endpoints",
        "",
        "**Generated:** Auto-generated from OpenAPI spec",
        f"**API Version:** {openapi_schema.get('info', {}).get('version', 'unknown')}",
        "",
        "## Available Endpoints",
        "",
    ]

    paths = openapi_schema.get("paths", {})

    # Group by tags
    endpoints_by_tag = {}

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                tags = details.get("tags", ["Uncategorized"])
                tag = tags[0] if tags else "Uncategorized"

                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []

                endpoints_by_tag[tag].append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                    }
                )

    # Generate markdown
    for tag in sorted(endpoints_by_tag.keys()):
        lines.append(f"### {tag}")
        lines.append("")

        for endpoint in sorted(endpoints_by_tag[tag], key=lambda x: x["path"]):
            lines.append(f"#### `{endpoint['method']}` {endpoint['path']}")
            lines.append("")
            if endpoint["summary"]:
                lines.append(f"**Summary:** {endpoint['summary']}")
                lines.append("")
            if endpoint["description"]:
                lines.append(f"{endpoint['description']}")
                lines.append("")

        lines.append("")

    # Add footer
    lines.extend(
        [
            "---",
            "",
            "**Note:** This file is auto-generated. Do not edit manually.",
            "",
            f"**Total Endpoints:** {sum(len(v) for v in endpoints_by_tag.values())}",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Generate API documentation")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
    args = parser.parse_args()

    try:
        # Import FastAPI app
        from apps.memory_api.main import app

        # Output paths
        api_docs_dir = PROJECT_ROOT / "docs" / ".auto-generated" / "api"
        openapi_path = api_docs_dir / "openapi.json"
        endpoints_path = api_docs_dir / "endpoints.md"

        # Generate OpenAPI spec
        if not args.quiet:
            print("📄 Generating OpenAPI specification...")
        openapi_schema = generate_openapi_spec(app, openapi_path)

        # Generate endpoints markdown
        if not args.quiet:
            print("📝 Generating endpoints documentation...")
        generate_endpoints_markdown(openapi_schema, endpoints_path)

        if not args.quiet:
            print("✅ API docs generated:")
            print(f"   - {openapi_path}")
            print(f"   - {endpoints_path}")

        return 0

    except Exception as e:
        if not args.quiet:
            print(f"❌ Error generating API docs: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
