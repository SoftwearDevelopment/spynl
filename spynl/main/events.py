"""
Custom handling of requests and responses.
"""

from os.path import basename, splitext
from copy import deepcopy

from pyramid.events import (NewRequest, BeforeTraversal, ContextFound,
                            NewResponse)
from pyramid.httpexceptions import HTTPUnsupportedMediaType

from spynl.main.utils import (unify_args, get_logger, is_origin_allowed,
                              get_settings)
from spynl.main.serial.typing import negotiate_request_content_type
from spynl.main.serial.exceptions import UnsupportedContentTypeException


def prepare_content_types(event):
    """
    Negotiate requested content type and pre-set
    response content type
    """
    request = event.request

    # negotiate request content type
    try:
        request.content_type = negotiate_request_content_type(request)
    except UnsupportedContentTypeException as e:
        request.content_type = None
        raise HTTPUnsupportedMediaType(detail=e.message.translate(
            request.localizer))

    # Overwrite the HTML assumption made by the browsers
    # about response type with the Spynl default, views can overwrite
    if request.response.content_type == 'text/html'\
      and '/static' not in request.path_url:
        request.response.content_type = 'application/json'


def corsify_response(event):
    """
    Add headers to the response, in order to allow
    Cross-Origin Resource Sharing (CORS).
    Then Spynl is usable from different domains. Check the ini settings
    spynl.tld_origin_whitelist and spynl.dev_origin_whitelist for info
    on how to whitelist domains.

    Helpful links:
    http://www.w3.org/TR/cors/
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Server-Side_Access_Control
    http://www.kinvey.com/bloog/60/kinvey-adds-cross-origin-resource-sharing-cors
    """
    response = event.request.response
    origin = event.request.headers.get('Origin')
    if origin:  # otherwise we are on localhost or are called directly
        if is_origin_allowed(origin):
            response.headerlist.append(('Access-Control-Allow-Origin', origin))
        else:
            response.headerlist.append(('Access-Control-Allow-Origin', 'null'))
    response.headerlist.append(('Access-Control-Allow-Credentials', 'true'))
    response.headerlist.append(('Vary', 'Accept-Encoding, Origin'))


def split_extension(event):
    """Split extension off the path info"""
    request = event.request
    # tweak path info for routing
    path, ext = splitext(request.path_info)
    if not path.startswith('/static'):
        request.original_path_info = request.path_info
        request.path_info = path
    request.path_extension = ext


def store_accepted_lang(event):
    """
    Store locale on request for pyramid.i18n.negotiate_locale_name.
    We do not support dialects at the moment, so for instance,
    "en-gb" will be treated as "en".

    We look for information about the locale in this order:
    1. The "lang" cookie
    2. The request header Accept-language
    3. The first of the supported languages (spynl.languages)
    4. We fall back to "en", which is the language the code uses
    """
    request = event.request
    settings = get_settings()

    language = None

    def langcode(langstr):
        """return only up to the first two characters"""
        if len(langstr) < 2:
            return langstr
        return langstr[:2]

    supported_languages = [langcode(lang.strip()) for lang in
                           settings.get('spynl.languages', '').split(',')]
    preferred_language = supported_languages[0]

    if 'lang' in request.cookies:
        language = langcode(request.cookies['lang'])
    elif request.accept_language:
        language = langcode(request.accept_language\
                                   .best_match(supported_languages,
                                               preferred_language))
    if language is None or language not in supported_languages:
        language = preferred_language
    if language is None:
        language = 'en'
    # pylint: disable=W0212
    request._LOCALE_ = language


def parse_args_and_log_request(event):
    """
    Parse request data when context is known,
    and log the request (together with parsed arguments) with
    log level INFO.
    Best to do this when the context is known and available
    through the request object, as this can influence how
    we parse request data.
    """
    request = event.request
    # bring all args together in the args dict on the request
    request.args = unify_args(request)
    # log the request
    log = get_logger()
    args = deepcopy(request.args)
    if 'password' in args:
        args['password'] = '*********'
    origin = request.headers.get('Origin', '')
    origin_txt = ''
    if origin:
        origin_txt = ' Origin: {}'.format(origin)
    log.info('New request for URL path "%s" from %s',
             request.path_url, origin_txt,
             extra=dict(meta=dict(url=request.path_url), payload=args))


def enforce_response_type(event):
    """
    Support two exotic types of response data: text and download, which can
    be enforced by arguments.
    In the first case, we set the content type, in the second we set headers.
    """
    r = event.request
    args = getattr(r, 'args', {})

    if 'force_text' in args:
        event.response.content_type = 'text/plain'

    if 'force_download' in args:
        filename = str(basename(r.path_info))
        event.response.headers.update(
            {'Content-Description': 'File Transfer',
             'Content-Type': 'application/octet-stream',
             'Content-Disposition': 'attachment: filename=' + filename,
             'Content-Transfer-Encoding': 'binary',
             'Expires': '0',
             'Cache-Control': 'must-revalidate',
             'Pragma': 'public'})


def main(config):
    """Subscribe to pyramid events."""
    config.add_subscriber(split_extension, NewRequest)
    config.add_subscriber(store_accepted_lang, NewRequest)
    config.add_subscriber(prepare_content_types, BeforeTraversal)
    config.add_subscriber(parse_args_and_log_request, ContextFound)
    config.add_subscriber(enforce_response_type, NewResponse)
    config.add_subscriber(corsify_response, NewResponse)
