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

import re
from itertools import chain
from typing import Any, Callable

from PyQt5 import QtCore, QtGui

from .common import KalpanaObject
from .common import TextBlockState as TBS


class Highlighter(QtGui.QSyntaxHighlighter, KalpanaObject):

    def __init__(self, document: QtGui.QTextDocument,
                 get_fg: Callable[[], QtGui.QColor],
                 check_word: Callable[[str], bool]) -> None:
        super().__init__(document)
        self.kalpana_settings = [
            'italic-marker',
            'bold-marker',
            'horizontal-ruler-marker',
            'spellcheck-active',
            'chapter-keyword',
        ]
        self.italic_marker = '/'
        self.bold_marker = '*'
        self.underline_marker = '_'
        self.hr_marker = '*'
        self.get_fg = get_fg
        self.check_word = check_word
        self.chapter_keyword = ''
        self.spellcheck_active = False
        self.active_block = document.firstBlock()
        self.last_block = self.active_block
        self.init_is_done = False

    def init_done(self) -> None:
        # This is here to avoid a gazillion different rehighlight() calls
        # when kalpana is booting
        self.init_is_done = True
        self.rehighlight()

    def rehighlight(self) -> None:
        if self.init_is_done:
            super().rehighlight()

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'italic-marker':
            self.italic_marker = str(new_value)
        elif name == 'bold-marker':
            self.bold_marker = str(new_value)
        elif name == 'underline-marker':
            self.underline_marker = str(new_value)
        elif name == 'horizontal-ruler-marker':
            self.hr_marker = str(new_value)
        elif name == 'spellcheck-active':
            if self.spellcheck_active != bool(new_value):
                self.spellcheck_active = bool(new_value)
                self.rehighlight()
        elif name == 'chapter-keyword':
            self.chapter_keyword = str(new_value)

    def new_cursor_position(self, new_block: QtGui.QTextBlock) -> None:
        """Make sure the horizontal rulers are drawn in the right place."""
        self.last_block = self.active_block
        self.active_block = new_block
        for block in [self.last_block, self.active_block]:
            if block.userState() & TBS.LINEFORMATS \
                    or block.userState() & TBS.HR:
                self.rehighlightBlock(block)
                if block.userState() & TBS.HR:
                    self.document().markContentsDirty(block.position(),
                                                      block.length())

    def rehighlight_word(self, word: str) -> None:
        block = self.document().firstBlock()
        while block.isValid():
            if word in block.text():
                self.rehighlightBlock(block)
            block = block.next()

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
        elif prefix('!!TODO'):
            return TBS.TODO
        elif prev_state & (TBS.CHAPTER | TBS.CHAPTERMETA):
            if not prev_state & TBS.DESC and prefix('[[') and suffix(']]'):
                return TBS.DESC
            elif not prev_state & TBS.TAGS and prefix('#'):
                return TBS.TAGS
            elif not prev_state & TBS.TIME \
                    and any(prefix(x) for x in ['🕑', '[time] ', '[date] ']):
                return TBS.TIME
        # Keep only formatting if not in a chapter line
        return prev_state & TBS.FORMATTING

    def highlightBlock(self, text: str) -> None:
        with self.try_it(f"Highlighting this block ({text!r}) failed"):
            prev_state = self.previousBlockState()
            # Default state is -1 which is Not Good
            if prev_state < 0:
                prev_state = 0
            new_state = self.get_line_format(
                text, self.chapter_keyword, prev_state)
            fg = self.get_fg()
            # Chapter/meta lines
            line_state = new_state & TBS.LINEFORMATS
            if line_state:
                self.highlight_lines(text, line_state, fg)
                self.setCurrentBlockState(line_state)
                return
            # Horizontal ruler
            if self.hr_marker in text \
                    and text.strip(f' \t{self.hr_marker}') == '':
                self.highlight_horizontal_ruler(text, fg)
                self.setCurrentBlockState(new_state | TBS.HR)
                return
            new_state = self.highlight_text_formatting(text, fg, new_state)
            self.setCurrentBlockState(new_state)
            if self.spellcheck_active:
                self.highlight_spelling(text)

    def highlight_horizontal_ruler(self, text: str, fg: QtGui.QColor) -> None:
        """Hide the asterisks where the horizontal ruler should be."""
        f = QtGui.QTextCharFormat()
        f.setFontPointSize(40)
        if not self.active_block or self.currentBlock() != self.active_block:
            fg.setAlphaF(0)
            f.setForeground(QtGui.QBrush(fg))
        self.setFormat(0, self.utf16_len(text), f)

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
        elif state & TBS.TODO:
            f.setFontWeight(QtGui.QFont.Bold)
            f.setFontOverline(True)
            f.setFontUnderline(True)
            f.setFontCapitalization(QtGui.QFont.SmallCaps)
            # fg = QtGui.QColor('#d8a200')
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
            # Skip chunks only consisting of dashes
            if chunk and chunk.group().strip('-'):
                word = chunk.group()
                if word.endswith("'s"):
                    word = word[:-2]
                if not self.check_word(word):
                    f = self.format(self.utf16_len(text[:chunk.start()]))
                    f.setUnderlineColor(QtCore.Qt.red)
                    f.setUnderlineStyle(QtGui.QTextCharFormat.WaveUnderline)
                    self.setFormat(chunk.start(), chunk.end()-chunk.start(), f)
