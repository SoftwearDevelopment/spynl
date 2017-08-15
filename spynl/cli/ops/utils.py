"""Helper functions for the devops tasks."""

import json

from invoke.exceptions import Exit

from spynl.main.pkg_utils import get_dev_config


def get_ecr_profile_and_uri(task):
    """Return either the dev ecr profile and uri or prod one."""
    key, env = 'dev', 'development'
    if task == 'production':
        key, env = 'prod', task
    setting = 'spynl.ops.ecr.{}_url'.format(key)

    ecr_profile, ecr_uri = get_dev_config().get(setting, '').split('@')
    if not ecr_uri:
        raise Exit('[spynl ops.deploy] ECR for {} is not configured. '
                   'Exiting ...'.format(env))

    return ecr_profile, ecr_uri


def validate_tasks(*tasks):
    """Check if given tasks are included in ecr_dev_tasks."""
    ecr_dev_tasks = [
        t.strip()
        for t in get_dev_config().get('spynl.ops.ecr.dev_tasks', '').split(',')
    ]
    for task in tasks:
        task = task.strip()
        if task not in ecr_dev_tasks:
            raise Exit("Task: %s not found in %s. Aborting ..."
                       % (task, ecr_dev_tasks))


def trigger_aws_ecr_tasks(ctx, *tasks):
    """Build tasks by stopping running ones so aws pick the newest ones."""
    for task in tasks:
        task = task.strip()
        print("[spynl ops.deploy] Deploying the new image for task "
              "%s ..." % task)
        # stop the task (so ECS restarts it and grabs new image)
        running_tasks = ctx.run('aws ecs list-tasks --cluster spynl '
                                '--service-name spynl-%s' % task)
        for task_id in json.loads(running_tasks.stdout)['taskArns']:
            ctx.run('aws ecs stop-task --cluster spynl --task %s' % task_id)
