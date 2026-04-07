using Blog.Api.Domain.Events;
using Marten.Events.Aggregation;

namespace Blog.Api.Domain.Projections;

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
