"""
Utils to get info about Spynl packages
"""

import os
import configparser
from collections import namedtuple
import subprocess

from spynl.main.exceptions import SpynlException


def read_setup_py(path):
    """return contents of setup.py"""
    content = ''
    with open('%s/setup.py' % path, 'r') as setup:
        return ''.join(setup.readlines())


def get_spynl_packages(include_scm_urls=False):
    """
    Return the (locally) installed spynl-plugin packages.
    The term 'package' is the preferred term, synonymous with 'distribution':
    https://packaging.python.org/glossary/#term-distribution-package
    We ask for packages in a separate pip process, so we catch latest
    ones installed earlier in this context.

    If include_scm_urls is True, this function also looks up the
    SCM Url of each package and stores it as "scm_url".
    """
    # mocking some package info pip.get_distributed_packages provides
    Package = namedtuple('Package', ['project_name', 'version', 'location',
                                     'scm_url'])
    installed_packages = []
    # --format json does not return locations :(
    plist = subprocess.run('pip list -l --format columns',
                           shell=True, stdout=subprocess.PIPE,
                           universal_newlines=True)
    for pinfo in [line for line in plist.stdout.split("\n")[2:]
                  if line.strip() != ""]:
        pinfo = pinfo.split()
        pname = pinfo[0]
        if len(pinfo) > 2:  # we need a location
            pversion = pinfo[1]
            plocation = pinfo[2]
            purl = None
            if include_scm_urls:
                purl = lookup_scm_url(plocation)
            package = Package(pname, pversion, plocation, purl)
            if 'spynl.plugins' in read_setup_py(plocation):
                installed_packages.append(package)
    return installed_packages


def get_spynl_package(name, packages=None):
    """Return the installed spynl package."""
    if packages is None:
        packages = get_spynl_packages()
    return next(filter(lambda p: p.project_name == name, packages),
                None)


def lookup_scm_url(package_location):
    """Look up the SCM URL for a package."""
    scm_cfg = configparser.ConfigParser()
    if os.path.exists('%s/.git' % package_location):
        scm_cfg.read('%s/.git/config' % package_location)
        if 'remote "origin"' in scm_cfg:
            return scm_cfg['remote "origin"'].get('url')
    elif os.path.exists('%s/.hg' % package_location):
        scm_cfg.read('%s/.hg/hgrc' % package_location)
        if 'paths' in scm_cfg:
            return scm_cfg['paths'].get('default')


def get_config_package():
    """
    Return the config package. Complain if several packages have the 
    .ini files.
    """
    config_package = None
    packages = get_spynl_packages()
    for package in packages:
        plisting = os.listdir(package.location)
        if 'development.ini' in plisting and 'production.ini' in plisting:
            if config_package is not None:
                emsg = ("Two packages have configurations (development.ini "
                        "and production.ini): %s and %s. unsure which to use!"
                        % (config_package.project_name, package.project_name))
                raise SpynlException(emsg)
            config_package = package
    return config_package


def get_dev_config():
    """Return the ConfigParser for development.ini"""
    config = configparser.ConfigParser()
    config_package = get_config_package()
    if config_package is None:
        return {}
    config.read('%s/development.ini'  % config_package.location)
    return config['app:main']
