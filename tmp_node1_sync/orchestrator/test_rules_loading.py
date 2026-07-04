"""Test if orchestrator agents load project rules correctly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.adapters.base import TaskComplexity, TaskRisk
from orchestrator.agents.base import AgentTask, BaseAgent


class TestAgent(BaseAgent):
    """Test agent implementation."""

    async def execute(self, task: AgentTask):
        """Dummy execute method."""
        pass


def test_rules_loading():
    """Test that rules are loaded and included in prompts."""
    print("🧪 Test: Project Rules Loading")
    print("=" * 60)

    # Create test agent
    agent = TestAgent(name="Test-Agent", role="tester")

    # Create test task
    task = AgentTask(
        task_id="TEST-001",
        description="Test task",
        context={"test": "value"},
        complexity=TaskComplexity.SMALL,
        risk=TaskRisk.LOW,
        working_directory=str(Path(__file__).parent.parent),
    )

    # Build prompt (should include rules)
    prompt = agent._build_base_prompt(task)

    print("\n📋 Generated Prompt Length:", len(prompt), "characters")
    print("\n✅ Checking for project rules...")

    # Check if rules are included
    checks = {
        "PROJECT RULES AND GUIDELINES": False,
        "CRITICAL_AGENT_RULES.md": False,
        "CONVENTIONS.md": False,
        "AUTONOMOUS_OPERATIONS.md": False,
        "BRANCH_STRATEGY.md": False,
        "PROJECT_STRUCTURE.md": False,
        "END OF PROJECT RULES": False,
    }

    for marker in checks.keys():
        if marker in prompt:
            checks[marker] = True
            print(f"  ✅ Found: {marker}")
        else:
            print(f"  ❌ Missing: {marker}")

    # Show first 500 chars of prompt
    print("\n📄 Prompt Preview (first 500 chars):")
    print("-" * 60)
    print(prompt[:500])
    print("...")
    print("-" * 60)

    # Count how many rules files were loaded
    found_count = sum(1 for k, v in checks.items() if ".md" in k and v)
    print(f"\n📊 Rules Files Loaded: {found_count}/5")

    # Overall result
    has_rules_section = (
        checks["PROJECT RULES AND GUIDELINES"] and checks["END OF PROJECT RULES"]
    )

    if has_rules_section and found_count >= 3:
        print("\n✅ SUCCESS: Rules loading works correctly!")
        print(f"   Loaded {found_count} documentation files into agent prompt")
        return True
    else:
        print("\n❌ FAILED: Rules not properly loaded")
        return False


if __name__ == "__main__":
    success = test_rules_loading()
    sys.exit(0 if success else 1)
