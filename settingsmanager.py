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

import os
from os.path import join, exists, dirname, isfile
import re
import sys

from PyQt4 import QtGui
from PyQt4.QtCore import pyqtSignal, QObject, Qt

from libsyntyche import common

class SettingsManager(QObject):
    print_ = pyqtSignal(str)
    error = pyqtSignal(str)
    switch_focus_to_terminal = pyqtSignal()
    set_number_bar_visibility = pyqtSignal(bool)
    set_vscrollbar_visibility = pyqtSignal(Qt.ScrollBarPolicy)
    set_terminal_command_separator = pyqtSignal(str)
    read_plugin_config = pyqtSignal()
    write_plugin_config = pyqtSignal()
    set_stylesheet = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.paths = get_paths()

        self.settings = {}
        self.allowed_setting_values = {}
        self.setting_names = {}

    def get_setting(self, key):
        return self.settings[key]

    def get_loadorder_path(self):
        return self.paths['loadorder']

    def get_config_directory(self):
        return self.paths['config_dir']

    def load_settings(self, refresh_only=False):
        """
        Load settings from the main config file.
        """
        default_config_path = common.local_path('defaultcfg.json')
        settings_dict = read_config(self.paths['config_file'],
                                    default_config_path)

        loaded_settings = settings_dict['settings']
        self.allowed_setting_values = settings_dict['legal_values']
        self.setting_names = settings_dict['acronyms']

        if loaded_settings['start_in_term'] and not refresh_only:
            self.switch_focus_to_terminal.emit()

        for key, value in loaded_settings.items():
            self.set_setting(key, value, quiet=True)

        # Make sure any potential corrected errors are saved
        self.save_settings()

        self.read_plugin_config.emit()
        self.set_theme()


    def manage_settings(self, argument):
        """
        Called from terminal.
        Allowed value for argument:
            <setting acronym> [<new value>]

        If new value is not specified, print current and allowed values
        for the specified setting.
        Otherwise set the setting to the new value.

        Print relevant error if value is not allowed, acronym does not exist,
        or the structure of argument does not follow above specification.
        """
        if not argument.strip():
            self.print_.emit('Settings: {}'\
                             .format(', '.join(sorted(self.setting_names))))
            return

        arg_rx = re.compile(r"""
            (?P<setting>\S+)
            (
                \ +
                (?P<value>.+?)
            )?
            \s*
            $
        """, re.VERBOSE)
        parsed_arg = arg_rx.match(argument)
        acronym = parsed_arg.group('setting')
        if acronym not in self.setting_names:
            self.error.emit('No such setting: {}'.format(acronym))
            return
        name = self.setting_names[acronym]

        # Set new value if there is one
        if parsed_arg.group('value'):
            new_value = parsed_arg.group('value')
            success = self.set_setting(name, new_value)
            if success:
                self.save_settings()
        # Otherwise just print the current value
        else:
            value = self.settings[name]
            self.print_.emit('{} = {} ({})'.format(name, value,
                ', '.join([str(x) for x in self.allowed_setting_values[name]])))


    def set_setting(self, key, new_value, quiet=False):
        """
        Set the value of a setting the the specified new value.

        key is the name of the setting.
        new_value is the new value.
        quiet means only errors will be printed.
        """
        # TODO: this needs to be better
        if isinstance(new_value, str):
            if new_value.lower() in ('n', 'false'):
                new_value = False
            elif new_value.lower() in ('y', 'true'):
                new_value = True

        if len(self.allowed_setting_values[key]) > 1 \
                and new_value not in self.allowed_setting_values[key]:
            self.error.emit('Wrong value {} for setting: {}'\
                            .format(new_value, key))
            return False
        self.settings[key] = new_value
        if not quiet:
            self.print_.emit('{} now set to: {}'.format(key, new_value))

        # Setting specific settings... yyyeah.
        if key == 'linenumbers':
            self.set_number_bar_visibility.emit(new_value)
        elif key == 'vscrollbar':
            policy = {'on': Qt.ScrollBarAlwaysOn,
                      'auto': Qt.ScrollBarAsNeeded,
                      'off':Qt.ScrollBarAlwaysOff}
            self.set_vscrollbar_visibility.emit(policy[new_value])
        elif key == 'cmd_separator':
            self.set_terminal_command_separator.emit(new_value)
        return True

    def save_settings(self):
        write_config(self.paths['config_file'], self.settings)
        self.write_plugin_config.emit()

    def set_theme(self):
        stylesheet = common.read_stylesheet(self.paths['theme'])
        # plugin_themes = [p.get_theme() for p in self.plugins]
        # stylesheet = '\n'.join([stylesheet] + [p for p in plugin_themes if p])
        self.set_stylesheet.emit(stylesheet)



## ==== Functions ========================================================= ##

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
            if len(legal_values[key]) > 1 \
                        and out[key] not in legal_values[key]:
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

    return {
        'config_dir':   config_dir,
        'config_file':  path('kalpana.conf'),
        'theme':        path('stylesheet.css'),
        'loadorder':    path('loadorder.conf')
    }
