# Building Reflection

Reflection is a core mechanism in RAE that allows agents to learn from their experiences, synthesize new knowledge, and build meta-memories.

## How Reflection Works

The reflection process typically involves:

1.  **Capturing Interaction**: After an agent completes a task (e.g., answering a user query), the entire interaction (user prompt, retrieved context, LLM response) is captured.
2.  **Formulating a Reflection Prompt**: This captured interaction is then used to formulate a new prompt for an LLM, asking it to reflect on the interaction. The LLM might be asked to:
    *   Summarize the key takeaways.
    *   Identify any new insights or patterns.
    *   Extract important facts or concepts.
    *   Evaluate the quality of the agent's response.
    *   Suggest improvements for future interactions.
3.  **Creating New Memories**: The LLM's reflection (its response to the reflection prompt) is then stored back into RAE as a new memory, typically in the `reflective memory (rm)` layer. These new memories can have higher importance scores, making them more likely to be retrieved in future, similar contexts.

## Reflection in RAE

RAE provides a `reflection hook` within the `/agent/execute` endpoint. After the LLM generates an answer, a reflection prompt is automatically constructed and sent to the RAE Memory API's `/memory/store` endpoint.

### Example Reflection Payload

```json
{
  "content": "User Query: How to implement RLS in Postgres?\n\nRetrieved Context:\n- Row-Level Security (RLS) in PostgreSQL allows to control which rows a user can access in a table.\n\n---\n\nAgent Answer: RLS in PostgreSQL is implemented using policies...",
  "source": "reflection_on_llm_response_id_xyz",
  "layer": "rm",
  "tags": ["reflection", "postgres", "rls"]
}
```

## Customizing Reflection

You can customize the reflection process by:

*   **Modifying the Reflection Prompt**: Adjust the prompt used to guide the LLM's reflection to focus on specific aspects (e.g., security, cost, user satisfaction).
*   **Filtering Reflection Content**: Implement logic to filter or refine the LLM's reflection before storing it as a new memory.
*   **Adjusting Reflection Frequency**: Control how often reflection occurs (e.g., after every interaction, after a certain number of interactions, or based on specific triggers).

## Benefits of Reflection

*   **Continuous Learning**: Agents continuously learn and improve their knowledge base.
*   **Adaptability**: RAE adapts to new information and evolving contexts.
*   **Meta-Knowledge**: Builds higher-level understanding and principles.
*   **Reduced Hallucinations**: By refining its own knowledge, the agent can reduce the likelihood of generating incorrect information.
