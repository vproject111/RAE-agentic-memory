# RAE-First Architecture Implementation Guide

> **Core Principle**: "Agents do not talk to users. Agents talk to RAE via typed actions. RAE talks to users."

## 1. The Contract

All Agents MUST implement `BaseAgent` and return `AgentAction`.

```python
from rae_core.interfaces.agent import BaseAgent
from rae_core.models.interaction import RAEInput, AgentAction, AgentActionType

class MyAgent(BaseAgent):
    async def run(self, input_payload: RAEInput) -> AgentAction:
        # PURE LOGIC ONLY
        # NO print(), NO save_memory(), NO direct IO.
        
        return AgentAction(
            type=AgentActionType.FINAL_ANSWER,
            content="Calculated result: 42",
            confidence=1.0,
            reasoning="Standard arithmetic"
        )
```

## 2. The Runtime (OS)

The `RAERuntime` handles the dirty work: memory persistence, logging, policy checks.

```python
runtime = RAERuntime(storage=rae_storage, agent=MyAgent())
result = await runtime.process(input_payload)
# At this point, memory is ALREADY saved.
```

## 3. Memory Policy (Automatic)

- **Final Answer**: Automatically stored as `episodic` memory.
- **Thought (with decision)**: Automatically stored as `working` memory.
- **Constraint Violation**: Rejected by Runtime.

## 4. Enforcement

Trying to bypass this architecture will raise exceptions:
- `NotImplementedError` if `print()` or `save_memory()` is called.
- `TypeError` if a `str` is returned instead of `AgentAction`.
