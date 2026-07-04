#!/usr/bin/env python3
"""
E2E Smoke Test Script (Integration Verification)

Scenariusz:
    1. Health Check
    2. Ingest
    3. Wait (Polling)
    4. Search (Verify)
    5. Assert
"""

import json
import logging
import os
import sys
import time

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log_pass(message):
    print(f"{GREEN}✅ {message}{RESET}")


def log_fail(message):
    print(f"{RED}❌ {message}{RESET}")


def log_info(message):
    print(f"{BOLD}ℹ️  {message}{RESET}")


API_URL = os.environ.get("API_URL", "http://localhost:8000")


def main():
    log_info(f"Starting Smoke Test against {API_URL}")

    # Step 1: Health Check
    try:
        log_info("Step 1: Health Check...")
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            log_pass("Health Check Passed")
        else:
            log_fail(f"Health Check Failed: Status {response.status_code}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        log_fail(f"Health Check Failed: {e}")
        sys.exit(1)

    # Step 2: Ingest
    log_info("Step 2: Ingest Memory...")
    ingest_payload = {
        "content": "SmokeTestUser pracuje w firmie TestCorp jako Senior Python Developer.",
        "metadata": {"source": "e2e_script"},
    }

    try:
        response = requests.post(
            f"{API_URL}/api/v1/memory", json=ingest_payload, timeout=10
        )
        if response.status_code in [200, 201, 202]:
            log_pass("Ingest Request Accepted")
            # Assuming response might contain an ID, but typically it returns status
            # print(response.json())
        else:
            log_fail(f"Ingest Failed: Status {response.status_code} - {response.text}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        log_fail(f"Ingest Request Failed: {e}")
        sys.exit(1)

    # Step 3: Waiting (Polling)
    log_info("Step 3: Waiting for processing...")
    # Wait for Celery workers to process the data
    # We will poll via search in Step 4, so maybe just a fixed sleep first?
    # User said "Pętla while (max 30 sekund), która czeka, aż asynchroniczne workery (Celery) przetworzą dane."
    # So we should probably poll the search endpoint until we find it.

    start_time = time.time()
    max_duration = 30
    found = False

    search_payload = {"query": "Gdzie pracuje SmokeTestUser?", "limit": 5}

    while time.time() - start_time < max_duration:
        time.sleep(2)  # Poll interval

        try:
            # Step 4: Verification (Hybrid Search)
            response = requests.post(
                f"{API_URL}/api/v1/memory/search", json=search_payload, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                # Check if "TestCorp" is in the response string dump
                # The response structure might be a list of results or an object containing results.
                # We'll stringify the whole JSON response to check for existence of substring.
                response_text = json.dumps(data)

                if "TestCorp" in response_text:
                    found = True
                    log_pass(
                        f"Found 'TestCorp' in search results after {time.time() - start_time:.1f}s"
                    )
                    break
                else:
                    print(f"Waiting... ({int(time.time() - start_time)}s)")
            else:
                print(f"Search error {response.status_code}, retrying...")

        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}, retrying...")

    # Step 5: Assertion
    if found:
        log_pass("TEST PASSED: 'TestCorp' found in search results.")
        # Step 6: Cleanup (Optional - strictly speaking we don't have IDs easily available unless Ingest returned it)
        # Assuming we skip cleanup for now as per "Opcjonalnie" and lack of explicit ID handling instructions.
        sys.exit(0)
    else:
        log_fail("TEST FAILED: Timeout waiting for data to appear in search.")
        sys.exit(1)


if __name__ == "__main__":
    main()
