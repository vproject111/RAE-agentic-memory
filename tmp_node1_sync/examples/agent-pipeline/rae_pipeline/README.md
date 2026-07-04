# Gemini CLI RAE Pipeline Example

This example demonstrates a complete workflow of populating the RAE memory and then using the agent, showcasing the benefits of the semantic/reflective cache.

## Purpose

The script simulates a real-world scenario where an agent needs to perform a task (refactoring code) based on both general rules (semantic memory) and recent events (episodic memory).

1.  **Semantic Memory**: We first store some "core knowledge" for the agent, such as coding style guides.
2.  **Episodic Memory**: We then store a sequence of recent events related to a specific task.
3.  **Reflection & Caching**: We manually trigger the reflection and caching mechanisms. In a live system, these would run periodically in the background. The reflection engine synthesizes the episodic events into a "lesson learned", and the caching engine pre-warms the Redis cache with all semantic and reflective memories.
4.  **Agent Execution**: Finally, we ask the agent a question. The RAE API uses the pre-warmed cache to provide the agent with the necessary context (style guides + lessons learned) in its system prompt, allowing it to answer the question effectively without needing to perform a new vector search for that context.

## How to Run

1.  **Ensure RAE is running.**
    You must have the full RAE environment running via Docker Compose from the project root:
    ```bash
    docker compose -f infra/docker compose.yml up --build
    ```

2.  **Install dependencies for this example.**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the script.**
    Make sure your `RAE_API_KEY` is set as an environment variable if you have configured one in your RAE `.env` file.
    ```bash
    python main.py
    ```

## Expected Outcome

The script will print its progress through each step. The final agent response should demonstrate that it has understood both the style guide rules (e.g., mentioning `snake_case`) and the lessons learned from the recent performance refactoring, even though its vector search only retrieved the most recent, relevant episodic memories. This shows the power of the layered memory and caching system.
