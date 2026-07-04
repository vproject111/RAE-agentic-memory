"""Performance dashboard CLI for orchestrator intelligence.

Displays performance metrics, model rankings, and optimization recommendations.
"""

import logging

import click

from .analytics import PerformanceAnalytics
from .performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


class PerformanceDashboard:
    """Interactive dashboard for performance metrics."""

    def __init__(self, tracker: PerformanceTracker):
        """Initialize dashboard.

        Args:
            tracker: Performance tracker
        """
        self.tracker = tracker
        self.analytics = PerformanceAnalytics(tracker)

    def show_summary(self):
        """Display performance summary."""
        stats = self.tracker.get_statistics()

        click.echo("\n" + "=" * 60)
        click.echo("📊 ORCHESTRATOR PERFORMANCE SUMMARY")
        click.echo("=" * 60 + "\n")

        # Overall metrics
        click.echo(f"Total Tasks: {stats['total_tasks']}")
        click.echo(
            f"  ✅ Successful: {stats['successful']} ({stats['success_rate']:.1%})"
        )
        click.echo(f"  ❌ Failed: {stats['failed']}")
        click.echo(f"  ⚠️  Partial: {stats['partial']}")
        click.echo(f"  🔍 Human Review: {stats['human_review']}")

        click.echo("\n💰 Cost Metrics:")
        click.echo(f"  Total Cost: ${stats['total_cost']:.2f}")
        click.echo(f"  Average Cost: ${stats['avg_cost']:.4f} per task")

        click.echo("\n⏱️  Duration Metrics:")
        click.echo(f"  Total Duration: {stats['total_duration']:.0f}s")
        click.echo(f"  Average Duration: {stats['avg_duration']:.1f}s per task")

    def show_provider_comparison(self):
        """Display provider performance comparison."""
        comparison = self.analytics.get_provider_comparison()

        if not comparison:
            click.echo("\n⚠️  No provider data available")
            return

        click.echo("\n" + "=" * 60)
        click.echo("🏆 PROVIDER PERFORMANCE COMPARISON")
        click.echo("=" * 60 + "\n")

        # Sort by success rate
        providers = sorted(
            comparison.items(), key=lambda x: x[1]["success_rate"], reverse=True
        )

        for provider, metrics in providers:
            success_icon = "✅" if metrics["success_rate"] >= 0.8 else "⚠️"

            click.echo(f"{success_icon} {provider.upper()}")
            click.echo(f"  Tasks: {metrics['total_tasks']}")
            click.echo(f"  Success Rate: {metrics['success_rate']:.1%}")
            click.echo(f"  Avg Cost: ${metrics['avg_cost']:.4f}")
            click.echo(f"  Avg Duration: {metrics['avg_duration']:.1f}s")
            click.echo()

    def show_model_rankings(self, task_area: str, task_risk: str):
        """Display model rankings for a task type.

        Args:
            task_area: Task area
            task_risk: Risk level
        """
        click.echo("\n" + "=" * 60)
        click.echo(f"📈 MODEL RANKINGS: {task_area.upper()} / {task_risk.upper()}")
        click.echo("=" * 60 + "\n")

        # Planner rankings
        click.echo("PLANNER MODELS (by success rate):")
        planner_ranks = self.analytics.rank_models_for_task(
            task_area, task_risk, "planner", metric="success_rate"
        )

        if planner_ranks:
            for i, (model_id, success_rate) in enumerate(planner_ranks[:5], 1):
                icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
                click.echo(f"  {icon} {model_id}: {success_rate:.1%}")
        else:
            click.echo("  ⚠️  Insufficient data")

        # Implementer rankings
        click.echo("\nIMPLEMENTER MODELS (by success rate):")
        impl_ranks = self.analytics.rank_models_for_task(
            task_area, task_risk, "implementer", metric="success_rate"
        )

        if impl_ranks:
            for i, (model_id, success_rate) in enumerate(impl_ranks[:5], 1):
                icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
                click.echo(f"  {icon} {model_id}: {success_rate:.1%}")
        else:
            click.echo("  ⚠️  Insufficient data")

    def show_optimization_opportunities(self):
        """Display cost optimization recommendations."""
        opportunities = self.analytics.identify_optimization_opportunities()

        click.echo("\n" + "=" * 60)
        click.echo("💡 OPTIMIZATION OPPORTUNITIES")
        click.echo("=" * 60 + "\n")

        if not opportunities:
            click.echo(
                "✨ No optimization opportunities found - routing is already optimal!"
            )
            return

        for i, opp in enumerate(opportunities[:5], 1):
            click.echo(
                f"#{i} {opp['task_area'].upper()} / {opp['task_risk'].upper()} ({opp['role']})"
            )
            click.echo(
                f"  Current: {opp['current_model']} (${opp['current_cost']:.4f}, {opp['current_success_rate']:.1%})"
            )
            click.echo(
                f"  Recommended: {opp['recommended_model']} (${opp['new_cost']:.4f}, {opp['new_success_rate']:.1%})"
            )
            click.echo(f"  💰 Savings: ${opp['savings_per_task']:.4f} per task")
            click.echo()

        total_savings = sum(opp["savings_per_task"] for opp in opportunities)
        click.echo(f"Total potential savings: ${total_savings:.4f} per task")

    def show_task_pattern(self, task_area: str, task_risk: str):
        """Display detailed analysis of a task pattern.

        Args:
            task_area: Task area
            task_risk: Risk level
        """
        pattern = self.analytics.analyze_task_pattern(task_area, task_risk)

        if not pattern:
            click.echo(f"\n⚠️  Insufficient data for {task_area}/{task_risk}")
            return

        click.echo("\n" + "=" * 60)
        click.echo(
            f"🔍 TASK PATTERN ANALYSIS: {task_area.upper()} / {task_risk.upper()}"
        )
        click.echo("=" * 60 + "\n")

        click.echo(f"Total Attempts: {pattern.total_attempts}")
        click.echo(
            f"  ✅ Successful: {pattern.successful} ({pattern.success_rate:.1%})"
        )
        click.echo(f"  ❌ Failed: {pattern.failed}")

        if pattern.best_planner:
            model, success_rate = pattern.best_planner
            click.echo(f"\n🏆 Best Planner: {model} ({success_rate:.1%})")

        if pattern.best_implementer:
            model, success_rate = pattern.best_implementer
            click.echo(f"🏆 Best Implementer: {model} ({success_rate:.1%})")

        click.echo("\n💰 Cost Analysis:")
        click.echo(f"  Average: ${pattern.avg_cost:.4f}")
        click.echo(f"  Min: ${pattern.min_cost:.4f}")
        click.echo(f"  Max: ${pattern.max_cost:.4f}")

        click.echo("\n⏱️  Duration Analysis:")
        click.echo(f"  Average: {pattern.avg_duration:.1f}s")
        click.echo(f"  Min: {pattern.min_duration:.1f}s")
        click.echo(f"  Max: {pattern.max_duration:.1f}s")

        if pattern.common_errors:
            click.echo("\n⚠️  Common Errors:")
            for error_type, count in pattern.common_errors[:3]:
                click.echo(f"  - {error_type}: {count} occurrences")

    def show_model_performance(self, model_id: str, role: str = "any"):
        """Display detailed performance metrics for a model.

        Args:
            model_id: Model identifier
            role: Role filter
        """
        perf = self.analytics.analyze_model_performance(model_id, role)

        if not perf:
            click.echo(f"\n⚠️  Insufficient data for model: {model_id}")
            return

        click.echo("\n" + "=" * 60)
        click.echo(f"📊 MODEL PERFORMANCE: {model_id}")
        click.echo(f"Provider: {perf.provider} | Role: {perf.role}")
        click.echo("=" * 60 + "\n")

        click.echo(f"Total Tasks: {perf.total_tasks}")
        click.echo(
            f"  ✅ Successful: {perf.successful_tasks} ({perf.success_rate:.1%})"
        )
        click.echo(f"  ❌ Failed: {perf.failed_tasks}")

        click.echo("\n💰 Cost Metrics:")
        click.echo(f"  Total Cost: ${perf.total_cost:.2f}")
        click.echo(f"  Average Cost: ${perf.avg_cost_per_task:.4f} per task")

        click.echo("\n⏱️  Duration Metrics:")
        click.echo(f"  Total Duration: {perf.total_duration:.0f}s")
        click.echo(f"  Average Duration: {perf.avg_duration:.1f}s per task")

        click.echo("\n✅ Quality Metrics:")
        click.echo(f"  Quality Gate Pass Rate: {perf.quality_gate_pass_rate:.1%}")
        click.echo(f"  Code Review Pass Rate: {perf.code_review_pass_rate:.1%}")
        click.echo(f"  Average Retries: {perf.avg_retries:.1f}")

        if perf.by_area:
            click.echo("\n📁 Tasks by Area:")
            for area, count in sorted(
                perf.by_area.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                click.echo(f"  {area}: {count}")

        if perf.by_risk:
            click.echo("\n⚠️  Tasks by Risk:")
            for risk, count in sorted(
                perf.by_risk.items(), key=lambda x: x[1], reverse=True
            ):
                click.echo(f"  {risk}: {count}")


# CLI Commands


@click.group()
def intelligence_cli():
    """Orchestrator intelligence and analytics commands."""
    pass


@intelligence_cli.command()
@click.option(
    "--storage-dir",
    default="orchestrator/intelligence/data",
    help="Performance data directory",
)
def summary(storage_dir: str):
    """Show performance summary."""
    tracker = PerformanceTracker(storage_dir=storage_dir)
    dashboard = PerformanceDashboard(tracker)
    dashboard.show_summary()
    dashboard.show_provider_comparison()


@intelligence_cli.command()
@click.option(
    "--storage-dir",
    default="orchestrator/intelligence/data",
    help="Performance data directory",
)
def optimize(storage_dir: str):
    """Show optimization opportunities."""
    tracker = PerformanceTracker(storage_dir=storage_dir)
    dashboard = PerformanceDashboard(tracker)
    dashboard.show_optimization_opportunities()


@intelligence_cli.command()
@click.argument("task_area")
@click.argument("task_risk")
@click.option(
    "--storage-dir",
    default="orchestrator/intelligence/data",
    help="Performance data directory",
)
def rankings(task_area: str, task_risk: str, storage_dir: str):
    """Show model rankings for a task type."""
    tracker = PerformanceTracker(storage_dir=storage_dir)
    dashboard = PerformanceDashboard(tracker)
    dashboard.show_model_rankings(task_area, task_risk)
    dashboard.show_task_pattern(task_area, task_risk)


@intelligence_cli.command()
@click.argument("model_id")
@click.option("--role", default="any", help="Role: planner, implementer, or any")
@click.option(
    "--storage-dir",
    default="orchestrator/intelligence/data",
    help="Performance data directory",
)
def model(model_id: str, role: str, storage_dir: str):
    """Show detailed performance for a model."""
    tracker = PerformanceTracker(storage_dir=storage_dir)
    dashboard = PerformanceDashboard(tracker)
    dashboard.show_model_performance(model_id, role)


if __name__ == "__main__":
    intelligence_cli()
