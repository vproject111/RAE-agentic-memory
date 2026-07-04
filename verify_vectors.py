import time

import requests

API_URL = "http://localhost:8000/v1/memory"
HEADERS = {"Content-Type": "application/json", "X-Tenant-Id": "default-tenant"}
PROJECT = "vector-verification-project"

TEST_DATA = [
    # Programming
    {
        "content": "Python uses whitespace indentation to delimit blocks.",
        "tags": ["coding", "python"],
    },
    {
        "content": "Rust's borrow checker ensures memory safety without garbage collection.",
        "tags": ["coding", "rust"],
    },
    {
        "content": "Docker containers provide lightweight virtualization.",
        "tags": ["coding", "devops"],
    },
    {
        "content": "React is a JavaScript library for building user interfaces.",
        "tags": ["coding", "frontend"],
    },
    {
        "content": "SQL databases use structured query language for data manipulation.",
        "tags": ["coding", "db"],
    },
    # Cooking
    {
        "content": "To make a roux, cook flour and fat together.",
        "tags": ["cooking", "basics"],
    },
    {
        "content": "Searing meat locks in flavor through the Maillard reaction.",
        "tags": ["cooking", "science"],
    },
    {
        "content": "Fresh basil should be added at the end of cooking to preserve flavor.",
        "tags": ["cooking", "herbs"],
    },
    {
        "content": "A sharp knife is safer than a dull one in the kitchen.",
        "tags": ["cooking", "safety"],
    },
    {
        "content": "Pasta water should be as salty as the sea.",
        "tags": ["cooking", "tips"],
    },
    # Space
    {
        "content": "The Sun creates energy through nuclear fusion.",
        "tags": ["space", "stars"],
    },
    {
        "content": "Jupiter is the largest planet in our solar system.",
        "tags": ["space", "planets"],
    },
    {
        "content": "A black hole's gravity is so strong that light cannot escape.",
        "tags": ["space", "physics"],
    },
    {"content": "The Moon causes tides on Earth.", "tags": ["space", "earth"]},
    {
        "content": "Mars is known as the Red Planet due to iron oxide.",
        "tags": ["space", "mars"],
    },
    # History
    {
        "content": "The Roman Empire built an extensive network of roads.",
        "tags": ["history", "rome"],
    },
    {
        "content": "The Industrial Revolution began in Britain in the 18th century.",
        "tags": ["history", "industry"],
    },
    {
        "content": "The printing press was invented by Gutenberg.",
        "tags": ["history", "inventions"],
    },
    {"content": "World War II ended in 1945.", "tags": ["history", "war"]},
    {
        "content": "The Pyramids of Giza were built as tombs for pharaohs.",
        "tags": ["history", "egypt"],
    },
]


def store_memories():
    print(f"Storing {len(TEST_DATA)} memories...")
    for item in TEST_DATA:
        payload = {
            "content": item["content"],
            "tags": item["tags"],
            "layer": "semantic",
            "importance": 0.8,
            "project": PROJECT,
        }
        try:
            res = requests.post(f"{API_URL}/store", headers=HEADERS, json=payload)
            if res.status_code != 200:
                print(f"Failed to store: {item['content']} - {res.text}")
            else:
                print(".", end="", flush=True)
        except Exception as e:
            print(f"Error: {e}")
    print("\nStorage complete.")


def test_search():
    queries = [
        "programming languages and frameworks",
        "how to cook better",
        "facts about planets and stars",
        "historical events and empires",
    ]

    print("\n--- Testing Search ---")
    for q in queries:
        print(f"\nQuery: '{q}'")
        payload = {"query_text": q, "k": 3, "project": PROJECT}
        res = requests.post(f"{API_URL}/query", headers=HEADERS, json=payload)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if not results:
                print("  No results found.")
            for r in results:
                print(f"  [{r['score']:.4f}] {r['content']} (Tags: {r.get('tags')})")
        else:
            print(f"Search failed: {res.text}")


if __name__ == "__main__":
    store_memories()
    time.sleep(2)
    test_search()
