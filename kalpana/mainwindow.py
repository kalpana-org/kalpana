# Copyright nycz 2011-2020

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

import json
from pathlib import Path
from typing import Dict, List, Optional, Union, cast

from PyQt5 import QtCore, QtGui, QtWidgets

from libsyntyche.cli import ArgumentRules, Command
from libsyntyche.widgets import mk_signal0

from .chapteroverview import ChapterOverview
from .common import KalpanaObject
from .terminal import MessageTray, Terminal
from .textarea import TextArea

InnerStackWidget = Union[ChapterOverview, TextArea]


class Stack(QtWidgets.QStackedWidget):
    resized = mk_signal0()

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        super().resizeEvent(ev)
        self.resized.emit()


class MainWindow(QtWidgets.QFrame, KalpanaObject):
    def __init__(self) -> None:
        super().__init__()
        self.kalpana_commands = [
                Command('quit', '', self.close, args=ArgumentRules.NONE)
        ]
        self.title = 'New file'
        self.sapfo_title = ''
        self.sapfo_filename: Optional[Path] = None
        self.modified = False
        self.force_close_flag = False
        self.update_window_title()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.stack = Stack(self)
        layout.addWidget(self.stack)
        self.stack_wrappers: Dict[int, QtWidgets.QFrame] = {}
        self.terminal: Optional[Terminal] = None
        self.message_tray = MessageTray(self)
        self.stack.resized.connect(self.adjust_tray)
        self.show()

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        super().resizeEvent(ev)
        self.adjust_tray()

    def adjust_tray(self) -> None:
        rect = self.stack.geometry()
        self.message_tray.setGeometry(rect)

    @property
    def active_stack_widget(self) -> InnerStackWidget:
        """Return the stack's actual active widget (not the wrapper)."""
        active_item = self.stack.currentWidget().layout().itemAt(1)
        # They can only be one of these so lets make everyone realize that thx
        assert active_item is not None
        return cast(InnerStackWidget, active_item.widget())

    @active_stack_widget.setter
    def active_stack_widget(self, widget: InnerStackWidget) -> None:
        """Set the stack's active widget to the wrapper of the argument."""
        self.stack.setCurrentWidget(self.stack_wrappers[id(widget)])

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.modified and not self.force_close_flag:
            self.confirm('There are unsaved changes. Discard them?',
                         self.force_close)
            event.ignore()
        else:
            super().closeEvent(event)

    def force_close(self, arg: str) -> None:
        self.force_close_flag = True
        self.close()

    def check_for_sapfo_title(self) -> None:
        p = Path(self.title)
        metadatafile = p.with_name(f'.{p.name}.metadata')
        if metadatafile.is_file():
            with self.try_it('failed checking for sapfo title'):
                if metadatafile != self.sapfo_filename:
                    self.sapfo_filename = metadatafile
                    with open(metadatafile) as f:
                        metadata = json.load(f)
                    self.sapfo_title = metadata['title']
            self.title = self.sapfo_title
        else:
            self.sapfo_filename = None

    def update_window_title(self) -> None:
        title = f'*{self.title}*' if self.modified else self.title
        self.setWindowTitle(title)

    def modification_changed(self, modified: bool) -> None:
        self.modified = modified
        self.update_window_title()

    def file_opened(self, filepath: str, is_new: bool) -> None:
        self.title = filepath or 'New file'
        if filepath:
            self.check_for_sapfo_title()
        self.update_window_title()

    def file_saved(self, filepath: str, new_name: bool) -> None:
        self.title = filepath
        self.check_for_sapfo_title()
        self.update_window_title()

    def set_terminal(self, terminal: Terminal) -> None:
        self.terminal = terminal
        self.layout().addWidget(terminal)

    def add_stack_widgets(self, widgets: List[InnerStackWidget]) -> None:
        """Add the widgets to the stack."""
        for widget in widgets:
            wrapper = QtWidgets.QFrame(self)
            layout = QtWidgets.QHBoxLayout(wrapper)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addStretch()
            layout.addWidget(widget, stretch=1)
            layout.addStretch()
            self.stack_wrappers[id(widget)] = wrapper
            self.stack.addWidget(wrapper)

    def setFocus(self) -> None:  # type: ignore
        if self.stack.count() > 0:
            self.active_stack_widget.setFocus()
        else:
            super().setFocus()

    def shake_screen(self) -> None:
        a = QtCore.QPropertyAnimation(self.stack, b'pos')
        a.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        a.setDuration(500)
        for step, offset in enumerate([0, 1, -2, 2, -1, 0]):
            a.setKeyValueAt(step * 0.2,
                            self.stack.pos() + QtCore.QPoint(offset*40, 0))
        a.start(QtCore.QPropertyAnimation.DeleteWhenStopped)
        self.shakeanim = a
