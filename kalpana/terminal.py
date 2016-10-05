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

from kalpana.autocompletion import SuggestionList

class Terminal(QtGui.QFrame):

    class InputField(QtGui.QLineEdit):
        @property
        def text(self):
            return super().text()

        @text.setter
        def text(self, text):
            self.setText(text)

        @property
        def cursor_position(self):
            return self.cursorPosition()

        @cursor_position.setter
        def cursor_position(self, pos):
            self.setCursorPosition(pos)

    error_triggered = pyqtSignal()
    run_command = pyqtSignal(str, str)

    def __init__(self, parent: QtGui.QWidget) -> None:
        super().__init__(parent)
        # Create the objects
        self.input_field = self.InputField(self)
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
        # Misc
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
        self.run_history = defaultdict(lambda: defaultdict(int))
        self.command_frequency = {cmd: 0 for cmd in self.commands}
        self.completer_popup = CompletionListWidget(parent, self.input_field)
        self.suggestion_list = SuggestionList(
                self.completer_popup,
                self.input_field
        )
        self.suggestion_list.add_autocompletion_pattern(
                name='command',
                end=r'( |$)',
                illegal_chars=' \t',
                get_suggestion_list=self.command_suggestions
        )
        self.suggestion_list.add_autocompletion_pattern(
                name='open-file',
                prefix=r'open-file\s+',
                get_suggestion_list=autocomplete_file_path
        )
        self.watch_terminal()

    def print_(self, msg: str) -> None:
        self.output_field.setText(msg)

    def error(self, msg: str) -> None:
        self.output_field.setText('Error: ' + msg)
        self.error_triggered.emit()

    def prompt(self, msg: str) -> None:
        self.input_field.setText(msg)

    def command_suggestions(self, name, text):
        suggestions = []
        raw_top = self.run_history.get(text, {})
        for cmd in self.commands:
            if cmd in raw_top:
                suggestions.append((cmd, raw_top[cmd], SuggestionType.exact))
            elif text and re.search('.*'.join(map(re.escape, text)), cmd):
                suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.fuzzy))
            else:
                suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.rest))
        return [(cmd, type_) for cmd, num, type_
                in sorted(suggestions, key=itemgetter(2, 1, 0))]

    def watch_terminal(self):
        class EventFilter(QtCore.QObject):
            backtab_pressed = pyqtSignal()
            tab_pressed = pyqtSignal()
            up_pressed = pyqtSignal()
            down_pressed = pyqtSignal()

            def eventFilter(self_, obj, ev):
                catch_keys = [
                    (Qt.Key_Backtab, Qt.ShiftModifier, self_.backtab_pressed),
                    (Qt.Key_Tab, Qt.NoModifier, self_.tab_pressed),
                    (Qt.Key_Up, Qt.NoModifier, self_.up_pressed),
                    (Qt.Key_Down, Qt.NoModifier, self_.down_pressed),
                ]
                if ev.type() == QEvent.KeyPress:
                    for key, mod, signal in catch_keys:
                        if ev.key() == key and ev.modifiers() == mod:
                            signal.emit()
                            return True
                elif ev.type() == QEvent.Paint:
                    self.completer_popup.update()
                return False

        self.term_event_filter = EventFilter()
        self.input_field.installEventFilter(self.term_event_filter)
        self.term_event_filter.tab_pressed.connect(self.suggestion_list.tab_pressed)
        self.term_event_filter.up_pressed.connect(self.suggestion_list.up_pressed)
        self.term_event_filter.down_pressed.connect(self.suggestion_list.down_pressed)
        self.input_field.returnPressed.connect(self.suggestion_list.return_pressed)
        self.input_field.textChanged.connect(self.suggestion_list.update)
        self.input_field.cursorPositionChanged.connect(self.suggestion_list.update)


class SuggestionType(IntEnum):
    rest = 0
    fuzzy = 1
    exact = 2
    history = 10


def autocomplete_file_path(name, text):
    import os
    import os.path
    full_path = os.path.abspath(os.path.expanduser(text))
    if text.endswith(os.path.sep):
        dir_path, name_fragment = full_path, ''
    else:
        dir_path, name_fragment = os.path.split(full_path)
    raw_paths = (os.path.join(dir_path, x)
                 for x in os.listdir(dir_path)
                 if x.startswith(name_fragment))
    return sorted((p + ('/' if os.path.isdir(p) else ''), SuggestionType.rest)
                  for p in raw_paths)


class CompletionListWidget(QtGui.QScrollArea):

    class CompletionListCanvas(QtGui.QFrame):

        def __init__(self, parent, get_line_height, get_suggestions, get_color, get_selection_color):
            super().__init__(parent)
            self.get_line_height = get_line_height
            self.get_suggestions = get_suggestions
            self.get_color = get_color
            self.get_selection_color = get_selection_color
            self.selection = 0

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


    def css_property(name):
        def set_color(self, color):
            self.set_status_color(name, color)
        return pyqtProperty(QColor, fset=set_color)

    history_color = css_property('history')
    exact_color = css_property('exact')
    fuzzy_color = css_property('fuzzy')
    rest_color = css_property('rest')
    selection_color = css_property('selection')

    def __init__(self, mainwindow, input_field):
        super().__init__(mainwindow)
        # Variables
        self.input_field = input_field
        self.mainwindow = mainwindow
        self.suggestions = []
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
        self.canvas = self.CompletionListCanvas(self,
                                                lambda: self.line_height,
                                                lambda: self.suggestions,
                                                self.status_colors.get,
                                                lambda: self._selection_color)
        self.setWidget(self.canvas)
        self.hide()

    @property
    def visible(self):
        return self.isVisible()

    @visible.setter
    def visible(self, value):
        self.setVisible(value)

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
        top = self.canvas.contentsRect().y() + self.line_height * self.canvas.selection
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

    def set_suggestions(self, suggestions, selection, text_fragment):
        """Set the list of suggestions."""
        self.text_fragment = text_fragment
        self.suggestions = list(self.format_suggestions(suggestions, text_fragment))
        self.visible_lines = min(len(suggestions), self.max_visible_lines)
        self.offset = len(self.suggestions)
        self.canvas.suggestions = suggestions
        self.canvas.selection = selection
        self.show()

    def set_selection(self, selection):
        """Update the selection position."""
        self.canvas.selection = selection
        self.update()

    def reset_suggestions(self):
        # self.clear()
        self.hide()
