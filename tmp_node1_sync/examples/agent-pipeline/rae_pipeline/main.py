import os
import time

import httpx
from tqdm import tqdm


class RAEAPISetup:
    def __init__(self, base_url, tenant_id, api_key, project_id):
        self.base_url = f"{base_url}/v1"
        self.tenant_id = tenant_id
        self.api_key = api_key
        self.project_id = project_id
        self.headers = {"X-Tenant-Id": self.tenant_id, "X-API-Key": self.api_key}

    def _make_request(self, method, endpoint, **kwargs):
        with httpx.Client(timeout=30.0) as client:
            try:
                res = client.request(
                    method, f"{self.base_url}{endpoint}", headers=self.headers, **kwargs
                )
                res.raise_for_status()
                return res.json()
            except httpx.HTTPStatusError as e:
                print(f"Error calling {endpoint}: {e.response.text}")
                raise
            except httpx.RequestError as e:
                print(f"Request error calling {endpoint}: {e}")
                raise

    def store_memory(self, content, layer, tags=None):
        if tags is None:
            tags = []
        payload = {
            "content": content,
            "layer": layer,
            "project": self.project_id,
            "source": "cli-setup-script",
            "tags": tags,
        }
        return self._make_request("POST", "/memory/store", json=payload)

    def trigger_reflection_rebuild(self):
        payload = {"project": self.project_id, "tenant_id": self.tenant_id}
        return self._make_request("POST", "/memory/rebuild-reflections", json=payload)

    def trigger_cache_rebuild(self):
        return self._make_request("POST", "/cache/rebuild")

    def execute_agent(self, prompt):
        payload = {
            "tenant_id": self.tenant_id,
            "project": self.project_id,
            "prompt": prompt,
        }
        return self._make_request("POST", "/agent/execute", json=payload)


def show_step(title):
    print("\n" + "=" * 50)
    print(f"STEP: {title}")
    print("=" * 50)


def main():
    # --- Configuration ---
    RAE_API_URL = os.environ.get("RAE_API_URL", "http://localhost:8000")
    RAE_TENANT_ID = "gemini-cli-example-tenant"
    RAE_API_KEY = os.environ.get("RAE_API_KEY", "test-key")
    PROJECT_ID = "cli-agent-project"

    setup = RAEAPISetup(RAE_API_URL, RAE_TENANT_ID, RAE_API_KEY, PROJECT_ID)

    # --- Step 1: Populate Semantic Memory ---
    show_step("Populating Semantic Memory (Core Knowledge)")
    semantic_memories = [
        (
            "Always use snake_case for Python variables.",
            "sm",
            ["python", "style-guide"],
        ),
        (
            "All Python functions must have a docstring.",
            "sm",
            ["python", "style-guide"],
        ),
        (
            "The primary key for database tables should be a UUID.",
            "sm",
            ["database", "architecture"],
        ),
    ]
    for content, layer, tags in tqdm(
        semantic_memories, desc="Storing Semantic Memories"
    ):
        setup.store_memory(content, layer, tags)
    print("Semantic memory populated.")

    # --- Step 2: Populate Episodic Memory ---
    show_step("Populating Episodic Memory (Recent Events)")
    episodic_memories = [
        (
            "User asked to refactor the 'get_user' function to be more performant.",
            "em",
            ["refactoring", "user-request"],
        ),
        (
            "Agent previously tried to use a list comprehension but it was too slow.",
            "em",
            ["refactoring", "performance-issue"],
        ),
        (
            "Agent then switched to a generator expression which improved performance.",
            "em",
            ["refactoring", "performance-solution"],
        ),
    ]
    for content, layer, tags in tqdm(
        episodic_memories, desc="Storing Episodic Memories"
    ):
        setup.store_memory(content, layer, tags)
    print("Episodic memory populated.")

    # --- Step 3: Trigger Reflection ---
    show_step("Triggering Reflection Engine")
    setup.trigger_reflection_rebuild()
    print("Reflection task dispatched. In a real system, this runs periodically.")
    time.sleep(2)  # Give a moment for the task to be picked up

    # --- Step 4: Trigger Cache Rebuild ---
    show_step("Triggering Cache Rebuild")
    setup.trigger_cache_rebuild()
    print("Cache rebuild task dispatched. This will pre-warm the cache for the agent.")
    print("Waiting for background tasks to hopefully complete...")
    for _ in tqdm(range(10), desc="Waiting"):
        time.sleep(1)

    # --- Step 5: Execute Agent ---
    show_step("Executing Agent with Cached Context")
    prompt = "How should I refactor the 'get_user' function, and what variable naming convention should I use?"

    print(f'\nAgent Prompt: "{prompt}"\n')

    try:
        agent_response = setup.execute_agent(prompt)
        print("\n--- Agent Response ---")
        print(agent_response.get("answer", "No answer received."))
        print("----------------------")

        used_memories = agent_response.get("used_memories", {}).get("results", [])
        print(f"\nAgent used {len(used_memories)} memories:")
        for mem in used_memories:
            print(f"- [Episodic] {mem['content'][:60]}...")

        print(
            "\nNote: The agent's answer should reflect the 'lesson learned' from the episodic memories"
        )
        print(
            "and the style guide rules from the semantic memory, which were loaded from the cache."
        )

    except Exception as e:
        print(
            f"\nFailed to execute agent. Is the RAE API and its workers running? Error: {e}"
        )


if __name__ == "__main__":
    main()
