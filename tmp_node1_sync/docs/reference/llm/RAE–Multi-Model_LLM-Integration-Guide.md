# RAE–Multi-Model_LLM-Integration-Guide
(Claude / Gemini / ChatGPT / Llama → + DeepSeek / Qwen / Grok)

**WAŻNE: Wykonaj wszystkie kroki poniżej od początku do końca bez przerywania. 
Nie pytaj o potwierdzenie między krokami. Kontynuuj aż do pełnego zakończenia.**

Version: 1.0
Status: ✅ COMPLETED (2025-11-27)
Scope: Ujednolicenie obsługi wielu modeli LLM w RAE, wdrożenie nowych providerów (DeepSeek, Qwen, Grok), refaktoryzacja brokerów, dopięcie kontraktu API.

**Implementation Summary:**
- ✅ Created unified LLMProvider interface
- ✅ Implemented 7 providers (OpenAI, Anthropic, Gemini, Ollama, DeepSeek, Qwen, Grok)
- ✅ Built LLMRouter with smart provider selection
- ✅ Added configuration files (providers.yaml, llm_profiles.yaml)
- ✅ Created contract tests for all providers
- ✅ Updated documentation (README.md, STATUS.md, TODO.md)
- ✅ Committed all changes to git (6 commits)

All tasks from this guide have been successfully completed.

1. Cel dokumentu

Celem jest:

Ujednolicenie architektury obsługi LLM
(spójny interfejs, brak logiki warunkowej typu „if vendor == X” poza providerami).

Dokończenie abstrahowania komunikacji z modelami
tak, aby dodanie dowolnego nowego modelu było:

dodaniem jednego pliku,

rejestracją wpisu w configu,

opcjonalnym opisaniem kosztów.

Rozszerzenie RAE o kolejne modele:

DeepSeek,

Qwen,

Grok,
w pełni zgodnie z istniejącą architekturą i mechanizmami:

cost-guard,

LLM-router,

telemetry,

profiles/yaml,

fallback policies.

2. Architektura docelowa
apps/
  llm/
    broker/
      llm_router.py
      cost_policy.py
      fallback_policy.py
      request_normalizer.py
      response_normalizer.py
    providers/
      base.py                  # kontrakt: LLMProvider
      openai_provider.py
      anthropic_provider.py
      gemini_provider.py
      ollama_provider.py
      llama_provider.py
      deepseek_provider.py     # NOWE
      qwen_provider.py         # NOWE
      grok_provider.py         # NOWE
    models/
      llm_request.py
      llm_response.py
      llm_error.py
    config/
      llm_profiles.yaml
      providers.yaml

3. Kontrakt: LLMProvider

Ustanawiamy jedyny, obowiązkowy interfejs, który musi spełnić każdy provider:

class LLMProvider(Protocol):
    name: str
    max_context_tokens: int
    supports_streaming: bool
    supports_tools: bool

    async def complete(self, request: LLMRequest) -> LLMResponse: ...
    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]: ...

Co to daje?

brak if-ów w routerze,

router ma 100% pewności, że provider ma te same metody,

nowe modele = tylko nowy plik w providers/.

4. Format wejścia: LLMRequest

Standaryzujemy:

@dataclass
class LLMRequest:
    model: str
    messages: list[LLMMessage]          # system/user/assistant
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    json_mode: bool = False
    tools: Optional[list[LLMTool]] = None
    metadata: dict = field(default_factory=dict)

Normalizacja prompts (ważne!)

Każdy provider odpowiada za:

mapowanie messages[] na format vendor-specific,

mapowanie tools,

ustawienie JSON-mode.

5. Format wyjścia: LLMResponse
@dataclass
class LLMResponse:
    text: str
    usage: TokenUsage
    finish_reason: str
    raw: dict

6. LLM Router

Router odpowiada za:

wybór modelu na podstawie profilu,

walidację budżetu przez cost-guard,

odpalanie providera,

fallback na inny model przy błędach,

logging + telemetry.

TO DO w routerze

 sprawdź, czy router nie sprawdza vendorów „po nazwie infrastrukturalnej”
→ ma pytać tylko provider: supports_streaming, supports_tools.

 dodać jednolite typy błędów:

LLMRateLimitError,

LLMAuthError,

LLMTransientError,

LLMProviderError.

 dodać fallback:

rate limit → przełącz model,

transient → retry,

autoryzacja → stop.

7. Zadania do wykonania PRZED dodaniem nowych modeli
7.1. Refaktoryzacja providerów Claude/Gemini/OpenAI/Llama do wspólnego kontraktu

 upewnić się, że każdy provider implementuje:

.complete()

.stream()

 wyciąć if-y typu:

if "gemini" in model_name

if vendor == "claude"
→ wszystko musi być schowane w providerze.

7.2. Ujednolicenie JSON-mode

 wprowadzić pole: json_mode: bool

 provider mapuje to na odpowiedni parametr API:

OpenAI: response_format={"type": "json_object"}

Gemini: "response_schema": {...}

Claude: "json": true

DeepSeek/Qwen/Grok → TBD

7.3. Ujednolicenie tool-calling

 wprowadzić jednolity LLMTool

 provider mapuje narzędzia na:

OpenAI: "tools": [...]

Claude: "functions": [...]

Gemini: "function_declarations": [...]

inne: brak/niestandardowe → discard lub symulacja

8. Implementacja nowych modeli (DeepSeek / Qwen / Grok)

Każdy provider musi:

dziedziczyć po LLMProvider,

konwertować LLMRequest → native request,

konwertować odpowiedź → LLMResponse,

raporotwać usage tokenów,

poprawnie obsłużyć błędy.

8.1. DeepSeek Provider – TODO

Plik:
apps/llm/providers/deepseek_provider.py

API:

REST

bardzo podobne do OpenAI

wspiera tool-calling

Plan:

 mapowanie messages → native format

 JSON-mode

 tool calling

 streaming

 obsługa 429 / 500 / timeout

 usage: input/output_tokens

8.2. Qwen Provider – TODO

Plik:
apps/llm/providers/qwen_provider.py

API:

różna struktura messages

narzędzia jako "prompt": { "tools": [...] }

częściowo kompatybilny z OpenAI

Plan:

 normalizacja message

 poprawne odwzorowanie narzędzi

 streaming

 token usage

 obsługa JSON-mode

8.3. Grok Provider – TODO

Plik:
apps/llm/providers/grok_provider.py

API:

OpenAI-like, ale

własna semantyka finish_reason

długi kontekst

Plan:

 adapter do messages

 usage i mapping finish_reason

 streaming

 error handling

 JSON-mode

9. Konfiguracja providers.yaml

Dodaj:

providers:
  deepseek:
    endpoint: https://api.deepseek.com/v1/chat/completions
    api_key_env: DEEPSEEK_API_KEY

  qwen:
    endpoint: https://api.qwen.ai/v1
    api_key_env: QWEN_API_KEY

  grok:
    endpoint: https://api.x.ai/v1/chat/completions
    api_key_env: GROK_API_KEY

10. Konfiguracja llm_profiles.yaml

Dodaj np.:

llm_profiles:

  cheap_bulk:
    candidates: [deepseek-lite, qwen-lite, llama3-8b]
    max_cost_per_1k: 0.002

  code_smart:
    candidates: [deepseek-coder, gpt-4.1, claude-3.5-sonnet]
    min_context: 16000

  reasoning_heavy:
    candidates: [grok-2, claude-3.7, gpt-o1]
    priority: [grok-2, claude-3.7]

11. Testy kontraktowe (obowiązkowe)

Plik: tests/llm/test_llm_provider_contract.py

Zakres:

 basic prompt: „Hello world”

 JSON-mode

 tool calling

 streaming

 duży prompt (>8000 tokenów)

 usage present

 poprawny finish_reason

Każdy provider jest testowany tą samą baterią testów.

12. Telemetry

Dodać eventy:

llm.provider.start

llm.provider.ok

llm.provider.error

llm.provider.fallback

llm.provider.retry

13. Checklista do PR
Przed dodaniem DeepSeek/Qwen/Grok:

 ujednolicony kontrakt LLMProvider

 wszystkie istniejące providery zgodne z kontraktem

 router bez if vendor == ...

 parametry JSON-mode zunifikowane

 narzędzia zunifikowane

Po dodaniu każdego nowego modelu:

 adapter w providers/

 wpis w providers.yaml

 wpis w llm_profiles.yaml

 testy kontraktowe

 testy smoke z realnymi kluczami

 dokumentacja w README

14. Koniec dokumentu

Wdrożenie powyższego sprawi, że:

cała obsługa modeli LLM w RAE będzie spójna,

dodanie kolejnych modeli (np. Mistral, Jamba, Delta, Luma, Codestral) zajmie mniej niż godzinę,

broker stanie się formalnym „multi-vendor engine”,

Feniks uzyska powtarzalne, mierzalne benchmarki modeli do refaktoryzacji AngularJS → NextJS,