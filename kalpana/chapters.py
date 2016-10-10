
from typing import cast, Any, List, Optional, Set, Sized, Tuple

from PyQt5 import QtCore, QtGui

from kalpana.textarea import LineFormatData
from kalpana.settings import KalpanaObject


class Section(Sized):

    def __init__(self, desc: Optional[str] = None) -> None:
        self.line_count = 0
        self.desc = desc

    def __len__(self) -> int:
        """Return how many lines long the section is."""
        return self.line_count

    def __eq__(self, other) -> bool:
        try:
            return self.line_count == other.line_count and\
                   self.desc == other.desc
        except:
            return False

    def __repr__(self) -> str:
        return '<{}.{} lines={} desc={!r} at {:x}>'\
                .format(self.__class__.__module__, self.__class__.__name__,
                        self.line_count, None, id(self))

class Chapter(Sized):

    def __init__(self, title: Optional[str] = None, complete: bool = False) -> None:
        self.title = title
        self.complete = complete
        self.metadata_line_count = 0
        self.desc = None  # type: Optional[str]
        self.time = None  # type: Optional[str]
        self.tags = None  # type: Optional[Set[str]]
        self.sections = [Section()]  # type: List[Section]

    def __len__(self) -> int:
        """Return how many lines long the chapter is."""
        return self.metadata_line_count + sum(map(len, self.sections))

    def __repr__(self) -> str:
        def cap(text, length):
            if text is None:
                return ''
            elif len(text) <= length:
                return repr(text)
            else:
                return repr(text[:length-1] + '…')
        template = '<{module}.{cls} {complete}lines={lines} title={title} '\
                   'desc={desc} time={time} tags={tags} sections={sections}>'
        return template.format(module=self.__class__.__module__,
                               cls=self.__class__.__name__,
                               lines=len(self),
                               complete='complete ' if self.complete else '',
                               title=cap(self.title, 10),
                               desc=cap(self.desc, 10),
                               time=cap(self.time, 10),
                               tags='' if self.tags is None else len(self.tags),
                               sections=len(self.sections))

    def __eq__(self, other) -> bool:
        try:
            return self.title == other.title and\
                   self.complete == other.complete and\
                   self.metadata_line_count == other.metadata_line_count and\
                   self.desc == other.desc and\
                   self.time == other.time and\
                   self.tags == other.tags and\
                   self.sections == other.sections
        except:
            return False


class ChapterIndex(QtCore.QObject, KalpanaObject):

    def __init__(self) -> None:
        super().__init__()
        self.kalpana_settings = ['chapter-keyword']
        self.chapters = []  # type: List[Chapter]
        self.chapter_line_numbers = []  # type: List[int]
        self.chapter_keyword = 'CHAPTER'

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'chapter-keyword':
            self.chapter_keyword = str(new_value)

    def update_line_index(self, block: QtGui.QTextBlock) -> None:
        ch_str = self.chapter_keyword
        chapters = [Chapter()]
        chapter_line_numbers = [0]
        current_chunk_start = 0
        n = 0
        while block.isValid():
            line = block.text()
            user_data = cast(LineFormatData, block.userData())
            state = user_data.text if user_data is not None else ''
            if state == 'chapter':
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters.append(Chapter(
                    title=line[len(ch_str):].strip('✓ \t'),
                    complete=line.rstrip().endswith('✓')
                ))
                chapter_line_numbers.append(n)
                current_chunk_start = n
            elif state == 'section':
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters[-1].sections.append(Section(
                    desc=line.rstrip()[2:-2].strip()
                ))
                current_chunk_start = n
            elif state in ('desc', 'time', 'tags'):
                if state == 'desc':
                    chapters[-1].desc = line.rstrip()[2:-2].strip()
                elif state == 'time':
                    chapters[-1].time = line[1:].strip()
                elif state == 'tags':
                    chapters[-1].tags = {tag.strip()[1:]
                                         for tag in line.split(',') if tag.strip()}
            n += 1
            block = block.next()
        chapters[-1].sections[-1].line_count = n - current_chunk_start
        # Shitty hack to fix the metadata line count
        for c in chapters:
            l = sum(x is not None for x in [c.title, c.desc, c.tags, c.time])
            c.metadata_line_count = l
            c.sections[0].line_count -= l
        self.chapters = chapters
        self.chapter_line_numbers = chapter_line_numbers

    def parse_line(self, text: str, previous_state: int) -> Tuple[int, Optional[str]]:
        chapter = 0b00001
        section = 0b00010
        desc = 0b00100
        tags = 0b01000
        time = 0b10000
        ch_str = self.chapter_keyword
        if text == ch_str or text.startswith(ch_str+' ') or text.startswith(ch_str+'\t'):
            return chapter, 'chapter'
        elif text.startswith('<<') and text.rstrip().endswith('>>'):
            return section, 'section'
        elif previous_state & chapter:
            if not previous_state & desc and text.startswith('[[') and text.rstrip().endswith(']]'):
                return previous_state | desc, 'desc'
            elif not previous_state & tags and text.startswith('#'):
                return previous_state | tags, 'tags'
            elif not previous_state & time and text.startswith('🕑'):
                return previous_state | time, 'time'
        return 0, None

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
