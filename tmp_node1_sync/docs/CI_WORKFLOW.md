# CI/CD Workflow dla RAE

## Zasada Główna

**Jeśli testy przechodzą lokalnie, to MUSZĄ przechodzić też na GitHub Actions.**

Środowisko lokalne i CI powinny być identyczne pod względem zależności i konfiguracji.

## Workflow Push

### 1. Testy Lokalne (OBOWIĄZKOWE)

Przed każdym pushem do develop:

```bash
# Uruchom wszystkie testy lokalnie
make test

# Lub bezpośrednio:
pytest --no-cov -v

# Upewnij się że wszystkie przeszły (892/892 passed)
```

✅ **Jeśli testy przechodzą lokalnie** → możesz pushować do develop
❌ **Jeśli testy failują** → popraw błędy najpierw

### 2. Push do Develop

```bash
# Commituj zmiany
git add .
git commit -m "feat: opis zmian"

# Push do develop
git push origin develop
```

### 3. Monitoring CI na Develop (Co 20 sekund)

**KRYTYCZNE:** Nie pushuj do main dopóki develop CI nie przejdzie!

```bash
# Sprawdzanie statusu co 20 sekund
while true; do
    STATUS=$(gh run list --branch develop --limit 1 --json conclusion -q '.[0].conclusion')
    echo "$(date '+%H:%M:%S') - CI Status: $STATUS"

    if [ "$STATUS" = "success" ]; then
        echo "✅ CI przeszło! Można mergować do main."
        break
    elif [ "$STATUS" = "failure" ]; then
        echo "❌ CI failed! Popraw błędy przed merge do main."
        exit 1
    fi

    sleep 20
done
```

Lub ręcznie:
```bash
# Sprawdź status
gh run list --branch develop --limit 1

# Zobacz szczegóły jeśli failed
gh run view --log-failed
```

### 4. Merge do Main (TYLKO jeśli develop CI = ✅)

```bash
# Przełącz na main
git checkout main
git pull origin main --no-rebase

# Merge develop
git merge develop --no-ff

# Push do main
git push origin main

# Zsynchronizuj develop
git checkout develop
git merge main --no-ff
git push origin develop
```

### 5. Weryfikacja Main CI

```bash
# Sprawdź czy main CI też przeszło
gh run list --branch main --limit 1

# Jeśli failed - szybka reakcja!
gh run view --log-failed
```

## Gwarancja Jakości

### Dlaczego Ten Workflow?

1. **Testy lokalne = Testy CI**: Identyczne środowisko zapobiega niespodziankom
2. **Develop jako gate**: Nie wpuszczamy złamanego kodu do main
3. **Monitoring co 20s**: Szybka detekcja problemów
4. **Main zawsze zielony**: Produkcja zawsze stabilna

### Checklist Przed Merge do Main

- [ ] ✅ Wszystkie testy lokalne przeszły (892/892)
- [ ] ✅ Develop CI = success (sprawdzone przez monitoring)
- [ ] ✅ Benchmark Smoke Test przeszedł
- [ ] ✅ Security scan przeszedł
- [ ] ✅ Linting przeszedł

## Rozwiązywanie Problemów

### Problem: CI failed a testy lokalne przeszły

**Powód:** Różnice w środowisku (zależności, wersje, konfiguracja)

**Rozwiązanie:**
1. Porównaj dependencies między lokalnym a CI:
   - Lokalne: `pip list`
   - CI: sprawdź logi Install dependencies
2. Sprawdź czy workflow używa tych samych requirements:
   - `.github/workflows/ci.yml`
   - `requirements-base.txt`, `requirements-dev.txt`
3. Upewnij się że używasz tej samej wersji Python (3.11)

### Problem: Benchmark Smoke Test timeout

**Powód:** Za mało czasu na pobranie dependencies lub wykonanie testu

**Rozwiązanie:**
```yaml
# W .github/workflows/ci.yml
timeout-minutes: 5  # Zwiększ jeśli potrzeba
```

### Problem: "No space left on device"

**Powód:** Za dużo ciężkich zależności (requirements-ml.txt ~3-4GB)

**Rozwiązanie:**
```yaml
# Instaluj TYLKO niezbędne dla benchmarków
pip install sentence-transformers  # ~400MB
# NIE instaluj: spacy, presidio, graph analysis libs
```

## Automatyzacja

### Pre-commit Hook (Opcjonalnie)

Hook automatycznie sprawdza testy przed commitowaniem:

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "🧪 Running tests before commit..."
pytest --no-cov -x || {
    echo "❌ Tests failed! Commit aborted."
    exit 1
}
echo "✅ Tests passed!"
```

### CI Monitoring Script

Automatyczny monitoring develop CI:

```bash
#!/bin/bash
# scripts/wait-for-ci.sh

BRANCH=${1:-develop}
echo "⏳ Waiting for CI on $BRANCH..."

while true; do
    RUN=$(gh run list --branch $BRANCH --limit 1 --json status,conclusion -q '.[0]')
    STATUS=$(echo $RUN | jq -r '.status')
    CONCLUSION=$(echo $RUN | jq -r '.conclusion')

    if [ "$STATUS" = "completed" ]; then
        if [ "$CONCLUSION" = "success" ]; then
            echo "✅ CI passed on $BRANCH!"
            exit 0
        else
            echo "❌ CI failed on $BRANCH!"
            gh run view --log-failed
            exit 1
        fi
    fi

    echo "$(date '+%H:%M:%S') - Still running..."
    sleep 20
done
```

Użycie:
```bash
# Push do develop
git push origin develop

# Czekaj na CI
./scripts/wait-for-ci.sh develop

# Jeśli przeszło, merge do main
git checkout main && git merge develop --no-ff && git push origin main
```

## Metryki CI

### Typowe Czasy Wykonania

- **Quick Test**: ~30s (tylko zmienione pliki)
- **Full Test**: ~4-5 minut (wszystkie 892 testy)
- **Benchmark Smoke Test**: ~2-3 minuty
- **Security Scan**: ~20s
- **Linting**: ~20s

**Total CI time**: ~5 minut dla develop, ~5 minut dla main

### Optymalizacja

1. **Caching**: Pip cache zmniejsza czas instalacji
2. **Parallel jobs**: Full Test na 3 wersjach Python równolegle
3. **Smart selection**: Quick Test tylko dla feature branches

## Podsumowanie

```
┌─────────────────────────────────────────────────────────┐
│                    WORKFLOW CI/CD                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Testy lokalne (make test)         ✅ PASSED         │
│           │                                              │
│           ▼                                              │
│  2. Push do develop                                      │
│           │                                              │
│           ▼                                              │
│  3. Monitor CI (co 20s)                                  │
│           │                                              │
│           ├─ ❌ FAILED ──→ Popraw i powtórz             │
│           │                                              │
│           └─ ✅ SUCCESS                                  │
│                   │                                      │
│                   ▼                                      │
│  4. Merge develop → main                                 │
│           │                                              │
│           ▼                                              │
│  5. Push main                                            │
│           │                                              │
│           ▼                                              │
│  6. Weryfikacja main CI                ✅ PASSED         │
│                                                          │
└─────────────────────────────────────────────────────────┘

         🎯 Main Branch zawsze zielony!
```

## Kontakt

Jeśli CI failuje mimo że testy lokalne przechodzą:
1. Sprawdź logi: `gh run view --log-failed`
2. Porównaj środowiska (pip list vs CI logs)
3. Zgłoś issue jeśli to błąd w konfiguracji CI
