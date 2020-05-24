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
from typing import cast, Iterable, List, Optional, Set, Tuple

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtProperty, Qt

from kalpana.chapters import Chapter, Section

from libsyntyche.widgets import Signal1


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
        self.desc.setText(desc or '[no description]')


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
        self.chapter: Optional[Chapter] = None
        self.expanded = False
        self.complete = False
        self._complete_color = QtGui.QColor(Qt.white)
        self._wip_color = QtGui.QColor(Qt.white)
        self._not_started_color = QtGui.QColor(Qt.white)
        self.index = num
        layout = QtWidgets.QVBoxLayout(self)
        # Top row
        top_row = QtWidgets.QHBoxLayout()
        self.num = label('num', top_row)
        self.expand_button = QtWidgets.QPushButton('+', self)
        self.expand_button.setObjectName('chapter_expand_button')
        self.expand_button.setCheckable(True)
        self.expand_button.setChecked(self.expanded)
        self.expand_button.setCursor(Qt.PointingHandCursor)
        cast(Signal1[bool],
             self.expand_button.toggled).connect(self.toggle)
        top_row.addWidget(self.expand_button)
        self.num.setText(str(num))
        self.title = label('title', top_row, word_wrap=False)
        self.length = label('length', top_row)
        top_row.addStretch(1)
        layout.addLayout(top_row)
        # The rest
        self.desc = label('desc', layout)
        self.time = label('time', layout)
        self.tags = label('tags', layout)
        self.section_items: List[SectionItem] = []

    @pyqtProperty(QtGui.QColor)
    def complete_color(self) -> QtGui.QColor:
        return self._complete_color

    @complete_color.setter
    def complete_color(self, color: QtGui.QColor) -> None:
        self._complete_color = color

    @pyqtProperty(QtGui.QColor)
    def wip_color(self) -> QtGui.QColor:
        return self._wip_color

    @wip_color.setter
    def wip_color(self, color: QtGui.QColor) -> None:
        self._wip_color = color

    @pyqtProperty(QtGui.QColor)
    def not_started_color(self) -> QtGui.QColor:
        return self._not_started_color

    @not_started_color.setter
    def not_started_color(self, color: QtGui.QColor) -> None:
        self._not_started_color = color

    def toggle(self, expand: bool) -> None:
        self.expanded = expand
        self.expand_button.setText('-' if expand else '+')
        for label in [self.desc, self.tags, self.time]:
            label.setVisible(expand and bool(label.text().strip()))
        for item in self.section_items:
            item.setVisible(expand)

    def set_data(self, chapter: Chapter, update_stylesheet: bool,
                 force_refresh: bool) -> None:
        if update_stylesheet:
            # This needs to be here to hack in colors for the various
            # chapter states, but it's a slow operation and it gets
            # overwritten so it should only be run when entering the
            # chapter overview.
            if chapter.complete:
                c = self._complete_color
            elif chapter.word_count:
                c = self._wip_color
            else:
                c = self._not_started_color
            self.setStyleSheet(f'color: rgba({c.red()}, {c.green()}, '
                               f'{c.blue()}, {c.alpha()});')
        if not force_refresh and self.chapter == chapter:
            return
        self.chapter = chapter
        title = chapter.title
        length = chapter.word_count
        time = chapter.time
        tags = chapter.tags
        desc = chapter.desc
        sections = chapter.sections
        complete = chapter.complete
        self.complete = complete
        self.expand_button.setChecked(self.expanded)
        complete_text = ' ✓' if complete else ''
        # Top row
        self.title.setText(f'Chapter {title or self.index}{complete_text}')
        if length is None:
            self.length.hide()
        else:
            self.length.setText(f'({length})')
            self.length.show()
        # Second row
        if time is None:
            self.time.hide()
        else:
            self.time.setText(f'🕑 {time}')
            self.time.show()
        if tags is None:
            self.tags.hide()
        else:
            self.tags.setText(', '.join('#' + t for t in sorted(tags)))
            self.tags.show()
        # The rest
        if desc is None:
            self.desc.hide()
        else:
            self.desc.setText(str(desc))
            self.desc.show()
        ziplist: Iterable[Tuple[int, Tuple[Optional[Section],
                                           Optional[SectionItem]]]] \
            = enumerate(zip_longest(sections[1:], self.section_items))
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
        self.toggle(self.expanded)


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
        self.chapter_items: List[ChapterItem] = []
        self.show()

    def load_chapter_data(self, chapters: List[Chapter],
                          update_stylesheet: bool = False,
                          force_refresh: bool = False) -> None:
        self.empty = not bool(chapters[1:])
        ziplist: Iterable[Tuple[int, Tuple[Optional[Chapter],
                                           Optional[ChapterItem]]]] \
            = enumerate(zip_longest(chapters[1:], self.chapter_items))
        for n, (chapter, item) in ziplist:
            if chapter is None:
                if item:
                    item.hide()
            else:
                if item is None:
                    item = ChapterItem(self, n)
                    self.chapter_items.append(item)
                    cast(QtWidgets.QVBoxLayout,
                         self.container.layout()).insertWidget(n, item)
                item.set_data(chapter, update_stylesheet=update_stylesheet,
                              force_refresh=force_refresh)
                item.show()
