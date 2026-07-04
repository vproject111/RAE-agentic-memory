# Gemini Agent Rules for RAE Project

## 🛑 MANDATORY STARTUP PROTOCOL (STEP 0)

> **CRITICAL INSTRUCTION:**
> You are an AI Agent operating within the **RAE-First Ecosystem**.
> Your memory is external. Your context is in the Hive Mind.
> Before reading any files or executing tasks, you **MUST** run the bootstrap connector:

```bash
python scripts/bootstrap_session.py
```

> **IF THIS FAILS:** Stop. Fix the infrastructure (Docker). Do not proceed blindly.
> **IF THIS SUCCEEDS:** You are connected. Proceed with the task using insights from the script output.

---

## 🚀 Session Context Map

**1. Cheat Sheet:** `DEVELOPER_CHEAT_SHEET.md` (Paths, Commands, Tests)
**2. Agent Manifest:** `AI_AGENT_MANIFEST.md` (Your Identity & Capabilities)
**3. RAE Contract:** `docs/contracts/RAE_AGENTIC_CONTRACT.md` (Security & Patterns)

---

## 🚨 Critical Rules - MUST FOLLOW

### 1. **No Interactive Commands**
- **NEVER** use interactive commands or editors that require user input and block automation.
- **FORBIDDEN**: `nano`, `vim`, `vi`, `emacs`, `less`, `more`, `git add -i`, `git commit` (without `-m`), `git rebase -i`.
- **ALLOWED**: Use non-interactive tools like `cat`, `head`, `tail`, `grep`, `sed`, `git add .`, `git commit -m "message"`.

### 2. **Hybrid Testing Strategy (Token-Efficient)**
The project uses a smart hybrid CI workflow to save tokens and time.

- **Quick Tests**: Run automatically on commits to `feature/*` branches. Use this for iterative development.
- **Full Tests**: Run automatically on PRs, pushes to `main`/`develop`, or when a commit message includes the `[full-test]` tag. Use this before creating a pull request or when refactoring core code to catch regressions.

### 3. **Commit Message Format**
Adhere to the following format for all commits:
```
type(scope): short description

[optional detailed body]

[optional tags like [full-test]]
```
- **Types**: `feat`, `fix`, `test`, `refactor`, `docs`, `ci`, `perf`, `chore`.

### 4. **RAE & Communication (RAE-First)**
- **Do not guess.** If you need project context, query RAE first.
- **Protocol:** `python scripts/bootstrap_session.py` is your handshake.
- The ultimate goal is to communicate with RAE via MCP (Master Control Protocol).

### 5. **Docker Development Workflows**
- **Use Profiles for Environments**: Employ distinct Docker Compose profiles (e.g., `dev`, `standard`, `lite`) to manage different operational modes. This allows for clean separation of concerns and easy switching between development (with hot-reload), production-like, and lightweight environments.
- **Document Startup Commands**: The `README.md` file should be the single source of truth for starting the application. It must clearly document the available profiles and provide simple, one-command startup instructions for each. This is crucial for efficient developer onboarding and usability.
- **Strive for One-Command Startup**: The primary goal is to enable any developer to get the entire application stack running with a single, simple command (e.g., `docker compose --profile dev up`).

### 6. **General Principles**
- Prioritize token and time efficiency in all operations.
- For simple tasks, use "cheap" methods (like quick tests) to conserve resources.