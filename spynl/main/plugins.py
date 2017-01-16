"""Module to find and include all spynl plugins"""
from pkg_resources import iter_entry_points  # pylint: disable=E0611
import logging


def include(config, name, _plugins=None):
    """
    Include a plugin. First, check if it is already included. Then, check its
    requirements (the plugin should implement the 'requires'-method for that).
    Finally, include the plugin (pyramid then calls the plugin's 'includeme'
    method, see http://pyramid.readthedocs.org/en/latest/api/config.html).
    """
    log = logging.getLogger(__name__)
    if _plugins is None:
        _plugins = config.get_settings()['plugins']

    if name not in _plugins:
        log.info('Initialising plugin %s', name.replace('.plugger', ''))
        _plugins.append(name)

        module = config.maybe_dotted(name)

        if hasattr(module, 'requires'):
            for name in module.requires():
                if not name.endswith('.plugger'):
                    name = name + '.plugger'
                include(config, name, _plugins)

        config.include(module)


def find(config):
    """
    Find all plugins.
    Either they are explicitly specified in settings or we find them in the
    'spynl'-namespace (which is declared in spynl.__init__). In that
    case, we look for entry_points in the group 'spynl.plugins', which they
    define in their setup.py.
    Finally, we call include on them.
    """
    log = logging.getLogger(__name__)
    settings = config.get_settings()
    plugins = settings['plugins']

    if 'enable_plugins' in settings:
        enable_plugins = settings['enable_plugins']
    else:
        enable_plugins = [e.name for e in
                          iter_entry_points('spynl.plugins')]

    for plugin in enable_plugins:
        log.debug('Found plugin %s', plugin.replace('.plugger', ''))
        include(config, plugin, plugins)


class PluginsLoaded(object):
    """ Event to signal that all plugins have been loaded"""
    def __init__(self, config):
        self.config = config


def main(config):
    """initialize this module, find all plugins and include them"""
    config.add_settings(plugins=[])

    config.add_directive('include_plugin', include)
    config.add_directive('find_plugins', find)
    config.find_plugins()
