# Plan: Elastyczny Dashboard Analityczny (Flex-Charts)

## Cel
Umożliwienie użytkownikowi tworzenia dowolnej liczby wykresów tego samego typu z niezależnymi ustawieniami czasu (zakres, rozdzielczość) oraz zarządzanie dostępnymi typami wykresów z poziomu panelu administracyjnego.

## 1. Backend (Django & API)
- [ ] **Modele**: 
    - Rozszerzenie `Widget` o pole `settings` (JSON) przechowywujące konfigurację czasu i typu wykresu.
    - Stworzenie modelu `WidgetDefinition` (dla Admina) definiującego dostępne typy wykresów i ich domyślne konfiguracje.
- [ ] **Uniwersalne API (`/api/telemetry/series/`)**:
    - Obsługa parametrów: `machine_id`, `metric` (np. speed, temp), `from`, `to`, `resolution` (1s, 1m, 1h, 1d, 1mo, 1y).
    - Implementacja dynamicznej agregacji (Django ORM `Trunc` / `Avg`).

## 2. Frontend (Builder & ECharts)
- [ ] **Globalny Pasek Narzędzi**:
    - Przycisk "Global Settings" otwierający modal do ustawienia domyślnego zakresu dla wszystkich wykresów.
    - Dynamiczne ładowanie listy dostępnych widgetów z API (zamiast hardcoded buttonów).
- [ ] **Komponent Wykresu (JS)**:
    - Dodanie obsługi `dataZoom` (suwak na dole).
    - Przycisk "Settings" w nagłówku widgetu otwierający modal z wyborem:
        - Zakres: Ostatnia godzina, zmiana, dzień, tydzień, miesiąc, rok, custom.
        - Rozdzielczość (Bucket): Auto, 1s, 1m, 1h...
- [ ] **Zapisywanie stanu**:
    - Serializacja ustawień każdego widgetu do bazy przy zapisie układu.

## 3. Administracja
- [ ] Rejestracja modeli w `admin.py` umożliwiająca włączanie/wyłączanie typów widgetów dla użytkowników.
