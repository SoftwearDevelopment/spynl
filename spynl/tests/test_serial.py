# coding=UTF8
"""Specifically test (de)serialisation with straightforward unit tests."""

from decimal import Decimal

import datetime
import json as json_py
from xml.etree.ElementTree import fromstring

import pytest

from spynl.main.dateutils import date_to_str, date_from_str, localize_date

from spynl.main.serial import (
    handlers,
    json,
    xml,
    csv,
    py,
    loads,
    dumps,
    MalformedRequestException,
    UnsupportedContentTypeException,
    DeserializationUnsupportedException,
    SerializationUnsupportedException,
)
from spynl.main.serial.csv import loads as csv_loads


def test_empty():
    """Test if empty."""
    assert loads('', None) == {}


def test_bad_content_types():
    """Test types that don't work urlencoded, plain text, nothing, object."""
    with pytest.raises(UnsupportedContentTypeException):
        dumps('|"a": 1|', 'application/y-www-form-urlencoded')

    with pytest.raises(UnsupportedContentTypeException):
        dumps('some plain text', 'text/plain')

    with pytest.raises(UnsupportedContentTypeException):
        dumps('null', '')

    with pytest.raises(UnsupportedContentTypeException):
        dumps('object', 'application/object')


def test_supported_content_type_but_not_loading(monkeypatch):
    """We might support only dumping or only loading in a content-type."""
    monkeypatch.setitem(handlers, 'foo/type', {})
    with pytest.raises(DeserializationUnsupportedException):
        loads('body', 'foo/type')


def test_supported_content_type_but_not_dumping(monkeypatch):
    """We might support only dumping or only loading in a content-type."""
    monkeypatch.setitem(handlers, 'foo/type', {})
    with pytest.raises(SerializationUnsupportedException):
        dumps('body', 'foo/type')


def test_sniff_braces():
    """Sniff true if body starts with {."""
    assert json.sniff('   {')


def test_sniff_triangle():
    """Sniff false if body starts with <."""
    assert not json.sniff('   <')


def test_sniff_nl():
    """Sniff true if body starts with newline {."""
    assert json.sniff('   \n{')


def test_main_json_loads_valid(app):
    """Test if valid jsons are loaded correctly."""
    valid_jsons = [
        ('{"string":"blah","int":1}', {'string': 'blah', 'int': 1}),
        ('{"object":{"int":1},"bool":true}', {'object': {'int': 1}, 'bool': True}),
        ('{"bool":true,"float":3.5}', {'bool': True, 'float': 3.5}),
    ]
    for data_in, output in valid_jsons:
        assert json.loads(data_in) == output


def test_main_json_loads_malformed():
    """Can't load malformed data_in (json loads)."""
    data_in = '{"malformed":'
    with pytest.raises(MalformedRequestException):
        json.loads(data_in)


def test_main_json_loads_encoding():
    """Load as unicode (json loads) strings with weird characters."""
    data_in = '{"a":"€9.80", "b":"Cëöß", "c":"äbc"}'
    int_repr = json.loads(data_in)
    assert int_repr['a'] == '€9.80'
    assert int_repr['b'] == 'Cëöß'
    assert int_repr['c'] == 'äbc'


def test_main_json_loads_date():
    """Test date to string conversion, load json and convert back."""
    now = datetime.datetime.now()
    dstr = date_to_str(now)
    data_in = '{"date": "' + dstr + '"}'
    assert json.loads(data_in) == {'date': date_from_str(dstr)}


def test_json_dumps_no_raise():
    """Test no raise (json dumps)."""
    assert json.dumps({'a': 1}) == '{"a": 1}'


def test_json_dumps_content_type():
    """Test content type (json dumps)."""
    response = dumps({'a': 1}, 'application/json')
    assert json.loads(response) == {'a': 1}


def test_json_dumps_encoding():
    """
    Dump weird characters in internal representation as unicode text.

    Dump them without problems. (json dumps)
    """
    body = {'data': [{'a': '€9.80', 'b': 'Cëöß', 'c': 'äbc'}]}
    response = json.dumps(body)
    assert '€9.80' in response
    assert 'Cëöß' in response
    assert 'äbc' in response


def test_json_dumps_str():
    """
    Test unicode (json dumps) and get dumped.

    Unicode a string and a unicode get dumped as one unicode without problems.
    """
    uni = {"foreigner": "H\xf6nëng"}
    assert '{"foreigner": "H\xf6nëng"}' == json.dumps(uni)


def test_json_dumps_date():
    """Test date (json dumps)."""
    now = datetime.datetime.now()
    assert (
        json.dumps({'now': now}) == '{"now": "' + date_to_str(localize_date(now)) + '"}'
    )


def test_xml_sniff_triangle():
    """< gives True for xml sniff."""
    assert xml.sniff('   <')


def test_xml_sniff_braces():
    """{ gives false for xml sniff."""
    assert not xml.sniff('   {')


def test_xml_sniff_nl():
    r"""\n< gives true for xml sniff."""
    assert xml.sniff('   \n<')


def test_xml_sniff_tab():
    r"""\t< gives true for xml sniff."""
    assert xml.sniff('   \t<')


def test_xml_loads_valid():
    """Test valid (xml loads)."""
    valid_xmls = [
        ('<a><b>1</b><c>2</c></a>', {"b": "1", "c": "2"}),
        ('<a><b>true</b><c>3.5</c></a>', {"b": "true", "c": "3.5"}),
        (
            """
                   <request>
                        <action>add</action>
                        <resource>user</resource>
                        <data type="collection">
                            <item>
                                <a>1</a>
                                <b>True</b>
                            </item>
                            <item>
                                <c>Just testing</c>
                                <h>&gt; 3</h>
                            </item>
                        </data>
                   </request>
                   """,
            {
                'action': 'add',
                'resource': 'user',
                'data': [{'a': '1', 'b': 'True'}, {'c': 'Just testing', 'h': '> 3'}],
            },
        ),
        (
            """
                   <request>
                        <filter>
                            <a>
                                <_gt>3</_gt>
                            </a>
                        </filter>
                   </request>
                   """,
            {'filter': {'a': {'_gt': '3'}}},
        ),
    ]
    for data_in, output in valid_xmls:
        assert xml.loads(data_in) == output


def test_xml_loads_smalformed():
    """Test malformed (xml loads)."""
    for data_in in ("<malformed>", "{}", "<a></b>"):
        with pytest.raises(MalformedRequestException):
            xml.loads(data_in)


def test_xml_loads_encoding():
    """Load strings with weird characters as unicode (xml loads)."""
    data_in = "<data><a>€9.80</a><b>Cëöß</b><c>äbc</c></data>"
    int_repr = xml.loads(data_in)
    assert int_repr['a'], '€9.80'
    assert int_repr['b'], 'Cëöß'
    assert int_repr['c'], 'äbc'


def test_xml_loads_html_umlaut():
    """
    html umlaut is loaded as str (xml loads).

    An HTML representation of an umlaut comes in, is loaded as
    unicode.
    """
    ums = [('<a><foreigner>H&#246;ning</foreigner></a>', {"foreigner": "H\xf6ning"})]
    for data_in, output in ums:
        assert xml.loads(data_in) == output


def test_xml_loads_date(app):
    """Test date (xml loads)."""
    now = datetime.datetime.now()
    dstr = date_to_str(now)
    data_in = '<root><date>' + dstr + '</date></root>'
    assert xml.loads(data_in)['date'] == date_from_str(dstr)


def test_xml_dumps_simple():
    """Test simple (xml dumps)."""
    body = {'a': 1, 'b': 2.5, 'c': True}

    response = xml.dumps(body)
    root = fromstring(response)

    assert root.tag == 'response'
    assert len(root) == 3
    a = root.find('a')
    assert a.text.strip() == '1'
    b = root.find('b')
    assert b.text.strip() == '2.5'
    c = root.find('c')
    assert c.text.strip() == 'true'


def test_xml_dumps_list():
    """Test list (xml dumps)."""
    response = dumps({'a': 1, 'b': [2.5, 1.6], 'c': {'ab': True}}, 'application/xml')
    root = fromstring(response)
    assert len(root) == 3
    assert root.findtext('a').strip() == '1'
    b = root.find('b')
    assert len(b) == 2
    assert b.get('type') == 'collection'
    items = b.findall('item')
    assert items[0].text.strip() == '2.5'
    assert items[1].text.strip() == '1.6'
    assert root.findtext('c/ab').strip() == 'true'


def test_xml_dumps_nested():
    """Test nested (xml dumps)."""
    body = {'a': 3.5, 'b': '0x10', 'c': [{'a': True}, {'c': False}]}

    response = xml.dumps(body)
    root = fromstring(response)

    assert len(root) == 3
    a = root.find('a')
    assert a.text.strip() == '3.5'
    b = root.find('b')
    assert b.text.strip() == '0x10'
    c = root.find('c')
    items = c.findall('item')
    assert len(items) == 2
    assert items[0].findtext('a') == 'true'
    assert items[1].findtext('c') == 'false'


def test_xml_dumps_encoding():
    """
    Test encoding (xml dumps).

    Weird characters in internal representation get dumped to unicode
    text without problems.
    """
    body = {'data': [{'a': '€9.80', 'b': 'Cëöß', 'c': 'äbc'}]}
    response = xml.dumps(body)
    assert '€9.80' in response
    assert 'Cëöß' in response
    assert 'äbc' in response


def test_xml_dumps_str():
    """A unicode in input comes out fine (xml dumps)."""
    data_in, output = ({u"foreigner": "H\xf6ning"}, "<foreigner>H\xf6ning</foreigner>")
    assert output in xml.dumps(data_in)


def test_xml_dumps_date():
    """Test date (xml dumps)."""
    now = datetime.datetime.now()
    response = fromstring(xml.dumps({'now': now}))
    assert response.find('now').text == date_to_str(localize_date(now))


def test_csv_dumps_simple():
    """Test simple input for csv dumps."""
    body = {'data': [{'a': 1, 'b': 2.5, 'c': True}]}
    response = csv.dumps(body)
    assert 'true' in response
    assert '2.5' in response
    assert '1' in response


def test_csv_dumps_regular_data():
    """Test regular data (csv dumps)."""
    data = {'data': [{"a": 100, "b": 200}, {"a": 150, "b": 250}]}
    dumped_lines = csv.dumps(data).split("\n")
    assert dumped_lines[0].strip() in ('a,b', 'b,a')
    assert dumped_lines[1].strip() in ('100,200', '200,100')
    assert dumped_lines[2].strip() in ('150,250', '250,150')


def test_csv_dumps_incomplete_data():
    """Test incomplete data."""
    data = {'data': [{"a": 100, "b": 200}, {"a": 150}]}
    dumped_lines = csv.dumps(data).split("\n")
    assert dumped_lines[0].strip('"\r ') in ('a,b', 'b,a')
    assert dumped_lines[2].strip('"\r ') in ('150,', ',150')
    data = {'data': [{"a": 100, "b": 200}, {"c": 150}]}
    dumped_lines = csv.dumps(data).split("\n")
    assert dumped_lines[2].strip('"\r ') == ','


def test_csv_dumps_encoding():
    """
    Dump weird characters in internal representation to unicode text.

    Dump them without problems.
    """
    body = {'data': [{'a': '€9.80', 'b': 'Cëöß', 'c': 'äbc'}]}
    response = csv.dumps(body)
    assert '€9.80' in response
    assert 'Cëöß' in response
    assert 'äbc' in response


def test_csv_dumps_str():
    """A string and a unicode come in, one unicode comes out (csv.dump)."""
    uni = {'data': [{"foreigner": "H\xf6nëng"}]}
    header, value = csv.dumps(uni).split()
    assert header == 'foreigner'
    assert value == '"H\xf6nëng"'


def test_csv_dumps_date():
    """Test date (csv dumps)."""
    now = datetime.datetime.now()
    response = csv.dumps({'data': [{'now': now}]})
    assert response.split("\n")[1].strip('"\r') == date_to_str(localize_date(now))


def test_for_py_dumps():
    """Test py.dumps."""
    data = {'my': 'test', 2: 'data'}
    assert eval(py.dumps(data)) == data


def test_csv_loads_json_returns_dict():
    """Test json as body input will return dict."""
    body = '{"a":1, "b":2}'
    assert csv_loads(body) == json_py.loads(body)


def test_csv_loads_csv_input_with_headers():
    """Test csv import with headers that returns dict."""
    body = 'name,surname,color\ntest_name,test_surname,"test, color"'

    headers = {'x-spynl-delimiter': ',', 'x-spynl-quotechar': '"'}
    dict_reader = csv_loads(body, headers)['data'][0]
    assert dict_reader['color'] == 'test, color'


def test_csv_loads_csv_import_without_headers_returns_dict():
    """Test csv import with headers, returns dict object."""
    body = 'name,surname,color\ntest_name,test_surname,test_color'
    dict_reader = csv_loads(body)['data'][0]
    result = {'name': 'test_name', 'surname': 'test_surname', 'color': 'test_color'}
    assert dict_reader == result


def test_csv_loads_csv_import_with_only_delimiter_specified_in_headers():
    """
    Test csv import with only delimiter specified in headers.

    Return correct dict, even if we have , in our body.
    """
    body = 'name,surname,color\ntest_name,test_surname,"test, color"'
    headers = {'x-spynl-delimiter': ',', 'x-spynl-quotechar': ''}
    dict_reader = csv_loads(body, headers)['data'][0]
    result = {'name': 'test_name', 'surname': 'test_surname', 'color': 'test, color'}
    assert dict_reader == result


def test_csv_loads_csv_import_with_only_quotechar_in_headers():
    """
    Test csv import with only quotechar specified in headers.

    Returns correct dict with correct identified delimiter.
    """
    body = (
        'a,b,\nc,d,\ne,f,\ng,h,\ni,j,\nk,l,\nm,n,\no,p,\nq,r,\n'
        's,"t, @",\nu,v,\nw,x,\ny,z'
    )
    headers = {'x-spynl-delimiter': '', 'x-spynl-quotechar': '"'}
    dict_reader = csv_loads(body, headers)['data'][8]
    assert dict_reader['b'] == 't, @'


def test_csv_loads_csvimport_with_datefield(app):
    """
    Test CSV import with a 'date' field present.

    Gets parsed into DateTime object.
    """
    body = 'name,surname,date\ntest_name,test_surname,2013-10-10T10:11:12'
    data = csv_loads(body)['data'][0]
    assert data['date'].year, 2013
    assert data['date'].month, 10
    assert data['date'].day, 10
    assert data['date'].hour, 10
    assert data['date'].minute, 11


def test_decimal_json_dumps():
    """test dumping decimals to floats."""
    assert dumps({'a': Decimal(1)}, 'application/json') == '{"a": 1.0}'
