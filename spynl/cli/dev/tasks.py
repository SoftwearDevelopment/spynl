"""Main tasks for spynl like intall, server etc."""

import os
from invoke import task
from invoke.exceptions import Exit

from spynl.main.version import __version__ as spynl_version
from spynl.main.utils import chdir
from spynl.main.pkg_utils import get_config_package
from spynl.cli.utils import resolve_packages_param, package_dir

from .utils import get_or_create_locale_path, languages_from_dev_config


PACKAGES_HELP = 'Affected packages, defaults to all installed.'


@task(help={'scm-url': 'The URL needed to clone the repo, either for '
                       'git or mercurial. Please no revision information, '
                       'you can use the revision parameter for that. '
                       'Include the protocol, e.g. ssh or https.',
            'developing': 'If True (default), python setup.py develop is '
                          'used, otherwise install',
            'revision': 'Which revision to update to (default: do not update)',
            'fallbackrevision': 'Use this revision if the repository does not '
                                ' have the target revision.',
            'install-deps': 'If True (default), pre-install dependencies '
                            '(eg. via apt-get).',
            'src-path': 'Desired installation path. Defaults to '
                        '$VIRTUAL_ENV/src directory.'})
def install(ctx, scm_url=None, developing=True, revision=None,
            fallbackrevision=None, install_deps=True, src_path=None):
    """
    Clone a repo, update to revision or fallbackrevision
    and install the Spynl package.
    """
    if scm_url is None:
        raise Exit("[spynl dev.install] Please give the --scm-url parameter.")
    virtualenv_path = os.environ['VIRTUAL_ENV']
    ctx.run('pip install --upgrade setuptools')  # make sure we have the latest
    scm_url = scm_url.strip('/')

    vcs_is_git = scm_url.endswith('.git') or '.git@' in scm_url
    vcs = 'git' if vcs_is_git else 'hg'
    repo_name = scm_url.split('/')[-1]
    if vcs_is_git and repo_name.endswith('.git'):
        repo_name = repo_name[:-4]

    src_path = src_path or (virtualenv_path + '/src')
    repo_path = src_path + '/' + repo_name

    if not os.path.exists(repo_path):
        print("[spynl dev.install] CLONING from ", scm_url)
        os.makedirs(src_path, exist_ok=True)
        path = src_path
        cmd = '{} clone {} {}'.format(vcs, scm_url, repo_name)
    else:
        print("[spynl dev.install] UPDATING ", repo_name)
        path = repo_path
        cmd = '{} pull {}'.format(vcs, '' if vcs_is_git else '--update')

    with chdir(path):
        ctx.run(cmd)

    with chdir(repo_path):
        if revision is not None:
            print('[spynl dev.install] Using revision %s ...' % revision)
            # this might not work for mercurial anymore:
            checkout_cmd = ' checkout' if vcs_is_git else ' update'
            try:
                ctx.run(vcs + checkout_cmd, warn=True)
            except Exception:
                default_branch = 'master' if vcs_is_git else 'default'
                print(
                    '[spynl dev.install] Updating to fallback revision %s ...'
                    % fallbackrevision or default_branch
                )
                cmd = vcs + checkout_cmd + ' ' + default_branch
                ctx.run(cmd)

        if os.path.isfile('./setup.sh'):
            pre_cmd = './setup.sh --pre-install --virtualenv={}'
            pre_cmd += ' --install-dependencies' if install_deps else ''
            ctx.run(pre_cmd.format(virtualenv_path))

        if developing:
            print("[spynl dev.install] DEVELOPING {}".format(repo_name))
            ctx.run('python setup.py develop')
        else:
            print("[spynl dev.install] INSTALLING {}".format(repo_name))
            ctx.run('python setup.py install')
        if os.path.isfile('./setup.sh'):
            ctx.run('./setup.sh --post-install')


@task(help={'ini-file': 'Optional location of an ini-file you want to use to '
                        'serve spynl with, if you do not want to use the '
                        'default.'})
def serve(ctx, ini_file=None):
    """
    Run a local server. The ini-file development.ini is searched for in
    installed Spynl plugins. If there is none, minimal.ini is used.
    """
    if ini_file:
        ini_location = ini_file
        print('[spynl dev.serve] Serving with %s ...' % ini_location)
    else:
        config_package = get_config_package(require='development.ini')
        if config_package is None:
            print('[spynl dev.serve] No config package found. '
                  'Serving with minimal.ini ...')
            path2spynl = os.path.dirname(__file__) + '/../../..'
            ini_location = '%s/minimal.ini' % path2spynl
        else:
            ini_location = '%s/development.ini' % config_package.location
            print('[spynl dev.serve] Serving with %s ...' % ini_location)

    with package_dir('spynl'):
        ctx.run('pserve %s --reload' % ini_location, pty=True)


@task(aliases=('tests',),
      help={'packages': PACKAGES_HELP,
            'called-standalone': 'If False, this task is a pre-task and the '
                                 'user gets to cancel the task flow when '
                                 'tests fail.',
            'reports': 'If True, Junit and Coverage reports will be made '
                       '(requires a few extra packages, '
                       'e.g. for pycoverage).'})
def test(ctx, packages='_all', called_standalone=True, reports=False):
    """
    Perfom tests in one or more spynl plugins.
    """
    for package_name in resolve_packages_param(packages):
        print("[spynl dev.test] Testing package: {}".format(package_name))
        with package_dir(package_name):
            if not reports:
                result = ctx.run('py.test', warn=True)
            else:
                result = ctx.run(
                    'py.test --junit-xml=pytests.xml --cov %s --cov-report xml'
                    ' --cov-append' % package_name
                )
            if result.ok or called_standalone:
                continue

            question = "[spynl dev.test] Tests failed. Continue anyway? Y/n"
            if input(question) not in ('y', 'Y'):
                raise Exit("[spynl dev.test] Aborting at user request.")


@task(help={'packages': PACKAGES_HELP,
            'languages': 'An iterable of language codes (e.g. ("nl",). '
                         'Defaults to the setting "spynl.languages".',
            'action': 'Either "compile" (compile selected languages) or '
                      '"refresh" (extract messages from the source code '
                      'and update the .po files for the selected languages). '
                      'Defaults to "compile".'})
def translate(ctx, packages='_all', languages=None, action='compile'):
    """
    Ensure that translations files are up-to-date w.r.t. to the code. If action
    is set to compile (default), this will compile the catalogs for all
    selected languages. If action is set to refresh, this will extract messages
    from the source code and update the .po files for the selected languages
    (will initialize if necessary).
    """
    refresh = dict(compile=False, refresh=True).get(action)
    if refresh is None:
        raise Exit("[spynl dev.translate] action should be 'compile' or "
                   "'refresh'.")

    languages = languages_from_dev_config() if languages is None else languages
    if languages is None:
        raise Exit('[spynl dev.translate] No languages set and also no '
                   'spynl.languages setting found. Cannot determine which '
                   'catalogues to work on.')

    for package_name in resolve_packages_param(packages):
        with package_dir(package_name):
            if package_name == 'spynl':
                package_name = 'spynl.main'
            print("[spynl dev.translate] Package: %s ..." % package_name)

            locale_path = get_or_create_locale_path()

            if refresh:  # Extract messages from source:
                ctx.run('python setup.py extract_messages '
                        '--output-file {lp}/locale/messages.pot --no-wrap '
                        '--sort-by-file --input-dirs {lp} --project {project} '
                        '--copyright-holder "Softwear BV" --version {v}'
                        .format(lp=locale_path, project=package_name,
                                v=spynl_version))

            for lang in languages:
                path2po = '%s/locale/%s/LC_MESSAGES/%s.po' % (locale_path,
                                                              lang,
                                                              package_name)
                command = get_translation_command(lang, path2po, refresh)
                command = command.format(lp=locale_path, pn=package_name,
                                         lang=lang)
                if command:
                    ctx.run(command)
                print("[spynl dev.translate] Done with language %s." % lang)
                print("--------------------------------------------------")


def get_translation_command(lang, po_file, refresh):
    """Translate package with the given language."""
    msg, command = '', ''
    # update if refresh
    if refresh and not os.path.exists(po_file):  # init if needed:
        msg = ('[spynl dev.translate] File %s does not exist.'
               ' Initializing.' % po_file)
        command = ('python setup.py init_catalog -l {lang} '
                   '-i {lp}/locale/messages.pot -d {lp}/locale -D {pn}')
    elif refresh:  # update if not init
        msg = '[spynl dev.translate] update the %s catalog' % lang
        command = ('python setup.py update_catalog -N --no-wrap -l {lang} '
                   '-i {lp}/locale/messages.pot -d {lp}/locale -D {pn}')
    # if not refresh, compile
    elif os.path.exists(po_file):
        command = ('python setup.py compile_catalog --domain {pn} '
                   '--directory {lp}/locale --domain {pn} --locale {lang}')
    else:
        msg = ('[spynl dev.translate] File %s does not exist.'
               ' Update the package first.' % po_file)

    if msg:
        print(msg)
    return command
