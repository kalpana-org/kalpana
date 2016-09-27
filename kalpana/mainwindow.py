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

from PyQt4 import QtCore, QtGui


class MainWindow(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QtGui.QVBoxLayout(self)
        self.stack = QtGui.QStackedWidget(self)
        self.layout.addWidget(self.stack)
        self.terminal = None
        self.show()

    def set_terminal(self, terminal):
        assert self.terminal is None
        self.terminal = terminal
        self.layout.addWidget(terminal)

    def add_stack_widgets(self, widgets):
        for widget in widgets:
            wrapper = QtGui.QWidget(self)
            layout = QtGui.QHBoxLayout(wrapper)
            layout.addStretch()
            layout.addWidget(widget, stretch=1)
            layout.addStretch()
            self.stack.addWidget(wrapper)

    def setFocus(self):
        if self.stack.count() > 0:
            self.stack.currentWidget().layout().itemAt(1).widget().setFocus()
        else:
            super().setFocus()
