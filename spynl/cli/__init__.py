"""Crete a Invoke instance with dev and ops tasks."""

from invoke import Program, Collection

from spynl.main.version import __version__ as spynl_version
from spynl.cli.dev import tasks as dev_tasks
from spynl.cli.ops import tasks as ops_tasks


NAMESPACE = Collection()
NAMESPACE.add_collection(dev_tasks, 'dev')
NAMESPACE.add_collection(ops_tasks, 'ops')
program = Program(version=spynl_version, namespace=NAMESPACE)
