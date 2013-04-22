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

from settingsmanager import get_paths

class PluginManager(QtCore.QObject):
    def __init__(self, *args):
        super().__init__()
        self.plugins, self.plugin_commands = init_plugins(*args)

    def get_compiled_hotkeys(self):
        hotkeys = {}
        for p in self.plugins:
            hotkeys.update(p.hotkeys)
        return hotkeys


def init_plugins(vert_layout, horz_layout, textarea, mainwindow,
                 settings_manager):
    def add_widget(widget, side):
        from pluginlib import NORTH, SOUTH, EAST, WEST
        if side in (NORTH, SOUTH):
            layout = vert_layout
        elif side in (WEST, EAST):
            layout = horz_layout
        if side in (NORTH, WEST):
            layout.insertWidget(0, widget)
        elif side in (SOUTH, EAST):
            layout.addWidget(widget)

    callbacks = [
        textarea.document().toPlainText,   # get_text()
        lambda:textarea.file_path,         # get_filepath()
        add_widget,                        # add_widget()
        textarea.new_file,                 # new_file()
        textarea.open_file,                # open_file()
        textarea.save_file,                # save_file()
        mainwindow.close,                  # quit()
    ]
    paths = get_paths()

    plugins = []
    plugin_commands = {}
    for name, path, module in get_plugins(paths['plugins'], paths['loadorder']):
        try:
            plugin_constructor = module.UserPlugin
        except AttributeError:
            print('"{0}" is not a valid plugin and was not loaded.'\
                  .format(name))
        else:
            p = plugin_constructor(callbacks, path)
            plugins.append(p)
            settings_manager.read_plugin_config.connect(p.read_config)
            settings_manager.write_plugin_config.connect(p.write_config)
            textarea.file_saved.connect(p.file_saved)
            textarea.document().contentsChanged.connect(p.contents_changed)
            plugin_commands.update(p.commands)

    return plugins, plugin_commands


def get_plugins(plugin_root_path, loadorder_path):
    loadorder = [l for l in common.read_file(loadorder_path).splitlines()
                 if not l.startswith('#')]

    out = []
    for plugin_name in loadorder:
        try:
            loaded_plugin = importlib.import_module(plugin_name)
        except ImportError:
            print("Plugin {} could not be imported. Most likely because it's "
                  "not a valid plugin.".format(plugin_name))
        else:
            out.append(plugin_name, join(plugin_root_path,plugin_name),
                                         loaded_plugin)
    return out
