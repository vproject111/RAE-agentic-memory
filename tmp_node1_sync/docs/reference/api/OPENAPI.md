# OpenAPI Specification

> **Note**: This file previously contained a static OpenAPI specification that became outdated. The OpenAPI specification is now **auto-generated** from code and always up-to-date.

## Access the Live OpenAPI Specification

### JSON Format (Machine-Readable)
**URL**: http://localhost:8000/openapi.json

Use this for:
- Generating API clients in various programming languages
- Importing into API tools (Postman, Insomnia, etc.)
- Integration with testing frameworks
- Building custom tooling

### Interactive Documentation (Human-Readable)

#### Swagger UI
**URL**: http://localhost:8000/docs

Features:
- ✅ Interactive testing interface
- ✅ All 116 endpoints with full documentation
- ✅ Request/response schemas with examples
- ✅ Authentication examples
- ✅ Try endpoints directly from browser

#### ReDoc
**URL**: http://localhost:8000/redoc

Features:
- ✅ Clean, three-panel layout
- ✅ Printable documentation
- ✅ Comprehensive data model documentation
- ✅ Easy navigation

## Current API Version

**Version**: 2.2.0-enterprise

**Total Endpoints**: 116
- 26 core endpoints
- 90 enterprise endpoints

## Why Auto-Generated?

Static OpenAPI files become outdated quickly. By using FastAPI's built-in OpenAPI generation:

1. **Always Accurate**: Documentation updates automatically when code changes
2. **No Maintenance**: No manual editing required
3. **Comprehensive**: Includes all endpoints, models, and validation rules
4. **Standards Compliant**: Follows OpenAPI 3.0+ specification

## Quick Start

1. **Start the API**:
   ```bash
   docker compose up memory-api
   ```

2. **Access Documentation**:
   - Browse to http://localhost:8000/docs
   - Or http://localhost:8000/redoc

3. **Download Specification**:
   ```bash
   curl http://localhost:8000/openapi.json > openapi.json
   ```

## Generate API Clients

Use the OpenAPI specification to generate clients:

```bash
# Download spec
curl http://localhost:8000/openapi.json > openapi.json

# Generate Python client
openapi-generator-cli generate -i openapi.json -g python -o ./client-python

# Generate TypeScript client
openapi-generator-cli generate -i openapi.json -g typescript-axios -o ./client-ts

# Generate Go client
openapi-generator-cli generate -i openapi.json -g go -o ./client-go
```

## Further Reading

- [API Reference](api_reference.md) - Complete API overview
- [API Cookbook](API_COOKBOOK.md) - Task-oriented recipes and examples
- [REST API Examples](rest-api.md) - Curl examples for all operations
- [Python SDK](python-sdk.md) - Official Python client library
