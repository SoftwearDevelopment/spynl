"""Test functions from spynl.main."""
import pytest

from spynl.main.exceptions import SpynlException


@pytest.fixture
def exception_app(app_factory, settings, monkeypatch):
    """Plugin an endpoint that always raises and echo's back information."""

    def patched_plugin_main(config):
        def echo_raise(request):
            """
            Always raises.

            If some information is passes in the query params it is included
            within the reponse.
            """
            if request.GET:
                class CustomException(SpynlException):
                    def make_response(self):
                        data = super().make_response()
                        data.update(request.GET)
                        return data

                raise CustomException
            raise SpynlException

        config.add_endpoint(echo_raise, 'echo-raise')

    # monkeypatch spynl.main.plugins.main as it is a simple entry point without
    # internal logic where normally external plugins would get included.
    monkeypatch.setattr('spynl.main.plugins.main', patched_plugin_main)
    app = app_factory(settings)

    return app


def test_spynlexception(exception_app):
    """Test regular SpynlException"""
    response = exception_app.get('/echo-raise', expect_errors=True)
    assert response.json == SpynlException().make_response()


def test_overridden_spynlexception(exception_app):
    """Test regular SpynlException"""
    response = exception_app.get('/echo-raise', params={'custom': 'blah'}, expect_errors=True)
    assert response.json.get('custom') == 'blah'
