"""Code-Reviewer-Agent: Reviews generated code before committing."""

import json
from typing import Any, Dict

from .base import AgentResponse, AgentTask, BaseAgent


class CodeReviewerAgent(BaseAgent):
    """Agent responsible for reviewing generated code.

    CRITICAL: Must use a different model than Implementer to catch issues.
    """

    def __init__(self):
        """Initialize Code-Reviewer-Agent."""
        super().__init__(name="Code-Reviewer-Agent", role="code_reviewer")

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Review generated code from Implementer.

        Args:
            task: Task containing code to review

        Returns:
            Agent response with review result
        """
        try:
            # Extract implementation from context
            implementation = task.context.get("implementation")
            step = task.context.get("step")

            if not implementation:
                return AgentResponse(
                    success=False,
                    result=None,
                    error="No implementation provided for review",
                )

            # Build review prompt
            prompt = self._build_review_prompt(task, implementation, step)

            # Call model
            result = await self._call_model(
                prompt=prompt,
                task_type="code_review",
                complexity=task.complexity,
                risk=task.risk,
                working_dir=task.working_directory,
            )

            if not result.success:
                return AgentResponse(
                    success=False,
                    result=None,
                    error=result.error,
                )

            # Parse review from output
            review = self._parse_review(result.output)

            return AgentResponse(
                success=True,
                result=review,
                metadata={
                    "model": result.metadata.get("model") if result.metadata else None,
                    "raw_output": result.output,
                },
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                result=None,
                error=f"Code review failed: {str(e)}",
            )

    def _build_review_prompt(
        self, task: AgentTask, implementation: Dict[str, Any], step: Dict[str, Any]
    ) -> str:
        """Build prompt for code review.

        Args:
            task: Agent task
            implementation: Implementation to review
            step: Original step description

        Returns:
            Formatted review prompt
        """
        base_prompt = self._build_base_prompt(task)

        # Format implementation for review
        impl_str = self._format_implementation(implementation)
        step_desc = step.get("description", "N/A") if step else "N/A"

        review_instructions = f"""

Your task is to review the code implementation below.

ORIGINAL STEP REQUIREMENT:
{step_desc}

IMPLEMENTATION TO REVIEW:
{impl_str}

REVIEW CRITERIA:
1. Correctness - Does it fulfill the step requirement?
2. Code Quality - Is it clean, readable, and maintainable?
3. Type Safety - Are type hints present and correct?
4. Documentation - Are docstrings adequate?
5. Error Handling - Are edge cases handled?
6. Performance - Any obvious performance issues?
7. Security - Any security concerns (SQL injection, XSS, etc.)?
8. Standards - Follows project coding standards?
9. ZERO-WARNINGS - Will it pass mypy/ruff without warnings?
10. Testing - Is it testable? Are tests needed?

OUTPUT FORMAT (JSON):
{{
  "step_id": "{step.get("id") if step else "unknown"}",
  "status": "approved|rejected|needs_changes",
  "review": {{
    "correctness": 1-10,
    "code_quality": 1-10,
    "type_safety": 1-10,
    "documentation": 1-10,
    "error_handling": 1-10,
    "performance_concerns": [],
    "security_issues": [],
    "standard_violations": []
  }},
  "required_changes": [
    {{
      "severity": "critical|major|minor",
      "description": "Clear description of what needs to change",
      "location": "file:line or general area"
    }}
  ],
  "optional_improvements": [
    {{
      "description": "Suggestion for improvement",
      "benefit": "Why this would be better"
    }}
  ],
  "reasoning": "Overall assessment and key concerns"
}}

IMPORTANT:
- Be thorough but fair
- Provide specific, actionable feedback
- Focus on real issues, not nitpicks
- Consider the context (low-risk docs vs high-risk core logic)
- Ensure feedback helps improve code quality
- Different perspective than Implementer (you're the second pair of eyes)

Now review the code:
"""

        return base_prompt + review_instructions

    def _format_implementation(self, implementation: Dict[str, Any]) -> str:
        """Format implementation for display.

        Args:
            implementation: Implementation dict from Implementer

        Returns:
            Formatted string
        """
        impl_type = implementation.get("type", "unknown")

        if impl_type == "code_blocks" and "files" in implementation:
            # Format multiple files
            parts = []
            for file_info in implementation["files"]:
                path = file_info.get("path", "unknown")
                lang = file_info.get("language", "text")
                content = file_info.get("content", "")
                parts.append(f"File: {path}\n```{lang}\n{content}\n```")
            return "\n\n".join(parts)
        elif impl_type == "raw":
            # Raw content
            return implementation.get("content", "")
        else:
            # Fallback to JSON
            return json.dumps(implementation, indent=2)

    def _parse_review(self, output: str) -> Dict[str, Any]:
        """Parse review from model output.

        Args:
            output: Raw model output

        Returns:
            Parsed review dictionary
        """
        import re

        # Look for JSON code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", output, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object
            json_match = re.search(r"\{.*\}", output, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # No JSON found, return structured error
                return {
                    "error": "Failed to parse review",
                    "raw_output": output,
                }

        try:
            review = json.loads(json_str)
            return review
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON in review: {e}",
                "raw_output": output,
            }
