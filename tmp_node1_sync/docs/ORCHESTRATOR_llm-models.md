#Claude


# Użyj Haiku (prosty/tani)
claude-code --model haiku task.md

# Użyj Sonnet (średni - domyślny)
claude-code --model sonnet task.md

# Użyj Opus (drogi/mocny)
claude-code --model opus task.md

Kiedy używać którego modelu:
Haiku (prosty/tani) - do:

Proste edycje plików
Linting i formatowanie
Aktualizacja dokumentacji
Proste testy
Rutynowe commity
Sprawdzanie logów

Sonnet (średni) - do:

Większość zadań programistycznych
Refactoring
Debugowanie
Pisanie testów
Normalna praca developerska

Opus (drogi) - do:

Skomplikowana architektura
Złożone algorytmy
Code review całego projektu
Trudne bugi
Projektowanie systemu


#Gemini
To change Gemini models in the Gemini CLI and understand available options for an orchestrator to assign tasks of varying difficulty, here's a summary based on the search results:

  1. Available Models:
  The Gemini CLI supports models like gemini-3-pro-preview, gemini-2.5-pro, gemini-2.5-flash, and gemini-2.5-flash-lite. You can see the available options by using the /model command within an active CLI session.

  2. Changing Models:
  You have several ways to switch between models:
   * At Launch: Use the --model flag when starting the CLI, e.g., gemini --model gemini-2.5-flash.
   * Within a Session: Use the /model command inside an active CLI session to select a different model from a dialog.
   * Environment Variable: Set the GEMINI_MODEL environment variable (e.g., export GEMINI_MODEL="gemini-2.5-pro") for a default model that persists across sessions.

  3. "Difficulty" for Orchestrator (Model Selection based on task complexity):
  The concept of "difficulty" isn't a direct parameter but can be controlled by choosing the appropriate model and using specific API parameters.

   * Model Choice:
       * For complex tasks requiring advanced reasoning and creativity, Pro models (e.g., gemini-2.5-pro, gemini-3-pro-preview) are recommended.
       * For simpler, quicker tasks that need a balance of speed and reasoning, Flash models (e.g., gemini-2.5-flash, gemini-2.5-flash-lite) are more suitable.


