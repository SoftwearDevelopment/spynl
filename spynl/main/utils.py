"""Helper functions and view derivers for spynl.main."""


import json
import logging
import traceback
import sys
from functools import wraps
from inspect import isfunction, isclass, getargspec
from collections import namedtuple
import yaml
from tld import get_tld
from tld.exceptions import TldBadUrl, TldDomainNotFound
import inspect

from pyramid.response import Response
from pyramid.renderers import json_renderer_factory
from pyramid.exceptions import Forbidden
from pyramid import threadlocal

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


def get_settings():
    """
    Get settings (from .ini file [app:main] section)
    Can also be accessed from the request object: request.registry.settings
    For more info on the way we do it here, consult
    http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/threadlocals.html
    Our policy is to not edit the settings during a request/response cycle.
    """
    registry = threadlocal.get_current_registry()
    return registry.settings if registry.settings is not None else {}


def check_origin(endpoint, info):
    """Check if origin is allowed"""
    def wrapper_view(context, request):
        """raise HTTPForbidden if origin isn't allowed"""
        origin = request.headers.get('Origin', '')
        if not is_origin_allowed(origin):
            # because this is a wrapper, the bad origin will not be properly
            # escalated to forbidden, so it needs to be done like this.
            raise Forbidden(detail=BadOrigin(origin).message.translate(
                request.localizer))
        return endpoint(context, request)
    return wrapper_view


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
            headerlist.extend([('Access-Control-Allow-Methods', 'GET,POST'),
                               ('Access-Control-Max-Age', '86400'),
                               ('Access-Control-Allow-Credentials', 'true'),
                               ('Content-Length', '0'),
                               ('Content-Type', 'text/plain')])
            # you can send any headers to Spynl, basically
            if 'Access-Control-Request-Headers' in request.headers:
                headerlist.append(
                    ('Access-Control-Allow-Headers',
                     request.headers['Access-Control-Request-Headers']))
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
    dev_whitelist = parse_csv_list(settings.get('spynl.dev_origin_whitelist',
                                                ''))
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
        tld_whitelist = parse_csv_list(settings.get(
            'spynl.tld_origin_whitelist', ''))
        if tld in tld_whitelist:
            origin_allowed = True
    return origin_allowed


def get_header_args(request):
    """Return a dictionary with arguments passed as headers."""
    # these require a spynl-specific prefix to be recognized
    headers = {key: value for key, value in request.headers.items()
               if key.lower().startswith('x-spynl-')}
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
            request.parsed_body = {} if not request.body \
                                     else json.loads(request.body)
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
    args.update(json.loads(json.dumps(urlson.loads_dict(request.GET)),
                           object_hook=objects.SpynlDecoder(context=context)))

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

    if hasattr(request, 'matched_route')\
      and request.matched_route:
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
    if request.registry.settings.get('user_info_function') is not None:
        return request.registry.settings['user_info_function'](request, purpose)
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
        return dict(module=first_call[0],
                    linenr=first_call[1],
                    method=first_call[2],
                    src_code=first_call[3])
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


def is_package_installed(package_name):
    """
    Return True if the package has been pip-installed
    in the current environment
    """
    # importing pip here so pip>=1.5.1 does not cause cyclic package troubles
    # when starting the spynl application
    import pip
    return package_name in [i.key for i in pip.get_installed_distributions()]



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
        except:
            raise SpynlException(_(
                'parse-value-exception-as-class',
                default='"${value}" could not be parsed as ${class}',
                mapping={'value': value, 'class': class_info.__name__}))

    if hasattr(class_info, '__iter__'):
        for cl in class_info:
            if not isclass(cl):
                raise SpynlException(_(
                    'parse-value-exception-not-class',
                    default='${class} is not a class. Cannot parse '
                            'value "${value}".',
                    mapping={'class': cl, 'value': value}))
            try:
                return cl(value)
            except Exception:
                pass
    raise SpynlException(_(
        'parse-value-exception-any-class',
        default='"${value}" could not be parsed into any class in ${classes}',
        mapping={'value': value,
                 'classes': [cl.__name__ for cl in class_info]}))



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
            if len(getargspec(func).args) == 1:
                return func(request)
            else:
                return func(*args)
        return inner_wrapper
    return outer_wrapper


def send_exception_to_external_monitoring(user_info=None, exc_info=None,
                                          metadata=None, endpoint=None):
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
    if exc_info is None:
        exc_info = sys.exc_info()
    # send Exception to Sentry if the raven package is installed
    # and sentry is configured
    try:
        if is_package_installed('raven') and settings.get('spynl.sentry_key')\
          and settings.get('spynl.sentry_project'):
            import raven  # pylint: disable=import-error
            spynl_env = settings.get('spynl.spynl_environment', 'dev')
            spynl_function = settings.get('spynl.function', 'all')
            client = raven.Client(
                dsn='https://{}@app.getsentry.com/{}'.format(
                    settings.get('spynl.sentry_key'),
                    settings.get('spynl.sentry_project')),
                release=spynl_version,
                site='Spynl [{}-{}]'.format(spynl_env, spynl_function),
                processors=('raven.processors.SanitizePasswordsProcessor',))
            if user_info is not None:
                client.user_context(user_info)
            data = dict(exc_info=exc_info, extra=metadata)
            if endpoint is not None:
                data.update(tags=dict(endpoint=endpoint))
            client.captureException(**data)
    except Exception as e:
        log.warning('Could not send Exception to Sentry: %s', e)

    # tell NewRelic about user information if the newrelic package is installed
    # (the rest of the configuration of NewRelic is ini-file-based)
    try:
        if is_package_installed('newrelic') and user_info is not None:
            import newrelic.agent  # pylint: disable=import-error
            for key in user_info:
                # do not include ipaddress for privacy
                if key != 'ipaddress':
                    newrelic.agent.add_custom_parameter(key, user_info[key])

    except Exception as e:
        log.warning('Could not add user info to NewRelic on exception: %s', e)


def log_error(exc, request, top_msg, error_type, error_msg):
    """
    Log the error from an error view to the log, and to external monitoring.
    Make sure the __cause__ of the exception is used.
    """
    log = get_logger()

    user_info = get_user_info(request, purpose='error_view')

    exc_info = sys.exc_info()
    if hasattr(exc, '__cause__') and exc.__cause__ is not None:
        exc_info = (exc.__cause__.__class__, exc.__cause__, sys.exc_info()[2])
    metadata = dict(user=user_info,
                    url=request.path_url,
                    err_source=get_err_source(sys.exc_info()[2]),
                    detail=getattr(exc, 'detail', None))
    log.error(top_msg, error_type, str(error_msg),
              exc_info=exc_info,
              extra=dict(meta=metadata,
                         payload=str(request.body)[:500]))

    send_exception_to_external_monitoring(user_info=user_info,
                                          exc_info=exc_info,
                                          metadata=metadata)


def is_production_environment(or_test=False):
    """Return if environment is either beta/production or not."""
    settings = get_settings()
    allowed_envs = ['beta', 'production']
    if or_test:
        allowed_envs.append('test')
    return settings.get('spynl.spynl_environment') in allowed_envs
