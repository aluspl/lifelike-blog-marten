using Blog.Api.Domain.Aggregates;
using Blog.Api.Domain.Commands;
using Blog.Api.Domain.Exceptions;
using Blog.Api.Domain.Projections;
using Blog.Api.Domain.Queries;
using Blog.Api.Infrastructure;
using Marten;
using Microsoft.AspNetCore.Mvc;
using Scalar.AspNetCore;

var builder = WebApplication.CreateBuilder(args);

// --- Infrastructure (KISS & DRY) ---
builder.Services.AddOpenApi();
builder.Services.AddMarten(options =>
{
    options.Connection(builder.Configuration.GetConnectionString("Postgres") ?? "Host=postgres;Database=marten;Username=postgres;Password=postgres");
    options.Projections.Add<PostDetailsProjection>(JasperFx.Events.Projections.ProjectionLifecycle.Inline);
    options.Projections.Add<PostSummaryProjection>(JasperFx.Events.Projections.ProjectionLifecycle.Inline);
    // Async: przetwarza zdarzenia po commicie - custom grouper może odczytać PostDetails
    options.Projections.Add<AuthorStatsProjection>(JasperFx.Events.Projections.ProjectionLifecycle.Async);
})
.UseLightweightSessions()
.AddAsyncDaemon(JasperFx.Events.Daemon.DaemonMode.HotCold);

builder.Services.AddScoped<IMediator, SimpleMediator>();
builder.Services.AddMediatorHandlers(typeof(Program).Assembly);

builder.Services.AddEndpointsApiExplorer();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.MapScalarApiReference();
}

// --- Endpoints (SRP: Routing only) ---
var posts = app.MapGroup("/posts");

posts.MapPost("/", async (IMediator m, [FromBody] CreatePostCommand cmd) => 
{
    await m.Send(cmd);
    return Results.Accepted();
});

posts.MapPost("/{id:guid}/publish", async (IMediator m, Guid id) => 
{
    try
    {
        await m.Send(new PublishPostCommand(id));
        return Results.NoContent();
    }
    catch (PostAlreadyPublishedException ex)
    {
        // Return 409 Conflict for an already published post
        return Results.Conflict(new { error = ex.Message });
    }
    catch (InvalidOperationException ex) when (ex.Message.Contains("already published"))
    {
        // Fallback catch if the derived type is not correctly caught
        return Results.Conflict(new { error = ex.Message });
    }
});

posts.MapPost("/{id:guid}/unpublish", async (IMediator m, Guid id) => 
{
    try
    {
        await m.Send(new UnpublishPostCommand(id));
        return Results.NoContent();
    }
    catch (InvalidOperationException ex)
    {
        return Results.BadRequest(new { error = ex.Message });
    }
});

posts.MapPut("/{id:guid}", async (IMediator m, Guid id, [FromBody] UpdatePostCommand cmd) => 
{
    await m.Send(cmd with { Id = id });
    return Results.NoContent();
});

posts.MapGet("/{id:guid}", async (IMediator m, Guid id) => 
{
    var post = await m.Query(new GetPostQuery(id));
    return post is { } ? Results.Ok(post) : Results.NotFound();
});

posts.MapGet("/{id:guid}/events", async (IMediator m, Guid id) => 
{
    var events = await m.Query(new GetPostEventsQuery(id));
    return Results.Ok(events);
});

posts.MapGet("/", async (IMediator m) => Results.Ok((object?)await m.Query(new GetPostsQuery())));

// --- Stats Endpoints ---
var stats = app.MapGroup("/stats");

stats.MapGet("/authors/{author}", async (IMediator m, string author) =>
{
    var result = await m.Query(new GetAuthorStatsQuery(author));
    return result is { } ? Results.Ok(result) : Results.NotFound();
});

// --- Admin Endpoints ---
var admin = app.MapGroup("/admin");

admin.MapPost("/rebuild", async (IDocumentStore store, CancellationToken ct) =>
{
    using var daemon = await store.BuildProjectionDaemonAsync();
    await daemon.RebuildProjectionAsync<PostDetails>(ct);
    await daemon.RebuildProjectionAsync<PostSummary>(ct);
    await daemon.RebuildProjectionAsync<AuthorStats>(ct);
    return Results.Ok(new { message = "Rebuild completed" });
});

app.Run();

public partial class Program { }

