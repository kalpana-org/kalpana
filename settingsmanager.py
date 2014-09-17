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

from collections import defaultdict, ChainMap
import os
from os.path import join, exists, dirname
import re
import shutil

from PyQt4 import QtGui
from PyQt4.QtCore import pyqtSignal, QObject, Qt

from libsyntyche import common
from common import SettingsError

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

        self.auto_setting_acronyms = get_auto_setting_acronym(self.default_config)
        self.setting_types = get_setting_types(self.default_config)
        self.setting_callbacks = defaultdict(list)

        self.auto_settings, self.manual_settings = {}, {}
        self.settings = ChainMap()

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
        """
        Save a callback function for a specified setting to be called when the
        setting is changed.

        settingname should be the full name (case-sensitive), not the acronym.

        Note that this doesn't check anything when called to make sure the
        setting actually exists.
        """
        self.setting_callbacks[settingname].append(callback)

    def set_setting(self, key, value):
        """
        Change the setting in the appropriate setting sub-dict.
        This should be used instead of self.setting[x] = y since that doesn't
        update the source dicts (self.auto_settings and self.manual_settings).
        """
        if key in self.auto_settings:
            self.auto_settings[key] = value
        elif key in self.manual_settings:
            self.manual_settings[key] = value

    def load_settings(self, refresh_only=False):
        """ Load settings from the main config file. """
        oldsettings = self.settings
        self.auto_settings, self.manual_settings\
                 = read_config(self.paths['config_file'], self.default_config)
        self.settings = ChainMap(self.auto_settings, self.manual_settings)

        def revert_setting(key):
            if key in oldsettings:
                reverted_value = oldsettings[key]
            else:
                reverted_value = self.default_config[key]
            self.set_setting(key, reverted_value)

        # Make sure the settings aren't fucked up yo
        for key, value in self.settings.items():
            if oldsettings.get(key) == value:
                continue
            # First make a simple check to see if the value is the right type
            if not valid_setting(key, value, self.setting_types):
                print('Invalid type for setting: "{}"'.format(key))
                self.error.emit('Errors while reading the config. Check terminal output.')
                revert_setting(key)
            # Then do a live update and see if things blow up
            try:
                self.update_runtime_setting(key, value)
            except SettingsError as e:
                print(str(e))
                self.error.emit('Errors while reading the config. Check terminal output.')
                revert_setting(key)

        if self.settings['start in terminal'] and not refresh_only:
            self.switch_focus_to_terminal.emit()

        self.save_settings()
        self.read_plugin_config.emit()
        self.set_theme()


    def change_setting(self, arg):
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
        # Print all settings
        if not arg.strip():
            self.print_.emit('Settings: {}'.format(', '.\
                             join(sorted(self.auto_setting_acronyms.keys()))))
            return
        parsed_arg = re.match(r"(?P<setting>\S+)(\s+(?P<value>.+?))?\s*$", arg)
        acronym = parsed_arg.group('setting')
        if acronym not in self.auto_setting_acronyms:
            self.error.emit('No such setting: {}'.format(acronym))
            return
        setting = self.auto_setting_acronyms[acronym]
        # Set new value if there is one
        if parsed_arg.group('value'):
            new_value = parsed_arg.group('value')
            parsed_value = parse_terminal_setting(new_value,
                                    self.setting_types['automatic'][setting])
            if parsed_value is None:
                self.error.emit('Wrong value "{}" for setting: {}'\
                                .format(new_value, setting))
            else:
                try:
                    self.update_runtime_setting(setting, parsed_value)
                except SettingsError as e:
                    self.error.emit(str(e))
                else:
                    self.auto_settings[setting] = parsed_value
                    self.save_settings()
                    self.print_.emit('{} now set to: {}'.format(setting, parsed_value))
        # Otherwise just print the current value
        else:
            name = setting.lower()
            value = self.auto_settings[setting]
            self.print_.emit('{} = {}'.format(name, value))

    def update_runtime_setting(self, key, new_value):
        """ Change specific runtime-settings. """
        for callback in self.setting_callbacks.get(key, []):
            callback(new_value)

    def save_settings(self):
        """ Save the settings to the config file """
        config_file_path = self.paths['config_file']
        settings = {'automatic': self.auto_settings, 'manual': self.manual_settings}
        common.write_json(config_file_path, settings)
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

def get_default_config():
    return common.read_json(common.local_path('defaultconfig.json'))

def get_auto_setting_acronym(default_config):
    """
    Return a list of (lower case) acronyms generated from all upper case
    characters in the automatic settings' names.
    E.g. "A Super awesome Setting!" --> "ass"
    """
    return {''.join(x for x in setting if x.isupper()).lower():setting
            for setting in default_config['automatic']}

def get_setting_types(default_config):
    """
    Return a dict with the type of each setting in the config using
    the default values in the default config.
    Only settings with default booleans, ints or floats are recognized.
    """
    setting_types = {'automatic':{}, 'manual':{}}
    for category in ('automatic', 'manual'):
        for setting, value in default_config[category].items():
            if isinstance(value, bool):
                type_ = bool
            elif isinstance(value, int):
                type_ = int
            elif isinstance(value, float):
                type_ = float
            else:
                type_ = None
            setting_types[category][setting] = type_
    return setting_types

def read_config(config_file_path, default_config):
    """
    Return the config after adding all settings it misses from the default
    config and purgin all settings it has that the default doesn't have.

    Return the default config if the current config is broken or doesn't exist.
    """
    try:
        raw_settings = common.read_json(config_file_path)
    except:
        print('Bad or no config, replacing with default')
        return default_config['automatic'], default_config['manual']
    def generate_settings(type_):
        return {k:raw_settings[type_][k] if k in raw_settings[type_] else v \
                for k,v in default_config[type_].items()}
    return generate_settings('automatic'), generate_settings('manual')

def valid_setting(setting, value, setting_types):
    """
    Return True if the setting matches the type that's been identified earlier
    or the type is unrecognized (is None).

    NOTE that this should NOT be called from the terminal-called change_setting
    function since all values there are strings. This should only be called on
    values read from the config.
    """
    if setting in setting_types['automatic']:
        type_ = setting_types['automatic'][setting]
    else:
        type_ = setting_types['manual'][setting]
    if type_ is None:
        return True
    return isinstance(value, type_)

def parse_terminal_setting(value, setting_type):
    """ Return the value converted to its correct type. """
    if setting_type == bool:
        if value.lower() in ('1', 'y', 'true'):
            return True
        elif value.lower() in ('0', 'n', 'false'):
            return False
    elif setting_type == int:
        try:
            return int(value)
        except:
            return None
    elif setting_type == float:
        try:
            return float(value)
        except:
            return None
    # "Dump" type for everything else
    elif setting_type == None:
        return value
    return None

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

