#!/usr/bin/env python3
"""
RAE Demo Data Seeding Script - Extended Edition

Seeds RAE with comprehensive sample data demonstrating:
- Scenario 1: Project Phoenix (Software Development)
- Scenario 2: City Hall Customer Service (Public Administration)

This script demonstrates RAE's full capabilities including:
- Multi-layer memory architecture (STM, EM, LTM, RM)
- Knowledge graph extraction
- ISO/IEC 42001 compliance features
- Complex decision workflows
- Context provenance tracking

Usage:
    python3 scripts/seed_demo_data.py [--scenario phoenix|city-hall|all]

Requirements:
    pip install httpx
"""

import argparse
import sys
import time
from typing import Any, Dict, List

try:
    import httpx
except ImportError:
    print("ERROR: httpx library not found")
    print("Install it with: pip install httpx")
    sys.exit(1)


# Configuration
RAE_API_URL = "http://localhost:8000"

# ============================================================================
# SCENARIO 1: PROJECT PHOENIX - Software Development
# ============================================================================

PHOENIX_TENANT_ID = "00000000-0000-0000-0000-000000000100"
PHOENIX_PROJECT_ID = "phoenix-project"

PHOENIX_MEMORIES = [
    # === Episodic Memories (Events and interactions) ===
    {
        "content": "Project Phoenix kickoff meeting held on 2024-01-15. Team decided to build a cloud-native microservices platform for real-time data processing. Key stakeholders: Alice Chen (Tech Lead), Bob Martinez (Product Manager), Charlie Kim (DevOps Engineer), Diana Wu (Security Lead).",
        "layer": "em",
        "tags": ["meeting", "kickoff", "planning", "stakeholders"],
        "source": "meeting-notes",
        "importance": 0.95,
    },
    {
        "content": "Alice proposed using Kafka for event streaming and PostgreSQL for persistent storage. The team agreed on this architecture after comparing it with Redis Streams and MongoDB alternatives. Decision rationale: Kafka's proven scalability and PostgreSQL's ACID guarantees.",
        "layer": "em",
        "tags": ["architecture", "decision", "kafka", "postgresql", "database"],
        "source": "technical-discussion",
        "importance": 0.95,
    },
    {
        "content": "Diana raised security concerns about the initial authentication design. The team scheduled a follow-up meeting to review OAuth2 implementation and discuss multi-factor authentication requirements. Security audit required before production launch.",
        "layer": "em",
        "tags": ["security", "authentication", "oauth2", "mfa", "audit"],
        "source": "security-review",
        "importance": 0.9,
    },
    {
        "content": "Bug #PX-42 reported by QA team: Authentication service crashes when handling concurrent requests above 100 RPS. The issue is related to connection pool exhaustion in the database layer. Severity: HIGH. Assigned to: Charlie Kim.",
        "layer": "em",
        "tags": ["bug", "authentication", "performance", "database", "critical"],
        "source": "bug-tracker",
        "importance": 0.9,
    },
    {
        "content": "Charlie implemented horizontal auto-scaling for the authentication service using Kubernetes HPA (Horizontal Pod Autoscaler). Configuration: min=2 pods, max=10 pods, target CPU=70%. The service now handles 500 RPS without issues. Bug #PX-42 resolved and verified.",
        "layer": "em",
        "tags": ["fix", "kubernetes", "performance", "devops", "scaling", "resolved"],
        "source": "git-commit",
        "importance": 0.92,
    },
    {
        "content": "Sprint retrospective insight: The team needs to improve test coverage for edge cases. Multiple bugs were found in production that could have been caught with better integration tests. Action item: Increase coverage to 85% minimum.",
        "layer": "em",
        "tags": ["retrospective", "testing", "quality", "action-item"],
        "source": "team-reflection",
        "importance": 0.75,
    },
    {
        "content": "Product roadmap Q2 2024 finalized: Priority features include OAuth2 integration, multi-tenant support, advanced analytics dashboard, and GraphQL API. Bob estimates 10 weeks for completion with current team size.",
        "layer": "em",
        "tags": ["roadmap", "planning", "features", "q2-2024"],
        "source": "product-planning",
        "importance": 0.85,
    },
    {
        "content": "Alice and Bob discussed the trade-offs between gRPC and REST for inter-service communication. They decided on REST for external APIs and gRPC for internal services to balance developer experience and performance. Decision documented in ADR-007.",
        "layer": "em",
        "tags": ["architecture", "discussion", "grpc", "rest", "adr"],
        "source": "technical-discussion",
        "importance": 0.88,
    },
    {
        "content": "Incident #INC-089: Production outage on 2024-02-20 from 14:30 to 15:45 UTC. Root cause: Redis cache cluster failure causing cascading failures in downstream services. Impact: 15% of users affected. Post-mortem scheduled.",
        "layer": "em",
        "tags": ["incident", "outage", "redis", "production", "postmortem"],
        "source": "incident-report",
        "importance": 0.95,
    },
    {
        "content": "Post-mortem INC-089 findings: Lack of circuit breakers caused cascading failures. Team agreed to implement Resilience4j circuit breakers for all external dependencies. Action owners assigned. Target completion: Sprint 12.",
        "layer": "em",
        "tags": ["postmortem", "circuit-breaker", "resilience", "action-items"],
        "source": "incident-postmortem",
        "importance": 0.93,
    },
    {
        "content": "Charlie deployed circuit breakers for all critical services: database, Redis cache, external payment API, and notification service. Configuration: failure threshold=5, timeout=30s, half-open wait=60s. System resilience significantly improved.",
        "layer": "em",
        "tags": ["devops", "circuit-breaker", "deployment", "resilience"],
        "source": "deployment-notes",
        "importance": 0.9,
    },
    {
        "content": "Customer feedback: Users love the new analytics dashboard but request export functionality to CSV and PDF. Bob added these features to Sprint 13 backlog with priority=HIGH.",
        "layer": "em",
        "tags": ["feedback", "analytics", "feature-request", "export"],
        "source": "customer-feedback",
        "importance": 0.7,
    },
    {
        "content": "Diana completed security audit and found 3 MEDIUM and 1 HIGH severity issues. HIGH issue: Sensitive data logged in application logs. Team implemented log scrubbing and PII detection. All issues resolved before production.",
        "layer": "em",
        "tags": ["security", "audit", "pii", "compliance", "remediation"],
        "source": "security-audit",
        "importance": 0.92,
    },
    # === Short-Term Memory (Working context) ===
    {
        "content": "Currently implementing feature FT-156: Multi-tenant support. Expected completion: end of Sprint 11. Dependencies: database schema migration, API authentication updates, UI tenant switcher.",
        "layer": "stm",
        "tags": ["wip", "multi-tenant", "sprint-11", "feature"],
        "source": "sprint-board",
        "importance": 0.8,
    },
    {
        "content": "Alice is blocked on PR #342 waiting for Bob's review. PR implements GraphQL API endpoints. Bob is in customer meetings all day. Expected review: tomorrow morning.",
        "layer": "stm",
        "tags": ["blocked", "pr-review", "graphql", "current"],
        "source": "team-status",
        "importance": 0.65,
    },
    {
        "content": "Charlie is investigating performance degradation in staging environment. CPU usage increased from 30% to 75% after last deployment. Suspect: new analytics queries causing database load.",
        "layer": "stm",
        "tags": ["investigation", "performance", "staging", "ongoing"],
        "source": "slack-discussion",
        "importance": 0.75,
    },
    # === Long-Term Memory (Structured knowledge) ===
    {
        "content": "The authentication service depends on the user-profile-service for JWT token validation and user metadata retrieval. This dependency was added in release v2.3.0 to centralize user management and improve data consistency.",
        "layer": "ltm",
        "tags": ["architecture", "dependencies", "authentication", "knowledge"],
        "source": "architecture-docs",
        "importance": 0.85,
    },
    {
        "content": "Best practice established: All microservices must implement structured logging with correlation IDs for distributed tracing. Log format: JSON with fields {timestamp, level, service, correlation_id, message, context}. This pattern significantly improved debugging time during incidents.",
        "layer": "ltm",
        "tags": ["best-practice", "logging", "observability", "standard"],
        "source": "engineering-standards",
        "importance": 0.9,
    },
    {
        "content": "Database schema versioning: We use Flyway for schema migrations. Migration files must be sequential and immutable. Rollback migrations required for all schema changes. Location: db/migrations/. Review process: mandatory peer review + DBA approval.",
        "layer": "ltm",
        "tags": ["database", "migrations", "process", "flyway"],
        "source": "database-documentation",
        "importance": 0.82,
    },
    {
        "content": "Deployment process: Feature branches merge to develop → CI runs tests → Deploy to staging → Manual QA → Merge to main → Deploy to production (blue-green). Rollback procedure: revert to previous blue environment. Average deployment time: 30 minutes.",
        "layer": "ltm",
        "tags": ["deployment", "ci-cd", "process", "blue-green"],
        "source": "devops-handbook",
        "importance": 0.88,
    },
    {
        "content": "Error handling strategy: Use custom exception hierarchy with ErrorCode enum. All errors must include: error_code, message, context, timestamp, correlation_id. Client-facing errors must be user-friendly. Internal errors logged with full stack traces.",
        "layer": "ltm",
        "tags": ["error-handling", "exceptions", "coding-standard"],
        "source": "coding-guidelines",
        "importance": 0.8,
    },
    {
        "content": "API versioning policy: Use URL path versioning (/v1/, /v2/). Maintain backward compatibility for at least 2 versions. Deprecation notice period: 6 months. Breaking changes require major version bump. Document all changes in CHANGELOG.md.",
        "layer": "ltm",
        "tags": ["api", "versioning", "policy", "compatibility"],
        "source": "api-guidelines",
        "importance": 0.85,
    },
    {
        "content": "Security requirements: All external APIs must use HTTPS. API keys stored in HashiCorp Vault. Passwords hashed with bcrypt (cost=12). Session timeout: 30 minutes. MFA required for admin accounts. Security headers: CSP, HSTS, X-Frame-Options.",
        "layer": "ltm",
        "tags": ["security", "requirements", "authentication", "standards"],
        "source": "security-policy",
        "importance": 0.95,
    },
    # === Reflective Memory (Meta-insights and patterns) ===
    {
        "content": "Meta-insight: When making architectural decisions, the team consistently prioritizes developer experience over raw performance, unless performance becomes a proven bottleneck. This philosophy has led to faster iteration cycles and higher team morale.",
        "layer": "rm",
        "tags": ["meta-learning", "philosophy", "decision-making", "culture"],
        "source": "pattern-analysis",
        "importance": 0.9,
    },
    {
        "content": "Pattern observed: Technical debt accumulates most rapidly during 'crunch time' before major releases. The team should allocate 20% of each sprint to technical debt reduction to maintain long-term velocity.",
        "layer": "rm",
        "tags": ["technical-debt", "velocity", "process-improvement"],
        "source": "retrospective-synthesis",
        "importance": 0.85,
    },
    {
        "content": "Communication pattern: Most misunderstandings occur at the boundary between product and engineering. Weekly sync meetings between Bob and Alice have reduced miscommunication by ~60%. Regular cross-functional alignment is critical.",
        "layer": "rm",
        "tags": ["communication", "collaboration", "cross-functional"],
        "source": "team-observation",
        "importance": 0.8,
    },
    {
        "content": "Quality insight: The correlation between test coverage and production bugs is strong. Services with >80% coverage have 70% fewer P1 incidents. Investing in testing infrastructure yields measurable ROI.",
        "layer": "rm",
        "tags": ["quality", "testing", "metrics", "roi"],
        "source": "data-analysis",
        "importance": 0.88,
    },
    {
        "content": "Incident pattern: 80% of production incidents occur during or shortly after deployments. Implementing canary deployments and automated rollback would significantly reduce incident frequency and MTTR.",
        "layer": "rm",
        "tags": ["incidents", "deployment", "reliability", "improvement"],
        "source": "incident-analysis",
        "importance": 0.92,
    },
    # === ENRICHMENT MEMORIES (Cross-references and temporal chains) ===
    {
        "content": "Follow-up on Bug #PX-42: Charlie's Kubernetes HPA implementation (Sprint 11) was directly triggered by the authentication service crashes. The fix reduced response time from 250ms to 80ms under load. Bob approved production deployment after seeing staging metrics.",
        "layer": "em",
        "tags": ["follow-up", "performance", "deployment", "cross-reference"],
        "source": "sprint-review",
        "importance": 0.85,
    },
    {
        "content": "Diana's security audit finding about PII in logs (HIGH severity) was discovered during investigation of Bug #PX-42. Alice implemented structured logging with PII scrubbing using regex patterns. This became part of engineering standards document.",
        "layer": "em",
        "tags": ["security", "pii", "logging", "standards", "cross-reference"],
        "source": "security-remediation",
        "importance": 0.9,
    },
    {
        "content": "GraphQL API implementation (PR #342 by Alice) depends on the multi-tenant support feature (FT-156) currently in Sprint 11. Bob prioritized FT-156 to unblock Alice's work. Expected integration: Sprint 12.",
        "layer": "em",
        "tags": [
            "dependencies",
            "graphql",
            "multi-tenant",
            "blocking",
            "sprint-planning",
        ],
        "source": "dependency-tracking",
        "importance": 0.78,
    },
    {
        "content": "Post-INC-089 improvement: Charlie's circuit breaker implementation was tested by Diana's security team before production. They verified that circuit breakers properly handle authentication service failures without exposing sensitive error messages.",
        "layer": "em",
        "tags": ["circuit-breaker", "testing", "security", "collaboration"],
        "source": "integration-testing",
        "importance": 0.82,
    },
    {
        "content": "Alice and Charlie pair-programmed the Redis cache failure handling after INC-089. They implemented automatic failover to in-memory cache when Redis circuit breaker opens. This pattern was documented in ADR-008.",
        "layer": "ltm",
        "tags": ["redis", "failover", "cache", "adr", "collaboration"],
        "source": "architecture-decision",
        "importance": 0.88,
    },
    {
        "content": "Bob's roadmap Q2 2024 OAuth2 feature is blocked waiting for Diana's security audit completion. Diana found 3 MEDIUM issues in OAuth2 provider integration. Target completion delayed from Sprint 12 to Sprint 14.",
        "layer": "em",
        "tags": ["oauth2", "blocked", "security-audit", "delay", "roadmap"],
        "source": "project-status",
        "importance": 0.75,
    },
    {
        "content": "Team velocity analysis: Sprint 10 (30 points) → Sprint 11 (25 points) → Sprint 12 projected (28 points). Velocity drop in Sprint 11 was due to INC-089 incident response taking 40% of team capacity. Circuit breaker implementation should prevent future drops.",
        "layer": "rm",
        "tags": ["velocity", "metrics", "incidents", "capacity-planning"],
        "source": "sprint-analytics",
        "importance": 0.83,
    },
    {
        "content": "Customer feedback (export to CSV/PDF) for analytics dashboard was implemented by Alice in Sprint 13. This feature reuses Bob's existing export library from the reporting module. Integration took 3 days instead of estimated 5 days.",
        "layer": "em",
        "tags": ["feature", "analytics", "export", "reuse", "implementation"],
        "source": "feature-completion",
        "importance": 0.7,
    },
    {
        "content": "The authentication-service → user-profile-service dependency (added in v2.3.0) caused Bug #PX-42. Connection pool exhaustion occurred because user-profile-service was overwhelmed by validation requests. Charlie's HPA solution scaled both services together.",
        "layer": "ltm",
        "tags": ["architecture", "dependencies", "root-cause", "scaling"],
        "source": "root-cause-analysis",
        "importance": 0.9,
    },
    {
        "content": "Cross-team learning: Diana shared PII scrubbing patterns with Bob's product team. Bob incorporated privacy-by-design principles into new feature specs. This collaboration reduced security review time from 2 weeks to 3 days for Sprint 13 features.",
        "layer": "rm",
        "tags": ["collaboration", "security", "privacy", "efficiency", "learning"],
        "source": "team-retrospective",
        "importance": 0.87,
    },
]


# ============================================================================
# SCENARIO 2: CITY HALL CUSTOMER SERVICE - Public Administration
# ============================================================================

CITYHALL_TENANT_ID = "00000000-0000-0000-0000-000000000200"
CITYHALL_PROJECT_ID = "customer-service"

CITYHALL_MEMORIES = [
    # === Episodic Memories (Citizen interactions and events) ===
    {
        "content": "Zgłoszenie #2024-001: Pan Jan Kowalski (PESEL: 12345678901) zgłosił się 2024-01-10 do Działu Ewidencji Ludności w sprawie wymiany dowodu osobistego. Powód: utrata dokumentu. Status: w trakcie realizacji. Termin odbioru: 2024-01-24.",
        "layer": "em",
        "tags": ["dowod-osobisty", "ewidencja", "wymiana", "utrata"],
        "source": "system-crm",
        "importance": 0.7,
    },
    {
        "content": "Zgłoszenie #2024-002: Pani Maria Nowak zgłosiła problem z odbiorem odpadów przy ul. Kwiatowej 15. Data zgłoszenia: 2024-01-11. Kategoria: odpady komunalne. Przekazano do Wydziału Gospodarki Komunalnej. Priorytet: normalny.",
        "layer": "em",
        "tags": ["odpady", "skargi", "gospodarka-komunalna", "interwencja"],
        "source": "system-crm",
        "importance": 0.6,
    },
    {
        "content": "Zgłoszenie #2024-003 (PRIORYTET WYSOKI): Awaria oświetlenia ulicznego przy ulicy Szkolnej - zgłoszenie od 5 mieszkańców. Data: 2024-01-12. Wydział Infrastruktury wysłał ekipę techniczną. Szacowany czas naprawy: 48h. Status: w realizacji.",
        "layer": "em",
        "tags": ["oswietlenie", "awaria", "infrastruktura", "pilne"],
        "source": "system-zgloszeniowy",
        "importance": 0.85,
    },
    {
        "content": "Wniosek #2024-005: Firma 'BudPol sp. z o.o.' złożyła wniosek o pozwolenie na budowę hali magazynowej przy ul. Przemysłowej 44. Data wpływu: 2024-01-15. Wymagana opinia Miejskiego Architekta oraz Wydziału Ochrony Środowiska. Termin rozpatrzenia: 65 dni.",
        "layer": "em",
        "tags": ["pozwolenie-budowlane", "budownictwo", "procedura", "firma"],
        "source": "system-ewidencyjny",
        "importance": 0.8,
    },
    {
        "content": "Sesja Rady Miejskiej 2024-01-18: Uchwalono nowy Regulamin Czystości i Porządku. Nowe stawki opłat za odpady: 28 zł/os/miesiąc (segregacja), 42 zł/os/miesiąc (bez segregacji). Wejście w życie: 2024-03-01. Wymagana kampania informacyjna dla mieszkańców.",
        "layer": "em",
        "tags": ["rada-miejska", "uchwala", "odpady", "regulamin", "stawki"],
        "source": "protokol-rady",
        "importance": 0.95,
    },
    {
        "content": "Szkolenie pracowników 2024-01-22: 'Obsługa klienta w administracji publicznej'. Uczestniczyło 23 pracowników. Omówiono: zasady komunikacji, standardy obsługi, rozwiązywanie konfliktów, procedury odwoławcze. Ocena szkolenia: 4.7/5.0.",
        "layer": "em",
        "tags": ["szkolenie", "obsluga-klienta", "rozwoj", "pracownicy"],
        "source": "system-hr",
        "importance": 0.75,
    },
    {
        "content": "Zgłoszenie #2024-010: Pan Andrzej Wiśniewski złożył skargę na przedłużający się czas rozpatrywania wniosku o zasiłek rodzinny (wniosek #ZR-2023-456 z dnia 2023-12-15). Sprawa przekazana do kierownika Wydziału Pomocy Społecznej. Odpowiedź udzielona w terminie 7 dni.",
        "layer": "em",
        "tags": ["skarga", "zasilek", "pomoc-spoleczna", "opoznienie"],
        "source": "system-skarg",
        "importance": 0.8,
    },
    {
        "content": "Zgłoszenie #2024-015: Zgłoszono dziurę w jezdni przy skrzyżowaniu ul. Długiej i Krótkiej. Zagrożenie bezpieczeństwa. Wydział Dróg i Mostów zlecił naprawę firmie zewnętrznej. Termin realizacji: 5 dni roboczych. Status: zrealizowano 2024-01-29.",
        "layer": "em",
        "tags": ["drogi", "naprawa", "bezpieczenstwo", "infrastruktura"],
        "source": "system-interwencyjny",
        "importance": 0.85,
    },
    {
        "content": "Wniosek o informację publiczną #IP-2024-003: Dziennikarz lokalnej gazety poprosił o dane dotyczące wydatków na remonty dróg w 2023 roku. Podstawa prawna: ustawa o dostępie do informacji publicznej. Odpowiedź udzielona w terminie 14 dni. Przekazano zestawienie z systemu finansowego.",
        "layer": "em",
        "tags": ["informacja-publiczna", "transparentnosc", "finanse", "media"],
        "source": "system-bip",
        "importance": 0.7,
    },
    {
        "content": "Zgłoszenie #2024-020 (DANE OSOBOWE - wymaga zatwierdzenia): Mieszkanka Maria Kowalska wnioskowała o dostęp do swoich danych osobowych przetwarzanych przez urząd (art. 15 RODO). Przygotowano raport zawierający: dane z USC, ewidencji podatkowej, systemu CRM. Zatwierdzenie przez IODO wymagane przed wydaniem.",
        "layer": "em",
        "tags": ["rodo", "dane-osobowe", "dostep", "prywatnosc", "compliance"],
        "source": "system-rodo",
        "importance": 0.95,
    },
    {
        "content": "Incydent #SEC-2024-001: Wykryto próbę nieautoryzowanego dostępu do systemu ewidencji ludności. Data: 2024-02-05 03:14 UTC. Źródło: IP 185.x.x.x (proxy TOR). Atak zablokowany przez firewall. Administrator IT powiadomiony. Raport bezpieczeństwa sporządzony. Nie doszło do wycieku danych.",
        "layer": "em",
        "tags": ["bezpieczenstwo", "incydent", "cyberatak", "ochrona-danych"],
        "source": "system-bezpieczenstwa",
        "importance": 0.95,
    },
    {
        "content": "Spotkanie zespołu 2024-02-08: Omówiono problemy z długimi kolejkami w godzinach szczytu (10:00-12:00). Zaproponowano: system rezerwacji wizyt online, dodatkowe stanowisko obsługi w godzinach 10-12, kampania promująca e-usługi. Decyzja: pilot systemu rezerwacji od marca 2024.",
        "layer": "em",
        "tags": ["kolejki", "usluga", "optymalizacja", "e-uslugi"],
        "source": "notatka-spotkanie",
        "importance": 0.85,
    },
    {
        "content": "Kontrola wewnętrzna 2024-02-12: Audyt procedur w Wydziale Podatków i Opłat. Wynik: pozytywny z uchybieniami. Stwierdzone nieprawidłowości: brak kompletnej dokumentacji w 3 sprawach, przekroczenie terminu rozpatrzenia w 2 sprawach. Zalecenia wdrożone w terminie 30 dni.",
        "layer": "em",
        "tags": ["audyt", "kontrola", "podatki", "procedury", "uchybienia"],
        "source": "raport-kontroli",
        "importance": 0.88,
    },
    {
        "content": "Zgłoszenie #2024-035: Przedsiębiorca Jan Nowak wnioskował o odroczenie płatności podatku od nieruchomości z powodu trudnej sytuacji finansowej firmy. Wymagana analiza sytuacji finansowej + opinia prawnika. Decyzja administracyjna wymaga zatwierdzenia przez Skarbnika Miasta.",
        "layer": "em",
        "tags": ["podatki", "odroczenie", "decyzja-administracyjna", "przedsiebiorca"],
        "source": "system-podatkowy",
        "importance": 0.8,
    },
    # === Short-Term Memory (Current work context) ===
    {
        "content": "Obecnie w realizacji: 47 aktywnych zgłoszeń. Podział: 12 USC, 18 gospodarka komunalna, 8 budownictwo, 9 inne. Priorytetowe: 5 zgłoszeń (awarie, pilne interwencje). Średni czas realizacji: 8 dni. Cel: 7 dni.",
        "layer": "stm",
        "tags": ["statystyki", "biezace", "realizacja", "monitoring"],
        "source": "dashboard-crm",
        "importance": 0.7,
    },
    {
        "content": "W trakcie: Wdrożenie nowego systemu e-Urząd. Faza testów akceptacyjnych. Uczestniczy 10 pracowników z różnych wydziałów. Zgłoszono 15 błędów (12 naprawionych, 3 w trakcie). Planowane uruchomienie: 2024-03-15.",
        "layer": "stm",
        "tags": ["wdrozenie", "e-urzad", "testy", "projekt"],
        "source": "status-projektu",
        "importance": 0.85,
    },
    {
        "content": "Oczekująca decyzja: Wniosek #2024-042 o pozwolenie na wycinkę 3 drzew przy ul. Parkowej. Czeka na opinię Wydziału Ochrony Środowiska. Zgłoszenie obywatelskie sprzeciwu (10 osób). Wymaga rozpatrzenia protestów przed wydaniem decyzji.",
        "layer": "stm",
        "tags": ["oczekujace", "wycinka", "srodowisko", "protest"],
        "source": "sprawy-w-toku",
        "importance": 0.75,
    },
    {
        "content": "Akcja bieżąca: Kampania informacyjna o nowych stawkach za odpady. Harmonogram: ulotki wysłane (100%), spotkania osiedlowe (3/5 zrealizowane), artykuł w gazecie lokalnej (opublikowany), post na Facebook (zasięg: 12,000 osób).",
        "layer": "stm",
        "tags": ["kampania", "komunikacja", "odpady", "informowanie"],
        "source": "plan-komunikacji",
        "importance": 0.7,
    },
    # === Long-Term Memory (Procedures, regulations, knowledge) ===
    {
        "content": "Procedura obsługi zgłoszeń: (1) Rejestracja w systemie CRM + nadanie numeru, (2) Klasyfikacja i określenie priorytetu, (3) Przypisanie do właściwego wydziału, (4) Realizacja przez wydział (termin: 14 dni standardowo), (5) Informacja zwrotna do zgłaszającego, (6) Zamknięcie sprawy. W przypadkach pilnych: termin skrócony do 48h.",
        "layer": "ltm",
        "tags": ["procedura", "zgloszenia", "crm", "proces"],
        "source": "instrukcja-obsluga",
        "importance": 0.9,
    },
    {
        "content": "Przepisy RODO w urzędzie: Administrator Danych Osobowych: Burmistrz. IOD: Jan Kowalski. Podstawy prawne przetwarzania: art. 6 ust. 1 lit. c (obowiązek prawny), lit. e (zadanie publiczne). Okres przechowywania: wg kategorii archiwalnej (kat. A - archiwum państwowe, kat. B - 50 lat, kat. BE - 5 lat).",
        "layer": "ltm",
        "tags": ["rodo", "dane-osobowe", "przepisy", "archiwizacja"],
        "source": "dokumentacja-rodo",
        "importance": 0.95,
    },
    {
        "content": "Standardy obsługi mieszkańców: Czas oczekiwania w kolejce: max 15 min. Czas obsługi pojedynczego klienta: 8-10 min. Wymóg uprzejmości i profesjonalizmu. W przypadku niemożności załatwienia sprawy na miejscu: przekazanie do właściwego wydziału z poinformowaniem o terminach.",
        "layer": "ltm",
        "tags": ["standardy", "obsluga", "jakość", "procedury"],
        "source": "regulamin-obsluga",
        "importance": 0.82,
    },
    {
        "content": "Procedura odwoławcza: Strona niezadowolona z decyzji może wnieść odwołanie w terminie 14 dni od doręczenia. Odwołanie kierowane do organu wyższego stopnia (Samorządowe Kolegium Odwoławcze). Urząd ma 7 dni na ustosunkowanie się i przekazanie akt. SKO rozpatruje w terminie 60 dni.",
        "layer": "ltm",
        "tags": ["odwolanie", "procedura", "prawo", "terminy"],
        "source": "kodeks-postepowania-administracyjnego",
        "importance": 0.9,
    },
    {
        "content": "Struktura organizacyjna urzędu: 8 wydziałów merytorycznych - (1) USC, (2) Ewidencja Ludności, (3) Budownictwo, (4) Gospodarka Komunalna, (5) Podatki i Opłaty, (6) Pomoc Społeczna, (7) Ochrona Środowiska, (8) Infrastruktura. Łącznie: 87 pracowników. Koordynator obsługi klienta: Pani Anna Lewandowska.",
        "layer": "ltm",
        "tags": ["struktura", "organizacja", "wydzialy", "pracownicy"],
        "source": "regulamin-organizacyjny",
        "importance": 0.75,
    },
    {
        "content": "Polityka bezpieczeństwa IT: Dostęp do systemów tylko z autoryzowanych stanowisk. Hasła: min 12 znaków, wymiana co 90 dni, uwierzytelnianie dwuskładnikowe dla administratorów. Backup danych: co 24h, przechowywanie 30 dni. Monitoring: SIEM, logi przechowywane 2 lata.",
        "layer": "ltm",
        "tags": ["bezpieczenstwo", "it", "polityka", "backup"],
        "source": "polityka-bezpieczenstwa",
        "importance": 0.92,
    },
    {
        "content": "Procedura zgłaszania incydentów bezpieczeństwa: (1) Natychmiastowe powiadomienie administratora IT, (2) Dokumentacja incydentu (czas, rodzaj, skutki), (3) Zabezpieczenie dowodów (logi, screenshoty), (4) Analiza i reakcja (max 4h), (5) Raport do IOD i UODO jeśli dotyczy danych osobowych (72h), (6) Wdrożenie środków naprawczych.",
        "layer": "ltm",
        "tags": ["incydenty", "bezpieczenstwo", "procedura", "rodo"],
        "source": "instrukcja-incydenty",
        "importance": 0.95,
    },
    {
        "content": "Zakres danych w systemie CRM: dane kontaktowe mieszkańców (imię, nazwisko, adres, telefon, email), historia zgłoszeń, przypisane sprawy, status realizacji, komunikacja z urzędem, preferencje komunikacji. Dane chronione: poziom 2 (dane osobowe). Dostęp: autoryzowani pracownicy obsługi.",
        "layer": "ltm",
        "tags": ["crm", "dane", "zakres", "dostep"],
        "source": "dokumentacja-systemu",
        "importance": 0.85,
    },
    # === ENRICHMENT MEMORIES (Cross-references and temporal chains) ===
    {
        "content": "Kontynuacja zgłoszenia #2024-001 (dziura na ul. Kwiatowej): Po naprawie awaryjnej przez Wydział Gospodarki Komunalnej mieszkanka Kowalska złożyła pozytywną opinię. Czas realizacji: 3 dni (standard: 7 dni). Pani Nowak otrzymała podziękowanie od Burmistrza za sprawną realizację.",
        "layer": "em",
        "tags": [
            "follow-up",
            "zgłoszenie",
            "realizacja",
            "pozytywna-opinia",
            "cross-reference",
        ],
        "source": "system-obslugi",
        "importance": 0.82,
    },
    {
        "content": "Zgłoszenie #2024-015 rozwiązało problem zgłoszony w #2024-003: Mieszkaniec Wiśniewski zgłaszał brak koszy w parku. Po implementacji decyzji z wniosku #2024-003 (zamontowanie 12 dodatkowych koszy) Wiśniewski potwierdził poprawę sytuacji. Koordynacja: Wydział Gospodarki Komunalnej + Wydział Infrastruktury.",
        "layer": "em",
        "tags": [
            "cross-reference",
            "rozwiązanie",
            "park",
            "infrastruktura",
            "koordynacja",
        ],
        "source": "tracking-zgloszenia",
        "importance": 0.85,
    },
    {
        "content": "Incydent bezpieczeństwa z 15.02.2024 (próba nieautoryzowanego dostępu) był bezpośrednią przyczyną wdrożenia dodatkowych kontroli bezpieczeństwa opisanych w zgłoszeniu #2024-007. IOD Jan Kowalski zrekomendował wzmocnienie monitoringu 24/7 oraz automatyczne blokowanie podejrzanych IP. Implementacja: marzec 2024.",
        "layer": "em",
        "tags": ["bezpieczenstwo", "incydent", "reakcja", "iod", "cross-reference"],
        "source": "raport-iod",
        "importance": 0.92,
    },
    {
        "content": "Hierarchia realizacji zgłoszenia #2024-002: (1) Przyjęcie przez Panią Nowak → (2) Przekazanie do Burmistrza → (3) Delegacja do Wydziału Budownictwa (Pan Zieliński) → (4) Konsultacja z IOD (Jan Kowalski) → (5) Decyzja odmowna z uzasadnieniem RODO. Czas procedowania: 14 dni roboczych.",
        "layer": "em",
        "tags": ["hierarchia", "workflow", "budownictwo", "rodo", "odmowa"],
        "source": "tracking-zgloszenia",
        "importance": 0.88,
    },
    {
        "content": "Zgłoszenie #2024-005 (podatki lokalne) ujawniło problem w systemie E-Urząd: obywatele nie mogli wydrukować zaświadczenia PIT. Wydział Podatków zgłosił to do firmy zewnętrznej (kontakt z 20.02.2024). Fix wdrożono 25.02.2024. 47 mieszkańców otrzymało przeprosiny + kompensatę opłaty za doręczenie.",
        "layer": "em",
        "tags": ["e-urzad", "awaria", "podatki", "kompensata", "cross-reference"],
        "source": "incident-tracking",
        "importance": 0.87,
    },
    {
        "content": "Współpraca międzywydziałowa: Zgłoszenie #2024-003 wymagało koordynacji 3 wydziałów - Gospodarka Komunalna (zakup koszy), Infrastruktura (montaż), Ochrona Środowiska (lokalizacja zgodna z planem zagospodarowania). Anna Lewandowska (koordynator) prowadziła spotkania koordynacyjne co 2 dni.",
        "layer": "em",
        "tags": ["współpraca", "koordynacja", "wydziały", "park", "realizacja"],
        "source": "protokol-spotkan",
        "importance": 0.84,
    },
    {
        "content": "Wniosek RODO mieszkańca Nowaka (#2024-002 dostęp do danych) ujawnił brak procedury archiwizacji. IOD Jan Kowalski wdrożył nową procedurę: dane przetwarzane w celach archiwalnych przechowywane w oddzielnym repozytorium z kontrolą dostępu. Szkolenie dla wszystkich wydziałów: marzec 2024.",
        "layer": "ltm",
        "tags": ["rodo", "archiwizacja", "procedura", "iod", "usprawnienie"],
        "source": "procedura-archiwizacji",
        "importance": 0.9,
    },
    {
        "content": "Zgłoszenie #2024-007 (pozwolenie na budowę) było zależne od decyzji środowiskowej z Wydziału Ochrony Środowiska. Proces zatrzymany na 21 dni z powodu brakującej dokumentacji. Po uzupełnieniu pozwolenie wydane w 7 dni. Lesson learned: automatyczne sprawdzenie kompletności dokumentacji przy przyjęciu wniosku.",
        "layer": "em",
        "tags": [
            "pozwolenie",
            "zależności",
            "dokumentacja",
            "usprawnienie",
            "lesson-learned",
        ],
        "source": "analiza-przypadku",
        "importance": 0.86,
    },
    {
        "content": "Citizen feedback loop: 85% mieszkańców, którzy otrzymali automatyczne SMS o statusie sprawy (wdrożone po zgłoszeniu #2024-001), oceniło obsługę jako 'doskonałą' lub 'bardzo dobrą'. Przed wdrożeniem: 62%. Burmistrz zdecydował o rozszerzeniu SMS na wszystkie wydziały. Budget: 12,000 PLN/rok.",
        "layer": "rm",
        "tags": ["feedback", "sms", "satysfakcja", "usprawnienie", "roi"],
        "source": "ankieta-satysfakcji",
        "importance": 0.89,
    },
    {
        "content": "Audit finding remediation chain: Audyt zewnętrzny (styczeń 2024) wykrył brak szyfrowania backupów (HIGH severity). IOD Jan Kowalski → Administrator IT (implementacja szyfrowania AES-256) → Re-audit (marzec 2024) → Finding zamknięty. Podobne zalecenie zastosowano prewencyjnie do wszystkich systemów miejskich.",
        "layer": "em",
        "tags": ["audit", "remediation", "szyfrowanie", "bezpieczenstwo", "follow-up"],
        "source": "audit-remediation",
        "importance": 0.93,
    },
    # === Reflective Memory (Meta-insights and improvements) ===
    {
        "content": "Wzorzec obserwowany: 70% zgłoszeń do Wydziału Gospodarki Komunalnej dotyczy odpadów. Z tego 60% to pytania o harmonogram wywozu. Rozwiązanie: automatyczny SMS reminder przed wywozem + aplikacja mobilna z harmonogramem. Implementacja zredukowałaby obciążenie call center o ~40%.",
        "layer": "rm",
        "tags": ["analiza", "optymalizacja", "odpady", "usprawnienie"],
        "source": "analiza-zgloszeniowa",
        "importance": 0.88,
    },
    {
        "content": "Refleksja jakościowa: Skargi mieszkańców najczęściej dotyczą nie merytorycznego rozstrzygnięcia, ale długiego czasu oczekiwania i braku informacji zwrotnej. Wdrożenie automatycznych notyfikacji SMS/email o statusie sprawy zmniejszyło liczbę skarg o 45%.",
        "layer": "rm",
        "tags": ["jakosc", "komunikacja", "skargi", "usprawnienie"],
        "source": "analiza-satysfakcji",
        "importance": 0.9,
    },
    {
        "content": "Korelacja zaobserwowana: Wydziały, które przeszły szkolenie z obsługi klienta, mają o 30% wyższą ocenę satysfakcji od mieszkańców. Inwestycja w szkolenia soft skills daje mierzalny ROI w postaci lepszej jakości usług i mniejszej liczby skarg.",
        "layer": "rm",
        "tags": ["szkolenia", "roi", "satysfakcja", "rozwoj"],
        "source": "badanie-efektywnosci",
        "importance": 0.85,
    },
    {
        "content": "Sezonowość zgłoszeń: Piki w styczniu (podatki), czerwcu (pozwolenia budowlane), wrześniu (sprawy szkolne). Planowanie urlopów pracowników powinno uwzględniać te okresy. Wzmocnienie zespołu w okresach szczytowych o pracowników tymczasowych zwiększyło efektywność o 25%.",
        "layer": "rm",
        "tags": ["sezonowosc", "planowanie", "zasoby", "efektywnosc"],
        "source": "analiza-obciazenia",
        "importance": 0.82,
    },
    {
        "content": "Lekcja z incydentów bezpieczeństwa: 80% prób nieautoryzowanego dostępu występuje poza godzinami pracy (18:00-08:00). Wdrożenie systemu wykrywania anomalii + monitoring 24/7 jest konieczny. Automatyczne blokowanie podejrzanych IP zmniejszyło liczbę prób ataków o 90%.",
        "layer": "rm",
        "tags": ["bezpieczenstwo", "monitoring", "prewencja", "lekcja"],
        "source": "raport-bezpieczenstwa",
        "importance": 0.93,
    },
    {
        "content": "Wzorzec cyfryzacji: Wdrożenie e-usług zmniejsza obciążenie tradycyjnych kanałów, ale wymaga wsparcia technicznego dla starszych mieszkańców. Optymalne rozwiązanie: e-usługi + punkty wsparcia dla osób starszych + infolinia. Takie podejście zwiększyło adopcję e-usług z 15% do 42%.",
        "layer": "rm",
        "tags": ["cyfryzacja", "e-uslugi", "wsparcie", "adopcja"],
        "source": "ewaluacja-e-urzad",
        "importance": 0.87,
    },
    {
        "content": "Meta-obserwacja: Najskuteczniejsze usprawnienia procesów pochodzą od sugestii pracowników pierwszej linii obsługi. Wdrożenie systemu zgłaszania pomysłów + nagrody za implementowane usprawnienia zwiększyło zaangażowanie o 60% i wygenerowało 23 wdrożone usprawnienia rocznie.",
        "layer": "rm",
        "tags": ["kultura", "innowacje", "zaangazowanie", "usprawnienia"],
        "source": "program-innowacyjny",
        "importance": 0.85,
    },
]


def check_rae_health() -> bool:
    """Check if RAE API is healthy and reachable."""
    try:
        response = httpx.get(f"{RAE_API_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def create_memory(
    client: httpx.Client, memory_data: Dict[str, Any], tenant_id: str, project_id: str
) -> bool:
    """Create a single memory in RAE."""
    try:
        payload = {"project": project_id, **memory_data}
        headers = {"X-Tenant-Id": tenant_id, "X-User-Id": "admin"}

        response = client.post(
            f"{RAE_API_URL}/v1/memory/store",
            json=payload,
            headers=headers,
            timeout=10.0,
        )

        if response.status_code in [200, 201]:
            return True
        else:
            print(f"   WARNING: Failed (status {response.status_code})")
            if (
                response.status_code != 404
            ):  # Don't spam with full error for missing endpoints
                print(f"   Response: {response.text[:150]}")
            return False

    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return False


def seed_scenario(
    client: httpx.Client,
    scenario_name: str,
    tenant_id: str,
    project_id: str,
    memories: List[Dict[str, Any]],
) -> tuple[int, int]:
    """Seed a specific scenario and return (success_count, failed_count)."""

    print(f"\n{'=' * 70}")
    print(f"  SCENARIO: {scenario_name}")
    print(f"  Tenant: {tenant_id}")
    print(f"  Project: {project_id}")
    print(f"  Memories: {len(memories)}")
    print(f"{'=' * 70}\n")

    success_count = 0
    failed_count = 0

    for i, memory in enumerate(memories, 1):
        layer_emoji = {
            "em": "📝",  # Episodic
            "stm": "⚡",  # Short-Term
            "ltm": "📚",  # Long-Term
            "rm": "💡",  # Reflective
        }.get(memory["layer"], "📄")

        # Truncate content for display
        content_preview = memory["content"][:80].replace("\n", " ")

        print(
            f"{layer_emoji} [{i:2d}/{len(memories):2d}] {memory['layer'].upper():3s}: {content_preview}..."
        )

        if create_memory(client, memory, tenant_id, project_id):
            success_count += 1
            print("   ✅ Created")
        else:
            failed_count += 1
            print("   ❌ Failed")

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    return success_count, failed_count


def print_usage_tips(scenarios: List[str]):
    """Print usage tips for the seeded data."""

    print("\n" + "=" * 70)
    print("  Demo Data Seeded Successfully! 🎉")
    print("=" * 70)

    if "phoenix" in scenarios:
        print("\n📦 PROJECT PHOENIX - Software Development Scenario")
        print(f"   Tenant: {PHOENIX_TENANT_ID}")
        print(f"   Project: {PHOENIX_PROJECT_ID}")
        print("   Try: Search for 'authentication bug' or 'circuit breaker'")

    if "city-hall" in scenarios:
        print("\n🏛️  CITY HALL - Public Administration Scenario")
        print(f"   Tenant: {CITYHALL_TENANT_ID}")
        print(f"   Project: {CITYHALL_PROJECT_ID}")
        print("   Try: Search for 'odpady' or 'bezpieczeństwo' or 'RODO'")

    print("\n💡 Explore the data:")
    print("   1. Dashboard: http://localhost:8501")
    print("   2. API Docs: http://localhost:8000/docs")
    print("   3. Query API: POST http://localhost:8000/v1/memory/query")
    print("   4. Graph extraction: http://localhost:8000/v1/graph/extract")
    print("   5. ISO/IEC 42001: http://localhost:8000/v1/compliance/...")
    print()


def main():
    """Main execution function."""

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Seed RAE with demo data (Phoenix and/or City Hall scenarios)"
    )
    parser.add_argument(
        "--scenario",
        choices=["phoenix", "city-hall", "all"],
        default="all",
        help="Which scenario to seed (default: all)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  RAE Demo Data Seeding Script - Extended Edition")
    print("=" * 70 + "\n")

    # Step 1: Check RAE health
    print(f"[1/3] Checking RAE API health at {RAE_API_URL}...")
    if not check_rae_health():
        print("❌ ERROR: RAE API is not reachable or unhealthy\n")
        print("Please ensure RAE is running:")
        print("  docker compose ps")
        print("  docker compose logs rae-api")
        print("\nOr run: ./scripts/quickstart.sh")
        sys.exit(1)

    print("✅ RAE API is healthy\n")

    # Step 2: Seed selected scenarios
    print("[2/3] Seeding demo data...")

    total_success = 0
    total_failed = 0
    scenarios_seeded = []

    with httpx.Client() as client:
        if args.scenario in ["phoenix", "all"]:
            success, failed = seed_scenario(
                client,
                "Project Phoenix (Software Development)",
                PHOENIX_TENANT_ID,
                PHOENIX_PROJECT_ID,
                PHOENIX_MEMORIES,
            )
            total_success += success
            total_failed += failed
            scenarios_seeded.append("phoenix")

        if args.scenario in ["city-hall", "all"]:
            success, failed = seed_scenario(
                client,
                "City Hall Customer Service (Public Administration)",
                CITYHALL_TENANT_ID,
                CITYHALL_PROJECT_ID,
                CITYHALL_MEMORIES,
            )
            total_success += success
            total_failed += failed
            scenarios_seeded.append("city-hall")

    # Step 3: Summary
    print("\n[3/3] Summary:")
    print(f"      ✅ Successfully created: {total_success} memories")

    if total_failed > 0:
        print(f"      ❌ Failed: {total_failed} memories")

    # Step 4: Usage tips
    print_usage_tips(scenarios_seeded)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
