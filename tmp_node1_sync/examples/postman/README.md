# Postman Collection for RAE Agentic Memory API

## Overview

Generate and import a Postman collection for all 116 API endpoints from the auto-generated OpenAPI specification.

**Why Postman?**
- ✅ Interactive API testing
- ✅ Environment variables for tenant_id, API keys
- ✅ Pre-request scripts for authentication
- ✅ Test scripts for validation
- ✅ Team collaboration

---

## Quick Start

### Method 1: Import from URL (Easiest)

1. **Start the API**:
   ```bash
   docker compose up memory-api
   ```

2. **Open Postman**

3. **Import → Link**:
   ```
   http://localhost:8000/openapi.json
   ```

4. **Done!** All 116 endpoints imported

---

### Method 2: Generate Collection File

Generate a portable Postman collection JSON file:

```bash
# 1. Ensure API is running
docker compose up memory-api

# 2. Download OpenAPI spec
curl http://localhost:8000/openapi.json > openapi.json

# 3. Convert to Postman collection (using openapi-to-postmanv2)
npx openapi-to-postmanv2 \
  -s openapi.json \
  -o RAE_API_Collection.postman_collection.json \
  -p

# 4. Import into Postman
# File → Import → Choose File → RAE_API_Collection.postman_collection.json
```

---

## Setup Environment Variables

Create a Postman environment with these variables:

### Environment: RAE Development

```json
{
  "name": "RAE Development",
  "values": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "enabled": true
    },
    {
      "key": "tenant_id",
      "value": "demo",
      "enabled": true
    },
    {
      "key": "project_id",
      "value": "my-app",
      "enabled": true
    },
    {
      "key": "api_key",
      "value": "your-api-key-here",
      "enabled": true,
      "type": "secret"
    }
  ]
}
```

### Environment: RAE Production

```json
{
  "name": "RAE Production",
  "values": [
    {
      "key": "base_url",
      "value": "https://api.yourcompany.com",
      "enabled": true
    },
    {
      "key": "tenant_id",
      "value": "prod-tenant",
      "enabled": true
    },
    {
      "key": "project_id",
      "value": "production",
      "enabled": true
    },
    {
      "key": "api_key",
      "value": "your-prod-api-key",
      "enabled": true,
      "type": "secret"
    }
  ]
}
```

---

## Configure Authentication

### Pre-request Script (Collection Level)

Add this to your collection's Pre-request Scripts:

```javascript
// Auto-add authentication headers
pm.request.headers.add({
    key: 'X-API-Key',
    value: pm.environment.get('api_key')
});

pm.request.headers.add({
    key: 'X-Tenant-ID',
    value: pm.environment.get('tenant_id')
});
```

---

## Request Examples

### 1. Store Memory

**Endpoint**: `POST {{base_url}}/v1/memory/store`

**Headers**:
- `Content-Type: application/json`
- `X-API-Key: {{api_key}}`
- `X-Tenant-ID: {{tenant_id}}`

**Body**:
```json
{
  "content": "User completed Python tutorial",
  "layer": "episodic",
  "tags": ["learning", "python"],
  "importance": 0.8
}
```

**Tests** (add to Tests tab):
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has memory_id", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('memory_id');
});

// Save memory_id for other requests
pm.environment.set("last_memory_id", pm.response.json().memory_id);
```

### 2. Query Memory

**Endpoint**: `POST {{base_url}}/v1/memory/query`

**Body**:
```json
{
  "tenant_id": "{{tenant_id}}",
  "query_text": "python learning",
  "k": 10
}
```

**Tests**:
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has results", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.memories).to.be.an('array');
});

pm.test("Results have relevance scores", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.memories[0]).to.have.property('score');
});
```

### 3. Create Trigger

**Endpoint**: `POST {{base_url}}/v1/triggers/create`

**Body**:
```json
{
  "tenant_id": "{{tenant_id}}",
  "project_id": "{{project_id}}",
  "rule_name": "Auto Reflection",
  "event_types": ["memory_created"],
  "conditions": {
    "memory_count": {"operator": ">=", "value": 100}
  },
  "actions": [
    {
      "action_type": "generate_reflection",
      "parameters": {"level": "L1"}
    }
  ],
  "created_by": "postman-test",
  "priority": 5
}
```

---

## Test Suites

### Collection Runner

Run entire collection or folders:

1. **Click "Runner"** in Postman
2. **Select Collection/Folder**
3. **Choose Environment**
4. **Set Iterations**: 1
5. **Add Delay**: 100ms (respect rate limits)
6. **Run**

### Example Test Suite

Create a folder "Core Workflows" with these requests in order:

1. Health Check (`GET /health`)
2. Store Memory (`POST /v1/memory/store`)
3. Query Memory (`POST /v1/memory/query`)
4. Get Memory Stats (`GET /v1/memory/stats`)
5. Delete Memory (`DELETE /v1/memory/delete`)

Run as suite to test full workflow.

---

## Advanced Features

### Dynamic Variables

Use Postman dynamic variables:

```json
{
  "tenant_id": "{{tenant_id}}",
  "memory_id": "{{$guid}}",
  "timestamp": "{{$isoTimestamp}}",
  "random_content": "Memory {{$randomInt}}"
}
```

### Data-Driven Testing

Create CSV file `test_data.csv`:
```csv
content,layer,importance
"User learned Python",episodic,0.8
"User prefers dark mode",semantic,0.7
"User timezone is PST",semantic,0.9
```

Use in Collection Runner:
1. Select Collection
2. **Data** → Select File → `test_data.csv`
3. Reference in body: `{{content}}`, `{{layer}}`, `{{importance}}`
4. Run iterations (one per row)

### Pre-request Scripts (Advanced)

```javascript
// Generate HMAC signature for requests
const crypto = require('crypto-js');
const timestamp = new Date().toISOString();
const secret = pm.environment.get('api_secret');
const message = `${timestamp}:${pm.request.url}`;
const signature = crypto.HmacSHA256(message, secret).toString();

pm.environment.set('request_timestamp', timestamp);
pm.environment.set('request_signature', signature);

pm.request.headers.add({
    key: 'X-Timestamp',
    value: timestamp
});
pm.request.headers.add({
    key: 'X-Signature',
    value: signature
});
```

### Response Chaining

Chain requests using saved variables:

**Request 1**: Store Memory
```javascript
// Tests tab
pm.environment.set("memory_id", pm.response.json().memory_id);
```

**Request 2**: Query Memory
```json
{
  "memory_id": "{{memory_id}}"
}
```

---

## Monitoring & CI/CD

### Newman (CLI Runner)

Run collections from command line:

```bash
# Install Newman
npm install -g newman

# Run collection
newman run RAE_API_Collection.postman_collection.json \
  -e RAE_Development.postman_environment.json \
  --reporters cli,json \
  --reporter-json-export results.json

# Run with delay (respect rate limits)
newman run RAE_API_Collection.postman_collection.json \
  -e RAE_Development.postman_environment.json \
  --delay-request 100 \
  --timeout-request 10000

# Run specific folder
newman run RAE_API_Collection.postman_collection.json \
  --folder "Core Endpoints" \
  -e RAE_Development.postman_environment.json
```

### CI/CD Integration (GitHub Actions)

```yaml
name: API Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Start API
        run: docker compose up -d memory-api

      - name: Wait for API
        run: |
          until curl -f http://localhost:8000/health; do
            sleep 5
          done

      - name: Install Newman
        run: npm install -g newman

      - name: Run Postman Tests
        run: |
          newman run examples/postman/RAE_API_Collection.postman_collection.json \
            -e examples/postman/RAE_Development.postman_environment.json \
            --reporters cli,junit \
            --reporter-junit-export test-results.xml

      - name: Publish Test Results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: test-results.xml
```

---

## Troubleshooting

### SSL Certificate Errors

Disable SSL verification (development only):
- Postman → Settings → General → **SSL certificate verification**: OFF

### Rate Limit Errors

Add delay between requests:
- Collection Runner → Delay: 100ms

Or use pre-request script:
```javascript
// Wait before request
setTimeout(function(){}, 100);
```

### Authentication Failures

Check environment variables:
```javascript
// Pre-request script
console.log('API Key:', pm.environment.get('api_key'));
console.log('Tenant ID:', pm.environment.get('tenant_id'));
```

---

## Best Practices

### 1. Use Environments

✅ **Do**: Create separate environments for dev/staging/prod

❌ **Don't**: Hardcode API keys or URLs

### 2. Add Tests

✅ **Do**: Validate status codes, response schema, data

❌ **Don't**: Just make requests without validation

### 3. Organize Collections

✅ **Do**: Use folders to group related endpoints

```
RAE API Collection
├── Core
│   ├── Health
│   ├── Memory
│   └── Agent
├── Enterprise
│   ├── Event Triggers
│   ├── Reflections
│   └── Graph Enhanced
└── Compliance
    ├── Approvals
    ├── Provenance
    └── Circuit Breakers
```

### 4. Document Requests

✅ **Do**: Add descriptions to requests and folders

### 5. Version Control

✅ **Do**: Export and commit collection JSON to git

```bash
# Export from Postman
# Commit to repo
git add examples/postman/*.json
git commit -m "chore: update Postman collection"
```

---

## Resources

- **Postman Learning Center**: https://learning.postman.com/
- **OpenAPI to Postman Converter**: https://github.com/postmanlabs/openapi-to-postman
- **Newman Documentation**: https://github.com/postmanlabs/newman
- **API Documentation**: [API_INDEX.md](../../docs/reference/api/API_INDEX.md)

---

**Last Updated**: 2025-12-04
**API Version**: 2.2.0-enterprise
**Total Endpoints**: 116
