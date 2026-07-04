#!/bin/bash

REPO="dreamsoft-pro/RAE-agentic-memory"

echo "🔍 GitHub Actions Status - $(date +%H:%M:%S)"
echo "================================================"
echo ""

# Pobierz aktualną gałąź
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Bieżąca gałąź: $CURRENT_BRANCH"
echo ""

# Pobierz ostatnie 10 runs i filtruj po bieżącej gałęzi
RUNS=$(gh run list --repo $REPO --limit 10 --json databaseId,status,conclusion,name,headBranch,createdAt,workflowName)

# Znajdź ostatni run dla bieżącej gałęzi
CURRENT_BRANCH_RUN=$(echo "$RUNS" | jq --arg branch "$CURRENT_BRANCH" '[.[] | select(.headBranch == $branch)] | .[0]')

# Jeśli nie ma workflow dla tej gałęzi, nie blokuj commita
if [ "$CURRENT_BRANCH_RUN" = "null" ] || [ -z "$CURRENT_BRANCH_RUN" ]; then
    echo "⚠️  Brak workflow dla gałęzi '$CURRENT_BRANCH'"
    echo "✓ Commit dozwolony - brak workflow do sprawdzenia"
    exit 0
fi

echo "✓ Znaleziono workflow dla gałęzi '$CURRENT_BRANCH'"
LAST_RUN=$CURRENT_BRANCH_RUN

RUN_ID=$(echo "$LAST_RUN" | jq -r '.databaseId')
CONCLUSION=$(echo "$LAST_RUN" | jq -r '.conclusion')
STATUS=$(echo "$LAST_RUN" | jq -r '.status')
NAME=$(echo "$LAST_RUN" | jq -r '.workflowName')
BRANCH=$(echo "$LAST_RUN" | jq -r '.headBranch')

echo "📌 Sprawdzany workflow: $NAME"
echo "   Gałąź: $BRANCH"
echo "   Status: $STATUS"
echo "   Result: $CONCLUSION"
echo ""

# Jeśli failed - pokaż logi błędów
if [ "$CONCLUSION" = "failure" ]; then
    echo "❌ WYKRYTO BŁĘDY! Analiza logów..."
    echo ""
    gh run view $RUN_ID --repo $REPO --log | grep -A 5 -i "error\|failed\|✗"
    echo ""
    echo "💡 Pełne logi: gh run view $RUN_ID --repo $REPO --log"
    exit 1
elif [ "$CONCLUSION" = "success" ]; then
    echo "✅ Wszystko działa poprawnie!"
    exit 0
else
    echo "⏳ Workflow w trakcie wykonywania..."
    exit 2
fi