# RAE Memory Replay Tool Design Document

## 1. Purpose

The RAE Memory Replay Tool is designed to provide unprecedented transparency and debuggability for agentic systems powered by the RAE Engine. Its primary goals are:

*   **Debugging Agents**: Understand why an agent made a particular decision by tracing its memory retrieval and reasoning process.
*   **Training & Evaluation**: Analyze agent behavior over time, identify patterns, and train new agents or improve existing ones.
*   **Reducing Hallucinations**: Pinpoint instances where an agent generated incorrect information due to faulty memory retrieval or reasoning.
*   **Improving Reasoning Quality**: Evaluate the effectiveness of memory heuristics, reflection mechanisms, and prompt construction.
*   **Auditing & Compliance**: Provide a verifiable log of agent interactions and memory usage.

## 2. Core Functionality

The Replay Tool will allow users to:

*   **Record Agent Sessions**: Automatically capture all relevant data points during an agent's execution.
*   **List Recorded Sessions**: View a history of all agent sessions.
*   **Replay Sessions Step-by-Step**: Walk through an agent's decision-making process, observing each stage.
*   **Visualize Context Flow**: See which memories were retrieved, their scores, and how they contributed to the final prompt.
*   **Inspect Internal State**: Examine the agent's internal state, including changes to memory heuristics or scoring.
*   **Filter & Search Sessions**: Find specific sessions based on agent ID, tenant ID, date, or keywords in prompts/responses.

## 3. Data Model for Recorded Sessions

To enable comprehensive replay, the following information needs to be stored for each agent session:

```json
{
  "session_id": "uuid",
  "timestamp": "iso8601",
  "agent_id": "string",
  "tenant_id": "string",
  "user_prompt": "string",
  "initial_query_k": "integer",
  "retrieval_steps": [
    {
      "step_id": "uuid",
      "timestamp": "iso8601",
      "query_text": "string",
      "raw_retrieved_memories": [
        {
          "memory_id": "uuid",
          "score": "float",
          "content": "string",
          "source": "string",
          "importance": "float",
          "layer": "stm|ltm|rm",
          "tags": ["string"],
          "timestamp": "iso8601",
          "last_accessed_at": "iso8601",
          "usage_count": "integer"
        }
      ],
      "reranked_memories": [
        {
          "memory_id": "uuid",
          "score": "float",
          "content": "string",
          "source": "string",
          "importance": "float",
          "layer": "stm|ltm|rm",
          "tags": ["string"],
          "timestamp": "iso8601",
          "last_accessed_at": "iso8601",
          "usage_count": "integer"
        }
      ],
      "final_context_block": "string"
    }
  ],
  "llm_call": {
    "model": "string",
    "final_prompt_sent": "string",
    "llm_response": "string",
    "cost_info": {
      "input_tokens": "integer",
      "output_tokens": "integer",
      "total_estimate": "float"
    }
  },
  "reflection_event": {
    "reflection_memory_id": "uuid",
    "reflection_content": "string",
    "success": "boolean",
    "error_message": "string"
  },
  "agent_answer": "string",
  "final_used_memories": [
    {
      "memory_id": "uuid",
      "score": "float",
      "content": "string",
      "source": "string",
      "importance": "float",
      "layer": "stm|ltm|rm",
      "tags": ["string"],
      "timestamp": "iso8601",
      "last_accessed_at": "iso8601",
      "usage_count": "integer"
    }
  ]
}
```

## 4. Storage Mechanism

Session logs will be stored in a dedicated database table within the RAE Postgres instance. This allows for efficient querying and integration with existing tenant management.

*   **Table Name**: `agent_sessions`
*   **Schema**: A single JSONB column to store the entire session log, along with indexed fields for `session_id`, `timestamp`, `agent_id`, and `tenant_id`.

## 5. User Interface (High-Level)

The Replay Tool could manifest in two forms:

*   **CLI Tool**: For basic listing and replaying of sessions in a text-based format.
*   **Web UI (Integrated with Dashboard)**: A more advanced, interactive web interface, potentially integrated into the Grafana dashboard or as a separate FastAPI application. This would allow for visual flowcharts, memory heatmaps, and step-by-step inspection.

## 6. Integration Points with RAE API

To enable recording, the `apps/memory-api/routers/agent.py` `execute` endpoint needs to be modified:

*   **Middleware/Decorator**: A new middleware or decorator could wrap the `execute` function to capture all relevant data before and after its execution.
*   **Explicit Logging**: Alternatively, explicit logging calls could be added at each stage of the `execute` pipeline to a dedicated `SessionLogger` service.

The `SessionLogger` service would then store the captured data into the `agent_sessions` table.

## 7. Future Enhancements

*   **Comparison Mode**: Compare two different agent sessions to identify performance differences.
*   **What-If Scenarios**: Modify retrieved memories or LLM responses during replay to test alternative outcomes.
*   **Automated Analysis**: Tools to automatically analyze session logs for common failure modes or successful patterns.

This design provides a comprehensive framework for building a powerful Replay Tool, significantly enhancing the debuggability and understanding of RAE-powered agents.
