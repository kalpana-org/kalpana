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

"""
Classes and functions needed in multiple different modules.

This is to avoid potential circular imports.
"""
import enum
import logging
from contextlib import contextmanager
from typing import Any, Callable, Iterator, List, TypeVar, cast

from PyQt5.QtCore import QVariant, pyqtSignal

from libsyntyche.cli import AutocompletionPattern, Command
from libsyntyche.widgets import Signal2, Signal3, mk_signal1

T = TypeVar('T', bound=Callable[..., Any])


def command_callback(func: T) -> T:
    def wrapper(self: 'FailSafeBase', *args, **kwargs):  # type: ignore
        with self.try_it(f'command with callback '
                         f'{func.__name__!r} failed'):
            return func(self, *args, **kwargs)
    return cast(T, wrapper)


class FailSafeBase:
    def error(self, text: str) -> None:
        raise NotImplementedError()

    @contextmanager
    def try_it(self, msg: str) -> Iterator[None]:
        try:
            yield
        except Exception as e:
            full_msg = f'[UNHANDLED EXCEPTION] {msg}, due to exception: {e!r}'
            logging.getLogger(self.__class__.__module__).exception(full_msg)
            self.error(full_msg)


class KalpanaObject(FailSafeBase):
    """
    An interface that all main objects should implement.

    Subclassing this class means the object will be able to register commands,
    settings, autocompletion patterns, and print to the terminal.
    """
    error_signal = mk_signal1(str)
    log_signal = mk_signal1(str)
    confirm_signal = cast(Signal3[str, Any, str], pyqtSignal(str, QVariant, str))
    change_setting_signal = cast(Signal2[str, Any], pyqtSignal(str, QVariant))
    kalpana_settings: List[str] = []
    kalpana_commands: List[Command] = []
    kalpana_autocompletion_patterns: List[AutocompletionPattern] = []

    def error(self, text: str) -> None:
        """Show an error in the terminal."""
        self.error_signal.emit(text)

    def log(self, text: str) -> None:
        """Show a regular message in the terminal."""
        self.log_signal.emit(text)

    def confirm(self, text: str, callback: Callable[..., Any],
                arg: str = '') -> None:
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


@enum.unique
class TextBlockState(enum.IntFlag):
    # Lines related to the chapter heading
    CHAPTER = 0x1
    DESC = 0x2
    TAGS = 0x4
    TIME = 0x8
    CHAPTERMETA = 0x2 | 0x4 | 0x8
    # Misc special lines
    SECTION = 0x100
    META = 0x1000
    TODO = 0x2000
    LINEFORMATS = 0x1 | 0x2 | 0x4 | 0x8 | 0x100 | 0x1000 | 0x2000
    # Formatting
    BOLD = 0x100000
    ITALIC = 0x200000
    UNDERLINE = 0x400000
    FORMATTING = 0x700000


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
