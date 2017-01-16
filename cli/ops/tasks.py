"""Tasks for operations around building and deploying Spynl"""

import os
import json
import configparser
from datetime import datetime, timedelta
import pytz
from urllib.parse import urlparse

import requests
from invoke import task
from invoke.exceptions import Exit

from cli.utils import (resolve_repo_names, repo, chdir, get_spynl_package,
                       assert_response_code) 
from cli.dev import tasks as dev_tasks


@task(help={'repos': dev_tasks.repos_help,
            'config-repo': 'The repo containing production.ini and '
                           'maybe smoke_test.py',
            'revision': 'The code revision (e.g. branch name or tag, '
                        'applicable across repositories). '
                        'Defaults to "default".',
            'fallbackrevision': 'Revision to fall back on if revision '
                                'is not given. Defaults to "default".',
            'spynlrevision': 'You can specify a revision for the spynl '
                             'repo that is used by Jenkins as basis for '
                             'the build. Defaults to "default".',
            'task': 'The AWS ECS task identifier to be restarted '
                    '(see the spynl.ops.ecr.dev_tasks setting). '
                    'Can be more than task (provide a comma-separated '
                    'list in that case). Alternatively, use "production" '
                    'to deploy to the production ECR.'})
def start_build(ctx, repos='_all', config_repo=None, revision='default',
                fallbackrevision='default', spynlrevision='default',
                task=''):
    """Make a new Spynl build: call the SPYNL job on Jenkins."""
    config = configparser.ConfigParser()
    config.read('%s/development.ini' % os.environ['VIRTUAL_ENV'])
    jenkins_url = config['app:main'].get('spynl.ops.jenkins_url', '').strip()
    if not jenkins_url:
        raise Exit('[spynl ops.start_build] No spynl.ops.jenkins_url '
                   'setting found! Exiting ...')
    if os.environ.get('JENKINS_USER') is None:
        jenkins_user = os.environ.get('USER')
        print('[spynl ops.start_build] Assuming jenkins user %s ...'
              'Set env variable JENKINS_USER to change this.' % jenkins_user)
    else:
        jenkins_user = os.environ.get('JENKINS_USER')
    if os.environ.get('JENKINS_PASSWORD') is None:
        raise Exit('[spynl ops.start_build] No jenkins password given -'
                   ' please set env variable JENKINS_PASSWORD. Exiting...')

    jurl_parts = urlparse(jenkins_url)
    url = "{jscheme}://{juser}:{jpw}@{jloc}/job/Spynl"\
          "/buildWithParameters?delay=0sec"\
          .format(jscheme=jurl_parts.scheme, juser=jenkins_user,
                  jpw=os.environ['JENKINS_PASSWORD'], jloc=jurl_parts.netloc)
    installed_repos = resolve_repo_names(repos, complain_not_installed=False)
    if config_repo is None:
        raise Exit('[spynl ops.start_build] Please set the --config-repo param '
                   '(the config repo contains development.ini and '
                   'production.ini).')
    if config_repo not in installed_repos:
        raise Exit('[spynl ops.start_build] Config repo %s is not installed.'
                   % config_repo)
    params = dict(repos=','.join(installed_repos), configrepo=config_repo,
                  revision=revision, fallbackrevision=fallbackrevision,
                  spynlrevision=spynlrevision, task=task)
    print('[spynl ops.start_build] Calling up Jenkins server at %s with params %s.' % (url, str(params)))
    response = requests.post(url, params)
    print('[spynl ops.start_build] Got response: %s' % response)


@task(help={'repos': dev_tasks.repos_help,
            'revision': 'The code revision (e.g. branch name or tag, '
                        'applicable across repositories). '
                        'Defaults to "default".',
            'fallbackrevision': 'Which revision to fallback on if the '
                                'repo does not have revision. '
                                'Defaults to "default".',
            'revertchanges': 'Revert uncommited changes in order to update.'
                             'Otherwise this task will raise if a repo has '
                             'local changes.'})
def tag_repo_states(ctx, repos='_all', revision='default',
                    fallbackrevision='default',
                    revertchanges=False):
    """
    Go through all repos and collect the commit IDs they are at
    in the current revision (e.g. a branch or tag).
    Store that information in a file.
    """
    if revision is None or revision == "":
        raise Exit("[spynl ops.tag_repo_states] revision argument is empty!")

    with open('repostate.txt', 'w') as repostate:
        # --- install/check for changes
        for name in resolve_repo_names(repos, complain_not_installed=False):
            package = get_spynl_package(name)
            if package is None or not os.path.exists(package.location):
                dev_tasks.install(ctx, repos=name, revision=revision,
                                  fallbackrevision=fallbackrevision)
            with repo(name):
                if revertchanges:
                    ctx.run('hg revert --all')
                elif ctx.run('hg st -amdr').stdout != "":
                    raise Exit("[spynl ops.tag_repo_states] Repo %s has "
                               "uncomitted changes." % name)
        # --- update to revision or fallbackrevision
        for name in resolve_repo_names(repos):
            with repo(name):
                ctx.run('hg pull -q')
                ctx.run("if echo \"$(hg branches) $(hg tags)\" | grep -i '^{rev}[[:space:]]' > /dev/null; then hg update -q {rev}; else hg update -q {fb_rev}; fi".format(rev=revision, fb_rev=fallbackrevision))
                commit_id = ctx.run('hg id -i', hide='both').stdout.strip()
                print("[spynl ops.tag_repo_states] "
                      "Repo %s (at branch %s) has commit ID: %s" %
                      (name, ctx.run('hg branch', hide='both').stdout.strip(),
                       commit_id))
                repostate.write("%s %s\n" % (name, commit_id))


@task(help={'buildnr': 'Number of the SPYNL-Deploy build of Jenkins.',
            'config-repo': 'The repo containing production.ini',
            'task': 'Can be either "production" or one of the dev '
                    'tasks given by the spynl.ops.ecr.dev_tasks setting. '
                    'With the former, the image will be pushed to the '
                    'production AWS ECR. The build number will be attached '
                    'to the tag. With the latter, the image will be pushed '
                    'to the development AWS ECR. It will be tagged with the '
                    'task name and the task in the AWS ECS will be restarted, '
                    'so the new image will be live.',
            'revision': 'The code revision (e.g. branch name or tag, '
                        'applicable across repositories). Optional - '
                        'should be left out if a repostate.txt file has '
                        'already been made.',
            'fallbackrevision': 'A fallback revision can also be given for the '
                                'case that a repo does not have revision.'})
def deploy(ctx, buildnr=None, config_repo=None, task=None, revision=None,
           fallbackrevision='default'):
    """Build a Spynl Docker image and deploy it."""
    # --- make sure we have repostate.txt
    if not os.path.exists('repostate.txt'):
        if revision is None:
            raise Exit("[spynl ops.deploy] No repostate.txt found and no "
                       "revision given.")
        tag_repo_states(ctx, revision=revision,
                        fallbackrevision=fallbackrevision)
    # --- put repostates.txt into the docker build directory
    spynl = get_spynl_package('spynl')
    ctx.run('mv repostate.txt %s/cli/ops/docker' % spynl.location)
    # --- put production.ini into the docker build directory
    config_package = get_spynl_package(config_repo)
    ctx.run('cp %s/production.ini %s/cli/ops/docker'
            % (config_package.location, spynl.location))

    # check ECR configuration
    config = configparser.ConfigParser()
    config.read('%s/development.ini'  % config_package.location)
    dev_ecr_profile, dev_ecr_uri =\
        config['app:main'].get('spynl.ops.ecr.dev_url', '').split('@')
    if task != 'production' and not dev_ecr_uri:
        raise Exit('[spynl ops.deploy] ECR for development is not configured. '
                   'Exiting ...')
    prod_ecr_profile, prod_ecr_uri =\
        config['app:main'].get('spynl.ops.ecr.prod_url', '').split('@')
    if task == 'production' and not prod_ecr_uri:
        raise Exit('[spynl ops.deploy] ECR for production is not configured. '
                   'Exiting ...')
    dev_domain = config['app:main'].get('spynl.ops.dev_domain', '')

    # --- build Docker image
    with chdir(spynl.location + '/cli/ops/docker'):
        result = ctx.run('./build-image.sh %s %s' % (buildnr, dev_domain))
        if not result:
            raise Exit("[spynl ops.deploy] Building docker image failed: %s"
                       % result.stderr)
        # report the Spynl version from the code we just built
        spynl_version = ctx.run('cat built.spynl.version').stdout.strip()
        ctx.run('rm -f built.spynl.version')  # clean up
        print('[spynl ops.deploy] Built Spynl version {}'.format(spynl_version))

    if task == 'production':
        get_login_cmd = ctx.run('aws ecr --profile %s get-login '
                                '--region eu-west-1' % prod_ecr_profile)
        ctx.run(get_login_cmd.stdout.strip())
        # tag & push image with spynl_version & buildnr as tag
        ctx.run('docker tag spynl:v{v} {aws_uri}/spynl:v{v}_b{bnr}'
                .format(v=spynl_version, aws_uri=prod_ecr_uri, bnr=buildnr))
        ctx.run('docker push {aws_uri}/spynl:v{v}_b{bnr}'
                .format(v=spynl_version, aws_uri=prod_ecr_uri, bnr=buildnr))
    else:
        get_login_cmd = ctx.run('aws ecr --profile %s get-login '
                                '--region eu-west-1' % dev_ecr_profile)
        ctx.run(get_login_cmd.stdout.strip())

        ctx.run('docker tag spynl:v{v} {aws_uri}/spynl:v{v}'
                .format(v=spynl_version, aws_uri=dev_ecr_uri))
        ctx.run('docker push {aws_uri}/spynl:v{v}'
                .format(v=spynl_version, aws_uri=dev_ecr_uri))

        # tag the image for being used in one of our defined Tasks
        if task:
            ecr_dev_tasks = [t.strip() for t in config['app:main']
                             .get('spynl.ops.ecr.dev_tasks', '')
                             .split(',')]
            for t in task.split(","):
                t = t.strip()
                if t not in ecr_dev_tasks:
                    raise Exit("Task: %s not found in %s. Aborting ..."
                               % (t, ecr_dev_tasks))
                print("[spynl ops.deploy] Deploying the new image for task "
                      "%s ..." % t)
                ctx.run('docker tag spynl:v{v} {aws_uri}/spynl:{task}'
                        .format(v=spynl_version, aws_uri=dev_ecr_uri, task=t))
                ctx.run('docker push {aws_uri}/spynl:{task}'
                        .format(aws_uri=dev_ecr_uri, task=t))

                # stop the task (so ECS restarts it and grabs new image)
                tasks = ctx.run('aws ecs list-tasks --cluster spynl '
                                '--service-name spynl-%s' % t)
                for task_id in json.loads(tasks.stdout)['taskArns']:
                    ctx.run('aws ecs stop-task --cluster spynl --task %s'
                            % task_id)
    ctx.run('docker logout')


@task(help={'repos': dev_tasks.repos_help})
def prepare_docker_run(ctx, repos='_all'):
    """
    Give repos a chance to make configuration changes just when the
    Docker container starts up, e.g. update /production.ini based
    on environment variables like SPYNL_ENVRIONMENT.
    This allows test/production environments to be configured in their
    preferred way.
    If the repos provide a script called "prepare-docker-run.sh",
    this task will run it.
    """
    print("[spynl ops.prepare_docker_run] Will check repos %s ..." % repos)
    for repo_name in resolve_repo_names(repos):
        package = get_spynl_package(repo_name)
        print("[spynl ops.prepare_docker_run] Checking repo %s at %s ..." % (repo_name, package.location))
        with repo(repo_name):
            if os.path.exists('%s/prepare-docker-run.sh' % package.location):
                print("[spynl ops.prepare_docker_run] Preparing repo: %s ..."
                      % repo_name)
                ctx.run('%s/prepare-docker-run.sh' % package.location)


@task(help={'repos': dev_tasks.repos_help,
            'config-repo': 'The repo containing development.ini',
            'task': 'Spynl task, used to find out at which URL to test Spynl. '
                    ' One of the tasks specified by the ini-setting '
                    ' "spynl.ops.dev_url". For tasks other than "dev", the '
                    ' term "spynl" in the dev_url will be replaced by '
                    ' "spynl-<task>". If no task parameter is given, '
                    ' then the <url> parameter should be given.',
            'url': 'URL to run smoke test against. Will overwrite whatever '
                   'URL the task parameter indicates.'})
def smoke_test(ctx, repos="_all", config_repo=None, url=None, task='dev'):
    """Run smoke tests"""
    config_package = get_spynl_package(config_repo)
    config = configparser.ConfigParser()
    config.read('%s/development.ini'  % config_package.location)
    ecr_dev_tasks = [t.strip() for t in config['app:main']
                     .get('spynl.ops.ecr.dev_tasks', '')
                     .split(',')]
    if url is not None:
        spynl_url = url.strip()
    elif task is None:
        raise Exit('Please specify a url or a task from [%s].'
                   % ecr_dev_tasks)
    else:
        if ',' in task:  # let's only do the first one
            task = task.split(',')[0].strip()
        if task not in ecr_dev_tasks:
            raise Exit('Task %s is not named in spynl.ops.ecr.dev.tasks.')
        spynl_url = config['app:main'].get('spynl.ops.dev_url', '').strip()
        if not spynl_url:
            raise Exit('spynl.ops.dev_url not set.')
        if task != 'dev':
            spynl_url = spynl_url.replace('spynl', 'spynl-%s' % task)
    print("[spynl ops.smoke_test] Accessing Spynl at: [{}]".format(spynl_url))

    # Check that Spynl answers at all
    print("[spynl_dev check] pinging ...")
    res = requests.get(spynl_url + '/ping')
    assert_response_code(res, 200)
    assert res.json()['greeting'] == 'pong'

    # Check that it serves the latest build
    print("[spynl ops.smoke_test] check if build is new ...")
    res = requests.get(spynl_url + '/about/build')
    assert_response_code(res, 200)
    build_time = datetime.strptime(res.json()['build_time'],
                                   '%Y-%m-%dT%H:%M:%S%z')
    now = datetime.now(tz=pytz.UTC)
    if not now - timedelta(minutes=15) < build_time:
        raise Exit("[spynl ops.smoke_test] Build seems to be old: "
                   "%s (now - 15m) is not before %s"
                   % (now - timedelta(minutes=15), build_time))

    for repo_name in resolve_repo_names(repos):
        package = get_spynl_package(repo_name)
        with repo(repo_name):
            if os.path.exists('%s/smoke-test.py' % package.location):
                print("[spynl ops.smoke_test] Running %s/smoke-test.py ..."
                      % package.location)
                ctx.run('python %s/smoke-test.py --spynl-url %s'
                        % (package.location, spynl_url))

    print('[spynl ops.smoke_test] Spynl presence checked successfully!')
