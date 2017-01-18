from invoke import Program, Collection

from spynl.main.version import __version__ as spynl_version
from spynl.cli.dev import tasks as dev_tasks
from spynl.cli.ops import tasks as ops_tasks


ns = Collection()
ns.add_collection(dev_tasks, 'dev')
ns.add_collection(ops_tasks, 'ops')
program = Program(version=spynl_version, namespace=ns)
