namespace Blog.Api.Infrastructure;

public interface ICommand : IRequest { }
public interface IQuery<out TResult> : IRequest<TResult> { }

public interface IRequest { }
public interface IRequest<out TResult> { }

public interface ICommandHandler<in TCommand> where TCommand : ICommand
{
    Task Handle(TCommand command, CancellationToken ct);
}

public interface IQueryHandler<in TQuery, TResult> where TQuery : IQuery<TResult>
{
    Task<TResult> Handle(TQuery query, CancellationToken ct);
}

public interface IMediator
{
    Task Send<TCommand>(TCommand command, CancellationToken ct = default) where TCommand : ICommand;
    Task<TResult> Query<TResult>(IQuery<TResult> query, CancellationToken ct = default);
}

public class SimpleMediator : IMediator
{
    private readonly IServiceProvider _serviceProvider;

    public SimpleMediator(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    public async Task Send<TCommand>(TCommand command, CancellationToken ct = default) where TCommand : ICommand
    {
        var handler = _serviceProvider.GetRequiredService<ICommandHandler<TCommand>>();
        await handler.Handle(command, ct);
    }

    public async Task<TResult> Query<TResult>(IQuery<TResult> query, CancellationToken ct = default)
    {
        var handlerType = typeof(IQueryHandler<,>).MakeGenericType(query.GetType(), typeof(TResult));
        var handler = _serviceProvider.GetRequiredService(handlerType);
        
        var method = handlerType.GetMethod("Handle");
        return await (Task<TResult>)method!.Invoke(handler, new object[] { query, ct })!;
    }
}
