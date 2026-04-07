using Blog.Api.Domain.Aggregates;
using Blog.Api.Domain.Commands;
using Blog.Api.Domain.Projections;
using Blog.Api.Domain.Queries;
using Blog.Api.Infrastructure;
using Marten;

namespace Blog.Api.Domain.Handlers;

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
