# Fix Type: Warning

This template addresses Python warnings in the RAE project.
Policy: ZERO WARNINGS (pytest -W error)

## Pattern: Deprecation Warning

### Description
Python or third-party library deprecation warnings that will become errors
in future versions. These must be fixed to maintain forward compatibility.

### Common Causes
- Using deprecated datetime methods (utcnow, utcfromtimestamp)
- Pydantic V1 style configuration in V2
- Deprecated pkg_resources usage
- Old-style string formatting in f-strings

### Before
```python
from datetime import datetime
timestamp = datetime.utcnow()
```

### After
```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)
```

### Verification
```bash
pytest -W error tests/path/to/test.py
```

---

## Pattern: External Library Warning

### Description
Warnings from third-party libraries that cannot be fixed in our code.
These should be filtered with appropriate documentation.

### Fix Strategy
1. Identify the source module generating the warning
2. Add filterwarnings directive to pytest.ini
3. Include comment explaining why and expected resolution

### pytest.ini
```ini
filterwarnings =
    error
    # [EXTERNAL] google-protobuf: deprecated in Python 3.14
    # Tracking: https://github.com/protocolbuffers/protobuf/issues/XXXXX
    ignore::DeprecationWarning:google._upb._message

    # [EXTERNAL] pydantic-settings: will be fixed in v2.x
    ignore::pydantic.warnings.PydanticDeprecatedSince20:pydantic_settings
```

### Verification
```bash
# Run with strict warning check
pytest -W error

# Verify filter is working
pytest --tb=short -v 2>&1 | grep -i warning
```

---

## Pattern: Expected Warning in Test

### Description
Tests that intentionally trigger warnings to verify deprecation notices
work correctly. Use pytest.warns() to capture and assert on warnings.

### Before
```python
def test_deprecated_function():
    # This generates a warning but doesn't verify it
    deprecated_function()
```

### After
```python
import pytest

def test_deprecated_function():
    with pytest.warns(DeprecationWarning, match="deprecated"):
        deprecated_function()
```

### Alternative: Multiple Warnings
```python
import warnings
import pytest

def test_deprecated_function_multiple():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        deprecated_function()

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message)
```

---

## Pattern: Pydantic V2 Migration

### Description
Pydantic V1-style configuration causing PydanticDeprecatedSince20 warnings.

### Before
```python
from pydantic import BaseModel

class MyModel(BaseModel):
    name: str

    class Config:
        extra = "forbid"
        validate_assignment = True
```

### After
```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    name: str
```

### Pydantic Field Changes
```python
# Before
from pydantic import Field
name: str = Field(..., regex=r"^[a-z]+$")

# After
from pydantic import Field
name: str = Field(..., pattern=r"^[a-z]+$")
```

---

## Pattern: ResourceWarning

### Description
Unclosed files, connections, or other resources. Usually indicates
missing context managers or cleanup in tests.

### Before
```python
def test_read_file():
    f = open("test.txt")
    content = f.read()
    assert "expected" in content
    # File never closed!
```

### After
```python
def test_read_file():
    with open("test.txt") as f:
        content = f.read()
    assert "expected" in content
```

### For HTTP Clients
```python
# Before
def test_api_call():
    response = httpx.get("https://api.example.com")
    assert response.status_code == 200

# After
def test_api_call():
    with httpx.Client() as client:
        response = client.get("https://api.example.com")
        assert response.status_code == 200
```

---

## Pattern: FutureWarning

### Description
Warnings about behavior that will change in future versions.
These are higher priority than DeprecationWarning.

### Common Sources
- NumPy array comparisons
- Pandas DataFrame operations
- SQLAlchemy query patterns

### Fix Strategy
1. Read the warning message carefully
2. Check the library's migration guide
3. Update to the new API immediately
4. Add tests to verify behavior matches expectations

---

## Project-Specific Guidelines

### RAE Warning Policy
From AGENT_TESTING_GUIDE.md:

1. **Fix at source** - Update code to not generate warnings
2. **Filter only external** - Only filter warnings from third-party code
3. **Document filters** - Every filterwarnings entry needs a comment
4. **Track upstream** - Link to upstream issue for external warnings
5. **Review quarterly** - Check if filters can be removed

### Common RAE Patterns
```python
# Memory client warnings - use async context
async with memory_client() as client:
    result = await client.store(data)

# PII scrubber - suppress specific external warnings
# See: docs/WARNING_REMOVAL_PLAN.md for tracking
```

## Verification Checklist

- [ ] Run `pytest -W error` - all tests pass
- [ ] Run `pytest --tb=short -v 2>&1 | grep -i warning` - no unexpected warnings
- [ ] Check CI logs for warning counts
- [ ] Verify fix doesn't change functionality (existing tests pass)
