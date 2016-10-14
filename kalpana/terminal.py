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

from datetime import datetime
from enum import IntEnum
from operator import itemgetter
import re

from typing import cast, Any, Callable, Dict, Iterable, Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal

from kalpana.autocompletion import SuggestionList, ListWidget, InputWidget
from kalpana.common import AutocompletionPattern, Command, KalpanaObject, SuggestionListAlias
from kalpana.settings import CommandHistory


class SuggestionType(IntEnum):
    rest = 0
    fuzzy = 1
    exact = 2
    history = 10


class FocusWrapper(QtWidgets.QLineEdit):
    def setText(self, text: str) -> None:
        super().setText(text)
        self.parentWidget().show()


class Terminal(QtWidgets.QFrame, KalpanaObject):

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

        def setFocus(self) -> None:
            self.parentWidget().show()
            super().setFocus()

    error_triggered = pyqtSignal()

    def __init__(self, parent: QtWidgets.QFrame,
                 command_history: CommandHistory) -> None:
        super().__init__(parent)
        self.commands = {}  # type: Dict[str, Command]
        self.autocompletion_history = command_history.autocompletion_history
        self.command_frequency = command_history.command_frequency
        self.kalpana_settings = ['visible-autocompletion-items']
        self.waiting_for_confirmation = False
        self.confirmation_callback = None  # type: Optional[Tuple[Callable, str]]
        # Create the objects
        self.input_field = Terminal.InputField(self)
        self.input_field.setObjectName('terminal_input')
        self.output_field = QtWidgets.QLineEdit(self)
        self.output_field.setObjectName('terminal_output')
        self.output_field.setDisabled(True)
        self.completer_popup = CompletionListWidget(parent, self.input_field)
        self.suggestion_list = SuggestionList(self.completer_popup,
                                              self.input_field,
                                              self.parse_command)
        self.log_history = LogHistory(self)
        self.register_autocompletion_pattern(AutocompletionPattern(
                name='command',
                end=r'( |$)',
                illegal_chars=' \t',
                get_suggestion_list=self.command_suggestions
        ))
        # Set the layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.log_history)
        layout.addWidget(self.input_field)
        layout.addWidget(self.output_field)
        self.watch_terminal()

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        self.handle_confirmation(False)
        self.output_field.setText('')
        super().hideEvent(event)

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'visible-autocompletion-items':
            self.completer_popup.max_visible_lines = int(new_value)

    def register_command(self, command: Command) -> None:
        self.commands[command.name] = command
        self.suggestion_list.command_help_texts[command.name] = command.help_text

    def register_commands(self, command_list: Iterable[Command]) -> None:
        for command in command_list:
            self.register_command(command)

    def register_autocompletion_pattern(self, pattern: AutocompletionPattern) -> None:
        self.suggestion_list.add_autocompletion_pattern(pattern)

    def register_autocompletion_patterns(self, pattern_list: Iterable[AutocompletionPattern]) -> None:
        for pattern in pattern_list:
            self.register_autocompletion_pattern(pattern)

    def print_(self, msg: str, show: bool = True) -> None:
        self.log_history.add(msg)
        self.output_field.setText(msg)
        if show:
            self.show()

    def error(self, msg: str, show: bool = True) -> None:
        self.log_history.add_error(msg)
        self.output_field.setText('Error: ' + msg)
        if show:
            self.show()
        self.error_triggered.emit()

    def confirm_command(self, text: str, callback: Callable, arg: str) -> None:
        self.print_('{} Type y to confirm.'.format(text))
        self.input_field.setText('')
        self.input_field.setFocus()
        self.completer_popup.visible = False
        self.waiting_for_confirmation = True
        self.suggestion_list.confirmation_mode = True
        self.confirmation_callback = (callback, arg)

    def exec_command(self, command_string: str) -> None:
        """
        Parse and run or prompt a command string from the config.

        If command_string starts with a space, set the input field's text to
        command_string (minus the leading space), otherwise run the command.
        """
        if self.waiting_for_confirmation:
            return
        if command_string.startswith(' '):
            self.input_field.text = command_string[1:]
            self.input_field.setFocus()
        else:
            self.parse_command(command_string, '')

    def parse_command(self, text: str, unautocompleted_cmd: Optional[str]) -> None:
        self.output_field.setText('')
        if self.waiting_for_confirmation:
            self.handle_confirmation(text == 'y')
            return
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
            if unautocompleted_cmd is not None and cmd_name != unautocompleted_cmd:
                self.autocompletion_history[unautocompleted_cmd][cmd_name] += 1
            self.command_frequency[cmd_name] += 1
            self.suggestion_list.history.append((text, SuggestionType.history))
            self.log_history.add_input(text)
            if command.accept_args:
                command.callback(arg)
            else:
                command.callback()

    def handle_confirmation(self, confirmed: bool) -> None:
        if self.confirmation_callback is None:
            return
        self.waiting_for_confirmation = False
        if confirmed:
            self.print_('Confirmed', show=False)
            callback, arg = self.confirmation_callback
            callback(arg)
        else:
            self.print_('Aborted', show=False)
        self.confirmation_callback = None
        self.suggestion_list.confirmation_mode = False


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

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        diffs = {Qt.Key_PageUp: -1, Qt.Key_PageDown: 1}
        if event.key() in diffs:
            diff = diffs[cast(Qt.Key, event.key())]
            if self.completer_popup.isVisible():
                jump = min(self.completer_popup.count(),
                           self.completer_popup.max_visible_lines) - 1
                self.suggestion_list.selection += diff * jump
                event.accept()
            elif self.log_history.isVisible():
                sb = self.log_history.verticalScrollBar()
                sb.setValue(sb.value() + sb.pageStep() * diff)
                event.accept()
        super().keyPressEvent(event)

    def watch_terminal(self) -> None:
        class EventFilter(QtCore.QObject):
            backtab_pressed = pyqtSignal()
            tab_pressed = pyqtSignal()
            up_pressed = pyqtSignal()
            down_pressed = pyqtSignal()
            page_up_pressed = pyqtSignal()
            page_down_pressed = pyqtSignal()
            def eventFilter(self_, obj: object, event: QtCore.QEvent) -> bool:
                catch_keys = [
                    (Qt.Key_Backtab, Qt.ShiftModifier, self_.backtab_pressed),
                    (Qt.Key_Tab, Qt.NoModifier, self_.tab_pressed),
                    (Qt.Key_Up, Qt.NoModifier, self_.up_pressed),
                    (Qt.Key_Down, Qt.NoModifier, self_.down_pressed),
                ]
                if event.type() == QtCore.QEvent.KeyPress:
                    key_event = cast(QtGui.QKeyEvent, event)
                    for key, mod, signal in catch_keys:
                        if key_event.key() == key and key_event.modifiers() == mod:
                            signal.emit()
                            return True
                elif event.type() == QtCore.QEvent.Paint:
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


class LogHistory(QtWidgets.QListWidget):

    class LogType(IntEnum):
        normal = 0
        error = 1
        input = 2

    def __init__(self, parent: Terminal) -> None:
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        parent.register_command(Command(
                name='toggle-terminal-log',
                help_text='Show or hide the log of all input and output in the terminal.',
                callback=self.toggle_visibility,
                accept_args=False))
        self.hide()

    def toggle_visibility(self) -> None:
        self.setVisible(not self.isVisible())

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime('%H:%M:%S')

    def add(self, message: str) -> None:
        self._add_to_log(LogHistory.LogType.normal, message)

    def add_error(self, message: str) -> None:
        self._add_to_log(LogHistory.LogType.error, message)

    def add_input(self, text: str) -> None:
        self._add_to_log(LogHistory.LogType.input, text)

    def _add_to_log(self, type_: int, message: str) -> None:
        timestamp = self._timestamp()
        if type_ == LogHistory.LogType.error:
            message = '< [ERROR] ' + message
        elif type_ == LogHistory.LogType.input:
            message = '> ' + message
        else:
            message = '< ' + message
        self.addItem('{} - {}'.format(timestamp, message))


class CompletionListWidget(QtWidgets.QListWidget, ListWidget):

    def __init__(self, mainwindow: QtWidgets.QFrame,
                 input_field: QtWidgets.QLineEdit) -> None:
        super().__init__(mainwindow)
        def list_item(name: str) -> QtWidgets.QLabel:
            widget = QtWidgets.QLabel()
            widget.setObjectName(name)
            widget.hide()
            return widget
        # Variables
        self.input_field = input_field
        self.mainwindow = mainwindow
        self.max_visible_lines = 6
        # These are here to make styling easier
        names = ['history', 'exact', 'fuzzy', 'rest', 'selected']
        self._list_item_bases = {name: list_item(name) for name in names}
        class CompletionListHelpText(QtWidgets.QLabel):
            pass
        self.help_text = CompletionListHelpText(mainwindow)
        self.help_text.setWordWrap(True)
        self.last_selection = 0
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._install_geometry_filters()

    def sizeHint(self) -> QtCore.QSize:
        left, top, right, bottom = self.getContentsMargins()
        visible_lines = min(self.count(), self.max_visible_lines)
        scrollbar_width = (self.verticalScrollBar().width()
                           if self.count() > self.max_visible_lines else 0)
        width = self.sizeHintForColumn(0) + scrollbar_width
        height = sum(self.sizeHintForRow(n) for n in range(visible_lines))
        return QtCore.QSize(left + width + right, top + height + bottom)

    @property
    def visible(self) -> bool:
        return self.isVisible()

    @visible.setter
    def visible(self, visible: bool) -> None:
        self.setVisible(visible)
        self.help_text.setVisible(visible)

    @property
    def selection(self) -> int:
        return self.currentRow()

    @selection.setter
    def selection(self, selection: int) -> None:
        # Reset the last selected item's color
        last_item = self.item(self.last_selection)
        if last_item is not None:
            last_item.setBackground(self.item_background(last_item.data(Qt.UserRole)))
            last_item.setForeground(self.item_foreground(last_item.data(Qt.UserRole)))
        self.last_selection = selection
        # Move the actual selection
        self.setCurrentRow(selection)
        # Set the color of the selected item to something nice
        current_item = self.item(selection)
        if current_item is not None:
            selection_bg = self.item_background('selected').color()
            bg = self.item_background(current_item.data(Qt.UserRole)).color()
            selection_fg = self.item_foreground('selected').color()
            fg = self.item_foreground(current_item.data(Qt.UserRole)).color()
            new_bg = self.blend_color(bg, selection_bg)
            new_fg = self.blend_color(fg, selection_fg)
            current_item.setBackground(QtGui.QBrush(new_bg))
            current_item.setForeground(QtGui.QBrush(new_fg))

    def blend_color(self, color1: QtGui.QColor, color2: QtGui.QColor) -> QtGui.QColor:
        """Return a mix of color1 and color2, based on color2's alpha."""
        a = color2.alphaF()
        r = color1.redF()*(1-a) + color2.redF()*a
        g = color1.greenF()*(1-a) + color2.greenF()*a
        b = color1.blueF()*(1-a) + color2.blueF()*a
        return QtGui.QColor(int(r*255), int(g*255), int(b*255))

    def item_background(self, name: str) -> QtGui.QBrush:
        return self._list_item_bases[name].palette().window()

    def item_foreground(self, name: str) -> QtGui.QBrush:
        return self._list_item_bases[name].palette().windowText()

    def set_suggestions(self, suggestions: SuggestionListAlias,
                        selection: int, text_fragment: str) -> None:
        self.clear()
        for n, (name, type_) in enumerate(suggestions):
            type_name = 'rest' if type_ is None else type_.name
            self.addItem(name)
            item = self.item(n)
            item.setData(Qt.UserRole, type_name)
            item.setBackground(self.item_background(type_name))
            item.setForeground(self.item_foreground(type_name))
        self.selection = self.count() - 1
        self.adjustSize()
        self.show()
        self.help_text.setFixedWidth(self.width())
        self.help_text.adjustSize()
        self.update_position()

    def set_help_text(self, help_text: str) -> None:
        if help_text:
            self.help_text.setText(help_text)
            self.help_text.show()
        else:
            self.help_text.hide()
        self.help_text.adjustSize()
        self.update_position()

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

    def update_position(self) -> None:
        """Match its position with the terminal's position."""
        pos = QtCore.QPoint(0, -self.height())
        self.move(self.input_field.mapTo(self.mainwindow, pos))
        pos2 = pos + QtCore.QPoint(0, -self.help_text.height())
        self.help_text.move(self.input_field.mapTo(self.mainwindow, pos2))
