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

from typing import Callable, List, Tuple
import re

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QEvent, pyqtSignal

from kalpana.chapters import ChapterIndex
from kalpana.filehandler import FileHandler, FileError
from kalpana.mainwindow import MainWindow
from kalpana.terminal import Terminal, Command, autocomplete_file_path
from kalpana.textarea import TextArea


class Controller:
    def __init__(self, mainwindow: MainWindow, textarea: TextArea, terminal: Terminal) -> None:
        self.mainwindow = mainwindow
        self.textarea = textarea
        self.terminal = terminal
        self.filehandler = FileHandler()
        self.chapter_index = ChapterIndex()
        self.set_hotkeys()
        self.connect_signals()
        self.register_commands()

    def set_hotkeys(self) -> None:
        self.termkey = QtWidgets.QShortcut(QtGui.QKeySequence('Escape'),
                                           self.mainwindow, self.toggle_terminal)

    def update_style(self) -> None:
        pass

    def register_commands(self):
        commands = [
                Command('open-file', '', self.load_file),
                Command('new-file', '', self.new_file),
                Command('go-to-line', '', self.go_to_line),
                Command('go-to-chapter', '', self.go_to_chapter),
                Command('go-to-next-chapter', '', self.go_to_next_chapter,
                        accept_args=False),
                Command('go-to-prev-chapter', '', self.go_to_prev_chapter,
                        accept_args=False),
                Command('word-count-total', '', self.count_total_words,
                        accept_args=False),
                Command('set-textarea-max-width', '', self.set_textarea_max_width),
        ]
        self.terminal.register_commands(commands)

    def connect_signals(self) -> None:
        pairs = [
            (self.textarea.textChanged, self.update_chapter_index),
            (self.terminal.error_triggered, self.mainwindow.shake_screen),
        ]  # type: List[Tuple[pyqtSignal, Callable]]
        for signal, slot in pairs:
            signal.connect(slot)

    def toggle_terminal(self) -> None:
        if self.terminal.input_field.hasFocus():
            if self.terminal.completer_popup.isVisible():
                self.terminal.completer_popup.hide()
            else:
                self.mainwindow.setFocus()
        else:
            self.terminal.input_field.setFocus()

    def update_chapter_index(self) -> None:
        self.chapter_index.parse_document(self.textarea.toPlainText())

    # def update_text_format(self, pos: int, removed: int, added: int) -> None:
    #     print(self.textarea.toPlainText()[pos:pos+added])

    def set_text_block_formats(self) -> None:
        def make_format(alpha: float = 1, bold: bool = False,
                        size: float = None) -> QtGui.QTextCharFormat:
            char_format = QtGui.QTextCharFormat()
            if bold:
                char_format.setFontWeight(QtGui.QFont.Bold)
            if size:
                char_format.setFontPointSize(size)
            if alpha < 1:
                col = self.textarea.palette().windowText().color()
                col.setAlphaF(alpha)
                char_format.setForeground(QtGui.QBrush(col))
            return char_format
        def set_line_format(line_number: int, format_: QtGui.QTextCharFormat) -> None:
            block = QtGui.QTextCursor(self.textarea.document().findBlockByNumber(line_number))
            block.select(QtGui.QTextCursor.BlockUnderCursor)
            block.setCharFormat(format_)
        chapter_format = make_format(bold=True, size=16)
        metadata_format = make_format(alpha=0.3)
        section_format = make_format(alpha=0.5, bold=True)
        chapter_data = self.chapter_index.chapters
        pos = 0
        self.textarea.setUndoRedoEnabled(False)
        for chapter in chapter_data:
            if chapter.title:
                set_line_format(pos, chapter_format)
                pos += 1
            for line_num in range(1, chapter.metadata_line_count):
                set_line_format(pos, metadata_format)
                pos += 1
            for section in chapter.sections:
                if section.desc:
                    set_line_format(pos, section_format)
                pos += section.line_count
        self.textarea.setUndoRedoEnabled(True)

    # =========== COMMANDS ================================

    def load_file(self, filepath: str) -> None:
        try:
            data = self.filehandler.open_file(filepath)
        except FileError as e:
            self.terminal.error(e.args[0])
        else:
            self.textarea.setPlainText(data)
            # self.chapter_index.parse_document(self.textarea.toPlainText())
            # x = ChapterIndex()
            # x.parse_document(self.textarea.toPlainText())
            # self.set_text_block_formats()
            # self.textarea.document().contentsChange.connect(self.update_text_format)

    def new_file(self, arg) -> None:
        self.textarea.setPlainText('')

    def go_to_line(self, arg: str) -> None:
        if not arg.isdecimal():
            self.terminal.error('Argument has to be a number!')
        else:
            line_num = min(int(arg), self.textarea.document().blockCount())
            self.textarea.center_on_line(line_num)

    def go_to_chapter(self, arg: str) -> None:
        if not self.chapter_index.chapters:
            self.terminal.error('No chapters detected!')
        elif not arg.isdecimal():
            # TODO: negative values for last chapter, 2nd last, etc
            self.terminal.error('Argument has to be a number!')
        elif int(arg) > len(self.chapter_index.chapters):
            self.terminal.error('Invalid chapter!')
        else:
            line_num = self.chapter_index.get_chapter_line(int(arg))
            self.textarea.center_on_line(line_num)

    def go_to_next_chapter(self) -> None:
        self.go_to_chapter_incremental(1)

    def go_to_prev_chapter(self) -> None:
        self.go_to_chapter_incremental(-1)

    def go_to_chapter_incremental(self, diff: int) -> None:
        """
        Move to a chapter a number of chapters from the current.

        diff - How many chapters to move, negative to move backwards.
        """
        current_line = self.textarea.textCursor().blockNumber()
        current_chapter = self.chapter_index.which_chapter(current_line)
        target_chapter = max(0, min(len(self.chapter_index.chapters)-1, current_chapter+diff))
        if current_chapter != target_chapter:
            line = self.chapter_index.get_chapter_line(target_chapter)
            self.textarea.center_on_line(line)

    def count_total_words(self):
        words = len(re.findall(r'\S+', self.textarea.document().toPlainText()))
        self.terminal.print_('Total words: {}'.format(words))

    def set_textarea_max_width(self, arg: str) -> None:
        if not arg.isdecimal():
            self.terminal.error('Argument has to be a number!')
            return
        elif int(arg) < 1:
            self.terminal.error('Width has to be at least 1!')
            return
        self.textarea.setMaximumWidth(int(arg))
        self.terminal.print_('Max textarea width set to {} px'.format(arg))
