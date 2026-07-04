# Contributing to RAE

First off, thank you for considering contributing to RAE! 🎉

It's people like you that make RAE such a great tool for the AI community.

## 🌟 Ways to Contribute

There are many ways to contribute to RAE:

### 1. 🐛 Report Bugs

Found a bug? [Open an issue](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues/new?template=bug_report.md) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, Docker version)
- Relevant logs or error messages

### 2. 💡 Suggest Features

Have an idea for a new feature? [Open a feature request](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues/new?template=feature_request.md)!

Please include:
- The use case - why is this feature needed?
- How it would work from a user's perspective
- Possible implementation approach (if you have ideas)

### 3. 📝 Improve Documentation

Documentation improvements are always welcome! This includes:
- Fixing typos or unclear explanations
- Adding examples
- Improving API documentation
- Writing tutorials or guides

### 4. 💻 Write Code

Check our [Good First Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/labels/good%20first%20issue) for beginner-friendly tasks.

### 5. 🤝 Help Others

Answer questions in:
- [GitHub Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)
- [Discord #help channel](https://discord.gg/rae)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/rae-memory)

## 🚀 Getting Started

### Development Setup

1. **Fork and clone the repository:**

```bash
git clone https://github.com/YOUR_USERNAME/RAE-agentic-memory.git
cd RAE-agentic-memory
```

2. **Set up your development environment:**

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
make install-all
```

3. **Start the environment:**

**Option A: Full Development Environment (Recommended)**
This starts all Docker services (Postgres, Redis, Qdrant), the MCP Server, and both the Memory API and Reranker Service with hot-reload enabled.

```bash
# Start everything
make dev-full
```

**Option B: Standard Docker Start**
If you just want to run the pre-built containers:

```bash
# Start Docker services
docker compose up -d

# Or use make
make start
```

**Option C: Install MCP Service (Optional)**
To have the RAE MCP Server start automatically with your system (via systemd):

```bash
make install-mcp-service
```

4. **Run tests to verify setup:**

```bash
make test
```

### Making Changes

1. **Create a new branch:**

   We follow a strict branching strategy (see `docs/BRANCHING.md`):

   - **Features**: Must branch from `develop`.
     ```bash
     git checkout develop
     git pull
     git checkout -b feature/amazing-feature
     ```

   - **Hotfixes** (Production critical): Must branch from `main`.
     ```bash
     git checkout main
     git pull
     git checkout -b hotfix/critical-fix
     ```

2. **Make your changes:**
   - Write clear, commented code
   - Follow our code style (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes:**

> **IMPORTANT:** When running specific tests during development, ALWAYS use the `--no-cov` flag (or the `make test-focus` command). The project has strict global coverage thresholds configured in `pytest.ini` which will cause single-file tests to fail if coverage is enabled.

```bash
# Run all tests (enforces global coverage)
make test

# Run specific tests WITHOUT coverage (Recommended for dev loop)
make test-focus FILE=apps/memory_api/tests/test_specific.py

# OR manually:
pytest --no-cov apps/memory_api/tests/test_specific.py

# Run with coverage report (for full suite)
make test-cov
```

4. **Format and lint:**

```bash
# Auto-format code
make format

# Run linters
make lint

# Or let pre-commit handle it
pre-commit run --all-files
```

5. **Update Documentation:**

   Run the documentation automator to update status and TODOs:
   ```bash
   make docs
   ```

6. **Commit your changes:**

We use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat: add amazing feature"
git commit -m "fix: resolve authentication bug"
git commit -m "docs: update API documentation"
git commit -m "test: add tests for hybrid search"
git commit -m "refactor: simplify graph traversal"
git commit -m "chore: update dependencies"
```

**Commit message format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Adding tests
- `refactor:` - Code change that neither fixes a bug nor adds a feature
- `perf:` - Performance improvement
- `chore:` - Maintenance tasks

7. **Push and create a Pull Request:**

```bash
git push origin feature/amazing-feature
```

Then open a PR on GitHub.

## 📋 Pull Request Process

1. **Ensure your PR:**
   - Has a clear title describing the change
   - References related issues (use `Fixes #123` or `Closes #456`)
   - Includes tests for new functionality
   - Updates documentation if needed
   - Passes all CI checks

2. **PR Review:**
   - A maintainer will review your PR
   - Address any requested changes
   - Once approved, a maintainer will merge it

3. **After merging:**
   - Your contribution will be included in the next release
   - You'll be added to the CONTRIBUTORS list
   - Thank you! 🎉

## 💻 Code Style

We use automated formatters and linters to maintain code quality:

### Python Style

- **Black** for code formatting (100 char line length)
- **isort** for import sorting
- **ruff** for linting
- **mypy** for type checking (optional but recommended)

**Run formatters:**
```bash
make format  # Auto-formats all code
```

**Run linters:**
```bash
make lint  # Checks code style
```

### Code Guidelines

- Use type hints where possible
- Write docstrings for public functions/classes
- Keep functions focused and small
- Write self-documenting code (clear variable names)
- Add comments for complex logic only
- Follow PEP 8 style guide

**Example:**

```python
async def store_memory(
    self,
    content: str,
    layer: MemoryLayer,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None
) -> MemoryRecord:
    """
    Store a memory in the specified layer.

    Args:
        content: The memory content to store
        layer: Memory layer (episodic, working, semantic, ltm)
        tags: Optional tags for categorization
        metadata: Optional additional metadata

    Returns:
        The stored memory record

    Raises:
        ValidationError: If content is empty or invalid
        StorageError: If storage fails
    """
    if not content.strip():
        raise ValidationError("Content cannot be empty")

    # ... implementation
```

## 🧪 Testing Guidelines

- **Write tests for all new features**
- **Maintain >= 75% code coverage overall, 80%+ for core modules**
- **Use pytest fixtures for common setup**
- **Mark tests appropriately** (`@pytest.mark.unit`, `@pytest.mark.integration`)

**Current Testing Status:**
- See [docs/TESTING_STATUS.md](docs/TESTING_STATUS.md) for current test coverage and status
- Target: 75%+ overall coverage, 80%+ for core modules (services, repositories)
- Current: 32.25% overall (200/264 tests passing)

**Test structure:**

```python
import pytest
from apps.memory_api.services import MemoryService

@pytest.fixture
async def memory_service():
    """Fixture for memory service with mocked dependencies."""
    service = MemoryService(...)
    yield service
    await service.cleanup()

@pytest.mark.unit
async def test_store_memory_success(memory_service):
    """Test successful memory storage."""
    result = await memory_service.store_memory(
        content="Test memory",
        layer="episodic"
    )

    assert result.id is not None
    assert result.content == "Test memory"
    assert result.layer == "episodic"

@pytest.mark.integration
async def test_query_memory_integration(memory_service, db_connection):
    """Test memory query against real database."""
    # Requires services to be running
    ...
```

## 📚 Documentation

- Update relevant documentation when adding features
- Use clear, concise language
- Include code examples where helpful
- Keep API documentation in sync with code

**Documentation locations:**
- `/docs/` - Main documentation
- `/README.md` - Project overview
- Docstrings - In-code documentation
- `/examples/` - Usage examples

## 🏷️ Issue Labels

We use labels to organize issues:

**Priority:**
- `🔴 critical` - Critical bugs or security issues
- `🟠 high` - Important features or bugs
- `🟡 medium` - Standard priority
- `🟢 low` - Nice to have

**Type:**
- `🐛 bug` - Something isn't working
- `✨ enhancement` - New feature or request
- `📝 documentation` - Documentation improvements
- `❓ question` - Further information requested
- `💡 idea` - Feature idea or proposal

**Status:**
- `🚧 in-progress` - Currently being worked on
- `✅ ready-to-merge` - PR is ready
- `🔍 needs-review` - Awaiting review
- `⏸️ on-hold` - Waiting for something

**Difficulty:**
- `🌱 good-first-issue` - Good for newcomers
- `🌿 beginner-friendly` - Suitable for beginners
- `🌲 intermediate` - Requires some experience
- `🌳 advanced` - Complex task

## 🤝 Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

By participating, you are expected to uphold this code. Please report unacceptable behavior to conduct@rae-project.io.

## 🎖️ Recognition

Contributors will be recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md) - List of all contributors
- GitHub contributor badge on your profile
- Release notes for significant contributions
- Our eternal gratitude! 💙

## 🤖 AI Agent Guidelines

If you are an AI assistant (Claude, ChatGPT, GitHub Copilot) working on this repository, please:

1.  **Read Instructions**: Check `.cursorrules` (for Cursor) or `.github/copilot-instructions.md`.
2.  **Branching**: ALWAYS create new features from `develop`. NEVER commit directly to `main` or `develop`.
3.  **Tests**: Always generate tests for new code.
4.  **Style**: Ensure code passes `black` and `ruff`.
5.  **CI Check**: Before merging to `main`, VERIFY that GitHub Actions have passed (`gh run watch` or checking PR status).

## ❓ Questions?

If you have questions about contributing:
- Ask in [Discord](https://discord.gg/rae)
- Tag @maintainer in a GitHub issue
- Email: lesniowskig@gmail.com

## 📝 License

By contributing to RAE, you agree that your contributions will be licensed under the Apache License 2.0.

---

**Thank you for making RAE better!** 🚀

We appreciate your time and effort in contributing to this project.

---

**Quick Links:**
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Testing Status](docs/TESTING_STATUS.md)
- [Version Matrix](docs/VERSION_MATRIX.md)
- [Legacy Documentation](docs/legacy/mcp.md)
- [Development Setup](docs/contributing/development-setup.md)
- [Architecture Overview](docs/concepts/architecture.md)
- [Testing Guide](docs/contributing/testing.md)
