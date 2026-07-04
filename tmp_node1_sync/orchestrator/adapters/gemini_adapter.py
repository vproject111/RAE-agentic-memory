"""Gemini CLI adapter for orchestrator."""

import asyncio
import json

from .base import AgentContext, AgentResult, ModelAdapter, ModelType


class GeminiAdapter(ModelAdapter):
    """Adapter for Gemini CLI (non-interactive, browser auth)."""

    def __init__(self, model_type: ModelType, working_dir: str):
        """Initialize Gemini adapter.

        Args:
            model_type: Gemini model type (PRO or FLASH)
            working_dir: Working directory for operations
        """
        if model_type not in [ModelType.GEMINI_PRO, ModelType.GEMINI_FLASH]:
            raise ValueError(f"Invalid model type for Gemini: {model_type}")

        super().__init__(model_type, working_dir)
        self.model_name = self._get_gemini_model_name()

    def _get_gemini_model_name(self) -> str:
        """Map ModelType to Gemini CLI model string."""
        mapping = {
            ModelType.GEMINI_PRO: "gemini-2.0-pro",
            ModelType.GEMINI_FLASH: "gemini-2.0-flash",
        }
        return mapping[self.model_type]

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute task with Gemini CLI.

        Args:
            context: Agent execution context

        Returns:
            Result of execution
        """
        try:
            # Build prompt from context
            prompt = self._build_prompt(context)

            # Call Gemini CLI (without -m flag as it causes 404 errors with API)
            # Gemini will use default model configured in ~/.gemini/settings.json
            # Use positional argument instead of deprecated -p flag
            # Run from /tmp to avoid loading large project context
            proc = await asyncio.create_subprocess_exec(
                "gemini",
                prompt,  # Positional argument
                "--output-format",
                "json",
                cwd="/tmp",  # Avoid loading project context
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=300,  # 5 minutes
            )

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"

                # Detect quota/rate limit errors
                if any(
                    keyword in error_msg.lower()
                    for keyword in [
                        "quota",
                        "rate limit",
                        "resource exhausted",
                        "429",
                        "too many requests",
                        "limit exceeded",
                    ]
                ):
                    return AgentResult(
                        success=False,
                        output="",
                        error=(
                            f"⚠️  GEMINI QUOTA LIMIT EXCEEDED ⚠️\n\n"
                            f"Limit dzienny wyczerpany na obecnym koncie.\n\n"
                            f"Aby kontynuować:\n"
                            f"1. Przełącz konto Gemini: .local/switch-gemini.sh [grzegorz|lili|marcel]\n"
                            f"2. Uruchom ponownie zadanie\n\n"
                            f"Alternatywnie: orkiestrator automatycznie użyje Claude Sonnet\n\n"
                            f"Szczegóły błędu: {error_msg}"
                        ),
                    )

                # Detect authentication errors (including 404 which can mean no API access)
                if any(
                    keyword in error_msg.lower()
                    for keyword in [
                        "unauthenticated",
                        "unauthorized",
                        "401",
                        "403",
                        "404",
                        "authentication",
                        "permission denied",
                        "not found",
                        "entity was not found",
                    ]
                ):
                    return AgentResult(
                        success=False,
                        output="",
                        error=(
                            f"⚠️  GEMINI AUTHENTICATION ERROR ⚠️\n\n"
                            f"Problem z autoryzacją konta Gemini.\n\n"
                            f"Aby naprawić:\n"
                            f"1. Uruchom: gemini /auth\n"
                            f"2. Zaloguj się w przeglądarce\n"
                            f"3. Uruchom ponownie zadanie\n\n"
                            f"Szczegóły błędu: {error_msg}"
                        ),
                    )

                return AgentResult(
                    success=False,
                    output="",
                    error=f"Gemini CLI failed: {error_msg}",
                )

            # Parse JSON response
            # Gemini CLI may output extra lines before JSON (like "Loaded cached credentials.")
            stdout_text = stdout.decode()
            # Find first { to start of JSON
            json_start = stdout_text.find("{")
            if json_start == -1:
                return AgentResult(
                    success=False,
                    output="",
                    error=f"No JSON found in Gemini response: {stdout_text[:200]}",
                )
            response_data = json.loads(stdout_text[json_start:])

            # Extract output (Gemini CLI format may vary)
            output = self._extract_output(response_data)

            return AgentResult(
                success=True,
                output=output,
                metadata={
                    "model": self.model_name,
                    "task_type": context.task_type,
                    "complexity": context.complexity.value,
                },
            )

        except asyncio.TimeoutError:
            return AgentResult(
                success=False,
                output="",
                error="Gemini CLI timed out after 5 minutes",
            )
        except json.JSONDecodeError as e:
            return AgentResult(
                success=False,
                output="",
                error=f"Failed to parse Gemini response: {e}",
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=f"Unexpected error: {e}",
            )

    def _build_prompt(self, context: AgentContext) -> str:
        """Build prompt from context.

        Args:
            context: Agent execution context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Task: {context.task_description}",
            f"Type: {context.task_type}",
            f"Complexity: {context.complexity.value}",
            f"Risk: {context.risk.value}",
        ]

        if context.files_to_read:
            prompt_parts.append(
                f"Files to consider: {', '.join(context.files_to_read)}"
            )

        if context.additional_context:
            for key, value in context.additional_context.items():
                prompt_parts.append(f"{key}: {value}")

        return "\n\n".join(prompt_parts)

    def _extract_output(self, response_data: dict) -> str:
        """Extract output text from Gemini CLI response.

        Args:
            response_data: Parsed JSON response

        Returns:
            Output text
        """
        # Gemini CLI may return different structures
        # Try common fields
        if "text" in response_data:
            return response_data["text"]
        elif "content" in response_data:
            return response_data["content"]
        elif "response" in response_data:
            return response_data["response"]
        else:
            return json.dumps(response_data, indent=2)

    async def is_available(self) -> bool:
        """Check if Gemini CLI is available and configured.

        Returns:
            True if Gemini CLI is ready to use
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "gemini",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    async def get_cost_per_1k_tokens(self) -> float:
        """Get cost per 1K tokens for this model.

        Returns:
            Cost in USD per 1K tokens
        """
        # Pricing as of December 2024 (from plan)
        if self.model_type == ModelType.GEMINI_FLASH:
            return 0.00001875  # $0.00001875 per 1K
        elif self.model_type == ModelType.GEMINI_PRO:
            return 0.00025  # $0.00025 per 1K
        else:
            return 0.0
