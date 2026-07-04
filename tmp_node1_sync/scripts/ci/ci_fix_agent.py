#!/usr/bin/env python3
"""
AI-powered CI fix generator.
Uses Claude or OpenAI GPT to generate fixes based on failure context.

Part of RAE CI Quality Implementation - Iteration 4: Auto-Healing CI

This module uses LLM APIs to analyze CI failure context and generate
appropriate code fixes. It supports both Anthropic Claude and OpenAI GPT.

Usage:
    python ci_fix_agent.py --context failure_context.json --fix-type warning --output-dir ./fixes

Environment variables:
    ANTHROPIC_API_KEY - API key for Anthropic Claude
    OPENAI_API_KEY - API key for OpenAI GPT

Exit codes:
    0 - Fix generated successfully
    1 - Error or fix not possible
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Optional imports for LLM providers
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None  # type: ignore
    HAS_ANTHROPIC = False

try:
    import openai

    HAS_OPENAI = True
except ImportError:
    openai = None  # type: ignore
    HAS_OPENAI = False


class CostTracker:
    """Track API usage costs."""

    # Approximate costs per 1K tokens (as of 2024)
    COSTS = {
        "anthropic": {
            "claude-sonnet-4-5-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        },
        "openai": {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4o": {"input": 0.005, "output": 0.015},
        },
    }

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    def track(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Track token usage and return estimated cost.

        Args:
            provider: LLM provider name
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        costs = self.COSTS.get(provider, {}).get(model, {"input": 0.01, "output": 0.03})
        cost = (input_tokens / 1000) * costs["input"] + (output_tokens / 1000) * costs[
            "output"
        ]
        self.total_cost_usd += cost

        return cost


class CIFixAgent:
    """Generate CI fixes using LLM."""

    FIX_TEMPLATES: Dict[str, str] = {
        "warning": """You are fixing a Python warning in the RAE project.

Policy: ZERO WARNINGS (pytest -W error)

Context:
{context}

Generate a fix that:
1. Eliminates the warning at its source
2. If from external library, add appropriate filterwarnings with comment
3. Preserves existing functionality
4. Follows project conventions (see AGENT_TESTING_GUIDE.md)

Return ONLY the modified code in a code block, no explanations.
Include file path as a comment at the top: # File: path/to/file.py
""",
        "flaky_test": """You are fixing a flaky test in the RAE project.

Test: {test_name}
Failure pattern: {failure_info}

Common causes:
- Timing issues (add explicit waits)
- Race conditions (add synchronization)
- External dependencies (add mocks)
- Non-deterministic data (add seed)

Generate a fix that makes the test deterministic.
Follow AGENT_TESTING_GUIDE.md principles.

Return ONLY the modified test code in a code block.
Include file path as a comment at the top: # File: path/to/file.py
""",
        "lint": """Fix the following linting issues:
{issues}

Apply black, isort, and ruff fixes.
Return the corrected code in a code block.
Include file path as a comment at the top: # File: path/to/file.py
""",
        "import_error": """Fix the following import error:
{error_message}

Context:
{context}

Common fixes:
- Add missing dependency to requirements.txt
- Fix import path
- Add __init__.py
- Use try/except for optional imports

Return the fixed code in a code block.
Include file path as a comment at the top: # File: path/to/file.py
""",
        "type_error": """Fix the following type error:
{error_message}

Context:
{context}

Update function signature or caller to match.
Add type hints if missing.

Return the fixed code in a code block.
Include file path as a comment at the top: # File: path/to/file.py
""",
    }

    # Models configuration
    MODELS = {
        "anthropic": "claude-sonnet-4-5-20241022",
        "openai": "gpt-4o-mini",
    }

    def __init__(self, provider: str = "anthropic"):
        """Initialize the fix agent with specified LLM provider.

        Args:
            provider: LLM provider ("anthropic" or "openai")

        Raises:
            RuntimeError: If provider is not available or API key not set
        """
        self.provider = provider
        self.cost_tracker = CostTracker()
        self.client: Any = None

        if provider == "anthropic":
            if not HAS_ANTHROPIC:
                raise RuntimeError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
            self.client = anthropic.Anthropic(api_key=api_key)

        elif provider == "openai":
            if not HAS_OPENAI:
                raise RuntimeError(
                    "openai package not installed. Install with: pip install openai"
                )
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY environment variable not set")
            self.client = openai.OpenAI(api_key=api_key)

        else:
            raise RuntimeError(f"Unknown provider: {provider}")

    def generate_fix(
        self, context: Dict[str, Any], fix_type: str, max_tokens: int = 4000
    ) -> Optional[str]:
        """Generate fix using LLM.

        Args:
            context: Failure context dictionary
            fix_type: Type of fix to generate
            max_tokens: Maximum tokens for response

        Returns:
            Generated fix content or None if failed
        """
        template = self.FIX_TEMPLATES.get(fix_type)
        if not template:
            print(f"Warning: No template for fix type: {fix_type}")
            return None

        # Prepare prompt with context
        prompt = self._prepare_prompt(template, context)

        print(f"[AI] Generating fix using {self.provider}...")
        print(f"[AI] Model: {self.MODELS.get(self.provider, 'unknown')}")

        try:
            if self.provider == "anthropic":
                return self._call_anthropic(prompt, max_tokens)
            elif self.provider == "openai":
                return self._call_openai(prompt, max_tokens)
            else:
                return None
        except Exception as e:
            print(f"Error generating fix: {e}")
            return None

    def _prepare_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Prepare the prompt by filling in template variables.

        Args:
            template: Prompt template
            context: Failure context

        Returns:
            Filled prompt string
        """
        # Get first failure for test info
        failures = context.get("failures", [])
        first_failure = failures[0] if failures else {}

        return template.format(
            context=json.dumps(context, indent=2, default=str),
            test_name=first_failure.get("nodeid", "unknown"),
            failure_info=json.dumps(failures[:3], indent=2, default=str),
            issues="\n".join(context.get("relevant_logs", [])[:20]),
            error_message="\n".join(context.get("relevant_logs", [])[:10]),
        )

    def _call_anthropic(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Call Anthropic Claude API.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum response tokens

        Returns:
            Response text or None
        """
        model = self.MODELS["anthropic"]

        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        # Track usage
        usage = response.usage
        cost = self.cost_tracker.track(
            "anthropic", model, usage.input_tokens, usage.output_tokens
        )
        print(f"[AI] Tokens: {usage.input_tokens} in / {usage.output_tokens} out")
        print(f"[AI] Estimated cost: ${cost:.4f}")

        return response.content[0].text

    def _call_openai(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Call OpenAI API.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum response tokens

        Returns:
            Response text or None
        """
        model = self.MODELS["openai"]

        response = self.client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        # Track usage
        usage = response.usage
        if usage:
            cost = self.cost_tracker.track(
                "openai", model, usage.prompt_tokens, usage.completion_tokens
            )
            print(
                f"[AI] Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out"
            )
            print(f"[AI] Estimated cost: ${cost:.4f}")

        return response.choices[0].message.content

    def save_fix(self, fix_content: str, output_dir: Path, affected_file: str) -> Path:
        """Save generated fix to file.

        Args:
            fix_content: The generated fix content
            output_dir: Directory to save fixes
            affected_file: Original file being fixed

        Returns:
            Path to saved fix file
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate fix filename
        stem = Path(affected_file).stem
        fix_file = output_dir / f"fix_{stem}.py"

        # Add target annotation and save
        content = (
            f"# TARGET: {affected_file}\n# Generated by CI Fix Agent\n\n{fix_content}"
        )
        fix_file.write_text(content, encoding="utf-8")

        print(f"[OK] Fix saved: {fix_file}")
        return fix_file

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get summary of API usage costs.

        Returns:
            Dictionary with cost summary
        """
        return {
            "total_input_tokens": self.cost_tracker.total_input_tokens,
            "total_output_tokens": self.cost_tracker.total_output_tokens,
            "total_cost_usd": self.cost_tracker.total_cost_usd,
        }


def load_cost_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load cost control configuration.

    Args:
        config_path: Path to cost_control.yaml

    Returns:
        Cost configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "ci" / "cost_control.yaml"

    if config_path.exists():
        try:
            import yaml

            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            print("Warning: PyYAML not installed, using default cost limits")
        except Exception as e:
            print(f"Warning: Failed to load cost config: {e}")

    # Default limits
    return {
        "limits": {
            "max_fixes_per_day": 10,
            "max_fixes_per_pr": 3,
            "max_tokens_per_fix": 4000,
        }
    }


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description="Generate CI fixes using AI")
    parser.add_argument(
        "--context", required=True, help="Path to failure context JSON file"
    )
    parser.add_argument("--fix-type", required=True, help="Type of fix to generate")
    parser.add_argument(
        "--output-dir",
        default="fixes/",
        help="Output directory for generated fixes (default: fixes/)",
    )
    parser.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "openai"],
        help="LLM provider to use (default: anthropic)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making API calls",
    )
    args = parser.parse_args()

    # Load context
    try:
        with open(args.context, encoding="utf-8") as f:
            context = json.load(f)
    except FileNotFoundError:
        print(f"Error: Context file not found: {args.context}")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in context file: {e}")
        return 1

    # Check if auto-fix is possible
    if not context.get("can_auto_fix", False):
        print("Warning: Context indicates this failure cannot be auto-fixed")
        print(f"Fix type: {context.get('fix_type', 'unknown')}")
        print(f"Confidence: {context.get('confidence', 'none')}")
        return 1

    # Load cost configuration
    cost_config = load_cost_config()
    max_tokens = cost_config.get("limits", {}).get("max_tokens_per_fix", 4000)

    # Get affected files
    affected_files = context.get("affected_files", [])
    if not affected_files:
        print("Warning: No affected files identified")
        return 1

    max_fixes = cost_config.get("limits", {}).get("max_fixes_per_pr", 3)
    files_to_fix = affected_files[:max_fixes]

    print(f"[INFO] Will generate fixes for {len(files_to_fix)} file(s)")

    if args.dry_run:
        print("[DRY-RUN] Would generate fixes for:")
        for f in files_to_fix:
            print(f"  - {f}")
        return 0

    # Initialize agent
    try:
        agent = CIFixAgent(provider=args.provider)
    except RuntimeError as e:
        print(f"Error initializing agent: {e}")
        return 1

    output_dir = Path(args.output_dir)
    fixes_generated = 0

    for file_path in files_to_fix:
        print(f"\n[FILE] Generating fix for: {file_path}")

        fix = agent.generate_fix(context, args.fix_type, max_tokens=max_tokens)

        if fix:
            agent.save_fix(fix, output_dir, file_path)
            fixes_generated += 1
        else:
            print(f"[SKIP] No fix generated for: {file_path}")

    # Print cost summary
    cost_summary = agent.get_cost_summary()
    print(
        f"\n[COST] Total tokens: {cost_summary['total_input_tokens']} in / "
        f"{cost_summary['total_output_tokens']} out"
    )
    print(f"[COST] Estimated total cost: ${cost_summary['total_cost_usd']:.4f}")

    # Save cost report
    cost_report_path = output_dir / "cost_report.json"
    with open(cost_report_path, "w") as f:
        json.dump(cost_summary, f, indent=2)

    print(f"\n[OK] Generated {fixes_generated} fix(es)")
    return 0 if fixes_generated > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
