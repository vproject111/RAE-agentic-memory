# Evaluation Suite

This directory contains the tools to evaluate the performance of the Agentic Memory API.

## Golden Set

The `goldenset.yaml` file contains the data for the evaluation. It is split into two sections:

- `memories`: A list of memories to be added to the system before running the evaluation. Each memory has a `content`, `source_id`, and other metadata.
- `queries`: A list of queries to be run against the system. Each query has a `query` text and a list of `expected_source_ids` that are considered relevant for that query.

## Running the Evaluation

To run the evaluation, you need to have the Agentic Memory API running. The script will target the API at the URL specified by the `MEMORY_API_URL` environment variable, which defaults to `http://localhost:8000`.

1.  **Install dependencies:**
    ```bash
    pip install pyyaml requests
    ```

2.  **Run the script:**
    ```bash
    python eval/run_eval.py
    ```
    By default, the script will first add the memories from the `goldenset.yaml` file and then run the evaluation queries.

    If you want to skip adding memories and only run the evaluation, use the `--no-add` flag:
    ```bash
    python eval/run_eval.py --no-add
    ```

## Metrics

The script calculates and prints the following metrics:

-   **Hit Rate @ 5**: The proportion of queries for which at least one of the expected documents was ranked in the top 5 results.
-   **Mean Reciprocal Rank (MRR)**: The average of the reciprocal ranks of the first relevant document for each query. The rank is the position of the document in the result list.
-   **P95 Latency (ms)**: The 95th percentile of the query latency in milliseconds.
-   **Average Latency (ms)**: The average query latency in milliseconds.