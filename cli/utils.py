import os
import contextlib
from collections import namedtuple
from invoke.exceptions import Exit
import pip
import subprocess


def read_setup_py(repo_path):
    """return contents of setup.py"""
    content = ''
    with open('%s/setup.py' % repo_path, 'r') as setup:
        return ''.join(setup.readlines())


def get_spynl_packages():
    """
    Return the installed spynl packages.
    We ask for packages in a separate pip process, so we catch latest
    ones installed earlier in this context.
    """
    # mocking some package info pip.get_distributed_packages provides
    Package = namedtuple('Package', ['project_name', 'location'])
    installed_packages = []
    # --format json does not return locations :(
    plist = subprocess.run('pip list -el --format columns',
                           shell=True, stdout=subprocess.PIPE,
                           universal_newlines=True)
    for pinfo in [line for line in plist.stdout.split("\n")[2:]
                  if line.strip() != ""]:
        pinfo = pinfo.split()
        pname = pinfo[0]
        if pname == 'spynl' or len(pinfo) > 2:  # we need a location to check
            plocation = pinfo[2]
            package = Package(pname, plocation)
            if pname == 'spynl' or 'spynl.plugins' in read_setup_py(plocation):
                installed_packages.append(package)
    return installed_packages


def get_spynl_package(name):
    """Return the installed spynl package."""
    return next(filter(lambda p: p.project_name == name, get_spynl_packages()),
                None)


def resolve_repo_names(repos_param, complain_not_installed=True):
    """resolve repo string parameter into a list of repos"""
    installed_repo_names = [r.project_name for r in get_spynl_packages()]
    installed_repo_names.sort()
    if repos_param != '_all':
        given_names = repos_param.split(',')
        for name in given_names:
            if name not in installed_repo_names and complain_not_installed:
                raise Exit("Repo %s is not installed. Exiting ..." % name)
        return given_names
    return installed_repo_names


@contextlib.contextmanager
def repo(reponame=None):
    """Change to this repo directory during this context"""
    curdir = os.getcwd()
    try:
        if reponame is not None:
            repo = get_spynl_package(reponame)
            if repo is not None:
                os.chdir(repo.location)
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
