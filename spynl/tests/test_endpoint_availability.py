"""Test functions from spynl.main."""


from json import loads

from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid import testing
from webtest import TestApp as WebtestApp  # prevent pytest warning
import pytest

from spynl.main import main, endpoints


@pytest.fixture
def pretend_production(settings, request):
    """Set production environment in settings, re-setUp after test."""
    settings['spynl.spynl_environment'] = 'production'

    def fin():
        """Delete setting and re-setUp for the next tests."""
        del settings['spynl.spynl_environment']
        testing.setUp(settings=settings)
    request.addfinalizer(fin)



def test_non_production_endpoints_that_doesnt_get_added(settings, monkeypatch,
                                                        pretend_production):
    """The available_in_production should not add an endpoint."""
    def patched_main(config):
        """Fake main function in order to add a non production endpoint."""
        def non_production_endpoint(ctx, request):
            """Return something to make it look like a response."""
            return 'Better not be in production.'

        config.add_endpoint(non_production_endpoint, 'test-endpoint',
                            permission=NO_PERMISSION_REQUIRED,
                            available_in_production=False)

    monkeypatch.setattr(endpoints, 'main', patched_main)

    testing.setUp(settings=settings)
    spynl_app = main(None, test_settings=settings)
    app = WebtestApp(spynl_app)
    response = app.get('/test-endpoint', expect_errors=True)
    assert "No endpoint found for path '/test-endpoint'"\
        in response.json['message']
