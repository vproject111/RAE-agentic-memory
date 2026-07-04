# RAE Reference Documentation

Official documentation for RAE (Reflective Agentic Environment).

## 📁 Documentation Structure

### Architecture
- [Background Workers](./architecture/BACKGROUND_WORKERS.md) - Decay, Summarization, Dreaming cycles
- [Reflection Engine V2](./architecture/REFLECTION_ENGINE_V2_IMPLEMENTATION.md) - Actor-Evaluator-Reflector pattern
- [Rules Engine](./architecture/RULES_ENGINE.md) - Event-driven automation
- [Multi-Tenancy](./architecture/MULTI_TENANCY.md) - Multi-tenant architecture and isolation
- [Repository Pattern](./architecture/repository-pattern.md)
- [Concepts](./concepts/) - Core concepts and design patterns
- [Services](./services/) - Service layer documentation

### API & SDK
- [Python SDK Reference](./api/SDK_PYTHON_REFERENCE.md) - Complete Python SDK documentation
- [CLI Reference](./api/CLI_REFERENCE.md) - Command-line interface
- [REST API](./api/rest-api.md) - REST API endpoints
- [API Reference](./api/api_reference.md) - General API documentation
- [OpenAPI](./api/OPENAPI.md) - OpenAPI specification

### Memory
- [Memory Model](./memory/MEMORY_MODEL.md) - 4-layer memory architecture
- [GraphRAG Implementation](./memory/GRAPHRAG_IMPLEMENTATION.md) - Knowledge graph RAG
- [GraphRAG Guide](./memory/graphrag_guide.md) - GraphRAG usage guide

### ISO/IEC 42001 & Security
- [ISO 42001 Compliance](./iso-security/RAE-ISO_42001.md) - AI Management System compliance
- [ISO 42001 Implementation Map](./iso-security/ISO42001_IMPLEMENTATION_MAP.md) - Code-to-requirements mapping
- [Security](./iso-security/SECURITY.md) - Security guidelines
- [Risk Register](./iso-security/RAE-Risk-Register.md) - Risk assessment
- [Roles & Responsibilities](./iso-security/RAE-Roles.md) - RACI matrix

### LLM Integration
- [LLM Profiles & Cost Guard](./llm/LLM_PROFILES_AND_COST_GUARD.md) - Multi-provider LLM support
- [LLM Backends](./llm/llm_backends.md) - Supported LLM providers
- [Multi-Model Integration](./llm/RAE–Multi-Model_LLM-Integration-Guide.md)
- [Cost Controller](./llm/cost-controller.md) - Cost tracking and budgets

### Deployment
- [Kubernetes & Helm](./deployment/DEPLOY_K8S_HELM.md) - K8s deployment guide
- [Hosting Options](./deployment/hosting_options.md) - Deployment options
- [RLS Deployment](./deployment/RLS-Deployment-Guide.md) - Row-Level Security setup
- [Configuration](./deployment/configuration.md) - Configuration guide
- [Observability](./deployment/observability.md) - Monitoring and logging

### Testing & Evaluation
- [Test Coverage Map](./testing/TEST_COVERAGE_MAP.md) - Feature-to-test mapping
- [Testing Status](./testing/TESTING_STATUS.md) - Current test status
- [Dev Tools & Scripts](./testing/DEV_TOOLS_AND_SCRIPTS.md) - Developer tools
- [Evaluation Framework](./testing/EVAL_FRAMEWORK.md) - Benchmarking framework

### Integrations
- [Integrations Overview](./integrations/INTEGRATIONS_OVERVIEW.md) - All integrations
- [MCP/IDE Integration](./integrations/MCP_IDE_INTEGRATION.md) - Model Context Protocol
- [Context Watcher](./integrations/context_watcher_daemon.md) - Automatic context tracking
- [Feniks Integration](./integrations/FENIKS_INTEGRATION_BLUEPRINT.md)

### Other
- [Version Matrix](./VERSION_MATRIX.md) - Version compatibility matrix

## 🎯 Quick Links

**Getting Started**: See [guides/developers/](../guides/developers/)
**Architecture Overview**: See [architecture/](./architecture/)
**API Documentation**: See [api/](./api/)
**Security & Compliance**: See [iso-security/](./iso-security/)

## 📚 Related Documentation

- [AI Specs](../ai-specs/README.md) - Specifications for AI agents
- [Project Design](../project-design/README.md) - Design documents and research
- [Guides](../guides/README.md) - User guides and tutorials
