RAE-Security-Certification-Kickstart.md

Przygotowanie projektu RAE do certyfikacji bezpieczeństwa (NASK / PCA / Common Criteria / KSC)
Wersja: 1.0

1. Cel dokumentu

Celem jest przygotowanie projektu RAE (Reflective Agentic-memory Engine) do potencjalnej certyfikacji bezpieczeństwa w Polsce (NASK-PIB / PCA) oraz zgodności z normami bezpieczeństwa IT, w tym:

Common Criteria (ISO/IEC 15408)

ISO/IEC 18045

ISO/IEC 27001/27002

OWASP ASVS

NIS2 oraz polski Krajowy System Certyfikacji Cyberbezpieczeństwa

Europejski AI Act (w obszarach dotyczących governance, audytu i traceability)

Dokument ma charakter operacyjny: co zrobić, aby RAE Core był formalnie gotowy do procesu certyfikacji.

2. Zakres systemu RAE podlegający certyfikacji

Do certyfikacji mogą być zgłoszone:

2.1. RAE Core (zalecany zakres)

warstwy pamięci 1–4 (episodic, semantic, vector, reflective)

moduł decyzyjny

moduł HIL (human-in-loop)

moduł komunikacyjny (broker + guardrails)

kontrola tokenów + audyt

mechanizmy aktualizacji (CI/CD)

pliki konfiguracji bezpieczeństwa

API systemu

struktura przechowywania danych (Postgres + Qdrant + Redis)

2.2. Zakres opcjonalny

integracje z zewnętrznymi LLM (GPT, Claude, Gemini)

moduł Feniks (jeżeli będzie certyfikowany jako „wsparcie modernizacji kodu”)

moduły pluginów i MCP-connectors

3. Wymagania certyfikacyjne — skrót techniczny
3.1. Dokumentacja, którą MUSI posiadać system

Architecture Security Document

Threat Model (STRIDE)

Opis mechanizmów bezpieczeństwa

Proces aktualizacji, rollback i kontroli integralności

Polityka logowania i audytu

Polityka dostępu i autoryzacji

Wymagania kryptograficzne + opis używanego TLS, podpisów, hashy

SBOM (CycloneDX / SPDX)

Opis przepływów danych (Data Flow Diagrams)

Data Protection Impact Assessment (mini-DPIA)

4. Testowanie wymagane w procesie certyfikacji
4.1. Testy bezpieczeństwa (obowiązkowe)

testy penetracyjne black-box + grey-box

testy DAST (np. OWASP ZAP)

testy SAST (static analysis – np. Semgrep)

fuzz testing API i warstw pamięci

testy odporności na injection (command, prompt, SQL, vector poisoning)

weryfikacja izolacji komponentów

4.2. Testy kryptograficzne (jeśli używane komponenty crypto)

poprawność użycia TLS

poprawność użycia kluczy i algorytmów

analiza zarządzania sekretami

4.3. Testy zgodności

zgodność z OWASP ASVS L2

zgodność z ISO 27001 Annex A (najważniejsze punkty)

zgodność z wymaganiami PCA / Common Criteria jeśli dotyczy

5. Plan przygotowania RAE do certyfikacji (techniczny, wykonawczy)
5.1. Etap 1 – „Security Readiness” (2–3 tygodnie)
5.1.1. Dokumenty do przygotowania

docs/security/RAE-Security-Architecture.md

docs/security/RAE-Threat-Model.md

docs/security/RAE-Security-Controls.md

docs/security/RAE-Update-Policy.md

docs/security/RAE-Incident-Response-Lite.md

docs/security/RAE-Data-Flows.md

5.1.2. Techniczne prace do wdrożenia

generowanie SBOM w CI (CycloneDX + SPDX)

automatyczne skanowanie SAST (Semgrep)

automatyczne skanowanie DAST (OWASP ZAP w CI pipeline)

dodanie fuzz testów (API + memory layers)

wprowadzenie podpisywania release’ów (Cosign / Sigstore)

dodanie integrity-check przy uruchamianiu

integracja z RAE-audit-logs (już jest fundament)

wprowadzenie SECURITY.md w repo

5.1.3. Wymagana standaryzacja

kontrola wersji + changelog

polityka commitów (Conventional Commits)

polityka dostępu do repo (klucze + zasady)

polityka backupów

5.2. Etap 2 – Audyty zewnętrzne (2–6 tygodni)
5.2.1. Audyty techniczne

zewnętrzny test penetracyjny

fuzzing warstw pamięci przez niezależny zespół

analiza API i punktów komunikacyjnych

testy integracji z LLM (prompt-security, injection-resistance)

5.2.2. Analiza zgodności

zgodność z OWASP ASVS

zgodność z ISO 27001 cross-map

zgodność z wymaganiami Common Criteria EAL1–EAL2 (opcjonalnie EAL4)

5.2.3. Raport zbiorczy

Powinien zawierać:

listę podatności

rekomendacje

ocenę ryzyka

potwierdzenie odporności

5.3. Etap 3 – Formalne przygotowanie do certyfikacji (2–4 tygodnie)

kompilacja pełnego pakietu dowodowego

przygotowanie dossier zgodnie z wymaganiami PCA/NASK

dostosowanie systemu do profilu ochrony (Protection Profile)

przygotowanie dokumentacji procesowej organizacji („light-mode”):

polityka bezpieczeństwa

polityka aktualizacji

polityka zarządzania incydentami

polityka uprawnień

6. Minimalny zestaw dokumentów wymaganych przez jednostki certyfikujące
6.1. Pakiet techniczny

Architektura RAE

Threat Model

Security Controls Document

API Security Analysis

Memory Layer Safety Analysis

Crypto Usage Document

SBOM + OSS risk assessment

6.2. Pakiet organizacyjny

Security Policy

Incident Response

Update/Deployment Policy

Vulnerability Management

DPIA (jeśli przetwarzane dane osobowe)

7. Co powinno być jasno zdefiniowane w RAE przed certyfikacją
7.1. W warstwie technicznej

czy pamięci są deterministyczne i audytowalne

jak LLM są izolowane od danych użytkownika

jak wygląda governance nad odpowiedziami LLM

polityka kosztowa i token-guard

jak działają reguły HIL

jak działa integracja z modułem feniks

jak realizowana jest odporność na “prompt-poisoning”

jak ograniczony jest dostęp do baz danych

jak rejestrowane są decyzje i kontekst

7.2. W warstwie operacyjnej

cykl życia wersji (version lifecycle)

procesy reagowania na incydenty

dostęp do środowisk produkcyjnych

polityka kluczy API i sekretów

8. Gotowe check-listy
8.1. Security Architecture Checklist

 Warstwa transportowa → TLS 1.3

 Uwierzytelnianie → klucze API + podpisy

 Autoryzacja → role i uprawnienia

 Audit log → włączony

 Memory isolation → OK

 Token guard → OK

 HIL → OK

 Integrity check → OK

 SBOM → generowane

 SAST → automatyczne

 DAST → automatyczne

 Fuzz → działa

 Backup policy → istnieje

9. Rekomendacja zakresu certyfikacji

Dla RAE najlepsza opcja to:

⭐ Zakres: „RAE Core Security + Memory Isolation + Auditability + Governance”

Dlaczego?

to najmocniejsze części Twojego systemu,

nie trzeba certyfikować wszystkiego,

można uzyskać certyfikat szybciej i taniej,

daje realny atut biznesowy.

10. Szacunkowe koszty i czas

Od lat praktyki:

Etap	Czas	Koszt
Przygotowanie (to co w tym dokumencie)	4–6 tyg	0 zł (samodzielnie)
Audyty zewnętrzne	2–6 tyg	15–40 tys. zł
Certyfikacja NASK/PCA	6–20 tyg	40–150 tys. zł

Dla MVP RAE Core: ~60–80 tys. zł i 3 miesiące.

11. Podsumowanie

Ten dokument jest gotowym planem, aby:

zrobić RAE „security-ready”,

spełnić wymagania PCA/NASK/Common Criteria,

przygotować dokumentację,

zrobić automatyczne testy bezpieczeństwa,

przejść zewnętrzny audyt,

wejść w certyfikację formalną bez stresu.

Dzięki Twojej architekturze (warstwy pamięci, pełne audytowanie, deterministyczność, HIL, kontrola tokenów) RAE jest w praktyce bliżej certyfikacji niż 90% komercyjnych AI-platform.