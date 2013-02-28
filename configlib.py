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

from PyQt4 import QtGui

from libsyntyche import common


def read_config(config_file_path, default_config):
        """ Read the config and update the appropriate variables. """
        default_config = common.read_json(common.local_path('defaultcfg.json'))

        legal_values = {k:v['values'] for k,v \
                        in default_config['settings'].items()}
        acronyms = {v['acronym']:name for name,v \
                        in default_config['settings'].items()}

        def check_config(cfg, defcfg):
            """ Make sure the config is valid """
            out = {}
            for key, section in defcfg.items():
                out[key] = cfg.get(key, section['values'][0])
                # If there are restrictions on the value, set to the default
                if len(legal_values[key]) > 1 and out[key] not in legal_values[key]:
                    print('config option "{}" has illegal value: {}'
                          ''.format(key, out[key]))
                    out[key] = section['values'][0]
            return out

        try:
            rawcfg = common.read_json(config_file_path)
        except (IOError, ValueError):
            print('no/bad config')
            cfg = check_config({}, default_config['settings'])
        else:
            cfg = check_config(rawcfg['settings'], default_config['settings'])

        return {'settings': cfg,
                'legal_values': legal_values,
                'acronyms': acronyms}


def write_config(config_file_path, settings):
        """
        Read the config, update the info with appropriate variables (optional)
        and then overwrite the old file with the updated config.
        """
        cfg = {
            'settings': settings
        }

        if not exists(dirname(config_file_path)):
            os.makedirs(dirname(config_file_path), mode=0o755, exist_ok=True)
            print('Creating config path...')
        common.write_json(config_file_path, cfg)


def get_paths():
    import platform
    # Paths init
    if platform.system() == 'Linux':
        config_dir = join(os.getenv('HOME'), '.config', 'kalpana')
    else: # Windows
        config_dir = common.local_path('')
    path = lambda fname: join(config_dir, fname)

    theme_path = path('stylesheet.css')
    config_file_path = path('kalpana.conf')
    loadorder_path = path('loadorder.conf')
    return config_file_path, config_dir, theme_path, loadorder_path


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
