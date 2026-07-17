"""
Pluggable Git Branch and SemVer validation engine for RAE-Core.
"""

import logging
import os
import re
import subprocess
from abc import ABC, abstractmethod


class BaseValidationStrategy(ABC):
    @abstractmethod
    def validate(self, branch_name: str) -> tuple[bool, str]:
        """
        Validates branch name.
        Returns (is_valid, error_message).
        """
        pass


class GitFlowStrategy(BaseValidationStrategy):
    # SemVer 2.0.0 official regex
    SEMVER_REGEX = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    ALLOWED_PATTERNS = [
        re.compile(r"^develop$"),
        re.compile(r"^(master|main)$"),
        re.compile(r"^feature/.*$"),
        re.compile(r"^bugfix/.*$"),
        re.compile(r"^release/.*$"),
        re.compile(r"^hotfix/.*$"),
        re.compile(r"^support/.*$"),
        re.compile(r"^checkpoint/.*$"),
        re.compile(r"^HEAD$"),
    ]

    def validate(self, branch_name: str) -> tuple[bool, str]:
        if branch_name.startswith("HEAD"):
            return True, ""

        matched = False
        for pattern in self.ALLOWED_PATTERNS:
            if pattern.match(branch_name):
                matched = True
                break

        if not matched:
            return False, (
                f"Branch name '{branch_name}' does not follow standard Git Flow prefixes "
                "(develop, master, main, feature/*, bugfix/*, release/*, hotfix/*, support/*, checkpoint/*)."
            )

        if branch_name.startswith("release/") or branch_name.startswith("hotfix/"):
            prefix, version = branch_name.split("/", 1)
            if version.startswith("v"):
                return False, (
                    f"Release/Hotfix branch '{branch_name}' uses legacy 'v' prefix. "
                    f"SemVer branch names must omit the 'v' (e.g., '{prefix}/1.2.3' instead of '{prefix}/v1.2.3')."
                )

            if not self.SEMVER_REGEX.match(version):
                return False, (
                    f"Version '{version}' in branch '{branch_name}' does not comply with SemVer 2.0.0 "
                    "(must be X.Y.Z, e.g. 1.2.3 or 1.2.3-rc.1)."
                )

        return True, ""


class GitHubFlowStrategy(BaseValidationStrategy):
    # SemVer 2.0.0 official regex
    SEMVER_REGEX = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def validate(self, branch_name: str) -> tuple[bool, str]:
        # GitHub Flow is permissive with branch names, but if someone explicitly uses
        # release/ or hotfix/, we enforce SemVer naming rules.
        if branch_name.startswith("release/") or branch_name.startswith("hotfix/"):
            prefix, version = branch_name.split("/", 1)
            if version.startswith("v"):
                return (
                    False,
                    f"Release/Hotfix branch '{branch_name}' uses legacy 'v' prefix. SemVer branch names must omit 'v'.",
                )
            if not self.SEMVER_REGEX.match(version):
                return (
                    False,
                    f"Version '{version}' in branch '{branch_name}' does not comply with SemVer 2.0.0.",
                )
        return True, ""


class PermissiveStrategy(BaseValidationStrategy):
    def validate(self, branch_name: str) -> tuple[bool, str]:
        return True, ""


class VersioningValidator:
    def __init__(self, project_path: str, module_name: str, config: dict | None = None):
        self.project_path = project_path
        self.module_name = module_name
        self.logger = logging.getLogger(f"rae.validator.{module_name}")
        self.config = config or self._load_config()

    def _load_config(self) -> dict:
        strategy = "permissive"
        strict = False

        # Read from environment variables first
        env_strict = (
            os.getenv("RAE_STRICT_SEMVER", "false").lower() == "true"
            or os.getenv("GIT_FLOW_STRICT", "false").lower() == "true"
        )
        if env_strict:
            strategy = "git-flow"
            strict = True

        pyproject_path = os.path.join(self.project_path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                import tomllib  # Python 3.11+

                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    version_config = (
                        data.get("tool", {}).get("rae", {}).get("versioning", {})
                    )
                    if "strategy" in version_config:
                        strategy = version_config["strategy"]
                    if "strict" in version_config:
                        strict = version_config["strict"]
            except Exception:
                # If tomllib is missing or parse fails, fall back to standard settings
                pass

        return {"strategy": strategy, "strict": strict or env_strict}

    def _get_current_branch(self) -> str | None:
        try:
            # Check if current directory or parent directory has .git
            git_dir = os.path.join(self.project_path, ".git")
            if not os.path.isdir(git_dir):
                parent_dir = os.path.dirname(self.project_path)
                if os.path.isdir(os.path.join(parent_dir, ".git")):
                    cwd = parent_dir
                else:
                    return None
            else:
                cwd = self.project_path

            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            return res.stdout.strip()
        except Exception:
            return None

    def validate(self) -> bool:
        branch = self._get_current_branch()
        if not branch:
            # No git repo (e.g. running in production/Docker container), pass validation silently
            return True

        strategy_name = self.config.get("strategy", "permissive")
        is_strict = self.config.get("strict", False)

        if strategy_name == "git-flow":
            strategy = GitFlowStrategy()
        elif strategy_name == "github-flow":
            strategy = GitHubFlowStrategy()
        else:
            strategy = PermissiveStrategy()

        is_valid, msg = strategy.validate(branch)
        if not is_valid:
            error_msg = f"RAE Contract Violation in module '{self.module_name}': {msg}"
            if is_strict:
                self.logger.critical(f"❌ {error_msg}")
                raise ValueError(error_msg)
            else:
                self.logger.warning(f"⚠️ {error_msg}")
                return False

        return True
