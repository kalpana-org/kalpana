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
    run_command = pyqtSignal(str, str)

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
        self.completer = Completer(parent, self.run_command, self.input_field)
        self.completer_popup = self.completer.popup_list
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
        self.completer.popup_list.update()


class SuggestionType(IntEnum):
    rest = 0
    fuzzy = 1
    exact = 2
    history = 10

    def color(self):
        return {
            'history': QColor('#3f5d6a'),
            'exact': QColor('#61009d'),
            'fuzzy': QColor('#1d6629'),
            'rest': QColor('#6a6a6a')
        }[self.name]


class Completer():

    def __init__(self, parent, run_command, input_field):
        self.input_field = input_field
        self.run_command = run_command
        self.suggestions = []
        self.last_autocompletion = None
        self.history = []
        # self.autocompleted_history = defaultdict
        # self.run_history = {
        #     'c': {
        #         'word-count': 10,
        #         'go-to-chapter': 2
        #     },
        #     'g': {
        #         'go-to-line': 2,
        #         'go-to-chapter': 4,
        #         'set-style': 9
        #     },
        #     ':': {
        #         'go-to-line': 13,
        #         'go-to-chapter': 1
        #     }
        # }
        self.run_history = defaultdict(lambda: defaultdict(int))

        # Simple list of how many time a certain command has been run

        self.commands = {
            'word-count-total': '',
            'word-count-chapter': '',
            'word-count-selection': '',
            'go-to-line': '',
            'go-to-chapter': '',
            'toggle-spellcheck': '',
            'add-word': 'Add a word to the spellcheck database.',
            'check-word': '',
            'new-file': '',
            'save-file': '',
            'open-file': '',
            'list-plugins': '',
            'set-style': ''
        }

        self.command_frequency = {cmd: 0 for cmd in self.commands}
        self.command_frequency['word-count'] = 9
        self.command_frequency['toggle-spellcheck'] = 14

        self.popup_list = CompletionList(parent, input_field)
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
                    self.popup_list.update()
                return False

        self.term_event_filter = EventFilter()
        self.input_field.installEventFilter(self.term_event_filter)
        self.term_event_filter.tab_pressed.connect(self.tab_pressed)
        self.input_field.returnPressed.connect(self.return_pressed)
        self.input_field.textChanged.connect(self.text_edited)
        self.term_event_filter.up_down_pressed.connect(self.up_down_pressed)

    def text_edited(self, new_text):
        if not new_text.strip():
            if self.popup_list.isVisible():
                self.popup_list.hide()
            self.suggestions = []
            return
        partial_cmd = new_text.split()[0] if new_text else ''
        suggestions = []
        raw_top = self.run_history.get(partial_cmd, {})
        for cmd in self.commands:
            if cmd in raw_top:
                suggestions.append((cmd, raw_top[cmd], SuggestionType.exact))
            elif partial_cmd and re.search('.*'.join(map(re.escape, partial_cmd)), cmd):
                suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.fuzzy))
            else:
                suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.rest))
        suggestions = [(cmd, type_) for cmd, num, type_
                       in sorted(suggestions, key=itemgetter(2, 1, 0))]
        if suggestions != self.suggestions:
            self.suggestions = suggestions
            self.selection = len(self.suggestions) - 1
            self.popup_list.set_suggestions(self.suggestions, partial_cmd)
            self.popup_list.set_selection(self.selection)

    def up_down_pressed(self, down):
        if not self.popup_list.isVisible():
            if down or not self.history:
                return
            self.suggestions = [(x, SuggestionType.history) for x in self.history]
            self.selection = len(self.suggestions) - 1
            self.popup_list.set_suggestions(self.suggestions, '')
            self.popup_list.set_selection(self.selection)
            return
        if down:
            self.selection = min(self.selection+1, len(self.suggestions)-1)
        else:
            self.selection = max(self.selection-1, 0)
        self.popup_list.set_selection(self.selection)

    def tab_pressed(self, backwards):
        if not self.popup_list.isVisible():
            if self.suggestions:
                self.popup_list.show()
            return
        new_text = self.suggestions[self.selection][0] + ' '
        old_text = self.input_field.text().split(None, 1)
        if old_text:
            self.last_autocompletion = old_text[0]
        if len(old_text) == 2:
            new_text += old_text[1]
        self.input_field.setText(new_text)

    def return_pressed(self):
        text = self.input_field.text()
        if not text.strip():
            return
        chunks = text.split(None, 1)
        raw_cmd = chunks[0]
        arg = chunks[1] if len(chunks) == 2 else ''
        if raw_cmd not in self.commands:
            self.last_autocompletion = raw_cmd
            cmd = self.suggestions[self.selection][0]
        else:
            cmd = raw_cmd
        self.command_frequency[cmd] += 1
        if self.last_autocompletion != cmd:
            self.run_history[self.last_autocompletion][cmd] += 1
        self.history.append(cmd + ((' ' + arg) if arg else ''))
        self.input_field.clear()
        self.popup_list.reset_suggestions()
        self.run_command.emit(cmd, arg)


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
        self.max_visible_lines = 6
        self.visible_lines = self.max_visible_lines
        self.border_width = 1
        self.hide()

    def update(self, *args):
        """Match its position with the terminal's position."""
        super().update(*args)
        pos = QtCore.QPoint(0, -self.height())
        global_pos = self.input_field.mapTo(self.mainwindow, pos)
        self.setGeometry(QRect(global_pos, self.size()))

    def calculate_scrollbar(self, scrollbar_width: int) -> QRect:
        """Return a QRect where the scrollbar should be drawn."""
        total_height = self.height() - self.border_width*2
        total_lines = len(self.suggestions)
        x = self.width() - scrollbar_width - self.border_width
        if total_lines <= self.visible_lines:
            scrollbar_height = total_height
            y = self.border_width
        else:
            scrollbar_height = max(self.visible_lines / total_lines, 0.2) * total_height
            pos_percent = (self.offset-self.visible_lines) / (total_lines-self.visible_lines)
            y = int((total_height-scrollbar_height) * pos_percent) + self.border_width
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

    def format_suggestions(self, suggestions, text_fragment: str):
        """
        Highlight relevant letters in the suggestions.

        All characters matching a character in the text fragment should
        get a bold html tag wrapped around it. Note that this only affects
        fuzzy matches.
        """
        for command, status in suggestions:
            if status != SuggestionType.fuzzy:
                yield (command, status)
                continue
            formatted_text = ''
            for char in text_fragment:
                pos = command.find(char)
                formatted_text += command[:pos] + '<b>' + char + '</b>'
                command = command[pos+1:]
            yield (formatted_text + command, status)

    def set_suggestions(self, suggestions, text_fragment):
        """Set the list of suggestions."""
        self.text_fragment = text_fragment
        self.suggestions = list(self.format_suggestions(suggestions, text_fragment))
        self.visible_lines = min(len(suggestions), self.max_visible_lines)
        width = max(len(cmd) for cmd, status in suggestions) * self.char_width + 20
        height = self.visible_lines * self.line_height + self.border_width*2
        self.setFixedSize(width, height)
        self.offset = len(self.suggestions)
        self.show()

    def set_selection(self, selection):
        """Update the selection position and make sure it's visible."""
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
