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

from itertools import accumulate
import re
from typing import Any, Dict, Iterable, List, Optional, Set

from PyQt5 import QtCore, QtGui

from kalpana.common import TextBlockState
from kalpana.settings import KalpanaObject


class Section:

    def __init__(self, desc: Optional[str] = None) -> None:
        self.line_count = 0
        self.word_count = 0
        self.desc = desc

    def update_word_count(self, block: QtGui.QTextBlock) -> None:
        offset = block.blockNumber()
        block = block.next()
        self.word_count = 0
        while block.isValid() \
                and block.blockNumber() < offset + self.line_count:
            self.word_count += len(block.text().split())
            block = block.next()

    def __eq__(self, other: Any) -> bool:
        try:
            return bool(self.line_count == other.line_count and
                        self.word_count == other.word_count and
                        self.desc == other.desc)
        except Exception:
            return False

    def __repr__(self) -> str:
        return '<{}.{} lines={} desc={!r} at {:x}>'\
                .format(self.__class__.__module__, self.__class__.__name__,
                        self.line_count, None, id(self))


class Chapter:

    def __init__(self, title: Optional[str] = None,
                 complete: bool = False) -> None:
        self.title = title
        self.complete = complete
        self.metadata_line_count = 0
        self.desc: Optional[str] = None
        self.time: Optional[str] = None
        self.tags: Optional[Set[str]] = None
        self.sections: List[Section] = [Section()]

    def update_line(self, state: int, line: str, ch_str: str,
                    line_num: int) -> None:
        if state & TextBlockState.CHAPTER:
            self.title = line[len(ch_str):].strip('✓ \t')
            self.complete = line.rstrip().endswith('✓')
        elif state & TextBlockState.SECTION:
            section_lines = list(accumulate([self.metadata_line_count]
                                            + [s.line_count for s in self.sections]))
            self.sections[section_lines.index(line_num)].desc = line.rstrip()[2:-2].strip()
        elif state & TextBlockState.DESC:
            self.desc = line.rstrip()[2:-2].strip()
        elif state & TextBlockState.TIME:
            self.time = line[1:].strip()
        elif state & TextBlockState.TAGS:
            self.tags = {tag.strip()[1:] for tag in line.split(',')
                         if tag.strip()}

    @property
    def line_count(self) -> int:
        """Return how many lines long the chapter is."""
        return (self.metadata_line_count
                + sum(s.line_count for s in self.sections))

    @property
    def word_count(self) -> int:
        return sum(s.word_count for s in self.sections)

    def __repr__(self) -> str:
        def cap(text: Optional[str], length: int) -> str:
            if text is None:
                return ''
            elif len(text) <= length:
                return repr(text)
            else:
                return repr(text[:length-1] + '…')
        template = ('<{module}.{cls} {complete}lines={lines} words={words} '
                    'title={title} desc={desc} time={time} tags={tags} '
                    'sections={sections}>')
        return template.format(
            module=self.__class__.__module__,
            cls=self.__class__.__name__,
            lines=self.line_count,
            complete='complete ' if self.complete else '',
            title=cap(self.title, 10),
            desc=cap(self.desc, 10),
            time=cap(self.time, 10),
            tags='' if self.tags is None else len(self.tags),
            sections=len(self.sections)
        )

    def __eq__(self, other: Any) -> bool:
        try:
            return bool(
                self.title == other.title
                and self.complete == other.complete
                and self.metadata_line_count == other.metadata_line_count
                and self.desc == other.desc
                and self.time == other.time
                and self.tags == other.tags
                and self.sections == other.sections
            )
        except Exception:
            return False

    def section_line_offsets(self, start: int) -> Iterable[int]:
        line = start
        for section in self.sections:
            yield line
            line += section.line_count


class ChapterIndex(QtCore.QObject, KalpanaObject):

    def __init__(self) -> None:
        super().__init__()
        self.kalpana_settings = ['chapter-keyword']
        self.chapters: List[Chapter] = []
        self.chapter_keyword = 'CHAPTER'
        self._block_count = -1
        # TODO: maybe actually use TextBlockState here?
        self._block_states: Dict[int, int] = {}

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'chapter-keyword':
            self.chapter_keyword = str(new_value)

    def update_line_index(self, document: QtGui.QTextDocument,
                          cursor: QtGui.QTextCursor,
                          pos: int, removed: int, added: int) -> bool:
        if not self.chapters:
            return self.full_line_index_update(document)

        def doc_text() -> str:
            # Dump this here to fix the UTF-16 garbage
            return re.sub(r'[\uffff-\U0010ffff]', 'xx', document.toPlainText())
        old_block_count = self._block_count
        new_block_count = self._block_count = document.blockCount()
        line_diff = new_block_count - old_block_count
        special_lines = self.special_lines()
        block = document.findBlock(pos)
        state = block.userState() & TextBlockState.LINEFORMATS
        line_num = block.blockNumber()
        # If only one line has been modified, try to update that data
        if not line_diff \
                and ((added and not removed) or (removed and not added)
                     or (added and removed
                         and '\n' not in doc_text()[pos:pos+added])):
            if state and state == self._block_states.get(line_num):
                chapter_num = self.which_chapter(line_num)
                offset = line_num - self.get_chapter_line(chapter_num)
                # TODO: recalc word count?
                # or just make it lazy maybe
                self.chapters[chapter_num].update_line(
                    state, block.text(), self.chapter_keyword, offset)
                return True
            elif state == self._block_states.get(line_num) == 0:
                return False
        # One line is shifted down irrelevantly
        if line_diff == 1 and added == 1 and line_num in special_lines:
            new_state = block.next().userState() & TextBlockState.LINEFORMATS
            if not state and new_state == self._block_states.get(line_num) \
                and (new_state & TextBlockState.CHAPTER
                     or new_state & TextBlockState.SECTION):
                success = self.add_remove_lines(line_num, line_diff)
                if success:
                    return True
        # Only added stuff which means we don't have to care about unknowns
        if added and not removed \
                and line_diff and line_num not in special_lines:
            start_block = document.findBlock(pos)
            clean = True
            block = start_block
            while block.isValid():
                if block.position() >= pos + added:
                    break
                if block.userState() & TextBlockState.LINEFORMATS:
                    clean = False
                    break
                block = block.next()
            # No fancy lines found, good
            if clean:
                success = self.add_remove_lines(line_num, line_diff)
                if success:
                    return True
        # Prolly spamming backspace, nbd
        if removed and not added and line_diff:
            removed_lines = set(range(line_num, line_num + 1 - line_diff))
            if not state and not removed_lines.intersection(special_lines):
                success = self.add_remove_lines(line_num, line_diff)
                if success:
                    return True
        return self.full_line_index_update(document)

    def full_line_index_update(self, document: QtGui.QTextDocument) -> bool:
        block = document.firstBlock()
        ch_str = self.chapter_keyword
        chapters = [Chapter()]
        current_chunk_start = 0
        n = 0
        self._block_states.clear()
        while block.isValid():
            line = block.text()
            state = block.userState()
            self._block_states[n] = state & TextBlockState.LINEFORMATS
            if state & TextBlockState.CHAPTER:
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters.append(Chapter())
                chapters[-1].update_line(state, line, ch_str, -1)
                current_chunk_start = n
            elif state & TextBlockState.SECTION:
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters[-1].sections.append(Section(
                    desc=line.rstrip()[2:-2].strip()
                ))
                current_chunk_start = n
            elif state & TextBlockState.CHAPTERMETA:
                chapters[-1].update_line(state, line, ch_str, -1)
            else:
                chapters[-1].sections[-1].word_count += len(line.split())
            n += 1
            block = block.next()
        chapters[-1].sections[-1].line_count = n - current_chunk_start
        # Shitty hack to fix the metadata line count
        for c in chapters:
            metalines = sum(x is not None
                            for x in [c.title, c.desc, c.tags, c.time])
            c.metadata_line_count = metalines
            c.sections[0].line_count -= metalines
        self.chapters = chapters
        return True

    @property
    def chapter_line_numbers(self) -> List[int]:
        return [0] + list(accumulate(chapter.line_count
                                     for chapter in self.chapters))[:-1]

    def get_chapter_line(self, num: int) -> int:
        """Return what line a given chapter begins on."""
        return self.chapter_line_numbers[num]

    def special_lines(self) -> List[int]:
        lines: List[int] = []
        pos = 0
        for chapter in self.chapters:
            lines.extend(range(pos, pos + chapter.metadata_line_count))
            pos += chapter.metadata_line_count
            for section in chapter.sections:
                lines.append(pos)
                pos += section.line_count
        return lines

    def which_chapter(self, line: int) -> int:
        """Return which chapter a given line is in."""
        if not self.chapters:
            return 0
        return next(n for n, chapter_line
                    in reversed(list(enumerate(self.chapter_line_numbers)))
                    if line >= chapter_line)

    def add_remove_lines(self, line: int, count: int) -> bool:
        if not self.chapters:
            return False
        pos = 0
        for n, chapter in enumerate(self.chapters):
            pos += chapter.metadata_line_count
            for section in chapter.sections:
                if pos + section.line_count >= line:
                    if count < 0 and count <= -section.line_count:
                        return False
                    section.line_count += count
                    self._block_states = {
                        k + (count if k >= line else 0): v
                        for k, v in self._block_states.items()
                    }
                    return True
                pos += section.line_count
        return False
