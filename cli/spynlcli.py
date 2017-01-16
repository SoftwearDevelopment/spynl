from invoke import Program, Collection

from spynl.main.version import __version__ as spynl_version
from cli.dev import tasks as dev_tasks
from cli.dev import hg
from cli.ops import tasks as ops_tasks


ns = Collection()
ns.add_collection(dev_tasks, 'dev')
ns.add_collection(hg)
ns.add_collection(ops_tasks, 'ops')
program = Program(version=spynl_version, namespace=ns)
