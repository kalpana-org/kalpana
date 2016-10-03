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
from PyQt4.QtCore import Qt, QEvent, QRect, pyqtSignal, pyqtProperty
from PyQt4.QtGui import QColor


class Terminal(QtGui.QFrame):
    error_triggered = pyqtSignal()
    run_command = pyqtSignal(str, str)

    def __init__(self, parent: QtGui.QWidget) -> None:
        super().__init__(parent)
        # Create the objects
        self.input_field = QtGui.QLineEdit(self)
        self.input_field.setObjectName('terminal_input')
        self.output_field = QtGui.QLineEdit(self)
        self.output_field.setObjectName('terminal_output')
        self.output_field.setDisabled(True)
        # Set the layout
        layout = QtGui.QVBoxLayout(self)
        layout.setMargin(0)
        layout.setSpacing(0)
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
        self.error_triggered.emit()

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
            'set-style': '',
            'set-textarea-max-width': ''
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
        self.popup_list.set_suggestions(suggestions, partial_cmd)
        if suggestions != self.suggestions:
            self.suggestions = suggestions
            self.selection = len(self.suggestions) - 1
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


class CompletionList(QtGui.QScrollArea):

    def css_property(name):
        def set_color(self, color):
            self.set_status_color(name, color)
        return pyqtProperty(QColor, fset=set_color)

    history_color = css_property('history')
    exact_color = css_property('exact')
    fuzzy_color = css_property('fuzzy')
    rest_color = css_property('rest')
    selection_color = css_property('selection')

    def __init__(self, parent, input_field):
        super().__init__(parent)
        # Variables
        self.input_field = input_field
        self.mainwindow = parent
        self.suggestions = []
        self.selection = 0
        self.line_height = 0
        self.visible_lines = self.max_visible_lines = 6
        # CSS properties
        self.status_colors = {
                SuggestionType.rest: QColor(),
                SuggestionType.fuzzy: QColor(),
                SuggestionType.exact: QColor(),
                SuggestionType.history: QColor(),
        }
        self._selection_color = QColor()
        # Misc init
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.NoFocus)
        self.canvas = CompletionListCanvas(self, lambda: self.line_height,
                                           lambda: self.suggestions,
                                           self.status_colors.get,
                                           lambda: self._selection_color)
        self.setWidget(self.canvas)
        self.hide()

    def set_status_color(self, status_name, color):
        if status_name == 'selection':
            self._selection_color = color
        else:
            self.status_colors[SuggestionType[status_name]] = color

    def update(self, *args):
        """Match its position with the terminal's position."""
        super().update(*args)
        font_metrics = QtGui.QFontMetricsF(self.font())
        self.line_height = font_metrics.height() + 4
        # Canvas size
        left, top, right, bottom = self.canvas.getContentsMargins()
        if not self.suggestions:
            width = 1
        else:
            width = max(font_metrics.width(re.sub(r'</?b>', '', text))
                        for text, _ in self.suggestions) + 20
            height = len(self.suggestions) * self.line_height
            self.canvas.resize(width+left+right, height+top+bottom)
        # ScrollArea geometry
        left, top, right, bottom = self.getContentsMargins()
        total_width = self.canvas.width() + left + right  # + self.verticalScrollBar().width()
        if self.verticalScrollBar().isVisible():
            total_width += self.verticalScrollBar().width()
        total_height = self.line_height * self.visible_lines + top + bottom
        size = QtCore.QSize(total_width, total_height)
        pos = QtCore.QPoint(0, -total_height)
        global_pos = self.input_field.mapTo(self.mainwindow, pos)
        self.setGeometry(QRect(global_pos, size))
        # Scroll correctly
        top = self.canvas.contentsRect().y() + self.line_height * self.selection
        bottom = top + self.line_height
        self.ensureVisible(0, top, xMargin=0, yMargin=0)
        self.ensureVisible(0, bottom, xMargin=0, yMargin=0)

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
        self.offset = len(self.suggestions)
        self.canvas.suggestions = suggestions
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
        self.canvas.selection = selection
        self.update()

    def reset_suggestions(self):
        # self.clear()
        self.hide()


class CompletionListCanvas(QtGui.QFrame):

    def __init__(self, parent, get_line_height, get_suggestions, get_color, get_selection_color):
        super().__init__(parent)
        self.get_line_height = get_line_height
        self.get_suggestions = get_suggestions
        self.get_color = get_color
        self.get_selection_color = get_selection_color

    def paintEvent(self, ev):
        super().paintEvent(ev)
        painter = QtGui.QPainter(self)
        no_wrap = QtGui.QTextOption()
        no_wrap.setWrapMode(QtGui.QTextOption.NoWrap)
        item_rect = self.contentsRect()
        item_rect.setHeight(self.get_line_height())
        for n, (text, status) in enumerate(self.get_suggestions()):
            painter.fillRect(item_rect, self.get_color(status))
            painter.fillRect(item_rect.adjusted(5, 0, 0, 0),
                             self.get_color(status).darker(300))
            if n == self.selection:
                painter.fillRect(item_rect, self.get_selection_color())
            st = QtGui.QStaticText(text)
            st.setTextOption(no_wrap)
            painter.drawStaticText(item_rect.x()+8, item_rect.y()+2, st)
            item_rect.translate(0, self.get_line_height())
        painter.end()
