"""Test functions from spynl.main."""
import pytest

from spynl.main.utils import log_error


@pytest.fixture
def logger(monkeypatch):
    """
    Patch calls to the outside.

    Don't care about real user info, monitoring and we want a logger that
    we can easily inspect.
    """
    def patched_get_user_info(*args, **kwargs):
        return dict(ipaddress='127.0.0.1')
    monkeypatch.setattr('spynl.main.utils.get_user_info', patched_get_user_info)

    def patched_monitoring(*args, **kwargs):
        pass
    monkeypatch.setattr('spynl.main.utils.send_exception_to_external_monitoring',
                        patched_monitoring)

    class Logger:
        """This logger will set the passed information on self.error_log"""

        def __init__(self):
            self.error_log = None

        def error(self, msg, *args, **kwargs):
            self.error_log = {
                'msg': msg % args,
                'kwargs': kwargs
            }

    logger = Logger()

    def patched_getLogger(name):
        return logger
    monkeypatch.setattr('logging.getLogger', patched_getLogger)

    return logger


@pytest.fixture
def fake_request():
    """Return a fake request."""
    class FakeRequest:
        path_url = '/fake'
        body = 'fake request'

    return FakeRequest()


TOP_MSG = "TEST Error of type %s with message: '%s'."


def test_log_error_msg(logger, fake_request):
    """Test casting the exception to string."""
    class Error(Exception):
        def __str__(self):
            return "An error has occurred"

    try:
        raise Error
    except Exception as exc:
        log_error(exc, fake_request, TOP_MSG)
        assert logger.error_log['msg'] == TOP_MSG % ('Error', 'An error has occurred')


def test_log_error_msg_attribute(logger, fake_request):
    """Test that the .message attr is passed correctly."""
    class Error(Exception):
        message = 'An error has occurred'

    try:
        raise Error
    except Exception as exc:
        log_error(exc, fake_request, TOP_MSG)
        assert logger.error_log['msg'] == TOP_MSG % ('Error', 'An error has occurred')


def test_log_exception_cause(logger, fake_request):
    """
    Test exception __cause__

    Test that when a second exception is raised from the context of a first
    the logger receives information about the original.
    """

    class Error(Exception):
        pass

    class SecondError(Exception):
        pass

    try:
        raise Error
    except Exception as exc:
        try:
            raise SecondError from exc
        except Exception as exc2:
            log_error(exc2, fake_request, TOP_MSG)
            assert logger.error_log['kwargs']['exc_info'][0] == Error


def test_log_exception_name(logger, fake_request):
    """Test stripping of "Exception" from the name."""

    class SomeException(Exception):
        pass

    try:
        raise SomeException
    except Exception as exc:
        log_error(exc, fake_request, TOP_MSG)
        assert 'Exception' not in logger.error_log['msg']


def test_log_exception_default_message(logger, fake_request):
    """
    Test default message.

    When the exception has no .message or str(Exc) returns
    an empty string the default message should be logged.
    """

    try:
        raise Exception
    except Exception as exc:
        log_error(exc, fake_request, TOP_MSG)
        assert 'No message available' in logger.error_log['msg']


def test_log_given_exc_type_and_msg(logger, fake_request):
    """Test that the given error_type and msg are used."""

    try:
        raise Exception
    except Exception as exc:
        log_error(exc, fake_request, TOP_MSG,
                  error_type="Argh", error_msg="what the hell")

        assert logger.error_log['msg'] == ("TEST Error of type Argh "
                                           "with message: 'what the hell'.")


def test_log_debug_message(logger, fake_request):
    """Test that the debug_message is logged."""

    class SomeException(Exception):
        debug_message = "Debug this."

    try:
        raise SomeException
    except Exception as exc:
        log_error(exc, fake_request, TOP_MSG)

        assert (logger.error_log['kwargs']['extra']['meta']['debug_message'] ==
                SomeException.debug_message)
