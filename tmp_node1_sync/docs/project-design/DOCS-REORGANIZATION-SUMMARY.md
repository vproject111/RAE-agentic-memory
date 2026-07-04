# Podsumowanie Planu Reorganizacji Dokumentacji

**Data:** 2025-12-03
**Status:** ✅ Plan gotowy do realizacji

## 🎯 Zidentyfikowane problemy

### 1. **Puste katalogi** (5 katalogów bez zawartości):
- `docs/api/`
- `docs/architecture/`
- `docs/deployment/`
- `docs/integrations/`
- `docs/contributing/`

### 2. **Duplikacja struktury**:
- `docs/security/` ↔️ `docs/reference/iso-security/`
- Dokumentacja API rozproszona w wielu miejscach

### 3. **Prace rozwojowe w głównym katalogu**:
- `docs/opentelemetry/` - powinno być w `project-design/active/`
- `docs/security/` - opis funkcjonalności do certyfikacji

### 4. **Brak struktury dla auto-generowanych dokumentów**:
- `STATUS.md`, `TESTING_STATUS.md`, `CHANGELOG.md` rozrzucone
- Brak dedykowanego katalogu dla raportów CI/CD
- Brak automatyzacji aktualizacji

### 5. **Brak implementacji 4-warstwowej architektury zgodności**:
Zgodnie z `RAE-security-Architektura-4-warstwy-zgodnosci.md`:
- **Warstwa 1:** ISO 42001 (fundament)
- **Warstwa 2:** Mapowanie (ISO → NIST/HIPAA/FedRAMP/GDPR/AI Act)
- **Warstwa 3:** Compliance Modules (policy packs)
- **Warstwa 4:** Enforcement (guardrails, controllers)

## 🏗️ Proponowane rozwiązanie

### Nowa struktura katalogów:

```
docs/
├── .auto-generated/         🆕 Auto-generowane dokumenty
│   ├── status/             (STATUS.md, TESTING_STATUS.md, CI_STATUS.md)
│   ├── reports/            (CHANGELOG.md, CODE_METRICS.md)
│   ├── api/                (openapi.json, api_endpoints.md)
│   └── compliance/         (iso42001-status.md, nist-coverage.md)
│
├── guides/                  📖 Podręczniki użytkownika
│   ├── getting-started/
│   ├── user/
│   ├── admin/
│   └── developer/
│
├── reference/              📚 Dokumentacja referencyjna
│   ├── api/
│   ├── architecture/
│   ├── deployment/
│   └── configuration/
│
├── compliance/             🆕 4-warstwowa architektura zgodności
│   ├── layer-1-foundation/  (ISO 42001)
│   ├── layer-2-mapping/     (ISO→NIST/HIPAA/etc.)
│   ├── layer-3-modules/     (Policy packs)
│   ├── layer-4-enforcement/ (Guardrails)
│   └── certifications/      (Audit reports)
│
├── project-design/         🔧 Plany i prace rozwojowe
│   ├── active/             (opentelemetry/ ← PRZENIESIONE)
│   ├── completed/
│   ├── planned/
│   └── research/
│
├── operations/             🆕 Dokumenty operacyjne
│   ├── runbooks/
│   ├── monitoring/
│   └── maintenance/
│
└── contributing/           👥 Dla kontrybutorów
    ├── CONTRIBUTING.md
    ├── BRANCHING.md
    └── TESTING.md
```

## 🤖 Dokumenty do automatycznej aktualizacji

### Częstotliwość aktualizacji:

| Dokument | Źródło | Częstotliwość |
|----------|--------|---------------|
| **STATUS.md** | Git + pytest + coverage | Po każdym push |
| **TESTING_STATUS.md** | pytest output | Po każdym push |
| **CI_STATUS.md** | GitHub Actions API | Po każdym workflow |
| **CHANGELOG.md** | Git commits | Daily (2 AM) |
| **CODE_METRICS.md** | radon + lizard | Weekly |
| **openapi.json** | FastAPI export | Po zmianach API |
| **api_endpoints.md** | OpenAPI parser | Po zmianach API |
| **iso42001-status.md** | pytest -m iso42001 | Monthly |
| **nist-coverage.md** | pytest -m nist | Monthly |
| **audit-summary.md** | DB access logs | Monthly |

### Automatyzacja:

✅ **GitHub Actions workflow:** `.github/workflows/docs-auto-update.yml`
- Job 1: Update status docs (każdy push)
- Job 2: Update reports (daily)
- Job 3: Update API docs (na zmiany)
- Job 4: Update compliance (monthly)

✅ **Pre-commit hooks:** Regeneracja OpenAPI spec
✅ **Scheduled cron:** Compliance reports (1. dzień miesiąca)

## 🛡️ Implementacja 4-warstwowej zgodności

### Warstwa 1: Foundation (ISO 42001)
```
compliance/layer-1-foundation/iso-42001/
├── implementation-map.md
├── risk-register.md
├── roles-responsibilities.md
└── audit-trail.md
```

### Warstwa 2: Mapping (ISO → Other Standards)
```
compliance/layer-2-mapping/
├── iso42001-to-nist.md
├── iso42001-to-hipaa.md
├── iso42001-to-fedramp.md
├── iso42001-to-gdpr.md
└── iso42001-to-ai-act.md
```

### Warstwa 3: Compliance Modules (Policy Packs)
```
compliance/layer-3-modules/
├── hipaa/
│   ├── policy-pack.yaml
│   ├── implementation.md
│   └── tests/
├── nist-ai-rmf/
├── fedramp/
├── gdpr/
├── ai-act/
└── iso-27001/
```

### Warstwa 4: Enforcement (Policy Engine)
```
compliance/layer-4-enforcement/
├── guardrails/
├── cost-controllers/
└── risk-controllers/
```

## 📋 Plan realizacji (12 dni)

### Faza 1: Przygotowanie (1 dzień)
- [x] Analiza obecnej struktury ✅
- [x] Stworzenie planu reorganizacji ✅
- [x] Przygotowanie struktury `.auto-generated/` ✅
- [ ] Stworzenie README.md w nowych katalogach
- [ ] Przygotowanie skryptów migracji

### Faza 2: Migracja plików (2 dni)
- [ ] Przeniesienie auto-generowanych do `.auto-generated/`
- [ ] Przeniesienie `docs/opentelemetry/` → `project-design/active/`
- [ ] Reorganizacja `docs/security/` według 4 warstw
- [ ] Uporządkowanie `guides/` i `reference/`
- [ ] Usunięcie pustych katalogów

### Faza 3: Automatyzacja (3 dni)
- [x] Stworzenie example workflow ✅
- [ ] Implementacja skryptów generujących:
  - `scripts/generate_status.py`
  - `scripts/generate_testing_status.py`
  - `scripts/generate_ci_status.py`
  - `scripts/generate_code_metrics.py`
  - `scripts/export_openapi.py`
  - `scripts/generate_api_endpoints.py`
  - `scripts/generate_compliance_report.py`
  - `scripts/generate_audit_summary.py`
- [ ] Testowanie pipeline
- [ ] Aktywacja workflow

### Faza 4: Dokumentacja compliance (4 dni)
- [ ] Utworzenie struktury 4-warstwowej
- [ ] Warstwa 1: ISO 42001 (przeniesienie z `reference/iso-security/`)
- [ ] Warstwa 2: Mapowania (nowe dokumenty)
- [ ] Warstwa 3: Policy packs (templates):
  - HIPAA module
  - NIST AI RMF module
  - FedRAMP module
  - GDPR module
  - AI Act module
  - ISO 27001 module
- [ ] Warstwa 4: Policy engine (dokumentacja)

### Faza 5: Aktualizacja linków (1 dzień)
- [ ] Aktualizacja linków w dokumentach
- [ ] Aktualizacja README.md głównego
- [ ] Aktualizacja CI/CD
- [ ] Weryfikacja wszystkich linków

### Faza 6: Czyszczenie (1 dzień)
- [ ] Usunięcie duplikatów
- [ ] Archiwizacja starych dokumentów
- [ ] Ostateczna weryfikacja

## 📁 Pliki utworzone

1. ✅ `docs/project-design/DOCS-REORGANIZATION-PLAN.md` (szczegółowy plan)
2. ✅ `docs/.auto-generated/README.md` (instrukcje dla auto-docs)
3. ✅ `.github/workflows/docs-auto-update.yml.example` (przykład workflow)
4. ✅ `docs/project-design/DOCS-REORGANIZATION-SUMMARY.md` (to podsumowanie)

## 🎯 Korzyści

### Dla użytkowników:
- ✅ Łatwe znajdowanie dokumentacji (jasna struktura)
- ✅ Zawsze aktualne statusy i metryki (auto-update)
- ✅ Przejrzysta struktura compliance (4 warstwy)

### Dla developerów:
- ✅ Automatyczna aktualizacja dokumentów (mniej manual work)
- ✅ Łatwe dodawanie policy packs (modułowa struktura)
- ✅ Jasna struktura dla prac rozwojowych (active/completed/planned)

### Dla compliance/certyfikacji:
- ✅ Modułowa struktura zgodności (4 warstwy)
- ✅ Łatwe mapowanie do różnych norm
- ✅ Automatyczne raporty zgodności
- ✅ Transparentność dla audytorów (open source policy packs)

### Dla projektu:
- ✅ Profesjonalny wygląd dokumentacji
- ✅ Łatwiejsza konserwacja
- ✅ Gotowość do certyfikacji
- ✅ Przygotowanie na skalowanie (multi-jurisdictional)

## 🚀 Następne kroki

1. **Review planu** przez maintainera
2. **Akceptacja** struktury i zakresu
3. **Rozpoczęcie Fazy 1** (przygotowanie)
4. **Wykonanie migracji** zgodnie z planem
5. **Testowanie** auto-update pipeline
6. **Merge** do main po weryfikacji

---

**Status:** ✅ READY FOR EXECUTION
**Oszacowany czas:** 12 dni roboczych
**Priorytet:** HIGH
**Zależności:** Brak (można zacząć natychmiast)
**Autor:** Claude Code (autonomous agent)
