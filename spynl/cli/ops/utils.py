"""Helper functions for the devops tasks."""

def docker_tag_and_push(ctx, ecr_profile, ecr_uri, version, build_num=None):
    """Tag and push the docker image to AWS."""
    get_login_cmd = ctx.run('aws ecr --profile %s get-login '
                            '--region eu-west-1' % ecr_profile)
    ctx.run(get_login_cmd.stdout.strip())

    # tag & push image with spynl_version & buildnr as tag
    cmd = 'docker tag spynl:v{v} {aws_uri}/spynl:v{v}'
    if build_num is not None:
        cmd += '_b{}'.format(build_num)
    ctx.run(cmd.format(v=version, aws_uri=ecr_uri, bnr=build_num))

    # push docker image
    cmd = 'docker push {aws_uri}/spynl:v{v}'
    if build_num is not None:
        cmd += '_b{}'.format(build_num)
    ctx.run(cmd.format(v=version, aws_uri=ecr_uri, bnr=build_num))
