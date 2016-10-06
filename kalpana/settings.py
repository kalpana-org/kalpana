
from collections import ChainMap
import os
import os.path
import sys
from typing import Any, Dict, Optional

import yaml

from PyQt5 import QtGui


def default_config_dir() -> str:
    return os.path.join(os.getenv('HOME'), '.config', 'kalpana2')


def local_path(filename: str) -> str:
    return os.path.join(sys.path[0], filename)


class Settings():
    def __init__(self, config_dir: Optional[str]) -> None:
        if config_dir is None:
            self.config_dir = default_config_dir()
        else:
            self.config_dir = config_dir
        self._settings = self.load_settings(self.config_dir)
        self.key_bindings = self.generate_key_bindings(self._settings)

    def error(self, text: str) -> None:
        """Show an error when something goes wrong."""
        # TODO: do something more useful with this
        print('[SETTINGS ERROR]:', text)

    def load_settings(self, config_dir: str) -> ChainMap:
        """Load both default and override settings."""
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

    def generate_key_bindings(self, settings: Dict) -> Dict[int, str]:
        """Return a dict with keycode and the command to run."""
        return {QtGui.QKeySequence(key)[0]: command
                for key, command in settings['key-bindings'].items()}
