# Copyright nycz 2011-2013

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

import re

from PyQt4 import QtCore, QtGui

from linewidget import LineTextWidget


class TextArea(LineTextWidget):
    print_ = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setTabStopWidth(30)
        self.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

        self.search_buffer = None
        self.replace_buffer = None

    def search_and_replace(self, arg):
        search_rx = re.compile(r'([^/]|\\/)+$')
        replace_rx = re.compile(r"""
            (?P<search>([^/]|\\/)*?[^\\])
            /
            (?P<replace>(([^/]|\\/)*[^\\])?)
            /
            (?P<flags>[ai]*)
            $
        """, re.VERBOSE)
        replace_append_rx = re.compile(r"""
            /
            (?P<replace>(([^/]|\\/)*[^\\])?)
            /
            (?P<flags>[ai]*)
            $
        """, re.VERBOSE)

        if not arg:
            self.search_next()

        elif arg == '/':
            self.replace_next()

        elif search_rx.match(arg):
            self.search_buffer = search_rx.match(arg).group(0)
            self.replace_buffer = None
            self.search_next()

        elif replace_append_rx.match(arg):
            if self.search_buffer is None:
                self.error.emit('No previous searches')
                return
            match = replace_append_rx.match(arg)
            self.replace_buffer = match.group('replace')
            if 'a' in match.group('flags'):
                self.replace_all()
            else:
                self.replace_next()

        elif replace_rx.match(arg):
            match = replace_rx.match(arg)
            self.search_buffer = match.group('search')
            self.replace_buffer = match.group('replace')
            if 'a' in match.group('flags'):
                self.replace_all()
            else:
                self.replace_next()

        else:
            self.error.emit('Malformed search/replace expression')


    def search_next(self):
        if self.search_buffer is None:
            self.error.emit("No previous searches")
            return
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer)
        if not found:
            if not self.textCursor().atStart():
                self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer)
                if not found:
                    self.setTextCursor(temp_cursor)
                    self.error.emit('Text not found')


    def replace_next(self):
        if self.replace_buffer is None:
            self.error.emit("Nothing to replace with")
            return

        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer)
        if not found:
            if not self.textCursor().atStart():
                self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer)
                if not found:
                    self.setTextCursor(temp_cursor)
        if found:
            t = self.textCursor()
            t.insertText(self.replace_buffer)
            l = len(self.replace_buffer)
            t.setPosition(t.position() - l)
            t.setPosition(t.position() + l, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(t)
            self.print_.emit('Replaced on line {}, pos {}'
                             ''.format(t.blockNumber(), t.positionInBlock()))
        else:
            self.error.emit('Text not found')


    def replace_all(self):
        if self.replace_buffer is None:
            self.error.emit("No previous replaces")
            return

        temp_cursor = self.textCursor()
        times = 0
        while True:
            found = self.find(self.search_buffer)
            if found:
                self.textCursor().insertText(self.replace_buffer)
                times += 1
            else:
                if self.textCursor().atStart():
                    break
                else:
                    self.moveCursor(QtGui.QTextCursor.Start)
                    continue
        if times:
            self.print_.emit('{0} instance{1} replaced'.format(times,
                                                            's'*(times>0)))
        else:
            self.setTextCursor(temp_cursor)
            self.error.emit('Text not found')


    def goto_line(self, line_str):
        if not line_str.strip().isdigit():
            self.error.emit('Invalid line number')
            return
        line_num = min(int(line_str.strip()), self.document().blockCount())
        block = self.document().findBlockByNumber(line_num + 1)
        new_cursor = QtGui.QTextCursor(block)
        self.setTextCursor(new_cursor)
        self.centerCursor()
