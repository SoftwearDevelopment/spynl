import pytest
from webtest import TestApp
from spynl.main import main

@pytest.fixture(scope="session")
def app():
    spynl_app = main(None)
    return TestApp(spynl_app)

def test_hello(app):
    response = app.get('/hello', status=200)
    assert response.json['message'] == "Hello, world!"
