"""
Some very basic endpoints that do not require permission:
    * ping
    * time
    * error
    * error500

Also, two endpoints to test requests:
    * request_echo
    * request_check
"""

from datetime import datetime

from pyramid.security import NO_PERMISSION_REQUIRED

from spynl.main.utils import get_user_info
from spynl.main.dateutils import now, localize_date, date_to_str


def ping(request):
    """
    Ping Spynl.

    ---
    get:
      tags:
        - contact
      description: >
        Spynl tells you "pong" and the time.

        ####Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        time      | string | time in format: $setting[spynl.date_format]\n
        greeting  | string | 'pong'\n
    """
    return {'time': now(), 'greeting': 'pong'}


def time(request):
    """
    Get the Spynl time.

    ---
    get:
      tags:
        - contact
      description: >
        Spynl tells you its server time and what it believes to be
        your local time if you are logged in.

        ####Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        server_time | string | server time in format:
        $setting[spynl.date_format]\n
        local_time  | string | local user time in format:
        $setting[spynl.date_format]\n
        tz        | string | local time zone, e.g. Europe/Amsterdam\n
    """
    response = {'server_time': date_to_str(localize_date(datetime.utcnow(),
                                                         user_specific=False))}
    user_info = get_user_info(request)
    if user_info.get('tz') is not None:
        response['local_time'] = date_to_str(now())
        response['tz'] = user_info.get('tz', None)

    return response


def request_echo(request):
    """return request args (see utils.get_args) - for testing"""
    return request.args


def request_check(r):
    """return a valid json response with meta data from request"""
    request = {'status': 'ok'}
    if r.args.get('data'):
        request['data'] = r.args.get('data')
    if r.args.get('method'):
        request['method'] = r.args.get('method')
    if r.args.get('resource'):
        request['resource'] = r.args.get('resource')
    return request


def main(config):
    """
    Add two basic views, two error views and two test views
    """
    config.add_endpoint(ping, 'ping', permission=NO_PERMISSION_REQUIRED)
    config.add_endpoint(time, 'time', permission=NO_PERMISSION_REQUIRED)

    # useful for testing purposes
    config.add_endpoint(request_echo, 'request_echo',
                        permission=NO_PERMISSION_REQUIRED)
    config.add_endpoint(request_check, 'request_check',
                        permission=NO_PERMISSION_REQUIRED)
