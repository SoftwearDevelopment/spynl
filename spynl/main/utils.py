"""Helper functions and view derivers for spynl.main."""


import json
import logging
import traceback
import sys
import os
import contextlib
from functools import wraps
from inspect import isclass, getfullargspec
import yaml
from tld import get_tld
from tld.exceptions import TldBadUrl, TldDomainNotFound

from pyramid.response import Response
from pyramid.renderers import json_renderer_factory
from pyramid.exceptions import Forbidden
from pyramid import threadlocal
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound

from spynl.main import urlson
from spynl.main.exceptions import SpynlException, MissingParameter, BadOrigin
from spynl.main.version import __version__ as spynl_version
from spynl.main.locale import SpynlTranslationString as _


def get_request():
    """
    Retrieve current request.

    Use with care, though:
    http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/threadlocals.html
    """
    return threadlocal.get_current_request()


def get_settings(setting=None):
    """
    Get settings (from .ini file [app:main] section)

    If setting is given, get its value from the application settings and return it.
    Can also be accessed from the request object: request.registry.settings
    For more info on the way we do it here, consult
    http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/threadlocals.html
    Our policy is to not edit the settings during a request/response cycle.
    """
    registry_settings = threadlocal.get_current_registry().settings or {}
    if setting is not None:
        return registry_settings.get(setting)
    return registry_settings


def check_origin(endpoint, info):
    """Check if origin is allowed"""

    def wrapper_view(context, request):
        """raise HTTPForbidden if origin isn't allowed"""
        origin = request.headers.get('Origin', '')
        if not is_origin_allowed(origin):
            # because this is a wrapper, the bad origin will not be properly
            # escalated to forbidden, so it needs to be done like this.
            raise Forbidden(
                detail=BadOrigin(origin).message.translate(request.localizer)
            )
        return endpoint(context, request)

    return wrapper_view


# NOTE this has NOTHING to do with the check options view deriver. But we
# need to register it somewhere.
check_origin.options = ('is_error_view',)


def validate_locale(locale):
    """Validate a locale against our supported languages."""
    supported_languages = [
        lang.strip().lower()
        for lang in get_settings().get('spynl.languages', 'en').split(',')
    ]
    language = None

    if not locale:
        return

    # we're only looking for languages here, not dialects.
    language = str(locale)[:2].lower()
    if language in supported_languages:
        return language


def handle_pre_flight_request(endpoint, info):
    """
    "pre-flight-request": return custom response with some information on
    what we allow. Used by browsers before they send XMLHttpRequests.
    """

    def wrapper(context, request):
        """Call the endpoint if not an OPTION (pre-flight) request,
        otherwise return a custom Response."""
        if request.method != 'OPTIONS':
            return endpoint(context, request)
        else:
            headerlist = []
            origin = request.headers.get('Origin')
            if origin:  # otherwise we are on localhost or are called directly
                if is_origin_allowed(origin):
                    headerlist.append(('Access-Control-Allow-Origin', origin))
                else:
                    headerlist.append(('Access-Control-Allow-Origin', 'null'))
            headerlist.extend(
                [
                    ('Access-Control-Allow-Methods', 'GET,POST'),
                    ('Access-Control-Max-Age', '86400'),
                    ('Access-Control-Allow-Credentials', 'true'),
                    ('Content-Length', '0'),
                    ('Content-Type', 'text/plain'),
                ]
            )
            # you can send any headers to Spynl, basically
            if 'Access-Control-Request-Headers' in request.headers:
                headerlist.append(
                    (
                        'Access-Control-Allow-Headers',
                        request.headers['Access-Control-Request-Headers'],
                    )
                )
            # returning a generic and resource-agnostic pre-flight response
            return Response(headerlist=headerlist)

    return wrapper


def is_origin_allowed(origin):
    """
    Check request origin for matching our whitelists.
    First tries dev whitelists (that list is expected to hold
    either complete URLs or mere protocols, e.g. "chrome-extension://").
    Then the tld whitelist is tried, which is expected to hold
    only the top-level domains.
    Returns True if origin is allowed, False otherwise.
    """
    if not origin:
        return True

    settings = get_settings()
    dev_whitelist = parse_csv_list(settings.get('spynl.dev_origin_whitelist', ''))
    dev_list_urls = [url for url in dev_whitelist if not url.endswith('://')]
    origin_allowed = origin in dev_list_urls
    dev_list_protocols = [url for url in dev_whitelist if url.endswith('://')]
    for protocol in dev_list_protocols:
        if origin.startswith(protocol):
            origin_allowed = True
    if not origin_allowed:
        try:
            tld = get_tld(origin)
        except (TldBadUrl, TldDomainNotFound):
            tld = origin  # dev domains like e.g. 0.0.0.0:9000 will fall here
        tld_whitelist = parse_csv_list(settings.get('spynl.tld_origin_whitelist', ''))
        if tld in tld_whitelist:
            origin_allowed = True
    return origin_allowed


def get_header_args(request):
    """Return a dictionary with arguments passed as headers."""
    # these require a spynl-specific prefix to be recognized
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower().startswith('x-spynl-')
    }
    # We might also get the session id and client IP address with the headers
    for key in request.headers.keys():
        if key.lower() == 'sid':
            headers['sid'] = request.headers[key]
        if key == 'X-Forwarded-For':
            headers['X-Forwarded-For'] = request.headers[key]

    return headers


def get_parsed_body(request):
    """Return the body of the request parsed if request was POST or PUT."""
    settings = get_settings()
    body_parser = settings.get('spynl.post_parser')

    if request.method in ('POST', 'PUT'):
        if body_parser:
            request.parsed_body = body_parser(request)
        else:
            request.parsed_body = {} if not request.body else json.loads(request.body)
    else:
        # disregard any body content if not a POST of PUT request
        request.parsed_body = {}

    return request.parsed_body


def unify_args(request):
    """
    Make one giant args dictonary from GET, POST, headers and cookies and
    return it. On the way, create r.parsed_body and r.parsed_get as well.

    It is possible to provide a custom parser for the POST body in the
    settings. Complex data can be given via GET as a JSON string.
    GET would overwrite POST when parameter names collide.
    """
    args = {}
    # get headers first, they might be useful for parsing the body
    args.update(get_header_args(request))
    # get POST data
    args.update(get_parsed_body(request))
    # get GET args, can be written in JSON style
    # args.update(urlson.loads_dict(request.GET))
    # TODO: needs some refactoring - maybe urlson can actually do this parsing
    # for us. We don't know the context yet.
    from spynl.main.serial import objects

    context = hasattr(request, 'context') and request.context or None
    args.update(
        json.loads(
            json.dumps(urlson.loads_dict(request.GET)),
            object_hook=objects.SpynlDecoder(context=context),
        )
    )

    request.endpoint_method = find_view_name(request)

    # get cookies, but do not overwrite explicitly given settings
    for key in request.cookies:
        if key not in args:
            args[key] = request.cookies[key]

    # we actually want the sid to live as a header from here on out.
    # It can come in other ways as well (e.g. in GET) for convenience,
    # but we agree for it to live in one place.
    if args.get('sid'):
        request.headers['sid'] = args['sid']
        del args['sid']

    return args


def find_view_name(request):
    """find the view name
    TODO: I believe this is not completely generic.
    """
    name = None

    if request.matchdict and 'method' in request.matchdict:  # a route was matched
        name = request.matchdict['method']
    else:
        name = request.path_info
    if name.startswith('/'):
        name = name[1:]

    if hasattr(request, 'matched_route') and request.matched_route:
        if name in request.matched_route.name:
            # method  name was not in the URL
            if request.method == 'POST':
                name = 'edit'
            elif request.method == 'GET':
                name = 'get'

    return name


def get_user_info(request, purpose=None):
    """
    Spynl.main has no user model. This function allows the use of a
    user_info function defined in a plugin, by setting it to the
    'user_info' setting in the plugger.py of the plugin. If no
    other function is defined, it uses _user_info instead.
    The user_info function should return a dictionary with
    information about the (authenticated) user. If no information is
    available it should return an empty dictionary.
    """
    try:
        return request.registry.settings['user_info_function'](request, purpose)
    except (KeyError, AttributeError, TypeError):
        return _get_user_info(request)


def _get_user_info(request):
    """
    Function to get user information as a dictionary. In spynl.main the
    only user information we can get is the ip address.
    """
    ipaddress = get_user_ip(request)
    return dict(ipaddress=ipaddress)


def get_user_ip(request):
    """ Get the ipaddress of the user """
    ipaddress = request.environ.get('REMOTE_ADDR', None)
    # Load balancers overwrite ipaddress,
    # so we prefer the forward header EBS sets
    if 'X-Forwarded-For' in request.headers.keys():
        ipaddress = request.headers['X-Forwarded-For']
    return ipaddress


def get_err_source(original_traceback=None):
    """Use this when an error is handled to get info on where it occured"""
    try:  # carefully try to get the actual place where the error happened
        if not original_traceback:
            original_traceback = sys.exc_info()[2]  # class, exc, traceback
        first_call = traceback.extract_tb(original_traceback)[-1]
        return dict(
            module=first_call[0],
            linenr=first_call[1],
            method=first_call[2],
            src_code=first_call[3],
        )
    except Exception:
        return 'I was unable to retrieve error source information.'


def renderer_factory(info):
    """
    Normally responses are rendered as bare JSON, but this factory will look
    into the settings for other requested renderers first.
    """
    if hasattr(info, 'settings'):
        settings = info.settings
    if settings and 'spynl.renderer' in settings:
        return settings['spynl.renderer']
    return json_renderer_factory(None)


def get_logger(name=None):
    """Return the Logger object with the given name."""
    if not name:
        name = __name__

    return logging.getLogger(name)


def parse_value(value, class_info):
    '''
    Parse a value. class_info is expected to be a class or a list
    of classes to try in order.
    Raises SpynlException exception if no parsing was possible.
    '''
    if isclass(class_info):
        try:
            return class_info(value)
        except Exception:
            raise SpynlException(
                _(
                    'parse-value-exception-as-class',
                    mapping={'value': value, 'class': class_info.__name__},
                )
            )

    if hasattr(class_info, '__iter__'):
        for cl in class_info:
            if not isclass(cl):
                raise SpynlException(
                    _(
                        'parse-value-exception-not-class',
                        mapping={'class': cl, 'value': value},
                    )
                )
            try:
                return cl(value)
            except Exception:
                pass
    raise SpynlException(
        _(
            'parse-value-exception-any-class',
            mapping={'value': value, 'classes': [cl.__name__ for cl in class_info]},
        )
    )


def parse_csv_list(csv_list):
    """Parse a list of CSV values."""
    return [i.strip() for i in csv_list.split(',')]


def get_yaml_from_docstring(doc_str, load_yaml=True):
    """
    Load the YAML part (after "---") from the docstring of a Spynl view.

    if load_yaml is True, return the result of yaml.load, otherwise return
    as string.
    """
    if doc_str:
        yaml_sep = doc_str.find('---')
    else:
        yaml_sep = -1

    if yaml_sep != -1:
        yaml_str = doc_str[yaml_sep:]
        if load_yaml:
            return yaml.load(yaml_str)
        else:
            return yaml_str
    return None


def required_args(*arguments):
    """Call the decorator that checks if required args passed in request."""

    def outer_wrapper(func):
        """Return the decorator."""

        @wraps(func)
        def inner_wrapper(*args):
            """
            Raise if a required argument is missing or is empty.

            Decorator checks if request.args were the expected <*arguments> of
            the current endpoint.
            """
            request = args[-1]  # request is always the last argument
            for required_arg in arguments:
                if request.args.get(required_arg, None) is None:
                    raise MissingParameter(required_arg)
            if len(getfullargspec(func).args) == 1:
                return func(request)
            else:
                return func(*args)

        return inner_wrapper

    return outer_wrapper


def report_to_sentry(exception, request):
    """Send exception info to online services for better monitoring
    The user_info param can be added so the services can display which user
    was involved.
    The exc_info parameter should only be passed in if a
    different exception than the current one on the stack should be sent.
    The metadata parameter can be used for any extra information.
    The endpoint parameter is sent under the tags Sentry parameter so
    exceptions can be filtered in their website by endpoint.
    """
    log = get_logger()
    settings = get_settings()

    try:
        import raven

        dsn = 'https://{}@app.getsentry.com/{}'.format(
            settings['spynl.sentry_key'], settings['spynl.sentry_project']
        )
        client = raven.Client(
            dsn=dsn,
            release=spynl_version,
            site='Spynl',
            environment=settings.get('spynl.ops.environment', 'dev'),
            processors=('raven.processors.SanitizePasswordsProcessor',),
        )
    except (ImportError, KeyError):
        # if raven package is not installed or sentry key or project don't exist move on
        return
    except raven.exceptions.InvalidDsn:
        log.warning('Invalid Sentry DSN')
        return

    user_info = get_user_info(request, purpose='error_view')
    if user_info:
        client.user_context(user_info)
    client.captureException(
        tags=dict(endpoint=request.path),
        extra=dict(
            url=request.path_url,
            debug_message=getattr(exception, 'debug_message', None),
            developer_message=getattr(exception, 'developer_message', None),
            detail=getattr(exception, 'detail', None),
        ),
    )


def report_to_newrelic(user_info):
    # tell NewRelic about user information if the newrelic package is installed
    # (the rest of the configuration of NewRelic is ini-file-based)
    try:
        import newrelic.agent
    except ImportError:
        return

    if not user_info:
        return

    log = get_logger()
    for key, value in user_info.items():
        # do not include ipaddress for privacy
        if key == 'ipaddress':
            continue
        if not newrelic.agent.add_custom_parameter(key, value):
            log.warning('Could not add user info to NewRelic on exception: %s', key)
            break


def log_error(exc, request, top_msg, error_type=None, error_msg=None):
    """
    Log the error from an error view to the log, and to external monitoring.
    Make sure the __cause__ of the exception is used.
    """
    log = get_logger()

    if not error_type:
        error_type = exc.__class__.__name__
    if error_type.endswith('Exception'):
        error_type = error_type[: -len('Exception')]

    if not error_msg:
        try:
            error_msg = exc.message
        except AttributeError:
            error_msg = str(exc)
            if not error_msg:
                error_msg = _('no-message-available')

    user_info = get_user_info(request, purpose='error_view')

    debug_message = (getattr(exc, 'debug_message', 'No debug message'),)
    developer_message = (getattr(exc, 'developer_message', 'No developer message'),)

    metadata = dict(
        user=user_info,
        url=request.path_url,
        debug_message=debug_message,
        developer_message=developer_message,
        err_source=get_err_source(exc.__traceback__),
        detail=getattr(exc, 'detail', None),
    )

    if developer_message:
        top_msg += " developer_message: %s" % developer_message

    if debug_message:
        top_msg += " debug_message: %s" % debug_message

    log.error(
        top_msg,
        error_type,
        str(error_msg),
        exc_info=sys.exc_info(),
        extra=dict(meta=metadata),
    )

    if getattr(exc, 'monitor', None) is True or not isinstance(
        exc, (HTTPForbidden, HTTPNotFound)
    ):
        report_to_sentry(exc, request)
        report_to_newrelic(user_info)


@contextlib.contextmanager
def chdir(dirname=None):
    """Change to this directory during this context"""
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)


def add_jinja2_filters(config, new_filters):
    """
    A helper function to add jinja filters in a plugger in such a
    way that previously added filters are not removed.
    """
    filters = config.get_settings().get('jinja2.filters', {})
    filters.update(new_filters)
    config.add_settings({'jinja2.filters': filters})
