# Copyright (C) 2009 John Schember

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Note: taken from http://john.nachtimwald.com/2009/08/15/qtextedit-with-line-numbers/
# Or more precisely: http://www.japh.de/blog/qtextedit-with-line-numbers/

from PySide import QtGui
from PySide.QtCore import Qt, SIGNAL

class LineTextWidget(QtGui.QPlainTextEdit):
 
    def append(self,string):
        self.appendPlainText(string)
 
    class NumberBar(QtGui.QWidget): 
 
        def __init__(self, *args):
            QtGui.QWidget.__init__(self, *args)
            self.edit = None
            # This is used to update the width of the control.
            # It is the highest line that is currently visibile.
            self.highest_line = 0
            self.showbar = False
 
        def setTextEdit(self, edit):
            self.edit = edit
 
        def update(self, *args):
            if not self.showbar:
                width = 0
            else:
                width = QtGui.QFontMetrics(self.edit.document().defaultFont()).\
                                            width(str(self.highest_line)) + 10
            if self.width() != width:
                self.setFixedWidth(width)
                self.edit.setViewportMargins(width,0,0,0)
            QtGui.QWidget.update(self, *args)
 
        def paintEvent(self, event):
            contents_y = 0
            page_bottom = self.edit.viewport().height()
            font_metrics = QtGui.QFontMetrics(self.edit.document().
                                              defaultFont())
            current_block = self.edit.document().findBlock(self.edit.
                                                           textCursor().
                                                           position())
 
            painter = QtGui.QPainter(self)
 
            # Iterate over all text blocks in the document.
            block = self.edit.firstVisibleBlock()
            viewport_offset = self.edit.contentOffset()
            line_count = block.blockNumber()
            painter.setFont(self.edit.document().defaultFont())
            painter.setPen(QtGui.QColor('darkGray'))
            while block.isValid():
                line_count += 1
 
                # The top left position of the block in the document
                position = self.edit.blockBoundingGeometry(block).topLeft()\
                            + viewport_offset
                # Check if the position of the block is out side of the visible
                # area.
                if position.y() > page_bottom:
                    break
 
                # We want the line number for the selected line to be bold.
                bold = False
                if block == current_block:
                    bold = True
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
 
                # Draw the line number right justified at the y position of the
                # line. 3 is a magic padding number. drawText(x, y, text).
                painter.drawText(self.width() - font_metrics.
                                 width(str(line_count)) - 3,
                                 round(position.y() + font_metrics.
                                       ascent()*1.05), str(line_count))
 
                # Remove the bold style if it was set previously.
                if bold:
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)
 
                block = block.next()
 
            self.highest_line = line_count
            painter.end()
 
            QtGui.QWidget.paintEvent(self, event)
 
 
    def __init__(self, *args):
        QtGui.QPlainTextEdit.__init__(self, *args)
 
        self.number_bar = self.NumberBar(self)
        self.number_bar.setTextEdit(self)
 
        self.viewport().installEventFilter(self)
 
    def resizeEvent(self,e):
        self.number_bar.setFixedHeight(self.height())
        QtGui.QPlainTextEdit.resizeEvent(self,e)
 
    def setDefaultFont(self,font):
      self.document().setDefaultFont(font)
 
    def eventFilter(self, object, event):
        # Update the line numbers for all events on the text edit
        # and the viewport.
        # This is easier than connecting all necessary singals.
        if object is self.viewport():
            self.number_bar.update()
            return False
        return QtGui.QPlainTextEdit.eventFilter(object, event)