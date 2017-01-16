"""
Mercurial-specific tasks to use across repos.
"""
import os

from invoke import task
from invoke.exceptions import Exit
import pip

from cli.utils import resolve_repo_names, repo, get_spynl_package
from cli import dev


@task(help={'repos': dev.tasks.repos_help})
def pullup(ctx, repos='_all'):
    '''Pull from repo(s) and update, whatever branch they're on.'''
    for repo_name in resolve_repo_names(repos):
        print("[SPYNL] Pulling repo: {}".format(repo_name))
        with repo(repo_name):
            ctx.run('hg pull --update')


@task(help={'repos': dev.tasks.repos_help,
            'show-all': 'If True, show all inactive branches as well. '
                        'Defaults to False.'})
def branches(ctx, repos='_all', show_all=False):
    '''Show the active branch in repos.'''
    for repo_name in resolve_repo_names(repos):
        with repo(repo_name):
            print('[SPYNL] Branches for {}:'.format(repo_name))
            if show_all:
                ctx.run('hg branches -q')
            else:
                ctx.run('hg branch -q')


@task(help={'repos': dev.tasks.repos_help,
            'revision ': 'The revision (e.g. branch or commit ID) '
                         'to update to'})
def update(ctx, repos='_all', revision='default'):
    '''Update all repos to a specific revision.'''
    for repo_name in resolve_repo_names(repos):
        print('[SPYNL] Updating repo {}:'.format(repo_name))
        with repo(repo_name):
            ctx.run('hg update {}'.format(revision), warn=True)


@task(help={'repos': dev.tasks.repos_help})
def status(ctx, repos='_all'):
    '''Show status in repos.'''
    for repo_name in resolve_repo_names(repos):
        print('[SPYNL] Status for {}:'.format(repo_name))
        with repo(repo_name):
            ctx.run('hg status')


@task(help={'repos': dev.tasks.repos_help})
def outgoing(ctx, repos='_all'):
    '''Show if there are outgoing (to be pushed) commits.'''
    for repo_name in resolve_repo_names(repos):
        with repo(repo_name):
            print('')
            print('[SPYNL] Outgoing commits for {}:'.format(repo_name))
            ctx.run('hg outgoing', warn=True)


@task(help={'repos': dev.tasks.repos_help})
def diff(ctx, repos='_all'):
    '''Show diff in repos.'''
    for repo_name in resolve_repo_names(repos):
        with repo(repo_name):
            ctx.run('hg diff')


@task(help={'repos': dev.tasks.repos_help,
            'tagname': 'Name of the tag. Required.',
            'force': 'Add the -f option to the mercurial tag command. '
                     'Defaults to True.'})
def tag(ctx, repos='_all', tagname=None, force=True):
    '''Tag current state in repos.'''
    if tagname is None:
        raise Exit("Error: No tagname argument given.")
    for repo_name in resolve_repo_names(repos):
        with repo(repo_name):
            if force:
                ctx.run('hg tag %s -f' % tagname)
            else:
                ctx.run('hg tag %s' % tagname)


@task(help={'repos': dev.tasks.repos_help,
            'msg': 'Commit Message'})
def commit(ctx, repos='_all', msg=''):
    '''Commit changed code.'''
    for repo_name in resolve_repo_names(repos):
        print("[SPYNL] Commiting repo: {}".format(repo_name))
        # mercurial returns non-zero error code when no changes
        with repo(repo_name):
            if msg != "":
                ctx.run("hg commit -m '{}'".format(msg), warn=True)
            else:
                ctx.run("hg commit", warn=True)


@task(optional=['skip-testing'],
      help={'repos': dev.tasks.repos_help,
            'skip-testing': 'Tests are skipped when this param is given.'})
def push(ctx, repos='_all', skip_testing=False):
    '''Push commited code to server, run tests first.'''
    if not skip_testing:
        for repo_name in resolve_repo_names(repos):
            dev.tasks.test(ctx, repos=repo_name, called_standalone=False)
    for repo_name in resolve_repo_names(repos):
        print("[SPYNL] Pushing repo: {}".format(repo_name))
        with repo(repo_name):
            # mercurial returns non-zero error code when no changes
            ctx.run("hg push", warn=True)


@task(help={'repos': dev.tasks.repos_help,
            'sourcebranch': 'Branch to merge from. Required.',
            'targetbranch': 'Branch to merge into. Defaults to "default"'})
def merge(ctx, repos='_all', sourcebranch=None, targetbranch='default'):
    '''Merge a source branch into the target branch.'''
    if sourcebranch is None:
        print("[SPYNL] No target branch given.")
        return
    spynl = get_spynl_package('spynl')
    for repo_name in resolve_repo_names(repos):
        print("[SPYNL] Merging branch {} of repo: {} into branch {}"
              .format(sourcebranch, repo_name, targetbranch))
        with repo(repo_name):
            ctx.run('{}/cli/dev/merge_branch.sh {} {}'
                    .format(spynl.location, sourcebranch, targetbranch))


@task(help={'repos': dev.tasks.repos_help,
            'name': 'The new branch name.'})
def new_branch(ctx, repos='_all', name=None):
    ''' Create a new branch.'''
    if not name:
        print("[SPYNL] No branch name given.")
        return
    spynl = get_spynl_package('spynl')
    for repo_name in resolve_repo_names(repos):
        print("[SPYNL] Making new branch named {} of repo: {}"
              .format(name, repo_name))
        with repo(repo_name):
            ctx.run('%s/cli/dev/new_branch.sh %s' % (spynl.location, name))
