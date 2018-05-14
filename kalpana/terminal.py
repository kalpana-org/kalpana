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

from datetime import datetime
from enum import IntEnum
from typing import Iterable

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from libsyntyche import cli, terminal

from kalpana.common import KalpanaObject
from kalpana.settings import CommandHistory


class FocusWrapper(QtWidgets.QLineEdit):
    def setText(self, text: str) -> None:
        super().setText(text)
        self.parentWidget().show()


class Terminal(terminal.Terminal, KalpanaObject):
    def __init__(self, parent: QtWidgets.QFrame,
                 command_history: CommandHistory) -> None:
        super().__init__(parent, short_mode=True)

    def register_commands(self, commands: Iterable[cli.Command]) -> None:
        for command in commands:
            self.add_command(command)

    def register_autocompletion_patterns(
                self, patterns: Iterable[cli.AutocompletionPattern]) -> None:
        for pattern in patterns:
            self.add_autocompletion_pattern(pattern)


class LogHistory(QtWidgets.QListWidget):

    class LogType(IntEnum):
        normal = 0
        error = 1
        input = 2

    def __init__(self, parent: Terminal) -> None:
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        parent.register_command(cli.Command(
                name='toggle-terminal-log',
                help_text='Show or hide the log of all input and output in the terminal.',
                callback=self.toggle_visibility,
                accept_args=False))
        self.hide()

    def toggle_visibility(self) -> None:
        self.setVisible(not self.isVisible())

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime('%H:%M:%S')

    def add(self, message: str) -> None:
        self._add_to_log(LogHistory.LogType.normal, message)

    def add_error(self, message: str) -> None:
        self._add_to_log(LogHistory.LogType.error, message)

    def add_input(self, text: str) -> None:
        self._add_to_log(LogHistory.LogType.input, text)

    def _add_to_log(self, type_: int, message: str) -> None:
        timestamp = self._timestamp()
        if type_ == LogHistory.LogType.error:
            message = '< [ERROR] ' + message
        elif type_ == LogHistory.LogType.input:
            message = '> ' + message
        else:
            message = '< ' + message
        self.addItem('{} - {}'.format(timestamp, message))
