# IDE_Integration_Plan_for_RAE (via MCP + HTTP)

**Cel:** Uporządkować i domknąć integrację RAE z różnymi IDE tak, aby:
- konfiguracja była **spójna i jednoznaczna**,
- każde IDE z obsługą **MCP** można było podpiąć w kilka minut,
- inne IDE (JetBrains, Vim/Neovim itp.) miały prostą ścieżkę przez CLI/HTTP.

Repozytorium zakłada, że głównym mechanizmem integracji z IDE jest:
- **MCP server:** `integrations/mcp` – pakiet `rae-mcp` z entrypointem `rae-mcp-server`,   
- **Context Watcher:** `integrations/context-watcher` – HTTP daemon, który streamuje zmiany plików do RAE.   

---

## 1. Stan obecny

### 1.1. MCP Server

- Pakiet: `integrations/mcp`, `pyproject.toml` z nazwą `rae-mcp`, wersja `1.2.0`. :contentReference[oaicite:4]{index=4}  
- Entry point: `rae-mcp-server` (script w PATH po `pip install -e .`).   
- Implementacja:
  - pełna obsługa MCP: tools, resources, prompts, JSON-RPC 2.0 po STDIO,   
  - klient HTTP do RAE (`RAEMemoryClient`),  
  - PII scrubbing, rate limiting, OpenTelemetry, Prometheus, testy obciążeniowe.   

### 1.2. Dostępne narzędzia MCP (wysoki poziom)

- **Tools**: `save_memory`, `search_memory`, `get_related_context` itd.   
- **Resources**: m.in. `rae://project/reflection`, `rae://project/guidelines`.   
- **Prompts**: `project-guidelines`, `recent-context`.   

To pozwala AI w IDE:
- zapisywać wspomnienia (decyzje architektoniczne, bugi, wzorce),
- wyszukiwać kontekst,
- wstrzykiwać „guidelines” i „recent context” automatycznie.

### 1.3. Dokumentacja IDE

Istniejące dokumenty:

- `docs/integrations/mcp_protocol_server.md` – pełny przewodnik MCP (architektura, konfiguracja, IDE integration, troubleshooting, performance).   
- `docs/guides/ide-integration.md` – ogólny „IDE Integration Guide” (Cursor, Claude Desktop, VSCode/Continue, Windsurf), ale wciąż referuje **legacy** `integrations/mcp-server`.   
- `integrations/MIGRATION.md` – migracja z `integrations/mcp-server` (v1.0) do `integrations/mcp` (v1.1+). :contentReference[oaicite:13]{index=13}  

### 1.4. Wsparcie IDE (stan faktyczny)

Na podstawie dokumentacji:

- **Claude Desktop** – gotowa konfiguracja MCP (`claude_desktop_config.json`).   
- **Cursor** – `.cursor/mcp.json` / `.cursor/config.json`, wymóg ścieżek absolutnych.   
- **Cline (VSCode)** – konfiguracja w `settings.json` rozszerzenia Cline.   
- **VSCode (Continue) & Windsurf** – wymienione w `docs/guides/ide-integration.md` jako wspierane, ale brak pełnych, finalnych snippetów konfiguracji. :contentReference[oaicite:17]{index=17}  

---

## 2. Luka / problemy do rozwiązania

1. **Rozjazd dokumentacji**  
   - Część docs wskazuje na **nowy** MCP (`integrations/mcp`, `rae-mcp-server`),   
   - Część nadal używa **legacy** `integrations/mcp-server` i `python -m rae_mcp_server`.   

2. **Brak jednego „hubu” integracji IDE**  
   - Info jest porozrzucane w kilku plikach (`ide-integration.md`, `mcp_protocol_server.md`, `MIGRATION.md`, README MCP).  

3. **Brak gotowych template'ów konfiguracyjnych w repo**  
   - JSON-y dla poszczególnych IDE pojawiają się w docs, ale nie ma folderu `examples/ide-config/`, który można po prostu skopiować.  

4. **Brak jasnej historii dla IDE bez MCP**  
   - JetBrains, Vim/Neovim, Sublime itp. – plan integracji przez:
     - MCP (gdy pojawi się plugin),
     - albo przez HTTP/CLI (context watcher + SDK + skrypty).

---

## 3. Cele planu

1. **Kanoniczny dokument „IDE Integration Guide”**  
   - Jeden plik, który jest *źródłem prawdy* i linkuje do MCP docs, Context Watchera i przykładów.

2. **Zero-zamieszania z mcp-server vs mcp**  
   - Cała dokumentacja wskazuje już tylko na `integrations/mcp` i `rae-mcp-server`.

3. **Szybki onboarding**  
   - Każdy developer ma:
     - *„5-min quickstart”* dla swojego IDE,
     - gotowy JSON w `examples/ide-config/<IDE>/...`.

4. **Ścieżka dla IDE bez MCP**  
   - Opis: „jak podpiąć RAE przez HTTP/CLI”, dopóki nie ma oficjalnego MCP pluginu.

---

## 4. Plan zmian w repo (wysoki poziom)

### 4.1. Dokumentacja

1. **Nowy / zaktualizowany dokument główny**  
   - Plik: `docs/guides/IDE_INTEGRATION.md` (lub refactor obecnego `ide-integration.md`).  
   - Struktura (szczegóły w sekcji 5):

     1. Overview (MCP + Context Watcher)
     2. Quick Start (3 kroki)
     3. Supported IDEs (matrix)
     4. IDE Recipes (podrozdziały per IDE)
     5. Non-MCP IDEs (HTTP/CLI path)
     6. Troubleshooting & FAQ

2. **Aktualizacja odwołań**  
   - We wszystkich docs:
     - zamiana `integrations/mcp-server` → `integrations/mcp`,  
     - zamiana `python -m rae_mcp_server` → `rae-mcp-server` (tam, gdzie dotyczy).   

3. **Cross-linki**  
   - W `README.md` projektu – sekcja „IDE Integration (MCP)” z linkiem do `docs/guides/IDE_INTEGRATION.md`. :contentReference[oaicite:21]{index=21}  
   - W `integrations/mcp/README.md` – link do tego głównego przewodnika jako „IDE Integration Guide (full)”.   

### 4.2. Przykładowe konfiguracje IDE

1. Dodać katalog: `examples/ide-config/` z podkatalogami:

   - `examples/ide-config/claude/claude_desktop_config.json`
   - `examples/ide-config/cursor/mcp.json`
   - `examples/ide-config/cline/settings.json`
   - `examples/ide-config/windsurf/mcp.json` (po weryfikacji formatu)
   - `examples/ide-config/continue/settings.json` (po weryfikacji formatu)

2. W każdym pliku:
   - placeholdery: `RAE_API_URL`, `RAE_API_KEY`, `RAE_PROJECT_ID`, `RAE_TENANT_ID`.   
   - komentarz / README w folderze z krótką instrukcją.

### 4.3. Narzędzia developerskie / DX

1. Skrypt generujący config (opcjonalne, ale wygodne):

   - `tools/generate-ide-config.py`:
     - wejście: `--ide=claude|cursor|cline|windsurf|continue`,
     - czyta `.env` z `integrations/mcp/.env` lub root `.env`,   
     - generuje JSON w `examples/ide-config/<IDE>/generated-config.json`
       lub w HOME użytkownika.

2. Makefile / task runner:

   - w root `Makefile` lub `taskfile.yml`:
     - `make mcp-dev-install` → `cd integrations/mcp && pip install -e ".[dev]"`,
     - `make mcp-test` → `pytest` w `integrations/mcp/tests`.   

### 4.4. Ścieżka dla IDE bez MCP

Dodać sekcję w `IDE_INTEGRATION.md`:

- **JetBrains (PyCharm/IntelliJ/WebStorm)**:
  - opcja 1: uruchamianie skryptu CLI (`rae-cli` lub prosty wrapper na `rae_memory_sdk`) jako *External Tool* w IDE;
  - opcja 2: korzystanie z Context Watchera (`integrations/context-watcher`) + integracja przez API RAEm – AI klient (np. Claude Desktop) i tak korzysta z MCP.   

- **Vim/Neovim/Sublime**:
  - alias terminalowy `rae-mcp-server` + konfig w zewnętrznym kliencie MCP (Claude Desktop / Cursor / Cline),
  - ewentualnie pluginy LSP/command hooks, które triggerują zapytania HTTP do RAE API (np. zapis pliku → POST na `/v1/memories/create`).   

---

## 5. Proponowana struktura `IDE_INTEGRATION.md`

> Ten rozdział można przekleić prawie 1:1 przy tworzeniu docsa.

### 5.1. Overview

- Krótkie wyjaśnienie:
  - RAE dostarcza **MCP server** (`rae-mcp-server`) + **Context Watcher**,
  - IDE integrują się z MCP, a MCP łączy się z RAE przez HTTP.   

### 5.2. Quick Start (3 kroki)

1. Uruchom RAE (np. `docker compose.lite.yml`).
2. Zainstaluj MCP:
   ```bash
   cd integrations/mcp
   pip install -e .
   rae-mcp-server --help
Skonfiguruj swoje IDE – wybierz podrozdział (Claude / Cursor / Cline / VSCode / Windsurf).

5.3. Supported IDEs (matrix)
Tabela np.:

IDE	Typ integracji	Status	Plik przykładowy
Claude Desktop	MCP (STDIO)	✅	examples/ide-config/claude/
Cursor	MCP	✅	examples/ide-config/cursor/
VSCode + Cline	MCP	✅	examples/ide-config/cline/
VSCode + Continue	MCP / HTTP (*)	🟡	examples/ide-config/continue/
Windsurf	MCP	🟡	examples/ide-config/windsurf/
JetBrains	HTTP/CLI	🟡	(patrz sekcja Non-MCP)
Vim/Neovim/Sublime	HTTP/CLI	🟡	(patrz sekcja Non-MCP)

* – do uzupełnienia po przetestowaniu aktualnej obsługi MCP przez Continue.

5.4. IDE Recipes
Dla każdego IDE:

Claude Desktop – snippet JSON, lokalizacja pliku, kroki weryfikacji.

Cursor – .cursor/mcp.json, wymóg absolute path.

Cline (VSCode) – cline.mcpServers w settings.json.

VSCode (Continue) – po dopracowaniu: sekcja z przykładową konfiguracją.

Windsurf – analogicznie, gdy format configu zostanie ustalony.

W każdym podrozdziale:

Komenda testowa:

bash
Skopiuj kod
which rae-mcp-server
curl http://localhost:8000/health
Scenariusz „smoke test” w IDE:

„Zapisz tę decyzję architektoniczną do pamięci…”

„Wyszukaj wcześniejsze decyzje dot. bazy danych…”

5.5. Non-MCP IDEs
Opisać:

prosty CLI (np. rae-memory-cli) oparty na rae_memory_sdk,

używanie go jako External Tool (JetBrains) lub command (Vim) do:

store-memory,

search-memory,

generowania sygnałów dla RAE.

Wyraźnie zaznaczyć, że gdy pojawi się oficjalny MCP plugin dla danego IDE, RAE MCP server jest już gotowy – wystarczy wskazać rae-mcp-server jako MCP provider.

5.6. Troubleshooting & FAQ
Zebrać w jednym miejscu najczęstsze case’y z obecnych docs:

command not found: rae-mcp-server,

problem z rate limiting,

RAE API nie wstaje / porty zajęte,

MCP server nie startuje w IDE (ścieżka, env, PATH).

6. Kroki wdrożeniowe – checklist
Docs

 Zrefaktorować docs/guides/ide-integration.md → zgodnie z rozdz. 5.

 Zaktualizować wszystkie odwołania do integrations/mcp-server → integrations/mcp.

 Dodać link do IDE_INTEGRATION.md w głównym README.md.

Examples

 Utworzyć examples/ide-config/* z JSON-ami dla głównych IDE.

 Dodać krótkie README.md w examples/ide-config/.

Developer Experience

 Dodać make mcp-dev-install / make mcp-test.

 (Opcjonalnie) dodać tools/generate-ide-config.py.

Non-MCP IDEs

 Ustalić minimalny CLI (opakowanie rae_memory_sdk) i dodać do docs.

 Dodać sekcję „External Tools / Commands” dla JetBrains / Vim.

Review

 Przejść dokumentację pod kątem spójności (brak wzmianek o starym MCP).

 Przetestować:

Claude Desktop + MCP,

Cursor,

Cline,

co najmniej jeden „non-MCP” scenariusz (np. PyCharm + external tool + Context Watcher).

7. Efekt końcowy
Po realizacji tego planu:

RAE jest „IDE-ready”:

out-of-the-box z IDE obsługującymi MCP,

z jasną ścieżką dla IDE bez MCP.

Dokumentacja jest spójna, bez dualizmu mcp-server vs mcp.

Nowy użytkownik:

czyta jeden dokument,

wybiera IDE,

kopiuje gotowy JSON,

w 5–10 minut ma RAE jako pamięć długoterminową w swoim edytorze.