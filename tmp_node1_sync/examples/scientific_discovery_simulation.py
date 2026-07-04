"""
Scientific Discovery Simulation using RAE
-----------------------------------------
This script demonstrates the "Reflective Loop" in a scientific context.
It simulates an agent conducting experiments, encountering anomalies,
and using RAE's multi-layered memory to refine its hypothesis.

Requirements:
    pip install rae-sdk rich
"""

import asyncio
import time

from rich.console import Console
from rich.panel import Panel


# Mocking RAEClient for demonstration purposes if SDK is not fully installed in this environment
# In a real scenario: from rae_sdk import RAEClient
class MockRAEClient:
    def __init__(self):
        self.semantic_memory = {
            "Compound X": {"theory": "Accelerates reaction > 50C", "confidence": 0.95}
        }
        self.episodic_memory = []
        self.reflective_rules = []
        self.math_policy = {
            "alpha": 0.5,
            "beta": 0.5,
        }  # Alpha=Relevance, Beta=Importance

    async def retrieve(self, query, layer="semantic"):
        # Math-1: Operational Control (Simple Retrieval)
        print(f"   [Math-1] Calculating semantic similarity for '{query}'...")
        if "Compound X" in query and layer == "semantic":
            return self.semantic_memory["Compound X"]
        return None

    async def store_episode(self, action, outcome, metadata):
        # Sensory -> Episodic
        print(f"   [Sensory] Buffering input: {action} -> {outcome}")
        episode = {
            "action": action,
            "outcome": outcome,
            "timestamp": time.time(),
            "meta": metadata,
        }
        self.episodic_memory.append(episode)
        return episode

    async def run_reflection_loop(self, last_episode):
        # Math-3: Systemic Control (Surprise Detection)
        theory = self.semantic_memory["Compound X"]["theory"]
        surprise_score = 0.0

        if last_episode["outcome"] == "Failure" and "Accelerates" in theory:
            surprise_score = 0.9  # High Entropy

        print(
            f"   [Math-3] Calculated Surprise Score: {surprise_score:.4f} (Threshold: 0.7)"
        )

        if surprise_score > 0.7:
            print("   [Reflection] Triggering Reflection Engine due to anomaly...")
            await asyncio.sleep(0.5)

            # Reflection Logic: Correlate with past ignored data
            new_insight = "Compound X is humidity-sensitive (correlated with high humidity in metadata)"
            self.reflective_rules.append(new_insight)

            # Math-2: Strategic Control (Policy Update)
            print("   [Math-2] Updating Retrieval Policy (MAB Reward Signal Received)")
            self.math_policy["beta"] = 0.8  # Increase importance of Metadata (Humidity)
            print(f"   [Math-2] New Policy Weights: {self.math_policy}")

            return new_insight
        return None


async def main():
    console = Console()
    client = MockRAEClient()

    console.print(
        Panel.fit("🧪 RAE Scientific Discovery Simulation", style="bold blue")
    )

    # Step 1: Hypothesis
    console.print(
        "\n[bold green]1. Hypothesis Generation (Semantic Memory)[/bold green]"
    )
    theory = await client.retrieve(
        "Expected reaction rate for Compound X?", layer="semantic"
    )
    console.print(
        f"Agent retrieves current theory: [italic]'{theory['theory']}'[/italic]"
    )

    # Step 2: Experimentation
    console.print("\n[bold green]2. Experimentation (Episodic Memory)[/bold green]")
    console.print("Agent runs experiment at 60°C... [bold red]FAILURE[/bold red]")
    episode = await client.store_episode(
        action="Test 60C",
        outcome="Failure",
        metadata={"humidity": "85%", "temp": "60C"},
    )

    # Step 3: Reflection & Adaptation
    console.print("\n[bold green]3. The Reflective Loop (Math-3 + Math-2)[/bold green]")
    insight = await client.run_reflection_loop(episode)

    if insight:
        console.print(f"\n[bold yellow]💡 NEW DISCOVERY:[/bold yellow] {insight}")
        console.print(
            "[dim]The agent has autonomousy refined its hypothesis and adjusted its search strategy for future experiments.[/dim]"
        )


if __name__ == "__main__":
    asyncio.run(main())
