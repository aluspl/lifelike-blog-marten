using Blog.Api.Domain;
using Blog.Api.Infrastructure;
using Marten;
using Microsoft.AspNetCore.Mvc;

var builder = WebApplication.CreateBuilder(args);

// --- Infrastructure (KISS & DRY) ---
builder.Services.AddMarten(options =>
{
    options.Connection(builder.Configuration.GetConnectionString("Postgres") ?? "Host=postgres;Database=marten;Username=postgres;Password=postgres");
    options.Projections.Add<PostDetailsProjection>(Marten.Events.Projections.ProjectionLifecycle.Inline);
}).UseLightweightSessions();

builder.Services.AddScoped<IMediator, SimpleMediator>();
builder.Services.AddMediatorHandlers(typeof(Program).Assembly);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
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

app.Run();

public partial class Program { }
