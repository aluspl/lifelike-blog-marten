using Blog.Api.Domain;
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
    options.Projections.Add<PostDetailsProjection>(Marten.Events.Projections.ProjectionLifecycle.Inline);
    options.Projections.Add<PostSummaryProjection>(Marten.Events.Projections.ProjectionLifecycle.Inline);
}).UseLightweightSessions();

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
    catch (Blog.Api.Domain.PostAlreadyPublishedException ex)
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

posts.MapGet("/", async (IMediator m) => 
{
    return Results.Ok(await m.Query(new GetPostsQuery()));
});

// --- Admin Endpoints ---
var admin = app.MapGroup("/admin");

admin.MapPost("/rebuild", async (IDocumentStore store, CancellationToken ct) => 
{
    using var daemon = await store.BuildProjectionDaemonAsync();
    await daemon.RebuildProjection<PostDetails>(ct);
    await daemon.RebuildProjection<PostSummary>(ct);
    return Results.Ok(new { message = "Rebuild completed" });
});

app.Run();

public partial class Program { }
