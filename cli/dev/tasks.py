import os
from invoke import task
from invoke.exceptions import Exit
import pip

from spynl.main.version import __version__ as spynl_version
from cli.utils import resolve_repo_names, repo, chdir, get_spynl_package


repos_help = "Affected repos, e.g. spynl,spynl.auth. "\
             "Defaults to all installed."


@task(help={'repos': repos_help,
            'developing': 'If True (default), python setup.py develop is '
                          'used, otherwise install',
            'revision': 'Which revision to update to (default: do not update)',
            'fallbackrevision': 'Use this revision if the repository does not '
                                ' have the target revision.',
            'url': 'Version control team URL, e.g. bitbucket.org/spynl '
                   '(default).',
            'install-deps': 'If True, pre-install dependencies '
                            '(eg. via apt-get) are installed.',
            'src_path': 'Desired installation path. Defaults to '
                        '$VIRTUAL_ENV/src directory.'})
def install(ctx, repos='_all', developing=True, revision=None,
            fallbackrevision='default', url='bitbucket.org/spynl',
            install_deps=True, src_path=None):
    '''Get code and install repos in the current virtual environment.'''
    ctx.run('pip install --upgrade setuptools')  # make sure we have the latest
    src_path = src_path or os.environ['VIRTUAL_ENV'] + '/src'
    if not os.path.exists(src_path):
        os.mkdir(src_path)
    for repo_name in resolve_repo_names(repos, complain_not_installed=False):
        repo_path = src_path + '/' + repo_name
        if not os.path.exists(repo_path):
            with chdir(src_path):
                clone_url = 'ssh://hg@%s/%s' % (url, repo_name)
                print("[spynl dev.install] CLONING from %s" % clone_url)
                ctx.run('hg clone %s' % clone_url)
        else:
            print("[spynl dev.install] UPDATING {}".format(repo_name))
            with chdir(repo_path):
                ctx.run('hg pull --update')
        with chdir(repo_path):
            if revision is not None:
                print('[spynl dev.install] Updating to revision %s ...' % revision)
                if not ctx.run('hg update {}'.format(revision), warn=True):
                    print('[spynl dev.install] Updating to fallback revision %s ...'
                          % fallbackrevision)
                    ctx.run('hg update {}'.format(fallbackrevision))
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
            translations(ctx, repos=repo_name, action='compile')
            if os.path.isfile('./setup.sh'):
                ctx.run('./setup.sh --post-install')


@task(help={"from-repo": "Name of the repository containing development.ini"})
def configure(ctx, from_repo):
    '''Configure which repo contains the development.ini file.
       Creates a symlink in $VIRTUAL_ENV.'''
    venv = os.environ['VIRTUAL_ENV']
    frepo = get_spynl_package(from_repo)
    if not os.path.exists("%s/development.ini" % (frepo.location)):
        raise Exit("[spynl dev.configure] No development.ini file found"
                   " in repo '%s'" % from_repo)
    if 'development.ini' in os.listdir(venv):
        os.remove("%s/development.ini" % venv)
    ctx.run("ln -s {rl}/development.ini {v}/development.ini"\
            .format(v=venv, rl=frepo.location))


@task
def serve(ctx):
    '''Run local dev server'''
    venv = os.environ['VIRTUAL_ENV']
    if not os.path.exists("%s/development.ini" % venv):
        raise Exit("[spynl dev.serve] No development.ini in %s. You might need"
                   " to use the <spynl dev.configure> task." % venv)
    with repo('spynl'):
        ctx.run('pserve %s/development.ini --reload' % venv, pty=True)


@task(aliases=('tests',),
      help={'repos': repos_help,
            'called-standalone': 'If False, this task is a pre-task and the '
                                 'user gets to cancel the task flow when '
                                 'tests fail.',
            'reports': 'If True, Junit and Coverage reports will be made '
                       '(requires a few extra packages, '
                       'e.g. for pycoverage).'})
def test(ctx, repos='_all', called_standalone=True, reports=False):
    '''
    Perfom tests in one or more spynl plugins.
    '''
    for repo_name in resolve_repo_names(repos):
        print("[spynl dev.test] Testing repo: {}".format(repo_name))
        with repo(repo_name):
            if not reports:
                result = ctx.run('py.test', warn=True)
            else:
                result = ctx.run('py.test --junit-xml=pytests.xml --cov %s '
                                 ' --cov-report xml --cov-append' % repo_name)
            if not result.ok and called_standalone is False\
               and input("[spynl dev.test] Tests failed. Continue anyway? Y/n") not in ('y', 'Y'):
                raise Exit("[spynl dev.test] Aborting at user request.")


@task(help={'version': 'The version (tag/revision) in the softwear.schemas repo.'})
def get_schemas(ctx, version=None):  # TODO: make independent of softwear.schemas
    '''get JSON schemas with git and put them where Spynl expects them.'''
    if version is None:
        raise Exit("[spynl dev.get_schemas] Please specify a version"
                   " (tag from softwear.schemas)")
    spynl = get_spynl_package('spynl')
    if spynl is None:
        raise Exit("Spynl main package is not installed.")

    with chdir(spynl.location):
        ctx.run('mkdir -p spynl/main/docs/docson/schemas')
        ctx.run('rm -rf spynl/main/docs/docson/schemas/*')

        ctx.run('git clone git@bitbucket.org:softwear/schemas.git'
                ' --branch %s schemas' % version)

        ctx.run('mv schemas/spynl/* spynl/main/docs/docson/schemas/')
        ctx.run('rm -rf schemas')


@task(help={'repos': repos_help,
            'languages': 'An iterable of language codes. Defaults to ("nl",).',
            'action': 'Either "compile" (compile selected languages) or '
                      '"refresh" (extract messages from the source code '
                      'and update the .po files for the selected languages). '
                      'Defaults to compile.'})
def translations(ctx, repos='_all', languages=('nl',), action='compile'):
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
        raise Exit("[spynl dev.translations] action should be 'compile' or "
                   "'refresh'.")

    for repo_name in resolve_repo_names(repos):
        with repo(repo_name):
            if repo_name == 'spynl':
                repo_name = 'spynl.main'
            print("[spynl dev.translations] Repo: %s ..." % repo_name)
            repo_path = repo_name.replace('.', '/')
            # make locale folder if it doesn't exist already:
            if not os.path.exists('%s/locale' % repo_path):
                os.mkdir('./%s/locale' % repo_path)
            if refresh:
                # Extract messages from source:
                ctx.run('python setup.py extract_messages '
                        '--output-file {rp}/locale/messages.pot --no-wrap '
                        '--sort-by-file --input-dirs {rp} --project {project} '
                        '--copyright-holder "Softwear BV" --version {v}'
                        .format(rp=repo_path, project=repo_name,
                                v=spynl_version))
            for lang in languages:
                path2po = '%s/locale/%s/LC_MESSAGES/%s.po' % (repo_path, lang,
                                                              repo_name)
                # update if refresh
                if refresh:
                    # init if needed:
                    if not os.path.exists(path2po):
                        print('[spynl dev.translations] File %s does not exist.'
                              ' Initializing.' % path2po)
                        ctx.run('python setup.py init_catalog -l {lang} '
                                '-i {rp}/locale/messages.pot '
                                '-d {rp}/locale -D {rn}'
                                .format(rp=repo_path, rn=repo_name, lang=lang))
                    # update if not init
                    else:
                        print('[spynl dev.translations] update the %s catalog'
                              % lang)
                        ctx.run('python setup.py update_catalog -N --no-wrap '
                                '-l {lang} -i {rp}/locale/messages.pot '
                                '-d {rp}/locale -D {rn}'
                                .format(rp=repo_path, rn=repo_name, lang=lang))
                # if not refresh, compile
                elif os.path.exists(path2po):
                    ctx.run('python setup.py compile_catalog --domain {rn} '
                            '--directory {rp}/locale --domain {rn} '
                            '--locale {lang}'
                            .format(rp=repo_path, rn=repo_name, lang=lang))
                else:
                    print('[spynl dev.translations] File %s does not exist.'
                          ' Update the repo first.' % path2po)

                print("[spynl dev.translations] Done with language %s." % lang)
                print("--------------------------------------------------")
