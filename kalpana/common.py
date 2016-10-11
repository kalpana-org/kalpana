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

from enum import IntEnum
from typing import Any, Callable, List, Optional, Tuple

from PyQt5.QtCore import pyqtSignal

SuggestionListAlias = List[Tuple[str, Optional[IntEnum]]]
SuggestionCallback = Callable[[str, str], SuggestionListAlias]


class KalpanaObject:
    """
    An interface that all main objects should implement.

    Subclassing this class means the object will be able to register commands,
    settings, autocompletion patterns, and print to the terminal.
    """
    error_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    kalpana_settings = []  # type: List[str]
    kalpana_commands = []  # type: List[Command]
    kalpana_autocompletion_patterns = []  # type: List[AutocompletionPattern]

    def error(self, text: str) -> None:
        """Show an error in the terminal."""
        self.error_signal.emit(text)

    def log(self, text: str) -> None:
        """Show a regular message in the terminal."""
        self.log_signal.emit(text)

    def setting_changed(self, name: str, new_value: Any) -> None:
        """
        Set the setting's corresponding variable to the new value.

        This is called any time the setting is changed. Since it does nothing
        as it is, it should be implemented by all subclasses.
        """
        pass


class Command:
    """A command run in the terminal."""

    def __init__(self, name: str, help_text: str, callback: Callable,
                 accept_args: bool = True) -> None:
        self.name = name
        self.help_text = help_text
        self.callback = callback
        self.accept_args = accept_args


class AutocompletionPattern:
    """A pattern to be autocompleted in the terminal's input field."""

    def __init__(self, name: str = '', prefix: str = '',
                 start: str = r'^', end: str = r'$',
                 illegal_chars: str = '',
                 remember_raw_text: bool = False,
                 is_file_path: bool = False,
                 get_suggestion_list: SuggestionCallback = None) -> None:
        """
        Create an autocompletion pattern.

        Note that the prefix will be removed from the string the start and end
        regexes are matched against.

        Args:
            name: The pattern's identifier. Should be unique.
            prefix: A regex that matches the start of the input string but
                which will not be considered for autocompletion.
            start: A regex that matches the start of the autocompleted text.
            end: A regex that matches the end of the autocompleted text.
            illegal_chars: A string with all character that the autocompleted
                text may not include.
            remember_raw_text: True if the original string should be saved when
                autocompleting. Useful when you want to remember what a certain
                string has been most often autocompleted to (eg. when
                autocompleting commands).
            is_file_path: Use the default file path function instead of using
                the get_suggestion_list function.
            get_suggestion_list: A function taking (name, text) as arguments,
                where name is the name of the pattern and text is the string
                that is being autocompleted.
        """
        if is_file_path:
            get_suggestion_list = autocomplete_file_path
        if get_suggestion_list is None:
            raise ValueError('AC pattern {} must have a suggestion list function!'.format(name))
        self.name = name
        self.prefix = prefix
        self.start = start
        self.end = end
        self.illegal_chars = illegal_chars
        self.remember_raw_text = remember_raw_text
        self.get_suggestion_list = get_suggestion_list


def autocomplete_file_path(name: str, text: str) -> SuggestionListAlias:
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
    return sorted((p + ('/' if os.path.isdir(p) else ''), None)
                  for p in raw_paths)
