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

from typing import Any, Callable
import re

from PyQt5 import QtCore, QtGui, QtWidgets

from kalpana.common import Command, KalpanaObject


class TextArea(QtWidgets.QPlainTextEdit, KalpanaObject):

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.kalpana_settings = ['show-line-numbers']
        self.kalpana_commands = [
                Command('go-to-line', '', self.go_to_line),
                Command('set-textarea-max-width', 'Set the max width of the page',
                        self.set_max_width),
                Command('toggle-line-numbers', '', self.toggle_line_numbers,
                        accept_args=False),
                Command('insert-text', '', self.insertPlainText),
                Command('search-and-replace', '', self.search_and_replace),
                Command('search-next', '', self.search_next,
                        accept_args=False),
        ]
        self.line_number_bar = LineNumberBar(self)
        self.search_buffer = None  # type: str

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'show-line-numbers':
            self.line_number_bar.setVisible(bool(new_value))

    def set_max_width(self, arg: str) -> None:
        if not arg.isdecimal():
            self.error('Argument has to be a number!')
        elif int(arg) < 1:
            self.error('Width has to be at least 1!')
        else:
            self.setMaximumWidth(int(arg))
            self.log('Max textarea width set to {} px'.format(arg))

    def toggle_line_numbers(self) -> None:
        self.line_number_bar.setVisible(not self.line_number_bar.isVisible())

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
        if not self.line_number_bar.isVisible():
            self.setViewportMargins(0, 0, 0, 0)
        super().paintEvent(ev)
        if self.line_number_bar.isVisible():
            self.line_number_bar.update()

    def word_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.WordUnderCursor)
        return cursor.selectedText()

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
        def generate_flags(flagstr):
            # self.search_flags is automatically generated and does not
            # need to be initialized in __init__()
            self.search_flags = QtGui.QTextDocument.FindFlags()
            if 'b' in flagstr:
                self.search_flags |= QtGui.QTextDocument.FindBackward
            if 'i' not in flagstr:
                self.search_flags |= QtGui.QTextDocument.FindCaseSensitively
            if 'w' in flagstr:
                self.search_flags |= QtGui.QTextDocument.FindWholeWords
        search_rx = re.compile(r'/([^/]|\\/)+$')
        search_flags_rx = re.compile(r'/([^/]|\\/)*?([^\\]/[biw]*)$')
        replace_rx = re.compile(r"""
            /
            (?P<search>([^/]|\\/)*?[^\\])
            /
            (?P<replace>(([^/]|\\/)*[^\\])?)
            /
            (?P<flags>[abiw]*)
            $
        """, re.VERBOSE)
        if search_rx.match(text):
            self.search_buffer = search_rx.match(text).group(0)[1:]
            self.search_flags = QtGui.QTextDocument.FindCaseSensitively
            self.search_next()
        elif search_flags_rx.match(text):
            self.search_buffer, flags = search_flags_rx.match(text).group(0)[1:].rsplit('/', 1)
            generate_flags(flags)
            self.search_next()
        elif replace_rx.match(text):
            match = replace_rx.match(text)
            self.search_buffer = match.group('search')
            generate_flags(match.group('flags'))
            if 'a' in match.group('flags'):
                self._replace_all(match.group('replace'))
            else:
                self._replace_next(match.group('replace'))
        else:
            self.error('Malformed search/replace expression')

    def _searching_backwards(self) -> int:
        return QtGui.QTextDocument.FindBackward & self.search_flags

    def search_next(self) -> None:
        """
        Go to the next string found.

        This does the same thing as running the same search-command again.
        """
        if self.search_buffer is None:
            self.error('No previous searches')
            return
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer, self.search_flags)
        if not found:
            if not self.textCursor().atStart() \
                        or (self._searching_backwards() and not self.textCursor().atEnd()):
                if self._searching_backwards():
                    self.moveCursor(QtGui.QTextCursor.End)
                else:
                    self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer, self.search_flags)
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
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer, self.search_flags)
        if not found:
            if not self.textCursor().atStart() \
                        or (self._searching_backwards() and not self.textCursor().atEnd()):
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
            l = len(replace_buffer)
            t.setPosition(t.position() - l)
            t.setPosition(t.position() + l, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(t)
            self.log('Replaced on line {}, pos {}'
                             ''.format(t.blockNumber(), t.positionInBlock()))
        else:
            self.error('Text not found')

    def _replace_all(self, replace_buffer: str) -> None:
        """
        Replace all strings found with the replace_buffer.

        As with replace_next, you probably don't want to call this manually.
        """
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
            self.log('{0} instance{1} replaced'.format(times, 's'*(times>0)))
        else:
            self.error('Text not found')
        self.setTextCursor(temp_cursor)


class LineFormatData(QtGui.QTextBlockUserData):

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class Highlighter(QtGui.QSyntaxHighlighter):

    def __init__(self, textarea,
                 chapter_index=None, spellchecker=None) -> None:
        super().__init__(textarea.document())
        self.textarea = textarea
        self.chapter_index = chapter_index
        self.spellchecker = spellchecker

    def highlightBlock(self, text: str) -> None:
        def utf16_len(text: str) -> int:
            """Adjust for the UTF-16 backend Qt uses."""
            return len(re.sub(r'[\uffff-\U0010ffff]', 'xx', text))
        state, line_format = self.chapter_index.parse_line(text, self.previousBlockState())
        self.setCurrentBlockState(state)
        self.setCurrentBlockUserData(LineFormatData(line_format))
        if line_format:
            f = QtGui.QTextCharFormat()
            fg = self.textarea.palette().windowText().color()
            if line_format == 'chapter':
                f.setFontPointSize(16)
                f.setFontWeight(QtGui.QFont.Bold)
            elif line_format == 'section':
                fg.setAlphaF(0.5)
                f.setFontWeight(QtGui.QFont.Bold)
                f.setForeground(QtGui.QBrush(fg))
            elif line_format in ('desc', 'tags', 'time'):
                fg.setAlphaF(0.3)
                f.setForeground(QtGui.QBrush(fg))
            self.setFormat(0, utf16_len(text), f)
            return
        if self.spellchecker.spellcheck_active:
            f = QtGui.QTextCharFormat()
            f.setUnderlineColor(QtCore.Qt.red)
            f.setUnderlineStyle(QtGui.QTextCharFormat.WaveUnderline)
            for chunk in re.finditer(r"[\w-]+(?:'\w+)?", text):
                if chunk and re.search(r'\w', chunk.group()):
                    if not self.spellchecker.check_word(chunk.group()):
                        self.setFormat(chunk.start(), chunk.end()-chunk.start(), f)


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
        max_width = int(left_margin + right_margin + font_metrics.width(str(total_lines)) + 2*self.text_margin)
        self.setFixedWidth(max_width)
        self.textarea.setViewportMargins(max_width, 0, 0, 0)
        super().update()

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
            rect = self.textarea.blockBoundingGeometry(block).translated(viewport_offset)
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
            painter.drawText(rect.adjusted(tm,tm/2, -tm,-tm/2),
                             str(block.blockNumber()+1), option=text_align)
            block = block.next()
        painter.end()
