"""Handle JSON content."""

import json
import re

from spynl.main.serial import objects
from spynl.main.serial.exceptions import MalformedRequestException


def loads(body, headers=None, context=None):
    """Return body as JSON."""
    try:
        decoder = objects.SpynlDecoder(context)
        return json.loads(body, object_hook=decoder)
    except ValueError as e:
        raise MalformedRequestException('application/json', str(e))


def dumps(body, pretty=False):
    """Return JSON body as string."""
    indent = None
    if pretty:
        indent = 4

    class JSONEncoder(json.JSONEncoder):
        def default(self, obj):  # pylint: disable=method-hidden
            return objects.encode(obj)
    return json.dumps(body, indent=indent, ensure_ascii=False, cls=JSONEncoder)


def sniff(body):
    """
    sniff to see if body is a json object.

    Body should start with any amount of whitespace and a {.
    """
    expression = re.compile(r'^\s*\{')
    return bool(re.match(expression, body))
