using Blog.Api.Domain.Aggregates;
using Blog.Api.Domain.Events;
using Blog.Api.Domain.Exceptions;
using FluentAssertions;
using Xunit;

namespace Blog.Api.UnitTests;

public class PostTests
{
    [Fact]
    public void CreateNew_Should_Return_Id_And_PostCreated_Event()
    {
        // Act
        var (id, @event) = Post.CreateNew("Title", "Content", "Author");

        // Assert
        id.Should().NotBeEmpty();
        @event.Id.Should().Be(id);
        @event.Title.Should().Be("Title");
        @event.Content.Should().Be("Content");
        @event.Author.Should().Be("Author");
    }

    [Fact]
    public void Apply_PostCreated_Should_Update_State()
    {
        // Arrange
        var post = new Post();
        var id = Guid.NewGuid();
        var @event = new PostCreated(id, "Title", "Content", "Author");

        // Act
        post.Apply(@event);

        // Assert
        post.Id.Should().Be(id);
        post.Title.Should().Be("Title");
        post.Content.Should().Be("Content");
        post.Author.Should().Be("Author");
        post.IsPublished.Should().BeFalse();
    }

    [Fact]
    public void Publish_Should_Return_PostPublished_Event_When_Draft()
    {
        // Arrange
        var post = new Post { Id = Guid.NewGuid(), IsPublished = false };

        // Act
        var @event = post.Publish();

        // Assert
        @event.Id.Should().Be(post.Id);
        @event.PublishedAt.Should().BeCloseTo(DateTime.UtcNow, TimeSpan.FromSeconds(1));
    }

    [Fact]
    public void Publish_Should_Throw_When_Already_Published()
    {
        // Arrange
        var post = new Post { IsPublished = true };

        // Act
        var act = () => post.Publish();

        // Assert
        act.Should().Throw<PostAlreadyPublishedException>();
    }

    [Fact]
    public void Unpublish_Should_Return_PostUnpublished_Event_When_Published()
    {
        // Arrange
        var post = new Post { Id = Guid.NewGuid(), IsPublished = true };

        // Act
        var @event = post.Unpublish();

        // Assert
        @event.Id.Should().Be(post.Id);
    }

    [Fact]
    public void Unpublish_Should_Throw_When_Not_Published()
    {
        // Arrange
        var post = new Post { IsPublished = false };

        // Act
        var act = () => post.Unpublish();

        // Assert
        act.Should().Throw<InvalidOperationException>().WithMessage("Post is not published.");
    }

    [Fact]
    public void Update_Should_Return_PostUpdated_Event()
    {
        // Arrange
        var post = new Post { Id = Guid.NewGuid() };

        // Act
        var @event = post.Update("New Title", "New Content");

        // Assert
        @event.Id.Should().Be(post.Id);
        @event.Title.Should().Be("New Title");
        @event.Content.Should().Be("New Content");
    }

    [Fact]
    public void Apply_PostUpdated_Should_Update_Title_And_Content()
    {
        // Arrange
        var post = new Post { Title = "Old", Content = "Old" };
        var @event = new PostUpdated(Guid.NewGuid(), "New", "New");

        // Act
        post.Apply(@event);

        // Assert
        post.Title.Should().Be("New");
        post.Content.Should().Be("New");
    }
}
