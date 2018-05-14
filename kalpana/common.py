# Copyright nycz 2011-2016

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

"""
Classes and functions needed in multiple different modules.

This is to avoid potential circular imports.
"""

from typing import Any, Callable, List, Optional

from PyQt5.QtCore import pyqtSignal, QVariant
from PyQt5.QtGui import QTextBlockUserData

from libsyntyche.cli import Command, AutocompletionPattern


class KalpanaObject:
    """
    An interface that all main objects should implement.

    Subclassing this class means the object will be able to register commands,
    settings, autocompletion patterns, and print to the terminal.
    """
    error_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    confirm_signal = pyqtSignal(str, QVariant, str)
    change_setting_signal = pyqtSignal(str, QVariant)
    kalpana_settings: List[str] = []
    kalpana_commands: List[Command] = []
    kalpana_autocompletion_patterns: List[AutocompletionPattern] = []

    def error(self, text: str) -> None:
        """Show an error in the terminal."""
        self.error_signal.emit(text)

    def log(self, text: str) -> None:
        """Show a regular message in the terminal."""
        self.log_signal.emit(text)

    def confirm(self, text: str, callback: Callable, arg: str = '') -> None:
        self.confirm_signal.emit(text, callback, arg)

    def change_setting(self, name: str, new_value: Any) -> None:
        self.change_setting_signal.emit(name, new_value)

    def setting_changed(self, name: str, new_value: Any) -> None:
        """
        Set the setting's corresponding variable to the new value.

        This is called any time the setting is changed. Since it does nothing
        as it is, it should be implemented by all subclasses.
        """
        pass

    def file_opened(self, filepath: str, is_new: bool) -> None:
        """
        This is called whenever a file is opened.

        is_new - The file does not exist yet.
        """
        pass

    def file_saved(self, filepath: str, new_name: bool) -> None:
        """
        This is called whenever a file is saved.

        new_name - The file was saved with a new name. (aka Save As)
        """
        pass


class LineFormatData(QTextBlockUserData):

    def __init__(self, text: Optional[str]) -> None:
        super().__init__()
        self.text = text


def autocomplete_file_path(name: str, text: str) -> List[str]:
    """A convenience autocompletion function for filepaths."""
    import os
    import os.path
    full_path = os.path.abspath(os.path.expanduser(text))
    if text.endswith(os.path.sep):
        dir_path, name_fragment = full_path, ''
    else:
        dir_path, name_fragment = os.path.split(full_path)
    raw_paths = (os.path.join(dir_path, x)
                 for x in os.listdir(dir_path)
                 if x.startswith(name_fragment))
    return sorted(p + ('/' if os.path.isdir(p) else '')
                  for p in raw_paths)
