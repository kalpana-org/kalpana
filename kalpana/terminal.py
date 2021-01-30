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

from typing import Iterable

from libsyntyche import cli, terminal
from PyQt5 import QtWidgets

from .common import KalpanaObject
from .settings import CommandHistory


class Terminal(terminal.Terminal, KalpanaObject):
    def __init__(self, parent: QtWidgets.QFrame, command_history: CommandHistory) -> None:
        super().__init__(parent, log_command='t')
        self.output_field.hide()

    def register_commands(self, commands: Iterable[cli.Command]) -> None:
        for command in commands:
            self.add_command(command)

    def register_autocompletion_patterns(
                self, patterns: Iterable[cli.AutocompletionPattern]) -> None:
        for pattern in patterns:
            self.add_autocompletion_pattern(pattern)
