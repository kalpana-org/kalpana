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

from typing import Optional
import os.path
import subprocess
import sys

from PyQt5 import QtCore

from kalpana.autocompletion import AutocompletionPattern
from kalpana.common import Command, KalpanaObject
from kalpana.textarea import TextArea


class FileHandler(QtCore.QObject, KalpanaObject):
    """Takes care of saving and opening files."""

    def __init__(self, textarea: TextArea) -> None:
        super().__init__()
        self.textarea = textarea
        self.filepath = None  # type: Optional[str]
        self.kalpana_commands = [
                Command('new-file', 'Create a new file. Filename is optional.',
                        self.new_file),
                Command('new-file-in-new-window',
                        'Create a new file. Filename is optional.',
                        self.new_file_in_new_window),
                Command('open-file', 'Open a file', self.open_file),
                Command('open-file-in-new-window',
                        'Open a file in a new window',
                        self.open_file_in_new_window),
                Command('save-file', 'Save the file', self.save_file),
        ]
        self.kalpana_autocompletion_patterns = [
                AutocompletionPattern(name='new-file',
                                      prefix=r'new-file\s+',
                                      is_file_path=True),
                AutocompletionPattern(name='new-file-in-new-window',
                                      prefix=r'new-file-in-new-window\s+',
                                      is_file_path=True),
                AutocompletionPattern(name='open-file',
                                      prefix=r'open-file\s+',
                                      is_file_path=True),
                AutocompletionPattern(name='open-file-in-new-window',
                                      prefix=r'open-file-in-new-window\s+',
                                      is_file_path=True),
                AutocompletionPattern(name='save-file',
                                      prefix=r'save-file\s+',
                                      is_file_path=True),
        ]

    def load_file_at_startup(self, filepath: str) -> None:
        """
        Initialize the filepath and textarea when the application starts.

        This is a convenience method so you can create a new file with a
        file name from the operating system's terminal or the
        open_file_in_new_window command easily.
        """
        if os.path.exists(filepath):
            self.open_file(filepath)
        else:
            self.new_file(filepath)

    def new_file(self, filepath: str) -> None:
        """
        Clear the textarea and filepath unless there are unsaved changes.

        If filepath is not an empty string, that string is made the active
        filepath, which means you can then use save_file without a filepath
        to save.

        Note that nothing is written to the disk when new_file is run. An
        invalid filepath will only be detected when trying to save.
        """
        if self.textarea.document().isModified():
            self.error('There are unsaved changes')
        elif os.path.exists(filepath):
            self.error('File already exists, open it instead')
        else:
            if filepath:
                self.filepath = filepath
            else:
                self.filepath = None
            self.textarea.setPlainText('')

    def new_file_in_new_window(self, filepath: str) -> None:
        """Open a new file in a new instance of Kalpana."""
        if os.path.exists(filepath):
            self.error('File already exists')
        else:
            subprocess.Popen([sys.executable, sys.argv[0]] +
                             ([filepath] if filepath else []))

    def open_file(self, filepath: str) -> None:
        """
        Open a file, unless there are unsaved changes.

        This will only open files encoded in utf-8 or latin1.
        """
        if self.textarea.document().isModified():
            self.error('There are unsaved changes')
        elif not os.path.isfile(filepath):
            self.error('The path is not a file')
        else:
            for e in ('utf-8', 'latin1'):
                try:
                    with open(filepath, encoding=e) as f:
                        text = f.read()
                except UnicodeDecodeError:
                    continue
                else:
                    self.textarea.setPlainText(text)
                    self.filepath = filepath
                    self.log('File opened')
                    return
            else:
                self.error('Unable to open the file')

    def open_file_in_new_window(self, filepath: str):
        """Open an existing file in a new instance of Kalpana."""
        if not filepath:
            self.error('No file specified')
        else:
            subprocess.Popen([sys.executable, sys.argv[0], filepath])

    def save_file(self, filepath: str) -> None:
        """
        Save the file to the disk.

        If filepath is specified, this works as "save as" works in most
        programs, otherwise it saves over the existing filepath without
        prompting.

        Note that this always saves in utf-8, no matter the original encoding.
        """
        if not filepath and self.filepath is None:
            self.error('No active file')
        elif filepath != self.filepath and os.path.exists(filepath):
            self.error('File already exists')
        else:
            if self.filepath is None:
                file_to_open = filepath
            else:
                file_to_open = self.filepath
            try:
                with open(file_to_open, 'w', encoding='utf-8') as f:
                    f.write(self.textarea.toPlainText())
            except IOError:
                self.error('Unable to save the file')
            else:
                self.filepath = file_to_open
                self.log('File saved')
