"""
Module for parsing docstrings and making the .json file for swagger-ui
"""

from os import path as osp
import json
import glob
import re
import yaml

from pyramid.settings import asbool

from spynl.main.version import __version__ as spynl_version
from spynl.main.utils import get_logger, get_yaml_from_docstring
from spynl.main.docs.settings import get_ini_doc_setting


extended_description = '''
All endpoints usually return application/json, unless otherwise
specified here or requested differently by the request.
They will have a "status" (ok|error) field and all error responses
also will have a "message" field.
'''


swagger_doc = {
    'swagger': '2.0',
    'info': {
        'version': spynl_version,
        'title': 'Spynl Endpoints',
        'description': 'A list of all endpoints on this Spynl instance,'
                       ' with a short description on how to use them.'
                       ' <br/><br/><span style="color: grey;">{}<span>'
                       .format(extended_description)
    },
    'paths': {},
    'definitions': {}
}


# list of endpoints where we hide the sandbox
HIDE_TRYITOUT_IDS = []


def document_endpoint(config, function, endpoint_name, resource=None):
    """parse docstring and store in swagger_doc dict"""
    log = get_logger('Spynl Documentation')

    path = '/{}'.format(endpoint_name)
    yaml_str = get_yaml_from_docstring(function.__doc__, load_yaml=False)

    if not yaml_str:
        log.warning("No YAML found in docstring of endpoint %s"
                    " (resource: %s). Cannot generate entry in /about/doc."
                    % (endpoint_name, resource))
    else:
        if resource:
            # Replace $resource in the docstring with the actual resource
            yaml_str = re.sub(r'\$resource', resource, yaml_str)
        try:
            yaml_str = insert_ini_settings(config, yaml_str)
            yaml_doc = yaml.load(yaml_str)
            # If a path has a different view for get and post, add both
            if path in swagger_doc['paths']:
                swagger_doc['paths'][path].update(yaml_doc)
            else:
                swagger_doc['paths'][path] = yaml_doc
        except yaml.YAMLError as e:
            log.error('Wrong yaml code for endpoint %s:', path)
            log.error(e)
            return

        if 'validations' in yaml_doc:
            for method in [m for m in ('get', 'post') if m in yaml_doc]:
                valdoc = "#### Validations\n"
                valdoc += "In | Schema | Apply to | Repeat\n"
                valdoc += "------ | ------ | ------ | -----\n"
                if isinstance(yaml_doc['validations'], list):
                    for val in yaml_doc['validations']:
                        if isinstance(val, dict):
                            valdoc += '{}|<a href="{}">{}</a>|{}|{}\n'\
                                    .format(val.get('in'),
                                            '/about/schemas?schema={}'
                                            .format(val.get('schema')),
                                            val.get('schema'),
                                            val.get('apply-to', '*'),
                                            val.get('repeat', 'no'))
                yaml_doc[method]['description'] += valdoc

        if 'show-try' in yaml_doc:
            if not asbool(yaml_doc['show-try']):
                for method in ('get', 'post'):
                    if method in yaml_doc:
                        for tag in yaml_doc.get(method).get('tags', []):
                            htio_id = '#{tag}_{method}{path}'\
                                    .format(tag=tag,
                                            method=method,
                                            path=path)
                HIDE_TRYITOUT_IDS.append(htio_id.replace('-', '_')
                                                .replace(' ', '_')
                                                .replace('/', '_'))

        # the 1st line of a docstring can be used for the swagger summary
        docstring = function.__doc__
        doc_lines = docstring.split("\n")
        if len(doc_lines) > 0:
            first_doc_line = doc_lines[1].strip()
            if first_doc_line == '---':
                first_doc_line = ''
        for method in [m for m in ('get', 'post')
                       if m in swagger_doc['paths'][path]]:
            path_doc = swagger_doc['paths'][path][method]
            if 'summary' not in path_doc or not path_doc['summary']:
                if resource:
                    path_doc['summary'] = re.sub(r'\$resource', resource,
                                                 first_doc_line)
                else:
                    path_doc['summary'] = first_doc_line


def make_docs(config):
    """Write swagger file. Get definitions from files first."""
    log = get_logger('Spynl Documentation')

    # add definitions from files
    def_folder = 'spynl/main/docs/definitions'
    definitions = glob.glob('%s/*.yml' % def_folder)
    for definition in definitions:
        try:
            with open(definition, 'r') as current_file:
                # check if the folder contains the definition
                match = re.match(r'%s/(.*)\.yml' % def_folder, definition)
                definition = match.group(1)
                # Read the file first, this will give a more descriptive
                # error message in case there is a yaml error.
                yaml_text = current_file.read()
                yaml_text = insert_ini_settings(config, yaml_text)
                swagger_doc['definitions'][definition] = yaml.load(yaml_text)
        except yaml.YAMLError as e:
            log.error('File %s has yaml errors:', current_file.name)
            log.error(e)
        except IOError as e:
            log.error('I/O error(%s: %s', e.errno, e.strerror)

    # turn swagger_doc into a JSON file
    swagger_file = '{}/swagger-ui/spynl.json'\
                   .format('/'.join(osp.abspath(__file__).split('/')[:-1]))
    try:
        with open(swagger_file, 'w') as outfile:
            json.dump(swagger_doc, outfile, indent=4, separators=(',', ': '),
                      sort_keys=True)
    except IOError as e:
        log.error('I/O error(%s: %s', e.errno, e.strerror)
    except (TypeError, OverflowError, ValueError) as e:
        log.error('Swagger file could not be dumped:')
        log.error(e)


def add_swagger_reusables(config, *args):
    """
    Add definitions from docstrings other than the endpoints.
    This function should be called from the plugger.py of the module.
    Arguments can be any object with a docstring, most probably a function.
    """
    log = get_logger('Spynl Documentation')

    for arg in args:
        docstring = arg.__doc__
        yaml_sep = docstring.find('---')
        tag = re.search('--(parameter|response)?:?([a-zA-Z_-]*?)--', docstring)
        yaml_description = None
        if tag and yaml_sep != -1:
            swagger_type = tag.group(1)
            name = tag.group(2)
            try:
                description = insert_ini_settings(config, docstring[yaml_sep:])
                yaml_description = yaml.load(description)
            except yaml.YAMLError as e:
                log.error('Docstring %s has yaml errors:', arg)
                log.error(e)
            if not yaml_description:
                log.error('No description could be parsed for %s:%s',
                          swagger_type, name)
        else:
            log.error('Docstring %s is missing yaml separation (---)'
                      ' or name tag (--tag--, allowed characters:'
                      ' a-z, A-Z, - and/or _)', arg)
        if swagger_type == 'parameter':
            if 'parameters' not in swagger_doc:
                swagger_doc['parameters'] = {}
            swagger_doc['parameters'][name] = yaml_description
        elif swagger_type == 'response':
            if 'responses' not in swagger_doc:
                swagger_doc['responses'] = {}
            swagger_doc['responses'][name] = yaml_description
        else:
            swagger_doc['definitions'][name] = yaml_description


def insert_ini_settings(config, description):
    """
    Fill in the value of a setting that was set in the ini file.

    The text $setting[setting_name] will be replaced by:
    actual_setting (the setting_name for this Spynl instance)
    """
    log = get_logger('Spynl Documentation')

    settings = config.registry.settings
    flag = re.compile(r'\$setting\[(?P<setting_name>[\S]*?)\]')
    match = flag.search(description)

    while match is not None:
        setting_name = match.group('setting_name')
        setting = settings.get(setting_name)
        if setting is not None:
            description = re.sub(r'\$setting\[' + setting_name + r'\]',
                                 str(setting) + r' (the ' + setting_name +
                                 ' for this Spynl instance)', description)
        else:
            default = None
            setting_doc = get_ini_doc_setting(setting_name)
            if setting_doc is not None:
                default = get_ini_doc_setting(setting_name).get('default')
            if default is not None:
                description = re.sub(r'\$setting\[' + setting_name + r'\]',
                                     str(default) + r' (the ' + setting_name +
                                     ' for this Spynl instance)', description)
            else:
                description = re.sub(r'\$setting\[' + setting_name + r'\]',
                                     setting_name, description)
                log.error('There is no value for setting %s', setting_name)
        match = flag.search(description)

    return description
