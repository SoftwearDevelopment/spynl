"""
The about plugin is used to display meta data about the application, e.g.
database connection or build information.
"""
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.settings import asbool
from pyramid.security import Allow, Authenticated, DENY_ALL

from spynl.main.routing import Resource
from spynl.main.about.endpoints import (hello, versions, build, environment,
                                        endpoint_doc, schemas, ini)


class AboutResource(Resource):
    """The resource class for /about."""

    paths = ['about']

    __acl__ = [(Allow, 'role:sw-developer', 'read'),
               DENY_ALL]


class StaticResource(Resource):
    """The resource class for static assets. Open if you're authenticated."""

    __acl__ = [(Allow, Authenticated, 'read'), DENY_ALL]




def main(config):
    """doc, get, version, build, add endpoints."""
    settings = config.get_settings()

    config.add_static_view(name='static_swagger',
                           path='spynl.main:docs/swagger-ui/',
                           factory=StaticResource,
                           permission='read')
    config.add_static_view(name='static_docson',
                           path='spynl.main:docs/docson/',
                           permission='read')

    # check if we can use authentication for the more sensitive views
    permission = NO_PERMISSION_REQUIRED
    if asbool(settings.get('spynl.auth', True)):
        permission = 'read'
    else:
        permission = NO_PERMISSION_REQUIRED

    config.add_endpoint(hello, None, context=AboutResource,
                        permission=NO_PERMISSION_REQUIRED)
    config.add_endpoint(versions, 'versions', context=AboutResource,
                        permission=permission)
    config.add_endpoint(build, 'build', context=AboutResource,
                        permission=NO_PERMISSION_REQUIRED)
    config.add_endpoint(environment, 'environment', context=AboutResource,
                        permission=permission)
    config.add_endpoint(endpoint_doc, 'doc', context=AboutResource,
                        permission=Authenticated)  # TODO: deprecate
    config.add_endpoint(endpoint_doc, 'endpoints', context=AboutResource,
                        permission=Authenticated)
    config.add_endpoint(schemas, 'schemas', context=AboutResource,
                        permission=Authenticated)
    config.add_endpoint(ini, 'ini', context=AboutResource,
                        permission=permission)
