# Advanced API Patterns

**Version**: 2.2.0-enterprise

## Overview

This guide covers advanced patterns for production use: batch operations, pagination, error recovery, retry strategies, and rate limiting.

---

## Batch Operations

Process multiple items efficiently with batch endpoints.

### Why Batch?

**Performance**: 10-50x faster than individual calls
- Reduced HTTP overhead
- Database connection pooling
- Transaction batching
- Network optimization

**Use When**: Processing >10 items

### Batch Create Memories

```bash
curl -X POST http://localhost:8000/v1/memory/store/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "memories": [
      {
        "content": "User completed Python tutorial",
        "layer": "episodic",
        "tags": ["learning", "python"],
        "importance": 0.7
      },
      {
        "content": "User prefers dark mode",
        "layer": "semantic",
        "tags": ["preferences", "ui"],
        "importance": 0.8
      },
      {
        "content": "User timezone: America/Los_Angeles",
        "layer": "semantic",
        "tags": ["preferences", "timezone"],
        "importance": 0.9
      }
    ]
  }'
```

**Response**:
```json
{
  "created_count": 3,
  "failed_count": 0,
  "memory_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001",
    "770e8400-e29b-41d4-a716-446655440002"
  ],
  "errors": [],
  "execution_time_ms": 145
}
```

### Batch Create Graph Nodes

```bash
curl -X POST http://localhost:8000/v1/graph-management/nodes/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "nodes": [
      {
        "node_id": "concept_python",
        "label": "Language",
        "properties": {"name": "Python", "type": "programming"}
      },
      {
        "node_id": "concept_javascript",
        "label": "Language",
        "properties": {"name": "JavaScript", "type": "programming"}
      },
      {
        "node_id": "concept_react",
        "label": "Framework",
        "properties": {"name": "React", "type": "frontend"}
      }
    ]
  }'
```

### Batch Create Graph Edges

```bash
curl -X POST http://localhost:8000/v1/graph-management/edges/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "project_id": "my-app",
    "edges": [
      {
        "source_node_id": "concept_react",
        "target_node_id": "concept_javascript",
        "relation": "BUILT_WITH",
        "edge_weight": 1.0
      },
      {
        "source_node_id": "concept_python",
        "target_node_id": "concept_javascript",
        "relation": "SIMILAR_TO",
        "edge_weight": 0.6
      }
    ]
  }'
```

### Batch with Error Handling

```bash
curl -X POST http://localhost:8000/v1/memory/store/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "memories": [
      {"content": "Valid memory", "layer": "episodic"},
      {"content": "", "layer": "episodic"},  # Invalid - empty content
      {"content": "Another valid memory", "layer": "semantic"}
    ],
    "continue_on_error": true
  }'
```

**Response**:
```json
{
  "created_count": 2,
  "failed_count": 1,
  "memory_ids": [
    "550e8400-...",
    null,
    "770e8400-..."
  ],
  "errors": [
    {
      "index": 1,
      "error": "ValidationError: content cannot be empty"
    }
  ]
}
```

### Batch Size Recommendations

| Items | Method | Notes |
|-------|--------|-------|
| 1-10 | Individual calls | Simple, good for small batches |
| 10-50 | Single batch | Optimal batch size |
| 50-200 | Single batch | Still efficient |
| 200-1000 | Multiple batches (200 each) | Split into chunks |
| 1000+ | Background job | Use async processing |

---

## Pagination

Handle large result sets efficiently.

### Why Paginate?

**Benefits**:
- Reduce memory usage
- Faster response times
- Better user experience
- Prevent timeouts

### Offset-Based Pagination

**Use for**: Static data, moderate result sets (<10K items)

```bash
# Page 1
curl "http://localhost:8000/v1/triggers/list?tenant_id=demo&project_id=my-app&limit=50&offset=0" \
  -H "X-API-Key: your-key"

# Page 2
curl "http://localhost:8000/v1/triggers/list?tenant_id=demo&project_id=my-app&limit=50&offset=50" \
  -H "X-API-Key: your-key"

# Page 3
curl "http://localhost:8000/v1/triggers/list?tenant_id=demo&project_id=my-app&limit=50&offset=100" \
  -H "X-API-Key: your-key"
```

**Response**:
```json
{
  "triggers": [...],
  "total_count": 347,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

### Cursor-Based Pagination

**Use for**: Real-time data, large result sets (>10K items)

```bash
# First page
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "query_text": "user preferences",
    "k": 50
  }'
```

**Response**:
```json
{
  "memories": [...],
  "cursor": "eyJsYXN0X2lkIjogIjU1MGU4NDAwLi4uIiwgImxhc3Rfc2NvcmUiOiAwLjg1fQ==",
  "has_more": true
}
```

```bash
# Next page
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "query_text": "user preferences",
    "k": 50,
    "cursor": "eyJsYXN0X2lkIjogIjU1MGU4NDAwLi4uIiwgImxhc3Rfc2NvcmUiOiAwLjg1fQ=="
  }'
```

### Pagination Helper (Python)

```python
import requests

def fetch_all_pages(url, params, max_pages=None):
    """Fetch all pages using offset pagination"""
    all_items = []
    offset = 0
    limit = params.get('limit', 50)
    page = 0

    while True:
        params['offset'] = offset
        response = requests.get(url, params=params)
        data = response.json()

        all_items.extend(data['items'])

        page += 1
        if max_pages and page >= max_pages:
            break

        if not data.get('has_more', False):
            break

        offset += limit

    return all_items

# Usage
items = fetch_all_pages(
    'http://localhost:8000/v1/triggers/list',
    {
        'tenant_id': 'demo',
        'project_id': 'my-app',
        'limit': 50
    },
    max_pages=10  # Safety limit
)
```

### Streaming Large Results

For very large result sets, use streaming:

```bash
curl -N http://localhost:8000/v1/memory/export/stream?tenant_id=demo \
  -H "X-API-Key: your-key" \
  > memories_export.jsonl
```

---

## Error Recovery

Handle failures gracefully with retry strategies.

### Error Types

| Error Type | Status Code | Retry? | Strategy |
|------------|-------------|--------|----------|
| Rate limit | 429 | ✅ Yes | Exponential backoff |
| Server error | 500, 502, 503 | ✅ Yes | Fixed delay |
| Timeout | 504 | ✅ Yes | Exponential backoff |
| Auth failure | 401, 403 | ❌ No | Fix credentials |
| Validation error | 400 | ❌ No | Fix request |
| Not found | 404 | ❌ No | Check resource |

### Exponential Backoff

```python
import time
import requests
from typing import Optional

def make_request_with_retry(
    method: str,
    url: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
) -> requests.Response:
    """
    Make HTTP request with exponential backoff retry

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        max_retries: Maximum retry attempts
        base_delay: Initial retry delay in seconds
        max_delay: Maximum retry delay in seconds
        **kwargs: Additional arguments for requests

    Returns:
        Response object

    Raises:
        requests.HTTPError: If all retries exhausted
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code

            # Don't retry client errors (except 429)
            if 400 <= status_code < 500 and status_code != 429:
                raise

            # Don't retry if last attempt
            if attempt == max_retries:
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)

            # Add jitter to prevent thundering herd
            import random
            delay = delay * (0.5 + random.random() * 0.5)

            print(f"Retry {attempt + 1}/{max_retries} after {delay:.2f}s (status: {status_code})")
            time.sleep(delay)

        except requests.exceptions.Timeout:
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            print(f"Timeout. Retry {attempt + 1}/{max_retries} after {delay:.2f}s")
            time.sleep(delay)

# Usage
response = make_request_with_retry(
    'POST',
    'http://localhost:8000/v1/memory/store',
    json={
        'tenant_id': 'demo',
        'content': 'Memory content',
        'layer': 'episodic'
    },
    headers={'X-API-Key': 'your-key'},
    max_retries=3,
    base_delay=1.0
)
```

### Rate Limit Handling

```python
def handle_rate_limit(response: requests.Response) -> float:
    """
    Extract retry-after from rate limit response

    Returns:
        Seconds to wait before retry
    """
    if response.status_code == 429:
        # Check Retry-After header
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                # Retry-After might be a date
                from email.utils import parsedate_to_datetime
                retry_date = parsedate_to_datetime(retry_after)
                return (retry_date - datetime.now()).total_seconds()

        # Check X-RateLimit-Reset header
        reset_time = response.headers.get('X-RateLimit-Reset')
        if reset_time:
            import time
            return max(0, int(reset_time) - int(time.time()))

    return 60.0  # Default: wait 1 minute

# Usage
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
except requests.HTTPError as e:
    if e.response.status_code == 429:
        wait_time = handle_rate_limit(e.response)
        print(f"Rate limited. Waiting {wait_time}s...")
        time.sleep(wait_time)
        # Retry request
```

### Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Client-side circuit breaker"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""

        # Check if circuit should transition to half-open
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        # Limit calls in half-open state
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise Exception("Circuit breaker half-open limit reached")
            self.half_open_calls += 1

        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            # Transition to closed after successful test
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN

# Usage
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

def api_call():
    return requests.post('http://localhost:8000/v1/memory/store', json=data)

try:
    response = breaker.call(api_call)
except Exception as e:
    print(f"Circuit breaker prevented call: {e}")
```

### Idempotency for Retries

Use idempotency keys to safely retry:

```bash
# Generate unique key
IDEMPOTENCY_KEY=$(uuidgen)

curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $IDEMPOTENCY_KEY" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "content": "Important memory",
    "layer": "episodic"
  }'

# Safe to retry with same key
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $IDEMPOTENCY_KEY" \
  -H "X-API-Key: your-key" \
  -d '{
    "tenant_id": "demo",
    "content": "Important memory",
    "layer": "episodic"
  }'
```

Second call returns same result as first (no duplicate created).

---

## Rate Limiting

Respect API rate limits.

### Default Limits

| Scope | Limit | Window |
|-------|-------|--------|
| Per tenant | 100 requests | 60 seconds |
| Per API key | 1000 requests | 60 seconds |
| Per IP | 200 requests | 60 seconds |

### Rate Limit Headers

```bash
curl -i http://localhost:8000/v1/memory/query \
  -H "X-API-Key: your-key"
```

**Response Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1735603200
```

### Handling 429 Responses

```python
def make_request_with_rate_limit_handling(url, **kwargs):
    """Make request with automatic rate limit handling"""
    while True:
        response = requests.request(**kwargs)

        if response.status_code != 429:
            return response

        # Extract wait time
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after}s...")
        time.sleep(retry_after)

        # Retry
```

### Rate Limit Budgeting

```python
class RateLimiter:
    """Client-side rate limiter using token bucket"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.tokens = max_requests
        self.last_update = time.time()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens"""
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens"""
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        needed = tokens - self.tokens
        return (needed / self.max_requests) * self.window_seconds

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update

        refill = (elapsed / self.window_seconds) * self.max_requests
        self.tokens = min(self.max_requests, self.tokens + refill)
        self.last_update = now

# Usage
limiter = RateLimiter(max_requests=100, window_seconds=60)

for i in range(150):
    if limiter.acquire():
        # Make request
        response = requests.get(url)
    else:
        wait_time = limiter.wait_time()
        print(f"Rate limit reached. Waiting {wait_time:.2f}s")
        time.sleep(wait_time)
```

---

## Complete Example: Robust Batch Upload

```python
import requests
import time
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class BatchResult:
    successful: List[Dict]
    failed: List[Dict]
    total_time: float

def robust_batch_upload(
    memories: List[Dict],
    batch_size: int = 50,
    max_retries: int = 3
) -> BatchResult:
    """
    Upload memories in batches with error handling

    Features:
    - Batch processing
    - Exponential backoff retry
    - Rate limit handling
    - Progress tracking
    """
    successful = []
    failed = []
    start_time = time.time()

    # Split into batches
    batches = [memories[i:i + batch_size] for i in range(0, len(memories), batch_size)]

    for batch_idx, batch in enumerate(batches):
        print(f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} items)")

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    'http://localhost:8000/v1/memory/store/batch',
                    json={'memories': batch},
                    headers={'X-API-Key': 'your-key'},
                    timeout=30
                )

                if response.status_code == 429:
                    # Rate limited
                    wait_time = int(response.headers.get('Retry-After', 60))
                    print(f"  Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                result = response.json()

                # Track results
                successful.extend(result.get('memory_ids', []))
                failed.extend(result.get('errors', []))

                print(f"  ✓ Batch {batch_idx + 1}: {result['created_count']} created, {result['failed_count']} failed")
                break

            except requests.exceptions.HTTPError as e:
                if e.response.status_code < 500:
                    # Client error - don't retry
                    print(f"  ✗ Batch {batch_idx + 1} failed: {e}")
                    failed.extend([{'error': str(e), 'batch': batch_idx}])
                    break

                # Server error - retry
                if attempt == max_retries:
                    print(f"  ✗ Batch {batch_idx + 1} failed after {max_retries} retries")
                    failed.extend([{'error': str(e), 'batch': batch_idx}])
                else:
                    delay = 2 ** attempt
                    print(f"  ⚠ Retry {attempt + 1}/{max_retries} after {delay}s")
                    time.sleep(delay)

            except requests.exceptions.Timeout:
                if attempt == max_retries:
                    print(f"  ✗ Batch {batch_idx + 1} timed out after {max_retries} retries")
                    failed.extend([{'error': 'timeout', 'batch': batch_idx}])
                else:
                    delay = 2 ** attempt
                    print(f"  ⚠ Timeout. Retry {attempt + 1}/{max_retries} after {delay}s")
                    time.sleep(delay)

    total_time = time.time() - start_time

    print(f"\n{'='*50}")
    print(f"Upload complete:")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Rate: {len(successful) / total_time:.2f} items/s")

    return BatchResult(
        successful=successful,
        failed=failed,
        total_time=total_time
    )

# Usage
memories = [
    {'content': f'Memory {i}', 'layer': 'episodic'}
    for i in range(500)
]

result = robust_batch_upload(memories, batch_size=50, max_retries=3)
```

---

## Best Practices Summary

### Batch Operations

✅ **Do**:
- Use batch endpoints for >10 items
- Optimal batch size: 50-200 items
- Enable `continue_on_error` for resilience

❌ **Don't**:
- Exceed 1000 items per batch
- Batch unrelated operations

### Pagination

✅ **Do**:
- Use offset pagination for static data
- Use cursor pagination for real-time data
- Set reasonable page sizes (50-200)

❌ **Don't**:
- Fetch all data without pagination
- Use offset pagination for >10K items

### Error Recovery

✅ **Do**:
- Implement exponential backoff
- Use idempotency keys
- Respect rate limits
- Add jitter to retries

❌ **Don't**:
- Retry 4xx errors (except 429)
- Retry without backoff
- Exceed max retries

### Rate Limiting

✅ **Do**:
- Check rate limit headers
- Implement client-side rate limiter
- Handle 429 gracefully

❌ **Don't**:
- Ignore rate limits
- Hammer API after 429

---

## Further Reading

- [API Reference](../reference/api/api_reference.md) - All endpoints
- [Error Codes](ERROR_CODES.md) - HTTP status codes
- [SDKs](../reference/api/python-sdk.md) - Python SDK handles retries

---

**Last Updated**: 2025-12-04
**API Version**: 2.2.0-enterprise
