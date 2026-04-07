using Alba;
using Blog.Api.Domain;
using FluentAssertions;
using Microsoft.Extensions.DependencyInjection;
using Marten;
using Testcontainers.PostgreSql;

namespace Blog.Api.Tests;

public class BlogIntegrationTests : IAsyncLifetime
{
    private IAlbaHost _host = null!;
    private readonly PostgreSqlContainer _postgresContainer = new PostgreSqlBuilder()
        .WithImage("postgres:16")
        .Build();

    public async Task InitializeAsync()
    {
        await _postgresContainer.StartAsync();

        _host = await AlbaHost.For<Program>(builder =>
        {
            builder.ConfigureServices(services =>
            {
                services.AddMarten(options =>
                {
                    options.Connection(_postgresContainer.GetConnectionString());
                    options.Projections.Add<PostDetailsProjection>(Marten.Events.Projections.ProjectionLifecycle.Inline);
                    options.Projections.Add<PostSummaryProjection>(Marten.Events.Projections.ProjectionLifecycle.Inline);
                }).UseLightweightSessions();
            });
        });
    }

    public async Task DisposeAsync()
    {
        await _host.DisposeAsync();
        await _postgresContainer.StopAsync();
    }

    [Fact]
    public async Task Should_Create_And_Publish_Post()
    {
        var command = new CreatePostCommand("Testcontainers Post", "Content", "Author");

        // 1. Create Post
        await _host.Scenario(s =>
        {
            s.Post.Json(command).ToUrl("/posts");
            s.StatusCodeShouldBe(202);
        });

        // 2. Verify in Read Model
        var store = _host.Services.GetRequiredService<IDocumentStore>();
        using var session = store.QuerySession();
        
        var post = await session.Query<PostDetails>().FirstOrDefaultAsync(x => x.Title == "Testcontainers Post");
        
        post.Should().NotBeNull();
        post!.IsPublished.Should().BeFalse();

        // 3. Publish Post
        await _host.Scenario(s =>
        {
            s.Post.Url($"/posts/{post.Id}/publish");
            s.StatusCodeShouldBe(204);
        });

        // 3b. Publishing again should yield 409 Conflict
        await _host.Scenario(s =>
        {
            s.Post.Url($"/posts/{post.Id}/publish");
            s.StatusCodeShouldBe(409);
        });

        // 4. Verify Final State
        using var session2 = store.QuerySession();
        var publishedPost = await session2.LoadAsync<PostDetails>(post.Id);
        publishedPost!.IsPublished.Should().BeTrue();

        // 5. Verify Summary List
        await _host.Scenario(s =>
        {
            s.Get.Url("/posts");
            s.StatusCodeShouldBe(200);
        });

        var summaries = await session2.Query<PostSummary>().ToListAsync();
        summaries.Should().Contain(x => x.Id == post.Id && x.IsPublished);

        // 6. Test Update
        await _host.Scenario(s =>
        {
            s.Put.Json(new UpdatePostCommand(post.Id, "Updated Title", "Updated Content")).ToUrl($"/posts/{post.Id}");
            s.StatusCodeShouldBe(204);
        });

        using var sessionUpdate = store.QuerySession();
        var updatedPost = await sessionUpdate.LoadAsync<PostDetails>(post.Id);
        updatedPost!.Title.Should().Be("Updated Title");
        updatedPost.Content.Should().Be("Updated Content");

        // 7. Test Admin Rebuild
        await _host.Scenario(s =>
        {
            s.Post.Url("/admin/rebuild");
            s.StatusCodeShouldBe(200);
        });

        // 8. Test Unpublish
        await _host.Scenario(s =>
        {
            s.Post.Url($"/posts/{post.Id}/unpublish");
            s.StatusCodeShouldBe(204);
        });

        using var session3 = store.QuerySession();
        var unpublishedPost = await session3.LoadAsync<PostDetails>(post.Id);
        unpublishedPost!.IsPublished.Should().BeFalse();
        unpublishedPost.PublishedAt.Should().BeNull();
    }
}
