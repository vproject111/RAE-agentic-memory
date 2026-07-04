# Claude Code Setup - Multi-Agent System with Shared Memory

Przewodnik konfiguracji Claude Code z RAE Memory i Gemini CLI jako narzędziem współpracy.

## Architektura Systemu

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                               │
│  • Główny agent (płatny, inteligentny)                         │
│  • Implementuje kod                                              │
│  • Deleguje proste zadania do Gemini                            │
└──────────────┬──────────────────────────┬────────────────────────┘
               │                          │
               │ MCP Tools                │ MCP Tools
               │ (RAE Memory)             │ (Gemini CLI)
               ↓                          ↓
┌──────────────────────────┐    ┌──────────────────────────────┐
│  RAE MCP Server          │    │  Gemini MCP Server           │
│  • save_memory           │    │  • run_gemini                │
│  • search_memory         │    │  • Logs to RAE               │
│  • get_related_context   │    └────────────┬─────────────────┘
└──────────────┬───────────┘                 │
               │                             ↓
               │                      ┌────────────────┐
               │                      │  Gemini CLI    │
               │                      │  • Flash/Pro   │
               │                      │  • FREE        │
               │                      └────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      RAE Memory API                              │
│                      (Port 8000)                                 │
│                                                                  │
│  Episodic Memory:                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ • "Claude implemented user authentication"             │    │
│  │ • "Claude delegated code review to Gemini"             │    │
│  │ • "Gemini suggested using bcrypt for passwords"        │    │
│  │ • "Claude applied Gemini's suggestion"                 │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Reflections (automatic):                                        │
│  • "Gemini excels at planning and review"                       │
│  • "Claude handles complex implementation"                      │
│  • "Optimal delegation ratio: 60% Claude, 40% Gemini"           │
└─────────────────────────────────────────────────────────────────┘
```

## Krok 1: Instalacja i Uruchomienie RAE API

```bash
# 1. Uruchom RAE Memory API w Docker
# Upewnij się, że jesteś w głównym katalogu projektu
cd /path/to/RAE-agentic-memory
docker compose up -d rae-api

# 2. Sprawdź czy działa
curl http://localhost:8000/health
# Powinno zwrócić: {"status":"ok"}
```

## Krok 2: Instalacja Serwerów MCP

```bash
# 1. Zainstaluj RAE MCP Server
cd integrations/mcp
source ../../.venv/bin/activate
pip install -e .

# 2. Zainstaluj Gemini MCP Server
cd ../gemini-mcp
pip install -e .

# 3. Sprawdź instalację
which rae-mcp-server
which gemini-mcp-server
```

## Krok 3: Konfiguracja Claude Code

### Linux

Edytuj `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "/path/to/RAE-agentic-memory/.venv/bin/rae-mcp-server",
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_API_KEY": "dev-key",
        "RAE_PROJECT_ID": "claude-code-project",
        "RAE_TENANT_ID": "claude-code"
      }
    },
    "gemini": {
      "command": "/path/to/RAE-agentic-memory/.venv/bin/gemini-mcp-server",
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_API_KEY": "dev-key",
        "RAE_PROJECT_ID": "claude-code-project",
        "RAE_TENANT_ID": "claude-code"
      }
    }
  }
}
```

### macOS

Edytuj `~/Library/Application Support/Claude/claude_desktop_config.json` (ta sama zawartość co dla Linux).

### Windows

Edytuj `%APPDATA%\Claude\claude_desktop_config.json` (ta sama zawartość, ale dostosuj ścieżki).

## Krok 4: Uruchomienie Claude Code

```bash
# 1. Zrestartuj Claude Code (jeśli jest uruchomiony)
# 2. Sprawdź logi w terminalu gdzie uruchomiłeś Claude Code

# Powinny pojawić się komunikaty:
# [INFO] rae-mcp-server: MCP server started
# [INFO] gemini-mcp-server: Gemini MCP server starting version=1.0.0
```

## Przykłady Użycia

### Przykład 1: Zapisywanie i Wyszukiwanie w Pamięci

**Ty w Claude Code**:
```
Zapamiętaj: W tym projekcie używamy PostgreSQL z pgvector
dla embeddings. Zawsze używaj async/await w Pythonie.
```

**Claude odpowiada**:
- Zapisuje do RAE przez `save_memory` tool
- Tag: architecture, guidelines
- Layer: semantic

**Później możesz zapytać**:
```
Jakie mamy wytyczne dotyczące bazy danych?
```

**Claude**:
- Używa `search_memory` tool
- Znajduje wcześniej zapisane informacje
- Odpowiada z kontekstem

### Przykład 2: Delegacja do Gemini

**Ty w Claude Code**:
```
Poproś Gemini żeby sprawdził czy ten kod jest zgodny
z PEP 8 i zasugerował poprawki:

def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
```

**Co się dzieje**:
1. Claude używa tool `run_gemini` z tym promptem
2. Gemini MCP server:
   - Zapisuje do RAE: "Claude delegated code review to Gemini"
   - Wywołuje Gemini CLI
   - Gemini analizuje kod
   - Zapisuje do RAE: "Gemini suggested using sum() and list comprehension"
3. Claude otrzymuje odpowiedź Gemini
4. Claude może zaimplementować sugestie

**W RAE zostaje**:
```
[episodic] Claude delegated task to Gemini (flash): Review Python code...
[episodic] Gemini (flash) completed: Suggested using sum(item.price for item in items)
```

### Przykład 3: Workflow Multi-Agentowy

**Ty w Claude Code**:
```
1. Zapytaj Gemini: "Zaproponuj 3 różne sposoby implementacji cache'u w FastAPI"
2. Ty (Claude) wybierz najlepszy sposób
3. Zaimplementuj wybrany sposób
4. Zapisz decyzję i implementację do RAE
```

**Rezultat**:
- Gemini generuje 3 opcje (FREE)
- Claude analizuje i wybiera najlepszą (PAID, ale szybkie)
- Claude implementuje (PAID, skoncentrowana praca)
- RAE przechowuje całą historię decyzji

### Przykład 4: Przeszukiwanie Historii Współpracy

**Miesiąc później**:
```
Wyszukaj w RAE: Jakie decyzje podjęliśmy na temat cache'u?
```

**Claude**:
- Używa `search_memory`
- Znajduje: "Gemini suggested 3 options: Redis, in-memory LRU, file-based"
- Znajduje: "Claude chose Redis for distributed caching"
- Znajduje: "Implementation in src/cache/redis_client.py"

## Optymalizacja Kosztów

### Strategia Delegacji

✅ **Deleguj do Gemini** (FREE):
- Planowanie architektury
- Code review (style, best practices)
- Generowanie testów
- Pisanie dokumentacji
- Brainstorming pomysłów
- Refactoring suggestions

❌ **Zostaw dla Claude** (PAID):
- Implementacja złożonej logiki
- Debugging trudnych problemów
- Krytyczna logika biznesowa
- Integracje z zewnętrznymi API
- Kwestie bezpieczeństwa

### Przykładowe Oszczędności

| Zadanie | Koszt Claude | Koszt Gemini | Oszczędność |
|---------|--------------|--------------|-------------|
| Planning (2000 tokens) | $0.006 | FREE | 100% |
| Code Review (3000 tokens) | $0.009 | FREE | 100% |
| Tests Generation (5000 tokens) | $0.015 | FREE | 100% |
| Implementation (10000 tokens) | $0.030 | N/A | 0% |

**Średnia**: 50% zadań delegowanych → **50% oszczędności kosztów**

## Zarządzanie Quotami Gemini

### Przełączanie Kont

Jeśli wyczerpiesz dzienny limit Gemini:

```bash
# Przełącz na inne konto (wymaga konfiguracji)
.local/switch-gemini.sh lili

# Sprawdź obecne konto
.local/switch-gemini.sh
```

### Obsługa Błędów Quota

Gdy Gemini zwróci błąd quota:

```
⚠️  GEMINI QUOTA LIMIT EXCEEDED ⚠️

Limit dzienny wyczerpany na obecnym koncie.

Aby kontynuować:
1. Przełącz konto Gemini: .local/switch-gemini.sh [grzegorz|lili|marcel]
2. Uruchom ponownie zadanie

Alternatywnie: Claude może kontynuować samodzielnie
```

## Monitoring i Debugging

### Logi RAE MCP Server

```bash
# Logi w konsoli Claude Code
# Szukaj wpisów:
[INFO] rae-mcp-server: memory_stored memory_id=... layer=episodic
[INFO] rae-mcp-server: memory_searched query=... result_count=5
```

### Logi Gemini MCP Server

```bash
# Logi w konsoli Claude Code
# Szukaj wpisów:
[INFO] gemini-mcp-server: run_gemini model=flash prompt_len=245
[INFO] gemini-mcp-server: gemini_success output_len=1523
[INFO] gemini-mcp-server: memory_stored source=gemini-mcp:delegation
[INFO] gemini-mcp-server: memory_stored source=gemini-mcp:response
```

### Sprawdzanie Zawartości RAE

```bash
# API endpoint do sprawdzenia pamięci
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -H "X-Tenant-Id: claude-code" \
  -d '{
    "query_text": "Gemini suggestions",
    "k": 10,
    "project": "claude-code-project"
  }'
```

## Troubleshooting

### Problem: RAE MCP Server nie startuje

```bash
# Sprawdź czy RAE API działa
curl http://localhost:8000/health

# Sprawdź logi Docker
docker compose logs rae-api

# Sprawdź czy port 8001 jest wolny
lsof -i :8001
```

### Problem: Gemini MCP Server nie znajduje Gemini CLI

```bash
# Sprawdź czy Gemini CLI jest zainstalowany
which gemini

# Zainstaluj jeśli potrzeba
npm install -g @google/generative-ai-cli

# Autoryzuj
gemini /auth
```

### Problem: Claude nie widzi narzędzi MCP

```bash
# 1. Sprawdź konfigurację
cat ~/.config/Claude/claude_desktop_config.json

# 2. Sprawdź ścieżki do serwerów
ls -la /path/to/RAE-agentic-memory/.venv/bin/rae-mcp-server
ls -la /path/to/RAE-agentic-memory/.venv/bin/gemini-mcp-server

# 3. Zrestartuj Claude Code
```

## Korzyści Systemu

### 1. Oszczędność Kosztów
- 50% zadań delegowanych do Gemini (FREE)
- Claude skupia się na tym co robi najlepiej (complex logic)

### 2. Wspólna Pamięć
- Oba modele zapisują do RAE
- Historia współpracy zachowana
- Kontekst dostępny w przyszłych sesjach

### 3. Uczenie się Systemu
- RAE analizuje które zadania pasują do którego modelu
- Automatyczne refleksje: "Gemini dobry w X, Claude lepszy w Y"
- Optymalizacja delegacji w czasie

### 4. Pełny Audit Trail
- Każda interakcja zapisana
- Możliwość odtworzenia procesu decyzyjnego
- Zgodność z wymogami compliance

## Następne Kroki

1. **Skonfiguruj Claude Code** według powyższych instrukcji
2. **Przetestuj** proste zadania z RAE i Gemini
3. **Monitoruj** koszty i efektywność delegacji
4. **Przeglądaj** RAE reflections po tygodniu używania

## Dokumentacja Powiązana

- [RAE MCP Server](../reference/integrations/mcp_protocol_server.md)
- [Gemini MCP Server](../../integrations/gemini-mcp/README.md)
- [Orchestrator](../../orchestrator/README.md)
- [Gemini Account Switcher](../../.local/README.md)

## Wsparcie

- GitHub Issues: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- Dokumentacja: https://github.com/dreamsoft-pro/RAE-agentic-memory/tree/main/docs
