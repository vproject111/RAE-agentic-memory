"""Implementer-Agent: Writes code for approved plan steps."""

from typing import Any, Dict, List

from .base import AgentResponse, AgentTask, BaseAgent


class ImplementerAgent(BaseAgent):
    """Agent responsible for implementing plan steps."""

    def __init__(self):
        """Initialize Implementer-Agent."""
        super().__init__(name="Implementer-Agent", role="implementer")

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Implement a single step from the plan.

        Args:
            task: Task containing step to implement

        Returns:
            Agent response with implementation (diff/patch/file content)
        """
        try:
            # Extract step from context
            step = task.context.get("step")
            if not step:
                return AgentResponse(
                    success=False,
                    result=None,
                    error="No step provided for implementation",
                )

            # Build implementation prompt
            prompt = self._build_implementation_prompt(task, step)

            # Call model
            result = await self._call_model(
                prompt=prompt,
                task_type="implementation",
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

            # Parse implementation from output
            implementation = self._parse_implementation(result.output)

            return AgentResponse(
                success=True,
                result=implementation,
                metadata={
                    "model": result.metadata.get("model") if result.metadata else None,
                    "raw_output": result.output,
                    "step_id": step.get("id"),
                },
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                result=None,
                error=f"Implementation failed: {str(e)}",
            )

    def _build_implementation_prompt(
        self, task: AgentTask, step: Dict[str, Any]
    ) -> str:
        """Build prompt for implementation.

        Args:
            task: Agent task
            step: Step to implement

        Returns:
            Formatted implementation prompt
        """
        base_prompt = self._build_base_prompt(task)

        # Extract step details
        step_id = step.get("id", "unknown")
        step_type = step.get("type", "implementation")
        description = step.get("description", "")
        files_to_read = step.get("files_to_read", [])
        files_to_create = step.get("files_to_create", [])
        files_to_modify = step.get("files_to_modify", [])

        implementation_instructions = f"""

Your task is to implement the following step from an approved plan.

STEP DETAILS:
- ID: {step_id}
- Type: {step_type}
- Description: {description}

FILES TO READ:
{self._format_file_list(files_to_read)}

FILES TO CREATE:
{self._format_file_list(files_to_create)}

FILES TO MODIFY:
{self._format_file_list(files_to_modify)}

IMPLEMENTATION GUIDELINES:
1. Follow the step description precisely
2. Maintain code quality and style consistency
3. Add type hints and docstrings
4. Ensure ZERO-WARNINGS compliance
5. Write clean, readable code
6. Consider edge cases and error handling
7. Follow existing patterns in the codebase

OUTPUT FORMAT:
Provide your implementation as either:
- Full file content (for new files)
- Unified diff/patch (for modifications)
- Multiple files if needed

Use markdown code blocks with language hints:
```python
# Your code here
```

IMPORTANT:
- Be precise and complete
- Don't skip error handling
- Follow the project's coding standards
- Ensure backward compatibility
- Add appropriate comments only where logic isn't self-evident

Now implement the step:
"""

        return base_prompt + implementation_instructions

    def _format_file_list(self, files: List[str]) -> str:
        """Format list of files.

        Args:
            files: List of file paths

        Returns:
            Formatted string
        """
        if not files:
            return "None"
        return "\n".join(f"- {f}" for f in files)

    def _parse_implementation(self, output: str) -> Dict[str, Any]:
        """Parse implementation from model output.

        Args:
            output: Raw model output

        Returns:
            Parsed implementation dictionary
        """
        import re

        # Extract code blocks
        code_blocks = re.findall(r"```(\w+)?\n(.*?)```", output, re.DOTALL)

        if not code_blocks:
            # No code blocks found, return raw output
            return {
                "type": "raw",
                "content": output,
            }

        # Parse code blocks
        files = []
        for lang, code in code_blocks:
            files.append(
                {
                    "language": lang or "text",
                    "content": code.strip(),
                }
            )

        # Extract file paths from output if present
        # Look for patterns like "File: path/to/file.py"
        file_mentions = re.findall(r"File:\s*([^\n]+)", output)

        # Match files to paths if possible
        result = {
            "type": "code_blocks",
            "files": [],
        }

        for i, file_info in enumerate(files):
            file_path = file_mentions[i] if i < len(file_mentions) else None
            result["files"].append(
                {
                    "path": file_path,
                    "language": file_info["language"],
                    "content": file_info["content"],
                }
            )

        return result
