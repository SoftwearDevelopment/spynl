from pkg_resources import iter_entry_points

from .commands import cli, dev


for plugin in iter_entry_points('spynl.commands'):
    plugin.resolve()
