# 🤖 Claude Code Configuration

This directory contains configuration for [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) CLI.

## 📁 Files

### `settings.local.json` (gitignored)
**Your personal Claude Code permissions**
- Controls what commands Claude can run autonomously
- User-specific (not tracked in git)
- Created automatically on first run OR copied from `settings.example.json`

### `settings.example.json` (tracked)
**Template for new users**
- Contains comprehensive permissions for full autonomy
- Copy to `settings.local.json` on first setup
- Aligned with project's `AUTONOMOUS_OPERATIONS.md` policy

```bash
# Setup (first time only)
cp .claude/settings.example.json .claude/settings.local.json
```

### `hooks/` (tracked)
**Custom hooks for Claude Code events**
- `user-prompt-submit.sh` - Runs before every agent response
- Example: Check git status, run linters, validate tests

### `scripts/` (tracked)
**Helper scripts for automation**
- Used by hooks or manual operations

## 🔐 Permissions Philosophy

This project follows **maximum autonomy** within safety boundaries:

✅ **Allowed without asking**:
- All git operations (add, commit, push, pull, merge, rebase)
- All testing (pytest, make test-unit)
- File operations (mkdir, touch, cp, mv, rm)
- **File editing** (Write, Edit, Read within project)
- Python/pip operations (.venv/bin/*)
- Build tools (make, black, isort, ruff)
- Docker operations

❌ **Never allowed**:
- `sudo` (system-wide changes)
- Destructive operations outside project
- Force push to protected branches (enforced by GitHub)

📝 **Requires asking**:
- Architecture decisions
- Breaking API changes
- Risky operations beyond standard workflow

See `../docs/CLAUDE_CODE_AUTOMATION_FIX.md` for full details.

## 🚀 Quick Start

### New Clone Setup
```bash
# 1. Copy permissions
cp .claude/settings.example.json .claude/settings.local.json

# 2. Verify autonomy
git status  # Should not ask for permission
```

### Troubleshooting

**Problem**: Agent keeps asking for permission
**Solution**:
```bash
# Check if settings.local.json exists
ls -la .claude/settings.local.json

# If missing, copy from example
cp .claude/settings.example.json .claude/settings.local.json

# If exists, check it has all patterns
cat .claude/settings.local.json | grep "Bash(git:*)"
```

**Problem**: Too many permissions, want to restrict
**Solution**: Edit `.claude/settings.local.json`:
```json
{
  "permissions": {
    "allow": [
      "Bash(git status:*)",
      "Bash(git diff:*)"
      // Only allow these two
    ],
    "ask": [
      "Bash(git push:*)"  // Ask before pushing
    ]
  }
}
```

## 📊 Impact

With proper configuration:
- **0 permission prompts** during standard workflow
- **99%+ autonomy** for agent operations (Bash + file operations)
- **100% aligned** with `AUTONOMOUS_OPERATIONS.md`
- **Safe** - no sudo, scoped to project
- **50 command patterns** (47 Bash + 3 file operations)

## 📖 Documentation

- **Setup Guide**: This file
- **Full Details**: `../docs/CLAUDE_CODE_AUTOMATION_FIX.md`
- **Policy**: `../AUTONOMOUS_OPERATIONS.md`
- **Official Docs**: https://docs.anthropic.com/claude/docs/claude-code-permissions
