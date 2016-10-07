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
from typing import Callable, DefaultDict, Dict, Iterable, List, Tuple, Union

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QEvent, QRect, pyqtSignal, pyqtProperty
from PyQt5.QtGui import QColor

from kalpana.autocompletion import SuggestionList

SuggestionListAlias = List[Tuple[str, int]]
SuggestionCallback = Callable[[str, str], SuggestionListAlias]
AutocompletionPattern = Dict[str, Union[str, bool, SuggestionCallback]]


class SuggestionType(IntEnum):
    rest = 0
    fuzzy = 1
    exact = 2
    history = 10


class Command:
    def __init__(self, name: str, help_text: str, callback: Callable,
                 accept_args: bool = True) -> None:
        self.name = name
        self.help_text = help_text
        self.callback = callback
        self.accept_args = accept_args


class Terminal(QtWidgets.QFrame):

    class InputField(QtWidgets.QLineEdit):
        @property
        def text(self) -> str:
            return super().text()

        @text.setter
        def text(self, text: str) -> None:
            self.setText(text)

        @property
        def cursor_position(self) -> int:
            return self.cursorPosition()

        @cursor_position.setter
        def cursor_position(self, pos: int) -> None:
            self.setCursorPosition(pos)

    error_triggered = pyqtSignal()

    def __init__(self, parent: QtWidgets.QFrame) -> None:
        super().__init__(parent)
        # Create the objects
        self.input_field = Terminal.InputField(self)
        self.input_field.setObjectName('terminal_input')
        self.output_field = QtWidgets.QLineEdit(self)
        self.output_field.setObjectName('terminal_output')
        self.output_field.setDisabled(True)
        # Set the layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.input_field)
        layout.addWidget(self.output_field)
        # Misc
        self.commands = {}  # type: Dict[str, Command]
        self.autocompletion_history = defaultdict(lambda: defaultdict(int))  # type: DefaultDict[str, DefaultDict[str, int]]
        self.command_frequency = defaultdict(int)  # type: DefaultDict[str, int]
        self.completer_popup = CompletionListWidget(parent, self.input_field)
        self.suggestion_list = SuggestionList(
                self.completer_popup,
                self.input_field,
                self.parse_command
        )
        self.suggestion_list.add_autocompletion_pattern(
                name='command',
                end=r'( |$)',
                illegal_chars=' \t',
                get_suggestion_list=self.command_suggestions
        )
        # self.suggestion_list.add_autocompletion_pattern(
        #         name='open-file',
        #         prefix=r'open-file\s+',
        #         get_suggestion_list=autocomplete_file_path
        # )
        self.watch_terminal()

    def register_command(self, command: Command) -> None:
        self.commands[command.name] = command

    def register_commands(self, command_list: Iterable[Command]) -> None:
        for command in command_list:
            self.register_command(command)

    def print_(self, msg: str) -> None:
        self.output_field.setText(msg)

    def error(self, msg: str) -> None:
        self.output_field.setText('Error: ' + msg)
        self.error_triggered.emit()

    def prompt(self, msg: str) -> None:
        self.input_field.setText(msg)

    def exec_command(self, command_string: str) -> None:
        """
        Parse and run or prompt a command string from the config.

        If command_string starts with a space, set the input field's text to
        command_string (minus the leading space), otherwise run the command.
        """
        if command_string.startswith(' '):
            self.input_field.text = command_string[1:]
            self.input_field.setFocus()
        else:
            self.parse_command(command_string, '')

    def parse_command(self, text: str, unautocompleted_cmd: str) -> None:
        chunks = text.split(None, 1)
        cmd_name = chunks[0]
        arg = chunks[1] if len(chunks) == 2 else ''
        if cmd_name not in self.commands:
            self.error('Invalid command: {}'.format(cmd_name))
        else:
            command = self.commands[cmd_name]
            if arg and not command.accept_args:
                self.error('This command does not take any arguments!')
                return
            if unautocompleted_cmd and cmd_name != unautocompleted_cmd:
                self.autocompletion_history[unautocompleted_cmd][cmd_name] += 1
            self.command_frequency[cmd_name] += 1
            self.suggestion_list.history.append((text, SuggestionType.history))
            if command.accept_args:
                command.callback(arg)
            else:
                command.callback()

    def command_suggestions(self, name: str, text: str) -> SuggestionListAlias:
        suggestions = []
        raw_top = self.autocompletion_history.get(text, {})  # type: ignore
        for cmd in self.commands:
            if cmd in raw_top:
                suggestions.append((cmd, raw_top[cmd], SuggestionType.exact))
            elif text and re.search('.*'.join(map(re.escape, text)), cmd):
                suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.fuzzy))
            else:
                suggestions.append((cmd, self.command_frequency[cmd], SuggestionType.rest))
        return [(cmd, type_) for cmd, num, type_
                in sorted(suggestions, key=itemgetter(*[2, 1, 0]))]

    def watch_terminal(self) -> None:
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


def autocomplete_file_path(name: str, text: str) -> List[Tuple[str, int]]:
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


class CompletionListWidget(QtWidgets.QScrollArea):

    class CompletionListCanvas(QtWidgets.QFrame):

        def __init__(self, parent: 'CompletionListWidget') -> None:
            super().__init__(parent)
            self.parent = parent

        def paintEvent(self, event: QtGui.QPaintEvent) -> None:
            super().paintEvent(event)
            visible_rect = event.rect()
            painter = QtGui.QPainter(self)
            top_visible_item = visible_rect.y() // self.parent.line_height
            no_wrap = QtGui.QTextOption()
            no_wrap.setWrapMode(QtGui.QTextOption.NoWrap)
            item_rect = self.contentsRect()
            item_rect.translate(0, top_visible_item*self.parent.line_height)
            item_rect.setHeight(self.parent.line_height)
            items = enumerate(self.parent.suggestions[top_visible_item:], top_visible_item)
            for n, (text, status) in items:
                painter.fillRect(item_rect, self.parent.status_colors[status])
                painter.fillRect(item_rect.adjusted(5, 0, 0, 0),
                                 self.parent.status_colors[status].darker(300))
                if n == self.parent.selection:
                    painter.fillRect(item_rect, self.parent._selection_color)
                st = QtGui.QStaticText(text)
                st.setTextOption(no_wrap)
                painter.drawStaticText(item_rect.x()+8, item_rect.y()+2, st)
                item_rect.translate(0, self.parent.line_height)
                if item_rect.y() > visible_rect.y()+visible_rect.height():
                    break
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

    def __init__(self, mainwindow: QtWidgets.QFrame,
                 input_field: QtWidgets.QLineEdit) -> None:
        super().__init__(mainwindow)
        # Variables
        self.input_field = input_field
        self.mainwindow = mainwindow
        self.suggestions = []  # type: SuggestionListAlias
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
        self.canvas = CompletionListWidget.CompletionListCanvas(self)
        self.setWidget(self.canvas)
        self._install_geometry_filters()
        self.hide()

    def set_status_color(self, status_name, color):
        if status_name == 'selection':
            self._selection_color = color
        else:
            self.status_colors[SuggestionType[status_name]] = color  # type: ignore

    def _install_geometry_filters(self) -> None:
        """Install event filters that keep the geometry up to date."""
        class MainWindowEventFilter(QtCore.QObject):
            def eventFilter(self_, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
                if event.type() == QtCore.QEvent.Resize:
                    self.update_position()
                    return True
                return False
        self.resize_filter = MainWindowEventFilter()
        self.mainwindow.installEventFilter(self.resize_filter)

        class ScrollBarEventFilter(QtCore.QObject):
            def eventFilter(self_, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
                if event.type() in (QtCore.QEvent.Show, QtCore.QEvent.Hide):
                    self.update_size()
                    return True
                return False
        self.scrollbar_filter = ScrollBarEventFilter()
        self.verticalScrollBar().installEventFilter(self.scrollbar_filter)

    @property
    def visible(self) -> bool:
        return self.isVisible()

    @visible.setter
    def visible(self, visible: bool) -> None:
        self.setVisible(visible)

    def update_position(self) -> None:
        """Match its position with the terminal's position."""
        pos = QtCore.QPoint(0, -self.height())
        global_pos = self.input_field.mapTo(self.mainwindow, pos)
        self.setGeometry(QRect(global_pos, self.size()))

    def update_size(self) -> None:
        """Update the size to match the number of suggestion items."""
        font_metrics = QtGui.QFontMetrics(self.font())
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
        total_width = self.canvas.width() + left + right
        if self.verticalScrollBar().isVisible():
            total_width += self.verticalScrollBar().width()
        total_height = self.line_height * self.visible_lines + top + bottom
        size = QtCore.QSize(total_width, total_height)
        self.resize(size)
        self.update_position()

    def ensure_selection_visible(self) -> None:
        top = self.canvas.contentsRect().y() + self.line_height * self.selection
        bottom = top + self.line_height
        self.ensureVisible(0, top, xMargin=0, yMargin=0)
        self.ensureVisible(0, bottom, xMargin=0, yMargin=0)

    def format_suggestions(self, suggestions: SuggestionListAlias,
                           text_fragment: str) -> Iterable[Tuple[str, int]]:
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

    def set_suggestions(self, suggestions: SuggestionListAlias,
                        selection: int, text_fragment: str) -> None:
        """Set the list of suggestions."""
        self.text_fragment = text_fragment
        self.suggestions = list(self.format_suggestions(suggestions, text_fragment))
        self.visible_lines = min(len(suggestions), self.max_visible_lines)
        self.selection = selection
        self.update_size()
        self.ensure_selection_visible()
        self.show()

    def set_selection(self, selection: int) -> None:
        """Update the selection position."""
        self.last_selection = self.selection
        self.selection = selection
        self.ensure_selection_visible()
        self.update()
