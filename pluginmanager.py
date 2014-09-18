# Copyright nycz 2011-2013

# This file is part of Kalpana.

# Kalpana is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Kalpana is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Kalpana. If not, see <http://www.gnu.org/licenses/>.

import importlib
import os
from os.path import join, exists, dirname, isfile
import sys

from PyQt4 import QtCore

from libsyntyche import common

class PluginManager(QtCore.QObject):
    def __init__(self, settingsmanager, *args):
        super().__init__()
        self.plugins, self.plugin_commands =\
                init_plugins(settingsmanager, *args)

    def get_compiled_hotkeys(self):
        hotkeys = {}
        for name, p in self.plugins:
            hotkeys.update(p.hotkeys)
        return hotkeys


def init_plugins(settingsmanager, mainwindow, textarea, terminal, chaptersidebar):
    plugins = []
    plugin_commands = {}

    objects = {
        'mainwindow': mainwindow,
        'textarea': textarea,
        'terminal': terminal,
        'settings manager': settingsmanager,
        'plugins': plugins,
        'chaptersidebar': chaptersidebar
    }

    paths = settingsmanager.paths
    for name, path, module in get_plugins(paths['plugins'], paths['loadorder']):
        try:
            plugin_constructor = module.UserPlugin
        except AttributeError:
            print('"{0}" is not a valid plugin and was not loaded.'\
                  .format(name))
        else:
            p = plugin_constructor(objects, lambda:path)
            plugins.append((name, p))
            p.signal_print.connect(terminal.print_)
            p.signal_error.connect(terminal.error)
            p.signal_prompt.connect(terminal.prompt)
            settingsmanager.read_plugin_config.connect(p.read_config)
            settingsmanager.write_plugin_config.connect(p.write_config)
            plugin_commands.update(p.commands)

    return plugins, plugin_commands


def get_plugins(plugin_root_path, loadorder_path):
    # Create the loadorder file if it doesn't exist
    if not os.path.exists(loadorder_path):
        open(loadorder_path, 'w').close()
    loadorder = [l for l in common.read_file(loadorder_path).splitlines()
                 if l and not l.startswith('#')]

    out = []
    for plugin_name in loadorder:
        plugin_path = join(plugin_root_path,plugin_name)
        if not os.path.exists(plugin_path):
            print("Plugin directory {} doesn't exist.".format(plugin_name))
            continue
        sys.path.append(plugin_path)
        try:
            loaded_plugin = importlib.import_module(plugin_name)
        except ImportError:
            print("Plugin {} could not be imported. Most likely because it's "
                  "not a valid plugin.".format(plugin_name))
        else:
            print("Plugin {} loaded.".format(plugin_name))
            out.append((plugin_name, plugin_path, loaded_plugin))
    return out
