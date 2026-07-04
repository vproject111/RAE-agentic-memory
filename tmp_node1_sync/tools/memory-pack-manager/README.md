# RAE Memory Pack Manager

This CLI tool allows you to manage "Memory Packs" for the RAE (Reflective Agentic Memory) Engine. Memory Packs are collections of pre-defined memories (e.g., coding best practices, safety policies) that can be easily imported into your RAE instance.

## Features

-   **Import**: Load memories from a JSON file into your RAE instance.
-   **Export**: (Planned) Export memories from your RAE instance into a JSON file.

## Memory Pack Format

Memory packs are simple JSON arrays of memory objects, conforming to the `StoreMemoryRequest` schema.

Example:
```json
[
  {
    "content": "Python Coding Conventions: Use descriptive variable names. For loops, use `index` for counters, and singular nouns for items (e.g., `for user in users`).",
    "source": "manual/coding_conventions.md",
    "layer": "ltm",
    "tags": ["python", "style-guide"]
  },
  {
    "content": "Refactoring technique: Extract Method. Identify a code fragment that can be grouped into a new method. This improves readability and reduces duplication.",
    "source": "refactoring-guru/extract-method",
    "layer": "ltm",
    "tags": ["refactoring", "best-practice"]
  }
]
```

## Usage

1.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Configure the RAE API endpoints and API key in a `.env` file:
    ```
    RAE_API_URL="http://localhost:8000"
    RAE_API_KEY="your-secret-key"
    RAE_TENANT_ID="my-project"
    ```

3.  Import a memory pack:
    ```bash
    python main.py import --file packs/code-refactoring.json
    ```

4.  (Planned) Export memories:
    ```bash
    python main.py export --output my-exported-memories.json --tags "python"
    ```
