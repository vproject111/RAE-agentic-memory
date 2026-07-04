# RAE - Role i Odpowiedzialności (Roles & Responsibilities)

> **Status dokumentu:** v1.0 - Utworzono w ramach ISO/IEC 42001 compliance
> **Właściciel:** RAE Project Management
> **Ostatnia aktualizacja:** 2025-11-30

## 1. Cel dokumentu

Dokument definiuje role, odpowiedzialności i uprawnienia dla zespołu RAE–agentic-memory zgodnie z wymaganiami ISO/IEC 42001 dla systemów zarządzania AI (AI Management System - AIMS).

**Zgodność z:**
- ISO/IEC 42001: Section 5.3 - Organizational roles, responsibilities and authorities
- ISO/IEC 42001: Section 7.2 - Competence
- GDPR: Article 24 - Responsibility of the controller
- GDPR: Article 39 - Tasks of the data protection officer

---

## 2. Struktura organizacyjna

```
┌────────────────────────────────────────────────────────┐
│                   Executive Sponsor                     │
│          (Decyzje strategiczne, budżet)                 │
└────────────────┬───────────────────────────────────────┘
                 │
┌────────────────┴───────────────────────────────────────┐
│              RAE Product/Technical Owner                │
│    (Kierunek produktu, zgodność ISO 42001)              │
└────────────────┬───────────────────────────────────────┘
                 │
     ┌───────────┼───────────┬─────────────┐
     │           │           │             │
     ▼           ▼           ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐
│  Lead   │ │  Data   │ │Security │ │  ML/AI          │
│Developer│ │ Steward │ │& Compl. │ │  Specialist     │
└─────────┘ └─────────┘ └─────────┘ └─────────────────┘
     │           │           │             │
     ▼           ▼           ▼             ▼
┌─────────────────────────────────────────────────────┐
│          Development Team & Contributors            │
│   (Developers, QA, DevOps, Documentation)           │
└─────────────────────────────────────────────────────┘
```

---

## 3. Definicje ról

### 3.1. Executive Sponsor

**Nazwa:** Executive Sponsor / Program Sponsor
**Liczba osób:** 1 (pojedyncza osoba z leadership)

#### Odpowiedzialności:
- Ostateczna odpowiedzialność za sukces projektu RAE
- Alokacja budżetu i zasobów
- Akceptacja kluczowych decyzji strategicznych
- Sponsorowanie inicjatyw ISO 42001 compliance
- Eskalacja i rozwiązywanie konfliktów na poziomie organizacji

#### Uprawnienia:
- Zatwierdzanie budżetu projektu
- Zatwierdzanie zmian w zakresie projektu
- Decyzje o priorytetach biznesowych

#### Wymagane kompetencje:
- Znajomość strategii AI w organizacji
- Zrozumienie ryzyk związanych z AI
- Doświadczenie w zarządzaniu projektami technologicznymi

#### Metryki sukcesu:
- ROI projektu RAE
- Zgodność z budżetem i harmonogramem
- Zadowolenie stakeholders

---

### 3.2. RAE Product/Technical Owner

**Nazwa:** Owner RAE (Product/Technical Owner)
**Liczba osób:** 1-2 (Product Owner + Tech Lead lub jedna osoba w obu rolach)

#### Odpowiedzialności:

**Product Ownership:**
- Definicja wizji i roadmapy produktu RAE
- Priorytetyzacja backlogu funkcjonalności
- Akceptacja zmian funkcjonalnych (user stories)
- Komunikacja z stakeholders i zespołami produktowymi
- Decyzje o trade-offs (feature vs. technical debt)

**Technical Ownership:**
- Architektura techniczna i decyzje projektowe
- Zgodność z ISO/IEC 42001 i standardami bezpieczeństwa
- Review i akceptacja Architecture Decision Records (ADR)
- Nadzór nad jakością kodu i best practices
- Decyzje o integracji z zewnętrznymi systemami

**ISO 42001 Compliance:**
- Utrzymanie zgodności z normą ISO 42001
- Aktualizacja Risk Register i polityk bezpieczeństwa
- Nadzór nad implementacją mechanizmów kontrolnych
- Przeglądy kwartalne zgodności z normą
- Koordynacja audytów external/internal

#### Uprawnienia:
- Akceptacja/odrzucenie pull requestów o znaczącym wpływie
- Decyzje o architekturze systemu
- Akceptacja zmian w politykach bezpieczeństwa
- Wybór technologii i narzędzi

#### Wymagane kompetencje:
- Dogłębna znajomość architektury RAE
- Znajomość ISO/IEC 42001 i AI governance
- Znajomość GDPR i compliance requirements
- Doświadczenie w zarządzaniu produktem technicznym
- Znajomość Python, FastAPI, PostgreSQL, AI/ML

#### Metryki sukcesu:
- Zgodność z ISO 42001 (audit pass rate)
- Quality metrics (test coverage, code quality)
- Time to market (feature delivery speed)
- System uptime i performance

#### Punkt kontaktowy:
- Email: [owner-email@domain.com]
- Slack/Teams: @rae-owner

---

### 3.3. Lead Developer / Maintainer

**Nazwa:** Lead Developer / Maintainer
**Liczba osób:** 1-2 (główni maintainerzy)

#### Odpowiedzialności:

**Development & Code Quality:**
- Implementacja kluczowych funkcjonalności RAE
- Code review wszystkich pull requestów
- Utrzymanie wysokiej jakości kodu (lint, tests, coverage)
- Refactoring i technical debt management
- Mentoring junior developers

**Technical Implementation:**
- Implementacja mechanizmów zgodnych z ISO 42001:
  - Source trust scoring
  - Data retention and cleanup
  - Audit logging
  - PII scrubbing
  - Policy enforcement
- Integracja z systemami zewnętrznymi
- Performance optimization i monitoring

**Documentation:**
- Utrzymanie dokumentacji technicznej
- Architecture Decision Records (ADR)
- API documentation (Swagger/OpenAPI)
- Contributing guidelines

#### Uprawnienia:
- Merge pull requestów
- Decyzje o implementacji technicznej (w ramach architektury)
- Konfiguracja CI/CD pipeline
- Access do production environment (read/limited write)

#### Wymagane kompetencje:
- Expert-level Python, FastAPI, asyncio
- PostgreSQL, Redis, Qdrant/vector databases
- AI/ML concepts (RAG, embeddings, LLMs)
- Testing (pytest, mocking, integration tests)
- Docker, Kubernetes, CI/CD (GitHub Actions)
- Git best practices, code review

#### Metryki sukcesu:
- Code quality metrics (sonarqube, coverage)
- Pull request turnaround time
- Bug rate i incident response time
- Developer satisfaction (team surveys)

#### Punkt kontaktowy:
- GitHub: @lead-developer-handle
- Email: [lead-dev@domain.com]

---

### 3.4. Data/Knowledge Steward

**Nazwa:** Data/Knowledge Steward (per tenant lub global)
**Liczba osób:** 1+ (zależnie od liczby tenants)

#### Odpowiedzialności:

**Data Governance:**
- Definicja polityk danych dla RAE:
  - Co może trafić do RAE (data classification)
  - Retention policies per tenant
  - Source trust levels i verification policies
- Oznaczanie źródeł wiedzy (source_owner, trust_level)
- Monitoring jakości danych w RAE

**Privacy & Compliance:**
- Nadzór nad prywatnością danych w RAE
- Realizacja żądań GDPR (right to be forgotten)
- Anonimizacja i pseudonimizacja danych
- Data minimization compliance

**Knowledge Quality:**
- Monitoring jakości pamięci (drift detection)
- Weryfikacja źródeł wiedzy (source verification)
- Flagowanie przestarzałych lub błędnych danych
- Curation of semantic nodes i knowledge graph

#### Uprawnienia:
- Ustawienie retention policies per tenant
- Oznaczanie danych jako "high trust" lub "low trust"
- Inicjowanie GDPR deletion requests
- Access do data quality dashboards

#### Wymagane kompetencje:
- Znajomość GDPR i data privacy regulations
- Zrozumienie koncepcji data governance
- Znajomość domeny biznesowej (dla domain-specific tenants)
- Podstawowa znajomość RAE architecture

#### Metryki sukcesu:
- Data quality score (drift metrics)
- GDPR compliance (timely deletion, audit logs)
- Source verification coverage
- User satisfaction z jakości pamięci

#### Punkt kontaktowy:
- Email: [data-steward@domain.com]
- Slack: @data-steward

---

### 3.5. Security & Compliance Contact

**Nazwa:** Security & Compliance Contact / Information Security Officer
**Liczba osób:** 1 (może być shared z organizacją)

#### Odpowiedzialności:

**Security:**
- Nadzór nad bezpieczeństwem RAE:
  - Authentication & authorization (JWT, API keys)
  - Multi-tenant isolation (RLS, tenant_id filtering)
  - Secrets management (env variables, vaults)
  - Network security (TLS, firewall rules)
- Reagowanie na incydenty bezpieczeństwa
- Vulnerability management (security scans, patches)

**Compliance:**
- Współpraca przy audytach ISO 42001
- Przegląd polityk bezpieczeństwa i prywatności
- Monitorowanie zgodności z regulations (GDPR, AI Act)
- Risk assessment i mitigation planning

**Incident Response:**
- Koordynacja incident response dla RAE
- Post-mortem analysis po incydentach
- Communication z affected parties (GDPR breach notification)

#### Uprawnienia:
- Inicjowanie security patches (poza scheduled releases)
- Blocking deployments z security concerns
- Access do audit logs i security monitoring
- Decyzje o eskalacji security incidents

#### Wymagane kompetencje:
- Cybersecurity fundamentals
- GDPR i data privacy regulations
- Incident response procedures
- Risk assessment methodologies
- Znajomość ISO 27001, ISO 42001

#### Metryki sukcesu:
- Security incident rate (liczba i severity)
- Time to patch critical vulnerabilities
- Audit findings (zero critical findings)
- Compliance rate z security policies

#### Punkt kontaktowy:
- Email: [security@domain.com]
- Emergency: [security-emergency@domain.com]
- Slack: @security-team

---

### 3.6. ML/AI Specialist

**Nazwa:** ML/AI Specialist / AI Engineer
**Liczba osób:** 1+ (opcjonalnie, zależnie od advanced use cases)

#### Odpowiedzialności:

**AI/ML Operations:**
- Design i implementation of AI/ML features:
  - Semantic extraction (NER, topic modeling)
  - Entity resolution (clustering, deduplication)
  - Reflection generation (LLM-based meta-learning)
  - Embedding models selection i fine-tuning
- Model evaluation i performance monitoring
- Integration z external LLM providers (OpenAI, Anthropic, etc.)

**AI Quality & Fairness:**
- Monitoring model performance (drift, degradation)
- Bias detection i mitigation
- Explainability i interpretability
- A/B testing dla model improvements

**Research & Innovation:**
- Research on latest RAG, vector search, AI agent techniques
- Prototyping new features (dreaming, wisdom extraction)
- Optimization of inference costs (model selection, caching)

#### Uprawnienia:
- Model selection i hyperparameter tuning
- LLM provider configuration
- Embedding model updates
- Access do ML service i reranker service

#### Wymagane kompetencje:
- Deep learning, NLP, transformer models
- RAG (Retrieval-Augmented Generation)
- Vector databases (Qdrant, pgvector)
- LLM APIs (OpenAI, Anthropic, Gemini)
- Python, PyTorch/TensorFlow
- MLOps (model versioning, monitoring)

#### Metryki sukcesu:
- Model accuracy metrics (precision, recall, F1)
- RAG quality (MRR, NDCG)
- Inference latency (p95, p99)
- Cost per query (LLM API costs)

#### Punkt kontaktowy:
- Email: [ml-specialist@domain.com]
- GitHub: @ml-specialist-handle

---

## 4. Macierz odpowiedzialności (RACI)

RACI: **R**esponsible, **A**ccountable, **C**onsulted, **I**nformed

| Zadanie / Decyzja | Executive Sponsor | RAE Owner | Lead Dev | Data Steward | Security & Compliance | ML Specialist |
|-------------------|-------------------|-----------|----------|--------------|----------------------|---------------|
| **Strategia produktu** | A | R | C | I | I | I |
| **Budżet i zasoby** | A/R | C | I | I | I | I |
| **Architektura techniczna** | I | A | R | C | C | C |
| **Code review & merge** | - | A | R | I | I | I |
| **ISO 42001 compliance** | A | R | C | C | R (security) | I |
| **Risk Register update** | I | A | C | C | R | I |
| **Data retention policies** | I | A | C | R | C | I |
| **GDPR deletion requests** | I | A/C | C | R | R | I |
| **Source trust verification** | I | C | C | R | I | I |
| **Security incident response** | A | C | C | I | R | I |
| **Model selection & tuning** | I | A/C | C | I | I | R |
| **Feature prioritization** | C | A/R | C | C | I | C |
| **Production deployment** | I | A | R | I | C | I |
| **External audit support** | A | R | C | C | R | I |

**Legenda:**
- **R (Responsible)**: Wykonuje zadanie
- **A (Accountable)**: Odpowiedzialny za wynik (tylko jedna osoba!)
- **C (Consulted)**: Konsultowany przed decyzją
- **I (Informed)**: Informowany o decyzji/wyniku

---

## 5. Procedury eskalacji

### 5.1. Eskalacja techniczna

**Poziom 1:** Developer → Lead Developer (standardowe issues)
**Poziom 2:** Lead Developer → RAE Owner (architektural decisions, breaking changes)
**Poziom 3:** RAE Owner → Executive Sponsor (strategic decisions, budget)

### 5.2. Eskalacja bezpieczeństwa

**Poziom 1:** Developer → Security Contact (vulnerability discovered)
**Poziom 2:** Security Contact → RAE Owner + Executive Sponsor (security incident)
**Poziom 3:** Executive Sponsor → Legal/Compliance (data breach, regulatory)

### 5.3. Eskalacja compliance

**Poziom 1:** Team → Data Steward (data quality issues)
**Poziom 2:** Data Steward → RAE Owner (policy violations)
**Poziom 3:** RAE Owner → Executive Sponsor + Legal (audit findings)

---

## 6. Onboarding nowych członków zespołu

### 6.1. Dla Developers

1. **Dzień 1-3:** Setup środowiska, dostęp do repo
2. **Tydzień 1:** Przeczytanie dokumentacji:
   - README.md
   - MEMORY_MODEL.md
   - RAE-ISO_42001.md (ten dokument)
   - RAE-Roles.md
3. **Tydzień 2:** Pierwsze zadanie (good first issue)
4. **Miesiąc 1:** Code review z Lead Developer
5. **Miesiąc 2:** Onboarding complete, pełna autonomia

### 6.2. Dla Data Stewards

1. **Tydzień 1:** Przeszkolenie z RAE architecture (Lead Developer)
2. **Tydzień 1:** Przeszkolenie z GDPR i data governance (Security Contact)
3. **Tydzień 2:** Shadow existing Data Steward (jeśli istnieje)
4. **Miesiąc 1:** Nadzór nad pierwszym tenantem (mentoring)
5. **Miesiąc 2:** Pełna autonomia w zarządzaniu danymi

### 6.3. Dla Security Contact

1. **Tydzień 1:** Deep dive do architektury security RAE (RAE Owner + Lead Dev)
2. **Tydzień 2:** Przegląd Risk Register i polityk bezpieczeństwa
3. **Miesiąc 1:** Audit simulation (tabletop exercise)
4. **Miesiąc 2:** Pełna odpowiedzialność za security

---

## 7. Przeglądy i aktualizacje

### 7.1. Częstotliwość przeglądów

- **Kwartalnie:** Przegląd ról i odpowiedzialności (RAE Owner)
- **Po zmianach organizacyjnych:** Update dokumentu (RAE Owner)
- **Przed audytami:** Weryfikacja aktualności (RAE Owner + Security Contact)

### 7.2. Proces aktualizacji

1. Propozycja zmiany → RAE Owner
2. Konsultacja z affected roles
3. Akceptacja Executive Sponsor (jeśli zmiana strategiczna)
4. Update dokumentu
5. Komunikacja do zespołu
6. Aktualizacja w systemach (np. GitHub teams, access control)

---

## 8. Kontakt i wsparcie

### 8.1. Kanały komunikacji

- **GitHub Issues:** Publiczne dyskusje techniczne
- **Slack/Teams:** Wewnętrzna komunikacja zespołu
- **Email:** Formalne decyzje i komunikacja z external stakeholders
- **Confluence/Notion:** Dokumentacja wewnętrzna i meeting notes

### 8.2. Meeting schedule

- **Daily standup:** 15 min, development team (optional remote)
- **Weekly sync:** 30 min, RAE Owner + Lead Developer + ML Specialist
- **Monthly review:** 1h, All roles (progress, risks, planning)
- **Quarterly ISO 42001 review:** 2h, RAE Owner + Security Contact + Data Steward

---

## 9. Historia zmian

| Data | Wersja | Autor | Zmiana |
|------|--------|-------|--------|
| 2025-11-30 | v1.0 | Claude Code | Utworzenie dokumentu w ramach ISO 42001 compliance |

---

## 10. Załączniki

- [RAE-ISO_42001.md](./RAE-ISO_42001.md) - Dokument zgodności z normą
- [RAE-Risk-Register.md](./RAE-Risk-Register.md) - Rejestr ryzyk
- [SECURITY.md](./SECURITY.md) - Security assessment
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Wytyczne dla contributors
