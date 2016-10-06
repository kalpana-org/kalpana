
from collections import ChainMap
import os
import os.path
import sys
from typing import Any, Dict, Optional

import yaml

from PyQt5 import QtCore, QtGui


def default_config_dir() -> str:
    return os.path.join(os.getenv('HOME'), '.config', 'kalpana2')


def local_path(*path: str) -> str:
    """Return the path joined with the directory kalpana.py is in."""
    return os.path.join(sys.path[0], *path)


def get_keycode(key_string: str) -> int:
    """Return the key code (including modifiers) of a key combination string."""
    return QtGui.QKeySequence(key_string)[0]


class Settings(QtCore.QObject):
    """Loads and takes care of settings and stylesheets."""

    css_changed = QtCore.pyqtSignal(str)

    def __init__(self, config_dir: Optional[str]) -> None:
        """Initiate the class. Note that this won't load any files."""
        super().__init__()
        if config_dir is None:
            self.config_dir = default_config_dir()
        else:
            self.config_dir = config_dir
        self.settings = None  # type: ChainMap
        self.key_bindings = {}  # type: Dict[int, str]
        self.terminal_key = -1
        self.css = ''

    def reload_settings(self) -> None:
        self.settings = self.load_settings(self.config_dir)
        self.key_bindings = self.generate_key_bindings(self.settings)
        self.terminal_key = get_keycode(self.settings['terminal-key'])

    def reload_stylesheet(self) -> None:
        self.css = self.load_stylesheet(self.config_dir)

    def error(self, text: str) -> None:
        """Show an error when something goes wrong."""
        # TODO: do something more useful with this
        print('[SETTINGS ERROR]:', text)

    def load_settings(self, config_dir: str) -> ChainMap:
        """Read and return the settings, with default values overriden."""
        default_config_path = local_path('default_settings.yaml')
        config_path = os.path.join(config_dir, 'settings.yaml')
        config = {}  # type: Dict[str, Any]
        with open(default_config_path) as f:
            default_config = yaml.load(f.read())
        try:
            with open(config_path) as f:
                raw_config = f.read()
        except OSError:
            # This is fine, the config file is probably just not created
            pass
        else:
            try:
                config = yaml.load(raw_config)
            except yaml.YAMLError as e:
                self.error('Invalid yaml! ' + str(e))
        return ChainMap(config, default_config)

    def load_stylesheet(self, config_dir: str) -> str:
        """Read and return the stylesheet."""
        with open(local_path('theming', 'qt.css')) as f:
            default_css = f.read()
        css_path = os.path.join(config_dir, 'qt.css')
        try:
            with open(css_path) as f:
                user_css = f.read()
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
