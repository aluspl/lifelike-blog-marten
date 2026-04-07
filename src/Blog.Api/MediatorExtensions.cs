using System.Reflection;

namespace Blog.Api.Infrastructure;

public static class MediatorExtensions
{
    public static IServiceCollection AddMediatorHandlers(this IServiceCollection services, Assembly assembly)
    {
        var types = assembly.GetTypes()
            .Where(t => !t.IsAbstract && !t.IsInterface);

        foreach (var type in types)
        {
            // Register Command Handlers
            var commandInterfaces = type.GetInterfaces()
                .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(ICommandHandler<>));
            
            foreach (var @interface in commandInterfaces)
                services.AddScoped(@interface, type);

            // Register Query Handlers
            var queryInterfaces = type.GetInterfaces()
                .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IQueryHandler<,>));
            
            foreach (var @interface in queryInterfaces)
                services.AddScoped(@interface, type);
        }

        return services;
    }
}
