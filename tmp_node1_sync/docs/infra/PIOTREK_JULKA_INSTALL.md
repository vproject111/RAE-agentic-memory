# RAE Compute Node - Szybka Instalacja

Ten pakiet pozwala dołączyć Twój komputer jako węzeł obliczeniowy (Compute Node) do systemu RAE.

## 1. Wymagania
- Python 3.10+
- [Ollama](https://ollama.com/)
- Tailscale (musisz być w tej samej sieci co Grzesiek)

## 2. Instalacja
1. Skopiuj katalog `infra/node_agent` na swój komputer.
2. Zainstaluj biblioteki:
   ```bash
   pip install httpx pyyaml
   ```
3. Pobierz modele do Ollamy:
   ```bash
   ollama pull deepseek-coder:33b
   ollama pull deepseek-coder:6.7b
   ```

## 3. Konfiguracja
Utwórz plik `config.yaml` w tym samym katalogu co `main.py`:
```yaml
rae_endpoint: "http://100.66.252.117:8000"  # IP Grześka z Tailscale
node_id: "piotrek-compute-01"               # Twój unikalny ID
heartbeat_interval_sec: 30
```

## 4. Uruchomienie
```bash
python main.py
```
*(Opcjonalnie możesz skonfigurować to jako usługę systemd, wzorując się na `docs/infra/REMOTE_NODE_CONNECTION.md` w repo).*

## 5. Co to robi?
Twój węzeł będzie teraz nasłuchiwał na zadania od RAE. Kiedy dostanie zadanie programistyczne, uruchomi cykl:
1. `deepseek-coder:33b` pisze kod.
2. `deepseek-coder:6.7b` sprawdza kod pod kątem błędów.
3. Jeśli są błędy, 33b nanosi poprawki.
4. Wynik (czysty kod) wraca do Grześka.
