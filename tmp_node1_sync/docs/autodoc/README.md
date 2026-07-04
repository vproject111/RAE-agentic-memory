# Autodoc System - Documentation Automation

> **Zero-Drift Documentation** - Automatically maintain documentation consistency.

---

## Overview

The Autodoc system ensures RAE documentation stays consistent and up-to-date through:

1. **Doc Fragments** - Reusable documentation snippets
2. **Consistency Checker** - Automated validation
3. **CI Integration** - Automatic checks on every commit

---

## Doc Fragments

### What Are Doc Fragments?

Doc fragments are reusable snippets of documentation that can be **injected into multiple files**. When a fragment is updated, all files using it are automatically synchronized.

### Location

```
docs/autodoc/doc_fragments/
├── memory_layers_overview.md
├── math_layers_summary.md
├── hybrid_search_core.md
└── [more fragments...]
```

### Usage

**In a documentation file**:

```markdown
<!-- RAE_DOC_FRAGMENT:memory_layers_overview -->
```

**This marker will be replaced with the content from**:
```
docs/autodoc/doc_fragments/memory_layers_overview.md
```

### Creating New Fragments

1. Create new file in `docs/autodoc/doc_fragments/`
2. Wrap content with markers:
   ```markdown
   <!-- RAE_DOC_FRAGMENT:fragment_name -->
   [Your content here]
   <!-- END_RAE_DOC_FRAGMENT:fragment_name -->
   ```

3. Use in other docs:
   ```markdown
   <!-- RAE_DOC_FRAGMENT:fragment_name -->
   ```

### Example

**Fragment file** (`doc_fragments/quick_start.md`):
```markdown
<!-- RAE_DOC_FRAGMENT:quick_start -->
## Quick Start

```bash
docker compose up -d
```

Visit http://localhost:8000/docs
<!-- END_RAE_DOC_FRAGMENT:quick_start -->
```

**Using in README.md**:
```markdown
# RAE Project

<!-- RAE_DOC_FRAGMENT:quick_start -->

More content...
```

**After processing, README.md contains**:
```markdown
# RAE Project

## Quick Start

```bash
docker compose up -d
```

Visit http://localhost:8000/docs

More content...
```

---

## Consistency Checker

### Purpose

Automatically detects:
- ✅ Missing doc fragment markers
- ✅ API endpoint mismatches between code and docs
- ✅ Broken internal links
- ✅ Duplicate content (should be fragments)

### Running Manually

```bash
# Check all documentation
python docs/autodoc/autodoc_checker.py

# Check specific files
python docs/autodoc/autodoc_checker.py docs/architecture/MEMORY_LAYERS.md

# Auto-fix issues
python docs/autodoc/autodoc_checker.py --fix
```

### CI Integration

Runs automatically on every pull request:

```yaml
# .github/workflows/docs-check.yml
- name: Validate documentation consistency
  run: python docs/autodoc/autodoc_checker.py
```

**Result**: PR fails if documentation is inconsistent.

---

## How It Works

### 1. Fragment Injection

```python
# Pseudocode
for each .md file in docs/:
    for each <!-- RAE_DOC_FRAGMENT:name --> marker:
        find docs/autodoc/doc_fragments/name.md
        extract content between markers
        replace marker with content
```

### 2. API Consistency Check

```python
# Pseudocode
endpoints_in_code = parse_fastapi_routes()
endpoints_in_docs = parse_api_markdown_files()

if endpoints_in_code != endpoints_in_docs:
    report_mismatch()
```

### 3. Link Validation

```python
# Pseudocode
for each .md file:
    for each [text](path) link:
        if path.startswith(('http', 'https')):
            skip  # External link
        else:
            check_file_exists(resolve_relative_path(path))
            if not exists:
                report_broken_link()
```

---

## Best Practices

### When to Use Fragments

✅ **DO** use fragments for:
- Content repeated in multiple files
- Core concepts (4-layer memory, math layers, etc.)
- Installation instructions
- Common examples

❌ **DON'T** use fragments for:
- File-specific content
- Content that varies by context
- Very short snippets (< 3 lines)

### Fragment Naming

```
lowercase_with_underscores.md

Good: memory_layers_overview.md
Bad: MemoryLayersOverview.md
Bad: memory-layers-overview.md
```

### Fragment Size

- **Ideal**: 10-50 lines
- **Max**: 100 lines
- If larger → split into multiple fragments

---

## Maintenance

### Updating Fragments

1. Edit fragment file directly
2. Run `python docs/autodoc/autodoc_checker.py --fix`
3. All files using the fragment are updated automatically
4. Commit changes

### Adding New Fragment Usage

1. Add marker to target file:
   ```markdown
   <!-- RAE_DOC_FRAGMENT:fragment_name -->
   ```

2. Run checker:
   ```bash
   python docs/autodoc/autodoc_checker.py --fix
   ```

3. Marker is replaced with fragment content

---

## Related Documentation

- **[Style Guide](../STYLE_GUIDE.md)** - Documentation writing standards
- **[Contributing](../../CONTRIBUTING.md)** - How to contribute documentation

---

**Version**: 1.0.0
**Last Updated**: 2025-12-08
**Status**: Production Ready ✅
