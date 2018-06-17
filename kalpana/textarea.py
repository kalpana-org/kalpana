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

from itertools import chain
from typing import cast, Any, List, Optional
import re

from PyQt5 import QtCore, QtGui, QtWidgets

from kalpana.common import KalpanaObject
from kalpana.common import TextBlockState as TBS
from kalpana.chapters import ChapterIndex
from libsyntyche.cli import Command, ArgumentRules


class TextArea(QtWidgets.QPlainTextEdit, KalpanaObject):

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.kalpana_settings = [
                'show-line-numbers',
                'max-textarea-width',
                'autohide-scrollbar'
        ]
        self.kalpana_commands = [
                Command('go-to-line', '', self.go_to_line,
                        args=ArgumentRules.REQUIRED, short_name=':'),
                Command('set-textarea-max-width',
                        'Set the max width of the page',
                        self.set_max_width, args=ArgumentRules.REQUIRED),
                Command('toggle-line-numbers', '', self.toggle_line_numbers,
                        args=ArgumentRules.NONE),
                Command('insert-text', '', self.insertPlainText,
                        short_name='_'),
                Command('search-and-replace', '', self.search_and_replace,
                        short_name='/'),
                Command('search-next', '', self.search_next,
                        args=ArgumentRules.NONE, short_name='*'),
        ]
        self.hr_blocks: List[QtGui.QTextBlock] = []
        self.line_number_bar = LineNumberBar(self)
        self.search_buffer: Optional[str] = None
        self.search_flags = QtGui.QTextDocument.FindFlag()

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

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self.line_number_bar.isVisible():
            self.setViewportMargins(0, 0, 0, 0)
        super().paintEvent(event)
        self.draw_horizontal_ruler()
        if self.line_number_bar.isVisible():
            self.line_number_bar.update()

    def draw_horizontal_ruler(self) -> None:
        painter = QtGui.QPainter(self.viewport())
        pagebottom = self.viewport().height()
        viewport_offset = self.contentOffset()
        block = self.firstVisibleBlock()
        hrmargin = 0.3
        fg = self.palette().windowText().color()
        fg.setAlphaF(0.4)
        painter.setPen(QtGui.QPen(QtGui.QBrush(fg), 2))
        while block.isValid():
            rect = self.blockBoundingGeometry(block)\
                .translated(viewport_offset)
            if rect.y() > pagebottom:
                break
            if block in self.hr_blocks and block != self.textCursor().block():
                x1 = int(rect.x() + rect.width()*hrmargin)
                x2 = int(rect.x() + rect.width()*(1-hrmargin))
                y = int(rect.y() + rect.height()*0.5)
                painter.drawLine(x1, y, x2, y)
            block = block.next()
        painter.end()

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
        def generate_flags(flagstr: str) -> None:
            # self.search_flags is automatically generated and does not
            # need to be initialized in __init__()
            search_flags = 0
            if 'b' in flagstr:
                search_flags |= QtGui.QTextDocument.FindBackward
            if 'i' not in flagstr:
                search_flags |= QtGui.QTextDocument.FindCaseSensitively
            if 'w' in flagstr:
                search_flags |= QtGui.QTextDocument.FindWholeWords
            self.search_flags = cast(QtGui.QTextDocument.FindFlag,
                                     search_flags)
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
        search_match = search_rx.match(text)
        search_flags_match = search_flags_rx.match(text)
        replace_match = replace_rx.match(text)
        if search_match:
            self.search_buffer = search_match.group(0)[1:]
            self.search_flags = QtGui.QTextDocument.FindCaseSensitively
            self.search_next()
        elif search_flags_match:
            self.search_buffer, flags = search_flags_match\
                .group(0)[1:].rsplit('/', 1)
            generate_flags(flags)
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
                        or (self._searching_backwards()
                            and not self.textCursor().atEnd()):
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


class Highlighter(QtGui.QSyntaxHighlighter, KalpanaObject):

    def __init__(self, textarea: TextArea,
                 chapter_index: ChapterIndex,
                 spellchecker=None) -> None:
        super().__init__(textarea.document())
        self.kalpana_settings = [
                'italic-marker',
                'bold-marker',
                'horizontal-ruler-marker'
        ]
        self.italic_marker = '/'
        self.bold_marker = '*'
        self.underline_marker = '_'
        self.hr_marker = '*'
        self.textarea = textarea
        self.textarea.cursorPositionChanged.connect(self.new_cursor_position)
        self.chapter_index = chapter_index
        self.spellchecker = spellchecker
        self.active_block = self.textarea.document().firstBlock()
        self.last_block = self.active_block

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'italic-marker':
            self.italic_marker = str(new_value)
        elif name == 'bold-marker':
            self.bold_marker = str(new_value)
        elif name == 'underline-marker':
            self.underline_marker = str(new_value)
        elif name == 'horizontal-ruler-marker':
            self.hr_marker = str(new_value)

    def new_cursor_position(self) -> None:
        """Make sure the horizontal rulers are drawn in the right place."""
        self.last_block = self.active_block
        self.active_block = self.textarea.textCursor().block()
        for block in [self.last_block, self.active_block]:
            if block.userState() & TBS.LINEFORMATS \
                    or block in self.textarea.hr_blocks:
                self.rehighlightBlock(block)
                if block in self.textarea.hr_blocks:
                    self.document().markContentsDirty(block.position(),
                                                      block.length())

    @staticmethod
    def utf16_len(text: str) -> int:
        """Adjust for the UTF-16 backend Qt uses."""
        return len(re.sub(r'[\uffff-\U0010ffff]', 'xx', text))

    @staticmethod
    def get_line_format(text: str, chapter_keyword: str,
                        prev_state: int) -> int:
        prefix = text.startswith
        suffix = text.rstrip().endswith
        if text.strip() and text.split()[0] == chapter_keyword:
            return TBS.CHAPTER
        elif prefix('<<') and suffix('>>'):
            return TBS.SECTION
        elif prefix('%%'):
            return TBS.META
        elif prev_state & (TBS.CHAPTER | TBS.CHAPTERMETA):
            if not prev_state & TBS.DESC and prefix('[[') and suffix(']]'):
                return TBS.DESC
            elif not prev_state & TBS.TAGS and prefix('#'):
                return TBS.TAGS
            elif not prev_state & TBS.TIME and prefix('🕑'):
                return TBS.TIME
        # Keep only formatting if not in a chapter line
        return prev_state & TBS.FORMATTING

    def highlightBlock(self, text: str) -> None:
        prev_state = self.previousBlockState()
        # Default state is -1 which is Not Good
        if prev_state < 0:
            prev_state = 0
        new_state = self.get_line_format(
            text, self.chapter_index.chapter_keyword, prev_state)
        fg = self.textarea.palette().windowText().color()
        # Chapter/meta lines
        line_state = new_state & TBS.LINEFORMATS
        if line_state:
            self.highlight_lines(text, line_state, fg)
            self.setCurrentBlockState(line_state)
            return
        # Horizontal ruler
        if self.hr_marker in text and text.strip(f' \t{self.hr_marker}') == '':
            self.highlight_horizontal_ruler(text, fg)
            self.setCurrentBlockState(new_state)
            return
        elif self.currentBlock() in self.textarea.hr_blocks:
            self.textarea.hr_blocks.remove(self.currentBlock())
        new_state = self.highlight_text_formatting(text, fg, new_state)
        self.setCurrentBlockState(new_state)
        if self.spellchecker.spellcheck_active:
            self.highlight_spelling(text)

    def highlight_horizontal_ruler(self, text: str, fg: QtGui.QColor) -> None:
        """Hide the asterisks where the horizontal ruler should be."""
        f = QtGui.QTextCharFormat()
        f.setFontPointSize(40)
        if not self.active_block or self.currentBlock() != self.active_block:
            fg.setAlphaF(0)
            f.setForeground(QtGui.QBrush(fg))
        self.setFormat(0, self.utf16_len(text), f)
        if self.currentBlock() not in self.textarea.hr_blocks:
            self.textarea.hr_blocks.append(self.currentBlock())

    def highlight_lines(self, text: str, state: int,
                        fg: QtGui.QColor) -> None:
        """Apply formatting to metadata lines (chapter headers, etc)."""
        f = QtGui.QTextCharFormat()
        if state & TBS.SECTION:
            if not self.currentBlock() == self.active_block:
                fg.setAlphaF(0.5)
            f.setFontWeight(QtGui.QFont.Bold)
        elif state & TBS.CHAPTERMETA:
            if not self.currentBlock() == self.active_block:
                fg.setAlphaF(0.3)
        elif state & TBS.META:
            if not self.currentBlock() == self.active_block:
                fg.setAlphaF(0.15)
        # Keep this last to not override the others
        elif state & TBS.CHAPTER:
            f.setFontPointSize(16)
            f.setFontWeight(QtGui.QFont.Bold)
        f.setForeground(QtGui.QBrush(fg))
        self.setFormat(0, self.utf16_len(text), f)

    def highlight_text_formatting(self, text: str, fg: QtGui.QColor,
                                  state: int) -> int:
        """Apply rich text formatting, such as bold or italic text."""
        faded = QtGui.QTextCharFormat()
        fg.setAlphaF(0.5)
        faded.setForeground(QtGui.QBrush(fg))
        # 1. find all markers
        # 2. use the current state and let the markers flip their state
        # 3. set relevant strings with respective formats
        # 4. return new state

        def update_format(fmt: QtGui.QTextCharFormat, marker: str) -> None:
            if marker == self.italic_marker:
                fmt.setFontItalic(not fmt.fontItalic())
            elif marker == self.underline_marker:
                fmt.setFontUnderline(not fmt.fontUnderline())
            elif marker == self.bold_marker:
                if fmt.fontWeight() == QtGui.QFont.Bold:
                    fmt.setFontWeight(QtGui.QFont.Normal)
                else:
                    fmt.setFontWeight(QtGui.QFont.Bold)

        def is_clean(fmt: QtGui.QTextCharFormat) -> bool:
            return not fmt.fontItalic() and not fmt.fontUnderline() \
                and fmt.fontWeight() == QtGui.QFont.Normal

        # Create format base on previous state
        f = self.format(0)
        if state & TBS.ITALIC:
            f.setFontItalic(True)
        if state & TBS.UNDERLINE:
            f.setFontUnderline(True)
        if state & TBS.BOLD:
            f.setFontWeight(QtGui.QFont.Bold)
        # Get all hits from all markers and sort by position
        markers = [self.italic_marker, self.bold_marker, self.underline_marker]
        rx = r'([^\w{0}]|^)?({0})(?(1)|([^\w{0}]|$))'
        hits = sorted((m.start(2), m.group(2)) for m in
                      chain(*(re.finditer(rx.format(re.escape(marker)),
                                          text) for marker in markers)))
        # Find each marker and set + update the format
        last_pos = 0
        for pos, marker in hits + [(self.utf16_len(text), '')]:
            # Only apply the format if it isn't plain or the text is empty
            if not is_clean(f):
                span = self.utf16_len(text[last_pos:pos])
                if span:
                    self.setFormat(last_pos, span, f)
            # Update the format and fade the marker slightly
            if marker:
                self.setFormat(pos, 1, faded)
                update_format(f, marker)
                pos += 1
            last_pos = pos
        # Make a new state based on the current format
        new_state = 0
        if f.fontItalic():
            new_state |= TBS.ITALIC
        if f.fontUnderline():
            new_state |= TBS.UNDERLINE
        if f.fontWeight() == QtGui.QFont.Bold:
            new_state |= TBS.BOLD
        return (state & ~TBS.FORMATTING) | new_state

    def highlight_spelling(self, text: str) -> None:
        """Highlight misspelled words."""
        for chunk in re.finditer(r"[\w-]+(?:'\w+)?", text):
            if chunk and re.search(r'\w', chunk.group()):
                if not self.spellchecker.check_word(chunk.group()):
                    f = self.format(self.utf16_len(text[:chunk.start()]))
                    f.setUnderlineColor(QtCore.Qt.red)
                    f.setUnderlineStyle(QtGui.QTextCharFormat.WaveUnderline)
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
