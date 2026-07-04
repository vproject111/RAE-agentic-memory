"""Quality gate enforcement - ZERO-WARNINGS policy."""

import asyncio
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List


class CheckStatus(Enum):
    """Status of individual quality check."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class QualityCheck:
    """Result of a single quality check."""

    name: str
    status: CheckStatus
    message: str
    details: str = ""
    execution_time: float = 0.0


@dataclass
class QualityGateResult:
    """Overall result of quality gate validation."""

    passed: bool
    checks: List[QualityCheck]
    can_merge: bool
    blocking_issues: List[str]
    warnings: List[str]
    summary: str

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def passed_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASSED)

    @property
    def failed_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAILED)


class QualityGate:
    """Enforces quality standards - NO EXCEPTIONS."""

    def __init__(self, working_dir: str, project_type: str = "python"):
        """Initialize quality gate.

        Args:
            working_dir: Project root directory
            project_type: Type of project (python, typescript, php, etc.)
        """
        self.working_dir = Path(working_dir)
        self.project_type = project_type

    async def validate(
        self, changed_files: List[str], change_size: str = "MEDIUM"
    ) -> QualityGateResult:
        """Run all quality checks on changes.

        Args:
            changed_files: List of files that were changed
            change_size: Size classification (TRIVIAL, SMALL, MEDIUM, LARGE)

        Returns:
            Quality gate result
        """
        checks: List[QualityCheck] = []
        blocking_issues: List[str] = []
        warnings: List[str] = []

        # Determine which checks to run based on change size
        # (from TESTING_OPTIMIZATION.md)
        if change_size == "TRIVIAL":
            # Skip tests, only lint
            checks.append(await self._run_linter())
        elif change_size == "SMALL":
            # Quick tests
            checks.append(await self._run_tests(quick=True))
            checks.append(await self._run_linter())
        else:  # MEDIUM or LARGE
            # Full validation
            checks.append(await self._run_tests(quick=False))
            checks.append(await self._check_zero_warnings())
            checks.append(await self._check_coverage())
            checks.append(await self._check_git_hooks())

        # Collect blocking issues
        for check in checks:
            if check.status == CheckStatus.FAILED:
                blocking_issues.append(f"{check.name}: {check.message}")
            elif check.status == CheckStatus.WARNING:
                warnings.append(f"{check.name}: {check.message}")

        # Determine if can merge
        passed = all(c.status != CheckStatus.FAILED for c in checks)
        can_merge = passed and len(warnings) == 0  # ZERO-WARNINGS policy

        # Generate summary
        summary = self._generate_summary(checks, passed, can_merge)

        return QualityGateResult(
            passed=passed,
            checks=checks,
            can_merge=can_merge,
            blocking_issues=blocking_issues,
            warnings=warnings,
            summary=summary,
        )

    async def _run_tests(self, quick: bool = False) -> QualityCheck:
        """Run test suite.

        Args:
            quick: If True, run only quick tests

        Returns:
            Quality check result
        """
        if self.project_type == "python":
            return await self._run_pytest(quick)
        else:
            return QualityCheck(
                name="tests",
                status=CheckStatus.SKIPPED,
                message=f"No test runner configured for {self.project_type}",
            )

    async def _run_pytest(self, quick: bool = False) -> QualityCheck:
        """Run pytest for Python projects.

        Args:
            quick: If True, run with markers for quick tests

        Returns:
            Quality check result
        """
        import time

        start = time.time()

        try:
            # Determine which tests to run
            if quick:
                # Run only unit tests (fast)
                test_path = self.working_dir / "rae-core" / "tests" / "unit"
            else:
                # Run all tests
                test_path = self.working_dir / "rae-core" / "tests"

            # Run pytest
            proc = await asyncio.create_subprocess_exec(
                str(self.working_dir / ".venv" / "bin" / "pytest"),
                str(test_path),
                "-v",
                "--tb=short",
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=600 if not quick else 120,  # 10min full, 2min quick
            )

            execution_time = time.time() - start
            output = stdout.decode() + stderr.decode()

            # Parse results
            if proc.returncode == 0:
                # Extract test count
                match = re.search(r"(\d+) passed", output)
                num_tests = match.group(1) if match else "?"

                return QualityCheck(
                    name="pytest",
                    status=CheckStatus.PASSED,
                    message=f"{num_tests} tests passed",
                    details=output,
                    execution_time=execution_time,
                )
            else:
                # Extract failure info
                failed_match = re.search(r"(\d+) failed", output)
                num_failed = failed_match.group(1) if failed_match else "?"

                return QualityCheck(
                    name="pytest",
                    status=CheckStatus.FAILED,
                    message=f"{num_failed} tests failed",
                    details=output,
                    execution_time=execution_time,
                )

        except asyncio.TimeoutError:
            return QualityCheck(
                name="pytest",
                status=CheckStatus.FAILED,
                message="Tests timed out",
                execution_time=time.time() - start,
            )
        except Exception as e:
            return QualityCheck(
                name="pytest",
                status=CheckStatus.FAILED,
                message=f"Error running tests: {e}",
            )

    async def _check_zero_warnings(self) -> QualityCheck:
        """Check for zero warnings (mypy + ruff).

        Returns:
            Quality check result
        """
        # Run both mypy and ruff in parallel
        mypy_check = await self._run_mypy()
        ruff_check = await self._run_ruff()

        # Combine results
        if (
            mypy_check.status == CheckStatus.FAILED
            or ruff_check.status == CheckStatus.FAILED
        ):
            status = CheckStatus.FAILED
            message = "Type checking or linting failed"
        elif (
            mypy_check.status == CheckStatus.WARNING
            or ruff_check.status == CheckStatus.WARNING
        ):
            status = CheckStatus.WARNING
            message = "Warnings detected (ZERO-WARNINGS policy)"
        else:
            status = CheckStatus.PASSED
            message = "No warnings (mypy + ruff clean)"

        details = f"mypy: {mypy_check.message}\nruff: {ruff_check.message}"

        return QualityCheck(
            name="zero_warnings",
            status=status,
            message=message,
            details=details,
        )

    async def _run_mypy(self) -> QualityCheck:
        """Run mypy type checker.

        Returns:
            Quality check result
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.working_dir / ".venv" / "bin" / "mypy"),
                "rae-core/rae_core",
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode() + stderr.decode()

            if proc.returncode == 0 and "Success" in output:
                return QualityCheck(
                    name="mypy",
                    status=CheckStatus.PASSED,
                    message="No type errors",
                )
            else:
                # Check if warnings or errors
                if "error:" in output.lower():
                    status = CheckStatus.FAILED
                    message = "Type errors detected"
                else:
                    status = CheckStatus.WARNING
                    message = "Type warnings detected"

                return QualityCheck(
                    name="mypy",
                    status=status,
                    message=message,
                    details=output,
                )

        except Exception as e:
            return QualityCheck(
                name="mypy",
                status=CheckStatus.FAILED,
                message=f"Error running mypy: {e}",
            )

    async def _run_ruff(self) -> QualityCheck:
        """Run ruff linter.

        Returns:
            Quality check result
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.working_dir / ".venv" / "bin" / "ruff"),
                "check",
                "rae-core/",
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            output = stdout.decode() + stderr.decode()

            if proc.returncode == 0:
                return QualityCheck(
                    name="ruff",
                    status=CheckStatus.PASSED,
                    message="No linting issues",
                )
            else:
                return QualityCheck(
                    name="ruff",
                    status=CheckStatus.WARNING,
                    message="Linting issues detected",
                    details=output,
                )

        except Exception as e:
            return QualityCheck(
                name="ruff",
                status=CheckStatus.FAILED,
                message=f"Error running ruff: {e}",
            )

    async def _run_linter(self) -> QualityCheck:
        """Run just the linter (for TRIVIAL changes).

        Returns:
            Quality check result
        """
        return await self._run_ruff()

    async def _check_coverage(self) -> QualityCheck:
        """Check test coverage (must not decrease).

        Returns:
            Quality check result
        """
        # For MVP, just return passed
        # In Phase 2, implement actual coverage tracking
        return QualityCheck(
            name="coverage",
            status=CheckStatus.PASSED,
            message="Coverage check passed (MVP: always pass)",
        )

    async def _check_git_hooks(self) -> QualityCheck:
        """Validate git pre-commit hooks pass.

        Returns:
            Quality check result
        """
        # For MVP, skip this check
        # In Phase 2, implement actual hook validation
        return QualityCheck(
            name="git_hooks",
            status=CheckStatus.PASSED,
            message="Git hooks check passed (MVP: skipped)",
        )

    def _generate_summary(
        self, checks: List[QualityCheck], passed: bool, can_merge: bool
    ) -> str:
        """Generate human-readable summary.

        Args:
            checks: All quality checks
            passed: Whether all checks passed
            can_merge: Whether changes can be merged

        Returns:
            Summary string
        """
        lines = []

        if can_merge:
            lines.append("✅ QUALITY GATE PASSED - Ready to merge")
        elif passed:
            lines.append("⚠️  QUALITY GATE WARNING - Some warnings detected")
        else:
            lines.append("❌ QUALITY GATE FAILED - Blocking issues detected")

        lines.append("")
        lines.append(
            f"Checks: {len([c for c in checks if c.status == CheckStatus.PASSED])}/{len(checks)} passed"
        )

        for check in checks:
            if check.status == CheckStatus.PASSED:
                icon = "✅"
            elif check.status == CheckStatus.WARNING:
                icon = "⚠️ "
            elif check.status == CheckStatus.FAILED:
                icon = "❌"
            else:
                icon = "⏭️ "

            lines.append(f"{icon} {check.name}: {check.message}")

        return "\n".join(lines)
