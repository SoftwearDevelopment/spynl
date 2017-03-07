"""Handle JSON content."""

import json
import re

import rapidjson

from spynl.main.serial import objects
from spynl.main.serial.exceptions import MalformedRequestException


def loads(body, headers=None, context=None):
    """Return body as JSON."""
    try:
        decoder = objects.SpynlDecoder(context)
        result = rapidjson.loads(body, object_hook=decoder)
        # Before replacing json with rapidjson, the first exception was raised
        # so the same functionlity is kept
        if decoder.errors:
            raise decoder.errors[0]
        return result
        # exceptions
    except ValueError as err:
        raise MalformedRequestException('application/json', str(err))


def dumps(body, pretty=False):
    """Return JSON body as string."""
    indent = None if pretty is False else 4
    return rapidjson.dumps(body, indent=indent, ensure_ascii=False,
                           default=objects.encode)


def sniff(body):
    """
    sniff to see if body is a json object.

    Body should start with any amount of whitespace and a {.
    """
    expression = re.compile(r'^\s*\{')
    return bool(re.match(expression, body))
