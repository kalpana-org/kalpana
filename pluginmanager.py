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
    def __init__(self, *args):
        super().__init__()
        self.plugins, self.plugin_commands = init_plugins(*args)

    def get_compiled_hotkeys(self):
        hotkeys = {}
        for p in self.plugins:
            hotkeys.update(p.hotkeys)
        return hotkeys


def init_plugins(config_dir, vert_layout, horz_layout,
                 textarea, mainwindow, settings_manager):
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

    plugins = []
    plugin_commands = {}
    for name, path, module in get_plugins(config_dir):
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


def get_plugins(root_path):
    loadorder_path = join(root_path, 'loadorder.conf')

    # Get load order from file
    try:
        loadorder = common.read_json(loadorder_path)
        assert len(loadorder) > 0
    except (IOError, AssertionError):
        pluginlist, activelist = [],[]
    else:
        pluginlist, activelist = zip(*loadorder)
        pluginlist = list(pluginlist)
        activelist = list(activelist)

    # Generate all existing plugins
    rawplugins = {}
    plugin_root_path = join(root_path, 'plugins')
    if not exists(plugin_root_path):
        os.makedirs(plugin_root_path, exist_ok=True)
    for name in os.listdir(plugin_root_path):
        plugin_path = join(plugin_root_path, name)
        if not isfile(join(plugin_path, name + '.py')):
            continue
        if name not in pluginlist:
            pluginlist.append(name)
            activelist.append(True)
        sys.path.append(plugin_path)
        rawplugins[name] = (plugin_path, importlib.import_module(name))

    # Update the load order
    newpluginlist = [(p,a) for p,a in zip(pluginlist, activelist)
                     if p in rawplugins]

    common.write_json(loadorder_path, newpluginlist, sort_keys=False)

    # Generate all the relevant plugins in the right order
    plugins = [(p, rawplugins[p][0], rawplugins[p][1])
               for p,is_active in zip(pluginlist, activelist)
               if p in rawplugins and is_active]

    return plugins
