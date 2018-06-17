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

from typing import Iterable

from PyQt5 import QtWidgets
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
        self.add_command(cli.Command(
                'toggle-log',
                ('Show or hide the log of all input '
                 'and output in the terminal.'),
                self.log_history.toggle_visibility,
                args=cli.ArgumentRules.NONE, short_name='t')
        )

    def register_commands(self, commands: Iterable[cli.Command]) -> None:
        for command in commands:
            self.add_command(command)

    def register_autocompletion_patterns(
                self, patterns: Iterable[cli.AutocompletionPattern]) -> None:
        for pattern in patterns:
            self.add_autocompletion_pattern(pattern)
