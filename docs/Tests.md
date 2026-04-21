# Testy — Marten Blog API

## Jak uruchomić

```bash
# Testy jednostkowe (szybkie, bez infrastruktury)
dotnet test src/Blog.Api.UnitTests/

# Testy integracyjne (wymagają Docker — Testcontainers uruchamia PostgreSQL automatycznie)
dotnet test src/Blog.Api.Tests/

# Wszystkie testy naraz
dotnet test Marten.sln

# Z logami
dotnet test Marten.sln --logger "console;verbosity=detailed"
```

---

## Testy jednostkowe — `Blog.Api.UnitTests`

**Projekt:** `src/Blog.Api.UnitTests/PostTests.cs`  
**Framework:** xUnit v3 + FluentAssertions  
**Infrastruktura:** brak (czyste testy domeny, zero I/O)

### Pokrycie: `Post` aggregate

| Test | Weryfikuje |
|------|------------|
| `CreateNew_Should_Return_Id_And_PostCreated_Event` | Fabryka tworzy ID i zdarzenie z poprawnymi danymi |
| `Apply_PostCreated_Should_Update_State` | `Apply(PostCreated)` ustawia wszystkie pola aggregate |
| `Publish_Should_Return_PostPublished_Event_When_Draft` | Publikacja draftu zwraca zdarzenie z poprawnym timestampem |
| `Publish_Should_Throw_When_Already_Published` | Podwójna publikacja rzuca `PostAlreadyPublishedException` |
| `Unpublish_Should_Return_PostUnpublished_Event_When_Published` | Cofnięcie publikacji zwraca zdarzenie z ID |
| `Unpublish_Should_Throw_When_Not_Published` | Cofnięcie draftu rzuca `InvalidOperationException` |
| `Update_Should_Return_PostUpdated_Event` | Update zwraca zdarzenie z nowym tytułem i treścią |
| `Apply_PostUpdated_Should_Update_Title_And_Content` | `Apply(PostUpdated)` mutuje właściwe pola |

---

## Testy integracyjne — `Blog.Api.Tests`

**Projekt:** `src/Blog.Api.Tests/BlogIntegrationTests.cs`  
**Framework:** xUnit + Alba + Testcontainers.PostgreSql + FluentAssertions  
**Infrastruktura:** Testcontainers uruchamia PostgreSQL w Dockerze automatycznie

> Projekcje w testach zarejestrowane jako `Inline` (zamiast `Async`) — brak potrzeby daemona.

### Pokrycie: pełny flow API + projekcje

| Test | Weryfikuje |
|------|------------|
| `Create_Post_Should_Return_Accepted` | `POST /posts` → 202 Accepted |
| `Get_Posts_Should_Return_Summary_List` | `GET /posts` → lista z `PostSummary` (SingleStreamProjection) |
| `Publish_Post_Should_Update_Status_And_Return_NoContent` | `POST /posts/{id}/publish` → 204 + `PostDetails.IsPublished = true` |
| `Publish_Already_Published_Post_Should_Return_409` | Podwójna publikacja → 409 Conflict |
| `Update_Post_Should_Return_NoContent` | `PUT /posts/{id}` → 204 + projekcja zaktualizowana |
| `Admin_Rebuild_Should_Return_Ok` | `POST /admin/rebuild` → 200 OK |
| `AuthorStats_Should_Aggregate_Posts_Across_Streams` | `GET /stats/authors/{autor}` → `AuthorStats.TotalPosts = 2` (MultiStreamProjection agreguje 2 niezależne streamy) |

---

## Architektura testów

```
Blog.Api.UnitTests/
└── PostTests.cs              ← testy domeny (aggregate + domain logic)

Blog.Api.Tests/
└── BlogIntegrationTests.cs   ← testy E2E (HTTP → Marten → PostgreSQL → projekcje)
```

### Dlaczego dwa projekty?

- **UnitTests** — testują logikę domenową izolowanie. Zero zależności zewnętrznych, uruchamiają się w milisekundach.
- **IntegrationTests** — testują cały stack: routing HTTP, handlery, Marten, PostgreSQL, projekcje inline. Wolniejsze (~20–30s ze startem kontenera), ale dają pewność że system działa end-to-end.

### Konfiguracja Testcontainers

Testy integracyjne automatycznie:
1. Uruchamiają kontener PostgreSQL (najnowszy oficjalny obraz)
2. Tworzą `AlbaHost` z aplikacją podłączoną do tego kontenera
3. Po zakończeniu zatrzymują i usuwają kontener

Nie wymaga żadnej lokalnej konfiguracji bazy danych.
