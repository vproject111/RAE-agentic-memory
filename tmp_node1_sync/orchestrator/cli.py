"""CLI commands for orchestrator management."""

import json
from pathlib import Path

import click

from orchestrator.core import StateMachine, StepState, TaskState


@click.group()
def cli():
    """Orchestrator CLI - manage tasks and review queue."""
    pass


@cli.command()
def summary():
    """Show orchestrator summary."""
    state_machine = StateMachine()
    summary_data = state_machine.get_summary()

    click.echo("\n📊 Orchestrator Summary\n")
    click.echo(f"Total Tasks: {summary_data['total_tasks']}")
    click.echo(f"Active Tasks: {summary_data['active_tasks']}")
    click.echo(f"Needs Human Review: {summary_data['needs_human_review']}")
    click.echo(f"Total Cost: ${summary_data['total_cost_usd']:.4f}\n")

    click.echo("Tasks by State:")
    for state, count in summary_data["by_state"].items():
        click.echo(f"  {state}: {count}")
    click.echo()


@cli.command()
def review():
    """Show tasks needing human review."""
    state_machine = StateMachine()
    tasks = state_machine.get_tasks_needing_human_review()

    if not tasks:
        click.echo("✅ No tasks need human review!")
        return

    click.echo(f"\n🔍 {len(tasks)} task(s) need human review:\n")

    for task in tasks:
        click.echo(f"Task ID: {task.task_id}")
        click.echo(f"Goal: {task.task_def.get('goal', 'N/A')}")
        click.echo(f"Status: {task.state.value}")
        click.echo(f"Error: {task.error or 'N/A'}")

        if task.plan:
            click.echo(f"Plan Steps: {len(task.plan.get('steps', []))}")

        if task.plan_review:
            review_status = task.plan_review.get("status", "unknown")
            click.echo(f"Plan Review Status: {review_status}")
            if review_status == "rejected":
                concerns = task.plan_review.get("review", {}).get("concerns", [])
                if concerns:
                    click.echo("Concerns:")
                    for concern in concerns:
                        click.echo(f"  - {concern}")

        failed_steps = task.get_failed_steps()
        if failed_steps:
            click.echo(f"Failed Steps: {len(failed_steps)}")
            for step in failed_steps:
                click.echo(f"  - {step.step_id}: {step.error}")

        click.echo(f"Cost so far: ${task.total_cost_usd:.4f}")
        click.echo("-" * 60)
        click.echo()


@cli.command()
@click.argument("task_id")
@click.option("--approve", is_flag=True, help="Approve and continue task")
@click.option("--reject", is_flag=True, help="Reject and mark as failed")
@click.option("--details", is_flag=True, help="Show full details")
def task(task_id: str, approve: bool, reject: bool, details: bool):
    """Manage specific task."""
    state_machine = StateMachine()
    task_exec = state_machine.get_task(task_id)

    if not task_exec:
        click.echo(f"❌ Task {task_id} not found")
        return

    if details:
        # Show full task details
        click.echo(json.dumps(task_exec.to_dict(), indent=2))
        return

    if approve:
        # Approve task - move to next appropriate state
        if task_exec.state == TaskState.PLAN_REJECTED:
            state_machine.update_task_state(task_id, TaskState.PLAN_APPROVED)
            click.echo(f"✅ Task {task_id} plan approved - ready for implementation")
        elif task_exec.state == TaskState.AWAITING_HUMAN:
            state_machine.update_task_state(task_id, TaskState.IMPLEMENTING)
            click.echo(f"✅ Task {task_id} approved - continuing implementation")
        else:
            click.echo(f"⚠️  Cannot approve task in state: {task_exec.state.value}")
        return

    if reject:
        # Reject task - mark as failed
        state_machine.update_task_state(
            task_id, TaskState.FAILED, error="Rejected by human reviewer"
        )
        click.echo(f"❌ Task {task_id} rejected and marked as failed")
        return

    # Default: show task info
    click.echo(f"\nTask: {task_id}")
    click.echo(f"Goal: {task_exec.task_def.get('goal', 'N/A')}")
    click.echo(f"State: {task_exec.state.value}")
    click.echo(f"Risk: {task_exec.task_def.get('risk', 'N/A')}")
    click.echo(f"Area: {task_exec.task_def.get('area', 'N/A')}")

    if task_exec.plan:
        click.echo(f"\nPlan: {len(task_exec.plan.get('steps', []))} steps")
        if task_exec.plan.get("estimated_duration"):
            click.echo(f"Estimated Duration: {task_exec.plan['estimated_duration']}")

    if task_exec.steps:
        click.echo(f"\nSteps: {len(task_exec.steps)} total")
        for step in task_exec.steps:
            icon = {
                StepState.COMPLETED: "✅",
                StepState.FAILED: "❌",
                StepState.IMPLEMENTING: "🔄",
                StepState.PENDING: "⏳",
            }.get(step.state, "")
            click.echo(
                f"  {icon} {step.step_id}: {step.state.value} (attempt {step.attempt})"
            )

    click.echo(f"\nCost: ${task_exec.total_cost_usd:.4f}")
    click.echo(f"Started: {task_exec.started_at}")
    if task_exec.completed_at:
        click.echo(f"Completed: {task_exec.completed_at}")

    click.echo()


@cli.command()
@click.option("--force", is_flag=True, help="Force clean without confirmation")
def clean_state(force: bool):
    """Clean all task state (start fresh)."""
    if not force:
        click.confirm("⚠️  This will delete all task state. Are you sure?", abort=True)

    state_dir = Path("orchestrator/state")
    if state_dir.exists():
        count = 0
        for state_file in state_dir.glob("*.json"):
            state_file.unlink()
            count += 1
        click.echo(f"✅ Cleaned {count} task state file(s)")
    else:
        click.echo("ℹ️  No state directory found")


@cli.command()
def active():
    """Show active (in-progress) tasks."""
    state_machine = StateMachine()
    tasks = state_machine.get_active_tasks()

    if not tasks:
        click.echo("ℹ️  No active tasks")
        return

    click.echo(f"\n🔄 {len(tasks)} active task(s):\n")

    for task in tasks:
        click.echo(
            f"  [{task.state.value}] {task.task_id}: {task.task_def.get('goal', 'N/A')[:60]}"
        )

    click.echo()


@cli.command()
@click.option(
    "--state",
    type=click.Choice(["done", "failed", "awaiting_human"]),
    help="Filter by state",
)
def list_tasks(state: str):
    """List all tasks (optionally filtered by state)."""
    state_machine = StateMachine()

    if state:
        task_state = TaskState[state.upper()]
        tasks = state_machine.get_tasks_by_state(task_state)
        click.echo(f"\nTasks in state '{state}':\n")
    else:
        tasks = list(state_machine._tasks.values())
        click.echo("\nAll tasks:\n")

    if not tasks:
        click.echo("No tasks found")
        return

    for task in tasks:
        status_icon = {
            TaskState.DONE: "✅",
            TaskState.FAILED: "❌",
            TaskState.AWAITING_HUMAN: "🔍",
        }.get(task.state, "🔄")

        click.echo(f"{status_icon} {task.task_id}")
        click.echo(f"   Goal: {task.task_def.get('goal', 'N/A')[:60]}")
        click.echo(f"   State: {task.state.value}")
        click.echo(f"   Cost: ${task.total_cost_usd:.4f}")
        click.echo()


if __name__ == "__main__":
    cli()
