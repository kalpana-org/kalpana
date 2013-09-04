# Copyright nycz 2011-2013

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

import os.path
import re
import subprocess
import sys

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSignal

from libsyntyche.common import write_file
from linewidget import LineTextWidget


class TextArea(LineTextWidget):
    print_ = pyqtSignal(str)
    error = pyqtSignal(str)
    hide_terminal = pyqtSignal()
    prompt_command = pyqtSignal(str)
    wordcount_changed = pyqtSignal(int)
    modification_changed = pyqtSignal(bool)
    filename_changed = pyqtSignal(str)
    file_saved = pyqtSignal()

    def __init__(self, parent, get_settings):
        super().__init__(parent)
        self.get_settings = get_settings

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setTabStopWidth(30)
        self.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

        def modified_slot(is_modified):
            self.modification_changed.emit(is_modified)
        self.document().modificationChanged.connect(modified_slot)
        self.document().contentsChanged.connect(self.contents_changed)
        self.document().blockCountChanged.connect(self.new_line)

        self.search_buffer = None
        self.replace_buffer = None

        self.file_path = ''

    def get_wordcount(self):
        return len(re.findall(r'\S+', self.document().toPlainText()))

    def print_wordcount(self):
        self.print_.emit('Words: {}'.format(self.get_wordcount()))

    def contents_changed(self):
        self.wordcount_changed.emit(self.get_wordcount())


    def goto_line(self, raw_line_num):
        if type(raw_line_num) == str:
            if not raw_line_num.strip().isdigit():
                self.error.emit('Invalid line number')
                return
            raw_line_num = int(raw_line_num.strip())
        line_num = min(raw_line_num, self.document().blockCount())
        block = self.document().findBlockByNumber(line_num - 1)
        new_cursor = QtGui.QTextCursor(block)
        self.setTextCursor(new_cursor)
        self.centerCursor()
        self.hide_terminal.emit()
        self.setFocus()


    def new_line(self, blocks):
        """ Generate auto-indentation if the option is enabled. """
        if self.get_settings('ai'):
            cursor = self.textCursor()
            blocknum = cursor.blockNumber()
            prevblock = self.document().findBlockByNumber(blocknum-1)
            indent = re.match(r'[\t ]*', prevblock.text()).group(0)
            cursor.insertText(indent)


    ## ==== Save & replace ================================================ ##

    def search_and_replace(self, arg):
        search_rx = re.compile(r'([^/]|\\/)+$')
        replace_rx = re.compile(r"""
            (?P<search>([^/]|\\/)*?[^\\])
            /
            (?P<replace>(([^/]|\\/)*[^\\])?)
            /
            (?P<flags>[ai]*)
            $
        """, re.VERBOSE)
        replace_append_rx = re.compile(r"""
            /
            (?P<replace>(([^/]|\\/)*[^\\])?)
            /
            (?P<flags>[ai]*)
            $
        """, re.VERBOSE)

        if not arg:
            self.search_next()

        elif arg == '/':
            self.replace_next()

        elif search_rx.match(arg):
            self.search_buffer = search_rx.match(arg).group(0)
            self.replace_buffer = None
            self.search_next()

        elif replace_append_rx.match(arg):
            if self.search_buffer is None:
                self.error.emit('No previous searches')
                return
            match = replace_append_rx.match(arg)
            self.replace_buffer = match.group('replace')
            if 'a' in match.group('flags'):
                self.replace_all()
            else:
                self.replace_next()

        elif replace_rx.match(arg):
            match = replace_rx.match(arg)
            self.search_buffer = match.group('search')
            self.replace_buffer = match.group('replace')
            if 'a' in match.group('flags'):
                self.replace_all()
            else:
                self.replace_next()

        else:
            self.error.emit('Malformed search/replace expression')


    def search_next(self):
        if self.search_buffer is None:
            self.error.emit("No previous searches")
            return
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer)
        if not found:
            if not self.textCursor().atStart():
                self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer)
                if not found:
                    self.setTextCursor(temp_cursor)
                    self.error.emit('Text not found')


    def replace_next(self):
        if self.replace_buffer is None:
            self.error.emit("Nothing to replace with")
            return

        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer)
        if not found:
            if not self.textCursor().atStart():
                self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer)
                if not found:
                    self.setTextCursor(temp_cursor)
        if found:
            t = self.textCursor()
            t.insertText(self.replace_buffer)
            l = len(self.replace_buffer)
            t.setPosition(t.position() - l)
            t.setPosition(t.position() + l, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(t)
            self.print_.emit('Replaced on line {}, pos {}'
                             ''.format(t.blockNumber(), t.positionInBlock()))
        else:
            self.error.emit('Text not found')


    def replace_all(self):
        if self.replace_buffer is None:
            self.error.emit("No previous replaces")
            return

        temp_cursor = self.textCursor()
        times = 0
        while True:
            found = self.find(self.search_buffer)
            if found:
                self.textCursor().insertText(self.replace_buffer)
                times += 1
            else:
                if self.textCursor().atStart():
                    break
                else:
                    self.moveCursor(QtGui.QTextCursor.Start)
                    continue
        if times:
            self.print_.emit('{0} instance{1} replaced'.format(times,
                                                            's'*(times>0)))
        else:
            self.setTextCursor(temp_cursor)
            self.error.emit('Text not found')


    ## ==== File ops help functions ======================================= ##

    def new_and_empty(self):
        """ Return True if the file is empty and unsaved. """
        return not self.document().isModified() and not self.file_path


    def set_file_name(self, filename='', new=False):
        """ Set both the output file and the title to filename. """
        assert bool(filename) != new # Either a filename or new, not both/none
        self.file_path = '' if new else filename
        self.filename_changed.emit('New file' if new else filename)


    ## ==== File operations: new/open/save ================================ ##

    def request_new_file(self, force=False):
        success = self.new_file(force)
        if not success:
            self.error.emit('Unsaved changes! Force new with n! or save first.')


    def request_open_file(self, filename, force=False):
        if not os.path.isfile(filename):
            self.error.emit('File not found!')
            return
        if self.get_settings('nw') and not self.new_and_empty():
            subprocess.Popen([sys.executable, sys.argv[0], filename])
        elif not self.document().isModified() or force:
            success = self.open_file(filename)
            if not success:
                self.error.emit('File could not be decoded!')
        else:
            self.error.emit('Unsaved changes! Force open with o! or save first.')


    def request_save_file(self, filename='', force=False):
        if not filename:
            if self.file_path:
                result = self.save_file()
                if not result:
                    self.error.emit('File not saved! IOError!')
            else:
                self.error.emit('No filename')
                self.prompt_command.emit('s')
        else:
            if os.path.isfile(filename) and not force:
                self.error.emit('File already exists, use s! to overwrite')
            # Make sure the parent directory actually exists
            elif os.path.isdir(os.path.dirname(filename)):
                result = self.save_file(filename)
                if not result:
                    self.error.emit('File not saved! IOError!')
            else:
                self.error.emit('Invalid path')


    def new_file(self, force=False):
        """
        Main new file function
        """
        if self.get_settings('nw') and not self.new_and_empty():
            subprocess.Popen([sys.executable, sys.argv[0]])
            return True
        elif not self.document().isModified() or force:
            self.document().clear()
            self.document().setModified(False)
            self.set_file_name(new=True)
            return True
        else:
            return False


    def open_file(self, filename):
        """
        Main open file function
        """
        encodings = ('utf-8', 'latin1')
        for e in encodings:
            try:
                with open(filename, encoding=e) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                continue
            else:
                self.document().setPlainText(''.join(lines))
                self.document().setModified(False)
                self.set_file_name(filename)
                self.moveCursor(QtGui.QTextCursor.Start)
                return True
        return False


    def save_file(self, filename=''):
        """
        Main save file function

        Save the file with the specified filename.
        If no filename is provided, save the file with the existing filename,
        (aka don't save as, just save normally)
        """
        if filename:
            savefname = filename
        else:
            savefname = self.file_path

        assert savefname.strip() != ''

        try:
            write_file(savefname, self.document().toPlainText())
        except IOError as e:
            print(e)
            return False
        else:
            self.set_file_name(savefname)
            self.document().setModified(False)
            self.file_saved.emit()
            return True
