"""
Utils to get info about Spynl packages
"""

import os
import configparser
import subprocess

from pkg_resources import iter_entry_points, get_distribution  # pylint: disable=E0611

from spynl.main.utils import chdir


SPYNL_DISTRIBUTION = get_distribution(__package__.split('.')[0])


def get_spynl_packages():
    """
    Return the (locally) installed spynl packages.
    The term 'package' is the preferred term, synonymous with 'distribution':
    https://packaging.python.org/glossary/#term-distribution-package
    We ask for packages in a separate pip process, so we catch latest
    ones installed earlier in this context.

    If include_scm_urls is True, this function also looks up the
    SCM Url of each package and stores it as "scm_url".
    """
    packages = {
        plugin.dist for plugin in iter_entry_points('spynl.plugins')
    }
    packages.add(SPYNL_DISTRIBUTION)
    return packages


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


def get_ini_files(packages=None):
    """
    Return the config package. Complain if several packages have the
    .ini files.
    """

    ini_files = []

    for package in packages or get_spynl_packages():
        ini = os.path.join(package.location, 'development.ini')
        if os.path.exists(ini):
            ini_files.append(ini)

    return ini_files


# def get_dev_config(packages=None):
#     """Return the ConfigParser for development.ini"""
#     config = configparser.ConfigParser()
#     config_package = get_ini_files()
#     if config_package is None:
#         return {}
#     config.read('%s/development.ini'  % config_package.location)
#     return config['app:main']
