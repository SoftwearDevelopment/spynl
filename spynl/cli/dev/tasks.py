import os
from invoke import task
from invoke.exceptions import Exit
import pip

from spynl.main.version import __version__ as spynl_version
from spynl.main.utils import chdir
from spynl.main.pkg_utils import get_config_package, get_dev_config
from spynl.cli.utils import resolve_packages_param, package_dir


packages_help = "Affected packages, defaults to all installed."


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
    ctx.run('pip install --upgrade setuptools')  # make sure we have the latest
    src_path = src_path or os.environ['VIRTUAL_ENV'] + '/src'
    if scm_url is None:
        raise Exit("[spynl dev.install] Please give the --scm-url parameter.")
    scm_url = scm_url.strip('/')
    # set scm_type
    scm_type = (scm_url.endswith('.git') or '.git@' in scm_url) and "git" or "hg"
    if not os.path.exists(src_path):
        os.mkdir(src_path)
    repo_name = scm_url.split('/')[-1]
    if scm_type == 'git' and repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    repo_path = src_path + '/' + repo_name
    if not os.path.exists(repo_path):
        with chdir(src_path):
            print("[spynl dev.install] CLONING from %s" % scm_url)
            ctx.run('%s clone %s %s' % (scm_type, scm_url, repo_name))
    else:
        print("[spynl dev.install] UPDATING {}".format(repo_name))
        with chdir(repo_path):
            cmd = scm_type == 'git' and 'git pull' or 'hg pull --update'
            ctx.run(cmd)
    with chdir(repo_path):
        if revision is not None:
            cmd = scm_type == 'git' and 'git checkout' or 'hg update'
            print('[spynl dev.install] Using revision %s ...' % revision)
            # this might not work for mercurial anymore:
            try:
                ctx.run('{} {}'.format(cmd, revision), warn=True)
            except:
                def_branch = 'master' if scm_type == 'git' else 'default'
                print('[spynl dev.install] Updating to fallback revision %s ...'
                        % fallbackrevision if fallbackrevision else def_branch)
                ctx.run('{} {}'.format(cmd, fallbackrevision))
        if os.path.isfile('./setup.sh'):
            pre_cmd = './setup.sh --pre-install '\
                        '--virtualenv=%s' % os.environ['VIRTUAL_ENV']
            if install_deps:
                pre_cmd += ' --install-dependencies'
            ctx.run(pre_cmd)
        if developing:
            print("[spynl dev.install] DEVELOPING {}".format(repo_name))
            ctx.run('python setup.py develop')
        else:
            print("[spynl dev.install] INSTALLING {}".format(repo_name))
            ctx.run('python setup.py install')
        if os.path.isfile('./setup.sh'):
            ctx.run('./setup.sh --post-install')


@task
def serve(ctx):
    '''
    Run a local server. The ini-file development.ini is searched for in
    installed Spynl plugins. If there is none, minimal.ini is used.
    '''
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
      help={'packages': packages_help,
            'called-standalone': 'If False, this task is a pre-task and the '
                                 'user gets to cancel the task flow when '
                                 'tests fail.',
            'reports': 'If True, Junit and Coverage reports will be made '
                       '(requires a few extra packages, '
                       'e.g. for pycoverage).'})
def test(ctx, packages='_all', called_standalone=True, reports=False):
    '''
    Perfom tests in one or more spynl plugins.
    '''
    for package_name in resolve_packages_param(packages):
        print("[spynl dev.test] Testing package: {}".format(package_name))
        with package_dir(package_name):
            if not reports:
                result = ctx.run('py.test', warn=True)
            else:
                result = ctx.run('py.test --junit-xml=pytests.xml --cov %s '
                                 ' --cov-report xml --cov-append' % package_name)
            if not result.ok and called_standalone is False\
               and input("[spynl dev.test] Tests failed. Continue anyway? Y/n") not in ('y', 'Y'):
                raise Exit("[spynl dev.test] Aborting at user request.")


@task(help={'packages': packages_help,
            'languages': 'An iterable of language codes (e.g. ("nl",). '
                         'Defaults to the setting "spynl.languages".',
            'action': 'Either "compile" (compile selected languages) or '
                      '"refresh" (extract messages from the source code '
                      'and update the .po files for the selected languages). '
                      'Defaults to "compile".'})
def translate(ctx, packages='_all', languages=None, action='compile'):
    '''
    Ensure that translations files are up-to-date w.r.t. to the code. If action
    is set to compile (default), this will compile the catalogs for all selected
    languages. If action is set to refresh, this will extract messages from the
    source code and update the .po files for the selected languages (will
    initialize if necessary).
    '''
    if action == 'compile':
        refresh = False
    elif action == 'refresh':
        refresh = True
    else:
        raise Exit("[spynl dev.translate] action should be 'compile' or "
                   "'refresh'.")

    if languages is None:
        config = get_dev_config()
        languages = config.get('spynl.languages', None)
        if languages is None:
            raise Exit('[spynl dev.translate] No languages set '
                       'and also no spynl.languages setting found. '
                       'Cannot determine which catalogues to work on.')
    if isinstance(languages, str):
        languages = [lang for lang in languages.split(',') if lang != '']

    for package_name in resolve_packages_param(packages):
        with package_dir(package_name):
            if package_name == 'spynl':
                package_name = 'spynl.main'
            print("[spynl dev.translate] Package: %s ..." % package_name)
            locale_path = ''
            for path, dirs, files in os.walk(os.path.abspath(os.getcwd())):
                if 'locale' in dirs:
                    locale_path = path
                    break
            # make locale folder if it doesn't exist already:
            if locale_path == '':
                print("[spynl dev.translate] Creating locale folder ...")
                os.mkdir('locale')
                locale_path = '.'
            else:
                print("[spynl dev.translate] Located locale folder in %s ..."
                      % locale_path)
            if refresh:
                # Extract messages from source:
                ctx.run('python setup.py extract_messages '
                        '--output-file {lp}/locale/messages.pot --no-wrap '
                        '--sort-by-file --input-dirs {lp} --project {project} '
                        '--copyright-holder "Softwear BV" --version {v}'
                        .format(lp=locale_path, project=package_name,
                                v=spynl_version))

            for lang in languages:
                path2po = '%s/locale/%s/LC_MESSAGES/%s.po' % (locale_path, lang,
                                                              package_name)
                # update if refresh
                if refresh:
                    # init if needed:
                    if not os.path.exists(path2po):
                        print('[spynl dev.translate] File %s does not exist.'
                              ' Initializing.' % path2po)
                        ctx.run('python setup.py init_catalog -l {lang} '
                                '-i {lp}/locale/messages.pot '
                                '-d {lp}/locale -D {pn}'
                                .format(lp=locale_path, pn=package_name, lang=lang))
                    # update if not init
                    else:
                        print('[spynl dev.translate] update the %s catalog'
                              % lang)
                        ctx.run('python setup.py update_catalog -N --no-wrap '
                                '-l {lang} -i {lp}/locale/messages.pot '
                                '-d {lp}/locale -D {pn}'
                                .format(lp=locale_path, pn=package_name, lang=lang))
                # if not refresh, compile
                elif os.path.exists(path2po):
                    ctx.run('python setup.py compile_catalog --domain {pn} '
                            '--directory {lp}/locale --domain {pn} '
                            '--locale {lang}'
                            .format(lp=locale_path, pn=package_name, lang=lang))
                else:
                    print('[spynl dev.translate] File %s does not exist.'
                          ' Update the package first.' % path2po)

                print("[spynl dev.translate] Done with language %s." % lang)
                print("--------------------------------------------------")
