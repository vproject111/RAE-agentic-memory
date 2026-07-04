import json
import os
from typing import List, Optional

import httpx
import typer
from rich.console import Console
from rich.progress import track

from .config import settings

app = typer.Typer()
console = Console()


@app.command(name="import")
def import_pack(
    file: str = typer.Option(
        ..., "--file", "-f", help="Path to the JSON memory pack file."
    ),
):
    """
    Imports memories from a JSON file into the RAE Memory Engine.
    """
    if not os.path.exists(file):
        console.print(
            f"[bold red]Error: Memory pack file not found at {file}[/bold red]"
        )
        raise typer.Exit(1)

    try:
        with open(file, "r", encoding="utf-8") as f:
            memories_data = json.load(f)
    except json.JSONDecodeError:
        console.print(f"[bold red]Error: Invalid JSON format in {file}[/bold red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Error reading file {file}: {e}[/bold red]")
        raise typer.Exit(1)

    if not isinstance(memories_data, list):
        console.print(
            "[bold red]Error: Memory pack JSON must be a list of memory objects.[/bold red]"
        )
        raise typer.Exit(1)

    console.print(
        f"[bold blue]Importing {len(memories_data)} memories from {file} into RAE...[/bold blue]"
    )

    headers = {
        "X-Tenant-Id": settings.RAE_TENANT_ID,
        "X-API-Key": settings.RAE_API_KEY,
        "Content-Type": "application/json",
    }

    successful_imports = 0
    failed_imports = 0

    with httpx.Client() as client:
        for memory_payload in track(memories_data, description="Storing memories..."):
            try:
                response = client.post(
                    f"{settings.RAE_API_URL}/memory/store",
                    json=memory_payload,
                    headers=headers,
                )
                response.raise_for_status()
                successful_imports += 1
            except httpx.HTTPStatusError as e:
                console.print(
                    f"[bold red]  - Failed to import memory (status {e.response.status_code}): {e.response.text}[/bold red]"
                )
                failed_imports += 1
            except Exception as e:
                console.print(
                    f"[bold red]  - An unexpected error occurred during import: {e}[/bold red]"
                )
                failed_imports += 1

    console.print("\n[bold green]Import complete:[/bold green]")
    console.print(f"  - [green]Successful: {successful_imports}[/green]")
    console.print(f"  - [red]Failed: {failed_imports}[/red]")


@app.command(name="export")
def export_pack(
    output: str = typer.Option(
        ..., "--output", "-o", help="Output file path for the exported memory pack."
    ),
    tags: Optional[List[str]] = typer.Option(
        None, "--tags", "-t", help="Filter memories by tags (comma-separated)."
    ),
):
    """
    (Planned) Exports memories from the RAE Memory Engine to a JSON file.
    """
    console.print(
        "[bold yellow]Export functionality is planned but not yet implemented.[/bold yellow]"
    )
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
