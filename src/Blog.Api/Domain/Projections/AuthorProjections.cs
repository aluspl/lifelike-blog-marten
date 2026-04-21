using Blog.Api.Domain.Events;
using JasperFx.Events;
using JasperFx.Events.Grouping;
using Marten;
using Marten.Events.Aggregation;
using Marten.Events.Projections;

namespace Blog.Api.Domain.Projections;

// Multi-stream projection: aggreguje zdarzenia z WIELU strumieni (jeden per post)
// w jeden dokument per autor. Klucz to nazwa autora (string).
public class AuthorStats
{
    public string Id { get; set; } = default!;
    public int TotalPosts { get; set; }
    public int PublishedPosts { get; set; }
}

public class AuthorStatsProjection : MultiStreamProjection<AuthorStats, string>
{
    public AuthorStatsProjection()
    {
        // PostCreated niesie informację o autorze - routing jest bezpośredni
        Identity<PostCreated>(e => e.Author);

        // PostPublished nie zawiera autora - potrzebny custom grouper,
        // który odpyta PostDetails (inline projection) aby znaleźć autora
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

// Grupuje zdarzenia PostPublished do odpowiednich autorów poprzez lookup w PostDetails
public class PostPublishedGrouper : IJasperFxAggregateGrouper<string, IQuerySession>
{
    public async Task Group(IQuerySession session, IEnumerable<IEvent> events, IEventGrouping<string> grouping)
    {
        var published = events.OfType<IEvent<PostPublished>>().ToList();
        if (published.Count == 0) return;

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
