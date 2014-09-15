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

from collections import defaultdict
import os
from os.path import join, exists, dirname
import re
import shutil

from PyQt4 import QtGui
from PyQt4.QtCore import pyqtSignal, QObject, Qt

from libsyntyche import common

class SettingsManager(QObject):
    print_ = pyqtSignal(str)
    error = pyqtSignal(str)
    switch_focus_to_terminal = pyqtSignal()
    read_plugin_config = pyqtSignal()
    write_plugin_config = pyqtSignal()
    set_stylesheet = pyqtSignal(str)

    def __init__(self, configdir):
        super().__init__()
        self.paths = get_paths(configdir)
        for x in ('config_dir', 'plugins', 'spellcheck-pwl'):
            if not exists(self.paths[x]):
                os.makedirs(self.paths[x], mode=0o755, exist_ok=True)
        self.current_cssdata = ''

        self.default_config = get_default_config()
        self.settings = {}
        self.setting_callbacks = defaultdict(list)

    # ======= Dict wrappers =============
    def get_setting(self, key):
        return self.settings[key]

    def get_path(self, key):
        return self.paths[key]

    def get_loadorder_path(self):
        return self.paths['loadorder']

    def get_config_directory(self):
        return self.paths['config_dir']
    # ===================================

    def register_setting(self, settingname, callback):
        self.setting_callbacks[settingname].append(callback)


    def load_settings(self, refresh_only=False):
        """
        Load settings from the main config file.
        """
        self.settings = read_config(self.paths['config_file'], self.default_config)

        if self.settings['sit'] and not refresh_only:
            self.switch_focus_to_terminal.emit()

        for key, value in self.settings.items():
            self.update_runtime_setting(key, value)

        self.save_settings()
        self.read_plugin_config.emit()
        self.set_theme()


    def change_setting(self, argument):
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
            self.print_.emit('Settings: {}'.format(', '.\
                             join(sorted(self.default_config.keys()))))
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
        setting = parsed_arg.group('setting')
        if setting not in self.default_config:
            self.error.emit('No such setting: {}'.format(setting))
            return

        # Set new value if there is one
        if parsed_arg.group('value'):
            new_value = parsed_arg.group('value')
            parsed_value = parse_terminal_setting(new_value, self.default_config[setting])
            if parsed_value is None:
                self.error.emit('Wrong value {} for setting: {}'\
                                .format(new_value, setting))
            else:
                self.update_runtime_setting(setting, parsed_value)
                self.settings[setting] = parsed_value
                self.save_settings()
                self.print_.emit('{} now set to: {}'.format(setting, parsed_value))
        # Otherwise just print the current value
        else:
            def get_allowed_values(settings_info):
                out = settings_info['type']
                if 'allowed values' in settings_info:
                    out += ': ' + ', '.join(map(str, settings_info['allowed values']))
                return out
            value = self.settings[setting]
            name = self.default_config[setting]['desc']
            self.print_.emit('{} = {} ({})'.format(name, value,
                             get_allowed_values(self.default_config[setting])))

    def update_runtime_setting(self, key, new_value):
        """
        Change specific runtime-settings.
        """
        for callback in self.setting_callbacks.get(key, []):
            callback(new_value)

    def save_settings(self):
        """ Save the settings to the config file """
        config_file_path = self.paths['config_file']
        common.write_json(config_file_path, self.settings)
        self.write_plugin_config.emit()

    def set_theme(self):
        # Copy in the default theme if a customized doesn't exist
        if not os.path.exists(self.paths['theme']):
            defaultcss = common.local_path(join('themes','default.css'))
            shutil.copyfile(defaultcss, self.paths['theme'])
        cssdata = common.read_file(self.paths['theme'])
        # plugin_themes = [p.get_theme() for p in self.plugins]
        # stylesheet = '\n'.join([stylesheet] + [p for p in plugin_themes if p])
        if cssdata != self.current_cssdata:
            self.set_stylesheet.emit(common.parse_stylesheet(cssdata))
        self.current_cssdata = cssdata


## ==== Functions ========================================================= ##

def allowed_value(value, settings_info):
    if 'allowed values' in settings_info:
        if value not in settings_info['allowed values']:
            return False
    return True

def parse_terminal_setting(value, settings_info):
    if settings_info['type'] == 'bool':
        if value.lower() in ('1', 'y', 'true'):
            return True
        elif value.lower() in ('0', 'n', 'false'):
            return False
        else:
            return None
    elif settings_info['type'] == 'int':
        try:
            return int(value)
        except:
            return None
    elif settings_info['type'] == 'float':
        try:
            return float(value)
        except:
            return None
    if not allowed_value(value, settings_info):
        return None
    return value

def get_default_config():
    default_config = common.read_json(common.local_path('defaultcfg.json'))
    return default_config

def read_config(config_file_path, default_config):
    default_settings = {k:v['default'] for k,v in default_config.items()}
    try:
        raw_settings = common.read_json(config_file_path)
    except:
        print('no/bad config')
        return default_settings

    raw_settings = {k:v for k,v in raw_settings.items()
                    if k in default_settings\
                        and is_valid_setting(v, default_config[k])}

    settings = default_settings.copy()
    settings.update(raw_settings)
    return settings

def is_valid_setting(value, settings_info):
    # TODO: Might do some real checking wrt keycode in the future eh?
    valid_types = (
        ('str',  str),
        ('bool', bool),
        ('int',  int),
        ('float', float),
        ('keycode', str))
    for name, type_ in valid_types:
        if settings_info['type'] == name and type(value) != type_:
            return False
    # lol fuk u if the type is something else eheh

    if not allowed_value(value, settings_info):
        return False
    return True

def get_paths(custom_config_dir):
    import platform
    # Paths init
    if custom_config_dir and os.path.isdir(custom_config_dir):
        config_dir = custom_config_dir
    elif platform.system() == 'Linux':
        config_dir = join(os.getenv('HOME'), '.config', 'kalpana')
    else: # Windows
        config_dir = common.local_path('')
    path = lambda fname: join(config_dir, fname)

    return {
        'config_dir':   config_dir,
        'config_file':  path('kalpana.conf'),
        'theme':        path('stylesheet.css'),
        'loadorder':    path('loadorder.conf'),
        'plugins':      path('plugins'),
        'spellcheck-pwl': path('spellcheck-pwl')
    }
