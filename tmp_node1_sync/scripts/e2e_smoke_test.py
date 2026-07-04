import json
import os
import sys
import time

import requests

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
TENANT_ID = os.getenv("TENANT_ID", "e2e-test-tenant")
PROJECT_ID = "e2e-test-project"

# Headers
headers = {"Content-Type": "application/json", "X-Tenant-Id": TENANT_ID}


def log(message):
    print(f"[E2E TEST] {message}")


def check_health():
    log(f"Checking health at {API_URL}/health")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            log("Health check passed.")
            return True
        else:
            log(f"Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        log("Could not connect to API. Is it running?")
        return False


def run_test():
    if not check_health():
        sys.exit(1)

    # 1. Store Memory
    memory_content = "Adam pracuje w Google"
    store_payload = {
        "content": memory_content,
        "source": "e2e-script",
        "project": PROJECT_ID,
    }

    log(f"Storing memory: '{memory_content}'")
    try:
        response = requests.post(
            f"{API_URL}/v1/memory/store", headers=headers, json=store_payload
        )
        response.raise_for_status()
        memory_id = response.json().get("id")
        log(f"Memory stored successfully. ID: {memory_id}")
    except Exception as e:
        log(f"Failed to store memory: {e}")
        if hasattr(e, "response") and e.response:
            log(f"Response: {e.response.text}")
        sys.exit(1)

    # 2. Wait for processing (simulating eventual consistency)
    wait_time = 5
    log(f"Waiting {wait_time} seconds for indexing...")
    time.sleep(wait_time)

    # 3. Query Memory
    query_text = "Gdzie pracuje Adam?"
    query_payload = {
        "query_text": query_text,
        "k": 5,
        "filters": {"tenant_id": TENANT_ID},
    }

    log(f"Querying: '{query_text}'")
    try:
        response = requests.post(
            f"{API_URL}/v1/memory/query", headers=headers, json=query_payload
        )
        response.raise_for_status()
        results = response.json().get("results", [])

        found = False
        for res in results:
            if "Google" in res.get("content", ""):
                found = True
                log(f"Found expected content in result: {res.get('content')}")
                break

        if found:
            log("SUCCESS: Memory retrieval verified.")
        else:
            log("FAILURE: Expected content 'Google' not found in search results.")
            log(f"Results: {json.dumps(results, indent=2)}")
            sys.exit(1)

    except Exception as e:
        log(f"Failed to query memory: {e}")
        if hasattr(e, "response") and e.response:
            log(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    run_test()
