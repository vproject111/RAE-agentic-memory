# What is RAE? Architecture, Philosophy & Use Cases

> *"It's not just a database. It's an operating system for agentic cognition."*

If you are new to RAE, you might be wondering: *"Is this just a vector database? Is it RAG? Is it an automation tool?"*
The answer is: RAE uses these technologies, but it solves a completely different problem.

This document explains **what RAE actually is**, based on its codebase capabilities and real-world usage patterns.

---

## 1. The Core Concept: "Shared Consciousness" for Agents

Most AI agents are "amnesiacs." They start every session blank. Even with standard RAG (Vector DB), they only retrieve *text snippets*, not *understanding*.

**RAE is a shared, persistent cognitive layer.**
Think of it as a "Hive Mind" for your AI ecosystem.

*   **Scenario:** You have a "Coder Agent" writing a Python script and a "Reviewer Agent" checking it.
*   **Without RAE:** You must manually copy-paste context between them. They don't know each other's history.
*   **With RAE:** Both agents connect to the same Project ID.
    *   The Coder saves its *reasoning* ("I chose FastAPI because...") to RAE.
    *   The Reviewer sees this reasoning instantly via the **Shared Memory** layer.
    *   **Result:** Coherent collaboration without redundancy.

### Evidence in Code
RAE enforces this via `TenantContextMiddleware` and specific memory layers (`episodic`, `semantic`, `reflective`) that are project-scoped, not session-scoped.

---

## 2. RAE as an Orchestrator (Not Just a Database)

A database is passive; it waits for queries. RAE is active.
Through the **Agent API** (`/v1/agent/execute`), RAE acts as an Orchestrator.

*   **Passive Usage:** You ask: *"Give me documents about Project X."* (Standard RAG)
*   **Active Usage (RAE):** You ask: *"Plan the migration for Project X."*
    1.  RAE retrieves relevant memories.
    2.  RAE uses its **Reasoning Engine** to evaluate the context.
    3.  RAE generates a plan using an LLM.
    4.  RAE saves this plan as a new "Reflective Memory" for future reference.

This turns RAE from a "hard drive" into a "CPU" that processes information and makes decisions.

---

## 3. Distributed Compute: The "Node1" Architecture

Unlike simple memory tools, RAE includes a **Control Plane** for heavy lifting.
Cognitive tasks (embeddings, re-ranking, graph extraction) are computationally expensive.

RAE implements a **Distributed Compute Architecture**:
*   **The Orchestrator (Your Laptop):** Runs the lightweight API and logic.
*   **Compute Nodes (e.g., "Node1"):** Powerful machines (with GPUs) that handle the heavy math.

### How it Works (Control Plane API)
The system uses a pull-based task queue.
1.  Orchestrator posts a task: *"Calculate embeddings for these 1000 documents."*
2.  **Node1** (registered via `/control/nodes/register`) picks up the task.
3.  Node1 processes it on GPU and returns the result.

This allows RAE to scale to millions of memories without slowing down your primary interface.

---

## 4. The "RAE-First" Workflow

The most effective way to use RAE – and the secret to our own development velocity – is the **RAE-First Protocol**. This is a methodology for Human-AI collaboration.

### The Protocol
Before writing a single line of code, the Agent/Human loop follows this sequence:

1.  **Context Loading (Read):**
    *   *Agent:* "Let me check RAE memory for `Project X conventions` and `previous bugs`."
    *   *Why:* Prevents regressive errors (fixing the same bug twice) and ensures style consistency.

2.  **Plan Verification (Reason):**
    *   *Agent:* "Based on memory, this approach caused issues last time. I propose Strategy B."
    *   *Why:* Leverages "Reflective Memory" (lessons learned) to avoid past mistakes.

3.  **Atomic Execution (Act):**
    *   *Agent:* Performs the task (e.g., refactoring) in small, verifiable steps.

4.  **Memory Consolidation (Write):**
    *   *Agent:* "Task complete. I am saving this architectural decision to RAE so future agents know *why* we did this."
    *   *Why:* Builds the "Hive Mind" for the next session.

### Why it matters
This protocol eliminates **Drift**. Most projects rot because decisions are forgotten. RAE ensures that every decision strengthens the system's long-term coherence.

---

## Summary: RAE vs. The World

| Feature | Vector Database | Standard RAG | Automation (Zapier) | **RAE** |
| :--- | :--- | :--- | :--- | :--- |
| **Role** | Storage | Retrieval | Execution | **Reasoning & Memory** |
| **Context** | None (Raw Vectors) | Limited Window | None | **Infinite & Structured** |
| **Learning** | None | None | None | **Reflective (Self-Improving)** |
| **Multi-Agent**| No | No | No | **Native Shared Memory** |
| **Compute** | Server-side | Local/API | Cloud SaaS | **Distributed (Node1)** |

**RAE is the missing bridge between "Static Data" and "Autonomous Agents."**
