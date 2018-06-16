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

import re
from typing import Any, Iterable, List, Optional, Set

from PyQt5 import QtCore, QtGui

from kalpana.common import TextBlockState
from kalpana.settings import KalpanaObject


class Section:

    def __init__(self, desc: Optional[str] = None) -> None:
        self.line_count = 0
        self.word_count = 0
        self.desc = desc

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
        self.chapter_line_numbers: List[int] = []
        self.chapter_keyword = 'CHAPTER'
        self._block_count = -1

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'chapter-keyword':
            self.chapter_keyword = str(new_value)

    def update_line_index(self, document: QtGui.QTextDocument,
                          cursor: QtGui.QTextCursor,
                          pos: int, removed: int, added: int) -> bool:
        old_block_count = self._block_count
        new_block_count = self._block_count = document.blockCount()
        # Only added stuff which means we don't have to care about unknowns
        if added and not removed and self.chapters:
            new_text = re.sub(r'[\uffff-\U0010ffff]', 'xx',
                              document.toPlainText())[pos: pos+added]
            # No new blocks
            if '\n' not in new_text:
                block = cursor.block()
                state = block.userState()
                # No relevant state and no relevant new state
                if not state & TextBlockState.LINEFORMATS \
                        and not block.text().startswith(self.chapter_keyword) \
                        and not (block.text().startswith('<<')
                                 and block.text().endswith('>>')):
                    return False
            # Simply update line numbers if the added lines are regular text
            else:
                start_block = document.findBlock(pos)
                clean = True
                block = start_block
                while block.isValid():
                    if block.position() > pos + added:
                        break
                    if block.userState() & TextBlockState.LINEFORMATS:
                        clean = False
                        break
                    block = block.next()
                # No fancy lines found, good
                if clean:
                    line_num = start_block.blockNumber()
                    line_diff = new_block_count - old_block_count
                    self.insert_lines(line_num, line_diff)
                    return True
        # Prolly spamming backspace, nbd
        elif removed and not added and self.chapters:
            block = cursor.block()
            line_num = block.blockNumber()
            chapter = self.which_chapter(line_num)
            chapter_start = self.chapter_line_numbers[chapter]
            line_diff = old_block_count - new_block_count
            if line_num not in self.chapter_line_numbers \
                    and line_num not in self.chapters[chapter].section_line_offsets(chapter_start) \
                    and not (chapter_start <= line_num < chapter_start + self.chapters[chapter].metadata_line_count):
                # All in one line, nothing fancy going on here
                if not line_diff:
                    state = block.userState()
                    if not state & TextBlockState.LINEFORMATS:
                        return False
                else:
                    success = self.remove_lines(line_num, line_diff)
                    if success:
                        return True
        return self.full_line_index_update(document)

    def full_line_index_update(self, document: QtGui.QTextDocument) -> bool:
        block = document.firstBlock()
        ch_str = self.chapter_keyword
        chapters = [Chapter()]
        chapter_line_numbers = [0]
        current_chunk_start = 0
        n = 0
        while block.isValid():
            line = block.text()
            state = block.userState()
            if state & TextBlockState.CHAPTER:
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters.append(Chapter(
                    title=line[len(ch_str):].strip('✓ \t'),
                    complete=line.rstrip().endswith('✓')
                ))
                chapter_line_numbers.append(n)
                current_chunk_start = n
            elif state & TextBlockState.SECTION:
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters[-1].sections.append(Section(
                    desc=line.rstrip()[2:-2].strip()
                ))
                current_chunk_start = n
            elif state & TextBlockState.DESC:
                chapters[-1].desc = line.rstrip()[2:-2].strip()
            elif state & TextBlockState.TIME:
                chapters[-1].time = line[1:].strip()
            elif state & TextBlockState.TAGS:
                chapters[-1].tags = {tag.strip()[1:]
                                     for tag in line.split(',')
                                     if tag.strip()}
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
        self.chapter_line_numbers = chapter_line_numbers
        return True

    def get_chapter_line(self, num: int) -> int:
        """Return what line a given chapter begins on."""
        return self.chapter_line_numbers[num]

    def which_chapter(self, line: int) -> int:
        """Return which chapter a given line is in."""
        if not self.chapters:
            return 0
        return next(n for n, chapter_line
                    in reversed(list(enumerate(self.chapter_line_numbers)))
                    if line >= chapter_line)

    def insert_lines(self, line: int, count: int) -> None:
        if not self.chapters:
            return
        pos = 0
        found = False
        for n, chapter in enumerate(self.chapters):
            if not found:
                pos += chapter.metadata_line_count
                for section in chapter.sections:
                    if pos + section.line_count >= line:
                        section.line_count += count
                        found = True
                        break
                    pos += section.line_count
            else:
                self.chapter_line_numbers[n] += count

    def remove_lines(self, line: int, count: int) -> bool:
        if not self.chapters:
            return True
        pos = 0
        found = False
        for n, chapter in enumerate(self.chapters):
            if not found:
                pos += chapter.metadata_line_count
                for section in chapter.sections:
                    if pos + section.line_count >= line:
                        if count >= section.line_count:
                            return False
                        section.line_count -= count
                        found = True
                        break
                    pos += section.line_count
            else:
                self.chapter_line_numbers[n] -= count
        return True
