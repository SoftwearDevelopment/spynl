"""Tests for origin whitelists."""


from json import loads
import pytest
from pyramid.httpexceptions import HTTPForbidden


def test_whitelisted_origin(app):
    """Test whitelisted origin."""
    headers = {"Origin": "http://www.softwearconnect.com"}
    response = loads(app.get('/ping', headers=headers).text)
    assert response['status'] == 'ok'
    headers = {"Origin": "http://www.swcloud.nl"}
    response = loads(app.get('/ping', headers=headers).text)
    assert response['status'] == 'ok'
    headers = {"Origin": "http://0.0.0.0:9001"}
    response = loads(app.get('/ping', headers=headers).text)
    assert response['status'] == 'ok'
    headers = {"Origin": "chrome-extension://sdlkhsldkfhlksjhsdfsdf"}
    response = loads(app.get('/ping', headers=headers).text)
    assert response['status'] == 'ok'


def test_notwhitelisted_origin(app):
    """Test not whitelisted origin."""
    headers = {"Origin": "Not-a-Url", "Content-Type": "application/json"}
    with pytest.raises_regexp(HTTPForbidden, "not permitted from origin 'Not-a-Url'"):
        app.get('/ping', headers=headers)
    headers = {"Origin": "http://www.swcloud.com"}
    with pytest.raises_regexp(HTTPForbidden, "not permitted from origin 'http://www.swcloud.com'"):
        app.get('/ping', headers=headers)
    headers = {"Origin": "http://0.0.0.0:9003"}
    with pytest.raises_regexp(HTTPForbidden, "not permitted from origin 'http://0.0.0.0:9003'"):
        app.get('/ping', headers=headers)
