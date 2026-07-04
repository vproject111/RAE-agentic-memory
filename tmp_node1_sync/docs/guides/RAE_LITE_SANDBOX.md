# RAE-Lite Sandbox Guide

This guide explains how to run RAE-Lite in a completely isolated sandbox environment. This is the recommended way for developers to test RAE-Lite without affecting their main RAE installation.

## Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for seeding scripts)
- (Optional) Ollama running on host for semantic features

## 1. Start the Sandbox
Run the following command to start RAE-Lite in an isolated project named `rae-sandbox`. This will use port **8002** by default to avoid conflicts.

```bash
docker compose -p rae-sandbox -f docker-compose.lite.yml up -d --build
```

## 2. Initialize Demo Data
To see RAE in action, populate it with sample memories (Project Phoenix and City Hall scenarios):

```bash
# Install dependencies
./.venv/bin/pip install httpx

# Run the seeding script (it uses X-User-Id: admin automatically)
./.venv/bin/python3 scripts/seed_demo_data.py --scenario all
```

## 3. Verify Installation
Test if the system returns results using hybrid search (Full-Text + Math):

```bash
curl -X POST http://localhost:8002/v1/memory/query \
     -H "Content-Type: application/json" \
     -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000100" \
     -H "X-User-Id: admin" \
     -d 
     {
       "query_text": "kickoff meeting",
       "k": 3,
       "project": "phoenix-project"
     }
```

## Key Features of this Setup
- **Hardware Agnostic:** Works without LLM using `FullTextStrategy`.
- **Intelligent Ranking:** Uses `MathLayerController` to rank results by importance and recency.
- **Isolated:** Clean DB volumes and network, no interference with standard RAE.
- **Developer Friendly:** Supports `X-User-Id` header for easy API access without JWT.

## Troubleshooting
If you encounter "Authentication required" errors, ensure you are sending the `X-User-Id: admin` header.
To reset the environment completely:
```bash
docker compose -p rae-sandbox -f docker-compose.lite.yml down -v
```

