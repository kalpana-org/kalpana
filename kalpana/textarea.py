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

import logging
import re
from typing import Any, Callable, Iterable, List, Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from libsyntyche.cli import ArgumentRules, Command

from .common import KalpanaObject, TextBlockState

logger = logging.getLogger(__name__)


class TextArea(QtWidgets.QPlainTextEdit, KalpanaObject):

    def __init__(self, parent: QtWidgets.QWidget,) -> None:
        super().__init__(parent)
        self.kalpana_settings = [
                'show-line-numbers',
                'max-textarea-width',
                'autohide-scrollbar',
                'start-at-pos',
        ]
        self.kalpana_commands = [
                Command('go-to-line', 'Go to line', self.go_to_line,
                        args=ArgumentRules.REQUIRED,
                        short_name=':',
                        category='movement',
                        arg_help=(('123', 'Center the view on line 123.'),)),
                Command('set-textarea-max-width',
                        'Set the max width of the page',
                        self.set_max_width,
                        args=ArgumentRules.REQUIRED,
                        arg_help=(('800', 'Set the max width to 800'),)),
                Command('toggle-line-numbers', '', self.toggle_line_numbers,
                        args=ArgumentRules.NONE),
                Command('insert-text', 'Insert text', self.insertPlainText,
                        short_name='_',
                        arg_help=(('_foo', 'Insert the text "foo" in the '
                                   'document as if you had typed it. (Mostly '
                                   'intended for keybindings.'),)),
                Command('search-and-replace',
                        'Search or replace', self.search_and_replace,
                        short_name='/',
                        strip_input=False,
                        args=ArgumentRules.REQUIRED,
                        arg_help=(('foo', 'Search for "foo".'),
                                  ('foo/b', 'Search backwards for "foo". '
                                   '(Can be combined with the other flags '
                                   'in any order.)'),
                                  ('foo/i', 'Search case-insensitively for '
                                   '"foo". (Can be combined with the other '
                                   'flags in any order.)'),
                                  ('foo/w', 'Search for "foo", only matching '
                                   'whole words. (Can be combined with the '
                                   'other flags in any order.)'),
                                  ('foo/#', 'Print the number of instances '
                                   'found instead of moving the cursor. '
                                   '(Can be combined with the other flags in '
                                   'any order.)'),
                                  ('foo/bar/', 'Replace the first instance '
                                   'of "foo" with "bar", starting from the '
                                   'cursor\'s position.'),
                                  ('foo/bar/[biw]', 'The flags works just '
                                   'like in the search action.'),
                                  ('foo/bar/a', 'Replace all instances '
                                   'of "foo" with "bar". (Can be combined '
                                   'with the other flags in any order.)'))),
                Command('search-next', 'Go to the next search hit',
                        self.search_next,
                        args=ArgumentRules.NONE, short_name='*'),
        ]
        self.line_number_bar = LineNumberBar(self)
        self.search_buffer: Optional[str] = None
        self.search_flags = QtGui.QTextDocument.FindFlags()
        self.saved_position = (self.textCursor().position(),
                               self.verticalScrollBar().value())

        def update_cursor_position() -> None:
            new_pos = (self.textCursor().position(),
                       self.verticalScrollBar().value())
            if self.saved_position != new_pos:
                self.saved_position = new_pos
                self.change_setting('start-at-pos', list(new_pos))

        self.cursor_timer = QtCore.QTimer()
        self.cursor_timer.setInterval(5000)
        self.cursor_timer.setSingleShot(False)
        self.cursor_timer.timeout.connect(update_cursor_position)
        self.cursor_timer.start()

        # Scrollbar fadeout
        self.autohide_scrollbar = False
        self.hide_scrollbar_timer = QtCore.QTimer(self)
        self.hide_scrollbar_timer.setInterval(1000)
        self.hide_scrollbar_timer.setSingleShot(True)
        self.hide_scrollbar_timer.timeout.connect(self.hide_scrollbar)
        self.verticalScrollBar().valueChanged.connect(self.scrollbar_moved)
        self.hide_scrollbar_effect = QtWidgets.QGraphicsOpacityEffect(
                self.verticalScrollBar())
        self.verticalScrollBar().setGraphicsEffect(self.hide_scrollbar_effect)
        a = QtCore.QPropertyAnimation(self.hide_scrollbar_effect, b'opacity')
        a.setEasingCurve(QtCore.QEasingCurve.InOutQuint)
        a.setDuration(500)
        a.setStartValue(1)
        a.setEndValue(0)
        self.hide_scrollbar_anim = a
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Input mode
        self.normal_mode_key_event: Optional[Callable[[QtGui.QKeyEvent], None]] = None
        self.setCursorWidth(3)
        self._insert_mode = False
        self.in_leader = False
        self.leader_timer = QtCore.QTimer()
        self.leader_timer.setInterval(500)
        self.leader_timer.setSingleShot(True)

        def update_leader() -> None:
            self.in_leader = False
        self.leader_timer.timeout.connect(update_leader)

    @property
    def insert_mode(self) -> bool:
        return self._insert_mode

    @insert_mode.setter
    def insert_mode(self, val: bool) -> None:
        if val:
            self.setCursorWidth(1)
        else:
            self.setCursorWidth(3)
        self._insert_mode = val

    def scrollbar_moved(self) -> None:
        if not self.autohide_scrollbar:
            return
        # For some reason it really doesn't like it when set to 1
        self.hide_scrollbar_effect.setOpacity(0.99)
        self.hide_scrollbar_timer.start()

    def hide_scrollbar(self) -> None:
        if not self.autohide_scrollbar:
            return
        self.hide_scrollbar_anim.start()

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'show-line-numbers':
            self.line_number_bar.setVisible(bool(new_value))
        elif name == 'max-textarea-width':
            width = int(new_value)
            if width < 1:
                self.error('Width has to be at least 1!')
            else:
                self.setMaximumWidth(width)
        elif name == 'autohide-scrollbar':
            if new_value:
                self.autohide_scrollbar = True
                self.scrollbar_moved()
            else:
                self.autohide_scrollbar = True
                self.hide_scrollbar_anim.stop()
                self.hide_scrollbar_timer.stop()
                self.hide_scrollbar_effect.setOpacity(0.99)
        elif name == 'start-at-pos':
            if new_value != self.saved_position:
                cursor_pos, sb_pos = new_value
                tc = self.textCursor()
                tc.setPosition(cursor_pos)
                self.setTextCursor(tc)
                self.verticalScrollBar().setValue(sb_pos)

    def set_max_width(self, arg: str) -> None:
        if not arg.isdecimal():
            self.error('Argument has to be a number!')
        else:
            width = int(arg)
            if width < 1:
                self.error('Width has to be at least 1!')
            else:
                self.setMaximumWidth(width)
                self.log(f'Max textarea width set to {width} px')
                self.change_setting('max-textarea-width', self.maximumWidth())

    def toggle_line_numbers(self) -> None:
        self.line_number_bar.setVisible(not self.line_number_bar.isVisible())
        self.change_setting('show-line-numbers',
                            self.line_number_bar.isVisible())

    def file_saved(self, filepath: str, new_name: bool) -> None:
        self.document().setModified(False)

    def visible_blocks(self) -> Iterable[Tuple[QtCore.QRectF, QtGui.QTextBlock]]:
        page_bottom = self.viewport().height()
        viewport_offset = self.contentOffset()
        block = self.firstVisibleBlock()
        while block.isValid():
            rect = self.blockBoundingGeometry(block).translated(viewport_offset)
            if rect.y() > page_bottom:
                break
            yield rect, block
            block = block.next()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if self.insert_mode:
            if event.text() == '\\' and not self.in_leader:
                def exit_leader() -> None:
                    if self.in_leader:
                        self.textCursor().insertText('\\')
                        self.in_leader = False
                QtCore.QTimer.singleShot(500, exit_leader)
                self.in_leader = True
            elif event.key() == Qt.Key_Escape or (self.in_leader and event.text() == 'e'):
                self.in_leader = False
                self.insert_mode = False
            else:
                super().keyPressEvent(event)
        elif self.normal_mode_key_event is not None:
            self.normal_mode_key_event(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self.line_number_bar.isVisible():
            self.setViewportMargins(0, 0, 0, 0)
        super().paintEvent(event)
        with self.try_it("horizontal ruler couldn't be drawn"):
            self.draw_horizontal_ruler()
        if self.line_number_bar.isVisible():
            self.line_number_bar.update()

    def draw_horizontal_ruler(self) -> None:
        painter = QtGui.QPainter(self.viewport())
        hrmargin = 0.3
        fg = self.palette().windowText().color()
        fg.setAlphaF(0.4)
        painter.setPen(QtGui.QPen(QtGui.QBrush(fg), 2))
        for rect, block in self.visible_blocks():
            if block.userState() & TextBlockState.HR and block != self.textCursor().block():
                x1 = int(rect.x() + rect.width()*hrmargin)
                x2 = int(rect.x() + rect.width()*(1-hrmargin))
                y = int(rect.y() + rect.height()*0.5)
                painter.drawLine(x1, y, x2, y)
        painter.end()

    def word_under_cursor(self) -> Optional[str]:
        cursor = self.textCursor()
        text = cursor.block().text()
        pos = cursor.positionInBlock()
        prefix = re.search(r"[\w'-]*$", text[:pos])
        suffix = re.search(r"^[\w'-]*", text[pos:])
        word = (('' if prefix is None else prefix[0])
                + ('' if suffix is None else suffix[0]))
        if not word.strip("'-"):
            return None
        return word

    def go_to_line(self, arg: str) -> None:
        if not arg.isdecimal():
            self.error('Argument has to be a number!')
        else:
            line = min(int(arg), self.document().blockCount())
            self.center_on_line(line)

    def center_on_line(self, line: int) -> None:
        block = self.document().findBlockByNumber(line)
        new_cursor = QtGui.QTextCursor(block)
        self.setTextCursor(new_cursor)
        self.centerCursor()

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        super().resizeEvent(ev)
        self.line_number_bar.setFixedHeight(self.height())

    def search_and_replace(self, text: str) -> None:
        def generate_flags(flagstr: str) -> QtGui.QTextDocument.FindFlags:
            # self.search_flags is automatically generated and does not
            # need to be initialized in __init__()
            search_flags = QtGui.QTextDocument.FindFlags()
            if 'b' in flagstr:
                search_flags |= QtGui.QTextDocument.FindBackward
            if 'i' not in flagstr:
                search_flags |= QtGui.QTextDocument.FindCaseSensitively
            if 'w' in flagstr:
                search_flags |= QtGui.QTextDocument.FindWholeWords
            return search_flags
        search_rx = re.compile(r'([^/]|\\/)+$')
        search_flags_rx = re.compile(r'([^/]|\\/)*?([^\\]/[biw#]*)$')
        replace_rx = re.compile(r"""
            (?P<search>([^/]|\\/)*?[^\\])
            /
            (?P<replace>(([^/]|\\/)*[^\\])?)
            /
            (?P<flags>[abiw]*)
            $
        """, re.VERBOSE)
        search_match = search_rx.match(text)
        search_flags_match = search_flags_rx.match(text)
        replace_match = replace_rx.match(text)
        if search_match:
            self.search_buffer = search_match.group(0)
            self.search_flags = QtGui.QTextDocument.FindCaseSensitively
            self.search_next()
        elif search_flags_match:
            search_buffer, flags = search_flags_match.group(0).rsplit('/', 1)
            if '#' in flags:
                self._count_hits(search_buffer, generate_flags(flags))
            else:
                self.search_buffer = search_buffer
                self.search_flags = generate_flags(flags)
                self.search_next()
        elif replace_match:
            self.search_buffer = replace_match.group('search')
            generate_flags(replace_match.group('flags'))
            if 'a' in replace_match.group('flags'):
                self._replace_all(replace_match.group('replace'))
            else:
                self._replace_next(replace_match.group('replace'))
        else:
            self.error('Malformed search/replace expression')

    def _searching_backwards(self) -> QtGui.QTextDocument.FindFlags:
        return QtGui.QTextDocument.FindBackward & self.search_flags

    def search_next(self, in_reverse: bool = False) -> None:
        """
        Go to the next string found.

        This does the same thing as running the same search-command again.
        """
        if self.search_buffer is None:
            self.error('No previous searches')
            return
        search_flags = QtGui.QTextDocument.FindFlags()
        if in_reverse != bool(self._searching_backwards()):
            searching_backwards = True
            search_flags |= self.search_flags | QtGui.QTextDocument.FindBackward
        else:
            searching_backwards = False
            search_flags |= self.search_flags & ~QtGui.QTextDocument.FindBackward
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer, search_flags)
        if not found:
            if not self.textCursor().atStart() \
                        or (searching_backwards
                            and not self.textCursor().atEnd()):
                if searching_backwards:
                    self.moveCursor(QtGui.QTextCursor.End)
                else:
                    self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer, search_flags)
                if not found:
                    self.setTextCursor(temp_cursor)
                    self.error('Text not found')
            else:
                self.setTextCursor(temp_cursor)
                self.error('Text not found')

    def _replace_next(self, replace_buffer: str) -> None:
        """
        Go to the next string found and replace it with replace_buffer.

        While this technically can be called from outside this class, it is
        not recommended (and most likely needs some modifications of the code.)
        """
        if self.search_buffer is None:
            return
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer, self.search_flags)
        if not found:
            if not self.textCursor().atStart() \
                        or (self._searching_backwards()
                            and not self.textCursor().atEnd()):
                if self._searching_backwards():
                    self.moveCursor(QtGui.QTextCursor.End)
                else:
                    self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer, self.search_flags)
                if not found:
                    self.setTextCursor(temp_cursor)
        if found:
            t = self.textCursor()
            t.insertText(replace_buffer)
            repllen = len(replace_buffer)
            t.setPosition(t.position() - repllen)
            t.setPosition(t.position() + repllen, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(t)
            self.log(f'Replaced on line {t.blockNumber()}, '
                     f'pos {t.positionInBlock()}')
        else:
            self.error('Text not found')

    def _count_hits(self, target: str,
                    flags: QtGui.QTextDocument.FindFlags) -> None:
        """
        Replace all strings found with the replace_buffer.

        As with replace_next, you probably don't want to call this manually.
        """
        times = 0
        cursor = QtGui.QTextCursor(self.document())
        # Don't use the backwards flag
        flags &= ~QtGui.QTextDocument.FindBackward
        while True:
            cursor = self.document().find(target, cursor, flags)
            if not cursor.isNull():
                times += 1
            else:
                break
        if times:
            self.log(f'The word "{target}" is used {times} times')
        else:
            self.log(f'The word "{target}" is not used')

    def _replace_all(self, replace_buffer: str) -> None:
        """
        Replace all strings found with the replace_buffer.

        As with replace_next, you probably don't want to call this manually.
        """
        if self.search_buffer is None:
            return
        temp_cursor = self.textCursor()
        times = 0
        self.moveCursor(QtGui.QTextCursor.Start)
        while True:
            found = self.find(self.search_buffer, self.search_flags)
            if found:
                self.textCursor().insertText(replace_buffer)
                times += 1
            else:
                break
        if times:
            self.log(f'{times} instance{"" if times == 1 else "s"} replaced')
        else:
            self.error('Text not found')
        self.setTextCursor(temp_cursor)


class LineNumberBar(QtWidgets.QFrame):
    def __init__(self, parent: TextArea) -> None:
        super().__init__(parent)
        self.textarea = parent
        self.text_margin = 2

    def update(self) -> None:  # type: ignore
        left_margin, _, right_margin, _ = self.getContentsMargins()
        total_lines = self.textarea.blockCount()
        font = self.font()
        font.setBold(True)
        font_metrics = QtGui.QFontMetricsF(font)
        max_width = int(sum([left_margin, right_margin,
                             font_metrics.width(str(total_lines)),
                             2 * self.text_margin]))
        self.setFixedWidth(max_width)
        self.textarea.setViewportMargins(max_width, 0, 0, 0)
        super().update()

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        super().hideEvent(event)
        self.textarea.setViewportMargins(0, 0, 0, 0)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.textarea.setViewportMargins(self.width(), 0, 0, 0)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        main_rect = self.contentsRect()
        main_rect.setTop(self.rect().top())
        main_rect.setHeight(self.rect().height())
        painter = QtGui.QPainter(self)
        viewport_offset = self.textarea.contentOffset()
        page_bottom = self.textarea.viewport().height()
        current_block = self.textarea.textCursor().block()
        block = self.textarea.firstVisibleBlock()
        text_align = QtGui.QTextOption(QtCore.Qt.AlignRight)
        font = painter.font()
        while block.isValid():
            rect = self.textarea.blockBoundingGeometry(block)\
                .translated(viewport_offset)
            rect.setLeft(main_rect.left())
            rect.setWidth(main_rect.width())
            if rect.y() > page_bottom:
                break
            if block == current_block:
                font.setBold(True)
                painter.setFont(font)
            elif font.bold():
                font.setBold(False)
                painter.setFont(font)
            tm = self.text_margin
            painter.drawText(rect.adjusted(tm, tm/2, -tm, -tm/2),
                             str(block.blockNumber()+1), option=text_align)
            block = block.next()
        painter.end()
