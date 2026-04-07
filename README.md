# Marten .NET 10 + Python + Docker - Blog Post System

Ten projekt demonstruje wykorzystanie biblioteki **Marten** (Event Store & Projections) w .NET 10, zintegrowanego z serwisem w Pythonie, działających w kontenerach Docker.

## Architektura i Event Storming

W systemie blogowym zdefiniowaliśmy następujące zdarzenia (Events):
- `PostCreated`: Inicjalizacja wpisu.
- `PostPublished`: Opublikowanie wpisu (z datą).
- `PostUpdated`: Zmiana tytułu lub treści.

**Projekcja (Read Model):**
- `PostDetails`: Aktualny stan posta, agregowany inline w momencie zapisu zdarzeń.

## Struktura projektu

- `src/Blog.Api`: Web API w .NET 10 korzystające z Martena do zapisu zdarzeń i odczytu projekcji.
- `src/Blog.Processor.Python`: Skrypt obserwujący bazę danych PostgreSQL i logujący projekcje Martena (pokazuje polyglot persistence).
- `docker/`: Konfiguracja Dockera (Dockerfile i docker-compose).

## Jak uruchomić?

1. Przejdź do folderu `docker`:
   ```bash
   cd docker
   docker-compose up --build
   ```

2. API będzie dostępne pod adresem: `http://localhost:5000` (Swagger pod `/swagger`).

3. Python Observer będzie wypisywał znalezione posty w logach kontenera:
   ```bash
   docker-compose logs -f python-observer
   ```

## Przykład użycia (cURL)

**Utworzenie posta:**
```bash
curl -X POST http://localhost:5000/posts \
     -H "Content-Type: application/json" \
     -d '{"title": "Pierwszy post", "content": "Witaj Marten!", "author": "Szymon"}'
```

**Opublikowanie posta:**
```bash
curl -X POST http://localhost:5000/posts/{GUID}/publish
```

**Pobranie szczegółów:**
```bash
curl http://localhost:5000/posts/{GUID}
```
