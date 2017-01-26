"""Test functions from spynl.main."""

from copy import deepcopy

from pyramid.security import NO_PERMISSION_REQUIRED

from spynl.main import endpoints


def test_non_production_endpoints_that_doesnt_get_added(app_factory, settings,
                                                        monkeypatch):
    """The available_in_production should not add an endpoint."""
    def patched_main(config):
        """Fake main function in order to add a non production endpoint."""
        def non_production_endpoint(ctx, request):
            """Return something to make it look like a response."""
            return {'status': 'ok', 'message': 'Better not be in production.'}

        config.add_endpoint(non_production_endpoint, 'test-endpoint',
                            permission=NO_PERMISSION_REQUIRED,
                            available_in_production=False)

    monkeypatch.setattr('spynl.main.main', patched_main)
    settings_ = deepcopy(settings)
    settings_['spynl.spynl_environment'] = 'production'
    app = app_factory(settings_)

    response = app.get('/test-endpoint', expect_errors=True)
    assert "No endpoint found for path '/test-endpoint'"\
        in response.json['message']
