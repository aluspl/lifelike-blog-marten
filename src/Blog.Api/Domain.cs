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
public record PostUnpublished(Guid Id);
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

    public void Apply(PostUnpublished unpublished)
    {
        IsPublished = false;
        PublishedAt = null;
    }

    public void Apply(PostUpdated updated)
    {
        Title = updated.Title;
        Content = updated.Content;
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

    public PostUnpublished Unpublish()
    {
        if (!IsPublished) throw new InvalidOperationException("Post is not published.");
        return new PostUnpublished(Id);
    }

    public PostUpdated Update(string title, string content)
    {
        return new PostUpdated(Id, title, content);
    }
}

// --- 3. Projections (Read Model) ---
public record PostDetails(Guid Id, string Title, string Content, string Author, bool IsPublished, DateTime? PublishedAt);
public record PostSummary(Guid Id, string Title, string Author, bool IsPublished, DateTime? PublishedAt);

public class PostDetailsProjection : SingleStreamProjection<PostDetails>
{
    public PostDetails Create(PostCreated created) 
        => new(created.Id, created.Title, created.Content, created.Author, false, null);

    public PostDetails Apply(PostPublished published, PostDetails details)
        => details with { IsPublished = true, PublishedAt = published.PublishedAt };

    public PostDetails Apply(PostUnpublished unpublished, PostDetails details)
        => details with { IsPublished = false, PublishedAt = null };

    public PostDetails Apply(PostUpdated updated, PostDetails details)
        => details with { Title = updated.Title, Content = updated.Content };
}

public class PostSummaryProjection : SingleStreamProjection<PostSummary>
{
    public PostSummary Create(PostCreated created) 
        => new(created.Id, created.Title, created.Author, false, null);

    public PostSummary Apply(PostPublished published, PostSummary summary)
        => summary with { IsPublished = true, PublishedAt = published.PublishedAt };

    public PostSummary Apply(PostUnpublished unpublished, PostSummary summary)
        => summary with { IsPublished = false, PublishedAt = null };

    public PostSummary Apply(PostUpdated updated, PostSummary summary)
        => summary with { Title = updated.Title };
}

// --- 4. Commands (CQRS) ---
public record CreatePostCommand(string Title, string Content, string Author) : ICommand;
public record PublishPostCommand(Guid Id) : ICommand;
public record UnpublishPostCommand(Guid Id) : ICommand;
public record UpdatePostCommand(Guid Id, string Title, string Content) : ICommand;

// --- 5. Queries (CQRS) ---
public record GetPostQuery(Guid Id) : IQuery<PostDetails?>;
public record GetPostsQuery() : IQuery<IReadOnlyList<PostSummary>>;
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

public class UnpublishPostHandler : ICommandHandler<UnpublishPostCommand>
{
    private readonly IDocumentSession _session;
    public UnpublishPostHandler(IDocumentSession session) => _session = session;

    public async Task Handle(UnpublishPostCommand cmd, CancellationToken ct)
    {
        // Load the aggregate
        var post = await _session.Events.AggregateStreamAsync<Post>(cmd.Id, token: ct);
        if (post == null) throw new Exception("Post not found");

        // Use domain logic
        var @event = post.Unpublish();
        
        _session.Events.Append(cmd.Id, @event);
        await _session.SaveChangesAsync(ct);
    }
}

public class UpdatePostHandler : ICommandHandler<UpdatePostCommand>
{
    private readonly IDocumentSession _session;
    public UpdatePostHandler(IDocumentSession session) => _session = session;

    public async Task Handle(UpdatePostCommand cmd, CancellationToken ct)
    {
        // Load the aggregate
        var post = await _session.Events.AggregateStreamAsync<Post>(cmd.Id, token: ct);
        if (post == null) throw new Exception("Post not found");

        // Use domain logic
        var @event = post.Update(cmd.Title, cmd.Content);
        
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

public class GetPostsHandler : IQueryHandler<GetPostsQuery, IReadOnlyList<PostSummary>>
{
    private readonly IQuerySession _session;
    public GetPostsHandler(IQuerySession session) => _session = session;

    public async Task<IReadOnlyList<PostSummary>> Handle(GetPostsQuery query, CancellationToken ct)
    {
        return await _session.Query<PostSummary>().ToListAsync(ct);
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
