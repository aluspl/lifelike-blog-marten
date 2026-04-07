namespace Blog.Api.Domain.Exceptions;

public class PostAlreadyPublishedException : InvalidOperationException
{
    public PostAlreadyPublishedException(string? message = null) : base(message) { }
}
