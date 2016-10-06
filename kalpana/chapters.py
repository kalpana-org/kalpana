
from typing import Any, List, Optional, Set, Sized

from kalpana.settings import Configurable


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


class Chapter(Sized):

    def __init__(self, title: str = '', complete: bool = False) -> None:
        self.title = title
        self.complete = complete
        self.metadata_line_count = 0
        self.desc = None  # type: str
        self.time = None  # type: str
        self.tags = None  # type: Set[str]
        self.sections = [Section()]  # type: List[Section]

    def __len__(self) -> int:
        """Return how many lines long the chapter is."""
        return self.metadata_line_count + sum(map(len, self.sections))

    def __repr__(self) -> str:
        return '<Chapter: title:{!r}>'.format(self.title)

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


class ChapterIndex(Configurable):

    registered_settings = ['chapter-keyword']

    def __init__(self) -> None:
        super().__init__()
        self.chapters = []  # type: List[Chapter]
        self.chapter_keyword = 'CHAPTER'

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'chapter-keyword':
            print(new_value)
            self.chapter_keyword = str(new_value)

    def get_chapter_line(self, num: int) -> int:
        """Return what line a given chapter begins on."""
        return sum(map(len, self.chapters[:num]))

    def which_chapter(self, line: int) -> int:
        """Return which chapter a given line is in."""
        if not self.chapters:
            return 0
        # ugly pos hack
        for chapter_num in range(len(self.chapters)):
            if line < self.get_chapter_line(chapter_num):
                return chapter_num-1
        return len(self.chapters)-1

    def parse_document(self, text: str) -> None:
        """Read a string and extract all chapter data from it."""
        ch_str = self.chapter_keyword
        start_chars = ch_str[0] + '[#🕑<'
        total_line_count = text.count('\n')
        lines = ((n, l) for n, l in enumerate(text.split('\n'))
                 if l and l[0] in start_chars)
        chapters = [Chapter()]
        current_chunk_start = 0
        consume_metadata = False
        last_n = 0
        for n, line in lines:
            if consume_metadata:
                last_n += 1
                if last_n == n:
                    if chapters[-1].desc is None and line.startswith('[[')\
                                            and line.rstrip().endswith(']]'):
                        chapters[-1].desc = line.rstrip()[2:-2].strip()
                        continue
                    elif chapters[-1].time is None and line[0] == '🕑':
                        chapters[-1].time = line[1:].strip()
                        continue
                    elif chapters[-1].tags is None and line[0] == '#':
                        chapters[-1].tags = {tag.strip()[1:]
                                             for tag in line.split(',') if tag.strip()}
                        continue
                chapters[-1].metadata_line_count = last_n - current_chunk_start
                current_chunk_start = last_n
                consume_metadata = False
            if line == ch_str or line.startswith(ch_str+' ') or line.startswith(ch_str+'\t'):
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters.append(Chapter(
                    title=line[len(ch_str):].strip('✓ \t'),
                    complete=line.rstrip().endswith('✓')
                ))
                current_chunk_start = last_n = n
                consume_metadata = True
            elif line.startswith('<<') and line.rstrip().endswith('>>'):
                chapters[-1].sections[-1].line_count = n - current_chunk_start
                chapters[-1].sections.append(Section(
                    desc=line.rstrip()[2:-2].strip()
                ))
                current_chunk_start = n
        chapters[-1].sections[-1].line_count = total_line_count - current_chunk_start + 1
        self.chapters = chapters
