"""
This module provides information for version, db, build and enviroment.
"""

import sys
import os
import json

from pyramid.renderers import render
from pyramid.i18n import negotiate_locale_name

from spynl.main.exceptions import SpynlException
from spynl.main.version import __version__ as spynl_version
from spynl.main.utils import get_settings
from spynl.main.locale import SpynlTranslationString as _
from spynl.main.dateutils import now, date_to_str
from spynl.main.docs.settings import ini_doc, ini_description
from spynl.main.pkg_utils import get_spynl_packages


def hello(request):
    """
    The index for all about-endpoints.

    ---
    get:
      description: >
        The index for all about-endpoints.

        ### Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        message   | string | Information about the available about/*
        endpoints.\n
        spynl_version | string | The version of the spynl package in this
        instance.\n
        plugins | dict | For each installed spynl plugin, the name as key
        and the version as value.\n
        language  | string | The language (e.g. "en") served.\n
        time      | string | Time in format: $setting[spynl.date_format]\n

      tags:
        - about
      show-try: true
    """
    plugin_versions = {}
    packages = get_spynl_packages()
    for package in packages:
        plugin_versions[package.project_name] = package.version
    return {
        'message': _('about-message'),
        'spynl_version': spynl_version,
        'plugins': plugin_versions,
        'language': negotiate_locale_name(request),
        'time': date_to_str(now()),
    }


def versions(request):
    """
    The changeset IDs of Spynl and all installed plugins.

    ---
    get:
      tags:
        - about
      description: >
        Requires 'read' permission for the 'about' resource.

        ### Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        spynl     | dict   | {commit: SCM commit id of the HEAD,
        version: package version, scmVersion: state of the working directory,
        will show version and commit, and dirty if the working directory
        contains uncommited changes}.\n
        plugins   | dict   | {spynl-plugin: {commit: SCM commit id of the HEAD,
        version: package version, scmVersion: state of the working directory,
        will show version and commit, and dirty if the working directory
        contains uncommited changes}} for each Spynl plugin.\n
        time      | string | time in format: $setting[spynl.date_format]\n
    """
    try:
        with open(os.path.join(sys.prefix, 'versions.json')) as f:
            response = json.loads(f.read())
        response['time'] = date_to_str(now())
    except FileNotFoundError:
        raise SpynlException('Version information not found')
    return response


def build(request):
    """
    Information about the build of this instance.

    ---
    get:
      tags:
        - about
      description: >

        ### Response

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
    response['spynl_function'] = spynl_settings.get('spynl.ops.function', None)
    response['build_number'] = spynl_settings.get('spynl.ops.build_number', None)

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
    result = render(
        'spynl.main:docs/ini.jinja2',
        {'settings': ini_doc, 'description': ini_description},
        request=request,
    )
    return result
