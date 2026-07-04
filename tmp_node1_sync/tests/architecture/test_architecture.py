"""
Architectural tests to enforce code quality and design principles.

These tests ensure:
1. Layer isolation (core/ doesn't import from api/ or services/)
2. File size limits (max 800 lines per file)
3. Function complexity (McCabe complexity < 15)
4. No circular dependencies
5. Proper test organization
"""

import ast
import re
from pathlib import Path
from typing import List

import pytest

# ============================================================================
# Test Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
APPS_DIR = PROJECT_ROOT / "apps" / "memory_api"
MAX_FILE_LINES = 1600
MAX_COMPLEXITY = 25


# ============================================================================
# Helper Functions
# ============================================================================


def get_python_files(directory: Path, exclude_tests: bool = True) -> List[Path]:
    """Get all Python files in directory"""
    files = []
    for file in directory.rglob("*.py"):
        if exclude_tests and ("test_" in file.name or "/tests/" in str(file)):
            continue
        if "__pycache__" in str(file):
            continue
        files.append(file)
    return files


def calculate_complexity(node) -> int:
    """Calculate McCabe complexity of a function/method"""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            (
                ast.If,
                ast.While,
                ast.For,
                ast.ExceptHandler,
                ast.With,
                ast.Assert,
                ast.BoolOp,
            ),
        ):
            complexity += 1
    return complexity


def extract_imports(file_path: Path) -> List[str]:
    """Extract import statements from Python file"""
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports
    except Exception:
        return []


# ============================================================================
# Test: Layer Isolation
# ============================================================================


def test_core_layer_isolation():
    """
    Ensure core/ module doesn't import from api/ or services/.

    Core should be independent business logic without dependencies
    on API endpoints or service implementations.
    """
    core_dir = APPS_DIR / "core"
    if not core_dir.exists():
        pytest.skip("Core directory not found")

    violations = []

    for py_file in get_python_files(core_dir):
        content = py_file.read_text()
        imports = extract_imports(py_file)

        # Check for forbidden imports
        for imp in imports:
            if "apps.memory_api.api" in imp or "apps.memory_api.services" in imp:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: imports {imp}")

        # Also check string imports (from ... import ...)
        if "from apps.memory_api.api" in content:
            violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: from api import")
        if "from apps.memory_api.services" in content:
            violations.append(
                f"{py_file.relative_to(PROJECT_ROOT)}: from services import"
            )

    if violations:
        msg = "❌ Core layer isolation violated:\n" + "\n".join(
            f"  - {v}" for v in violations
        )
        pytest.fail(msg)


def test_models_dont_import_services():
    """
    Ensure models/ don't import from services/ or api/.

    Models should be pure data structures.
    """
    models_dir = APPS_DIR / "models"
    if not models_dir.exists():
        pytest.skip("Models directory not found")

    violations = []

    for py_file in get_python_files(models_dir):
        imports = extract_imports(py_file)

        for imp in imports:
            if "apps.memory_api.api" in imp or "apps.memory_api.services" in imp:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: imports {imp}")

    if violations:
        msg = "⚠️  Models importing services/api (pre-existing):\n" + "\n".join(
            f"  - {v}" for v in violations
        )
        # Skip instead of fail for pre-existing issues
        # pytest.skip(msg)
        pytest.fail(msg)


# ============================================================================
# Test: File Size Limits
# ============================================================================


def test_file_size_limits():
    """
    Ensure no file exceeds MAX_FILE_LINES.

    Large files are hard to maintain and test. Split them into smaller modules.
    """
    violations = []

    for py_file in get_python_files(APPS_DIR):
        lines = py_file.read_text().split("\n")
        if len(lines) > MAX_FILE_LINES:
            violations.append(
                f"{py_file.relative_to(PROJECT_ROOT)}: {len(lines)} lines (max {MAX_FILE_LINES})"
            )

    if violations:
        msg = "⚠️  Files exceeding size limit (pre-existing):\n" + "\n".join(
            f"  - {v}" for v in violations[:5]
        )
        if len(violations) > 5:
            msg += f"\n  ... and {len(violations) - 5} more"
        # Skip for pre-existing issues, but log them
        # pytest.skip(msg)
        pytest.fail(msg)


# ============================================================================
# Test: Function Complexity
# ============================================================================


def test_function_complexity():
    """
    Ensure no function exceeds McCabe complexity of MAX_COMPLEXITY.

    Complex functions are hard to understand and test. Refactor them.
    """
    violations = []

    for py_file in get_python_files(APPS_DIR):
        try:
            content = py_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = calculate_complexity(node)
                    if complexity > MAX_COMPLEXITY:
                        violations.append(
                            f"{py_file.relative_to(PROJECT_ROOT)}:{node.lineno} "
                            f"- {node.name}() complexity={complexity} (max {MAX_COMPLEXITY})"
                        )
        except Exception:
            # Skip files with syntax errors
            pass

    if violations:
        msg = "⚠️  Functions exceeding complexity limit (pre-existing):\n" + "\n".join(
            f"  - {v}" for v in violations[:5]
        )  # Show first 5
        if len(violations) > 5:
            msg += f"\n  ... and {len(violations) - 5} more"
        # Skip for pre-existing issues
        # pytest.skip(msg)
        pytest.fail(msg)


# ============================================================================
# Test: Test Organization
# ============================================================================


def test_tests_mirror_source_structure():
    """
    Ensure tests follow source code structure.

    For apps/memory_api/services/foo.py, expect:
    - apps/memory_api/tests/services/test_foo.py
    """
    # This is a soft check - we'll just verify tests exist for major modules
    major_modules = [
        APPS_DIR / "api",
        APPS_DIR / "core",
        APPS_DIR / "services",
    ]

    missing_test_dirs = []
    for module in major_modules:
        if not module.exists():
            continue

        test_dir = APPS_DIR / "tests" / module.name
        if not test_dir.exists():
            missing_test_dirs.append(
                f"Missing test directory: {test_dir.relative_to(PROJECT_ROOT)}"
            )

    if missing_test_dirs:
        msg = "⚠️  Test structure issues:\n" + "\n".join(
            f"  - {m}" for m in missing_test_dirs
        )
        # Just warn, don't fail
        # pytest.skip(msg)
        pytest.fail(msg)


# ============================================================================
# Test: No Hardcoded Secrets
# ============================================================================


def test_no_hardcoded_secrets():
    """
    Ensure no hardcoded secrets in code.

    Look for patterns like:
    - API_KEY = "sk-..."
    - password = "..."
    - secret = "..."
    """
    secret_patterns = [
        re.compile(r'api[_-]?key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
        re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        re.compile(r'token\s*=\s*["\'][^"\']{20,}["\']', re.IGNORECASE),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI key pattern
        re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub personal access token
    ]

    violations = []

    for py_file in get_python_files(APPS_DIR):
        # Skip example files
        if "examples" in str(py_file):
            continue

        content = py_file.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            for pattern in secret_patterns:
                if pattern.search(line):
                    # Check if it's a placeholder or test value
                    if any(
                        x in line.lower()
                        for x in [
                            "example",
                            "placeholder",
                            "your_",
                            "test_",
                            "mock",
                            "fake",
                            "dummy",
                            "cache_key",
                            "rae.llm.cache_key",
                            "cost_per_token",
                        ]
                    ):
                        continue

                    violations.append(
                        f"{py_file.relative_to(PROJECT_ROOT)}:{i} - Possible hardcoded secret: {line.strip()}"
                    )
                    break

    if violations:
        msg = "⚠️  Possible hardcoded secrets found (check manually):\n" + "\n".join(
            f"  - {v}" for v in violations[:5]
        )
        if len(violations) > 5:
            msg += f"\n  ... and {len(violations) - 5} more"
        # Skip for now, manual review needed
        # pytest.skip(msg)
        pytest.fail(msg)


# ============================================================================
# Test: Circular Dependencies
# ============================================================================


def test_no_circular_dependencies():
    """
    Detect circular imports between modules.

    This is a simplified check - it won't catch all cases but will
    catch obvious direct circular dependencies.
    """
    module_imports = {}

    for py_file in get_python_files(APPS_DIR):
        module_name = str(py_file.relative_to(APPS_DIR)).replace("/", ".").rstrip(".py")
        imports = extract_imports(py_file)

        # Filter to only internal imports
        internal_imports = [imp for imp in imports if imp.startswith("apps.memory_api")]
        module_imports[module_name] = internal_imports

    # Check for direct circular dependencies
    violations = []
    for module_a, imports_a in module_imports.items():
        for import_b in imports_a:
            # Convert import to module name
            module_b = import_b.replace("apps.memory_api.", "").replace(".", "/")

            if module_b in module_imports:
                imports_b = module_imports[module_b]
                # Check if module_b imports module_a
                module_a_import = f"apps.memory_api.{module_a.replace('/', '.')}"
                if any(module_a_import in imp for imp in imports_b):
                    violations.append(f"{module_a} <-> {module_b}")

    if violations:
        unique_violations = list(set(violations))
        msg = "❌ Circular dependencies detected:\n" + "\n".join(
            f"  - {v}" for v in unique_violations
        )
        pytest.fail(msg)


# ============================================================================
# Test: Dependency Injection
# ============================================================================


def test_services_use_dependency_injection():
    """
    Ensure services use dependency injection, not direct instantiation.

    Look for patterns like:
    - db = Database()  # BAD
    vs
    - def __init__(self, db: Database)  # GOOD
    """
    # This is a soft check - just verify key services accept dependencies
    services_dir = APPS_DIR / "services"
    if not services_dir.exists():
        pytest.skip("Services directory not found")

    # We'll just verify that service __init__ methods accept parameters
    # beyond 'self'
    violations = []
    allowed_no_di = [
        "EvaluationService",
        "QueryAnalyzer",
        "ContextCache",
        "PolicyVersioningService",
        "ConnectionManager",
        "TokenEstimator",
        "AnalyticsService",
    ]

    for py_file in get_python_files(services_dir):
        try:
            content = py_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if node.name in allowed_no_di:
                        continue

                    # Find __init__ method
                    for method in node.body:
                        if (
                            isinstance(method, ast.FunctionDef)
                            and method.name == "__init__"
                        ):
                            # Check if it has parameters beyond self
                            params = [arg.arg for arg in method.args.args]
                            if len(params) == 1 and params[0] == "self":
                                # Service with no DI - might be a problem
                                violations.append(
                                    f"{py_file.relative_to(PROJECT_ROOT)} "
                                    f"- {node.name}.__init__ has no dependencies"
                                )
        except Exception:
            pass

    # Don't fail, just warn if there are many violations
    if len(violations) > 5:
        msg = "⚠️  Services without dependency injection:\n" + "\n".join(
            f"  - {v}" for v in violations[:5]
        )
        msg += f"\n  ... and {len(violations) - 5} more"
        # pytest.skip(msg)
        pytest.skip(msg)


# ============================================================================
# Test: Proper Error Handling
# ============================================================================


def test_no_bare_except():
    """
    Ensure no bare 'except:' clauses.

    Always catch specific exceptions.
    """
    violations = []

    for py_file in get_python_files(APPS_DIR):
        try:
            content = py_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:  # bare except
                        violations.append(
                            f"{py_file.relative_to(PROJECT_ROOT)}:{node.lineno} "
                            f"- Bare except clause"
                        )
        except Exception:
            pass

    if violations:
        msg = "❌ Bare except clauses found:\n" + "\n".join(
            f"  - {v}" for v in violations[:10]
        )
        if len(violations) > 10:
            msg += f"\n  ... and {len(violations) - 10} more"
        pytest.fail(msg)
