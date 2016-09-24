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


from collections import defaultdict
import re

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QEvent, pyqtSignal


class Terminal(QtGui.QWidget):
    run_command = pyqtSignal(str)

    def __init__(self, parent: QtGui.QWidget) -> None:
        super().__init__(parent)
        # Create the objects
        self.input_field = QtGui.QLineEdit(self)
        self.output_field = QtGui.QLineEdit(self)
        self.output_field.setDisabled(True)
        # Set the layout
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.input_field)
        layout.addWidget(self.output_field)
        # Autocompletion test
        self.completer = Completer(parent, self.input_field)
        # ['arst', 'aoop', 'aruh'], self)
        # self.completer.setCompletionMode(QtGui.QCompleter.InlineCompletion)
        # self.input_field.setCompleter(self.completer)
        # Signals
        # self.input_field.returnPressed.connect(self.parse_command)

    def print_(self, msg: str) -> None:
        self.output_field.setText(msg)

    def error(self, msg: str) -> None:
        self.output_field.setText('Error: ' + msg)

    def prompt(self, msg: str) -> None:
        self.input_field.setText(msg)

    def parse_command(self) -> None:
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.setText('')
        self.run_command.emit(text)
        self.completer.widget.update()


class Completer():

    def __init__(self, parent, input_field):
        """
        {
            'a': {
                'abolish': 12,
                'django': 1,
                'arst': 4
            },
            'hj': {
                'hack jaw': 9,
                'thjack': 3
            }
        }
        """
        self.input_field = input_field
        self.suggestions = []
        # self.autocompleted_history = defaultdict
        self.run_history = []

        # Simple list of how many time a certain command has been run

        self.commands = [
            'word count',
            'go to line',
            'go to chapter',
            'toggle spellcheck',
            'add word',
            'check word',
            'new file',
            'save file',
            'open file',
            'list plugins',
            'set style'
        ]

        self.command_frequency = {cmd: 0 for cmd in self.commands}

        self.widget = CompletionList(parent, input_field)
        self.watch_terminal()

    def watch_terminal(self):
        class EventFilter(QtCore.QObject):
            tab_pressed = pyqtSignal(bool)

            def eventFilter(self_, obj, ev):
                if ev.type() == QEvent.KeyPress:
                    if ev.key() == Qt.Key_Backtab and ev.modifiers() == Qt.ShiftModifier:
                        self_.tab_pressed.emit(True)
                        return True
                    elif ev.key() == Qt.Key_Tab and ev.modifiers() == Qt.NoModifier:
                        self_.tab_pressed.emit(False)
                        return True
                    # elif ev.key() ==
                elif ev.type() == QEvent.Paint:
                    self.widget.update()
                return False

        self.term_event_filter = EventFilter()
        self.input_field.installEventFilter(self.term_event_filter)
        self.term_event_filter.tab_pressed.connect(self.tab_pressed)
        self.input_field.returnPressed.connect(self.return_pressed)
        self.input_field.textChanged.connect(self.text_edited)

    def text_edited(self, new_text):
        self.suggestions = []
        for command in self.commands:
            if re.search('.*'.join(map(re.escape, new_text)), command):
                self.suggestions.append(command)
        self.suggestions.sort(key=lambda cmd: (self.command_frequency[cmd], cmd))
        self.widget.set_suggestions(self.suggestions, new_text)

    def tab_pressed(self, backwards):
        if self.suggestions:
            self.input_field.setText(self.suggestions[-1])
        # text = self.input_field.text()
        # matches = []
        # for command in self.commands:
        #     if re.search('.*'.join(map(re.escape, text)), command):
        #         matches.append(command)
        # print('MATCHES')
        # print(*matches, sep='\n')
        # print('')

    def return_pressed(self):
        text = self.input_field.text()
        cmd = None
        for command in self.commands:
            if text.startswith(command):
                cmd = command
                break
        if cmd:
            self.command_frequency[cmd] += 1
            print('command:', cmd)
        else:
            print('invalid command')
        self.input_field.clear()
        self.widget.reset_suggestions()


class CompletionList(QtGui.QLabel):

    def __init__(self, parent, input_field):
        super().__init__(parent)
        self.mainwindow = parent
        self.input_field = input_field
        self.setFont(QtGui.QFont('monospace'))
        self.setWordWrap(False)
        self.setAutoFillBackground(True)
        self.setStyleSheet('CompletionList {border: 1px solid black; background-color:gray}')
        self.line_height = QtGui.QFontMetricsF(self.font()).height()
        self.hide()

        # print(parent.height())
        # self.move(0,-15)

    def update(self, *args):
        super().update(*args)
        pos = QtCore.QPoint(0, -self.sizeHint().height())
        global_pos = self.input_field.mapTo(self.mainwindow, pos)
        self.setGeometry(QtCore.QRect(global_pos, self.sizeHint()))

    # def paintEvent(self, ev):
    #     super().paintEvent(ev)
    #     text_align = QtGui.QTextOption(QtCore.Qt.AlignTop)
    #     painter = QtGui.QPainter(self)
    #     painter.setPen(QtGui.QColor(Qt.black))
    #     painter.setBrush(QtGui.QBrush(Qt.lightGray))
    #     painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
    #     for n, text in enumerate(self.suggestions):
    #         rect = QtCore.QRectF(0, n*self.line_height, self.width(), self.line_height)
    #         painter.drawText(rect, text, text_align)
    #     painter.end()



    def format_suggestions(self, suggestions, text_fragment):
        for command in suggestions:
            formatted_text = ''
            for char in text_fragment:
                pos = command.find(char)
                formatted_text += command[:pos] + '<b>' + char + '</b>'
                command = command[pos+1:]
            yield formatted_text + command

    def set_suggestions(self, suggestions, text_fragment):
        self.text_fragment = text_fragment
        if not suggestions:
            self.hide()
        else:
            self.setText('<br>'.join(self.format_suggestions(suggestions, text_fragment)))
            self.show()

    def reset_suggestions(self):
        self.clear()
        self.hide()
