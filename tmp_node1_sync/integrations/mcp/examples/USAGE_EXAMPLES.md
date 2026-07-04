# RAE MCP Server - Usage Examples

## Table of Contents

- [Basic Setup](#basic-setup)
- [Tool Usage Examples](#tool-usage-examples)
- [Resource Usage Examples](#resource-usage-examples)
- [Prompt Usage Examples](#prompt-usage-examples)
- [Advanced Scenarios](#advanced-scenarios)

---

## Basic Setup

### 1. Start RAE API

Ensure RAE Memory API is running:

```bash
# From project root
docker compose up -d

# Or run directly
cd apps/memory-api
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Configure Environment

Create `.env` file:

```bash
cp examples/.env.example .env
# Edit .env with your settings
```

### 3. Install MCP Server

```bash
cd integrations/mcp-server
pip install -e .
```

### 4. Configure IDE

Choose your IDE and follow the configuration:

#### Claude Desktop (macOS)

```bash
# Copy config to Claude Desktop
cp examples/configs/claude-desktop-config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Cursor

```bash
# Add to your project's .cursor/config.json
cat examples/configs/cursor-config.json
```

#### Cline (VSCode)

```bash
# Add to Cline extension settings
cat examples/configs/cline-config.json
```

---

## Tool Usage Examples

### Example 1: Saving Design Decisions

**User Input:**
```
Please save this architectural decision to memory:

We've decided to use PostgreSQL with pgvector for our vector database
because it provides excellent integration with our existing infrastructure
and supports ACID transactions which are critical for our use case.

The alternatives considered were:
- Qdrant: Better performance but requires separate service
- Weaviate: Good features but adds complexity
- Pinecone: Cloud-only, not self-hostable

Tags: architecture, database, decision
Layer: semantic
```

**AI Response:**
```
I'll save that architectural decision to RAE memory.

[Uses save_memory tool]

✓ Memory stored successfully
ID: mem-abc123
Layer: semantic
Tags: architecture, database, decision

This decision has been recorded and will be available for future reference.
```

### Example 2: Searching for Past Decisions

**User Input:**
```
What database technologies have we considered for this project?
```

**AI Response:**
```
Let me search our memory for database-related decisions.

[Uses search_memory tool with query "database technologies decisions"]

Found 3 relevant memories:

1. [Score: 0.95]
   Source: architecture-decisions
   Tags: architecture, database, decision
   Content: We've decided to use PostgreSQL with pgvector for our vector database...

2. [Score: 0.87]
   Source: team-meeting-notes
   Tags: database, performance
   Content: Discussed database performance optimization strategies...

3. [Score: 0.82]
   Source: tech-spike-results
   Tags: database, research
   Content: Completed spike on vector database options...

Based on our memory, we've considered PostgreSQL with pgvector (chosen),
Qdrant, Weaviate, and Pinecone for our vector database needs.
```

### Example 3: Getting File Context

**User Input:**
```
I need to modify auth.py. What should I know about this file?
```

**AI Response:**
```
Let me check the historical context for auth.py.

[Uses get_related_context tool with file_path="auth.py"]

Historical context for: auth.py
Found 5 related items:

1. [2025-11-15 10:30:00]
   Added JWT token validation with RSA256 algorithm.
   Fixed security vulnerability CVE-2024-XXXX.

2. [2025-11-10 14:20:00]
   Refactored authentication middleware to support multiple tenants.
   Each tenant now has isolated authentication context.

3. [2025-11-05 09:15:00]
   Initial implementation of OAuth2 password flow.
   Uses bcrypt for password hashing with cost factor 12.

Key things to know:
- The file uses JWT with RSA256 for token validation
- Multi-tenant authentication is supported
- Recent security fix was applied
- Password hashing uses bcrypt with cost 12
```

### Example 4: Recording Bug Fixes

**User Input:**
```
Save to memory:
Fixed a race condition in the cache invalidation logic.
The issue occurred when multiple workers tried to invalidate
the same cache key simultaneously, causing inconsistent state.

Solution: Added a distributed lock using Redis before cache operations.

Tags: bugfix, cache, redis, concurrency
Layer: episodic
```

**AI Response:**
```
I'll record this bug fix for future reference.

[Uses save_memory tool]

✓ Memory stored successfully
ID: mem-def456
Layer: episodic
Tags: bugfix, cache, redis, concurrency

This fix has been documented and will help prevent similar issues in the future.
```

---

## Resource Usage Examples

### Example 5: Accessing Project Reflection

**User Input:**
```
What has the team been working on recently?
```

**AI Response:**
```
Let me check the current project reflection.

[Reads rae://project/reflection resource]

Based on the project reflection, here are the key activities:

**Recent Focus Areas:**
- Performance optimization of the vector search (3x speedup achieved)
- Implementation of hierarchical reflection system
- Security hardening of authentication system
- MCP server development for IDE integration

**Key Decisions:**
- Adopted PostgreSQL pgvector over standalone solutions
- Implemented multi-tenant isolation at database level
- Standardized on Python 3.10+ for all services

**Active Challenges:**
- Optimizing large-scale graph traversal performance
- Balancing memory usage with cache hit rates
```

### Example 6: Checking Project Guidelines

**User Input:**
```
What are our coding standards for this project?
```

**AI Response:**
```
Let me retrieve the project guidelines from memory.

[Reads rae://project/guidelines resource]

PROJECT GUIDELINES
================================================================

1. Use Python 3.10+ for all new code
2. Follow PEP 8 style guide, enforced by Black formatter
3. All functions must have type hints and Google-style docstrings
4. Minimum 80% test coverage for new features
5. Use async/await for I/O operations
6. Structured logging with structlog for all services
7. Database migrations managed through Alembic
8. API versioning follows /v{N}/ pattern
9. Security: No secrets in code, use environment variables
10. Performance: Profile before optimizing, maintain benchmarks

================================================================
Last updated: 2025-11-20T15:30:00

These are the current coding standards that should be followed.
```

---

## Prompt Usage Examples

### Example 7: Automatic Guideline Injection

**Background:** The `project-guidelines` prompt is automatically injected into
the AI's context, ensuring coding standards are always followed.

**User Input:**
```
Write a function to calculate fibonacci numbers.
```

**AI Response:**
```
I'll create a fibonacci function following our project guidelines.

[project-guidelines prompt automatically loaded in context]

Here's the implementation with type hints, docstring, and following PEP 8:

```python
def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number.

    Uses iterative approach for O(n) time complexity and O(1) space.

    Args:
        n: The position in the Fibonacci sequence (0-indexed)

    Returns:
        The nth Fibonacci number

    Raises:
        ValueError: If n is negative

    Example:
        >>> fibonacci(0)
        0
        >>> fibonacci(10)
        55
    """
    if n < 0:
        raise ValueError("n must be non-negative")

    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b

    return b
```

This follows our guidelines:
- ✓ Type hints on function signature
- ✓ Google-style docstring with examples
- ✓ PEP 8 compliant formatting
- ✓ Proper error handling
- ✓ Optimal algorithm choice (O(n) time, O(1) space)
```

### Example 8: Recent Context Awareness

**User Input:**
```
Continue with the authentication work.
```

**AI Response:**
```
Based on recent context, I can see we've been working on authentication:

[recent-context prompt provides awareness]

Looking at recent activities:
- [2025-11-20] Fixed JWT validation security issue
- [2025-11-18] Added multi-tenant authentication support
- [2025-11-15] Implemented OAuth2 password flow

The most recent work was the JWT security fix. Would you like to:
1. Add tests for the JWT validation fix
2. Document the multi-tenant authentication setup
3. Implement additional OAuth2 flows (authorization code, client credentials)
4. Something else related to authentication

What would you like to focus on?
```

---

## Advanced Scenarios

### Example 9: Onboarding New Team Member

**User Input:**
```
I'm new to the project. What do I need to know?
```

**AI Response:**
```
Welcome to the team! Let me give you a comprehensive overview.

[Combines project/reflection resource + project/guidelines + search]

**Project Overview:**
[From rae://project/reflection]
This is RAE (Reflective Agentic Memory Engine), an advanced memory system
for AI agents with multi-layered architecture...

**Key Technologies:**
- Python 3.10+ with FastAPI
- PostgreSQL with pgvector for vector storage
- Redis for caching and distributed locks
- Celery for background tasks
- Docker for containerization

**Current Focus:**
- GraphRAG implementation (knowledge graph + vector search)
- MCP server for IDE integration
- Performance optimization at scale

**Coding Standards:**
[From rae://project/guidelines]
- Follow PEP 8, use Black formatter
- Type hints and docstrings required
- 80% test coverage minimum
- Async/await for I/O operations
...

**Recent Work:**
[From recent-context prompt]
- Completed hierarchical reflection system
- Fixed critical security vulnerability in auth
- Achieved 3x performance improvement in vector search

**Getting Started:**
1. Read the main README.md
2. Run `docker compose up` to start services
3. Check out examples/ directory
4. Look at recent PRs for coding patterns

Would you like me to elaborate on any specific area?
```

### Example 10: Code Review with Context

**User Input:**
```
Review this pull request for the cache invalidation fix.
```

**AI Response:**
```
I'll review this PR with full project context.

[Searches memory for related cache issues + checks guidelines]

**Context Check:**
I found that we had a similar race condition issue in the session management
code 2 months ago. That was fixed using Redis distributed locks.

**Code Review:**

✅ **Positives:**
- Uses Redis distributed lock (consistent with our previous solution)
- Proper error handling with try/finally
- Type hints and docstring included
- Test coverage at 85%

⚠️ **Suggestions:**

1. **Lock Timeout:** The lock timeout is 5 seconds. Based on our monitoring
   data, cache operations typically complete in <100ms. Consider reducing
   timeout to 1 second to fail faster.

2. **Logging:** Add structured logging for lock acquisition/release events.
   This helped us debug the previous issue.

3. **Metrics:** Consider adding Prometheus metrics for lock contention.
   This was mentioned in our performance guidelines.

4. **Tests:** Add a test case for lock timeout scenario.

**Verdict:** ✅ Approve with minor suggestions
The fix is sound and follows our patterns. The suggestions are non-blocking.
```

---

## Tips for Maximum Benefit

### 1. Store Important Decisions

```
Always save key architectural decisions, bug fixes, and design patterns
to memory with appropriate tags and layers.
```

### 2. Use Semantic Layer for Guidelines

```
Store coding standards, best practices, and team agreements in the
semantic layer so they persist long-term.
```

### 3. Leverage Episodic for Recent Work

```
Episodic memories automatically track recent work, making it easy to
resume where you left off.
```

### 4. Tag Consistently

```
Use consistent tagging conventions:
- Technology: python, postgresql, redis
- Type: bugfix, feature, refactor, decision
- Area: auth, cache, database, api
```

### 5. Trust the Context Injection

```
The project-guidelines prompt ensures the AI always knows your standards.
You don't need to repeat them in every conversation.
```

---

## Troubleshooting

### Tool Not Being Used

If the AI isn't using tools automatically:

```
Explicitly ask:
"Please save this to memory using the save_memory tool"
"Search our memory for authentication decisions"
```

### Incomplete Results

If search results are limited:

```
"Search again with top_k=20 for more comprehensive results"
```

### Wrong Layer

If memories are in the wrong layer:

```
"Save this to the semantic layer since it's a long-term guideline"
```

---

For more examples and use cases, see the main README.md and documentation.
