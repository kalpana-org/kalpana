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

from datetime import datetime
from typing import Iterable, cast

from PyQt5 import QtCore, QtWidgets

from libsyntyche import cli, terminal
from libsyntyche.widgets import Signal0

from .common import KalpanaObject
from .settings import CommandHistory


class MessageTrayItem(QtWidgets.QLabel):
    def __init__(self, text: str, name: str,
                 parent: QtWidgets.QWidget) -> None:
        super().__init__(text, parent)
        self.parent = parent
        self.setObjectName(name)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Preferred)
        # Fade out animation
        effect = QtWidgets.QGraphicsOpacityEffect(self)
        effect.setOpacity(1)
        self.setGraphicsEffect(effect)
        a1 = QtCore.QPropertyAnimation(effect, b'opacity')
        a1.setEasingCurve(QtCore.QEasingCurve.InOutQuint)
        a1.setDuration(500)
        a1.setStartValue(1)
        a1.setEndValue(0)
        cast(Signal0, a1.finished).connect(self.deleteLater)
        self.fade_animation = a1
        # Move animation
        a2 = QtCore.QPropertyAnimation(self, b'pos')
        a2.setEasingCurve(QtCore.QEasingCurve.InQuint)
        a2.setDuration(300)
        self.move_animation = a2

    def kill(self) -> None:
        self.fade_animation.start()
        self.move_animation.setStartValue(self.pos())
        self.move_animation.setEndValue(self.pos() - QtCore.QPoint(0, 50))
        self.move_animation.start()


class MessageTray(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        # TODO: put this in settings
        self.seconds_alive = 5
        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch()
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def add_message(self, timestamp: datetime, msgtype: terminal.MessageType,
                    text: str) -> None:
        if msgtype == terminal.MessageType.INPUT:
            return
        classes = {
            terminal.MessageType.ERROR: 'terminal_error',
            terminal.MessageType.PRINT: 'terminal_print',
        }
        # if msgtype == terminal.MessageType.ERROR:
            # text = f'Error: {text}'
        lbl = MessageTrayItem(text, classes[msgtype], self)
        self.layout().addWidget(lbl)
        QtCore.QTimer.singleShot(1000 * self.seconds_alive, lbl.kill)


class FocusWrapper(QtWidgets.QLineEdit):
    def setText(self, text: str) -> None:
        super().setText(text)
        self.parentWidget().show()


class Terminal(terminal.Terminal, KalpanaObject):
    def __init__(self, parent: QtWidgets.QFrame,
                 command_history: CommandHistory) -> None:
        super().__init__(parent, short_mode=True, log_command='t')
        self.output_field.hide()

    def register_commands(self, commands: Iterable[cli.Command]) -> None:
        for command in commands:
            self.add_command(command)

    def register_autocompletion_patterns(
                self, patterns: Iterable[cli.AutocompletionPattern]) -> None:
        for pattern in patterns:
            self.add_autocompletion_pattern(pattern)
