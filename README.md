# Marten .NET 10 + Python + Docker - Blog Post System

Ten projekt demonstruje wykorzystanie biblioteki **Marten** (Event Store & Projections) w .NET 10, zintegrowanego z serwisem w Pythonie, działających w kontenerach Docker.

## Architektura i Event Storming

W systemie blogowym zdefiniowaliśmy następujące zdarzenia (Events):
- `PostCreated`: Inicjalizacja wpisu.
- `PostPublished`: Opublikowanie wpisu (z datą).
- `PostUpdated`: Zmiana tytułu lub treści.

**Projekcje (Read Models):**
- `PostDetails`: Pełny stan posta wraz z treścią, agregowany inline.
- `PostSummary`: Zoptymalizowany model do listowania wpisów (bez ciężkiej treści).

## Struktura projektu

- `src/Blog.Api`: Web API w .NET 10 korzystające z Martena do zapisu zdarzeń i odczytu projekcji.
- `src/Blog.Processor.Python`: Skrypt obserwujący bazę danych PostgreSQL i logujący projekcje Martena.
- `scripts/tester.py`: Interaktywny i skryptowalny CLI tester do testowania flow API.
- `docker/`: Konfiguracja Dockera (Dockerfile i docker-compose).

## Jak uruchomić?

1. Przejdź do folderu `docker`:
   ```bash
   cd docker
   docker compose up --build
   ```

2. Dokumentacja API (Scalar) będzie dostępna pod adresem: `http://localhost:5000/scalar/v1`

3. Możesz użyć testera CLI:
   ```bash
   python scripts/tester.py
   ```

## Przykład użycia (cURL)

**Utworzenie posta:**
```bash
curl -X POST http://localhost:5000/posts \
     -H "Content-Type: application/json" \
     -d '{"title": "Pierwszy post", "content": "Witaj Marten!", "author": "Szymon"}'
```

**Lista postów (Summary):**
```bash
curl http://localhost:5000/posts
```

**Opublikowanie posta:**
```bash
curl -X POST http://localhost:5000/posts/{GUID}/publish
```

**Pobranie szczegółów (Details):**
```bash
curl http://localhost:5000/posts/{GUID}
```

**Rebuild projekcji (Admin):**
```bash
curl -X POST http://localhost:5000/admin/rebuild
```
