import os
# import contextlib
import subprocess
import shlex

import click

from spynl.main.pkg_utils import get_spynl_packages, SPYNL_DISTRIBUTION, \
    get_ini_files


def exit(msg):
    click.get_current_context().fail(msg)


def run_command(command, **kwargs):
    return subprocess.run(shlex.split(command), **kwargs)


def resolve_packages(ctx, param, value):
    """
    Callback that resolves the value into a set of packages.
    """
    value = {v.lower() for v in value}

    packages = get_spynl_packages()

    if value:
        not_installed = value - {p.project_name.lower() for p in packages}
        if not_installed:
            msg = '{} is/are not installed. Exiting ...'.format(
                    ', '.join(not_installed))
            exit(msg)

        packages = list(filter(lambda p: p.project_name.lower() in value, packages))
    return packages


def check_ini(ctx, param, value):
    if value:
        return value

    ini_files = get_ini_files()

    if len(ini_files) == 1:
        value = ini_files[0]

    elif len(ini_files) > 1:
        click.echo('\n'.join([
            '{}:\t{}'.format(i + 1, ini) for i, ini in enumerate(ini_files)
        ]))
        i = click.prompt('Which ini file should be used', type=int, default=0)
        try:
            value = ini_files[i - 1]
        except IndexError:
            raise click.BadParameter('Choices are between 1 and {}'.format(len(ini_files)))
    else:
        value = os.path.join(SPYNL_DISTRIBUTION.location, 'minimal.ini')

    return value
