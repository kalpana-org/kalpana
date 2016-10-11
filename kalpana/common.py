"""
Classes and functions needed in multiple different modules.

This is to avoid potential circular imports.
"""

from enum import IntEnum
from typing import Any, Callable, List, Optional, Tuple

from PyQt5.QtCore import pyqtSignal

from kalpana.autocompletion import AutocompletionPattern


SuggestionListAlias = List[Tuple[str, Optional[IntEnum]]]

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
