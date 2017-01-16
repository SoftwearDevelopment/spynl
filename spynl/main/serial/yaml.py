"""Handle YAML content"""

import re

import yaml

from spynl.main.serial.exceptions import MalformedRequestException


expression = re.compile(r'^\s*\-')


def sniff(body):
    """Sniff body content, return True if YAML detected"""
    return bool(re.match(expression, body))


def dumps(body, pretty=False):
    """return YAML body as string"""
    if pretty:
        return yaml.dump(body, indent=4)
    else:
        return yaml.dump(body)


def loads(body, headers=None):
    """return body as YAML"""
    try:
        return yaml.load(body)
    except ValueError as e:
        raise MalformedRequestException('application/x-yaml', str(e))
