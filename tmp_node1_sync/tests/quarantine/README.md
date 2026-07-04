# Test Quarantine Directory

This directory contains tests that have been identified as flaky and are
temporarily excluded from the main test suite.

## Why Quarantine?

Flaky tests (tests with non-deterministic outcomes) reduce CI reliability
and make it harder to trust test results. Instead of ignoring them, we:

1. Move them to quarantine
2. Mark them with `@pytest.mark.skip`
3. Create a ticket to fix them
4. Once fixed, move them back to the main suite

## Flaky Test Lifecycle

```
Detection → Analysis → Quarantine → Fix → Verification → Restore
```

### Detection
- Automated via `flaky-detection` CI job
- Runs tests 3x and compares outcomes
- Generates `flaky_report.json`

### Quarantine
```bash
python scripts/ci/quarantine_test.py tests/path/to/test.py::test_name
```

### Fix
1. Run locally multiple times:
   ```bash
   for i in {1..10}; do pytest tests/quarantine/path/to/test.py -v; done
   ```

2. Common fixes:
   - **Timing issues:** Add explicit waits (`time.sleep()`, `await asyncio.sleep()`)
   - **Race conditions:** Add locks, synchronization
   - **External deps:** Mock them (`@patch`, `monkeypatch`)
   - **Random data:** Add seed (`random.seed(42)`)
   - **Time-based:** Use `freezegun` to freeze time

3. Verify stability (10+ consecutive passes)

### Restore
```bash
mv tests/quarantine/path/to/test.py tests/path/to/test.py
# Remove quarantine marker from file
# Open PR with fix
```

## SLA

Per RAE-CI-QUALITY-SPEC-enterprise-v2.0.md:
- **SLA-2:** Every flaky test in main → fix or quarantine within 5 working days

## Running Quarantined Tests

```bash
# Run all quarantined tests (for debugging)
pytest tests/quarantine/ -v

# Check which tests are quarantined
find tests/quarantine -name "test_*.py"

# Run specific quarantined test
pytest tests/quarantine/api/v1/test_cache.py::test_flaky -v
```

## Current Status

See `flaky_report.json` artifact in latest `flaky-detection` CI run.
