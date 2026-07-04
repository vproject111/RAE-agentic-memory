# Template Usage Examples

> **Purpose**: Working examples showing how to use `.ai-templates/` to create production-ready code.

## 📚 What's Here

This directory contains complete, working examples of code created using the templates in `.ai-templates/`.

Each example demonstrates:
- ✅ How to adapt templates for your use case
- ✅ Complete 3-layer architecture (Repository → Service → API)
- ✅ Comprehensive tests for all layers
- ✅ Best practices and patterns
- ✅ Security (tenant isolation)
- ✅ Error handling and logging

## 🎯 Examples

### 1. User Notifications System
**Directory**: `user_notifications/`

**What it demonstrates**:
- Complete CRUD operations
- Pydantic models with validation
- Repository pattern with RLS (Row Level Security)
- Service layer with business logic
- API endpoints with proper HTTP codes
- Comprehensive test suite

**Files**:
```
user_notifications/
├── README.md                    # Detailed walkthrough
├── models.py                    # Pydantic models
├── notification_repository.py   # Data access layer
├── notification_service.py      # Business logic layer
├── notification_routes.py       # API endpoints
└── tests/
    ├── test_notification_repository.py
    ├── test_notification_service.py
    └── test_notification_routes.py
```

**Use case**: When you need to add a new entity with full CRUD operations.

## 🚀 How to Use These Examples

### Step 1: Study the Example
```bash
cd examples/template-usage/user_notifications
cat README.md  # Read the detailed walkthrough
```

### Step 2: Compare with Templates
```bash
# Open template and example side by side
cat ../../.ai-templates/repository_template.py
cat notification_repository.py

# See what was changed and why
```

### Step 3: Adapt for Your Use Case
1. Copy the template structure
2. Replace entity names (e.g., "Notification" → "Order")
3. Customize business logic
4. Add your specific validations
5. Run tests to verify

### Step 4: Follow the Patterns
- Keep the same structure
- Use the same patterns (DI, error handling, logging)
- Add similar tests
- Follow naming conventions

## 📝 Template Mapping

| Template | Example File | What Changed |
|----------|--------------|--------------|
| `repository_template.py` | `notification_repository.py` | Added notification-specific queries |
| `service_template.py` | `notification_service.py` | Added notification business logic |
| `route_template.py` | `notification_routes.py` | Added notification endpoints |
| `test_template.py` | `tests/test_*.py` | Added notification-specific test cases |

## 🎓 Learning Path

### For New Agents
1. **Read** `user_notifications/README.md` - Detailed walkthrough
2. **Study** each file and compare with templates
3. **Understand** WHY patterns are used (see comments)
4. **Try** creating your own entity using the same patterns

### For Experienced Agents
1. **Quick reference** - See how patterns are applied
2. **Copy** the structure for new features
3. **Customize** for your specific needs
4. **Improve** - Suggest template enhancements

## 🔍 Key Patterns Demonstrated

### 1. Repository Pattern
- ✅ Single responsibility (one entity)
- ✅ Parameterized queries (SQL injection prevention)
- ✅ Row Level Security (tenant_id in all queries)
- ✅ Error handling and logging
- ✅ Returns dicts, not models

### 2. Service Pattern
- ✅ Dependency Injection
- ✅ Business logic validation
- ✅ Pydantic models for I/O
- ✅ Private methods for internal logic
- ✅ Comprehensive error handling

### 3. API Pattern
- ✅ FastAPI with proper dependencies
- ✅ Pydantic request/response models
- ✅ Proper HTTP status codes
- ✅ OpenAPI documentation
- ✅ RBAC with tenant verification

### 4. Testing Pattern
- ✅ AAA (Arrange-Act-Assert)
- ✅ Descriptive test names
- ✅ Proper mocking
- ✅ Tests as contracts, not snapshots
- ✅ Coverage for all scenarios

## 🛠️ Running the Examples

### Install Dependencies
```bash
# From project root
make install
```

### Run Example Tests
```bash
# Test repository layer
pytest --no-cov examples/template-usage/user_notifications/tests/test_notification_repository.py -v

# Test service layer
pytest --no-cov examples/template-usage/user_notifications/tests/test_notification_service.py -v

# Test API layer
pytest --no-cov examples/template-usage/user_notifications/tests/test_notification_routes.py -v

# All example tests
pytest --no-cov examples/template-usage/user_notifications/tests/ -v
```

### Run Linting
```bash
black examples/template-usage/
isort examples/template-usage/
ruff check examples/template-usage/
```

## 📚 Related Documentation

- **Templates**: `.ai-templates/` - Base templates
- **Structure**: `PROJECT_STRUCTURE.md` - Where to put files
- **Conventions**: `CONVENTIONS.md` - Why we use patterns
- **Testing**: `docs/AGENTS_TEST_POLICY.md` - Testing philosophy
- **Onboarding**: `ONBOARDING_GUIDE.md` - Complete guide

## 💡 Tips

### Do's ✅
- Start with templates, customize minimally
- Keep the structure and patterns intact
- Add comments explaining WHY (not WHAT)
- Write tests first or alongside code
- Use structured logging
- Include tenant_id in all queries

### Don'ts ❌
- Don't rewrite from scratch
- Don't skip layers
- Don't mix business logic into wrong layers
- Don't skip tests
- Don't ignore security (tenant_id)
- Don't use relative imports

## 🎯 Next Steps

1. **Study** the user_notifications example
2. **Practice** by creating your own entity
3. **Compare** your code with the example
4. **Refine** using feedback
5. **Contribute** - improve examples and templates!

## 🤝 Contributing Examples

Want to add more examples? Great!

**Good candidate examples**:
- Different types of entities (orders, invoices, settings)
- Complex business logic scenarios
- Integration with external services
- Background tasks with Celery
- WebSocket endpoints

**How to contribute**:
1. Create new directory under `examples/template-usage/`
2. Use templates from `.ai-templates/`
3. Add comprehensive README.md
4. Include all 3 layers + tests
5. Follow existing example structure
6. Add to this README

---

**Last Updated**: 2025-12-04
**Maintained by**: AI Agent Code Quality System

**Remember**: These examples exist to accelerate your development. Use them! 🚀
