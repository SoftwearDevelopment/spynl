# coding=UTF8
"""Tests for JSON schema validation of Spynl request and response data."""


import json
import os
from copy import deepcopy
import pytest

from spynl.main.validation import interprete_validation_instructions as validate_json
from spynl.main.exceptions import BadValidationInstructions, InvalidResponse


ping_schema = {
    "$schema": "http://json-schema.org/schema#",
    "required": ["status", "greeting", "time"],
    "properties": {"status": {"type": "string"},
                   "greeting": {"type": "string"},
                   "time": {"type": "string"}}}

usual_ping_response = {
    "status": "ok",
    "greeting": "pong",
    "time": "2015-09-28T13:06:32+0000"
}

tenant_schema = {
    "$schema": "http://json-schema.org/schema#",
    "required": ["id", "name"],
    "properties": {"id": {"type": "string"},
                   "name": {"type": "string"}}}


def _sfolder():
    """return schema folder location"""
    venv_loc = os.environ.get('VIRTUAL_ENV', '')
    return '%s/spynl-schemas' % venv_loc


def _write_schema(sname, sdata):
    """write a schema file"""
    if not os.path.exists(_sfolder()):
        os.mkdir(_sfolder())
    sfile = open('{}/{}.json'.format(_sfolder(), sname), 'w')
    sfile.write(json.dumps(sdata, indent=2))
    sfile.close()


@pytest.fixture(autouse=True)
def file_cleanup(request):
    """Do file cleanups after each test in this module."""
    def fin():
        """Finalizer."""
        for filename in os.listdir(_sfolder()):
            if filename.startswith('__'):
                os.remove('{}/{}'.format(_sfolder(), filename))
    request.addfinalizer(fin)


def test_novalidations_possible():
    """Test cases where no validations are possible."""
    invalid_ping_response = deepcopy(usual_ping_response)
    del invalid_ping_response['greeting']
    # no validations given
    validate_json(invalid_ping_response, [], 'response')
    vals = [{'schema': '__missing.json', 'in': 'response'}]
    with pytest.raises_regexp(BadValidationInstructions,
        ".* required schema __missing.json could not be found .*"):
        validate_json(invalid_ping_response, vals, 'response')
    # invalid schema
    _write_schema('__ping_inv', [])
    vals = [{'schema': '__ping_inv.json', 'in': 'response'}]
    with pytest.raises_regexp(BadValidationInstructions, ".* not valid"):
        validate_json(usual_ping_response, vals, 'response')


def test_invalid_description():
    """
    Test missing information and wrong format.
    The full exception.messages are longer than just Missing field etc, but
    the exception that's shown just shows the args, which is only the
    sub-message (Missing field ...)
    """
    _write_schema('__ping', ping_schema)
    vals = [{'apply-to': 'bla', 'in': 'response'}]
    with pytest.raises_regexp(BadValidationInstructions, "Missing field: schema"):
        validate_json(usual_ping_response, vals, 'response')
    vals = [{'schema': '__ping.json'}]
    with pytest.raises_regexp(BadValidationInstructions, "Missing field: in"):
        validate_json(usual_ping_response, vals, 'response')
    vals = [{'schema': 'bla', 'apply-to': 'bla', 'in': 'repsonse'}]
    with pytest.raises_regexp(BadValidationInstructions, '"request" or "response"'):
        validate_json(usual_ping_response, vals, 'response')
    vals = {'apply-to': 'bla', 'in': 'response'}
    with pytest.raises_regexp(BadValidationInstructions, "Validations should be a list"):
        validate_json(usual_ping_response, vals, 'response')


def test_correct_response_schema():
    """Test validating a usual ping reponse."""
    _write_schema('__ping', ping_schema)
    vals = [{'schema': '__ping.json', 'in': 'response'}]
    validate_json(usual_ping_response, vals, 'response')


def test_correct_sub_schema():
    """Test usual ping with tenants."""
    _write_schema('__ping', ping_schema)
    _write_schema('__tenants', tenant_schema)
    vals = [{'schema': '__ping.json', 'in': 'response'},
            {'schema': '__tenants.json', 'in': 'response',
             'apply-to': 'tenants', 'repeat': True}]
    ping_response_with_tenants = deepcopy(usual_ping_response)
    ping_response_with_tenants['tenants'] = \
            [{'id': 'Bla1', 'name': 'Tenant'}, {'id': 'Bla2', 'name': 'TTT2'}]
    validate_json(ping_response_with_tenants, vals, 'response')


def test_incorrect_response_schema():
    """Change schema so that the /ping response is not correct."""
    wrong_ping_schema = deepcopy(ping_schema)
    wrong_ping_schema['required'].extend(['di'])
    wrong_ping_schema['properties']['di'] = {'type': 'string'}
    _write_schema('__wrong-ping', wrong_ping_schema)
    vals = [{'schema': '__wrong-ping.json', 'in': 'response'}]
    with pytest.raises_regexp(InvalidResponse, "'di' is a required property"):
        validate_json(usual_ping_response, vals, 'response')


def test_incorrect_sub_schema():
    """Test usual ping with wrong tenant data."""
    _write_schema('__ping', ping_schema)
    _write_schema('__tenants', tenant_schema)
    vals = [{'schema': '__ping.json', 'in': 'response'},
            {'schema': '__tenants.json', 'in': 'response',
             'apply-to': 'tenants', 'repeat': True}]
    response_with_bad_tenant_data = deepcopy(usual_ping_response)
    response_with_bad_tenant_data['tenants'] = \
            [{'id': 'Bla1', 'name': 'Tenant'}, {'id': 'Bla2', 'nname': 'TTT2'}]
    with pytest.raises_regexp(InvalidResponse, "'name' is a required property"):
        validate_json(response_with_bad_tenant_data, vals, 'response')
