#!/usr/bin/env python3
"""
API Documentation Generator
Exports OpenAPI spec and generates endpoint list.
"""

import json
from pathlib import Path


def generate_api_docs():
    """
    Generate API documentation from OpenAPI spec.

    Exports:
    - docs/.auto-generated/api/openapi.json
    - docs/.auto-generated/api/endpoints.md
    """
    output_dir = Path("docs/.auto-generated/api")
    output_dir.mkdir(parents=True, exist_ok=True)

    # TODO: Implement FastAPI OpenAPI export
    # This requires running the app or importing it
    # For now, create placeholder

    placeholder = {
        "openapi": "3.0.0",
        "info": {
            "title": "RAE Memory API",
            "version": "2.1.1",
            "description": "Reflective Agentic Memory Engine API",
        },
        "note": "Auto-generated from FastAPI app - implementation pending",
    }

    # Write OpenAPI JSON
    openapi_path = output_dir / "openapi.json"
    with open(openapi_path, "w") as f:
        json.dump(placeholder, f, indent=2)

    # Generate endpoints markdown
    endpoints_md = """# API Endpoints Reference

**Auto-Generated** from OpenAPI specification

**Last Updated:** {timestamp}
**API Version:** 2.1.1

## Core Memory Endpoints

### POST /v1/memories/create
Create a new memory entry.

**Request Body:**
```json
{{
  "content": "string",
  "layer": "episodic|semantic|ltm|rm",
  "tags": ["string"],
  "metadata": {{}}
}}
```

### POST /v1/memory/query
Query memories with hybrid search.

### POST /v1/memory/reflection
Generate reflection from memories.

## GraphRAG Endpoints

### POST /v1/graph/entities
Extract entities from text.

### GET /v1/graph/traverse
Traverse knowledge graph.

## Enterprise Endpoints

### POST /v1/triggers/create
Create event trigger rule.

### GET /v1/cost/usage
Get cost tracking data.

---

**Note:** Full API documentation will be auto-generated from FastAPI app in future iteration.
See interactive docs at: http://localhost:8000/docs
""".format(
        timestamp="2025-12-06"
    )

    endpoints_path = output_dir / "endpoints.md"
    with open(endpoints_path, "w") as f:
        f.write(endpoints_md)

    print(f"✅ Generated API docs in {output_dir}")


if __name__ == "__main__":
    generate_api_docs()
