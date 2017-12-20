"""Tests for utils.py."""


import pytest
from pyramid.testing import DummyRequest
from marshmallow import fields

from spynl.main.serial.query_string_loading import query_string_loader, QueryStringSchema
from spynl.main.exceptions import BadQueryString


class DummySchema(QueryStringSchema):
    """Sample schema which includes all fields/constraints of some views."""

    data = fields.Dict(required=True)
    data2 = fields.Dict()


@query_string_loader(DummySchema())
def get_view(request): pass


def test_errors_in_query_string():
    """Pass invalid query string."""
    with pytest.raises(BadQueryString) as err:
        get_view(DummyRequest(params={'data': 1}, args={}))
    expected = {'message': 'Invalid query string.',
                'errors': {'data': ['Not a valid mapping type.']}}
    assert err.value.developer_message == expected


def test_valid_query_string():
    """Pass valid query string."""
    get_view(DummyRequest(params={'data': {}}, args={}))
