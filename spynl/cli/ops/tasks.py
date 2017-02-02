"""Tasks for operations around building and deploying Spynl"""

import os
import json
from datetime import datetime, timedelta
import pytz
from urllib.parse import urlparse

import requests
from invoke import task
from invoke.exceptions import Exit

from spynl.main.utils import chdir
from spynl.main.pkg_utils import (get_spynl_package, get_dev_config,
                                  get_config_package, lookup_scm_url,
                                  lookup_scm_commit)
from spynl.cli.utils import (resolve_packages_param, get_spynl_package,
                             package_dir, assert_response_code) 
from spynl.cli.dev import tasks as dev_tasks


@task(help={'packages': dev_tasks.packages_help,
            'revision': 'The code revision (e.g. branch name or tag, '
                        'applicable across repositories). '
                        'Defaults to "master" on git and "default" on '
                        'mercurial.',
            'fallbackrevision': 'Revision to fall back on if revision '
                                'is not given. Defaults to "master" on git '
                                'and "default" on mercurial.',
            'spynlbranch': 'You can specify a branch for the main Spynl '
                           'package. Defaults to "master".',
            'task': 'The AWS ECS task identifier to be restarted '
                    '(see the spynl.ops.ecr.dev_tasks setting). '
                    'Can be more than task (provide a comma-separated '
                    'list in that case). Alternatively, use "production" '
                    'to deploy to the production ECR.'})
def start_build(ctx, packages='_all', revision='', fallbackrevision='',
                spynlbranch='master', task=''):
    """Make a new Spynl build: call the SPYNL job on Jenkins."""
    config = get_dev_config()
    jenkins_url = config.get('spynl.ops.jenkins_url', '').strip()
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
    installed_packages_urls = resolve_packages_param(packages, to='scm-urls')
    params = dict(scm_urls=','.join(installed_packages_urls),
                  revision=revision, fallbackrevision=fallbackrevision,
                  spynlbranch=spynlbranch, task=task)
    print('[spynl ops.start_build] Calling up Jenkins server at '
          '%s with params %s.' % (url, str(params)))
    response = requests.post(url, params)
    print('[spynl ops.start_build] Got response: %s' % response)


@task(help={'packages': dev_tasks.packages_help})
def mk_repo_state(ctx, packages='_all'):
    """
    Go through all packages (spynl&spynl-plugins) and collect the commit IDs
    they are at. Store their scm URLs and the commit IDs in a file called
    "repo-state.txt".
    This allows us to store this meta information in a human-readable form
    as a build artefact and also to restore this state inside of a Docker
    image.
    """
    with open('repo-state.txt', 'w') as repo_state:
        spynl_scm_url = lookup_scm_url(os.getcwd())
        commit_id = lookup_scm_commit(os.getcwd())
        print("[spynl ops.mk_repo_state] Package spynl has commit ID: %s"
              % commit_id)
        repo_state.write("%s %s\n" % (spynl_scm_url, commit_id))
        for name in resolve_packages_param(packages):
            with package_dir(name):
                scm_url = lookup_scm_url(os.getcwd())
                commit_id = lookup_scm_commit(os.getcwd())
                print("[spynl ops.mk_repo_state] Package %s has commit ID: %s"
                      % (name, commit_id))
                repo_state.write("%s %s\n" % (scm_url, commit_id))


@task(help={'buildnr': 'Number of the SPYNL-Deploy build of Jenkins.',
            'task': 'Can be either "production" or one of the dev '
                    'tasks given by the spynl.ops.ecr.dev_tasks setting. '
                    'With the former, the image will be pushed to the '
                    'production AWS ECR. The build number will be attached '
                    'to the tag. With the latter, the image will be pushed '
                    'to the development AWS ECR. It will be tagged with the '
                    'task name and the task in the AWS ECS will be restarted, '
                    'so the new image will be live.'})
def deploy(ctx, buildnr=None, task=None):
    """Build a Spynl Docker image and deploy it."""
    # --- make sure we have repostate.txt
    if not os.path.exists('repo-state.txt'):
        mk_repo_state(ctx)
    # --- put repo-state.txt into the docker build directory
    ctx.run('mv repo-state.txt spynl/cli/ops/docker')
    # --- put production.ini into the docker build directory
    config_package = get_config_package()
    ctx.run('cp %s/production.ini spynl/cli/ops/docker'
            % config_package.location)

    # check ECR configuration
    config = get_dev_config()
    dev_ecr_profile, dev_ecr_uri =\
        config.get('spynl.ops.ecr.dev_url', '').split('@')
    if task != 'production' and not dev_ecr_uri:
        raise Exit('[spynl ops.deploy] ECR for development is not configured. '
                   'Exiting ...')
    prod_ecr_profile, prod_ecr_uri =\
        config.get('spynl.ops.ecr.prod_url', '').split('@')
    if task == 'production' and not prod_ecr_uri:
        raise Exit('[spynl ops.deploy] ECR for production is not configured. '
                   'Exiting ...')
    dev_domain = config.get('spynl.ops.dev_domain', '')

    # --- build Docker image
    with chdir('spynl/cli/ops/docker'):
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
            ecr_dev_tasks = [t.strip() for t in config
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


@task(help={'packages': dev_tasks.packages_help})
def prepare_docker_run(ctx, packages='_all'):
    """
    Give repos a chance to make configuration changes just when the
    Docker container starts up, e.g. update /production.ini based
    on environment variables like SPYNL_ENVIRONMENT.
    This allows test/production environments to be configured in their
    preferred way.
    If the packages provide a script called "prepare-docker-run.sh",
    this task will run it.
    """
    print("[spynl ops.prepare_docker_run] Will check packages %s ..." % packages)
    for package_name in resolve_packages_param(packages):
        package = get_spynl_package(package_name)
        print("[spynl ops.prepare_docker_run] Checking package %s at %s ..."
              % (package_name, package.location))
        with package_dir(package_name):
            if os.path.exists('%s/prepare-docker-run.sh' % package.location):
                print("[spynl ops.prepare_docker_run] Preparing repo: %s ..."
                      % package_name)
                ctx.run('%s/prepare-docker-run.sh' % package.location)


@task(help={'packages': dev_tasks.packages_help,
            'task': 'Spynl task, used to find out at which URL to test Spynl. '
                    ' One of the tasks specified by the ini-setting '
                    ' "spynl.ops.dev_url". For tasks other than "dev", the '
                    ' term "spynl" in the dev_url will be replaced by '
                    ' "spynl-<task>". If no task parameter is given, '
                    ' then the <url> parameter should be given.',
            'url': 'URL to run smoke test against. Will overwrite whatever '
                   'URL the task parameter indicates.'})
def smoke_test(ctx, packages="_all", url=None, task='dev'):
    """Run smoke tests"""
    config = get_dev_config()
    ecr_dev_tasks = [t.strip() for t in config
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
        spynl_url = config.get('spynl.ops.dev_url', '').strip()
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

    for package_name in resolve_packages_param(packages):
        with package_dir(package_name):
            package = get_spynl_package(package_name) 
            if os.path.exists('%s/smoke-test.py' % package.location):
                print("[spynl ops.smoke_test] Running %s/smoke-test.py ..."
                      % package.location)
                ctx.run('python %s/smoke-test.py --spynl-url %s'
                        % (package.location, spynl_url))

    print('[spynl ops.smoke_test] Spynl presence checked successfully!')
