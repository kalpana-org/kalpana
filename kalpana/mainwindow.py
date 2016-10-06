#!/usr/bin/env python3
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

from PyQt5 import QtCore, QtWidgets


class MainWindow(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.stack = QtWidgets.QStackedWidget(self)
        layout.addWidget(self.stack)
        self.terminal = None  # type: QtWidgets.QFrame
        self.show()

    def set_terminal(self, terminal: QtWidgets.QFrame) -> None:
        self.terminal = terminal
        self.layout().addWidget(terminal)

    def add_stack_widgets(self, widgets: Iterable[QtWidgets.QFrame]) -> None:
        for widget in widgets:
            wrapper = QtWidgets.QFrame(self)
            layout = QtWidgets.QHBoxLayout(wrapper)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addStretch()
            layout.addWidget(widget, stretch=1)
            layout.addStretch()
            self.stack.addWidget(wrapper)

    def setFocus(self) -> None:
        if self.stack.count() > 0:
            self.stack.currentWidget().layout().itemAt(1).widget().setFocus()
        else:
            super().setFocus()

    def shake_screen(self) -> None:
        a = QtCore.QPropertyAnimation(self.stack, b'pos')
        a.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        a.setDuration(500)
        for step, offset in enumerate([0, 1, -2, 2, -1, 0]):
            a.setKeyValueAt(step*0.2, self.stack.pos() + QtCore.QPoint(offset*40, 0))
        a.start(QtCore.QPropertyAnimation.DeleteWhenStopped)
        self.shakeanim = a
