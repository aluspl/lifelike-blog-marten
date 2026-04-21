# Marten .NET 10 + Docker - Blog Post System

Ten projekt demonstruje wykorzystanie biblioteki **Marten** (Event Store & Projections) w .NET 10 w kontenerach Docker. Jest to kompletna implementacja systemu blogowego opartego na architekturze Event Sourcing.

## Architektura i Event Storming

W systemie blogowym zdefiniowaliśmy następujące zdarzenia (Events):
- `PostCreated`: Inicjalizacja wpisu.
- `PostUpdated`: Zmiana tytułu lub treści.
- `PostPublished`: Opublikowanie wpisu.
- `PostUnpublished`: Cofnięcie publikacji.

**Projekcje (Read Models):**
- `PostDetails`: Pełny stan posta wraz z treścią, agregowany inline.
- `PostSummary`: Zoptymalizowany model do listowania wpisów (bez ciężkiej treści).

## Struktura projektu

### Usługi (Core Services)
- `src/Blog.Api`: Web API w .NET 10 korzystające z Martena do zapisu zdarzeń i odczytu projekcji.

### Narzędzia (Tooling)
- `cli.sh`: Główny punkt wejścia — tworzy venv, instaluje zależności i uruchamia tester.
- `scripts/tester.py`: Zaawansowany, interaktywny i skryptowalny CLI tester do weryfikacji całego flow API (obsługuje orchestrację Docker Compose).
- `scripts/processor.py`: Skrypt demonstracyjny **Polyglot Persistence** — bezpośrednio obserwuje tabele Martena w PostgreSQL i loguje stan projekcji (uruchamiany lokalnie).

### Infrastruktura
- `docker/`: Konfiguracja Dockera (Dockerfile i docker-compose).

## Jak uruchomić?

1. Przejdź do folderu `docker`:
   ```bash
   cd docker
   docker compose up --build
   ```

2. Dokumentacja API (Scalar) będzie dostępna pod adresem: `http://localhost:5501/scalar/v1`

3. Tester CLI (interaktywny):
   ```bash
   ./cli.sh
   ```

4. Automatyczny test całego flow (Orchestration):
   ```bash
   ./cli.sh --action run-all
   ```

5. Podgląd bazy Martena przez skrypt Python:
   ```bash
   python3 scripts/processor.py
   ```

> `cli.sh` automatycznie tworzy wirtualne środowisko Python (`.venv`) i instaluje zależności przy pierwszym uruchomieniu.

## Dostępne akcje CLI

```bash
./cli.sh                            # tryb interaktywny (menu)
./cli.sh --action health            # healthcheck API
./cli.sh --action list-posts        # lista wpisów
./cli.sh --action run-all           # pełny scenariusz E2E
./cli.sh --action run-all --no-teardown   # E2E bez zatrzymania compose
./cli.sh --action compose-logs      # logi docker-compose
./cli.sh --action compose-up        # uruchom środowisko docker-compose
./cli.sh --action compose-down      # zatrzymaj środowisko docker-compose
./cli.sh --action run-scenario      # uruchom scenariusz z pliku YAML
```

## Przykład użycia (cURL)

**Utworzenie posta:**
```bash
curl -X POST http://localhost:5501/posts \
     -H "Content-Type: application/json" \
     -d '{"title": "Pierwszy post", "content": "Witaj Marten!", "author": "Szymon"}'
```

**Aktualizacja posta:**
```bash
curl -X PUT http://localhost:5501/posts/{GUID} \
     -H "Content-Type: application/json" \
     -d '{"title": "Zmieniony tytuł", "content": "Nowa treść"}'
```

**Opublikowanie posta:**
```bash
curl -X POST http://localhost:5501/posts/{GUID}/publish
```

**Cofnięcie publikacji:**
```bash
curl -X POST http://localhost:5501/posts/{GUID}/unpublish
```

**Pobranie szczegółów:**
```bash
curl http://localhost:5501/posts/{GUID}
```

**Rebuild projekcji (Admin):**
```bash
curl -X POST http://localhost:5501/admin/rebuild
```
