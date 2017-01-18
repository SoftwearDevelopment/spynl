import os
import contextlib
from invoke.exceptions import Exit

from spynl.main.pkg_utils import get_spynl_package, get_spynl_packages


def resolve_packages_param(packages_param, complain_not_installed=True,
                           to='package-names'):
    """
    Resolve "packages" string parameter (a CSV list) into a list
    of installed package names, or alternatively their SCM url
    (if to=='scm-urls').

    The param has the special value "_all" in which case we return
    all installed spynl packages.
    """
    installed_packages = get_spynl_packages(include_scm_urls=to=='scm-urls')
    if packages_param != '_all':
        pnames = [pn.strip() for pn in packages_param.split(',')]
        for name in pnames:
            if (name != 'spynl'
                and name not in [p.project_name for p in installed_packages]):
                if complain_not_installed:
                    raise Exit("Package %s is not installed. Exiting ..." % name)
        packages = [p for p in installed_packages if p.projectname in pnames]
    else:
        packages = installed_packages
    if to == 'scm-urls':
        return [p.scm_url for p in installed_packages]
    else:
        return [p.project_name for p in installed_packages]


@contextlib.contextmanager
def package_dir(package_name=None):
    """Change to this package's directory during this context"""
    curdir = os.getcwd()
    try:
        if package_name is not None:
            package = get_spynl_package(package_name)
            if package is not None:
                os.chdir(package.location)
        yield
    finally:
        os.chdir(curdir)


@contextlib.contextmanager
def chdir(dirname=None):
    """Change to this directory during this context"""
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)


def assert_response_code(response, exp_code):
    """
    Make it easy to expect one or more HTTP status codes
    in a requests library response.
    """
    code = response.status_code
    if isinstance(exp_code, tuple):
        if not code in exp_code:
            raise Exit("Code %s is not in %s when testing %s"
                       % (code, exp_code, response.request.url))
    else:
        if not code == exp_code:
            raise Exit("Code %s was expected to be %s when testing %s "
                       % (code, exp_code, response.request.url))
