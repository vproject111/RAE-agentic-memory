"""
RAE Quickstart - Interactive Tutorial
======================================

This script walks you through RAE's core features step by step.
Perfect for first-time users!

Run with: python examples/quickstart.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError:
    print("❌ Error: 'rich' library not installed")
    print("Install with: pip install rich")
    sys.exit(1)

try:
    from sdk.python.rae_memory_sdk.client import MemoryClient
except ImportError:
    print("❌ Error: RAE SDK not found")
    print("Install with: pip install -e sdk/python/rae_memory_sdk")
    sys.exit(1)

console = Console()


def print_header():
    """Print welcome banner"""
    banner = """
    ╔═══════════════════════════════════════════════════╗
    ║   🧠 RAE - Reflective Agentic Memory Engine      ║
    ║   Interactive Quickstart Tutorial                ║
    ╚═══════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_step(number: int, title: str):
    """Print step header"""
    console.print(f"\n[bold blue]Step {number}:[/bold blue] {title}", style="bold")


async def check_api_connection():
    """Check if RAE API is running"""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=3.0)
            if response.status_code == 200:
                return True
    except Exception:
        pass

    return False


async def main():
    print_header()

    console.print(
        Panel.fit(
            "This tutorial will show you how to:\n\n"
            "1. ✅ Connect to RAE\n"
            "2. 💾 Store memories\n"
            "3. 🔍 Query with semantic search\n"
            "4. 🕸️  Build knowledge graphs\n"
            "5. 🤔 Generate reflections",
            title="📚 What You'll Learn",
            border_style="green",
        )
    )

    console.print("\n[dim]Press Ctrl+C at any time to exit[/dim]\n")

    # Step 1: Check connection
    print_step(1, "Checking RAE API connection")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Connecting to RAE API...", total=None)

        api_running = await check_api_connection()

        if not api_running:
            console.print("\n[bold red]❌ RAE API is not running![/bold red]")
            console.print("\nTo start RAE, run:")
            console.print("  [cyan]make start[/cyan]  (if Docker installed)")
            console.print("  or")
            console.print("  [cyan]docker compose up -d[/cyan]\n")
            return

        progress.update(task, completed=True)

    console.print("✅ Connected to RAE API at http://localhost:8000\n")

    # Initialize client
    print_step(2, "Initializing RAE client")

    client = MemoryClient(
        api_url="http://localhost:8000",
        tenant_id="quickstart-demo",
        project_id="my-first-agent",
    )

    console.print("✅ Client initialized!")
    console.print("  Tenant ID: [cyan]quickstart-demo[/cyan]")
    console.print("  Project ID: [cyan]my-first-agent[/cyan]\n")

    # Step 3: Store memories
    print_step(3, "Storing sample memories")

    memories = [
        {
            "content": "User prefers dark mode in all applications",
            "tags": ["preference", "ui"],
        },
        {
            "content": "User is learning Python and FastAPI",
            "tags": ["skill", "learning"],
        },
        {
            "content": "User's favorite coffee is cappuccino",
            "tags": ["preference", "personal"],
        },
        {
            "content": "User had a bug with async/await in authentication module",
            "tags": ["bug", "auth", "async"],
        },
        {
            "content": "User fixed the bug by adding proper exception handling",
            "tags": ["solution", "auth"],
        },
    ]

    stored_ids = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Storing memories...", total=len(memories))

        for i, memory in enumerate(memories, 1):
            try:
                response = await client.store_memory(
                    content=memory["content"], layer="episodic", tags=memory["tags"]
                )
                stored_ids.append(response.get("id"))
                console.print(f"  {i}. [green]✓[/green] {memory['content'][:60]}...")
                progress.advance(task)
            except Exception as e:
                console.print(f"  {i}. [red]✗[/red] Error: {e}")

    console.print(f"\n✅ Stored {len(stored_ids)} memories!\n")

    # Step 4: Query memories
    print_step(4, "Semantic search")

    queries = [
        "What programming issues did the user face?",
        "What are the user's preferences?",
        "What technologies is the user learning?",
    ]

    for query in queries:
        console.print(f"\n[bold]Query:[/bold] [italic]{query}[/italic]")

        try:
            results = await client.query_memory(query=query, top_k=3)

            if results:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Score", width=8)
                table.add_column("Content", width=60)
                table.add_column("Tags", width=20)

                for result in results:
                    score = result.get("score", 0)
                    content = result.get("content", "")[:60]
                    tags = ", ".join(result.get("tags", [])[:3])

                    table.add_row(f"{score:.3f}", content, tags)

                console.print(table)
            else:
                console.print("  [dim]No results found[/dim]")

        except Exception as e:
            console.print(f"  [red]Error:[/red] {e}")

    console.print("\n✅ Semantic search works!\n")

    # Step 5: Knowledge Graph
    print_step(5, "Knowledge Graph (GraphRAG)")

    console.print("📊 Building knowledge graph from memories...")
    console.print("[dim](This feature requires graph extraction to be enabled)[/dim]\n")

    try:
        # Try to query with graph enabled
        graph_results = await client.hybrid_search(
            query="authentication and bugs", use_graph=True, graph_depth=2, top_k=5
        )

        if graph_results:
            console.print("✅ Knowledge graph query successful!")
            console.print(
                f"  Found {len(graph_results.get('vector_matches', []))} vector matches"
            )
            console.print(
                f"  Found {len(graph_results.get('graph_nodes', []))} graph nodes"
            )
            console.print(
                f"  Found {len(graph_results.get('graph_edges', []))} graph edges\n"
            )
        else:
            console.print("[yellow]⚠️  GraphRAG not yet configured[/yellow]")
            console.print("  See docs for setup instructions\n")

    except Exception as e:
        console.print(f"[yellow]⚠️  GraphRAG not available: {e}[/yellow]\n")

    # Step 6: Reflection
    print_step(6, "Generating AI reflection")

    console.print("🤔 Analyzing memories to extract insights...")
    console.print("[dim](This uses an LLM to generate insights)[/dim]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating reflection...", total=None)

            reflection = await client.generate_reflection(memory_limit=50)

            progress.update(task, completed=True)

        if reflection:
            console.print(
                Panel.fit(
                    reflection.get("content", "No reflection generated"),
                    title="🤔 AI-Generated Reflection",
                    border_style="green",
                )
            )
        else:
            console.print("[yellow]⚠️  Reflection generation not available[/yellow]")
            console.print("  Configure an LLM provider in .env\n")

    except Exception as e:
        console.print(f"[yellow]⚠️  Reflection not available: {e}[/yellow]")
        console.print("  Make sure you have an LLM API key configured\n")

    # Completion
    console.print("\n" + "=" * 60 + "\n")

    console.print(
        Panel.fit(
            "✨ [bold green]Tutorial Complete![/bold green] ✨\n\n"
            "You've successfully:\n"
            "✅ Connected to RAE\n"
            "✅ Stored memories\n"
            "✅ Performed semantic search\n"
            "✅ Explored knowledge graphs\n"
            "✅ Generated AI reflections",
            border_style="green",
        )
    )

    # Next steps
    console.print("\n[bold cyan]📚 Next Steps:[/bold cyan]\n")

    next_steps = [
        ("📖 Read the docs", "http://localhost:8000/docs"),
        ("📊 Open dashboard", "http://localhost:8501"),
        ("🔧 Try advanced examples", "examples/"),
        ("🔌 Setup IDE integration", "docs/guides/ide-integration.md"),
        ("💡 Explore use cases", "docs/examples/"),
    ]

    for step, link in next_steps:
        console.print(f"  • {step}: [link={link}]{link}[/link]")

    console.print(
        "\n[dim]💡 Tip: Run 'make help' to see all available commands[/dim]\n"
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Tutorial interrupted. Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        console.print(
            "\n[dim]If you need help, visit: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues[/dim]"
        )
        sys.exit(1)
