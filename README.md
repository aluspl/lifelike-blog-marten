# Marten .NET 10 + Docker - Blog Post System

Ten projekt demonstruje wykorzystanie biblioteki **Marten** (Event Store & Projections) w .NET 10 w kontenerach Docker.

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
- `scripts/tester.py`: Zaawansowany, interaktywny i skryptowalny CLI tester do weryfikacji całego flow API (obsługuje orchestrację Docker Compose).

### Infrastruktura
- `docker/`: Konfiguracja Dockera (Dockerfile i docker-compose).

## Jak uruchomić?

1. Przejdź do folderu `docker`:
   ```bash
   cd docker
   docker compose up --build
   ```

2. Dokumentacja API (Scalar) będzie dostępna pod adresem: `http://localhost:5001/scalar/v1`

3. Tester CLI (interaktywny):
   ```bash
   python3 scripts/tester.py
   ```

4. Automatyczny test całego flow (Orchestration):
   ```bash
   python3 scripts/tester.py --action run-all --api-url http://localhost:5001
   ```

## Przykład użycia (cURL)

**Utworzenie posta:**
```bash
curl -X POST http://localhost:5001/posts \
     -H "Content-Type: application/json" \
     -d '{"title": "Pierwszy post", "content": "Witaj Marten!", "author": "Szymon"}'
```

**Aktualizacja posta:**
```bash
curl -X PUT http://localhost:5001/posts/{GUID} \
     -H "Content-Type: application/json" \
     -d '{"title": "Zmieniony tytuł", "content": "Nowa treść"}'
```

**Opublikowanie posta:**
```bash
curl -X POST http://localhost:5001/posts/{GUID}/publish
```

**Cofnięcie publikacji:**
```bash
curl -X POST http://localhost:5001/posts/{GUID}/unpublish
```

**Pobranie szczegółów:**
```bash
curl http://localhost:5001/posts/{GUID}
```

**Rebuild projekcji (Admin):**
```bash
curl -X POST http://localhost:5001/admin/rebuild
```
