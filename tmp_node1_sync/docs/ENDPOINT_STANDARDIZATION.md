# Endpoint Reference Standardization

**Status**: In Progress
**Last Updated**: 2025-12-04

## Purpose

Ensure all documentation uses consistent, accurate endpoint paths matching the actual API implementation.

---

## Standard Endpoint Format

### Correct Format

✅ **Use actual endpoint paths from code**:
```
POST /v1/memory/store
POST /v1/search/hybrid
GET /v1/triggers/list
```

### Incorrect Formats to Avoid

❌ **Don't use old/non-existent paths**:
```
POST /memory/add          # OLD - doesn't exist
POST /memories/create     # WRONG - should be /memory/store
GET /trigger/list         # WRONG - missing plural
```

---

## Endpoint Reference

All endpoints are documented in [API_INDEX.md](reference/api/API_INDEX.md).

### Quick Reference by Module

| Module | Prefix | Example |
|--------|--------|---------|
| Memory Core | `/v1/memory/*` | `/v1/memory/store` |
| Agent | `/v1/agent/*` | `/v1/agent/execute` |
| Knowledge Graph | `/v1/graph/*` | `/v1/graph/extract` |
| Event Triggers | `/v1/triggers/*` | `/v1/triggers/create` |
| Hybrid Search | `/v1/search/*` | `/v1/search/hybrid` |
| Reflections | `/v1/reflections/*` | `/v1/reflections/generate` |
| Graph Enhanced | `/v1/graph-management/*` | `/v1/graph-management/nodes` |
| Evaluation | `/v1/evaluation/*` | `/v1/evaluation/search` |
| Dashboard | `/v1/dashboard/*` | `/v1/dashboard/metrics` |
| Compliance | `/v1/compliance/*` | `/v1/compliance/approvals` |
| Governance | `/v1/governance/*` | `/v1/governance/overview` |

---

## Verification Process

### 1. Check Against Source Code

```bash
# Find all router definitions
rg "@router\.(get|post|put|delete|patch)" apps/memory_api/ -A 1

# Find all API prefixes
rg "APIRouter\(prefix=" apps/memory_api/
```

### 2. Compare with Documentation

```bash
# Find all endpoint references in docs
rg "POST|GET|PUT|DELETE /v1/" docs/ -g "*.md" > endpoint_refs.txt

# Check for old patterns
rg "/memory/add|/memories/create" docs/ -g "*.md"
```

### 3. Validate Against OpenAPI

```bash
# Start API
docker compose up memory-api

# Fetch OpenAPI spec
curl http://localhost:8000/openapi.json | jq '.paths | keys[]' > actual_endpoints.txt

# Compare with docs
diff endpoint_refs.txt actual_endpoints.txt
```

---

## Known Inconsistencies (To Fix)

### API_COOKBOOK.md

**Status**: ⚠️ Contains some old endpoint names

**Issues**:
- Some examples use `/memories/create` instead of `/memory/store`
- Need to verify all curl examples

**Action**: Audit and update all examples

### rest-api.md

**Status**: ⚠️ May contain outdated examples

**Action**: Cross-reference with API_INDEX.md

---

## Automated Validation Script

```python
#!/usr/bin/env python3
"""
Validate endpoint references in documentation match actual API
"""

import re
import requests
from pathlib import Path

def get_actual_endpoints():
    """Fetch actual endpoints from running API"""
    response = requests.get('http://localhost:8000/openapi.json')
    spec = response.json()
    return set(spec['paths'].keys())

def find_doc_endpoints(docs_dir='docs'):
    """Find all endpoint references in documentation"""
    endpoint_pattern = r'(GET|POST|PUT|DELETE|PATCH)\s+(/v1/[^\s\n]+)'
    doc_endpoints = {}

    for md_file in Path(docs_dir).rglob('*.md'):
        with open(md_file, 'r') as f:
            content = f.read()
            matches = re.findall(endpoint_pattern, content)

            for method, path in matches:
                if path not in doc_endpoints:
                    doc_endpoints[path] = []
                doc_endpoints[path].append((str(md_file), method))

    return doc_endpoints

def validate():
    """Compare documented vs actual endpoints"""
    print("Fetching actual endpoints from API...")
    actual = get_actual_endpoints()

    print(f"Found {len(actual)} actual endpoints\n")

    print("Scanning documentation...")
    documented = find_doc_endpoints()

    print(f"Found {len(documented)} unique endpoints in docs\n")

    # Find mismatches
    doc_only = set(documented.keys()) - actual
    if doc_only:
        print("⚠️  Endpoints in docs but not in API:")
        for endpoint in sorted(doc_only):
            print(f"  {endpoint}")
            for file, method in documented[endpoint]:
                print(f"    → {file} ({method})")
        print()

    # Find undocumented
    api_only = actual - set(documented.keys())
    if api_only:
        print("⚠️  Endpoints in API but not documented:")
        for endpoint in sorted(api_only):
            print(f"  {endpoint}")
        print()

    if not doc_only and not api_only:
        print("✅ All endpoints match!")

if __name__ == '__main__':
    validate()
```

**Usage**:
```bash
# Ensure API is running
docker compose up memory-api

# Run validation
python scripts/validate_endpoints.py
```

---

## Standardization Checklist

When updating documentation:

- [ ] Use actual endpoint paths from API_INDEX.md
- [ ] Include HTTP method (GET, POST, etc.)
- [ ] Include `/v1/` prefix
- [ ] Match plurality (e.g., `/triggers/` not `/trigger/`)
- [ ] Verify against OpenAPI spec
- [ ] Test curl examples
- [ ] Update all related examples

---

## Example: Correcting Documentation

### Before (Incorrect)

```markdown
## Create Memory

```bash
curl -X POST http://localhost:8000/memories/create \
  -d '{"content": "..."}'
```
```

### After (Correct)

```markdown
## Store Memory

```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "content": "...",
    "layer": "episodic"
  }'
```
```

---

## Quick Fix Guide

### 1. Find Inconsistent References

```bash
# Find old patterns
rg "/memory/add|/memories/" docs/ -g "*.md" -l

# Find references without /v1/ prefix
rg "POST /(memory|graph|triggers)" docs/ -g "*.md" -l
```

### 2. Batch Update

```bash
# Example: Replace old pattern
find docs/ -name "*.md" -exec sed -i 's|/memories/create|/v1/memory/store|g' {} \;

# Verify changes
git diff docs/
```

### 3. Test Examples

```bash
# Extract curl commands from doc
rg "^curl" docs/guides/enterprise/EVENT_TRIGGERS_GUIDE.md > test_commands.sh

# Make executable
chmod +x test_commands.sh

# Test (with API running)
bash test_commands.sh
```

---

## Maintenance

### On New Endpoint Addition

1. Add to code with proper prefix
2. Update API_INDEX.md
3. Add examples to relevant guides
4. Run validation script
5. Update CHANGELOG.md

### On Endpoint Deprecation

1. Mark as deprecated in OpenAPI docstring
2. Add deprecation notice to docs
3. Provide migration path
4. Update all examples to new endpoint

---

## Resources

- **Source of Truth**: [API_INDEX.md](reference/api/API_INDEX.md)
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Swagger UI**: http://localhost:8000/docs
- **Code Definitions**: `apps/memory_api/routes/*.py`

---

## Status Tracking

| File | Status | Last Checked | Issues |
|------|--------|--------------|--------|
| API_INDEX.md | ✅ Complete | 2025-12-04 | None |
| API_AUDIT_REPORT.md | ✅ Complete | 2025-12-04 | None |
| EVENT_TRIGGERS_GUIDE.md | ✅ Verified | 2025-12-04 | None |
| GRAPH_ENHANCED_GUIDE.md | ✅ Verified | 2025-12-04 | None |
| COMPLIANCE_GUIDE.md | ✅ Verified | 2025-12-04 | None |
| API_COOKBOOK.md | ⚠️ Needs Audit | - | Possible old refs |
| rest-api.md | ⚠️ Needs Audit | - | Possible old refs |

---

**Next Actions**:
1. Audit API_COOKBOOK.md for old endpoint references
2. Verify rest-api.md against API_INDEX.md
3. Run automated validation script
4. Update any mismatched references

---

**Last Updated**: 2025-12-04
