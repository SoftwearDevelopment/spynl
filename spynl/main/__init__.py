"""The main package of Spynl."""
import os

from pyramid.config import Configurator
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.viewderivers import INGRESS

from marshmallow import ValidationError

from spynl.main import serial, about, plugins, routing, events, endpoints, session

from spynl.main.utils import renderer_factory, check_origin, handle_pre_flight_request


from spynl.main.exceptions import SpynlException
from spynl.main.error_views import spynl_error, error400, error500, validation_error

from spynl.main.docs.documentation import make_docs
from spynl.main.docs.settings import check_required_settings
from spynl.main.dateutils import now
from spynl.main.locale import TemplateTranslations
from spynl.main.utils import add_jinja2_filters


class ConfigCommited(object):
    """ Event to signal that configurator finished and commited."""

    def __init__(self, config):
        self.config = config


def main(global_config, config=None, **settings):
    """
    Return a Pyramid WSGI application.

    Before that, we tell plugins how to add a view and tell views which
    renderer to use. And we take care of test settings. Then, we initialise the
    main plugins and the external plugins (which are not in this repository).
    """
    if config is None:
        config = Configurator(settings=settings)
        main_includeme(config)

    config.commit()
    config.registry.notify(ConfigCommited(config))

    return config.make_wsgi_app()


def main_includeme(config):
    config.add_settings({'spynl.ops.start_time': now()})

    # Add spynl.main's view derivers
    config.add_view_deriver(handle_pre_flight_request, under=INGRESS)
    config.add_view_deriver(check_origin)

    # initialize the main plugins
    # serial should be before plugins, because plugins can overwrite field
    # treatment
    # session needs to be after plugins, because plugins can set the session
    # mechanism
    routing.main(config)
    events.main(config)
    serial.main(config)
    endpoints.main(config)
    about.main(config)
    plugins.main(config)
    session.main(config)

    check_required_settings(config)

    # Custom renderer from main.serial or vanilla json renderer
    config.add_renderer('spynls-renderer', renderer_factory)

    config.add_translation_dirs('spynl.main:locale/')

    # Error views
    config.add_view(
        error400,
        context='pyramid.httpexceptions.HTTPError',
        renderer='spynls-renderer',
        is_error_view=True,
        permission=NO_PERMISSION_REQUIRED,
    )
    config.add_view(
        spynl_error,
        context=SpynlException,
        renderer='spynls-renderer',
        is_error_view=True,
        permission=NO_PERMISSION_REQUIRED,
    )
    config.add_view(
        error500,
        context=Exception,
        renderer='spynls-renderer',
        is_error_view=True,
        permission=NO_PERMISSION_REQUIRED,
    )
    config.add_view(
        validation_error,
        context=ValidationError,
        renderer='spynls-renderer',
        is_error_view=True,
        permission=NO_PERMISSION_REQUIRED,
    )

    # make spynl documentation
    if os.environ.get('GENERATE_SPYNL_DOCUMENTATION') == 'generate':
        make_docs(config)
        exit()

    # add jinja for templating
    config.include('pyramid_jinja2')
    config.add_settings({'jinja2.i18n.gettext': TemplateTranslations})
    config.add_settings({'jinja2.trim_blocks': 'true'})
    jinja_filters = {
        'static_url': 'pyramid_jinja2.filters:static_url_filter',
        'quoteplus': 'urllib.parse.quote_plus',
    }
    add_jinja2_filters(config, jinja_filters)
    return config
