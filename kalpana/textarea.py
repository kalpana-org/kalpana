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

from PyQt5 import QtCore, QtGui, QtWidgets


class TextArea(QtWidgets.QPlainTextEdit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.line_number_bar = LineNumberBar(self)

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
        super().paintEvent(ev)
        painter = QtGui.QPainter(self.viewport())
        #painter.fillRect(0,0,400,400, QtCore.Qt.red)
        painter.end()
        self.line_number_bar.update()

    def center_on_line(self, line: int) -> None:
        block = self.document().findBlockByNumber(line)
        new_cursor = QtGui.QTextCursor(block)
        self.setTextCursor(new_cursor)
        self.centerCursor()

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        super().resizeEvent(ev)
        self.line_number_bar.setFixedHeight(self.height())


class LineNumberBar(QtWidgets.QFrame):
    def __init__(self, parent: TextArea) -> None:
        super().__init__(parent)
        self.textarea = parent
        self.text_margin = 2

    def update(self, *args) -> None:
        left_margin, _, right_margin, _ = self.getContentsMargins()
        total_lines = self.textarea.blockCount()
        font = self.font()
        font.setBold(True)
        font_metrics = QtGui.QFontMetricsF(font)
        max_width = int(left_margin + right_margin + font_metrics.width(str(total_lines)) + 2*self.text_margin)
        self.setFixedWidth(max_width)
        self.textarea.setViewportMargins(max_width, 0, 0, 0)
        super().update(*args)

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
        super().paintEvent(ev)
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
