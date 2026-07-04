# Documentation Templates

This directory contains templates for creating consistent documentation across the RAE project.

## Available Templates

### 1. Guide Template (`guide_template.md`)

**Use for:** User-facing tutorials and how-to guides

**Target audiences:**
- Developers learning the system
- Administrators deploying RAE
- Researchers using the evaluation suite

**Structure:**
- Overview and prerequisites
- Step-by-step instructions
- Examples and verification
- Troubleshooting

**Example usage:**
```bash
cp docs/templates/guide_template.md docs/guides/developers/my-new-guide.md
# Edit the file, replacing [placeholders]
```

### 2. Reference Template (`reference_template.md`)

**Use for:** Technical API documentation and component references

**Target audiences:**
- Developers integrating with RAE
- Contributors extending the codebase

**Structure:**
- API reference with parameters and return types
- Configuration options
- Usage examples
- Performance and security considerations

**Example usage:**
```bash
cp docs/templates/reference_template.md docs/reference/services/my-service.md
# Document your service/component
```

### 3. Architecture Template (`architecture_template.md`)

**Use for:** System design and architecture documentation

**Target audiences:**
- Architects planning integrations
- Engineers understanding system design
- Operations teams deploying at scale

**Structure:**
- Context and goals
- High-level and detailed design
- Technology stack and trade-offs
- Scalability, security, reliability

**Example usage:**
```bash
cp docs/templates/architecture_template.md docs/reference/architecture/my-subsystem.md
# Document your architecture decisions
```

## Quick Start

### Creating a New Guide

1. Choose the appropriate template
2. Copy to the target location:
   ```bash
   cp docs/templates/guide_template.md docs/guides/[audience]/[topic].md
   ```
3. Replace all `[placeholders]` with actual content
4. Fill in all sections (remove N/A sections if not applicable)
5. Update `[audience]/INDEX.md` to include your new guide

### Creating a New Reference Document

1. Copy the reference template:
   ```bash
   cp docs/templates/reference_template.md docs/reference/[category]/[component].md
   ```
2. Document your component/API thoroughly
3. Include code examples for all public APIs
4. Add links to related documentation

### Creating Architecture Documentation

1. Copy the architecture template:
   ```bash
   cp docs/templates/architecture_template.md docs/reference/architecture/[subsystem].md
   ```
2. Document high-level design first
3. Add detailed design and diagrams
4. Include trade-offs and decision rationale
5. Review with team before finalizing

## Template Conventions

### Placeholders

Templates use `[Square Brackets]` for placeholders that must be replaced:

- `[Component Name]` - Replace with actual component name
- `[Description]` - Replace with actual description
- `[YYYY-MM-DD]` - Replace with actual date

### Optional Sections

If a section doesn't apply to your documentation:

```markdown
## Section Title

N/A - [Brief explanation why this doesn't apply]
```

Or simply remove the section if it's clearly not relevant.

### Code Examples

Always include working code examples:

```python
# ✅ GOOD - Complete, runnable example
from rae_memory_sdk import RAEClient

client = RAEClient(api_key="your-key")
result = client.memories.create(
    content="Example memory",
    metadata={"source": "docs"}
)
print(result.id)
```

```python
# ❌ BAD - Incomplete example
client.memories.create(...)
```

### Audience Tags

Always specify the target audience:

- **Developers** - Software engineers integrating with RAE
- **Administracja** - Government agencies and administrators (Polish content)
- **Enterprise** - Large-scale production deployments
- **Usługi** - Professional services (lawyers, auditors, accountants)
- **Researchers** - Academic and research use cases

## Style Guide

### Language

- **Primary language:** English
- **Polish content:** Only for Administracja and Usługi audiences
- **Tone:** Professional, clear, concise

### Formatting

- **Headers:** Use sentence case ("Getting started" not "Getting Started")
- **Code blocks:** Always specify language (```python, not ```)
- **Lists:** Use `-` for unordered, `1.` for ordered
- **Emphasis:** Use `**bold**` for UI elements, `*italic*` for emphasis

### Links

- **Internal links:** Use relative paths: `[CONTRIBUTING](../../CONTRIBUTING.md)`
- **External links:** Use full URLs: `[FastAPI](https://fastapi.tiangolo.com)`
- **Code references:** Include line numbers: `apps/memory_api/services/memory_service.py:123`

## Validation

Before committing new documentation:

1. **Check formatting:**
   ```bash
   # Install markdownlint if not already installed
   npm install -g markdownlint-cli

   # Validate your doc
   markdownlint docs/guides/developers/my-new-guide.md
   ```

2. **Verify links:**
   ```bash
   # Run doc validation (when implemented in Iteration 3)
   make docs-validate
   ```

3. **Test code examples:**
   - All code examples must be tested and working
   - Include expected output
   - Use real (but safe) example data

## Integration with Auto-Documentation

### Auto-Generated vs Manual

**Auto-generated** (DO NOT edit manually):
- `docs/.auto-generated/api/` - OpenAPI specs
- `docs/.auto-generated/metrics/` - Code metrics
- `docs/.auto-generated/status/` - Status files
- `CHANGELOG.md`, `STATUS.md`, `TODO.md`

**Manual** (Use templates):
- `docs/guides/` - User guides
- `docs/reference/` - Technical documentation
- `docs/compliance/` - Compliance documentation

### Adding Documentation to CI

If your documentation should be auto-generated:

1. Create generator script in `scripts/docs_generators/`
2. Add to `scripts/docs_automator.py`
3. Update `.github/workflows/docs.yml`
4. See `CONTRIBUTING_DOCS.md` for details

## Examples

### Good Documentation Examples

- `docs/guides/developers/quickstart.md` - Clear, step-by-step guide
- `docs/reference/architecture/hybrid-search.md` - Thorough architecture doc
- `docs/compliance/ISO-42001.md` - Complete compliance mapping

### Template Usage Examples

```bash
# Example 1: New developer guide
cp docs/templates/guide_template.md docs/guides/developers/vector-search-guide.md
# Edit file, test examples, commit

# Example 2: New service reference
cp docs/templates/reference_template.md docs/reference/services/llm-orchestrator.md
# Document API, add examples, commit

# Example 3: New architecture doc
cp docs/templates/architecture_template.md docs/reference/architecture/multi-tenancy.md
# Design doc, review with team, commit
```

## Questions?

- **Documentation structure:** See `DOCUMENTATION_INVENTORY.md`
- **Contributing docs:** See `CONTRIBUTING_DOCS.md`
- **Automation:** See `CRITICAL_AGENT_RULES.md` RULE #8

---

**Maintained By:** Documentation Team
**Last Updated:** 2025-12-06
