# RAE Code Conventions - Patterns and Why We Use Them

> **Purpose**: This document explains the architectural patterns, conventions, and **WHY** we use them. Understanding the reasoning helps agents write code that fits naturally into the existing codebase.
>
> **⚠️ CRITICAL**: This document describes HOW to write code. For WHAT rules you MUST follow, read [CRITICAL_AGENT_RULES.md](./CRITICAL_AGENT_RULES.md) first!
> - 3-phase testing workflow (RULE #1 & #3)
> - `make format && make lint` before every commit
> - tenant_id in all queries (RULE #4)
> - No interactive commands (RULE #6)
> - Tests as contracts (RULE #7)
> - Auto vs manual documentation (RULE #8)

## 🏛️ Architecture Philosophy

### Core Principle: Separation of Concerns

**Why?**
- **Testability**: Each layer can be tested independently
- **Maintainability**: Changes in one layer don't cascade to others
- **Scalability**: Easy to replace implementations (e.g., swap databases)
- **Team collaboration**: Clear boundaries for parallel development

**The Three Layers**:
```
┌─────────────────────────────────────┐
│   API Layer (FastAPI Routes)       │  ← HTTP requests/responses
│   - Input validation                │  ← Pydantic models
│   - Authentication/Authorization    │  ← Security middleware
│   - Response formatting             │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│   Service Layer (Business Logic)   │  ← Orchestration
│   - Business rules                  │  ← Domain logic
│   - Workflow orchestration          │  ← Composition
│   - Cross-cutting concerns          │  ← Logging, metrics
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│   Repository Layer (Data Access)   │  ← Database queries
│   - SQL queries                     │  ← PostgreSQL
│   - Connection pooling              │  ← AsyncPG
│   - Data mapping                    │  ← Dict ↔ Model
└─────────────────────────────────────┘
```

## 🗂️ Repository Pattern

### What It Is

A **Repository** encapsulates all database operations for a specific entity or aggregate.

### Why We Use It

1. **Single Responsibility**: Each repository handles ONE entity's data access
2. **Testability**: Easy to mock repositories in service tests
3. **Database Agnostic**: Business logic doesn't depend on SQL details
4. **Query Optimization**: Centralized place for query tuning
5. **RLS (Row Level Security)**: Consistent tenant isolation

### Pattern Structure

```python
class EntityRepository:
    """
    Repository for [Entity] data access operations.

    Handles all SQL queries related to [Entity] CRUD operations.
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize repository.

        Args:
            pool: AsyncPG connection pool for database operations
        """
        self.pool = pool

    async def get_by_id(self, entity_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve entity by ID.

        Args:
            entity_id: Unique identifier
            tenant_id: Tenant identifier for RLS

        Returns:
            Entity dict or None if not found

        Raises:
            asyncpg.PostgresError: If database query fails
        """
        query = """
            SELECT * FROM entities
            WHERE id = $1 AND tenant_id = $2
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, entity_id, tenant_id)
            return dict(record) if record else None

    async def insert(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new entity."""
        # Implementation...

    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing entity."""
        # Implementation...

    async def delete(self, entity_id: str, tenant_id: str) -> bool:
        """Delete entity."""
        # Implementation...
```

### Key Rules

1. **✅ DO**: Return dicts or None (let services handle model conversion)
2. **✅ DO**: Accept primitive types (str, int, Dict) as parameters
3. **✅ DO**: Include tenant_id in all queries (multi-tenancy)
4. **✅ DO**: Use parameterized queries ($1, $2) to prevent SQL injection
5. **✅ DO**: Use async/await for all database operations
6. **✅ DO**: Log errors with structured logging (structlog)

7. **❌ DON'T**: Import Pydantic models in repositories
8. **❌ DON'T**: Put business logic in repositories (only data access)
9. **❌ DON'T**: Call other repositories from a repository
10. **❌ DON'T**: Use raw SQL strings without parameterization

### Example: Why NOT to Put Business Logic in Repository

```python
# ❌ BAD - Business logic in repository
class OrderRepository:
    async def create_order(self, order_data: Dict) -> Dict:
        # Calculating discount is BUSINESS LOGIC
        if order_data['total'] > 100:
            order_data['discount'] = 0.10  # ❌ DON'T

        query = "INSERT INTO orders ..."
        # ...

# ✅ GOOD - Repository only does data access
class OrderRepository:
    async def insert_order(self, order_data: Dict) -> Dict:
        """Insert order (expects discount already calculated)."""
        query = "INSERT INTO orders ..."
        # ...

class OrderService:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    async def create_order(self, order_data: Dict) -> Order:
        # Business logic in service ✅
        if order_data['total'] > 100:
            order_data['discount'] = self._calculate_discount(order_data['total'])

        result = await self.order_repo.insert_order(order_data)
        return Order(**result)
```

## 🔧 Service Pattern

### What It Is

A **Service** contains business logic and orchestrates operations across multiple repositories or external services.

### Why We Use It

1. **Business Logic Centralization**: All domain rules in one place
2. **Testability**: Mock dependencies, test logic in isolation
3. **Reusability**: Services can call other services
4. **Transaction Management**: Coordinate multi-step operations
5. **Clear API**: Well-defined methods for common operations

### Pattern Structure

```python
class MyBusinessService:
    """
    Service for [Business Domain] operations.

    Handles business logic for [specific domain], orchestrating
    operations across repositories and external services.

    Features:
    - Feature 1 description
    - Feature 2 description
    - Full Dependency Injection for testability
    """

    def __init__(
        self,
        entity_repo: EntityRepository,
        other_service: OtherService,
        pool: asyncpg.Pool,  # If needed for additional operations
    ):
        """
        Initialize service with dependencies.

        Args:
            entity_repo: Repository for entity data access
            other_service: Other service for related operations
            pool: Database connection pool (if needed)
        """
        self.entity_repo = entity_repo
        self.other_service = other_service
        self.pool = pool
        self.logger = structlog.get_logger(__name__)

    async def perform_complex_operation(
        self,
        tenant_id: str,
        input_data: InputModel,
    ) -> OutputModel:
        """
        Perform complex business operation.

        This method orchestrates multiple steps:
        1. Validate input
        2. Fetch related data
        3. Apply business rules
        4. Persist results
        5. Return formatted output

        Args:
            tenant_id: Tenant identifier for multi-tenancy
            input_data: Validated input (Pydantic model)

        Returns:
            OutputModel: Result of operation

        Raises:
            ValueError: If business rules are violated
            DatabaseError: If persistence fails
        """
        self.logger.info(
            "operation_started",
            tenant_id=tenant_id,
            operation="complex_operation"
        )

        try:
            # Step 1: Validate business rules
            self._validate_business_rules(input_data)

            # Step 2: Fetch related data
            related_data = await self.entity_repo.get_related(
                input_data.entity_id,
                tenant_id
            )

            # Step 3: Apply business logic
            result = self._apply_business_logic(input_data, related_data)

            # Step 4: Persist
            saved = await self.entity_repo.insert(result)

            # Step 5: Post-processing (e.g., trigger events)
            await self.other_service.notify(saved['id'])

            self.logger.info(
                "operation_completed",
                tenant_id=tenant_id,
                result_id=saved['id']
            )

            return OutputModel(**saved)

        except ValueError as e:
            self.logger.warning(
                "business_rule_violation",
                tenant_id=tenant_id,
                error=str(e)
            )
            raise

        except Exception as e:
            self.logger.exception(
                "operation_failed",
                tenant_id=tenant_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to complete operation: {e}")

    def _validate_business_rules(self, input_data: InputModel):
        """Private method for business validation."""
        if input_data.amount < 0:
            raise ValueError("Amount must be positive")

    def _apply_business_logic(self, input_data, related_data) -> Dict:
        """Private method for business calculations."""
        # Complex business logic here
        return {...}
```

### Key Rules

1. **✅ DO**: Use Dependency Injection (pass dependencies in __init__)
2. **✅ DO**: Use Pydantic models for input/output
3. **✅ DO**: Log important operations with structlog
4. **✅ DO**: Validate business rules before calling repository
5. **✅ DO**: Handle exceptions and wrap them appropriately
6. **✅ DO**: Use private methods (_method_name) for internal logic
7. **✅ DO**: Document complex operations with step-by-step comments

8. **❌ DON'T**: Access database directly (use repositories)
9. **❌ DON'T**: Import FastAPI dependencies (HTTPException, Request, etc.)
10. **❌ DON'T**: Mix multiple domains in one service (Single Responsibility)

### Example: Why Use Dependency Injection

```python
# ❌ BAD - Hard-coded dependencies (untestable)
class OrderService:
    def __init__(self):
        # Creating dependencies inside __init__ ❌
        self.repo = OrderRepository(get_pool())  # Hard to mock!
        self.email_service = EmailService()  # Can't test without sending emails!

    async def create_order(self, order: Order):
        await self.repo.insert(order)
        await self.email_service.send_confirmation(order.email)

# ✅ GOOD - Dependency Injection (testable)
class OrderService:
    def __init__(self, repo: OrderRepository, email_service: EmailService):
        # Dependencies injected ✅
        self.repo = repo
        self.email_service = email_service

    async def create_order(self, order: Order):
        await self.repo.insert(order)
        await self.email_service.send_confirmation(order.email)

# In tests:
async def test_create_order():
    mock_repo = Mock(OrderRepository)
    mock_email = Mock(EmailService)

    service = OrderService(mock_repo, mock_email)  # ✅ Easy to inject mocks

    await service.create_order(test_order)

    mock_repo.insert.assert_called_once()
    mock_email.send_confirmation.assert_called_once()
```

## 🌐 API Layer (FastAPI Routes)

### What It Is

FastAPI **router endpoints** that handle HTTP requests and responses.

### Why We Use It

1. **Input Validation**: Pydantic models validate requests automatically
2. **Documentation**: OpenAPI docs generated automatically
3. **Security**: Centralized authentication/authorization
4. **HTTP Concerns**: Status codes, headers separate from business logic
5. **Error Handling**: Consistent HTTP error responses

### Pattern Structure

```python
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.memory_api.models import InputModel, OutputModel
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.my_service import MyBusinessService

router = APIRouter(
    prefix="/my-domain",
    tags=["my-domain"],
    dependencies=[Depends(auth.verify_token)],  # Require auth for all endpoints
)

logger = structlog.get_logger(__name__)


@router.post("/operation", response_model=OutputModel)
async def perform_operation(
    input_data: InputModel,  # Pydantic validates automatically
    request: Request,  # Access to app state (pool, etc.)
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),  # RBAC
):
    """
    Perform business operation.

    This endpoint orchestrates [business operation] by:
    1. Validating input (automatic via Pydantic)
    2. Checking authorization (automatic via Depends)
    3. Delegating to service layer
    4. Formatting response

    **Security:** Requires authentication and tenant access.

    **Request Body:**
    ```json
    {
        "field1": "value1",
        "field2": 123
    }
    ```

    **Response:**
    ```json
    {
        "id": "uuid",
        "result": "success"
    }
    ```

    Args:
        input_data: Input model with validated fields
        request: FastAPI request object
        verified_tenant_id: Tenant ID from RBAC verification

    Returns:
        OutputModel: Result of operation

    Raises:
        HTTPException 400: If input validation fails
        HTTPException 401: If not authenticated
        HTTPException 403: If not authorized for tenant
        HTTPException 500: If operation fails
    """

    # Use verified tenant_id from RBAC
    tenant_id = verified_tenant_id

    logger.info(
        "api_request",
        endpoint="perform_operation",
        tenant_id=tenant_id,
        method=request.method
    )

    try:
        # Initialize service with dependencies
        service = MyBusinessService(
            entity_repo=EntityRepository(request.app.state.pool),
            other_service=OtherService(...),
            pool=request.app.state.pool,
        )

        # Delegate to service layer
        result = await service.perform_complex_operation(
            tenant_id=tenant_id,
            input_data=input_data,
        )

        logger.info(
            "api_success",
            endpoint="perform_operation",
            tenant_id=tenant_id,
            result_id=result.id
        )

        return result

    except ValueError as e:
        # Business rule violation → 400 Bad Request
        logger.warning(
            "api_validation_error",
            endpoint="perform_operation",
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Unexpected error → 500 Internal Server Error
        logger.exception(
            "api_error",
            endpoint="perform_operation",
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/resource/{resource_id}", response_model=OutputModel)
async def get_resource(
    resource_id: str,
    request: Request,
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),
):
    """Get resource by ID. Security: Requires authentication."""
    # Implementation...
```

### Key Rules

1. **✅ DO**: Use Pydantic models for request/response
2. **✅ DO**: Use Depends() for authentication and dependencies
3. **✅ DO**: Document with docstrings (appears in OpenAPI)
4. **✅ DO**: Log all requests and errors
5. **✅ DO**: Map exceptions to appropriate HTTP status codes
6. **✅ DO**: Delegate business logic to services (thin controllers)
7. **✅ DO**: Use response_model for automatic serialization

8. **❌ DON'T**: Put business logic in route handlers
9. **❌ DON'T**: Access repositories directly from routes
10. **❌ DON'T**: Return raw dicts (use Pydantic response_model)
11. **❌ DON'T**: Expose internal error details to clients

### HTTP Status Code Guidelines

| Status | When to Use | Example |
|--------|-------------|---------|
| 200 OK | Successful GET/PATCH | Fetched resource |
| 201 Created | Successful POST (resource created) | Created new memory |
| 204 No Content | Successful DELETE | Deleted resource |
| 400 Bad Request | Invalid input / business rule violation | Invalid email format |
| 401 Unauthorized | Missing/invalid authentication | No JWT token |
| 403 Forbidden | Authenticated but not authorized | Wrong tenant |
| 404 Not Found | Resource doesn't exist | Memory ID not found |
| 409 Conflict | Resource conflict | Duplicate entry |
| 422 Unprocessable Entity | Validation failed (Pydantic) | Missing required field |
| 500 Internal Server Error | Unexpected error | Database down |

## 🧪 Testing Conventions

### Test File Naming

```
Code: apps/memory_api/services/hybrid_search.py
Test: apps/memory_api/tests/services/test_hybrid_search.py

Code: apps/llm/providers/openai.py
Test: apps/llm/tests/providers/test_openai.py
```

### Test Function Naming

```python
# ✅ GOOD - Descriptive test names
def test_calculate_score_returns_zero_for_empty_input():
    ...

def test_calculate_score_raises_value_error_for_negative_weight():
    ...

async def test_store_memory_persists_to_database():
    ...

# ❌ BAD - Vague test names
def test_score():
    ...

def test_1():
    ...
```

### Test Structure (AAA Pattern)

```python
@pytest.mark.unit
def test_calculate_importance_score():
    # Arrange: Set up test data
    memory_data = {
        'content': 'Important meeting notes',
        'source': 'user_input',
        'tags': ['work', 'meeting']
    }
    service = ImportanceScoringService()

    # Act: Execute the operation
    score = service.calculate_score(memory_data)

    # Assert: Verify the result
    assert 0.0 <= score <= 1.0
    assert score > 0.5  # Should be high importance
```

### Mocking Guidelines

```python
from unittest.mock import AsyncMock, Mock, patch

@pytest.mark.unit
async def test_service_handles_repository_error():
    # Mock repository
    mock_repo = Mock(spec=MemoryRepository)
    mock_repo.get_by_id = AsyncMock(side_effect=DatabaseError("Connection lost"))

    # Initialize service with mock
    service = MemoryService(repo=mock_repo)

    # Test error handling
    with pytest.raises(ServiceError):
        await service.fetch_memory("mem_123", "tenant_1")

    # Verify repository was called
    mock_repo.get_by_id.assert_called_once_with("mem_123", "tenant_1")
```

### What to Test

**✅ DO Test:**
- Business logic (algorithms, calculations)
- Error handling (invalid input, edge cases)
- Boundary conditions (empty lists, null values, max values)
- Integration between layers (service + repository)

**❌ DON'T Test:**
- Third-party libraries (trust them)
- Framework behavior (FastAPI, Pydantic)
- Trivial getters/setters
- Private methods directly (test through public API)

## 🔐 Security Conventions

### Multi-Tenancy (Row Level Security)

**Every query MUST include tenant_id:**

```python
# ✅ CORRECT - Includes tenant_id
query = """
    SELECT * FROM memories
    WHERE id = $1 AND tenant_id = $2
"""
result = await conn.fetchrow(query, memory_id, tenant_id)

# ❌ WRONG - Missing tenant_id (SECURITY VIOLATION!)
query = """
    SELECT * FROM memories
    WHERE id = $1
"""
result = await conn.fetchrow(query, memory_id)  # ❌ Can access other tenants' data!
```

### Authentication Flow

```
Request → verify_token() → get_and_verify_tenant_id() → Handler
            ↓                      ↓
       Check JWT           Check tenant access
            ↓                      ↓
       Extract tenant      Compare with request
            ↓                      ↓
       Return tenant_id    Return verified_tenant_id
```

### Using Auth in Routes

```python
@router.post("/endpoint")
async def my_endpoint(
    data: InputModel,
    verified_tenant_id: str = Depends(get_and_verify_tenant_id),  # ✅ Use this
):
    # verified_tenant_id is GUARANTEED to be:
    # 1. From authenticated JWT
    # 2. Authorized for this request
    # 3. Safe to use in queries

    await service.do_something(tenant_id=verified_tenant_id, data=data)
```

## 📊 Logging Conventions

### Structured Logging (structlog)

```python
import structlog

logger = structlog.get_logger(__name__)

# ✅ GOOD - Structured logging
logger.info(
    "memory_stored",
    memory_id=memory_id,
    tenant_id=tenant_id,
    layer="episodic",
    tokens=1234
)

logger.error(
    "database_error",
    operation="insert_memory",
    tenant_id=tenant_id,
    error=str(e)
)

# ❌ BAD - Unstructured logging
logger.info(f"Stored memory {memory_id} for tenant {tenant_id}")  # Hard to parse!
```

### Log Levels

- **DEBUG**: Detailed diagnostic information (not in production)
- **INFO**: General informational messages (operation success)
- **WARNING**: Something unexpected but handled
- **ERROR**: Operation failed, needs attention
- **EXCEPTION**: Use `logger.exception()` in except blocks (includes traceback)

## 🎯 Pydantic Model Conventions

### Input Models (Requests)

```python
from pydantic import BaseModel, Field, validator

class StoreMemoryRequest(BaseModel):
    """Request model for storing a memory."""

    content: str = Field(..., min_length=1, max_length=10000, description="Memory content")
    source: str = Field(..., description="Source of the memory")
    tags: List[str] = Field(default_factory=list, description="Optional tags")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score")

    @validator('content')
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Meeting notes about project X",
                "source": "user_input",
                "tags": ["work", "meeting"],
                "importance": 0.8
            }
        }
```

### Output Models (Responses)

```python
class MemoryResponse(BaseModel):
    """Response model for memory operations."""

    id: str = Field(..., description="Unique memory identifier")
    content: str
    tenant_id: str
    created_at: datetime
    importance: float

    class Config:
        from_attributes = True  # Allow creation from ORM models
```

## 🔄 Error Handling Patterns

### Custom Exceptions

```python
# apps/memory_api/exceptions.py

class RAEException(Exception):
    """Base exception for RAE application."""
    pass

class ServiceError(RAEException):
    """Service layer error."""
    pass

class DatabaseError(RAEException):
    """Database operation error."""
    pass

class BusinessRuleViolation(RAEException):
    """Business rule was violated."""
    pass
```

### Error Handling in Layers

```python
# Repository Layer: Let PostgreSQL errors bubble up
async def insert_memory(self, data: Dict) -> Dict:
    try:
        result = await self.pool.fetchrow(query, *params)
        return dict(result)
    except asyncpg.PostgresError as e:
        # Log but don't catch - let service handle it
        logger.error("db_error", error=str(e))
        raise

# Service Layer: Catch and wrap with domain-specific errors
async def store_memory(self, data: MemoryInput) -> Memory:
    try:
        result = await self.repo.insert_memory(data.dict())
        return Memory(**result)
    except asyncpg.PostgresError as e:
        raise DatabaseError(f"Failed to store memory: {e}")
    except ValueError as e:
        raise BusinessRuleViolation(f"Invalid memory data: {e}")

# API Layer: Convert to HTTP exceptions
@router.post("/memories")
async def store_memory(data: MemoryInput, ...):
    try:
        memory = await service.store_memory(data)
        return memory
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.exception("api_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 💡 Summary: When to Use What

| Scenario | Use | Don't Use |
|----------|-----|-----------|
| Database query | Repository | Service, API route |
| Business logic | Service | Repository, API route |
| HTTP handling | API route | Service, Repository |
| Input validation | Pydantic model | Manual checks in service |
| Error for client | HTTPException | Generic Exception |
| Error in service | Custom exception | HTTPException |
| Logging | Structlog with fields | Print or string logs |
| Testing services | Mock repositories | Real database |
| Testing repositories | Real database (integration) | Mocking SQL |

## 📚 Additional Resources

- **Real Examples**: See `.ai-templates/` for working code examples
- **Project Structure**: `PROJECT_STRUCTURE.md` for file locations
- **Testing Policy**: `docs/AGENTS_TEST_POLICY.md` for detailed test guidelines

---

**Key Takeaway**: These conventions exist to make the codebase **predictable, testable, and maintainable**. Follow them and your code will integrate seamlessly!

**Last Updated**: 2025-12-04
**Maintained by**: AI Agent Code Quality System
