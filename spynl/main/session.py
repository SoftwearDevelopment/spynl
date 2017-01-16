"""Configuration for session factory"""

from spynl.main.exceptions import SpynlException
from spynl.main.utils import get_parsed_body


def main(config):
    """
    * Configure which session factory to use, pyramid's default or one that
      is set in a plugin. In the plugger.py the plugin can set function by
      assigning that function to a setting with the name of the 'spynl.session'
    * Get session id from request to retrieve session
    * Save current session after each response
    """
    settings = config.get_settings()
    if 'spynl.session' in settings and settings['spynl.session'] != 'Pyramid':

        Session = settings.get(settings['spynl.session'])
        if not Session:
            msg = ('The function for the session factory is not set in any of '
                   'the plugins for this spynl.session option: {}'
                   .format(settings['spynl.session']))
            raise SpynlException(msg)

        def mksession(sid):
            return Session(id=sid)
    else:
        from beaker.session import Session

        def mksession(sid):
            return Session(None, id=sid, use_cookies=False)

    def session_factory(request):
        """We keep one session per sid"""
        sid = None
        # getting the sid from request.args would be easier,
        # but we cannot rely on args being unified there already.
        # We look for a session ID (sid) with decreasing priority in
        # cookies, headers, GET vars, POST vars.
        try:
            body = get_parsed_body(request)
        except:
            body = {}
        for params in (body, request.GET,
                       request.headers, request.cookies):
            if 'sid' in params:
                sid = params['sid']

        return mksession(sid)

    config.set_session_factory(session_factory)

    def new_response(event):
        """
        Make sure new and pristine sessions are saved.
        Changes to sessions should save them automatically
        and set session.new to False.
        """
        session = event.request.session
        if session:
            if hasattr(session, 'new'):
                if session.new is True:
                    session.save()
            else:
                session.save()

    config.add_subscriber(new_response, 'pyramid.events.NewResponse')
