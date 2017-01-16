"""
Routing - make it possible to add endpoints and document them.
For endpoints that are based on resources, it is important
that the right path leads to the right resource being used
as context in the request.
Spynl allows each Resource being accessible with more than
paths (aliases). We use the URLDispatch feature of Pyramid
here, so we create routes for all possible cases.
"""


from collections import namedtuple

from pyramid.security import NO_PERMISSION_REQUIRED

from spynl.main.utils import get_logger, is_production_environment
from spynl.main.docs import document_endpoint


class Resource:
    """
    Spynl Resource class, which handles only a name property.

    Inherit from this class to produce a resource context
    for config.add_endpoint.
    """

    def __init__(self, request):
        """by accepting a request, this class is now a context factory"""
        pass

    paths = []
    """list here the URL paths under which the resource will be visible"""

    available_in_production = True
    """Set this to False if you want this resource to be seen in dev only"""

    @property
    def name(self):
        """
        This property is the name of the path under which Spynl uses this
        resource
        """
        return self.__class__.__name__.lower()


def add_resource(config, resource_class):
    """
    Add a resource which Spynl handles to a dict.
    Also add routes for this resource (for all its paths),
    such that the endpoints defined with it as context will
    work and that Spynl will use the resource's ACLs to
    authorise them.
    """
    logger = get_logger('spynl.main.routing')

    if not issubclass(resource_class, Resource):
        raise Exception("The resource cannot be added, as it is not a "
                        "subclass of spynl.main.routing.Resource")
    resource_name = resource_class.__name__
    resources = config.get_settings()['spynl.resources']

    added_paths = []
    if 'paths' in resource_class.__dict__:  # only add paths on this very class
        for path in resource_class.paths:
            added_paths.append(path)
            for ex_res in resources.values():  # check if other resources
                                               # claimed this path already
                if path in ex_res.paths:
                    logger.warn('Cannot add path "%s" for resource %s, as it'
                                ' was already added by resource %s!' %
                                (path, resource_name, ex_res.__name__))
                    added_paths.pop()
                    break
            if path in added_paths:
                route_info = config.get_settings()['spynl.resource_routes_info']
                for rpattern, route_info in route_info.items():
                    if issubclass(resource_class, route_info['resources']):
                        rf = route_info['route_factory']
                        rf(config,
                           route_name=rpattern.replace('{path}', path),
                           resource_class=resource_class, path=path)
                        logger.info("Adding routes for resource: '%s',"
                                    " path '%s', pattern '%s'",
                                    resource_name, path, rpattern)
    if len(added_paths) > 0:
        resources[resource_name] = resource_class


def add_resource_routes(config, route_name, resource_class, path):
    """
    Add routes to the config for a resource_class and path.
    We also add a route for no method passed.
    """
    config.add_route(name=route_name,
                     pattern='/%s/{method}' % path,
                     factory=resource_class)
    config.add_route(name=route_name + '.nomethod',
                     pattern='/%s' % path,
                     factory=resource_class)


def add_endpoint(config, func, endpoint_name,
                 permission=NO_PERMISSION_REQUIRED, context=None,
                 available_in_production=True, **kw):
    """
    Add an endpoint configuration.
    The context param is the resource class which will act as context
    factory in requests (we keep to the name "context" here, because
    it is being used as a keyword param in add_view).
    If None (not given), this view is basic, otherwise a resource-based
    endpoint. For a resource-based endpoint, the endpoint_name describes
    the method, but it can be empty or "/", meaning a default method
    is added (usually for GET and POST).
    All routes your endpoint should be applied to must be known at
    this point, so if a Spynl plugin adds a new route scheme, include
    (require) it before you add endpoints.
    """
    logger = get_logger('spynl.main.routing')
    if (is_production_environment(or_test=True)
            and not available_in_production):
        logger.warn("Skipping endpoint '%s' - should not be available in "
                    "production environments", endpoint_name)
        return
    if 'renderer' not in kw:
        kw['renderer'] = 'spynls-renderer'
    if context:  # This is a resource-based endpoint
        context_name = context.__name__
        if (is_production_environment(or_test=True)
                and not context.available_in_production):
            logger.warn("Not adding endpoint %s, as its resource (%s) is "
                        "not to be used in a production-like environment." %
                        (endpoint_name, context_name))
            return
        # add resource and routes if we haven't yet
        resources = config.get_settings()['spynl.resources']
        if not context_name in resources.keys():
            add_resource(config, context)
        # each resource should define their own paths
        if 'paths' not in context.__dict__.keys() or len(context.paths) == 0:
            logger.warn("Resource %s defines no paths, cannot add endpoint." %
                        context_name)
            return
        has_method = endpoint_name and endpoint_name != '/'
        match_param = has_method and "method={}".format(endpoint_name) or None
        for path in context.paths:
            rroutes = config.get_settings()['spynl.resource_routes_info']
            for route_name, rinfo in rroutes.items():
                if issubclass(context, rinfo['resources']):
                    route_name = route_name.replace('{path}', path)
                    if not has_method:
                        route_name = route_name + '.nomethod'
                    config.add_view(func, context=context,
                                    route_name=route_name,
                                    match_param=match_param,
                                    permission=permission, **kw)
                    logger.info("Added endpoint '%s' for route '%s', resource '%s'",
                                endpoint_name, route_name, context_name)
                    document_endpoint(config, func,
                                      has_method and path + '/' + endpoint_name\
                                          or endpoint_name,
                                      resource=path)
    else:  # This is a general endpoint without route
        logger.debug("Adding endpoint '%s'", endpoint_name)
        config.add_view(func, name=endpoint_name,
                        permission=permission,
                        **kw)
        document_endpoint(config, func, endpoint_name)



def main(config):
    """Define our list of resources and the means to add an endpoint."""
    resources = {}
    '''A dictionary of the resource classes Spynl serves with at least
       one endpoint. Keys are class names.'''
    config.add_settings({'spynl.resources': resources})
    resource_routes_info = {'spynl.{path}':
                            {'resources': (Resource,),
                             'route_factory': add_resource_routes}}
    '''This dict maps patterns of resource route names (with path
       being replacable) which are available to a factory function that
       adds these routes and a list of resource classes these routes
       should be created for. The function will receive config, route_name,
       resource_class and path parameters. This is extensible by other
       Spynl plugins. Our convention is that there is also a route
       pattern that ends with ".nomethod"'''
    config.add_settings({'spynl.resource_routes_info': resource_routes_info})

    config.add_directive('add_endpoint', add_endpoint)
