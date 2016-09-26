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
from enum import IntEnum
from operator import itemgetter
import re

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QEvent, QRect, pyqtSignal
from PyQt4.QtGui import QColor


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


class SuggestionType(IntEnum):
    exact = 2
    fuzzy = 1
    rest = 0

    def color(self):
        return {
            'exact': QColor('#61009d'),
            'fuzzy': QColor('#1d6629'),
            'rest': QColor('#6a6a6a')
        }[self.name]


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
        self.run_history = {
            'c': {
                'word count': 10,
                'go to chapter': 2
            },
            'g': {
                'go to line': 2,
                'go to chapter': 4,
                'set style': 9
            },
            ':': {
                'go to line': 13,
                'go to chapter': 1
            }
        }

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
        self.command_frequency['word count'] = 9
        self.command_frequency['toggle spellcheck'] = 14

        self.widget = CompletionList(parent, input_field)
        self.selection = None
        self.watch_terminal()

    def watch_terminal(self):
        class EventFilter(QtCore.QObject):
            tab_pressed = pyqtSignal(bool)
            up_down_pressed = pyqtSignal(bool)

            def eventFilter(self_, obj, ev):
                if ev.type() == QEvent.KeyPress:
                    if ev.key() == Qt.Key_Backtab and ev.modifiers() == Qt.ShiftModifier:
                        self_.tab_pressed.emit(True)
                        return True
                    elif ev.key() == Qt.Key_Tab and ev.modifiers() == Qt.NoModifier:
                        self_.tab_pressed.emit(False)
                        return True
                    elif ev.key() == Qt.Key_Up:
                        self_.up_down_pressed.emit(False)
                        return True
                    elif ev.key() == Qt.Key_Down:
                        self_.up_down_pressed.emit(True)
                        return True
                elif ev.type() == QEvent.Paint:
                    self.widget.update()
                return False

        self.term_event_filter = EventFilter()
        self.input_field.installEventFilter(self.term_event_filter)
        self.term_event_filter.tab_pressed.connect(self.tab_pressed)
        self.input_field.returnPressed.connect(self.return_pressed)
        self.input_field.textChanged.connect(self.text_edited)
        self.term_event_filter.up_down_pressed.connect(self.up_down_pressed)

    def text_edited(self, new_text):
        self.suggestions = []
        raw_top = self.run_history.get(new_text, {})
        for cmd in self.commands:
            if cmd in raw_top:
                self.suggestions.append((cmd, raw_top[cmd], SuggestionType.exact))
            elif new_text and re.search('.*'.join(map(re.escape, new_text)), cmd):
                self.suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.fuzzy))
            else:
                self.suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.rest))
        self.suggestions = [(cmd, type_) for cmd, num, type_
                            in sorted(self.suggestions, key=itemgetter(2, 1, 0))]
        self.selection = len(self.suggestions) - 1
        self.widget.set_suggestions(self.suggestions, new_text)
        self.widget.set_selection(self.selection)

    def up_down_pressed(self, down):
        if down:
            self.selection = min(self.selection+1, len(self.suggestions)-1)
        else:
            self.selection = max(self.selection-1, 0)
        self.widget.set_selection(self.selection)

    def tab_pressed(self, backwards):
        if self.suggestions:
            self.input_field.setText(self.suggestions[-1][0])
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


class CompletionList(QtGui.QWidget):

    def __init__(self, parent, input_field):
        super().__init__(parent)
        self.mainwindow = parent
        self.input_field = input_field
        self.suggestions = []
        self.selection = None
        self.offset = None
        self.setFont(QtGui.QFont('monospace'))
        font_metrics = QtGui.QFontMetricsF(self.font())
        self.char_width = font_metrics.widthChar('x')
        self.line_height = font_metrics.height() + 4
        self.visible_lines = 6
        self.border_width = 1
        self.hide()

    def update(self, *args):
        super().update(*args)
        pos = QtCore.QPoint(0, -self.height())
        global_pos = self.input_field.mapTo(self.mainwindow, pos)
        self.setGeometry(QRect(global_pos, self.size()))

    def calculate_scrollbar(self, scrollbar_width: int) -> QRect:
        """Return a QRect where the scrollbar should be drawn."""
        scrollbar_height = int(self.height()/4)
        percent = (self.offset-self.visible_lines)/(len(self.suggestions)-self.visible_lines)
        x = self.width() - scrollbar_width - self.border_width
        y = int((self.height()-scrollbar_height-self.border_width*2) * percent) + self.border_width
        return QRect(x, y, scrollbar_width, scrollbar_height)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        color = {
            'border': QColor('#111'),
            'scrollbar': QColor('#555'),
            'bg': QColor('#181818'),
            'text': QColor('#ccc'),
            'sel': QColor(255, 255, 255, 48)
        }
        painter = QtGui.QPainter(self)
        painter.setPen(color['border'])
        painter.setBrush(color['bg'])
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(color['text'])
        scrollbar_width = 5
        no_wrap = QtGui.QTextOption()
        no_wrap.setWrapMode(QtGui.QTextOption.NoWrap)
        numbered_suggestions = list(enumerate(self.suggestions))
        end = self.offset
        start = max(end - self.visible_lines, 0)
        item_rect = QRect(self.border_width, self.border_width,
                          self.width()-self.border_width*2-scrollbar_width,
                          self.line_height)
        # QRect(1, 1, self.width()-2-scrollbar_width, self.line_height)
        for n, (text, status) in numbered_suggestions[start:end]:
            painter.fillRect(item_rect, status.color())
            painter.fillRect(item_rect.adjusted(5, 0, 0, 0), status.color().darker(300))
            if n == self.selection:
                painter.fillRect(item_rect, color['sel'])
            st = QtGui.QStaticText(text)
            st.setTextOption(no_wrap)
            painter.drawStaticText(item_rect.x()+8, item_rect.y()+2, st)
            item_rect.translate(0, self.line_height)
        painter.fillRect(self.calculate_scrollbar(scrollbar_width),
                         color['scrollbar'])
        painter.end()

    def format_suggestions(self, suggestions, text_fragment):
        for command, status in suggestions:
            if status != SuggestionType.fuzzy:
                yield (command, status)
                continue
            formatted_text = ''
            for char in text_fragment:
                pos = command.find(char)
                fixed_char = '&nbsp;' if char == ' ' else char
                formatted_text += command[:pos] + '<b>' + fixed_char + '</b>'
                command = command[pos+1:]
            yield (formatted_text + command, status)

    def set_suggestions(self, suggestions, text_fragment):
        self.text_fragment = text_fragment
        self.suggestions = list(self.format_suggestions(suggestions, text_fragment))
        width = max(len(cmd) for cmd, status in suggestions) * self.char_width + 20
        height = self.visible_lines * self.line_height + self.border_width*2
        self.setFixedSize(width, height)
        self.offset = len(self.suggestions)
        self.show()

    def set_selection(self, selection):
        self.selection = selection
        # selection too far up
        if self.selection < self.offset - self.visible_lines:
            self.offset = self.selection + self.visible_lines
        # selection too far down
        elif self.selection >= self.offset:
            self.offset = self.selection + 1
        self.update()

    def reset_suggestions(self):
        # self.clear()
        self.hide()
