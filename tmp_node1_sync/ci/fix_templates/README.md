# Auto-Fix Templates

This directory contains templates and examples for common CI fixes.
These guide the AI agent in generating appropriate fixes.

## Overview

The RAE CI Auto-Healing system uses these templates to provide context
and examples to the LLM when generating fixes. Templates help ensure
consistent, high-quality fixes that follow project conventions.

## Available Templates

| Template | Description | Auto-fixable |
|----------|-------------|--------------|
| `warning_fix.md` | Deprecation warnings, Pydantic migrations | Yes |
| `flaky_fix.md` | Flaky test patterns and solutions | Yes |
| `lint_fix.md` | Linting and formatting issues | Yes |
| `import_fix.md` | Import errors and dependency issues | Yes |

## Template Structure

Each template follows this standard format:

```markdown
# Fix Type: <name>

## Pattern Description
[What this fix addresses]

## Common Causes
- Cause 1
- Cause 2

## Fix Strategy
1. Step 1
2. Step 2

## Examples
### Before
[Bad code]

### After
[Fixed code]

## Verification
[How to verify the fix works]
```

## How Templates Are Used

1. **Failure Analysis**: `analyze_failure.py` classifies the failure type
2. **Template Selection**: Based on the failure type, the appropriate template is selected
3. **Context Building**: The template is combined with failure context
4. **LLM Generation**: The LLM uses the template + context to generate a fix
5. **Validation**: Generated fix is validated before creating a PR

## Adding New Templates

To add a new fix template:

1. Create a new `.md` file in this directory
2. Follow the structure shown above
3. Include at least 2-3 real examples from the project
4. Add common pitfalls to avoid
5. Update the `ci_fix_agent.py` FIX_TEMPLATES dict

### Example Template Addition

```python
# In ci_fix_agent.py
FIX_TEMPLATES = {
    # ... existing templates ...
    "new_fix_type": """Your template here...
Context: {context}
..."""
}
```

## Quality Guidelines

When creating templates:

1. **Be Specific**: Include project-specific patterns and conventions
2. **Show Real Examples**: Use actual code from this repository
3. **Explain Why**: Help the LLM understand the reasoning, not just the fix
4. **Include Verification**: Show how to test that the fix works
5. **Document Exceptions**: Note when a pattern should NOT be auto-fixed

## Integration with AGENT_TESTING_GUIDE.md

All templates should reference `docs/AGENT_TESTING_GUIDE.md` for:
- Test structure conventions
- Fixture usage patterns
- Mocking guidelines
- Performance considerations

## Cost Considerations

Templates should be concise to minimize token usage:
- Keep examples brief but complete
- Avoid unnecessary prose
- Use code blocks efficiently
- Reference external docs rather than duplicating

## Maintenance

Templates should be updated when:
- New patterns emerge from repeated failures
- Project conventions change
- New deprecation warnings appear in dependencies
- CI requirements change
