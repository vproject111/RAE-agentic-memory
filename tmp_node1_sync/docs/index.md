# RAE Documentation

Welcome to the RAE (Reflective Agentic Environment) documentation.

## 📚 Documentation Structure

### [Reference](./reference/README.md)
**Official production documentation**

Complete technical reference for RAE:
- Architecture & Design Patterns
- API & SDK Documentation
- Memory Model & GraphRAG
- Security & ISO 42001 Compliance
- LLM Integration & Cost Guard
- Deployment & Operations
- Testing & Evaluation

👉 **Start here** for production use and integration.

### [Guides](./guides/README.md)
**User guides and tutorials**

Practical guides for different use cases:
- RAE Lite (cost-optimized)
- Developer guides
- Getting started tutorials
- Best practices

👉 **Start here** if you're new to RAE.

### [AI Specs](./ai-specs/README.md)
**Specifications for AI agents**

Materials for AI coding assistants (Claude, Gemini, Jules):
- Prompt templates
- Test generation specs
- Agent workflows
- IDE integration plans

👉 For AI assistant developers and LLM integration.

### [Project Design](./project-design/README.md)
**Design documents and research**

Working notes, experiments, and research:
- Feniks integration
- Architecture evolution
- Enterprise roadmap
- Research ideas and experiments

👉 For contributors and researchers interested in RAE's development.

## 🚀 Quick Links

**New Users**: [Getting Started Guide](./guides/developers/getting_started.md)
**Developers**: [Python SDK Reference](./reference/api/SDK_PYTHON_REFERENCE.md)
**DevOps**: [Kubernetes Deployment](./reference/deployment/DEPLOY_K8S_HELM.md)
**Security**: [ISO 42001 Compliance](./reference/iso-security/RAE-ISO_42001.md)
**AI Integration**: [MCP/IDE Integration](./reference/integrations/MCP_IDE_INTEGRATION.md)

## 📖 Key Documentation

### Architecture
- [Memory Model](./reference/memory/MEMORY_MODEL.md) - 4-layer memory architecture
- [GraphRAG](./reference/memory/GRAPHRAG_IMPLEMENTATION.md) - Knowledge graph RAG
- [Reflection Engine V2](./reference/architecture/REFLECTION_ENGINE_V2_IMPLEMENTATION.md) - Learning from execution
- [Multi-Tenancy](./reference/architecture/MULTI_TENANCY.md) - Enterprise isolation

### Development
- [Python SDK](./reference/api/SDK_PYTHON_REFERENCE.md) - SDK documentation
- [CLI Reference](./reference/api/CLI_REFERENCE.md) - Command-line tools
- [Dev Tools](./reference/testing/DEV_TOOLS_AND_SCRIPTS.md) - Developer utilities
- [Testing](./reference/testing/TEST_COVERAGE_MAP.md) - Test coverage

### Operations
- [Deployment Guide](./reference/deployment/DEPLOY_K8S_HELM.md) - Kubernetes/Helm
- [LLM Profiles](./reference/llm/LLM_PROFILES_AND_COST_GUARD.md) - LLM configuration
- [Cost Guard](./reference/llm/cost-controller.md) - Cost management
- [Observability](./reference/deployment/observability.md) - Monitoring

## 🏗️ Documentation Philosophy

RAE documentation is organized by **purpose and audience**:

1. **Reference** = Production documentation for users and integrators
2. **Guides** = Tutorials and practical how-to guides
3. **AI Specs** = Materials for AI coding assistants
4. **Project Design** = Internal design docs and research

This structure keeps production documentation clean while preserving valuable research and design artifacts.

## 🤝 Contributing

See [Contributing Guide](./guides/developers/contributing/) for documentation contribution guidelines.

## 📄 Other Resources

- [Code of Conduct](./CODE_OF_CONDUCT.md)
- [Version Matrix](./reference/VERSION_MATRIX.md)
- [Main README](../README.md)
