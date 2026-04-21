# Marten .NET 10 + Docker - Blog Post System

Ten projekt demonstruje wykorzystanie biblioteki **[Marten](https://martendb.io/)** (Event Store & Projections) w .NET 10 w kontenerach Docker. Jest to kompletna implementacja systemu blogowego opartego na architekturze Event Sourcing.

> **Dokumentacja:** [martendb.io](https://martendb.io/) | [Event Sourcing](https://martendb.io/events/) | [Projekcje](https://martendb.io/events/projections/)

## Architektura i Event Storming

W systemie blogowym zdefiniowaliśmy następujące zdarzenia (Events):
- `PostCreated`: Inicjalizacja wpisu.
- `PostUpdated`: Zmiana tytułu lub treści.
- `PostPublished`: Opublikowanie wpisu.
- `PostUnpublished`: Cofnięcie publikacji.

**Projekcje (Read Models):**
- `PostDetails`: Pełny stan posta wraz z treścią — `SingleStreamProjection`, lifecycle `Inline`.
- `PostSummary`: Zoptymalizowany model do listowania wpisów — `SingleStreamProjection`, lifecycle `Inline`.
- `AuthorStats`: Statystyki per autor agregowane z wielu strumieni — `MultiStreamProjection`, lifecycle `Async`.

## Struktura projektu

### Usługi (Core Services)
- `src/Blog.Api`: Web API w .NET 10 korzystające z Martena do zapisu zdarzeń i odczytu projekcji.

### Narzędzia (Tooling)
- `cli.sh`: Główny punkt wejścia — tworzy venv, instaluje zależności i uruchamia tester.
- `scripts/tester.py`: Zaawansowany, interaktywny i skryptowalny CLI tester do weryfikacji całego flow API (obsługuje orchestrację Docker Compose).
- `scripts/presentation_guide.py`: Interaktywny przewodnik "Guided Tour" po architekturze Event Sourcing (wyjaśnia kroki i zagląda bezpośrednio do bazy danych).
- `scripts/processor.py`: Skrypt demonstracyjny **Polyglot Persistence** — bezpośrednio obserwuje tabele Martena w PostgreSQL i loguje stan projekcji (uruchamiany lokalnie).

### Dokumentacja
- `docs/PRESENTATION.md`: Skrypt prezentacji i kompendium wiedzy o Event Sourcingu w tym projekcie.
- `docs/PRESENTATION.html`: Interaktywna prezentacja wizualna (gotowa do exportu do PDF).

## Jak uruchomić?

1. Przejdź do folderu `docker`:
   ```bash
   cd docker
   docker compose up --build
   ```

2. Dokumentacja API (Scalar) będzie dostępna pod adresem: `http://localhost:5501/scalar/v1`

3. Prezentacja Interaktywna (Guided Tour):
   ```bash
   ./cli.sh --action presentation
   ```

4. Tester CLI (interaktywny):
   ```bash
   ./cli.sh
   ```

5. Automatyczny test całego flow (Orchestration):
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
./cli.sh --action presentation      # interaktywny guided tour
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

**Pobranie statystyk autora (Multi-Stream Projection):**
```bash
curl http://localhost:5501/stats/authors/Szymon
```

**Rebuild projekcji (Admin):**
```bash
curl -X POST http://localhost:5501/admin/rebuild
```

## Multi-Stream Projection

`AuthorStats` to przykład `MultiStreamProjection<AuthorStats, string>` — jeden dokument per autor agregujący zdarzenia z **wielu niezależnych strumieni** (każdy post to osobny strumień).

```csharp
public class AuthorStatsProjection : MultiStreamProjection<AuthorStats, string>
{
    public AuthorStatsProjection()
    {
        // PostCreated niesie autora — bezpośredni routing
        Identity<PostCreated>(e => e.Author);

        // PostPublished nie zna autora — custom grouper odpytuje PostDetails
        CustomGrouping(new PostPublishedGrouper());
    }

    public AuthorStats Create(PostCreated e)
        => new() { Id = e.Author, TotalPosts = 1, PublishedPosts = 0 };

    public AuthorStats Apply(PostCreated e, AuthorStats stats)
    {
        stats.TotalPosts++;
        return stats;
    }

    public AuthorStats Apply(PostPublished e, AuthorStats stats)
    {
        stats.PublishedPosts++;
        return stats;
    }
}
```

**Kluczowe różnice vs `SingleStreamProjection`:**

| | `SingleStreamProjection` | `MultiStreamProjection` |
|---|---|---|
| Strumienie | 1 stream → 1 dokument | N streamów → 1 dokument |
| Klucz (ID) | Stream ID | Dowolna wartość z eventu |
| Przykład | `PostDetails` per post | `AuthorStats` per autor |
| Lifecycle | `Inline` (sync) | `Async` (daemon) |

Projekcja jest **Async** — przetwarza zdarzenia po commicie inline projekcji, dzięki czemu `PostPublishedGrouper` może odczytać `PostDetails` (który już zawiera autora).
