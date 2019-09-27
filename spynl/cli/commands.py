import json
import shutil
import os
import subprocess
import sys
import configparser

import click
from babel.messages.pofile import read_po

from spynl.main.version import __version__ as spynl_version
from spynl.cli.utils import resolve_packages, check_ini, run_command, fail
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
    '-p',
    '--packages',
    multiple=True,
    callback=resolve_packages,
    help='Packages to operate on.',
)


language_option = click.option(
    '-l',
    '--languages',
    multiple=True,
    default=['nl', 'en', 'de', 'fr', 'es', 'it'],
    help=(
        'A language code such as "en" or "nl". '
        'Can be provided multiple times for multiple languages.'
    ),
)


ini_option = click.option(
    '-i',
    '--ini',
    help='Specify an ini file to use.',
    type=click.Path(exists=True),
    callback=check_ini,
)

task_option = click.option(
    '-t', '--task', type=click.Choice(['dev', 'latest']), default='dev'
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
                'scmVersion': lookup_scm_commit_describe(package.location),
            }
        }
        if package.project_name == SPYNL_DISTRIBUTION.project_name:
            versions.update(info)
        else:
            versions['plugins'].update(info)

    versions_path = os.path.join(sys.prefix, 'versions.json')
    with open(versions_path, 'w') as f:
        versions = json.dumps(versions, indent=4)
        print(versions, file=f)
    click.echo('Installed versions file successfully.')
    click.echo(versions)


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
                fail("Tests for {} failed".format(pkg.project_name))
            else:
                msg = 'Do you wish to continue?'
                if idx != len(packages) and not click.confirm(msg):
                    fail('Aborting at user request.')


@dev.command()
@click.option(
    '--force', '-f', is_flag=True, default=False, help='Overwrite existing hooks'
)
@package_option
def install_git_hooks(force, packages):
    """Install git hooks"""
    dependencies = ['flake8', 'flake8-breakpoint', 'black']
    cmd = sys.executable + ' -m pip install {}'.format(' '.join(dependencies))
    run_command(cmd, check=True)

    def resolve_package_hook_path(pkg):
        return os.path.join(pkg.location, '.git', 'hooks', 'pre-commit')

    if not force:
        existing_hooks = []
        for pkg in packages:
            hook_path = resolve_package_hook_path(pkg)
            if os.path.exists(hook_path):
                existing_hooks.append(hook_path)
        if existing_hooks:
            msg = 'Please back up existing hooks before running this command.\n{}'
            fail(msg.format('\n'.join(existing_hooks)))

    for pkg in packages:
        hook_path = resolve_package_hook_path(pkg)
        shutil.copy(os.path.join(SPYNL_DISTRIBUTION.location, 'pre-commit'), hook_path)
        click.echo('Installed {}'.format(hook_path))


@dev.command()
@ini_option
def serve(ini):
    """Run a local server."""
    run_command('pserve {} --reload'.format(ini))


@dev.command()
@ini_option
def generate_documentation(ini):
    """Run a local server."""
    os.environ['GENERATE_SPYNL_DOCUMENTATION'] = 'generate'
    run_command('pserve {}'.format(ini))


@dev.command()
@package_option
@language_option
@click.option(
    '--refresh', '-r', help='Refresh the translations calalogs.', is_flag=True
)
@click.option(
    '--no-location',
    '-n',
    help='Remove the comments (locations) from the .pot and .po file',
    is_flag=True,
)
@click.option(
    '--add-comments',
    '-c',
    help=(
        'Add translator comments from the code (translator comments'
        ' should start with #.)'
    ),
    is_flag=True,
)
def translate(packages, languages, refresh, no_location, add_comments):
    """Perform translation tasks."""
    base_command = sys.executable + ' setup.py '

    for package in packages:
        os.chdir(package.location)

        if refresh:
            cmd = base_command + 'extract_messages'
            if no_location:
                cmd += ' --no-location'
            if add_comments:
                cmd += ' --add-comments .'
            run_command(cmd)

            for lang in languages:
                try:
                    run_command(base_command + 'update_catalog -l ' + lang, check=True)
                except subprocess.CalledProcessError:
                    # po file does not exist
                    run_command(base_command + 'init_catalog -l ' + lang)

        for lang in languages:
            run_command(base_command + 'compile_catalog -l ' + lang)


@dev.command()
@package_option
@language_option
@click.pass_context
def extract_missing_translations(ctx, packages, languages):
    """ extract the messages that still need to be translated """
    wd = os.getcwd()
    # prepare files with comments:
    ctx.invoke(
        translate,
        packages=packages,
        languages=languages,
        refresh=True,
        no_location=True,
        add_comments=True,
    )

    for package in packages:
        os.chdir(package.location)
        config = configparser.ConfigParser()
        config.read('setup.cfg')
        try:
            domain = config['update_catalog']['domain']
            output_dir = config['update_catalog']['output_dir']
        # package is not configured for translations
        except KeyError:
            continue
        json_messages = {}

        # Use English as the standard:
        filename = os.path.join(output_dir, 'en', 'LC_MESSAGES', domain + '.po')
        with open(filename, 'r') as f:
            en_messages = read_po(f)._messages
        # Check the English messages, fail if there is one missing:
        for message_id, message in en_messages.items():
            if not message.string:
                fail('missing English message: {} in {}'.format(message_id, filename))

        warnings = []
        for lang in [lang for lang in languages if lang != 'en']:
            filename = os.path.join(output_dir, lang, 'LC_MESSAGES', domain + '.po')
            with open(filename, 'r') as po_file:
                po_messages = read_po(po_file)._messages

            for message_id, message in po_messages.items():
                if not message.string:
                    warnings.append(
                        'missing message: {} in {}'.format(message_id, filename)
                    )
                # if it's not the same as en, it doesn't need to be translated
                # + we do not want to translate locale_id's for now.
                elif (
                    message.string != en_messages[message_id].string
                    or 'locale_id' in message_id
                ):
                    continue
                json_messages[message_id] = {
                    'message': en_messages[message_id].string,
                    'description': str(en_messages[message_id].auto_comments),
                }

        if json_messages:
            filename = os.path.join(wd, domain + '.json')
            with open(filename, 'w') as outfile:
                print('Writing file: {}'.format(filename))
                json.dump(json_messages, outfile, sort_keys=True, indent=4)

    # restore files:
    ctx.invoke(
        translate,
        packages=packages,
        languages=languages,
        refresh=True,
        no_location=True,
        add_comments=False,
    )

    # print warnings after all the other output:
    if warnings:
        print('\n\nWarnings:\n')
    for warning in warnings:
        print(warning)


@dev.command()
def build_spynl():
    """build spynl dev"""
    run_command(
        'git fetch && git rebase origin/dev &&'
        ' git submodule update --remote && git commit -am build &&'
        ' git push'
    )
