# 🔴 Problem z Gemini CLI - Analiza

## TL;DR

**Gemini CLI NIE DZIAŁA z orkiestratorem** z powodu błędu:
```
"Unable to submit request because thinking is not supported by this model"
```

**Rozwiązanie:** Użyj Claude API zamiast Gemini CLI.

---

## 🐛 Błędy Które Widzieliśmy

### Błąd #1: Parsing Error (pozorny)
```
[ERROR] [ImportProcessor] Could not find child token in parent raw content
```

**Myśleliśmy że:** Problem z długimi promptami/special chars
**Próbowaliśmy:**
- ✅ Skrócenie reguł projektowych (73KB → 5KB)
- ✅ Rozbicie dużych zadań na małe
- ✅ Wysyłanie promptu przez stdin zamiast `-p` flag

**Efekt:** Dalej ten sam błąd

### Błąd #2: Prawdziwa Przyczyna
```json
{
  "error": {
    "code": 400,
    "message": "Unable to submit request because thinking is not supported by this model",
    "status": "INVALID_ARGUMENT"
  }
}
```

**Źródło:** `/tmp/gemini-client-error-Turn.run-sendMessageStream-*.json`

---

## 🔍 Analiza Przyczyny

### Co się dzieje:

1. **Gemini CLI dodaje własny kontekst:**
   - Strukturę katalogów projektu (~200 plików)
   - Informacje o systemie operacyjnym
   - Working directory
   - Setup message: "This is the Gemini CLI. We are setting up the context..."

2. **Gemini CLI próbuje użyć "thinking mode":**
   - Gemini CLI ma wbudowany advanced mode
   - Automatycznie włącza extended thinking
   - Model `gemini-2.0-flash` **NIE WSPIERA** thinking mode

3. **Konflikt:**
   ```
   Gemini CLI context setup
   + Thinking mode request
   + Orchestrator prompt
   = ERROR 400: thinking not supported
   ```

---

## 💡 Dlaczego Proste Testy Działały?

W `test_simple.py` prosty prompt działał:
```python
prompt = "What is 2+2? Answer in one word only."
```

**Działa bo:**
- Krótki prompt
- Brak kontekstu orkiestratora
- Gemini CLI nie włącza thinking mode dla prostych promptów

**Nie działa dla orkiestratora bo:**
- Długi prompt z project rules
- Strukturalny JSON output required
- System prompt + user prompt
- Gemini CLI recognition → thinking mode → ERROR

---

## 🚫 Czego NIE można zrobić

### ❌ Opcja 1: Wyłączyć thinking mode w Gemini CLI
**Problem:** Brak takiej opcji w CLI flags
```bash
gemini --help  # Nie ma --no-thinking ani podobnych
```

### ❌ Opcja 2: Użyć innego modelu Gemini
**Problem:** Wszystkie modele mają ten sam problem z CLI
- gemini-2.0-flash → nie wspiera thinking
- gemini-2.0-pro → nie wspiera thinking
- gemini-2.5-flash → nie wspiera thinking
- gemini-3.0-pro-preview → MOŻE wspierać, ale preview/unstable

### ❌ Opcja 3: Obejść CLI context
**Problem:** CLI zawsze dodaje swój setup context
- Nie da się tego wyłączyć
- To wbudowane w CLI behavior

---

## ✅ Co MOŻNA zrobić

### Opcja A: Użyj Claude API (ZALECANE) ✅
```yaml
# .orchestrator/providers.yaml
providers:
  claude:
    enabled: true
    default_model: claude-sonnet-4-5-20250929

  gemini:
    enabled: false  # Disabled
```

**Zalety:**
- ✅ Działa niezawodnie
- ✅ Świetna jakość dla orkiestracji
- ✅ Brak problemów z promptami
- ✅ Support dla złożonych zadań

**Wady:**
- 💰 Koszt: ~$0.003/$0.015 per 1K tokens
- 💰 ~$0.01-0.10 per zadanie

---

### Opcja B: Użyj Gemini API (z API key)

Zamiast Gemini CLI, użyj bezpośrednio Gemini API:

```python
# Wymaga google-generativeai package
import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content(prompt)
```

**Zalety:**
- ✅ Brak CLI context overhead
- ✅ Pełna kontrola nad requestem
- ✅ Darmowe (generous free tier)

**Wady:**
- ⚠️ Wymaga API key (nie browser auth)
- ⚠️ Trzeba przepisać GeminiProvider
- ⚠️ Nie testowane z orkiestratorem

---

### Opcja C: Ollama (local models)

```yaml
providers:
  ollama:
    enabled: true
    default_model: llama3:70b
    settings:
      endpoint: http://localhost:11434
```

**Zalety:**
- ✅ Całkowicie darmowe
- ✅ Privacy - wszystko local
- ✅ Brak limitów API

**Wady:**
- ⚠️ Wymaga lokalnej instalacji Ollama
- ⚠️ Potrzebuje GPU/dużo RAM
- ⚠️ Wolniejsze niż API

---

## 📊 Porównanie Kosztów

| Provider | Model | Koszt/zadanie | Niezawodność |
|----------|-------|---------------|--------------|
| Claude API | Sonnet 4.5 | ~$0.01-0.10 | ✅✅✅ Wysoka |
| Gemini CLI | 2.0-flash | $0 | ❌ Nie działa |
| Gemini API | 2.0-flash | $0* | ✅ Powinna działać |
| Ollama | Llama 3 70B | $0 | ✅✅ Średnia-Wysoka |

*Free tier: 15 RPM, 1M tokens/day

---

## 🎯 Rekomendacja

**Dla produkcji:** Claude API
- Najlepsza niezawodność
- Sprawdzona jakość
- Warto $0.01-0.10 per zadanie

**Dla local dev:** Ollama
- Darmowe
- Privacy
- Wymaga setup

**NIE używaj:** Gemini CLI
- Nie działa z orkiestratorem
- Błędy thinking mode
- Zmarnowany czas debugowania

---

## 📝 Historia Debugowania

1. ✅ Znaleziono błąd parsing (prompt too long)
2. ✅ Skrócono prompty (73KB → 5KB)
3. ✅ Zmieniono na stdin zamiast -p flag
4. ❌ Dalej ten sam błąd
5. ✅ Znaleziono error log: `/tmp/gemini-client-error-*.json`
6. ✅ Odkryto prawdziwą przyczynę: "thinking not supported"
7. ✅ Przełączono na Claude API
8. ✅ **DZIAŁA!**

---

## 🔗 Linki

- Error log: `/tmp/gemini-client-error-Turn.run-sendMessageStream-*.json`
- Gemini docs: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini
- Claude API docs: https://docs.anthropic.com/claude/reference/

---

**Wniosek:** Gemini CLI nie nadaje się do orkiestracji multi-agent. Użyj Claude API.
