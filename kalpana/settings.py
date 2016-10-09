
from collections import ChainMap, defaultdict
import json
import os
import os.path
import re
import sys
from typing import Any, DefaultDict, Dict, Iterable, Match, Optional

import yaml

from PyQt5 import QtCore, QtGui

from kalpana.common import KalpanaObject


def default_config_dir() -> str:
    return os.path.join(os.getenv('HOME'), '.config', 'kalpana2')


def local_path(*path: str) -> str:
    """Return the path joined with the directory kalpana.py is in."""
    return os.path.join(sys.path[0], *path)


def get_keycode(key_string: str) -> int:
    """Return the key code (including modifiers) of a key combination string."""
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

    def __init__(self, config_dir: str) -> None:
        self._path = os.path.join(config_dir, 'command_history.json')
        self.command_frequency = defaultdict(int)  # type: DefaultDict[str, int]
        self.autocompletion_history = defaultdict(lambda: defaultdict(int))  # type: DefaultDict[str, DefaultDict[str, int]]
        try:
            with open(self._path) as f:
                data = json.loads(f.read())  # type: Dict[str, Any]
                autocompletion_history = data['autocompletion_history']
                command_frequency = data['command_frequency']
        except (IOError, json.JSONDecodeError):  # type: ignore
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
        with open(self._path, 'w') as f:
            f.write(json.dumps(data, sort_keys=True, indent=2))


class Settings(QtCore.QObject, KalpanaObject):
    """Loads and takes care of settings and stylesheets."""

    css_changed = QtCore.pyqtSignal(str)

    def __init__(self, config_dir: Optional[str]) -> None:
        """Initiate the class. Note that this won't load any files."""
        super().__init__()
        if config_dir is None:
            self.config_dir = default_config_dir()
        else:
            self.config_dir = config_dir
        self.registered_settings = {}  # type: Dict[str, KalpanaObject]
        self.command_history = CommandHistory(self.config_dir)
        self.settings = None  # type: ChainMap
        self.key_bindings = {}  # type: Dict[int, str]
        self.terminal_key = -1
        self.css = ''

    def save_settings(self) -> None:
        self.command_history.save()

    def reload_settings(self) -> None:
        self.settings = self.load_settings(self.config_dir)
        self.key_bindings = self.generate_key_bindings(self.settings)
        self.terminal_key = get_keycode(self.settings['terminal-key'])

    def reload_stylesheet(self) -> None:
        self.css = self.load_stylesheet(self.config_dir)

    def register_settings(self, names: Iterable[str], obj: KalpanaObject) -> None:
        """Register that an object is waiting for changes to a certain setting."""
        for name in names:
            self.registered_settings[name] = obj

    def notify_settings_changes(self, new_settings: ChainMap) -> None:
        """Send changed settings to the objects that registered them."""
        if new_settings:
            for setting, obj in self.registered_settings.items():
                if not self.settings or (new_settings[setting] != self.settings[setting]):
                    obj.setting_changed(setting, new_settings[setting])

    def load_settings(self, config_dir: str) -> ChainMap:
        """Read and return the settings, with default values overriden."""
        default_config_path = local_path('default_settings.yaml')
        config_path = os.path.join(config_dir, 'settings.yaml')
        config = {}  # type: Dict[str, Any]
        with open(default_config_path) as f:
            default_config = yaml.load(f.read())
        try:
            with open(config_path) as f:
                raw_config = f.read()  # type: str
        except OSError:
            # This is fine, the config file is probably just not created
            pass
        else:
            try:
                config = yaml.load(yaml_escape_unicode(raw_config))
            except yaml.YAMLError as e:
                self.error('Invalid yaml in the config: {}'.format(e))
        new_settings = ChainMap(config, default_config)
        self.notify_settings_changes(new_settings)
        return new_settings

    def load_stylesheet(self, config_dir: str) -> str:
        """Read and return the stylesheet."""
        with open(local_path('theming', 'qt.css')) as f:
            default_css = f.read()  # type: str
        css_path = os.path.join(config_dir, 'qt.css')
        try:
            with open(css_path) as f:
                user_css = f.read()  # type: str
        except OSError:
            # No file present which is perfectly fine
            user_css = ''
        css = default_css + '\n' + user_css
        self.css_changed.emit(css)
        return css

    def generate_key_bindings(self, settings: Dict) -> Dict[int, str]:
        """Return a dict with keycode and the command to run."""
        return {get_keycode(key): command
                for key, command in settings['key-bindings'].items()}
