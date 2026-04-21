using Blog.Api.Domain.Projections;
using Blog.Api.Infrastructure;

namespace Blog.Api.Domain.Queries;

public record GetPostQuery(Guid Id) : IQuery<PostDetails?>;
public record GetPostsQuery() : IQuery<IReadOnlyList<PostSummary>>;
public record GetPostEventsQuery(Guid Id) : IQuery<IReadOnlyList<PostEventInfo>>;
public record GetAuthorStatsQuery(string Author) : IQuery<AuthorStats?>;

public record PostEventInfo(long Version, DateTimeOffset Timestamp, string EventType, object Data);
