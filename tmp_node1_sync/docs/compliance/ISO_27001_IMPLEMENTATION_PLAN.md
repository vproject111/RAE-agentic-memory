# ISO/IEC 27001:2022 Implementation Plan for RAE-Core

## 1. Executive Summary & Scope
This document outlines the technical strategy to prepare **RAE-Core** (Reflective Agentic Memory Engine) for ISO 27001 certification.
While ISO 27001 certifies the *Information Security Management System (ISMS)* of an organization, the **RAE-Core software must adhere to specific controls** to be compliant.

**Certification Scope:**
- **Primary Asset:** RAE-Core (Python codebase, logic, memory processing).
- **Supporting Assets:** Distributed Compute Nodes (Node1/KUBUS), Vector Database (Qdrant), SQL Database (Postgres).
- **Excluded:** External LLM Provider internals (OpenAI/Anthropic are treated as Suppliers).

## 2. Gap Analysis & Risk Assessment (Clause 6)

### Key Risks for RAE-Core
1.  **Memory Leakage (Confidentiality):** User memories (personally identifiable information - PII) leaking into logs or unauthorized tenants.
2.  **Model Hallucination/Injection (Integrity):** Prompt injection attacks altering long-term memory.
3.  **Distributed Node Compromise (Availability/Confidentiality):** Node1 (KUBUS) is a physical machine connected via Tailscale. Physical theft or compromise could expose cached vectors.
4.  **Dependency Vulnerabilities:** Supply chain attacks via Python packages.

## 3. Technical Implementation Roadmap (Annex A Controls)

### Phase 1: Secure Development Lifecycle (SDLC)
*Focus: A.8.25 (Secure Development Lifecycle), A.8.28 (Secure Coding)*

- [ ] **Static Application Security Testing (SAST):**
    - Formalize `bandit` and `safety` checks in CI/CD (currently in Makefile but needs enforcement).
    - **Action:** Update `Makefile` to fail builds on High/Critical security issues.
- [ ] **Dependency Management (SBOM):**
    - Generate Software Bill of Materials.
    - **Action:** Implement tools to scan `requirements.txt` for known CVEs daily.
- [ ] **Branch Protection & Code Review:**
    - Enforce "Four Eyes Principle" (Peer Review) for all PRs merging to `main` or `develop`.
    - **Action:** Configure Git hooks to prevent direct commits to protected branches.

### Phase 2: Access Control & Identity
*Focus: A.5.15 (Access Control), A.9.2 (User Access Provisioning)*

- [ ] **Strict Tenant Isolation:**
    - Verify `tenant_id` propagation in *every* SQL query and Vector search.
    - **Action:** Create a regression test suite specifically for Cross-Tenant Data Leakage (Negative Testing).
- [ ] **Secrets Management:**
    - **Critical:** Eliminate all hardcoded IP addresses and Keys (partially done).
    - **Action:** Move to a `.env` injection system or a Secrets Manager (Vault) for production.
- [ ] **Node Authentication:**
    - Secure communication between Control Node and Node1.
    - **Action:** Implement mTLS or strict API Key rotation for Node Agents.

### Phase 3: Cryptography & Data Protection
*Focus: A.8.24 (Cryptography), A.8.12 (Data Leakage Prevention)*

- [ ] **Encryption at Rest:**
    - Ensure Postgres and Qdrant volumes are encrypted (LUKS/Docker Secrets).
- [ ] **Encryption in Transit:**
    - Enforce TLS 1.3 for all HTTP traffic (even inside Tailscale is recommended for Defense in Depth).
- [ ] **PII Sanitization in Logs:**
    - RAE processes raw thoughts.
    - **Action:** Configure `structlog` to mask PII in `INFO` level logs. Debug logs must be ephemeral.

### Phase 4: Operations Security
*Focus: A.12 (Operations Security), A.8.15 (Logging)*

- [ ] **Audit Trails:**
    - Log *who* accessed *which* memory and *when*.
    - **Action:** Implement an immutable `audit_log` table in Postgres for all Memory Retrieval events.
- [ ] **Backup & Recovery:**
    - Automated backups of the Knowledge Graph.
    - **Action:** Create scripts for encrypted off-site backups (3-2-1 rule).

## 4. Implementation Checklist for Developer

| Task ID | Control | Description | Priority |
| :--- | :--- | :--- | :--- |
| **SEC-01** | A.8.28 | Configure `pre-commit` hooks for `bandit` (Security Linter). | **High** |
| **SEC-02** | A.5.15 | Audit `rae_core` SQL queries for missing `tenant_id` filters. | **Critical** |
| **SEC-03** | A.8.12 | Implement PII masking in `apps/memory_api/config.py` logging. | **Medium** |
| **SEC-04** | A.8.24 | Verify API Key handling (remove defaults in code). | **High** |
| **SEC-05** | A.8.26 | Create a `SECURITY.md` with Vulnerability Disclosure Policy. | **Low** |
| **SEC-06** | A.5.19 | Ensure Node1 (KUBUS) disk is encrypted. | **High** |

## 5. Documentation Requirements
To pass the audit, the following artifacts must be generated from the code:
1.  **Architecture Diagram:** Updated data flow diagram (Control Node <-> Node1).
2.  **Asset Inventory:** List of all databases, services, and APIs.
3.  **Risk Treatment Plan:** How we addressed the risks identified in Section 2.

---
*Drafted: 2026-01-03 for RAE-Core Certification Readiness.*
