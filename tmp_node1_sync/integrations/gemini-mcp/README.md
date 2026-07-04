# Gemini MCP Server - Multi-Agent Collaboration with Shared Memory

MCP server that enables Claude Code to delegate tasks to Gemini CLI while maintaining **shared memory** through RAE.

## Key Features

- **Claude ↔ Gemini Delegation**: Claude can ask Gemini to handle simple tasks (planning, documentation, code review)
- **Shared Memory via RAE**: All interactions are recorded in RAE's episodic memory
- **Cost Optimization**: Gemini is FREE (within quota), Claude is paid - delegate wisely!
- **Multi-Agent Learning**: RAE can analyze collaboration patterns and suggest optimal task delegation

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code (via MCP)                                          │
│  "Can you ask Gemini to review this code?"                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ MCP Tool: run_gemini
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│  Gemini MCP Server                                              │
│  1. Record delegation to RAE: "Claude asked Gemini..."         │
│  2. Call Gemini CLI with prompt                                 │
│  3. Record response to RAE: "Gemini completed..."               │
│  4. Return result to Claude                                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
      ┌──────────────┴────────────────┐
      │                               │
      ↓                               ↓
┌──────────────┐              ┌─────────────────┐
│  Gemini CLI  │              │  RAE Memory API │
│  (Flash/Pro) │              │  Port 8001      │
└──────────────┘              └─────────────────┘
                                      │
                              ┌───────┴────────┐
                              │  Episodic      │
                              │  Memory:       │
                              │  - Delegations │
                              │  - Responses   │
                              │  - Patterns    │
                              └────────────────┘
```

## Installation

```bash
cd integrations/gemini-mcp
pip install -e .
```

## Configuration

### For Claude Code

Edit `~/.config/Claude/claude_desktop_config.json` (Linux) or equivalent:

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "/path/to/.venv/bin/rae-mcp-server",
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_API_KEY": "dev-key",
        "RAE_PROJECT_ID": "claude-code-project",
        "RAE_TENANT_ID": "claude-code"
      }
    },
    "gemini": {
      "command": "/path/to/.venv/bin/gemini-mcp-server",
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_API_KEY": "dev-key",
        "RAE_PROJECT_ID": "claude-code-project",
        "RAE_TENANT_ID": "claude-code"
      }
    }
  }
}
```

### Prerequisites

1. **Gemini CLI** must be installed and authenticated:
   ```bash
   npm install -g @google/generative-ai-cli
   gemini /auth
   ```

2. **RAE Memory API** must be running on port 8001:
   ```bash
   docker compose up rae-api
   ```

3. **Gemini Account Switcher** (optional, for quota rotation):
   ```bash
   .local/switch-gemini.sh [grzegorz|lili|marcel]
   ```

## Usage Examples

### Example 1: Code Review

**Claude Code user**:
```
Can you ask Gemini to review this function for best practices?

def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
```

**What happens**:
1. Claude uses `run_gemini` tool
2. Gemini MCP server records: "Claude delegated code review to Gemini"
3. Gemini CLI reviews the code
4. Gemini MCP server records: "Gemini completed review with suggestions"
5. Claude receives Gemini's feedback

**RAE Memory contains**:
```
[episodic] Claude delegated task to Gemini (flash): Review Python function...
[episodic] Gemini (flash) completed task: Suggested using sum() instead of loop
```

### Example 2: Planning

**Claude Code user**:
```
Use Gemini to create a high-level plan for implementing user authentication
```

**Result**:
- Gemini creates the plan (FREE)
- Claude can then implement the plan (paid, but with clear direction)
- RAE remembers the plan for future reference

### Example 3: Multi-Agent Workflow

**Claude Code user**:
```
1. Ask Gemini to suggest 3 different API designs
2. Then you (Claude) choose the best one and implement it
```

**Result**:
- Gemini generates 3 options (FREE)
- Claude analyzes and implements (paid, but focused work)
- RAE captures the entire decision-making process

## RAE Memory Benefits

### 1. Audit Trail
Every Claude<->Gemini interaction is logged:
```python
# Query RAE
search_memory("What did Gemini suggest for authentication?")

# Returns:
# "Gemini suggested OAuth 2.0 with JWT tokens..."
```

### 2. Pattern Learning
RAE can analyze which tasks work best with Gemini vs Claude:
```python
# RAE reflection might discover:
# "Simple planning tasks delegated to Gemini complete 3x faster
#  with no quality loss. Complex logic requires Claude."
```

### 3. Context Continuity
Future sessions can reference past Gemini work:
```python
# Days later, Claude can ask:
"Search RAE: What API design did we choose last week?"
# RAE returns the Gemini-suggested design that Claude implemented
```

## Cost Optimization Strategy

### When to Use Gemini (via MCP)

✅ **Good for Gemini**:
- Planning and brainstorming
- Simple code review
- Documentation writing
- Explaining concepts
- Generating test cases
- Refactoring suggestions

❌ **Avoid Gemini for**:
- Complex algorithm implementation
- Critical business logic
- Security-sensitive code
- Precise code generation
- Debugging intricate issues

### Cost Comparison

| Task Type | Claude Cost | Gemini Cost | Savings |
|-----------|-------------|-------------|---------|
| Planning (1000 tokens) | ~$0.003 | FREE | 100% |
| Code Review (2000 tokens) | ~$0.006 | FREE | 100% |
| Implementation (5000 tokens) | ~$0.015 | N/A | 0% |

**Strategy**: Use Gemini for 50% of tasks → **50% cost reduction**

## Quota Management

Gemini has daily quotas per account. If you hit the limit:

```bash
# Switch to another Gemini account (requires setup)
.local/switch-gemini.sh lili

# Or let Claude handle it (more expensive but always works)
```

**Error message when quota exceeded**:
```
⚠️  GEMINI QUOTA LIMIT EXCEEDED ⚠️

Limit dzienny wyczerpany na obecnym koncie.

Aby kontynuować:
1. Przełącz konto Gemini: .local/switch-gemini.sh [grzegorz|lili|marcel]
2. Uruchom ponownie zadanie

Alternatywnie: Claude może kontynuować samodzielnie
```

## Troubleshooting

### Issue: Gemini MCP server not found

```bash
# Verify installation
which gemini-mcp-server

# Reinstall if needed
cd integrations/gemini-mcp
pip install -e .
```

### Issue: RAE connection failed

```bash
# Check RAE API is running
curl http://localhost:8000/health

# Start RAE if needed
docker compose up -d rae-api
```

### Issue: Gemini CLI not authenticated

```bash
# Re-authenticate
gemini /auth

# Follow browser prompt to sign in
```

## Architecture: Multi-Agent Memory System

```
┌─────────────────────────────────────────────────────────────┐
│                   RAE Memory Engine                          │
│                                                              │
│  Episodic Memory:                                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │ • "Claude asked Gemini to review code..."          │    │
│  │ • "Gemini suggested using list comprehension"      │    │
│  │ • "Claude implemented Gemini's suggestion"         │    │
│  │ • "Claude asked Gemini to plan authentication"    │    │
│  │ • "Gemini proposed OAuth 2.0 + JWT"               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Working Memory:                                             │
│  • Current task context                                      │
│  • Active collaboration state                                │
│                                                              │
│  Semantic Memory (Reflections):                              │
│  • "Gemini excels at planning tasks"                         │
│  • "Claude handles complex logic better"                     │
│  • "Optimal delegation ratio: 60% Claude, 40% Gemini"       │
└─────────────────────────────────────────────────────────────┘
         ↑                                  ↑
         │                                  │
         │                                  │
    ┌────┴──────┐                      ┌───┴─────┐
    │  Claude   │ ← collaborates →     │ Gemini  │
    │  Code     │                       │  CLI    │
    └───────────┘                      └─────────┘
```

## Future Enhancements

1. **Automatic Task Routing**: RAE learns which model is best for each task type
2. **Confidence Scoring**: Gemini can ask Claude to verify uncertain responses
3. **Multi-Model Consensus**: Critical decisions reviewed by both models
4. **Cost Tracking**: RAE monitors spend and suggests optimizations

## Related Documentation

- [RAE MCP Server](../mcp/README.md) - Core RAE integration
- [Orchestrator](../../orchestrator/README.md) - Multi-agent orchestration
- [Gemini Account Switcher](../../.local/README.md) - Quota management

## License

Apache License 2.0
