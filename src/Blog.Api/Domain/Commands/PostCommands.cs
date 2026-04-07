using Blog.Api.Infrastructure;

namespace Blog.Api.Domain.Commands;

public record CreatePostCommand(string Title, string Content, string Author) : ICommand;
public record PublishPostCommand(Guid Id) : ICommand;
public record UnpublishPostCommand(Guid Id) : ICommand;
public record UpdatePostCommand(Guid Id, string Title, string Content) : ICommand;
