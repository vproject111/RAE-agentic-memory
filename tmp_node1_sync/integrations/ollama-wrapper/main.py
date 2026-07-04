import json

import httpx
import typer
from rich.console import Console

from .config import settings

app = typer.Typer()
console = Console()


@app.command()
def chat(
    prompt: str,
    model: str = typer.Option(
        "llama3", "--model", "-m", help="The Ollama model to use."
    ),
):
    """
    Chat with an Ollama model, using RAE for memory.
    """
    console.print(f"[bold blue]User prompt:[/bold blue] {prompt}")
    console.print(f"[bold blue]Using model:[/bold blue] {model}")

    # 1. Query RAE Memory API for context
    context_block = ""
    try:
        console.print("\n[yellow]1. Querying RAE for context...[/yellow]")
        headers = {
            "X-Tenant-Id": settings.RAE_TENANT_ID,
            "X-API-Key": settings.RAE_API_KEY,
        }
        payload = {"query_text": prompt, "k": 5}

        with httpx.Client() as client:
            response = client.post(
                f"{settings.RAE_API_URL}/v1/memory/query", json=payload, headers=headers
            )
            response.raise_for_status()

            query_response = response.json()
            if query_response.get("results"):
                context_block = "\n".join(
                    [f"- {item['content']}" for item in query_response["results"]]
                )
                console.print("[green]  - Context found.[/green]")
            else:
                console.print("[green]  - No relevant context found.[/green]")

    except httpx.HTTPStatusError as e:
        console.print(
            f"[bold red]Error querying RAE API: {e.response.status_code}[/bold red]"
        )
        console.print(e.response.text)
        raise typer.Exit(1)
    except Exception as e:
        console.print(
            f"[bold red]An unexpected error occurred while querying RAE: {e}[/bold red]"
        )
        raise typer.Exit(1)

    # 2. Construct the final prompt
    final_prompt = f"""Based on the following context, answer the user's query. If the context is not relevant, ignore it.

Context:
{context_block}

---

User query: {prompt}
"""

    # 3. Call Ollama API and stream the response
    try:
        console.print("\n[yellow]2. Sending prompt to Ollama...[/yellow]\n")
        with httpx.stream(
            "POST",
            f"{settings.OLLAMA_API_URL}/api/generate",
            json={"model": model, "prompt": final_prompt, "stream": True},
            timeout=None,
        ) as response:
            response.raise_for_status()

            console.print("[bold green]Ollama's Answer:[/bold green]")
            full_response = ""
            for chunk in response.iter_text():
                try:
                    data = json.loads(chunk)
                    part = data.get("response", "")
                    full_response += part
                    print(part, end="", flush=True)
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    console.print(
                        f"[bold red]Error decoding JSON chunk: {chunk}[/bold red]"
                    )

        console.print("\n")

    except httpx.HTTPStatusError as e:
        console.print(
            f"[bold red]Error calling Ollama API: {e.response.status_code}[/bold red]"
        )
        console.print(e.response.text)
        raise typer.Exit(1)
    except Exception as e:
        console.print(
            f"[bold red]An unexpected error occurred while calling Ollama: {e}[/bold red]"
        )
        raise typer.Exit(1)

    # 4. (Optional) Trigger reflection hook in RAE
    # This can be implemented later.


if __name__ == "__main__":
    app()
