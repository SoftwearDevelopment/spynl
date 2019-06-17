"""Module to find and include all spynl plugins"""
from pkg_resources import iter_entry_points  # pylint: disable=E0611


def main(config):
    """initialize this module, find all plugins and include them"""
    installed_plugins = {
        plugin.name: plugin for plugin in iter_entry_points('spynl.plugins')
    }

    # Either load what is requested or all the installed plugins.
    load = config.get_settings().get('enable_plugins')
    if load is None:
        load = list(installed_plugins.keys())

    # Recursively load plugins and their dependencies.
    def load_plugins(load):
        for plugin_ in load:
            try:
                plugin = installed_plugins.pop(plugin_)
            except KeyError:
                continue

            if plugin.extras:
                load_plugins(plugin.extras)

            # We call resolve instead of load because extras are not actually
            # available distributions but other plugins that need to be loaded
            # first. Load would call require which would raise.
            # http://setuptools.readthedocs.io/en/latest/pkg_resources.html#entrypoint-objects
            entrypoint = plugin.resolve()
            # If the entrypoint is a callable let pyramid include it.
            if callable(entrypoint):
                config.include(entrypoint)

    load_plugins(load)
