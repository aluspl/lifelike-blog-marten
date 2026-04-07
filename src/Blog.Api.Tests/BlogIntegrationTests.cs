using Alba;
using Blog.Api.Domain.Aggregates;
using Blog.Api.Domain.Commands;
using Blog.Api.Domain.Events;
using Blog.Api.Domain.Projections;
using Blog.Api.Domain.Queries;
using FluentAssertions;
using Microsoft.Extensions.DependencyInjection;
using Marten;
using Testcontainers.PostgreSql;
using Xunit;

namespace Blog.Api.Tests;

public class BlogIntegrationTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgresContainer = new PostgreSqlBuilder().Build();
    private IAlbaHost _host = null!;

    public async Task InitializeAsync()
    {
        await _postgresContainer.StartAsync();

        _host = await AlbaHost.For<Program>(builder =>
        {
            builder.ConfigureServices(services =>
            {
                services.AddMarten(options =>
                {
                    options.Connection(_postgresContainer.GetConnectionString() + ";Ssl Mode=Disable");
                    options.Projections.Add<PostDetailsProjection>(Marten.Events.Projections.ProjectionLifecycle.Inline);
                    options.Projections.Add<PostSummaryProjection>(Marten.Events.Projections.ProjectionLifecycle.Inline);
                }).UseLightweightSessions();
            });
        });
    }

    public async Task DisposeAsync()
    {
        await _host.DisposeAsync();
        await _postgresContainer.DisposeAsync();
    }

    [Fact]
    public async Task Create_Post_Should_Return_Accepted()
    {
        await _host.Scenario(s =>
        {
            s.Post.Json(new CreatePostCommand("New Post", "Content", "Author")).ToUrl("/posts");
            s.StatusCodeShouldBe(202);
        });
    }

    [Fact]
    public async Task Get_Posts_Should_Return_Summary_List()
    {
        // Arrange
        var store = _host.Services.GetRequiredService<IDocumentStore>();
        using var session = store.LightweightSession();
        var id = Guid.NewGuid();
        session.Events.StartStream<Post>(id, new PostCreated(id, "Title", "Content", "Author"));
        await session.SaveChangesAsync();

        // Act & Assert
        var result = await _host.Scenario(s =>
        {
            s.Get.Url("/posts");
            s.StatusCodeShouldBe(200);
        });

        var posts = result.ReadAsJson<IReadOnlyList<PostSummary>>();
        posts.Should().Contain(x => x.Id == id);
    }

    [Fact]
    public async Task Publish_Post_Should_Update_Status_And_Return_NoContent()
    {
        // Arrange
        var store = _host.Services.GetRequiredService<IDocumentStore>();
        using var session = store.LightweightSession();
        var id = Guid.NewGuid();
        session.Events.StartStream<Post>(id, new PostCreated(id, "Title", "Content", "Author"));
        await session.SaveChangesAsync();

        // Act
        await _host.Scenario(s =>
        {
            s.Post.Url($"/posts/{id}/publish");
            s.StatusCodeShouldBe(204);
        });

        // Assert
        using var query = store.QuerySession();
        var post = await query.LoadAsync<PostDetails>(id);
        post!.IsPublished.Should().BeTrue();
    }

    [Fact]
    public async Task Publish_Already_Published_Post_Should_Return_409()
    {
        // Arrange
        var store = _host.Services.GetRequiredService<IDocumentStore>();
        using var session = store.LightweightSession();
        var id = Guid.NewGuid();
        session.Events.StartStream<Post>(id, new PostCreated(id, "Title", "Content", "Author"), new PostPublished(id, DateTime.UtcNow));
        await session.SaveChangesAsync();

        // Act & Assert
        await _host.Scenario(s =>
        {
            s.Post.Url($"/posts/{id}/publish");
            s.StatusCodeShouldBe(409);
        });
    }

    [Fact]
    public async Task Update_Post_Should_Return_NoContent()
    {
        // Arrange
        var store = _host.Services.GetRequiredService<IDocumentStore>();
        using var session = store.LightweightSession();
        var id = Guid.NewGuid();
        session.Events.StartStream<Post>(id, new PostCreated(id, "Old Title", "Old Content", "Author"));
        await session.SaveChangesAsync();

        // Act
        await _host.Scenario(s =>
        {
            s.Put.Json(new UpdatePostCommand(id, "New Title", "New Content")).ToUrl($"/posts/{id}");
            s.StatusCodeShouldBe(204);
        });

        // Assert
        using var query = store.QuerySession();
        var post = await query.LoadAsync<PostDetails>(id);
        post!.Title.Should().Be("New Title");
    }

    [Fact]
    public async Task Admin_Rebuild_Should_Return_Ok()
    {
        await _host.Scenario(s =>
        {
            s.Post.Url("/admin/rebuild");
            s.StatusCodeShouldBe(200);
        });
    }
}
