# Marten Blog API - Prezentacja Event Sourcing

Witaj w prezentacji systemu blogowego opartego na bibliotece **Marten** (Event Store dla .NET) oraz architekturze **Event Sourcing**.

## Czym jest Event Sourcing?

W tradycyjnych systemach zapisujemy "aktualny stan" obiektu (np. `IsPublished = true`). W Event Sourcingu zapisujemy **historię zmian** (zdarzenia), które doprowadziły do tego stanu.

**Zalety:**
- Pełny audyt (wiemy co, kto i kiedy zmienił).
- Możliwość odtworzenia stanu z dowolnego punktu w czasie.
- Elastyczność: możemy tworzyć nowe widoki danych (projekcje) na podstawie starych zdarzeń.

---

## Scenariusz Demo

Możesz przejść ten scenariusz interaktywnie, uruchamiając:
```bash
./cli.sh --action presentation
```

### Krok 1: Narodziny zdarzenia (`PostCreated`)
Zdarzenia domenowe to **fakty**, które miały miejsce w systemie. Są niemutowalne i zapisywane w formacie JSON.

```csharp
// Definicja zdarzenia w C#
public record PostCreated(Guid Id, string Title, string Content, string Author);
```

**Baza danych (tabela `mt_events`):**
Marten zapisuje to zdarzenie przypisując mu `stream_id` (ID posta) oraz `version` (v1).

### Krok 2: Mechanizm Projekcji
Projekcja to proces przekształcania strumienia zdarzeń w aktualny stan (Read Model). W tym projekcie stosujemy **SingleStreamProjection**, co pozwala na automatyczne budowanie stanu z jednego strumienia.

```csharp
public class PostDetailsProjection : SingleStreamProjection<PostDetails>
{
    // Tworzy początkowy stan z pierwszego zdarzenia
    public PostDetails Create(PostCreated created) 
        => new(created.Id, created.Title, created.Content, created.Author, false, null);

    // Aktualizuje istniejący stan o kolejne zdarzenia
    public PostDetails Apply(PostUpdated updated, PostDetails details)
        => details with { Title = updated.Title, Content = updated.Content };
}
```

### Krok 3: Ewolucja (Update & Publish)
Każda kolejna zmiana to nowe zdarzenie. 
- Zmiana tytułu? -> `PostUpdated` (wersja v2)
- Publikacja? -> `PostPublished` (wersja v3)

Dzięki temu mamy pełny **Audit Log** – wiemy nie tylko jaki jest tytuł, ale też jaki był wcześniej.


### Krok 4: Source of Truth
Jeśli pobierzemy post przez API (`GET /posts/{id}`), Marten zwróci nam zmergowany stan z projekcji. Jeśli jednak zapytamy o historię (`GET /posts/{id}/events`), zobaczymy czystą prawdę o tym, jak ten obiekt ewoluował.

### Krok 5: Magia Rebuildingu
... (istniejąca treść) ...

---

## Poza SingleStreamProjection: Alternatywy w Marten

`SingleStreamProjection<T>` (użyta w tym projekcie) to tylko wierzchołek góry lodowej. Marten oferuje znacznie więcej:

### 1. MultiStreamProjection — zaimplementowana w projekcie!

`MultiStreamProjection<TDoc, TId>` agreguje zdarzenia z **wielu niezależnych strumieni** w jeden dokument per klucz.

**Nasz przykład: `AuthorStats`** — statystyki per autor, gdzie każdy post to osobny stream.

```
Stream post-1 → PostCreated(Author: "Szymon") ──┐
Stream post-2 → PostCreated(Author: "Szymon") ──┼──► AuthorStats { Id: "Szymon", TotalPosts: 3, PublishedPosts: 1 }
Stream post-3 → PostPublished(Id: post-3)    ───┘
```

**Kod projekcji:**
```csharp
public class AuthorStatsProjection : MultiStreamProjection<AuthorStats, string>
{
    public AuthorStatsProjection()
    {
        // PostCreated niesie autora — bezpośredni routing po polu Author
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

**Custom Grouper** — bo `PostPublished` nie zawiera autora:
```csharp
public class PostPublishedGrouper : IAggregateGrouper<string>
{
    public async Task Group(IQuerySession session, IEnumerable<IEvent> events, ITenantSliceGroup<string> grouping)
    {
        var published = events.OfType<IEvent<PostPublished>>().ToList();
        if (published.Count == 0) return;

        // Lookup autora przez istniejącą projekcję PostDetails (inline, już scommitowana)
        var ids = published.Select(e => e.Data.Id).ToList();
        var posts = await session.Query<PostDetails>()
            .Where(p => ids.Contains(p.Id))
            .Select(p => new { p.Id, p.Author })
            .ToListAsync();

        var authorById = posts.ToDictionary(p => p.Id, p => p.Author);
        foreach (var @event in published)
            if (authorById.TryGetValue(@event.Data.Id, out var author))
                grouping.AddEvents(author, [@event]);
    }
}
```

**Lifecycle Async** — klucz do poprawności:
```csharp
// Inline: przetwarza synchronicznie, razem z zapisem zdarzeń
options.Projections.Add<PostDetailsProjection>(ProjectionLifecycle.Inline);

// Async: przetwarza PO commicie — PostDetails jest już dostępna dla groupera!
options.Projections.Add<AuthorStatsProjection>(ProjectionLifecycle.Async);

// Daemon musi być uruchomiony aby Async projekcje działały
.AddAsyncDaemon(DaemonMode.HotCold);
```

**Endpoint:** `GET /stats/authors/{author}` zwraca `AuthorStats`.

### 2. Flat Table Projections (Projekcje do Entity/SQL)
Marten domyślnie zapisuje projekcje jako JSONB. Możesz jednak rzutować zdarzenia bezpośrednio na **płaskie tabele SQL**:
- Każde pole zdarzenia trafia do oddzielnej kolumny.
- Idealne pod raportowanie SQL, PowerBI lub integrację ze starymi systemami.

### 3. Custom IProjection
Jeśli potrzebujesz pełnej kontroli, możesz zaimplementować interfejs `IProjection`. Pozwala on na:
- Wykonywanie dowolnego kodu przy zdarzeniu.
- Integrację z zewnętrznymi usługami (np. wysyłka powiadomienia Push).
- Skomplikowaną logikę biznesową, która nie mieści się w prostym `Apply`.

### 4. Event Projections
Pozwalają na transformację zdarzeń "w locie" na inne zdarzenia lub obiekty, zanim trafią do bazy.

---

## Gdzie szukać kodu?
- **Agregat i logika**: `src/Blog.Api/Domain/Aggregates/Post.cs`
- **Definicje zdarzeń**: `src/Blog.Api/Domain/Events/PostEvents.cs`
- **Definicje projekcji**: `src/Blog.Api/Domain/Projections/PostProjections.cs`
- **Konfiguracja Marten**: `src/Blog.Api/Program.cs`
