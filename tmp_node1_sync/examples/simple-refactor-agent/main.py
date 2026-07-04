import os

import httpx
import typer
from rich.console import Console
from rich.markdown import Markdown

from .config import settings

app = typer.Typer()
console = Console()


@app.command()
def refactor(
    file_path: str = typer.Argument(..., help="The path to the file to refactor."),
    instruction: str = typer.Argument(
        ..., help="The refactoring instruction for the agent."
    ),
):
    """
    Refactors a given file using the RAE Agent.
    """
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error: File not found at {file_path}[/bold red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]Refactoring file:[/bold blue] {file_path}")
    console.print(f"[bold blue]Instruction:[/bold blue] {instruction}")

    # 1. Read file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()
        console.print("[green]  - File content read successfully.[/green]")
    except Exception as e:
        console.print(f"[bold red]Error reading file: {e}[/bold red]")
        raise typer.Exit(1)

    # 2. Construct prompt for the RAE Agent
    agent_prompt = f"""You are a code refactoring agent. Your task is to refactor the provided Python code snippet according to the user's instruction.
Ensure the refactored code is syntactically correct and follows best practices.

Refactoring Instruction: {instruction}

Original Python Code:
```python
{original_content}
```

Provide only the refactored code in your response, enclosed in a ```python block.
"""

    # 3. Call RAE Agent's /agent/execute endpoint
    try:
        console.print("\n[yellow]3. Sending refactoring task to RAE Agent...[/yellow]")
        headers = {
            "X-Tenant-Id": settings.RAE_TENANT_ID,
            "X-API-Key": settings.RAE_API_KEY,
        }
        payload = {
            "tenant_id": settings.RAE_TENANT_ID,  # Redundant, but kept for now
            "prompt": agent_prompt,
            "budget_tokens": 5000,  # Example budget
        }

        with httpx.Client() as client:
            response = client.post(
                f"{settings.RAE_API_URL}/agent/execute",
                json=payload,
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()

            agent_response = response.json()
            refactored_code = agent_response["answer"]

            console.print("[green]  - RAE Agent returned a response.[/green]")
            console.print(
                f"[bold green]  - Cost estimate: {agent_response['cost']['total_estimate']:.4f} USD[/bold green]"
            )

    except httpx.HTTPStatusError as e:
        console.print(
            f"[bold red]Error calling RAE Agent API: {e.response.status_code}[/bold red]"
        )
        console.print(e.response.text)
        raise typer.Exit(1)
    except Exception as e:
        console.print(
            f"[bold red]An unexpected error occurred while calling RAE Agent: {e}[/bold red]"
        )
        raise typer.Exit(1)

    # 4. Extract refactored code from LLM response
    # Assuming the LLM response is markdown with a python block
    if "```python" in refactored_code and "```" in refactored_code:
        start = refactored_code.find("```python") + len("```python")
        end = refactored_code.find("```", start)
        extracted_code = refactored_code[start:end].strip()
    else:
        extracted_code = refactored_code.strip()
        console.print(
            "[yellow]  - Warning: Could not find a '```python' block in the response. Using raw response.[/yellow]"
        )

    console.print("\n[bold yellow]Refactored Code Preview:[/bold yellow]")
    console.print(Markdown(f"```python\n{extracted_code}\n```"))

    # 5. Overwrite original file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(extracted_code)
        console.print(
            f"[bold green]  - File {file_path} updated successfully with refactored code.[/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]Error writing to file: {e}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
