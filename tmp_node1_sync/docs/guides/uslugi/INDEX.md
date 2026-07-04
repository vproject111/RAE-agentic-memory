# Portal Dokumentacji dla Usług Profesjonalnych

**Witamy w dokumentacji RAE dla doradców, prawników, audytorów i księgowych!** ⚖️

Ten portal został stworzony specjalnie dla firm świadczących usługi profesjonalne, w których **izolacja wiedzy klientów jest absolutnie krytyczna**. RAE zapewnia pełną separację danych między klientami, ścieżki audytu i zgodność z wymogami prawno-regulacyjnymi dla kancelarii prawnych, firm audytorskich i biur rachunkowych.

## 🔐 Dlaczego RAE dla Usług Profesjonalnych?

**Kluczowe Zalety:**

✅ **Absolutna Izolacja Klientów** - Zero ryzyka przecieków między sprawami
✅ **Pełne Ścieżki Audytu** - Śledzenie każdej operacji dla compliance
✅ **Zgodność z RODO/GDPR** - Wbudowane mechanizmy ochrony danych osobowych
✅ **Tajemnica Zawodowa** - Separacja na poziomie architektury systemu
✅ **Kontrola Dostępu** - Role i uprawnienia per projekt/klient
✅ **Retention Policies** - Automatyczne zarządzanie cyklem życia danych

## 🚀 Szybki Start (10 minut)

**Nowy w RAE?** Zacznij tutaj:

1. **[Wielodostępność dla Usług Profesjonalnych](#-wielodostępność-dla-usług-profesjonalnych)**
   - Model separacji: jeden tenant = jedna kancelaria/firma
   - Projekty = poszczególni klienci/sprawy
   - Automatyczna izolacja danych
   - Brak możliwości cross-contamination

2. **[Izolacja Wiedzy Klientów](#-izolacja-wiedzy-klientów)**
   - Każdy klient/sprawa w osobnym projekcie
   - Dane nigdy nie mieszają się między sprawami
   - Kontrola dostępu per projekt
   - Audit trail dla każdej operacji

3. **[Zgodność Prawno-Regulacyjna](#-zgodność-prawno-regulacyjna)**
   - RODO/GDPR compliance
   - Tajemnica zawodowa (attorney-client privilege)
   - Retencja dokumentów zgodna z prawem
   - Eksport dla celów compliance

## 📚 Dokumentacja dla Różnych Ról

### Dla Prawników (Kancelarie Prawne)

| Przypadek Użycia | Opis | Dokumentacja |
|-----------------|------|--------------|
| **Baza Wiedzy Prawnej** | Precedensy, orzecznictwo, wzory pism | [Knowledge Management](#baza-wiedzy-prawnej) |
| **Separacja Spraw** | Każda sprawa = osobny projekt | [Project Isolation](#izolacja-projektów-spraw) |
| **Wyszukiwanie Kontekstowe** | Znajdź podobne sprawy, precedensy | [Hybrid Search](../../reference/architecture/hybrid-search.md) |
| **Dokumentacja Sprawy** | Automatyczne notatki, timeline wydarzeń | [Case Documentation](#dokumentacja-spraw) |
| **Conflict of Interest Check** | Wykrywanie konfliktów interesów | [Conflict Detection](#wykrywanie-konfliktów-interesów) |

### Dla Audytorów (Firmy Audytorskie)

| Przypadek Użycia | Opis | Dokumentacja |
|-----------------|------|--------------|
| **Baza Wiedzy Audytorskiej** | Standardy, procedury, checklisty | [Audit Knowledge Base](#baza-wiedzy-audytorskiej) |
| **Separacja Klientów** | Każdy klient = osobny projekt | [Client Isolation](#izolacja-klientów) |
| **Dokumentacja Ustaleń** | Notatki z wywiadów, findings | [Audit Trail](#ścieżki-audytu) |
| **Analiza Ryzyka** | Historia ryzyk, incident management | [Risk Analysis](#analiza-ryzyka) |
| **Raportowanie** | Generowanie raportów audytowych | [Reporting](#raportowanie) |

### Dla Księgowych (Biura Rachunkowe)

| Przypadek Użycia | Opis | Dokumentacja |
|-----------------|------|--------------|
| **Baza Wiedzy Księgowej** | Interpretacje podatkowe, procedury | [Accounting Knowledge](#baza-wiedzy-księgowej) |
| **Separacja Klientów** | Każda firma-klient = projekt | [Client Separation](#separacja-klientów) |
| **Dokumentacja Operacji** | Historia transakcji, uzgodnień | [Transaction Log](#log-transakcji) |
| **Zgodność Podatkowa** | Śledzenie zmian w prawie, deadlines | [Tax Compliance](#zgodność-podatkowa) |
| **Archiwizacja** | Retencja dokumentów zgodna z KSR/UoR | [Archiving](#archiwizacja-dokumentów) |

## 🔒 Wielodostępność dla Usług Profesjonalnych

### Model Architektury

**RAE dla usług profesjonalnych używa 2-poziomowej izolacji:**

```
┌──────────────────────────────────────────────────────────┐
│              TENANT = Kancelaria/Firma                    │
│  (np. "kancelaria-kowalski", "audit-abc", "biuro-xs")   │
└──────────────────────────────────────────────────────────┘
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
┌─────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│ PROJECT A  │    │  PROJECT B  │    │  PROJECT C  │
│            │    │             │    │             │
│ Klient XYZ │    │ Sprawa 123  │    │ Firma ABC   │
│            │    │             │    │             │
│ 100% Izolacja   │ 100% Izolacja    │ 100% Izolacja
└────────────┘    └─────────────┘    └─────────────┘

❌ PROJECT A nie widzi danych PROJECT B
❌ PROJECT B nie widzi danych PROJECT C
✅ Każdy projekt = oddzielna "silos" danych
```

### Tworzenie Struktury dla Kancelarii

**Krok 1: Rejestracja Kancelarii (Tenant)**

```python
# Jednokrotna rejestracja kancelarii
POST /api/v1/admin/tenants

{
  "name": "Kancelaria Kowalski & Wspólnicy",
  "tenant_id": "kancelaria-kowalski",
  "settings": {
    "industry": "legal",
    "data_retention_years": 10,     # Wymóg prawny dla dokumentów
    "enable_audit": true,            # Obowiązkowe dla compliance
    "enable_conflict_check": true,   # Wykrywanie konfliktów interesów
    "gdpr_contact": "rodo@kancelaria-kowalski.pl"
  }
}
```

**Krok 2: Tworzenie Projektu dla Każdej Sprawy/Klienta**

```python
# Nowa sprawa = nowy projekt
POST /api/v1/projects

{
  "tenant_id": "kancelaria-kowalski",
  "project_id": "sprawa-2025-001",
  "name": "Sprawa: XYZ vs. ABC - odszkodowanie",
  "metadata": {
    "client_name": "Jan Kowalski (powód)",
    "case_type": "civil_litigation",
    "start_date": "2025-01-10",
    "status": "active",
    "assigned_lawyers": ["jan.nowak@kancelaria.pl"],
    "confidentiality": "attorney_client_privilege"
  },
  "isolation_level": "strict"  # Maksymalna izolacja
}
```

**Krok 3: Praca w Ramach Projektu**

```python
# Wszystkie operacje automatycznie izolowane do projektu
POST /api/v1/memories

{
  "tenant_id": "kancelaria-kowalski",
  "project_id": "sprawa-2025-001",  # WYMAGANE - bez tego API zwróci błąd
  "content": "Spotkanie z klientem - ustalenia co do strategii procesowej",
  "metadata": {
    "type": "meeting_notes",
    "date": "2025-01-15",
    "participants": ["Jan Kowalski (klient)", "Jan Nowak (adwokat)"],
    "confidential": true
  }
}

# Ta pamięć:
# ✅ JEST widoczna w projekcie "sprawa-2025-001"
# ❌ NIE JEST widoczna w innych projektach
# ❌ NIE MOŻE być dostępna dla innych tenantów
```

## 🛡️ Izolacja Wiedzy Klientów

### Gwarancje Bezpieczeństwa

**RAE zapewnia 3-poziomową ochronę:**

#### Poziom 1: Izolacja Bazodanowa

```sql
-- ✅ POPRAWNIE - Każde zapytanie zawiera tenant_id I project_id
SELECT * FROM memories
WHERE tenant_id = 'kancelaria-kowalski'
  AND project_id = 'sprawa-2025-001'
  AND id = '12345'

-- ❌ NIEMOŻLIWE - Zapytania bez project_id są odrzucane
SELECT * FROM memories WHERE tenant_id = 'kancelaria-kowalski'
-- Błąd: "project_id is required for professional services"
```

#### Poziom 2: Izolacja API

```python
# Próba dostępu do pamięci z innego projektu
GET /api/v1/memories/mem-xyz-999
X-Tenant-ID: kancelaria-kowalski
X-Project-ID: sprawa-2025-001

# Jeśli mem-xyz-999 należy do projektu "sprawa-2025-002":
# Response: 404 Not Found (nie 403 - zero information leakage)
```

#### Poziom 3: Izolacja Wyszukiwania

```python
# Wyszukiwanie ZAWSZE ograniczone do projektu
POST /api/v1/memories/search

{
  "tenant_id": "kancelaria-kowalski",
  "project_id": "sprawa-2025-001",
  "query": "odszkodowanie precedens",
  "limit": 10
}

# Wyniki:
# ✅ Tylko z projektu "sprawa-2025-001"
# ❌ NIGDY z innych projektów (nawet podobne sprawy)
```

### Izolacja Projektów (Spraw)

**Każdy projekt jest całkowicie odizolowany:**

| Zasób | Izolacja | Przykład |
|-------|----------|----------|
| **Memories** | Per projekt | Notatki ze spotkań, dokumenty |
| **Searches** | Per projekt | Wyszukiwanie w materiałach sprawy |
| **Reflections** | Per projekt | Automatyczne podsumowania |
| **Graph Entities** | Per projekt | Osoby, firmy, zdarzenia |
| **Embeddings** | Per projekt | Wektory semantyczne |
| **Audit Logs** | Per projekt | Historia operacji |

**Przykład dla Kancelarii Prawnej:**

```
Tenant: kancelaria-kowalski

├─ Projekt: sprawa-2025-001 (XYZ vs ABC)
│  ├─ Memories: 245 dokumentów
│  ├─ Entities: 12 osób, 3 firmy
│  └─ Audit Log: 1,234 operacje
│
├─ Projekt: sprawa-2025-002 (DEF vs GHI)
│  ├─ Memories: 189 dokumentów
│  ├─ Entities: 8 osób, 2 firmy
│  └─ Audit Log: 897 operacje
│
└─ Projekt: baza-wiedzy (Wspólna wiedza kancelarii)
   ├─ Memories: 5,678 precedensów
   ├─ Entities: Sądy, przepisy
   └─ Audit Log: 23,456 operacje

❌ sprawa-2025-001 NIE widzi danych sprawa-2025-002
✅ Obydwie sprawy MOGĄ czytać z "baza-wiedzy" (jeśli udzielono dostępu)
```

## 📋 Zgodność Prawno-Regulacyjna

### RODO/GDPR dla Usług Profesjonalnych

**RAE implementuje wszystkie wymagania RODO:**

#### 1. Minimalizacja Danych

```yaml
# Automatyczne usuwanie po okresie retencji
data_retention:
  legal_documents: 10y      # Dokumentacja spraw - 10 lat
  meeting_notes: 5y         # Notatki ze spotkań - 5 lat
  email_correspondence: 3y  # Korespondencja - 3 lata
  temp_files: 30d          # Pliki tymczasowe - 30 dni
  auto_delete: true        # Automatyczne kasowanie
```

#### 2. Prawo do Usunięcia (Right to be Forgotten)

```python
# Usunięcie wszystkich danych osoby po zakończeniu sprawy
DELETE /api/v1/tenants/{tenant_id}/projects/{project_id}/data-subjects/{subject_id}

# Przykład:
DELETE /api/v1/tenants/kancelaria-kowalski/projects/sprawa-2025-001/data-subjects/jan-kowalski

# Usuwa:
# - Wszystkie memories zawierające dane osoby
# - Wszystkie embeddingi
# - Wszystkie encje grafu
# - Zachowuje audit log (wymóg prawny) z zanonimizowanymi danymi
```

#### 3. Prawo do Przenoszenia Danych

```python
# Eksport wszystkich danych klienta
GET /api/v1/tenants/{tenant_id}/projects/{project_id}/export

# Zwraca JSON z:
# - Wszystkimi memories
# - Timeline wydarzeń
# - Dokumentami
# - Metadanymi
# Format zgodny z RODO Art. 20
```

#### 4. Szyfrowanie i Zabezpieczenia

| Warstwa | Mechanizm | Standard |
|---------|-----------|----------|
| **Dysk** | Szyfrowanie bazy danych | AES-256-GCM |
| **Transmisja** | TLS | TLS 1.3 |
| **Pola wrażliwe** | Tokenizacja | Format-preserving |
| **Backupy** | Zaszyfrowane archiwa | AES-256 + GPG |
| **Klucze** | HSM / KMS | FIPS 140-2 Level 2 |

### Tajemnica Zawodowa (Attorney-Client Privilege)

**RAE chroni tajemnicę zawodową na poziomie architektury:**

```python
# Flaga "privileged" dla komunikacji chronionej
POST /api/v1/memories

{
  "tenant_id": "kancelaria-kowalski",
  "project_id": "sprawa-2025-001",
  "content": "Rozmowa z klientem o strategii obrony",
  "metadata": {
    "privileged": true,              # CHRONIONE tajemnicą zawodową
    "privilege_type": "attorney_client",
    "participants": ["client", "attorney"],
    "confidentiality_level": "highest"
  }
}

# Skutki ustawienia "privileged": true:
# ✅ Dodatkowe szyfrowanie
# ✅ Specjalne audit logi
# ✅ Brak możliwości eksportu bez autoryzacji partnera
# ✅ Automatyczne retention policies
```

### Retencja Dokumentów (Zgodna z Prawem)

**Wymogi retencji w Polsce:**

| Typ Dokumentu | Okres | Podstawa Prawna |
|---------------|-------|-----------------|
| **Dokumentacja spraw sądowych** | 10 lat | Ustawa o adwokaturze |
| **Dokumentacja audytowa** | 5 lat | Ustawa o rachunkowości |
| **Dokumenty księgowe** | 5 lat | Ordynacja podatkowa |
| **Faktury VAT** | 5 lat | Ustawa o VAT |
| **Dokumentacja pracownicza** | 10/50 lat | Kodeks pracy |

**Konfiguracja RAE:**

```yaml
# .env
RETENTION_POLICY_ENABLED=true

# Per industry defaults
RETENTION_LEGAL_DOCS=3650      # 10 lat
RETENTION_AUDIT_DOCS=1825      # 5 lat
RETENTION_ACCOUNTING=1825      # 5 lat
RETENTION_TAX_DOCS=1825        # 5 lat

# Automatyczne archiwizowanie
ENABLE_AUTO_ARCHIVING=true
ARCHIVE_TO_COLD_STORAGE=true   # S3 Glacier, Azure Archive

# Powiadomienia przed usunięciem
NOTIFY_BEFORE_DELETION_DAYS=30
```

## 🔍 Ścieżki Audytu

### Comprehensive Audit Logging

**Każda operacja jest logowana:**

```json
{
  "timestamp": "2025-12-06T14:23:45.123Z",
  "tenant_id": "kancelaria-kowalski",
  "project_id": "sprawa-2025-001",
  "user_id": "jan.nowak@kancelaria.pl",
  "user_role": "attorney",
  "action": "memory.read",
  "resource_type": "memory",
  "resource_id": "mem-12345",
  "resource_metadata": {
    "confidentiality": "attorney_client_privilege",
    "case_id": "sprawa-2025-001"
  },
  "ip_address": "10.0.1.50",
  "user_agent": "RAE-SDK/1.0",
  "status": "success",
  "duration_ms": 45,
  "data_classification": "privileged"
}
```

### Raportowanie Audytowe

**Generowanie raportów dla compliance:**

```python
# Raport wszystkich dostępów do sprawy
GET /api/v1/admin/audit-logs?project_id=sprawa-2025-001&from=2025-01-01&to=2025-12-31

# Raport dostępów konkretnego użytkownika
GET /api/v1/admin/audit-logs?user_id=jan.nowak@kancelaria.pl

# Eksport do CSV dla audytorów
GET /api/v1/admin/audit-logs/export?format=csv&project_id=sprawa-2025-001
```

**Typowe pytania audytorów:**

| Pytanie | Zapytanie API | Odpowiedź |
|---------|---------------|-----------|
| "Kto miał dostęp do tej sprawy?" | `GET /audit-logs?project_id=X&action=*.read` | Lista użytkowników + timestamp |
| "Kiedy dokument został zmodyfikowany?" | `GET /audit-logs?resource_id=Y&action=memory.update` | Historia zmian |
| "Czy były nieautoryzowane próby dostępu?" | `GET /audit-logs?status=forbidden` | Lista prób + IP |
| "Jakie dane były eksportowane?" | `GET /audit-logs?action=data.export` | Lista eksportów |

### Retencja Audit Logów

```yaml
# Logi audytu przechowywane DŁUŻEJ niż dane
AUDIT_LOG_RETENTION_DAYS=2555  # 7 lat (wymóg prawny)
AUDIT_LOG_IMMUTABLE=true       # Niemożliwe do usunięcia/modyfikacji
AUDIT_LOG_ENCRYPTION=true      # Zaszyfrowane
```

## 📊 Przypadki Użycia

### Baza Wiedzy Prawnej

**Scenariusz:** Kancelaria buduje bazę precedensów i orzeczeń

```python
# Projekt: baza-wiedzy (wspólny dla całej kancelarii)
POST /api/v1/memories

{
  "tenant_id": "kancelaria-kowalski",
  "project_id": "baza-wiedzy",
  "content": "Wyrok SN z 2024-05-15: Odszkodowanie za naruszenie dóbr osobistych...",
  "metadata": {
    "type": "case_law",
    "court": "Sąd Najwyższy",
    "date": "2024-05-15",
    "case_number": "I CSK 123/24",
    "topic": ["odszkodowanie", "dobra_osobiste"],
    "accessible_to": "all_attorneys"  # Dostęp dla wszystkich prawników
  }
}

# Wyszukiwanie precedensów
POST /api/v1/memories/search

{
  "tenant_id": "kancelaria-kowalski",
  "project_id": "baza-wiedzy",  # Szukamy w bazie wiedzy
  "query": "odszkodowanie dobra osobiste precedens",
  "limit": 10
}
```

### Dokumentacja Spraw

**Scenariusz:** Automatyczne tworzenie timeline sprawy

```python
# Dodawanie kolejnych wydarzeń
events = [
    {"date": "2025-01-10", "event": "Pierwsze spotkanie z klientem"},
    {"date": "2025-01-15", "event": "Złożenie pozwu do sądu"},
    {"date": "2025-02-01", "event": "Termin pierwszej rozprawy"},
    {"date": "2025-02-15", "event": "Przesłuchanie świadków"},
]

for event in events:
    POST /api/v1/memories
    {
        "tenant_id": "kancelaria-kowalski",
        "project_id": "sprawa-2025-001",
        "content": event["event"],
        "metadata": {
            "type": "case_event",
            "date": event["date"],
            "case_phase": "discovery"
        }
    }

# Odtworzenie timeline
GET /api/v1/memories?project_id=sprawa-2025-001&sort=metadata.date&type=case_event
```

### Wykrywanie Konfliktów Interesów

**Scenariusz:** Sprawdzenie czy można reprezentować nowego klienta

```python
# Nowy potencjalny klient: Firma XYZ
POST /api/v1/conflict-check

{
  "tenant_id": "kancelaria-kowalski",
  "potential_client": "Firma XYZ Sp. z o.o.",
  "opposing_party": "Firma ABC S.A.",
  "matter_description": "Spór o niezapłacone faktury"
}

# RAE sprawdza:
# 1. Czy ABC jest naszym klientem w innych sprawach?
# 2. Czy jakiś partner/adwokat ma konflikt?
# 3. Czy są powiązania w grafie wiedzy?

# Response:
{
  "conflict_detected": true,
  "details": {
    "reason": "current_client_opposition",
    "existing_projects": ["sprawa-2024-089"],
    "conflicting_client": "Firma ABC S.A.",
    "recommendation": "decline_representation"
  }
}
```

### Analiza Ryzyka (dla Audytorów)

**Scenariusz:** Identyfikacja obszarów ryzyka w audycie

```python
# Analiza ryzyk wykrytych w trakcie audytu
POST /api/v1/memories/search

{
  "tenant_id": "firma-audit-abc",
  "project_id": "audyt-klient-xyz-2025",
  "query": "ryzyko istotne kontrola wewnętrzna",
  "filters": {
    "metadata.risk_level": ["high", "critical"],
    "metadata.status": "open"
  }
}

# Generowanie raportu ryzyk
GET /api/v1/projects/{project_id}/risk-report
```

### Raportowanie (dla Księgowych)

**Scenariusz:** Generowanie raportu compliance dla klienta

```python
# Eksport wszystkich operacji księgowych
GET /api/v1/projects/{project_id}/export?type=accounting_operations&format=xlsx

# Filtrowanie per okres
GET /api/v1/memories?project_id=klient-abc&from=2025-01-01&to=2025-03-31&type=transaction
```

## 🛠️ Instalacja i Konfiguracja

### Konfiguracja dla Usług Profesjonalnych

```bash
# .env
# === Multi-tenancy & Isolation ===
TENANCY_ENABLED=true
PROJECT_ISOLATION_ENABLED=true    # KRYTYCZNE dla usług profesjonalnych
STRICT_ISOLATION=true              # Maksymalna izolacja

# === RODO/GDPR ===
ENABLE_GDPR_COMPLIANCE=true
DATA_RETENTION_LEGAL_DOCS=3650    # 10 lat
DATA_RETENTION_AUDIT_DOCS=1825    # 5 lat
AUTO_DELETE_EXPIRED=true

# === Audit & Compliance ===
ENABLE_AUDIT_LOGS=true
AUDIT_RETENTION_DAYS=2555         # 7 lat
AUDIT_LOG_IMMUTABLE=true          # Niemożliwe do usunięcia
AUDIT_DETAILED_LOGGING=true       # Szczegółowe logi

# === Security ===
ENABLE_ENCRYPTION_AT_REST=true
ENCRYPTION_ALGORITHM=AES-256-GCM
ENABLE_FIELD_TOKENIZATION=true    # Dla danych wrażliwych
ENABLE_HSM=true                    # Hardware Security Module

# === Attorney-Client Privilege ===
ENABLE_PRIVILEGE_PROTECTION=true
PRIVILEGE_EXTRA_ENCRYPTION=true
PRIVILEGE_RETENTION_INDEFINITE=true

# === Conflict of Interest Detection ===
ENABLE_CONFLICT_CHECK=true
CONFLICT_CHECK_DEPTH=3            # Głębokość sprawdzania w grafie

# === Backups ===
ENABLE_AUTOMATED_BACKUPS=true
BACKUP_FREQUENCY=daily
BACKUP_RETENTION_DAYS=2555        # 7 lat
BACKUP_ENCRYPTION=true
```

### Uprawnienia i Role

**Role dla usług profesjonalnych:**

| Rola | Uprawnienia | Przypadek Użycia |
|------|-------------|------------------|
| **Partner** | Pełny dostęp do wszystkich projektów tenanta | Właściciel kancelarii/firmy |
| **Senior Associate** | Dostęp do przypisanych projektów + baza wiedzy | Starszy prawnik/audytor |
| **Associate** | Dostęp do przypisanych projektów (read/write) | Młodszy prawnik/audytor |
| **Paralegal** | Dostęp tylko do odczytu w projektach | Asystent prawny |
| **Admin** | Zarządzanie użytkownikami, brak dostępu do spraw | Administrator systemu |

**Przypisywanie dostępu do projektów:**

```python
# Dodanie prawnika do sprawy
POST /api/v1/projects/{project_id}/access

{
  "user_id": "jan.nowak@kancelaria.pl",
  "role": "associate",
  "permissions": ["read", "write", "comment"],
  "valid_from": "2025-01-10",
  "valid_until": "2025-12-31"  # Automatyczne cofnięcie po zakończeniu sprawy
}
```

## 🆘 Wsparcie i Pomoc

### Typowe Problemy

#### Problem: Nie mogę zobaczyć danych klienta/sprawy

**Objawy:**
- 404 Not Found przy próbie dostępu
- Puste wyniki wyszukiwania

**Rozwiązanie:**
1. Sprawdź czy masz dostęp do projektu:
   ```bash
   GET /api/v1/users/me/projects
   ```
2. Poproś partnera o przyznanie dostępu:
   ```bash
   POST /api/v1/projects/{project_id}/access
   ```

#### Problem: Conflict check zwraca false positive

**Objawy:**
- System wykrywa konflikt, którego nie ma

**Rozwiązanie:**
1. Sprawdź graf relacji:
   ```bash
   GET /api/v1/graph/entities?name="Firma XYZ"
   ```
2. Zaktualizuj relacje jeśli są błędne
3. Uruchom ponownie conflict check

#### Problem: Dane nie są automatycznie usuwane

**Objawy:**
- Stare dokumenty wciąż w systemie po okresie retencji

**Rozwiązanie:**
```bash
# Sprawdź konfigurację retencji
grep RETENTION .env

# Uruchom manualnie cleanup
docker compose exec rae-api python scripts/retention_cleanup.py

# Sprawdź logi
docker compose logs celery-worker | grep retention
```

### Kontakt

**Wsparcie dla usług profesjonalnych:**
- Email: professional-services@rae-memory.ai
- Dedicated Slack channel (Enterprise customers)
- Phone: +48 22 xxx xx xx (24/7 for Enterprise)

## 📚 Dodatkowa Dokumentacja

### Dla Administratorów

- [Installation Guide](../../reference/deployment/on-premise.md)
- [Multi-Tenancy Configuration](../administracja/INDEX.md#-wielodostępność-multi-tenancy)
- [Backup & Recovery](../../reference/deployment/backup-recovery.md)

### Dla Zespołów Compliance

- [RODO/GDPR Compliance](../../compliance/GDPR.md)
- [ISO 42001](../../compliance/ISO-42001.md)
- [Data Processing Agreement](../../compliance/DPA.md)
- [Audit Trail Documentation](../../reference/services/audit-service.md)

### Techniczne

- [API Reference](http://localhost:8000/docs)
- [Project Isolation Architecture](../../reference/architecture/multi-tenancy.md)
- [Encryption & Security](../../reference/security/encryption.md)

## 🗺️ Roadmapa dla Usług Profesjonalnych

**Aktualna wersja:** 1.0.0

**Q1 2025:**
- ✅ Project-level isolation
- ✅ Conflict of interest detection
- ✅ Attorney-client privilege protection
- 🔄 Advanced retention policies

**Q2 2025:**
- E-signature integration (kwalifikowany podpis elektroniczny)
- Integration with Polish court systems (e-Sąd)
- Advanced redaction tools
- Multi-language support (EN/PL)

**Q3 2025:**
- Automated compliance reporting
- Risk scoring for audit findings
- Time tracking & billing integration
- Client portal (secure document sharing)

Zobacz [Roadmap](../../reference/enterprise/roadmap.md) dla szczegółów.

---

**Pytania?** Skontaktuj się: professional-services@rae-memory.ai

**Potrzebujesz demo?** Umów się: [rae-memory.ai/professional-services](https://rae-memory.ai/professional-services)

**Ostatnia aktualizacja:** 2025-12-06
