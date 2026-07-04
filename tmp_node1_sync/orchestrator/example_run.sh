#!/bin/bash
# Przykład uruchomienia orkiestratora - krok po kroku

echo "🚀 Orchestrator - Practical Example"
echo "===================================="
echo ""

# Sprawdź czy jesteś w odpowiednim katalogu
if [ ! -f "orchestrator/test_simple.py" ]; then
    echo "❌ Błąd: Uruchom ten skrypt z głównego katalogu projektu"
    echo "   (katalog zawierający folder 'orchestrator')"
    exit 1
fi

echo "📍 Krok 1: Weryfikacja (czy orkiestrator działa?)"
echo "   Uruchom: cd orchestrator && python test_simple.py"
echo ""
read -p "Naciśnij Enter aby kontynuować..."

cd orchestrator
python test_simple.py
cd ..

echo ""
echo "✅ Jeśli wszystkie testy przeszły, możesz kontynuować"
echo ""

echo "📍 Krok 2: Zobacz przykładowe zadania"
echo "   Plik: .orchestrator/tasks.yaml"
echo ""
cat .orchestrator/tasks.yaml
echo ""
read -p "Naciśnij Enter aby kontynuować..."

echo ""
echo "📍 Krok 3: Wybierz zadanie do uruchomienia"
echo ""
echo "Dostępne zadania:"
echo "  TEST-001      - Dodaj docstrings (low risk, FREE - Gemini)"
echo "  TEST-002      - Dodaj testy (medium risk, FREE - Gemini Pro)"
echo "  RAE-PHASE2-001 - Implementacja core (high risk, PAID - Claude)"
echo "  RAE-API-001    - REST endpoint (medium risk, FREE - Gemini Pro)"
echo ""
echo "💡 Zalecam zacząć od TEST-001 (prosty, darmowy)"
echo ""
read -p "Które zadanie chcesz uruchomić? (np. TEST-001): " TASK_ID

if [ -z "$TASK_ID" ]; then
    echo "❌ Nie podano ID zadania. Kończę."
    exit 1
fi

echo ""
echo "📍 Krok 4: Uruchomienie zadania: $TASK_ID"
echo ""
echo "Komenda:"
echo "  cd orchestrator"
echo "  python main.py --task-id $TASK_ID"
echo ""
read -p "Uruchomić zadanie? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Anulowano. Możesz uruchomić manualnie:"
    echo "  cd orchestrator"
    echo "  python main.py --task-id $TASK_ID"
    exit 0
fi

echo ""
echo "🚀 Uruchamiam zadanie $TASK_ID..."
echo "   (To może potrwać kilka minut)"
echo ""

cd orchestrator
python main.py --task-id "$TASK_ID"
EXIT_CODE=$?

cd ..

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Zadanie zakończone!"
    echo ""
    echo "📊 Zobacz wyniki:"
    echo "   - Logi: ORCHESTRATOR_RUN_LOG.md"
    echo "   - Stan: orchestrator/state/${TASK_ID}.json"
    echo ""
    echo "💰 Koszt:"
    grep "Cost:" ORCHESTRATOR_RUN_LOG.md | tail -1
else
    echo "❌ Zadanie nie powiodło się (kod: $EXIT_CODE)"
    echo ""
    echo "🔍 Sprawdź logi w ORCHESTRATOR_RUN_LOG.md"
fi

echo ""
echo "📖 Więcej informacji:"
echo "   orchestrator/QUICK_START.md"
echo "   orchestrator/README.md"
