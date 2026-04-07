namespace Blog.Api.Domain.Events;

public record PostCreated(Guid Id, string Title, string Content, string Author);
public record PostPublished(Guid Id, DateTime PublishedAt);
public record PostUnpublished(Guid Id);
public record PostUpdated(Guid Id, string Title, string Content);
