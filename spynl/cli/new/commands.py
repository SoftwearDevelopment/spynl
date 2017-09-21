import json
import os
import subprocess
import sys

import click

from spynl.main.version import __version__ as spynl_version
from spynl.cli.new.utils import resolve_packages, check_ini, run_command, exit
from spynl.main.pkg_utils import (
    SPYNL_DISTRIBUTION,
    lookup_scm_commit,
    lookup_scm_commit_describe,
    get_spynl_packages,
)


@click.group()
@click.version_option(spynl_version)
def cli():
    """Entry point for all commands."""


@cli.group()
def dev():
    """entry point for dev commands."""


package_option = click.option(
    '-p', '--packages',
    multiple=True,
    callback=resolve_packages,
    help='Packages to operate on.'
)

ini_option = click.option(
    '-i', '--ini',
    help='Specify an ini file to use.',
    type=click.Path(exists=True),
    callback=check_ini
)

task_option = click.option(
    '-t', '--task',
    type=click.Choice(['dev', 'latest']),
    default='dev'
)


@dev.command()
def versions():
    """Generate a human readable json file specifiying the versions in use."""
    versions = {'plugins': {}}
    for package in get_spynl_packages():
        info = {
            package.project_name: {
                'version': package.version,
                'commit': lookup_scm_commit(package.location),
                'scmVersion': lookup_scm_commit_describe(package.location)
            }
        }
        if package.project_name == SPYNL_DISTRIBUTION.project_name:
            versions.update(info)
        else:
            versions['plugins'].update(info)

    versions_path = os.path.join(sys.prefix, 'versions.json')
    with open(versions_path, 'w') as f:
        print(json.dumps(versions, indent=4), file=f)


@dev.command()
@package_option
@click.option('--reports', is_flag=True)
@click.option('--non-interactive', is_flag=True)
@click.option('--reports', is_flag=True)
@click.argument('pytest-options', nargs=-1)
def test(packages, reports, non_interactive, pytest_options):
    """Run tests."""
    cmd = sys.executable + ' -m pytest '

    if reports:
        cmd += ' --cov=spynl '

    for idx, pkg in enumerate(packages, start=1):
        cmd += ' '.join(pytest_options)

        os.chdir(pkg.location)
        try:
            run_command(cmd, check=True)
        except subprocess.CalledProcessError:
            if non_interactive:
                exit("Tests for {} failed".format(pkg.project_name))

            msg = ('Tests for {} failed. Do you wish to continue?'.format(
                pkg.project_name))

            if idx == len(packages):
                click.echo(msg, err=True)
            elif not click.confirm(msg):
                exit("Aborting at user request.")


@dev.command()
@ini_option
def serve(ini):
    """Run a local server."""
    run_command('pserve {} --reload'.format(ini))


@dev.command()
@package_option
@click.option('-l', '--languages',
              multiple=True,
              default=['nl'],
              help=('A language code such as "en" or "nl". '
                    'Can be provided multiple times for multiple languages. ')
              )
@click.option('--refresh', '-r',
              help='Refresh the translations calalogs.',
              is_flag=True)
def translate(packages, languages, refresh):
    """Perform translation tasks."""
    base_command = sys.executable + ' setup.py '

    for package in packages:
        os.chdir(package.location)

        if refresh:
            run_command(base_command + 'extract_messages')

            for lang in languages:
                try:
                    run_command(base_command + 'update_catalog -l ' + lang,
                                check=True)
                except subprocess.CalledProcessError:
                    # po file does not exist
                    run_command(base_command + 'init_catalog -l ' + lang)

        for lang in languages:
            run_command(base_command + 'compile_catalog -l ' + lang)
