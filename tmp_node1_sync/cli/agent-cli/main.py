import json
import os

import requests
import typer

app = typer.Typer(help="A CLI for interacting with the RAE API.")


def _get_api_url() -> str:
    return os.environ.get("RAE_API_URL", "http://localhost:8000")


def _get_api_key() -> str:
    return os.environ.get("RAE_API_KEY", "test-key")


@app.command()
def health():
    """Checks the health of the RAE API."""
    url = f"{_get_api_url()}/health"
    try:
        r = requests.get(url)
        r.raise_for_status()
        print(r.json())
    except requests.RequestException as e:
        print(f"Error connecting to API at {url}: {e}")


@app.command()
def store(
    content: str = typer.Argument(..., help="The text content of the memory."),
    tenant: str = typer.Option(..., "--tenant", "-t", help="The tenant ID."),
    project: str = typer.Option(..., "--project", "-p", help="The project ID."),
    source: str = typer.Option("cli", help="The source of the memory."),
    layer: str = typer.Option("ltm", help="The memory layer (e.g., 'em', 'sm', 'rm')."),
):
    """Stores a new memory in the RAE."""
    headers = {"X-Tenant-Id": tenant, "X-API-Key": _get_api_key()}
    payload = {
        "content": content,
        "source": source,
        "layer": layer,
        "project": project,
    }
    url = f"{_get_api_url()}/v1/memory/store"
    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
    except requests.RequestException as e:
        print(f"Error storing memory: {e}")


@app.command()
def query(
    query_text: str = typer.Argument(..., help="The search query."),
    tenant: str = typer.Option(..., "--tenant", "-t", help="The tenant ID."),
    k: int = typer.Option(10, help="Number of results to return."),
):
    """Queries for memories in the RAE."""
    headers = {"X-Tenant-Id": tenant, "X-API-Key": _get_api_key()}
    payload = {"query_text": query_text, "k": k}
    url = f"{_get_api_url()}/v1/memory/query"
    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except requests.RequestException as e:
        print(f"Error querying memory: {e}")


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="The prompt for the agent."),
    tenant: str = typer.Option(..., "--tenant", "-t", help="The tenant ID."),
    project: str = typer.Option(..., "--project", "-p", help="The project ID."),
):
    """Asks the RAE agent a question."""
    headers = {"X-Tenant-Id": tenant, "X-API-Key": _get_api_key()}
    payload = {
        "tenant_id": tenant,
        "project": project,
        "prompt": prompt,
    }
    url = f"{_get_api_url()}/v1/agent/execute"
    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except requests.RequestException as e:
        print(f"Error executing agent: {e}")


if __name__ == "__main__":
    app()
