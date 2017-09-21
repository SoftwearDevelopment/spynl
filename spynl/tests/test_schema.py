# coding=UTF8
"""Tests for JSON schema validation of Spynl request and response data."""


import json
from copy import deepcopy
import pytest

from spynl.main.validation import interprete_validation_instructions as validate_json
from spynl.main.exceptions import BadValidationInstructions, InvalidResponse


USUAL_PING_RESPONSE = {"status": "ok", "greeting": "pong",
                       "time": "2015-09-28T13:06:32+0000"}

PING_SCHEMA = {"$schema": "http://json-schema.org/schema#",
               "required": ["status", "greeting", "time"],
               "properties": {"status": {"type": "string"},
                              "greeting": {"type": "string"},
                              "time": {"type": "string"}}}


@pytest.fixture(autouse=True)
def patch_validation_file_path(tmpdir, monkeypatch):
    """Patch schemas directory."""
    tmpdir.mkdir('schemas')
    monkeypatch.setattr('sys.prefix', tmpdir.strpath)


@pytest.fixture
def ping_schema(tmpdir):
    file_ = tmpdir.join('schemas/ping.json')
    file_.write(json.dumps(PING_SCHEMA, indent=2))
    yield file_
    file_.remove()


@pytest.fixture
def wrong_ping_schema(tmpdir):
    schema = deepcopy(PING_SCHEMA)
    schema['required'].extend(['di'])
    schema['properties']['di'] = {'type': 'string'}
    file_ = tmpdir.join('schemas/wrong-ping.json')
    file_.write(json.dumps(schema, indent=2))
    yield file_
    file_.remove()


@pytest.fixture
def tenants_schema(tmpdir):
    schema = {"$schema": "http://json-schema.org/schema#",
              "required": ["id", "name"],
              "properties": {"id": {"type": "string"},
                             "name": {"type": "string"}}}
    file_ = tmpdir.join('schemas/tenants.json')
    file_.write(json.dumps(schema, indent=2))
    yield file_
    file_.remove()


@pytest.fixture
def invalid_schema(tmpdir):
    file_ = tmpdir.join('schemas/invalid_ping.json')
    file_.write(json.dumps([], indent=2))
    yield file_
    file_.remove()


def test_novalidations_possible(invalid_schema):
    """Test cases where no validations are possible."""
    invalid_ping_response = deepcopy(USUAL_PING_RESPONSE)
    del invalid_ping_response['greeting']
    # no validations given
    validate_json(invalid_ping_response, [], 'response')
    vals = [{'schema': '__missing.json', 'in': 'response'}]
    with pytest.raises_regexp(
            BadValidationInstructions,
            ".* required schema __missing.json could not be found .*"):
        validate_json(invalid_ping_response, vals, 'response')
    # invalid schema
    vals = [{'schema': invalid_schema.basename, 'in': 'response'}]
    with pytest.raises_regexp(BadValidationInstructions, ".* not valid"):
        validate_json(USUAL_PING_RESPONSE, vals, 'response')


def test_invalid_description(ping_schema):
    """
    Test missing information and wrong format.
    The full exception.messages are longer than just Missing field etc, but
    the exception that's shown just shows the args, which is only the
    sub-message (Missing field ...)
    """
    vals = [{'apply-to': 'bla', 'in': 'response'}]
    with pytest.raises_regexp(BadValidationInstructions,
                              "Missing field: schema"):
        validate_json(USUAL_PING_RESPONSE, vals, 'response')
    vals = [{'schema': ping_schema.basename}]
    with pytest.raises_regexp(BadValidationInstructions, "Missing field: in"):
        validate_json(USUAL_PING_RESPONSE, vals, 'response')
    vals = [{'schema': 'bla', 'apply-to': 'bla', 'in': 'repsonse'}]
    with pytest.raises_regexp(BadValidationInstructions,
                              '"request" or "response"'):
        validate_json(USUAL_PING_RESPONSE, vals, 'response')
    vals = {'apply-to': 'bla', 'in': 'response'}
    with pytest.raises_regexp(BadValidationInstructions,
                              "Validations should be a list"):
        validate_json(USUAL_PING_RESPONSE, vals, 'response')


def test_correct_response_schema(ping_schema):
    """Test validating a usual ping reponse."""
    vals = [{'schema': ping_schema.basename, 'in': 'response'}]
    validate_json(USUAL_PING_RESPONSE, vals, 'response')


def test_correct_sub_schema(ping_schema, tenants_schema):
    """Test usual ping with tenants."""
    vals = [{'schema': ping_schema.basename, 'in': 'response'},
            {'schema': tenants_schema.basename, 'in': 'response',
             'apply-to': 'tenants', 'repeat': True}]
    ping_response_with_tenants = deepcopy(USUAL_PING_RESPONSE)
    ping_response_with_tenants['tenants'] = [{'id': 'Bla1', 'name': 'Tenant'},
                                             {'id': 'Bla2', 'name': 'TTT2'}]
    validate_json(ping_response_with_tenants, vals, 'response')


def test_incorrect_response_schema(wrong_ping_schema):
    """Change schema so that the /ping response is not correct."""
    vals = [{'schema': wrong_ping_schema.basename, 'in': 'response'}]
    with pytest.raises_regexp(InvalidResponse, "'di' is a required property"):
        validate_json(USUAL_PING_RESPONSE, vals, 'response')


def test_incorrect_sub_schema(ping_schema, tenants_schema):
    """Test usual ping with wrong tenant data."""
    vals = [{'schema': ping_schema.basename, 'in': 'response'},
            {'schema': tenants_schema.basename, 'in': 'response',
             'apply-to': 'tenants', 'repeat': True}]
    response_with_bad_tenant_data = deepcopy(USUAL_PING_RESPONSE)
    response_with_bad_tenant_data['tenants'] = [
        {'id': 'Bla1', 'name': 'Tenant'}, {'id': 'Bla2', 'nname': 'TTT2'}]
    with pytest.raises_regexp(InvalidResponse,
                              "'name' is a required property"):
        validate_json(response_with_bad_tenant_data, vals, 'response')
