using Blog.Api.Infrastructure;
using Marten;
using Marten.Events.Aggregation;

namespace Blog.Api.Domain;

// Domain-specific exceptions
public class PostAlreadyPublishedException : InvalidOperationException
{
    public PostAlreadyPublishedException(string? message = null) : base(message) { }
}

// --- 1. Events (Immutable facts) ---
public record PostCreated(Guid Id, string Title, string Content, string Author);
public record PostPublished(Guid Id, DateTime PublishedAt);
public record PostUpdated(Guid Id, string Title, string Content);

// --- 2. Aggregate Root (Domain Logic & Aggregation) ---
public class Post
{
    public Guid Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public string Author { get; set; } = string.Empty;
    public bool IsPublished { get; set; }
    public DateTime? PublishedAt { get; set; }

    // Aggregate Logic: How to apply events to the state
    public void Apply(PostCreated created)
    {
        Id = created.Id;
        Title = created.Title;
        Content = created.Content;
        Author = created.Author;
    }

    public void Apply(PostPublished published)
    {
        IsPublished = true;
        PublishedAt = published.PublishedAt;
    }

    // Static helper to create a new post (Renamed from Create to avoid Marten conflict)
    public static (Guid Id, PostCreated Event) CreateNew(string title, string content, string author)
    {
        var id = Guid.NewGuid();
        return (id, new PostCreated(id, title, content, author));
    }

    // Domain behavior
    public PostPublished Publish()
    {
        if (IsPublished) throw new PostAlreadyPublishedException("Post is already published.");
        return new PostPublished(Id, DateTime.UtcNow);
    }
}

// --- 3. Projections (Read Model) ---
public record PostDetails(Guid Id, string Title, string Content, string Author, bool IsPublished, DateTime? PublishedAt);

public class PostDetailsProjection : SingleStreamProjection<PostDetails>
{
    public PostDetails Create(PostCreated created) 
        => new(created.Id, created.Title, created.Content, created.Author, false, null);

    public PostDetails Apply(PostPublished published, PostDetails details)
        => details with { IsPublished = true, PublishedAt = published.PublishedAt };
}

// --- 4. Commands (CQRS) ---
public record CreatePostCommand(string Title, string Content, string Author) : ICommand;
public record PublishPostCommand(Guid Id) : ICommand;

// --- 5. Queries (CQRS) ---
public record GetPostQuery(Guid Id) : IQuery<PostDetails?>;
public record GetPostsQuery() : IQuery<IReadOnlyList<PostDetails>>;
public record GetPostEventsQuery(Guid Id) : IQuery<IReadOnlyList<PostEventInfo>>;

public record PostEventInfo(long Version, DateTimeOffset Timestamp, string EventType, object Data);

// --- 6. Handlers (Mediator Implementation) ---
public class CreatePostHandler : ICommandHandler<CreatePostCommand>
{
    private readonly IDocumentSession _session;
    public CreatePostHandler(IDocumentSession session) => _session = session;

    public async Task Handle(CreatePostCommand cmd, CancellationToken ct)
    {
        var (id, @event) = Post.CreateNew(cmd.Title, cmd.Content, cmd.Author);
        _session.Events.StartStream<Post>(id, @event);
        await _session.SaveChangesAsync(ct);
    }
}

public class PublishPostHandler : ICommandHandler<PublishPostCommand>
{
    private readonly IDocumentSession _session;
    public PublishPostHandler(IDocumentSession session) => _session = session;

    public async Task Handle(PublishPostCommand cmd, CancellationToken ct)
    {
        // Load the aggregate
        var post = await _session.Events.AggregateStreamAsync<Post>(cmd.Id, token: ct);
        if (post == null) throw new Exception("Post not found");

        // Use domain logic
        var @event = post.Publish();
        
        _session.Events.Append(cmd.Id, @event);
        await _session.SaveChangesAsync(ct);
    }
}

public class GetPostHandler : IQueryHandler<GetPostQuery, PostDetails?>
{
    private readonly IQuerySession _session;
    public GetPostHandler(IQuerySession session) => _session = session;

    public async Task<PostDetails?> Handle(GetPostQuery query, CancellationToken ct)
        => await _session.LoadAsync<PostDetails>(query.Id, ct);
}

public class GetPostsHandler : IQueryHandler<GetPostsQuery, IReadOnlyList<PostDetails>>
{
    private readonly IQuerySession _session;
    public GetPostsHandler(IQuerySession session) => _session = session;

    public async Task<IReadOnlyList<PostDetails>> Handle(GetPostsQuery query, CancellationToken ct)
    {
        return await _session.Query<PostDetails>().ToListAsync(ct);
    }
}

public class GetPostEventsHandler : IQueryHandler<GetPostEventsQuery, IReadOnlyList<PostEventInfo>>
{
    private readonly IQuerySession _session;
    public GetPostEventsHandler(IQuerySession session) => _session = session;

    public async Task<IReadOnlyList<PostEventInfo>> Handle(GetPostEventsQuery query, CancellationToken ct)
    {
        var events = await _session.Events.FetchStreamAsync(query.Id, token: ct);
        return events.Select(e => new PostEventInfo(
            e.Version,
            e.Timestamp,
            e.EventTypeName,
            e.Data
        )).ToList().AsReadOnly();
    }
}
