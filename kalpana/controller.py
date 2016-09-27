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
from PyQt4.QtCore import Qt, QEvent, pyqtSignal

from kalpana.filehandler import FileHandler, FileError


class Controller:
    def __init__(self, mainwindow, textarea, terminal):
        self.mainwindow = mainwindow
        self.textarea = textarea
        self.terminal = terminal
        self.filehandler = FileHandler()
        self.set_hotkeys()
        self.connect_signals()

    def set_hotkeys(self):
        self.termkey = QtGui.QShortcut(QtGui.QKeySequence('Escape'),
                                       self.mainwindow, self.toggle_terminal)
        self.termkey = QtGui.QShortcut(QtGui.QKeySequence('F9'),
                                       self.mainwindow, self.test)

    def test(self):
        print('mw:', self.mainwindow.width())
        print('stack:', self.mainwindow.stack.width())
        print('textarea:', self.textarea.width())
        sp = self.textarea.sizePolicy()
        print('ta sizepolicy', sp.controlType(), sp.horizontalPolicy())

    def connect_signals(self):
        pairs = (
            (self.terminal.run_command, self.run_command),
        )
        for signal, slot in pairs:
            signal.connect(slot)

    def toggle_terminal(self):
        if self.terminal.input_field.hasFocus():
            if self.terminal.completer_popup.isVisible():
                self.terminal.completer_popup.hide()
            else:
                self.mainwindow.setFocus()
        else:
            self.terminal.input_field.setFocus()

    def load_file(self, filepath):
        try:
            data = self.filehandler.open_file(filepath)
        except FileError as e:
            self.terminal.error(e.args[0])
        else:
            self.textarea.setPlainText(data)

    def watch_terminal(self):
        class EventFilter(QtCore.QObject):
            def eventFilter(self_, obj, ev):
                if ev.type() == QEvent.KeyPress:
                    if ev.key() == Qt.Key_Backtab and ev.modifiers() == Qt.ShiftModifier:
                        return True
                    elif ev.key() == Qt.Key_Tab and ev.modifiers() == Qt.NoModifier:
                        return True
                return False
        self.term_event_filter = EventFilter()
        self.terminal.input_field.installEventFilter(self.term_event_filter)

    def run_command(self, cmd, arg):
        print('COMMAND:', cmd)
        print('ARG:', arg)
        # self.terminal.error('invalid command')
