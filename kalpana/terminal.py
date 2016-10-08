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

from typing import Any, Callable, DefaultDict, Dict, Iterable, List, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty

from kalpana.autocompletion import SuggestionList, ListWidget, InputWidget, AutocompletionPattern
from kalpana.settings import Configurable

SuggestionListAlias = List[Tuple[str, int]]
SuggestionCallback = Callable[[str, str], SuggestionListAlias]


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


class Terminal(QtWidgets.QFrame, Configurable):

    class InputField(QtWidgets.QLineEdit, InputWidget):
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

    def __init__(self, parent: QtWidgets.QFrame, command_history) -> None:
        super().__init__(parent)
        # Settings
        self.registered_settings = ['visible-autocompletion-items']
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
        self.autocompletion_history = command_history.autocompletion_history
        self.command_frequency = command_history.command_frequency
        self.completer_popup = CompletionListWidget(parent, self.input_field)
        self.suggestion_list = SuggestionList(
                self.completer_popup,
                self.input_field,
                self.parse_command
        )
        self.register_autocompletion_pattern(AutocompletionPattern(
                name='command',
                end=r'( |$)',
                illegal_chars=' \t',
                get_suggestion_list=self.command_suggestions
        ))
        self.watch_terminal()

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'visible-autocompletion-items':
            self.completer_popup.max_visible_lines = int(new_value)
            self.completer_popup.scrollbar.setPageStep(int(new_value))

    def register_command(self, command: Command) -> None:
        self.commands[command.name] = command
        self.suggestion_list.command_help_texts[command.name] = command.help_text

    def register_commands(self, command_list: Iterable[Command]) -> None:
        for command in command_list:
            self.register_command(command)

    def register_autocompletion_pattern(self, pattern: AutocompletionPattern):
        self.suggestion_list.add_autocompletion_pattern(pattern)

    def register_autocompletion_patterns(self, pattern_list: Iterable[AutocompletionPattern]) -> None:
        for pattern in pattern_list:
            self.register_autocompletion_pattern(pattern)

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
                if ev.type() == QtCore.QEvent.KeyPress:
                    for key, mod, signal in catch_keys:
                        if ev.key() == key and ev.modifiers() == mod:
                            signal.emit()
                            return True
                elif ev.type() == QtCore.QEvent.Paint:
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


class CompletionListWidget(QtWidgets.QFrame, ListWidget):

    def __init__(self, mainwindow: QtWidgets.QFrame,
                 input_field: QtWidgets.QLineEdit) -> None:
        super().__init__(mainwindow)
        # Variables
        self.input_field = input_field
        self.mainwindow = mainwindow
        class CompletionListHelpText(QtWidgets.QLabel):
            pass
        self.help_text = CompletionListHelpText(self)
        self.help_text.setWordWrap(True)
        self.suggestions = []  # type: SuggestionListAlias
        self._selection = 0
        self.line_height = 0
        self.line_spacing = 0
        self.visible_lines = self.max_visible_lines = 6
        # CSS properties
        class CompletionListItem(QtWidgets.QFrame):
            def __init__(self, name: str = '') -> None:
                super().__init__()
                self.setObjectName(name)
        self._base_item = CompletionListItem()
        self._selected_item = CompletionListItem('selected')
        self._status_items = {}  # type: Dict[int, CompletionListItem]
        ST = SuggestionType
        for type_ in [ST.rest, ST.fuzzy, ST.exact, ST.history]:
            self._status_items[type_] = CompletionListItem(type_.name)  # type: ignore
        # scrollbar
        self.scrollbar = QtWidgets.QScrollBar(QtCore.Qt.Vertical, self)
        self.scrollbar.setPageStep(self.max_visible_lines)
        self.scrollbar.setDisabled(True)
        self._install_geometry_filters()
        self.hide()

    @pyqtProperty(str)  # type: ignore
    def item_spacing(self) -> str:  # type: ignore
        return str(self.line_spacing)

    @item_spacing.setter  # type: ignore
    def item_spacing(self, new_value: str) -> None:
        self.line_spacing = int(new_value.rstrip('px'))

    @property
    def visible(self) -> bool:
        return self.isVisible()

    @visible.setter
    def visible(self, visible: bool) -> None:
        if visible:
            self.ensure_selection_visible()
        self.setVisible(visible)
        if visible and not self.help_text.text():
            self.help_text.hide()

    @property
    def selection(self) -> int:
        return self._selection

    @selection.setter
    def selection(self, selection: int) -> None:
        self._selection = selection
        self.ensure_selection_visible()
        self.update()

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

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        diff = 1 if event.angleDelta().y() < 0 else -1
        self.scrollbar.setValue(self.scrollbar.value() + diff)
        self.update()

    def ensure_selection_visible(self) -> None:
        offset = self.scrollbar.value()
        if offset > self.selection:
            offset = self.selection
        elif offset <= self.selection - self.visible_lines:
            offset = self.selection - self.visible_lines + 1
        self.scrollbar.setValue(offset)

    def set_help_text(self, help_text: str) -> None:
        if help_text:
            self.help_text.setText(help_text)
            self.help_text.show()
        else:
            self.help_text.hide()
        if self.suggestions:
            self.update_size()

    def set_suggestions(self, suggestions: SuggestionListAlias,
                        selection: int, text_fragment: str) -> None:
        """Set the list of suggestions."""
        if not suggestions:
            self.hide()
        else:
            if not self.visible:
                self.show()
            self.suggestions = [(suggestion, SuggestionType.rest if type_ is None else type_)
                                for suggestion, type_ in suggestions]
            self.visible_lines = min(len(suggestions), self.max_visible_lines)
            self.scrollbar.setMaximum(len(suggestions) - self.visible_lines)
            self.scrollbar.setVisible(self.scrollbar.maximum() > 0)
            self.selection = selection
            self.update_size()

    def update_position(self) -> None:
        """Match its position with the terminal's position."""
        pos = QtCore.QPoint(0, -self.height())
        self.move(self.input_field.mapTo(self.mainwindow, pos))

    def set_item_sizes(self, width: int, height: int) -> None:
        items = list(self._status_items.values()) + [self._base_item, self._selected_item]
        for type_ in items:
            type_.setFixedSize(width, height)

    def update_size(self) -> None:
        fm = self._base_item.fontMetrics()
        text_width = max(fm.width(re.sub(r'</?\w+?>', '', items[0]))
                         for items in self.suggestions)
        left, top, right, bottom = self._base_item.getContentsMargins()
        width = left + text_width + right
        self.line_height = top + fm.height() + bottom
        self.set_item_sizes(width, self.line_height)
        height = self.visible_lines * (self.line_height + self.line_spacing) - self.line_spacing
        # Scrollbar
        self.scrollbar.setFixedHeight(height)
        scrollbar_width = self.scrollbar.width() if self.scrollbar.isVisible() else 0
        # Help text
        self.help_text.setFixedWidth(width + scrollbar_width)
        help_text_height = self.help_text.height() if self.help_text.isVisible() else 0
        # Resize and move
        left, top, right, bottom = self.getContentsMargins()
        self.scrollbar.move(left + width, top + help_text_height)
        self.help_text.move(left, top)
        self.resize(left + width + scrollbar_width + right,
                    top + help_text_height + height + bottom)
        self.update_position()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        no_wrap = QtGui.QTextOption()
        no_wrap.setWrapMode(QtGui.QTextOption.NoWrap)
        item_rect = QtCore.QRect(self.contentsRect().topLeft(), self._base_item.size())
        if self.help_text.isVisible():
            item_rect.translate(0, self.help_text.height())
        offset = self.scrollbar.value()
        items = enumerate(self.suggestions[offset:offset+self.visible_lines], offset)
        for n, (text, status) in items:
            active_item = self._status_items[status]
            painter.drawPixmap(item_rect, active_item.grab())
            if n == self.selection:
                painter.drawPixmap(item_rect, self._selected_item.grab())
            st = QtGui.QStaticText(text)
            st.setTextOption(no_wrap)
            painter.setFont(active_item.font())
            painter.setPen(active_item.palette().windowText().color())
            inner_rect = item_rect - self._base_item.contentsMargins()
            painter.drawStaticText(inner_rect.topLeft(), st)
            if n == self.selection:
                painter.setPen(self._selected_item.palette().windowText().color())
                painter.drawStaticText(inner_rect.topLeft(), st)
            item_rect.translate(0, self.line_height + self.line_spacing)
        painter.end()
