import urllib
import os
import subprocess
import pprint

from pkg_resources import iter_entry_points  # pylint: disable=E0611

import requests
import click

from spynl.main.version import __version__ as spynl_version
from spynl.cli.utils import resolve_packages, check_ini, run_command, exit
from spynl.main.dateutils import now
from spynl.main.pkg_utils import lookup_scm_url, SPYNL_DISTRIBUTION


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
@package_option
@click.option('--reports', is_flag=True)
@click.option('--non-interactive', is_flag=True)
def test(packages, reports, non_interactive):
    """Run tests."""
    cmd = 'py.test'

    for i, pkg in enumerate(packages):
        if reports:
            cmd += ('--junit-xml=pytests.xml --cov %s  --cov-report xml '
                    '--cov-append' % pkg.location)

        os.chdir(pkg.location)
        try:
            run_command(cmd, check=True)
        except subprocess.CalledProcessError:
            if non_interactive:
                exit("Tests for {} failed".format(pkg.project_name))

            msg = ('Tests for {} failed. Do you wish to continue?'.format(
                pkg.project_name))

            if (i + 1) == len(packages):
                click.echo(msg, err=True)
            elif not click.confirm(msg):
                exit("Aborting at user request.")


@dev.command()
@ini_option
def serve(ini):
    """Run a local server."""
    run_command('pserve {} --reload'.format(ini))


# TODO pick up languages from ini
@dev.command()
@package_option
@click.option('-l', '--languages',
              multiple=True,
              default=['nl'],
              help='One or more language codes such as "nl". '
                   ' defaults to the setting spynl.languages.')
@click.option('--action', '-a',
              type=click.Choice(['compile', 'refresh']),
              default='compile',
              help='Compile translations or refresh the translations calalogs.')
def translate(packages, languages, action):
    """Perform translation tasks."""

    for package in packages:
        domain = package.key

        os.chdir(package.location)

        for path, dirs, _ in os.walk(package.location):
            if 'locale' in dirs:
                locale_path = path
                output_dir = os.path.join(locale_path, 'locale')
                output_file = os.path.join(output_dir, 'messages.pot')

                break
        else:
            click.echo('Could not find locale folder for {}'
                       .package.project_name)

        if action == 'refresh':
            run_command(
                'pybabel extract '
                '--no-wrap '
                '--sort-by-file '
                '--output-file {output_file} '
                '--project {domain} '
                '--copyright-holder "Softwear BV" '
                '--version {version} '
                '--no-location '
                '{path}'
                .format(
                    output_file=output_file,
                    domain=domain,
                    version=spynl_version
                )
            )

        for lang in languages:
            if action == 'refresh':
                common = (
                    '--no-wrap '
                    '--input-file {output_file} '
                    '--output-dir {output_dir} '
                    '--domain {domain} '
                    '-l {lang}'
                    .format(
                        output_dir=output_dir,
                        output_file=output_file,
                        domain=domain,
                        lang=lang,
                    )
                )
                try:
                    run_command(
                        'pybabel update --no-fuzzy-matching ' + common,
                        check=True
                    )
                except subprocess.CalledProcessError:
                    run_command('pybabel init ' + common)

            elif action == 'compile':
                run_command(
                    'pybabel compile '
                    '--directory {output_dir} '
                    '--domain {domain} '
                    '-l {lang}'
                    .format(
                        output_dir=output_dir,
                        domain=domain,
                        lang=lang,
                    )
                )

            else:
                exit('error')


@cli.group()
def ops():
    """entry point for ops commands."""


DEFAULT_PASSWORD_PROMPT = '*****'


def retrieve_password_from_environment(ctx, param, value):
    if value == DEFAULT_PASSWORD_PROMPT:
        value = os.environ.get('JENKINS_PASSWORD', '')
    return value


@ops.command()
@package_option
@task_option
@click.option('-b', '--branch',
              help='The branch for the spynl.main',
              default='master')
@click.option('--user', '-u',
              prompt=True,
              default=lambda: os.environ.get('JENKINS_USER'))
@click.option('--password', '-p',
              prompt=True,
              hide_input=True,
              default=DEFAULT_PASSWORD_PROMPT,
              callback=retrieve_password_from_environment)
@click.option('--url', '-h',
              prompt=True,
              default=lambda: os.environ.get('JENKINS_URL'),
              callback=lambda c, p, v: urllib.parse.urlparse(v))
@click.option('--revision', '-r',
              default='master',
              help='Which branch or tag to checkout for the plugins.')
@click.option('--fallback-revision', '-f',
              default='master',
              help=('Which branch or tag to checkout for the plugins '
                    'if the specified revision does not exists.'))
def jenkins(packages, branch, task, user, password, url, revision, fallback_revision):
    """Trigger a spynl build on Jenkins."""

    # we do not care about the main spynl package here
    packages.remove(SPYNL_DISTRIBUTION)

    url = ('{scheme}://{user}:{pw}@{loc}/job/Spynl/buildWithParameters?delay=0sec'
           .format(
               scheme=url.scheme,
               user=user,
               pw=password,
               loc=url.netloc,
           ))

    params = dict(
        scm_urls=','.join([lookup_scm_url(p.location) for p in packages]),
        spynlbranch=branch,
        task=task,
        revision=revision,
        fallbackrevision=fallback_revision,
    )

    click.echo(
        'Starting a build at with the following packages: {plugins!s}.\n'
        'Calling Jenkins at {url} with the following parameters:\n{params}'
        .format(
            url=url,
            plugins=[p.project_name for p in packages],
            params=pprint.pformat(params)
        )
    )

    if click.confirm('Do you wish to proceed?'):
        response = requests.post(url, params)
        click.echo('Jenkins responded with: {0!s}'.format(response))


@ops.command()
@click.option('--build-nr', '-b', required=True)
@click.option('--revision', '-r', default='master')
def build(build_nr, revision):
    """Build a Spynl Docker image and deploy it."""

    run_command(
        'docker build -t spynl '
        '--build-arg BUILD_NR={build_nr} '
        '--build-arg BUILD_TIME=\"{build_time}\" '
        '--build-arg VERSION={version} '
        '{path}'
        .format(
            build_nr=build_nr,
            build_time=now(),
            version=revision,
            path=os.path.join(os.path.dirname(__file__), 'docker')
        )
    )

    # with chdir(os.path.join(SPYNL_DISTRIBUTION.location, 'docker')):
    #     command = ("docker build -t {project}:{version} "
    #                "--build-arg BUILD_TIME=\"{datetime!s}\" "
    #                "--build-arg BUILD_NR={build_nr} "
    #                "--build-arg DOMAIN={domain} ."
    #                .format(
    #                    project=SPYNL_DISTRIBUTION.project_name,
    #                    version=spynl_version,
    #                    datetime=now(),
    #                    build_nr=build_nr,
    #                    domain='localhost'
    #                ))
    #     run_command(command, check=True)

#     ctx.run('mv repo-state.txt spynl/cli/ops/docker')
#     # --- put production.ini into the docker build directory
#     config_package = get_config_package()
#     ctx.run('cp %s/production.ini spynl/cli/ops/docker'
#             % config_package.location)

#     # check ECR configuration
#     config = get_dev_config()
#     dev_ecr_profile, dev_ecr_uri =\
#         config.get('spynl.ops.ecr.dev_url', '').split('@')
#     if task != 'production' and not dev_ecr_uri:
#         raise Exit('[spynl ops.deploy] ECR for development is not configured. '
#                    'Exiting ...')
#     prod_ecr_profile, prod_ecr_uri =\
#         config.get('spynl.ops.ecr.prod_url', '').split('@')
#     if task == 'production' and not prod_ecr_uri:
#         raise Exit('[spynl ops.deploy] ECR for production is not configured. '
#                    'Exiting ...')
#     dev_domain = config.get('spynl.ops.dev_domain', '')

#     # --- build Docker image
#     with chdir('spynl/cli/ops/docker'):
#         result = ctx.run('./build-image.sh %s %s' % (buildnr, dev_domain))
#         if not result:
#             raise Exit("[spynl ops.deploy] Building docker image failed: %s"
#                        % result.stderr)
#         # report the Spynl version from the code we just built
#         spynl_version = ctx.run('cat built.spynl.version').stdout.strip()
#         ctx.run('rm -f built.spynl.version')  # clean up
#         print('[spynl ops.deploy] Built Spynl version {}'.format(spynl_version))

#     if task == 'production':
#         get_login_cmd = ctx.run('aws ecr --profile %s get-login '
#                                 '--region eu-west-1' % prod_ecr_profile)
#         ctx.run(get_login_cmd.stdout.strip())
#         # tag & push image with spynl_version & buildnr as tag
#         ctx.run('docker tag spynl:v{v} {aws_uri}/spynl:v{v}_b{bnr}'
#                 .format(v=spynl_version, aws_uri=prod_ecr_uri, bnr=buildnr))
#         ctx.run('docker push {aws_uri}/spynl:v{v}_b{bnr}'
#                 .format(v=spynl_version, aws_uri=prod_ecr_uri, bnr=buildnr))
#     else:
#         get_login_cmd = ctx.run('aws ecr --profile %s get-login '
#                                 '--region eu-west-1' % dev_ecr_profile)
#         ctx.run(get_login_cmd.stdout.strip())

#         ctx.run('docker tag spynl:v{v} {aws_uri}/spynl:v{v}'
#                 .format(v=spynl_version, aws_uri=dev_ecr_uri))
#         ctx.run('docker push {aws_uri}/spynl:v{v}'
#                 .format(v=spynl_version, aws_uri=dev_ecr_uri))

#         # tag the image for being used in one of our defined Tasks
#         if task:
#             ecr_dev_tasks = [t.strip() for t in config
#                              .get('spynl.ops.ecr.dev_tasks', '')
#                              .split(',')]
#             for t in task.split(","):
#                 t = t.strip()
#                 if t not in ecr_dev_tasks:
#                     raise Exit("Task: %s not found in %s. Aborting ..."
#                                % (t, ecr_dev_tasks))
#                 print("[spynl ops.deploy] Deploying the new image for task "
#                       "%s ..." % t)
#                 ctx.run('docker tag spynl:v{v} {aws_uri}/spynl:{task}'
#                         .format(v=spynl_version, aws_uri=dev_ecr_uri, task=t))
#                 ctx.run('docker push {aws_uri}/spynl:{task}'
#                         .format(aws_uri=dev_ecr_uri, task=t))

#                 # stop the task (so ECS restarts it and grabs new image)
#                 tasks = ctx.run('aws ecs list-tasks --cluster spynl '
#                                 '--service-name spynl-%s' % t)
#                 for task_id in json.loads(tasks.stdout)['taskArns']:
#                     ctx.run('aws ecs stop-task --cluster spynl --task %s'
#                             % task_id)
#     ctx.run('docker logout')


# @task(help={'scm-url': 'The URL needed to clone the repo, either for '
#                        'git or mercurial. Please no revision information, '
#                        'you can use the revision parameter for that. '
#                        'Include the protocol, e.g. ssh or https.',
#             'developing': 'If True (default), python setup.py develop is '
#                           'used, otherwise install',
#             'revision': 'Which revision to update to (default: do not update)',
#             'fallbackrevision': 'Use this revision if the repository does not '
#                                 ' have the target revision.',
#             'install-deps': 'If True (default), pre-install dependencies '
#                             '(eg. via apt-get).',
#             'src-path': 'Desired installation path. Defaults to '
#                         '$VIRTUAL_ENV/src directory.'})
# def install(ctx, scm_url=None, developing=True, revision=None,
#             fallbackrevision=None, install_deps=True, src_path=None):
#     """
#     Clone a repo, update to revision or fallbackrevision
#     and install the Spynl package.
#     """
#     ctx.run('pip install --upgrade setuptools')  # make sure we have the latest
#     src_path = src_path or os.environ['VIRTUAL_ENV'] + '/src'
#     if scm_url is None:
#         raise Exit("[spynl dev.install] Please give the --scm-url parameter.")
#     scm_url = scm_url.strip('/')
#     # set scm_type
#     scm_type = (scm_url.endswith('.git') or '.git@' in scm_url) and 'git' or 'hg'
#     if not os.path.exists(src_path):
#         os.mkdir(src_path)
#     repo_name = scm_url.split('/')[-1]
#     if scm_type == 'git' and repo_name.endswith('.git'):
#         repo_name = repo_name[:-4]
#     repo_path = src_path + '/' + repo_name
#     if not os.path.exists(repo_path):
#         with chdir(src_path):
#             print("[spynl dev.install] CLONING from %s" % scm_url)
#             ctx.run('%s clone %s %s' % (scm_type, scm_url, repo_name))
#     else:
#         print("[spynl dev.install] UPDATING {}".format(repo_name))
#         with chdir(repo_path):
#             cmd = scm_type == 'git' and 'git pull' or 'hg pull --update'
#             ctx.run(cmd)
#     with chdir(repo_path):
#         if revision is not None:
#             cmd = scm_type == 'git' and 'git checkout' or 'hg update'
#             print('[spynl dev.install] Using revision %s ...' % revision)
#             # this might not work for mercurial anymore:
#             try:
#                 ctx.run('{} {}'.format(cmd, revision), warn=True)
#             except:
#                 def_branch = 'master' if scm_type == 'git' else 'default'
#                 print('[spynl dev.install] Updating to fallback revision %s ...'
#                         % fallbackrevision if fallbackrevision else def_branch)
#                 ctx.run('{} {}'.format(cmd, fallbackrevision))
#         if os.path.isfile('./setup.sh'):
#             pre_cmd = './setup.sh --pre-install '\
#                         '--virtualenv=%s' % os.environ['VIRTUAL_ENV']
#             if install_deps:
#                 pre_cmd += ' --install-dependencies'
#             ctx.run(pre_cmd)
#         if developing:
#             print("[spynl dev.install] DEVELOPING {}".format(repo_name))
#             ctx.run('python setup.py develop')
#         else:
#             print("[spynl dev.install] INSTALLING {}".format(repo_name))
#             ctx.run('python setup.py install')
#         if os.path.isfile('./setup.sh'):
#             ctx.run('./setup.sh --post-install')
#


for plugin in iter_entry_points('spynl.commands'):
    plugin.resolve()
