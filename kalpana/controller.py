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

import re

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QEvent, pyqtSignal

from kalpana.filehandler import FileHandler, FileError
from kalpana.chapters import ChapterIndex


class Controller:
    def __init__(self, mainwindow, textarea, terminal):
        self.mainwindow = mainwindow
        self.textarea = textarea
        self.terminal = terminal
        self.filehandler = FileHandler()
        self.chapter_index = ChapterIndex()
        self.set_hotkeys()
        self.connect_signals()

    def set_hotkeys(self):
        self.termkey = QtWidgets.QShortcut(QtGui.QKeySequence('Escape'),
                                           self.mainwindow, self.toggle_terminal)
        self.termkey = QtWidgets.QShortcut(QtGui.QKeySequence('F9'),
                                           self.mainwindow, self.test)

    def update_style(self):
        pass

    def test(self):
        print('mw:', self.mainwindow.width())
        print('stack:', self.mainwindow.stack.width())
        print('textarea:', self.textarea.width())
        sp = self.textarea.sizePolicy()
        print('ta sizepolicy', sp.controlType(), sp.horizontalPolicy())

    def connect_signals(self):
        pairs = (
            (self.terminal.run_command, self.run_command),
            (self.terminal.error_triggered, self.mainwindow.shake_screen),
        )
        for signal, slot in pairs:
            signal.connect(slot)

    def toggle_terminal(self):
        if self.terminal.input_field.hasFocus():
            if self.terminal.completer_popup.isVisible():
                self.terminal.completer_popup.hide()
            else:
                self.mainwindow.setFocus()
        else:
            self.terminal.input_field.setFocus()

    def load_file(self, filepath):
        try:
            data = self.filehandler.open_file(filepath)
        except FileError as e:
            self.terminal.error(e.args[0])
        else:
            self.textarea.setPlainText(data)
            self.chapter_index.parse_document(self.textarea.toPlainText())
            # x = ChapterIndex()
            # x.parse_document(self.textarea.toPlainText())
            self.set_text_block_formats()
            self.textarea.document().contentsChange.connect(self.update_text_format)

            # print(x.chapters[0])
            # print(self.chapter_index.chapters[0])
            # print(x == self.chapter_index)
            # print(*[c.title for c in self.chapter_index.chapters], sep='\n')

    def update_text_format(self, pos, removed, added):
        print(self.textarea.toPlainText()[pos:pos+added])

    def set_text_block_formats(self):
        def make_format(alpha=1, bold=False, size=None):
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
        def set_line_format(line_number, format_):
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

    def watch_terminal(self):
        class EventFilter(QtCore.QObject):
            def eventFilter(self_, obj, ev):
                if ev.type() == QEvent.KeyPress:
                    if ev.key() == Qt.Key_Backtab and ev.modifiers() == Qt.ShiftModifier:
                        return True
                    elif ev.key() == Qt.Key_Tab and ev.modifiers() == Qt.NoModifier:
                        return True
                return False
        self.term_event_filter = EventFilter()
        self.terminal.input_field.installEventFilter(self.term_event_filter)

    def run_command(self, cmd, arg):
        # File handling
        if cmd == 'open-file':
            self.load_file(arg)
        # Word count
        elif cmd == 'word-count-total':
            self.count_words('total', arg)
        elif cmd == 'word-count-chapter':
            self.count_words('chapter', arg)
        elif cmd == 'word-count-selection':
            self.count_words('selection', arg)
        # Go to position
        elif cmd == 'go-to-line':
            self.go_to_position('line', arg)
        elif cmd == 'go-to-chapter':
            self.go_to_position('chapter', arg)
        # Set textarea max width
        elif cmd == 'set-textarea-max-width':
            self.set_textarea_max_width(arg)

    def count_words(self, mode, arg):
        if mode == 'total':
            if arg:
                self.terminal.error('Too many arguments!')
                return
            words = len(re.findall(r'\S+', self.textarea.document().toPlainText()))
            self.terminal.print_('Total words: {}'.format(words))
        elif mode == 'chapter':
            self.terminal.error('No chapters detected!')
        elif mode == 'selection':
            self.terminal.error('Not implented yet!')

    def go_to_position(self, mode, arg):
        if not arg.isdecimal():
            # TODO: add negative numbers for last chapter etc
            self.terminal.error('Argument has to be a number!')
            return
        if mode == 'line':
            line_num = min(int(arg), self.textarea.document().blockCount())
            block = self.textarea.document().findBlockByNumber(line_num - 1)
            new_cursor = QtGui.QTextCursor(block)
            self.textarea.setTextCursor(new_cursor)
            self.textarea.centerCursor()
        elif mode == 'chapter':
            self.terminal.error('Not implented yet!')

    def set_textarea_max_width(self, arg):
        if not arg.isdecimal():
            self.terminal.error('Argument has to be a number!')
            return
        elif int(arg) < 1:
            self.terminal.error('Width has to be at least 1!')
            return
        self.textarea.setMaximumWidth(int(arg))
        self.terminal.print_('Max textarea width set to {} px'.format(arg))
