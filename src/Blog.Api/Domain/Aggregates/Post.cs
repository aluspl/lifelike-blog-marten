using Blog.Api.Domain.Events;
using Blog.Api.Domain.Exceptions;

namespace Blog.Api.Domain.Aggregates;

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

    // Static helper to create a new post
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
