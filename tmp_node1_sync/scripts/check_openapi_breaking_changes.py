#!/usr/bin/env python3
"""
Check for breaking changes in OpenAPI schema.

Breaking changes include:
- Removed endpoints
- Removed required fields in responses
- Changed field types in responses
- New required fields in requests (unless with defaults)

Non-breaking changes (allowed):
- New endpoints
- New optional fields
- Deprecated fields (still present)

Usage:
    python scripts/check_openapi_breaking_changes.py old_schema.json new_schema.json

Exit codes:
    0: No breaking changes
    1: Breaking changes detected
    2: Error reading schemas
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_schema(path: str) -> Dict:
    """Load OpenAPI schema from JSON file"""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading schema from {path}: {e}")
        sys.exit(2)


def extract_endpoints(schema: Dict) -> Dict[str, Dict]:
    """Extract all endpoints from OpenAPI schema"""
    endpoints = {}
    paths = schema.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                endpoint_key = f"{method.upper()} {path}"
                endpoints[endpoint_key] = details

    return endpoints


def extract_response_schema(endpoint: Dict, status_code: str = "200") -> Dict:
    """Extract response schema from endpoint"""
    responses = endpoint.get("responses", {})
    response = responses.get(status_code, {})

    content = response.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})

    return schema


def extract_request_schema(endpoint: Dict) -> Dict:
    """Extract request body schema from endpoint"""
    request_body = endpoint.get("requestBody", {})
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})

    return schema


def get_schema_properties(schema: Dict) -> Dict[str, Any]:
    """Extract properties and their types from schema"""
    properties = {}

    # Handle direct properties
    if "properties" in schema:
        for prop, prop_schema in schema["properties"].items():
            properties[prop] = {
                "type": prop_schema.get("type", "unknown"),
                "required": prop in schema.get("required", []),
            }

    # Handle $ref (simplified - would need full resolution in production)
    elif "$ref" in schema:
        # For now, just note it's a reference
        properties["_ref"] = schema["$ref"]

    return properties


def check_endpoint_changes(
    old_endpoints: Dict, new_endpoints: Dict
) -> Tuple[List[str], List[str]]:
    """Check for added/removed endpoints"""
    old_keys = set(old_endpoints.keys())
    new_keys = set(new_endpoints.keys())

    removed = list(old_keys - new_keys)
    added = list(new_keys - old_keys)

    return removed, added


def check_response_changes(
    old_endpoint: Dict, new_endpoint: Dict, endpoint_name: str
) -> List[str]:
    """Check for breaking changes in response schema"""
    violations = []

    old_schema = extract_response_schema(old_endpoint)
    new_schema = extract_response_schema(new_endpoint)

    old_props = get_schema_properties(old_schema)
    new_props = get_schema_properties(new_schema)

    # Check for removed fields
    old_fields = set(old_props.keys())
    new_fields = set(new_props.keys())

    removed_fields = old_fields - new_fields
    if removed_fields:
        for field in removed_fields:
            violations.append(
                f"{endpoint_name}: Response field '{field}' was removed (BREAKING)"
            )

    # Check for type changes
    for field in old_fields & new_fields:
        old_type = old_props[field].get("type")
        new_type = new_props[field].get("type")

        if old_type != new_type:
            violations.append(
                f"{endpoint_name}: Response field '{field}' type changed "
                f"from {old_type} to {new_type} (BREAKING)"
            )

    return violations


def check_request_changes(
    old_endpoint: Dict, new_endpoint: Dict, endpoint_name: str
) -> List[str]:
    """Check for breaking changes in request schema"""
    violations = []

    old_schema = extract_request_schema(old_endpoint)
    new_schema = extract_request_schema(new_endpoint)

    old_props = get_schema_properties(old_schema)
    new_props = get_schema_properties(new_schema)

    # Check for new required fields (breaking for clients)
    for field, props in new_props.items():
        if props.get("required") and field not in old_props:
            violations.append(
                f"{endpoint_name}: New required field '{field}' in request (BREAKING)"
            )

    return violations


def main():
    if len(sys.argv) != 3:
        print("Usage: python check_openapi_breaking_changes.py old.json new.json")
        sys.exit(2)

    old_schema_path = sys.argv[1]
    new_schema_path = sys.argv[2]

    # Handle case where old schema doesn't exist (first run)
    if not Path(old_schema_path).exists():
        print("ℹ️  No previous schema found. Skipping breaking change check.")
        sys.exit(0)

    print("📋 Checking for breaking changes in OpenAPI schema...")
    print()

    old_schema = load_schema(old_schema_path)
    new_schema = load_schema(new_schema_path)

    old_endpoints = extract_endpoints(old_schema)
    new_endpoints = extract_endpoints(new_schema)

    violations = []

    # 1. Check for removed endpoints
    removed_endpoints, added_endpoints = check_endpoint_changes(
        old_endpoints, new_endpoints
    )

    if removed_endpoints:
        print("❌ Removed endpoints (BREAKING):")
        for endpoint in removed_endpoints:
            print(f"   - {endpoint}")
            violations.append(f"Endpoint removed: {endpoint}")
        print()

    if added_endpoints:
        print("✅ New endpoints (non-breaking):")
        for endpoint in added_endpoints:
            print(f"   + {endpoint}")
        print()

    # 2. Check for breaking changes in existing endpoints
    common_endpoints = set(old_endpoints.keys()) & set(new_endpoints.keys())

    for endpoint_name in common_endpoints:
        old_endpoint = old_endpoints[endpoint_name]
        new_endpoint = new_endpoints[endpoint_name]

        # Check response changes
        response_violations = check_response_changes(
            old_endpoint, new_endpoint, endpoint_name
        )
        violations.extend(response_violations)

        # Check request changes
        request_violations = check_request_changes(
            old_endpoint, new_endpoint, endpoint_name
        )
        violations.extend(request_violations)

    # 3. Report results
    if violations:
        print("❌ BREAKING CHANGES DETECTED:")
        print()
        for violation in violations:
            print(f"   - {violation}")
        print()
        print(f"Total breaking changes: {len(violations)}")
        print()
        print("⚠️  These changes will break existing clients!")
        print("   Consider:")
        print("   1. Bumping major version (v1 -> v2)")
        print("   2. Deprecating instead of removing")
        print("   3. Providing migration guide")
        sys.exit(1)
    else:
        print("✅ No breaking changes detected!")
        print()
        if added_endpoints:
            print(f"   {len(added_endpoints)} new endpoints added (non-breaking)")
        print("   All existing endpoints maintain backward compatibility")
        sys.exit(0)


if __name__ == "__main__":
    main()
