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

from itertools import zip_longest
from typing import cast, Iterable, List, Optional, Tuple

from PyQt5 import QtWidgets

from kalpana.chapters import Chapter, Section


class SectionItem(QtWidgets.QFrame):

    def __init__(self, parent: 'ChapterItem', num: int) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        self.index = num
        self.num = QtWidgets.QLabel(str(num), self)
        self.num.setObjectName('num')
        layout.addWidget(self.num)
        self.desc = QtWidgets.QLabel(self)
        self.desc.setObjectName('desc')
        self.desc.setWordWrap(True)
        layout.addWidget(self.desc, stretch=1)

    def set_data(self, desc: Optional[str]) -> None:
        self.desc.setText(desc if desc else '[no description]')


class ChapterItem(QtWidgets.QFrame):

    def __init__(self, parent: 'ChapterOverview', num: int) -> None:
        super().__init__(parent)
        def label(name: str, layout: QtWidgets.QBoxLayout,
                  word_wrap: bool = True) -> QtWidgets.QLabel:
            widget = QtWidgets.QLabel(self)
            widget.setWordWrap(word_wrap)
            widget.setObjectName(name)
            layout.addWidget(widget)
            return widget
        self.complete = False
        self.index = num
        layout = QtWidgets.QVBoxLayout(self)
        # Top row
        top_row = QtWidgets.QHBoxLayout()
        self.num = label('num', top_row)
        self.num.setText(str(num))
        self.title = label('title', top_row, word_wrap=False)
        self.length = label('length', top_row)
        top_row.addStretch(1)
        layout.addLayout(top_row)
        # The rest
        self.time = label('time', layout)
        self.tags = label('tags', layout)
        self.desc = label('desc', layout)
        self.section_items = []  # type: List[SectionItem]

    def set_data(self, title: Optional[str], length: Optional[int],
                 time: Optional[str], tags: Optional[set], desc: Optional[str],
                 sections: List[Section], complete: bool):
        self.complete = complete
        self.setDisabled(complete)
        self.title.setDisabled(complete)
        # Top row
        self.title.setText('Chapter {}'.format(title if title else self.index))
        if length is None:
            self.length.hide()
        else:
            self.length.setText('({})'.format(length))
            self.length.show()
        # Second row
        if time is None:
            self.time.hide()
        else:
            self.time.setText('🕑 {}'.format(time))
            self.time.show()
        if tags is None:
            self.tags.hide()
        else:
            self.tags.setText(', '.join('#'+t for t in sorted(tags)))
            self.tags.show()
        # The rest
        if desc is None:
            self.desc.hide()
        else:
            self.desc.setText(str(desc))
            self.desc.show()
        ziplist = enumerate(zip_longest(sections[1:], self.section_items))  # type: Iterable[Tuple[int, Tuple[Optional[Section], Optional[SectionItem]]]]
        for n, (section, item) in ziplist:
            if section is None:
                if item:
                    item.hide()
            else:
                if item is None:
                    item = SectionItem(self, n)
                    self.section_items.append(item)
                    self.layout().addWidget(item)
                item.set_data(section.desc)
                item.show()


class ChapterOverview(QtWidgets.QScrollArea):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.empty = True
        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName('container')
        self.setWidget(self.container)
        self.setWidgetResizable(True)
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        self.chapter_items = []  # type: List[ChapterItem]
        self.show()

    def load_chapter_data(self, chapters: List[Chapter]) -> None:
        self.empty = not bool(chapters[1:])
        ziplist = enumerate(zip_longest(chapters[1:], self.chapter_items))  # type: Iterable[Tuple[int, Tuple[Optional[Chapter], Optional[ChapterItem]]]]
        for n, (chapter, item) in ziplist:
            if chapter is None:
                if item:
                    item.hide()
            else:
                if item is None:
                    item = ChapterItem(self, n)
                    self.chapter_items.append(item)
                    cast(QtWidgets.QVBoxLayout, self.container.layout()).insertWidget(n, item)
                item.set_data(chapter.title, len(chapter), chapter.time,
                              chapter.tags, chapter.desc, chapter.sections,
                              chapter.complete)
                item.show()
