# AI Agent Code Templates

> **Purpose**: These templates provide working examples of the RAE project's architecture patterns. Use them as starting points for new code to ensure consistency and quality.

## 📚 Available Templates

### 1. `repository_template.py` - Data Access Layer

**Use when**: Adding new database table/entity

**What it includes**:
- Complete CRUD operations (Create, Read, Update, Delete)
- Row Level Security (RLS) with tenant_id
- Error handling and logging
- Dynamic query building
- Example test cases

**Example use case**: Adding user profiles, orders, notifications

### 2. `service_template.py` - Business Logic Layer

**Use when**: Adding business operations/workflows

**What it includes**:
- Dependency Injection pattern
- Pydantic models for input/output
- Business rule validation
- Error handling with custom exceptions
- Private helper methods
- Example test cases (unit + integration)

**Example use case**: Order processing, user registration, data transformation

### 3. `route_template.py` - API Endpoints

**Use when**: Adding REST API endpoints

**What it includes**:
- Complete CRUD endpoints (POST, GET, PATCH, DELETE)
- Authentication and authorization
- Input validation (Pydantic)
- HTTP status codes
- OpenAPI documentation
- Error handling
- Example test cases

**Example use case**: User API, order API, notification API

### 4. `test_template.py` - Testing Patterns

**Use when**: Writing tests for any layer

**What it includes**:
- Unit test examples (with mocks)
- Integration test examples (with real DB)
- API test examples (with TestClient)
- Parametrized tests
- Fixtures
- AAA pattern (Arrange-Act-Assert)

**Example use case**: Testing any new code

## 🎯 How to Use These Templates

### Step-by-Step Process

1. **Read the relevant documentation first**:
   - `PROJECT_STRUCTURE.md` - Where to put files
   - `CONVENTIONS.md` - Why we use these patterns
   - This README - Which template to use

2. **Choose the right template(s)**:
   - Adding new entity? → Use all 3 (repository, service, route)
   - Adding business logic? → Use service template
   - Adding API endpoint? → Use route template
   - Adding tests? → Use test template

3. **Copy and customize**:
   - Open the template file
   - Read the "WHY" comments to understand the pattern
   - Replace "Entity" with your entity name
   - Replace "MyBusiness" with your domain name
   - Keep the structure intact
   - Customize the specific logic

4. **Follow the checklist** (in template comments):
   - ✅ Correct file location (PROJECT_STRUCTURE.md)
   - ✅ Naming conventions followed
   - ✅ Security: tenant_id in queries
   - ✅ Logging added
   - ✅ Tests added
   - ✅ Docstrings added

5. **Run linting and tests**:
   ```bash
   make lint
   pytest --no-cov apps/memory_api/tests/path/to/test_your_feature.py
   ```

## 💡 Common Patterns (Quick Reference)

### Pattern 1: Adding a Complete New Entity

**Files to create** (following templates):

1. **Repository**: `apps/memory_api/repositories/my_entity_repository.py`
   - Template: `repository_template.py`
   - Methods: get_by_id, get_all, insert, update, delete

2. **Service**: `apps/memory_api/services/my_entity_service.py`
   - Template: `service_template.py`
   - Methods: create_entity, get_entity, update_entity, delete_entity
   - Plus business logic methods

3. **API**: `apps/memory_api/api/v1/my_entities.py`
   - Template: `route_template.py`
   - Endpoints: POST, GET, PATCH, DELETE

4. **Tests**:
   - `apps/memory_api/tests/repositories/test_my_entity_repository.py`
   - `apps/memory_api/tests/services/test_my_entity_service.py`
   - `apps/memory_api/tests/api/v1/test_my_entities.py`
   - Template: `test_template.py`

5. **Register router**:
   - Edit: `apps/memory_api/api/v1/__init__.py`
   - Add: `from .my_entities import router as my_entities_router`
   - Add: `app.include_router(my_entities_router)`

### Pattern 2: Adding Business Logic Only

**Files to create**:

1. **Service**: `apps/memory_api/services/my_logic_service.py`
   - Template: `service_template.py`
   - Inject existing repositories
   - Add business methods

2. **Tests**: `apps/memory_api/tests/services/test_my_logic_service.py`
   - Template: `test_template.py` (unit tests section)

### Pattern 3: Adding API Endpoint to Existing Service

**Files to modify**:

1. **API**: `apps/memory_api/api/v1/existing_domain.py`
   - Template: `route_template.py` (copy endpoint example)
   - Add new @router.post or @router.get

2. **Tests**: `apps/memory_api/tests/api/v1/test_existing_domain.py`
   - Template: `test_template.py` (API tests section)

## 🔍 Template Features Explained

### Why Templates Include "WHY" Comments

```python
# ✅ GOOD - Template with explanation
def insert(self, data: Dict) -> Dict:
    """
    Insert entity.

    WHY: Centralized insertion logic
    WHY: Handles dynamic fields and returns full record
    """
    # Implementation...

# ❌ BAD - No context
def insert(self, data: Dict) -> Dict:
    """Insert entity."""
    # Implementation...
```

**Benefit**: Agents understand the reasoning and maintain it correctly.

### Why Templates Use Specific Patterns

| Pattern | Why | Example in Template |
|---------|-----|---------------------|
| Dependency Injection | Testability, loose coupling | `__init__(self, repo: Repo, service: Service)` |
| Pydantic Models | Type safety, validation | `input_data: EntityInput` |
| Structured Logging | Searchable logs, metrics | `logger.info("event", field=value)` |
| AAA Test Pattern | Readable tests | `# Arrange → Act → Assert` |
| Async/Await | Non-blocking I/O | `async def method() → await repo.fetch()` |

## 🎓 Learning from Templates

### For New AI Agents

If you're a new agent working on this project:

1. **Start here**: Read all 4 templates completely
2. **Understand WHY**: Pay attention to "WHY" comments
3. **See patterns**: Notice how layers interact
4. **Check examples**: See test examples at bottom of each template
5. **Apply consistently**: Use same patterns everywhere

### For Experienced Agents

Quick checklist when adding code:

- [ ] Matches template structure?
- [ ] All "WHY" patterns followed?
- [ ] Security (tenant_id) included?
- [ ] Tests added?
- [ ] Logging added?
- [ ] Docstrings complete?

## 🚨 Common Mistakes (Learn from Others)

### Mistake 1: Skipping Layers

❌ **Wrong**: API directly accessing database
```python
@router.post("/entities")
async def create(data: Input, request: Request):
    query = "INSERT INTO entities ..."  # ❌ Direct SQL in API
    result = await request.app.state.pool.fetchrow(query)
```

✅ **Correct**: API → Service → Repository
```python
@router.post("/entities")
async def create(data: Input, request: Request):
    service = EntityService(EntityRepository(pool), pool)
    return await service.create_entity(tenant_id, data)
```

### Mistake 2: Business Logic in Repository

❌ **Wrong**: Validation in repository
```python
class EntityRepository:
    async def insert(self, data: Dict):
        if data['value'] > 100:  # ❌ Business rule in repository
            raise ValueError("Too high")
        # ...
```

✅ **Correct**: Business logic in service
```python
class EntityService:
    async def create_entity(self, data: EntityInput):
        if data.value > 100:  # ✅ Business rule in service
            raise BusinessRuleViolation("Too high")
        await self.repo.insert(data.dict())
```

### Mistake 3: Missing Tenant Isolation

❌ **Wrong**: No tenant_id in query
```python
query = "SELECT * FROM entities WHERE id = $1"  # ❌ Security risk!
result = await conn.fetchrow(query, entity_id)
```

✅ **Correct**: Always include tenant_id
```python
query = "SELECT * FROM entities WHERE id = $1 AND tenant_id = $2"  # ✅ Secure
result = await conn.fetchrow(query, entity_id, tenant_id)
```

### Mistake 4: Not Following File Structure

❌ **Wrong**: Random file locations
```
apps/memory_api/entity_stuff.py  # ❌ What layer is this?
apps/memory_api/my_tests.py      # ❌ Not in tests/ folder
```

✅ **Correct**: Follow PROJECT_STRUCTURE.md
```
apps/memory_api/repositories/entity_repository.py
apps/memory_api/services/entity_service.py
apps/memory_api/api/v1/entities.py
apps/memory_api/tests/repositories/test_entity_repository.py
```

## 📖 Further Reading

- **PROJECT_STRUCTURE.md**: Where to put files (map of project)
- **CONVENTIONS.md**: Why we use these patterns (architectural reasoning)
- **docs/AGENTS_TEST_POLICY.md**: Testing philosophy and guidelines
- **.cursorrules**: Complete rules including Design-First Protocol

## 🤝 Contributing Templates

If you discover a common pattern missing from templates:

1. Document the pattern clearly
2. Include "WHY" comments
3. Add example usage
4. Add test examples
5. Update this README

## ✨ Summary

**Templates = Consistent Code = Less Refactoring = Faster Development**

Use these templates every time you add code. They embody the project's architectural decisions and best practices. Following them means your code will integrate seamlessly and won't need refactoring later.

---

**Last Updated**: 2025-12-04
**Maintained by**: AI Agent Code Quality System
