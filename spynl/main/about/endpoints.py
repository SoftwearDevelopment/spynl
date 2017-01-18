"""
This module provides information for version, db, build and enviroment.
"""

import sys
import os
from subprocess import check_output
import pip

from pyramid.renderers import render
from pyramid.httpexceptions import HTTPFound

from spynl.main.version import __version__ as spynl_version
from spynl.main.utils import get_settings
from spynl.main.locale import SpynlTranslationString as _
from spynl.main.dateutils import now, date_to_str
from spynl.main.docs.settings import ini_doc, ini_description
from spynl.main.docs.documentation import HIDE_TRYITOUT_IDS
from spynl.main.pkg_utils import (get_spynl_package,
                                  get_dev_config,
                                  get_spynl_packages)


def hello(request):
    """
    The index for all about-endpoints.

    ---
    get:
      description: >
        The index for all about-endpoints.

        ####Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        message   | string | Information about the available about/*
        endpoints.\n
        spynl_version | string | The version of this Spynl instance.\n
        language  | string | The language (e.g. "en") served.\n
        time      | string | Time in format: $setting[spynl.date_format]\n

      tags:
        - about
      show-try: true
    """
    return {'message': _('about-message',
                         default='This is the Spynl API/Middleware. '
                                 'You can get more information at '
                                 'about/endpoints, about/ini, about/versions, '
                                 'about/build and about/environment.'),
            'spynl_version': spynl_version,
            'language': request._LOCALE_,
            'time': date_to_str(now())}


def endpoint_doc(request):
    """
    All endpoints offered by this instance, with explanations.

    ---
    get:
      tags:
        - about
      description:
        Presented as text/html (in swagger-ui).
        Requires 'read' permission for the 'about' resource.
    show-try: No
    """
    request.response.content_type = 'text/html'
    path2swagger = '{}/../docs/swagger-ui/index.html'\
                   .format('/'.join(os.path.abspath(__file__).split('/')[:-1]))
    index = open(path2swagger, 'r').read()
    static_url = request.static_url('spynl.main:docs/swagger-ui/')
    # We would like to treat the swagger-ui directory as a drop-in
    # replacable dir, so we simply re-create the HTML by doing some
    # replacements.
    index = index.replace("<title>Swagger UI",
                          "<title>Spynl Endpoints Documentation")
    index = index.replace("http://petstore.swagger.io/v2/swagger.json",
                          "{}spynl.json".format(static_url))
    index = index.replace("href='css", "href='{}css".format(static_url))
    index = index.replace("src='", "src='{}".format(static_url))
    # We'll now add some CSS before the body closes
    # We hide the Swagger head
    css = '#header {display:none; !important}'
    # We hide the parameter sandbox for some views
    for htio_id in HIDE_TRYITOUT_IDS:
        css += '{} .sandbox {{display:none; !important}}'.format(htio_id)
    ins = index.find('</body>')
    index = index[:ins] + '<style>' + css + '</style></body></html>'

    return index


def schemas(request):
    """
    Using docson to display any relevant JSON schemas used by Spynl.

    ---
    get:
      tags:
        - about
      description: >
        Schema files are read from an internal Spynl location and
        Presented as text/html (using docson).
        This endpoint requires 'read' permission for the 'about' resource.
        It is linked from by /about/doc when schemas are used for
        validations by an endpoint.

        ####Parameters

        JSON keys |   Type   |    Req.     | Description\n
        --------- | -------- | ----------- | --------- \n
        schema    |   string |  &#10004;   | Name of the schema file. \n

    show-try: No
    """
    request.response.content_type = 'text/html'
    static_url = request.static_url('spynl.main:docs/docson/')
    schema = request.args.get('schema')
    if not schema.endswith('.json'):
        schema = schema + '.json'
    return HTTPFound("{}#schemas/{}".format(static_url, schema))


def versions(request):
    """
    The changeset IDs of Spynl and all installed plugins.

    ---
    get:
      tags:
        - about
      description: >
        Requires 'read' permission for the 'about' resource.

        ####Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        plugins   | dict   | "spynl.plugin": "SCM checkin id" for each Spynl
        plugin. Currently works only with mercurial.\n
        spynl_version | string | The version of this Spynl instance.\n
        time      | string | time in format: $setting[spynl.date_format]\n

    """
    spynl_settings = get_settings()
    dev_config = get_dev_config()

    response = dict(spynl_version=spynl_version)
    response['time'] = date_to_str(now())

    # Plugins
    response['plugins'] = {}
    packages = get_spynl_packages()
    cmd = 'git log --format="%H" -n 1'
    if dev_config.get('scm_type') == 'hg':
        cmd = 'hg id -i 2>&1'
    # TODO: if pip-installed, we'll have to ask pip explicitly for spynl
    spynl = get_spynl_package('spynl', packages)
    try:
        os.chdir(spynl.location)
        response['plugins']['spynl'] = \
                check_output(cmd, shell=True).strip()
    except Exception as err:
        response['plugins']['spynl'] = str(err)
    for package in packages:
        try:
            os.chdir(package.location)
            response['plugins'][package.project_name] = \
              check_output(cmd, shell=True).strip()
        except Exception as err:
            response['plugins'][package.project_name] = str(err)
    return response


def build(request):
    """
    Information about the build of this instance.

    ---
    get:
      tags:
        - about
      description: >

        ####Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        build_time| string | time in format: $setting[spynl.date_format]\n
        start_time| string | time in format: $setting[spynl.date_format]\n
        build_number | string | The build number, set by Jenkins\n
        spynl_function| string | Which functionality this node has been spun up
        to fulfil\n
        time      | string | time in format: $setting[spynl.date_format]\n
    """
    spynl_settings = get_settings()
    response = {}

    response['time'] = date_to_str(now())
    response['build_time'] = spynl_settings.get('spynl.ops.build_time', None)
    response['start_time'] = spynl_settings.get('spynl.ops.start_time', None)
    response['build_number'] = spynl_settings.get('spynl.ops.build_number', None)
    response['spynl_function'] = spynl_settings.get('spynl.ops.function', None)

    return response


def environment(request):
    """
    All software packages installed by pip for this instance.

    ---
    get:
      tags:
        - about
      description: >
        Requires 'read' permission for the 'about' resource.

        ####Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        time      | string | time in format: $setting[spynl.date_format]\n
        python    | string | Python version\n
        pip-installed-packages | dict | "name":"version" for each package.\n
    """
    response = dict(time=date_to_str(now()))
    vi = sys.version_info
    response['python'] = "%s.%s.%s" % (vi.major, vi.minor, vi.micro)
    response['pip-installed-packages'] = {}
    installed_packages = pip.get_installed_distributions()
    for package in [p for p in installed_packages
                    if not p.key.startswith('spynl')]:
        response['pip-installed-packages'][package.key] = package.version

    return response


def ini(request):
    """
    A table of all Spynl ini settings in this instance.

    ---
    get:
      tags:
        - about
      description: >
        Presented as a text/html table. Columns for name of the setting,
        the value in this instance, whether it is required, default value
        and text description.


        Requires 'read' permission for the 'about' resource.
    """
    spynl_settings = get_settings()
    for i, setting in enumerate(ini_doc):
        ini_doc[i]['value'] = str(spynl_settings.get(setting['name']))

    request.response.content_type = 'text/html'
    result = render('spynl.main:docs/ini.jinja2',
                    {'settings': ini_doc,
                     'description': ini_description},
                    request=request)
    return result
