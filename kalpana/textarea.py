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

from PyQt4 import QtCore, QtGui


class TextArea(QtGui.QPlainTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumWidth(500)
        self.line_number_bar = LineNumberBar(self)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        painter = QtGui.QPainter(self.viewport())
        #painter.fillRect(0,0,400,400, QtCore.Qt.red)
        painter.end()
        self.line_number_bar.update()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.line_number_bar.setFixedHeight(self.height())



class LineNumberBar(QtGui.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.textarea = parent
        self.text_margin = 2

    def update(self, *args):
        total_lines = self.textarea.blockCount()
        font = self.font()
        font.setBold(True)
        font_metrics = QtGui.QFontMetricsF(font)
        max_width = font_metrics.width(str(total_lines)) + 2*self.text_margin
        self.setFixedWidth(max_width)
        self.textarea.setViewportMargins(max_width,0,0,0)
        super().update(*args)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        painter = QtGui.QPainter(self)
        viewport_offset = self.textarea.contentOffset()
        page_bottom = self.textarea.viewport().height()
        current_block = self.textarea.textCursor().block()
        block = self.textarea.firstVisibleBlock()
        text_align = QtGui.QTextOption(QtCore.Qt.AlignRight)
        font = painter.font()
        while block.isValid():
            rect = self.textarea.blockBoundingGeometry(block).translated(viewport_offset)
            rect.setWidth(self.width())
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
                             str(block.blockNumber()), option=text_align)
            block = block.next()
        painter.end()