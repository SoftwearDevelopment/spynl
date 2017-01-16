"""Handle XML content"""

from xml.etree.ElementTree import fromstring, ParseError
from xml.sax import saxutils
import re

from spynl.main.serial import objects
from spynl.main.serial.exceptions import MalformedRequestException


expression = re.compile(r'^\s*\<')


def loads(body, headers=None, context=None):
    """return body as XML"""
    try:
        root = fromstring(body)
    except ParseError as e:
        # pylint: disable=E1101
        raise MalformedRequestException('application/xml', str(e))

    dic = __loads(root, True)
    return objects.SpynlDecoder(context=context)(dic)


def __loads(element, force_dict=False):
    """Recurse through etree node, return parsed structure"""
    if len(element) and element.get('type') != 'collection' or force_dict:
        # this is a mapping (dict)
        result = {}
        for field in element:
            result[field.tag] = __loads(field)
    elif element.get('type') == 'collection':
        # this is a collection (list)
        result = [__loads(item) for item in element]
    else:
        # this is a value
        result = None
        if element.text:
            result = element.text.strip()

    return result


def dumps(body, pretty=True):
    """return XML body as string"""
    result = __dumps(body)

    if pretty:
        result = prettify_xml(result)

    # concatenating bytes and str objects to one str
    ustr = ''
    for item in result:
        ustr += str(item)

    return '<response>{}{}</response>'.format(pretty * '\n', ustr)


def __dumps(value):
    """Recurse through dict/list structure, returning XML text"""
    result = []

    if isinstance(value, (list, tuple, set)):
        for item in value:
            result.append('<item>')
            result.extend(__dumps(item))
            result.append('</item>')
    elif isinstance(value, dict):
        for field, value in value.items():
            if field.startswith('$'):  # e.g. query operators
                field = field[1:]

            alpha = re.match(r'\D', field)  # alphanumeric field name?

            start_tag = '<' + (field if alpha else 'item')
            if not alpha:
                start_tag += ' key="{}"'.format(field)
            if isinstance(value, (list, tuple)):
                start_tag += ' type="collection"'
            start_tag += '>'
            end_tag = '</{}>' if alpha else '</item>'

            result.append(start_tag.format(field))
            result.extend(__dumps(value))
            result.append(end_tag.format(field))
    else:
        if isinstance(value, str):
            value = saxutils.escape(value)
        result.append(objects.encode(value))

    return result


def sniff(body):
    """sniff to see if body is xml"""
    return bool(re.match(expression, body))


def prettify_xml(xmlstr):
    """add indentation to create pretty xml"""
    indent = 1
    for i in range(len(xmlstr)):
        item = xmlstr[i]
        if item.startswith('</'):
            indent -= 1
            tag = xmlstr[i - 1].startswith('<')
            yield tag * ' ' * indent * 4 + item + '\n'
        elif item.startswith('<'):
            tag = xmlstr[i + 1].startswith('<')
            yield ' ' * indent * 4 + item + tag * '\n'
            indent += 1
        else:
            yield item
    raise StopIteration()
