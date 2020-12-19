# Copyright nycz 2011-2020

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
import json
from pathlib import Path
import re
from typing import (cast, Any, ChainMap, DefaultDict, Dict, Iterable, Mapping,
                    Match, Optional)

import yaml

from PyQt5 import QtCore, QtGui
from libsyntyche.widgets import mk_signal1

from .common import KalpanaObject


LOCAL_DATA_DIR = Path(__file__).resolve().parent / 'data'


def default_config_dir() -> Path:
    return Path.home() / '.config' / 'kalpana2'


def get_keycode(key_string: str) -> int:
    """
    Return the key code (including modifiers) of a key combination string.
    """
    return QtGui.QKeySequence(key_string)[0]


def yaml_escape_unicode(text: str) -> str:
    r"""
    Return a string where all 32 bit characters are escaped.

    There's a bug in PyYAML that stops any character above \ufffe from being
    read. Fortunately other characters can still be read without problems as
    long as they're written in eight-character form: \U12345678.
    """
    def escape(match: Match[str]) -> str:
        return '\\U{:0>8}'.format(hex(ord(match.group()))[2:])
    return re.sub(r'[\ufffe-\U0001f9ff]', escape, text)


class CommandHistory:

    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / 'command_history.json'
        self.command_frequency: DefaultDict[str, int] = defaultdict(int)
        self.autocompletion_history: DefaultDict[str, DefaultDict[str, int]] \
            = defaultdict(lambda: defaultdict(int))
        try:
            data: Dict[str, Any] = json.loads(self._path.read_text())
            autocompletion_history = data['autocompletion_history']
            command_frequency = data['command_frequency']
        except (IOError, json.JSONDecodeError):
            pass
        else:
            self.command_frequency.update(command_frequency)
            for abbr, data in autocompletion_history.items():
                self.autocompletion_history[abbr].update(data)
        self._hash = json.dumps([self.command_frequency,
                                self.autocompletion_history], sort_keys=True)

    def save(self) -> None:
        data = {'autocompletion_history': self.autocompletion_history,
                'command_frequency': self.command_frequency}
        json_data = json.dumps(data, sort_keys=True, indent=2)
        self._path.write_text(json_data)


class Settings(QtCore.QObject, KalpanaObject):
    """Loads and takes care of settings and stylesheets."""

    css_changed = mk_signal1(str)

    def __init__(self, config_dir: Optional[Path]) -> None:
        """Initiate the class. Note that this won't load any files."""
        super().__init__()
        self.config_dir = config_dir or default_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.active_file: str = ''
        self.registered_settings: Dict[str, KalpanaObject] = {}
        self.command_history = CommandHistory(self.config_dir)
        self.settings: ChainMap[str, Any] = ChainMap()
        self.key_bindings: Dict[int, str] = {}
        self.terminal_key = -1
        self.css = ''

    def save_settings(self) -> None:
        with self.try_it("Couldn't save settings"):
            self.command_history.save()

    def reload_settings(self) -> None:
        with self.try_it("Couldn't reload settings"):
            self.settings = self.load_settings(self.config_dir)
            self.key_bindings = self.generate_key_bindings(self.settings)
            self.terminal_key = get_keycode(self.settings['terminal-key'])

    def reload_stylesheet(self) -> None:
        with self.try_it("Couldn't reload stylesheet"):
            self.css = self.load_stylesheet(self.config_dir)
            self.css_changed.emit(self.css)

    def file_opened(self, filepath: str, is_new: bool) -> None:
        if filepath:
            self.active_file = str(Path(filepath).resolve())
            self.reload_settings()

    def file_saved(self, filepath: str, new_name: bool) -> None:
        if new_name:
            self.active_file = str(Path(filepath).resolve())
            self.reload_settings()

    def change_setting(self, name: str, new_value: Any) -> None:
        # TODO: warning if the setting doesn't exist?
        self.settings[name] = new_value
        if not self.active_file:
            return
        all_files_config_path = self.config_dir / 'file_settings.yaml'
        try:
            all_files_config = self._load_yaml_file(all_files_config_path)
        except yaml.YAMLError as e:
            self.error(f'Invalid yaml in the file config: {e}')
        else:
            file_settings = self.settings.maps[0]
            all_files_config[self.active_file] = file_settings
            with self.try_it("Couldn't save yaml settings to disk"):
                yaml_data = yaml.safe_dump(all_files_config,
                                           default_flow_style=False)
                with open(all_files_config_path, 'w') as f:
                    f.write(yaml_data)

    def register_settings(self, names: Iterable[str],
                          obj: KalpanaObject) -> None:
        """
        Register that an object is waiting for changes to a certain setting.
        """
        for name in names:
            self.registered_settings[name] = obj

    def notify_settings_changes(self, new_settings: Mapping[str, Any]) -> None:
        """Send changed settings to the objects that registered them."""
        if new_settings:
            for setting, obj in self.registered_settings.items():
                if not self.settings \
                        or (new_settings[setting] != self.settings[setting]):
                    with obj.try_it(f"Couldn't update setting {setting!r}"):
                        obj.setting_changed(setting, new_settings[setting])

    def _load_yaml_file(self, config_path: Path) -> Dict[str, Any]:
        """
        Load a yaml config file.

        If the file doesn't exist, return an empty dict.
        If the yaml is invalid, return None.
        """
        try:
            raw_config = config_path.read_text()
        except OSError:
            return {}
        else:
            config = yaml.safe_load(yaml_escape_unicode(raw_config))
            if not isinstance(config, dict):
                raise yaml.YAMLError('root type has to be a dict')
            return config

    def load_settings(self, config_dir: Path) -> ChainMap[str, Any]:
        """Read and return the settings, with default values overriden."""
        # Default config
        default_config_path = LOCAL_DATA_DIR / 'default_settings.yaml'
        default_config = cast(Dict[str, Any],
                              yaml.safe_load(default_config_path.read_text()))
        # Global config
        global_config_path = config_dir / 'settings.yaml'
        global_config: Dict[str, Any] = {}
        try:
            global_config = self._load_yaml_file(global_config_path)
        except yaml.YAMLError as e:
            self.error(f'Invalid yaml in the global config: {e}')
        # File specific config
        all_files_config_path = self.config_dir / 'file_settings.yaml'
        file_config: Dict[str, Any] = {}
        try:
            all_files_config = self._load_yaml_file(all_files_config_path)
            file_config = all_files_config.get(self.active_file, {})
        except yaml.YAMLError as e:
            self.error(f'Invalid yaml in the file config: {e}')
        new_settings = ChainMap(file_config, global_config, default_config)
        self.notify_settings_changes(new_settings)
        return new_settings

    @staticmethod
    def load_stylesheet(config_dir: Path) -> str:
        """Read and return the stylesheet."""
        default_css = (LOCAL_DATA_DIR / 'qt.css').read_text()
        try:
            user_css = (config_dir / 'qt.css').read_text()
        except OSError:
            # No file present which is perfectly fine
            user_css = ''
        return default_css + '\n' + user_css

    @staticmethod
    def generate_key_bindings(settings: Mapping[str, Any]
                              ) -> Dict[int, str]:
        """Return a dict with keycode and the command to run."""
        return {get_keycode(key): command
                for key, command in settings['key-bindings'].items()}
