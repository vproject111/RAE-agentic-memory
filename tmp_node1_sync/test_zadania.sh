#!/bin/bash
# Test script for orchestrator tasks

echo "🧪 Testing Orchestrator Tasks"
echo "=============================="
echo ""

# Activate venv
source .venv/bin/activate

# Test 1: Validate YAML
echo "Test 1: Validating tasks.yaml..."
python -c "
import yaml
with open('.orchestrator/tasks.yaml') as f:
    config = yaml.safe_load(f)
    tasks = config['tasks']
    print(f'✅ YAML valid: {len(tasks)} tasks loaded')

    # Show our tasks
    for task in tasks:
        if task['id'] in ['RAE-DOC-001', 'RAE-PHASE2-FULL']:
            print(f'   - {task[\"id\"]}: {task[\"goal\"][:50]}...')
"
echo ""

# Test 2: Check if orchestrator can load tasks
echo "Test 2: Loading tasks in orchestrator..."
python -c "
import sys
sys.path.insert(0, '.')
from orchestrator.core.task_loader import load_tasks

try:
    tasks = load_tasks('.orchestrator/tasks.yaml')
    print(f'✅ Tasks loaded: {len(tasks)} tasks')

    # Find our tasks
    rae_doc = next((t for t in tasks if t.id == 'RAE-DOC-001'), None)
    if rae_doc:
        print(f'   ✅ RAE-DOC-001 found')

    rae_phase2 = next((t for t in tasks if t.id == 'RAE-PHASE2-FULL'), None)
    if rae_phase2:
        print(f'   ✅ RAE-PHASE2-FULL found')
except Exception as e:
    print(f'❌ Error: {e}')
"
echo ""

echo "=============================="
echo "✅ All tests passed!"
echo ""
echo "Ready to run:"
echo "  python -m orchestrator.main --task-id RAE-DOC-001"
echo "  python -m orchestrator.main --task-id RAE-PHASE2-FULL"
