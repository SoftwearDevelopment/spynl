"""
Utils to get info about Spynl packages
"""

import os
import configparser
from collections import namedtuple
import subprocess

from pkg_resources import iter_entry_points, get_distribution  # pylint: disable=E0611

from spynl.main.utils import chdir
from spynl.main.exceptions import SpynlException


# mocking some package info pip.get_distributed_packages provides
Package = namedtuple('Package', ['project_name', 'version', 'location',
                                 'scm_url'])


SPYNL_DISTRIBUTION = get_distribution(__package__.split('.')[0])


def read_setup_py(path):
    """return contents of setup.py"""
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
    packages = {
        Package(
            plugin.dist.project_name,
            plugin.dist.version,
            plugin.dist.location,
            lookup_scm_url(plugin.dist.location) if include_scm_urls else None

        ) for plugin in iter_entry_points('spynl.plugins')
    }

    packages.add(Package(
        SPYNL_DISTRIBUTION.project_name,
        SPYNL_DISTRIBUTION.version,
        SPYNL_DISTRIBUTION.location,
        lookup_scm_url(SPYNL_DISTRIBUTION.location) if include_scm_urls else None
    ))

    return packages


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


def lookup_scm_commit(package_location):
    """Look up the SCM commit ID for a package."""
    with chdir(package_location):
        if os.path.exists('.git'):
            cmd = 'git rev-parse HEAD'
        elif os.path.exists('.hg'):
            cmd = 'hg id -i'
        else:
            return None
        cmd_result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                                    universal_newlines=True)
        return cmd_result.stdout.strip()


def lookup_scm_commit_describe(package_location):
    """
    Look up the SCM commit ID to give the version and, if the latest commit is
    not that of the version tag, the commit number (for git, hg works slightly
    differently)
    """
    with chdir(package_location):
        if os.path.exists('.git'):
            cmd = 'git describe --dirty'
        elif os.path.exists('.hg'):
            cmd = 'hg log -r . --template '\
              '"{latesttag}-{latesttagdistance}-{node|short}\n"'
        else:
            return None
        cmd_result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                                    universal_newlines=True)
        return cmd_result.stdout.strip()


def get_config_package(require=None):
    """
    Return the config package. Complain if several packages have the
    .ini files.
    """
    config_package = None
    if require is None:
        require = ('development.ini', 'production.ini')
    if not isinstance(require, (list, tuple,)):
        require = (require,)
    packages = get_spynl_packages()
    for package in packages:
        plisting = os.listdir(package.location)
        if all([ini in plisting for ini in require]):
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
    config.read('%s/development.ini' % config_package.location)
    return config['app:main']
