# CLI Reference

## Overview

The RAE CLI (`agent-cli`) provides command-line tools for interacting with RAE, managing data, and diagnostics.

**Location**: `cli/agent-cli/`

## Installation

```bash
# From repository
cd cli/agent-cli
pip install -e .

# Verify installation
rae --version
```

## Configuration

### Environment Variables

```bash
RAE_BASE_URL=http://localhost:8000
RAE_API_KEY=your-api-key
RAE_TENANT_ID=your-tenant-id
RAE_PROJECT_ID=default
```

### Config File

Create `~/.rae/config.yaml`:

```yaml
default_profile: production

profiles:
  production:
    base_url: https://rae.example.com
    api_key: ${RAE_API_KEY}
    tenant_id: tenant-123
    project_id: default

  local:
    base_url: http://localhost:8000
    api_key: test-key
    tenant_id: test-tenant
    project_id: default
```

## Commands

### rae memory

Manage memories.

```bash
# Store a memory
rae memory store "User prefers dark mode" \
  --source cli \
  --importance 0.7 \
  --tags ui,preferences

# Query memories
rae memory query "What are user preferences?" \
  --k 10 \
  --min-importance 0.5

# List recent memories
rae memory list --limit 20 --layer em

# Delete memory
rae memory delete <memory-id>

# Export memories to JSON
rae memory export --output memories.json --layer em
```

### rae query

Perform searches and queries.

```bash
# Semantic search
rae query "How does authentication work?" --k 5

# GraphRAG query
rae query graph "What are the dependencies of module X?" \
  --max-depth 2

# Hybrid search
rae query hybrid "database optimization" \
  --semantic-weight 0.7 \
  --keyword-weight 0.3
```

### rae ingest

Import data into RAE.

```bash
# Ingest documents
rae ingest documents ./docs/*.md \
  --source documentation \
  --importance 0.8 \
  --tags docs,reference

# Ingest from JSON
rae ingest json memories.json

# Ingest git history
rae ingest git --repo . \
  --branch main \
  --since "2025-01-01"
```

### rae worker

Control background workers.

```bash
# Run decay cycle
rae worker decay --tenant-id tenant-123

# Run dreaming cycle
rae worker dream --tenant-id tenant-123 --lookback-hours 24

# Run summarization
rae worker summarize --session-id <uuid>

# Run full maintenance
rae worker maintenance --all-tenants
```

### rae stats

View statistics and usage.

```bash
# Memory statistics
rae stats memories

# Cost usage
rae stats cost --month 2025-12

# API usage
rae stats api --last-7-days

# Budget status
rae stats budget
```

### rae tenant

Manage tenants (admin only).

```bash
# Create tenant
rae tenant create --name "Acme Corp" --plan enterprise

# List tenants
rae tenant list

# Get tenant info
rae tenant info <tenant-id>

# Update tenant settings
rae tenant update <tenant-id> --budget 1000
```

### rae config

Manage CLI configuration.

```bash
# Show current config
rae config show

# Set profile
rae config use local

# Set configuration values
rae config set base_url http://localhost:8000
```

## Usage Examples

### Example 1: Daily Development Workflow

```bash
# Morning: Review what happened yesterday
rae memory list --since yesterday --tags development

# Store important code decision
rae memory store "Decided to use Redis for caching" \
  --importance 0.9 \
  --tags decision,architecture

# Search for past decisions
rae query "caching strategy decisions" --tags decision
```

### Example 2: Bulk Import Documentation

```bash
# Import all markdown docs
rae ingest documents ./docs/**/*.md \
  --source documentation \
  --importance 0.7 \
  --batch-size 50

# Verify import
rae stats memories --layer em --source documentation
```

### Example 3: Debug Cost Issues

```bash
# Check current budget
rae stats budget

# View detailed cost breakdown
rae stats cost --month 2025-12 --detailed

# Check which profiles are expensive
rae stats cost --by-profile
```

## Output Formats

The CLI supports multiple output formats:

```bash
# JSON output
rae memory query "test" --format json

# Table output (default)
rae memory list --format table

# CSV output
rae memory list --format csv > memories.csv

# YAML output
rae config show --format yaml
```

## Scripting

Use the CLI in scripts:

```bash
#!/bin/bash

# Store all git commits from today
git log --since=midnight --format="%s" | while read commit; do
  rae memory store "$commit" \
    --source git \
    --importance 0.6 \
    --tags commit
done

# Check if budget exceeded
budget_status=$(rae stats budget --format json | jq -r '.status')
if [ "$budget_status" = "exceeded" ]; then
  echo "WARNING: Budget exceeded!"
  exit 1
fi
```

## Related Documentation

- [Python SDK](./SDK_PYTHON_REFERENCE.md) - Programmatic access
- [Background Workers](./BACKGROUND_WORKERS.md) - Worker commands
- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant management
