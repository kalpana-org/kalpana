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

import os.path

from PyQt5 import QtCore

from kalpana.autocompletion import AutocompletionPattern
from kalpana.common import Command, KalpanaObject
from kalpana.textarea import TextArea


class FileHandler(QtCore.QObject, KalpanaObject):
    """Takes care of saving and opening files."""

    def __init__(self, textarea: TextArea) -> None:
        super().__init__()
        self.textarea = textarea
        self.filepath = None  # type: str
        self.kalpana_commands = [
                Command('new-file', 'Create a new file. Filename is optional.',
                        self.new_file),
                Command('open-file', 'Open a file', self.open_file),
                Command('save-file', 'Save the file', self.save_file),
        ]
        self.kalpana_autocompletion_patterns = [
                AutocompletionPattern(name='new-file',
                                      prefix=r'new-file\s+',
                                      is_file_path=True),
                AutocompletionPattern(name='open-file',
                                      prefix=r'open-file\s+',
                                      is_file_path=True),
                AutocompletionPattern(name='save-file',
                                      prefix=r'save-file\s+',
                                      is_file_path=True),
        ]

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
            return
        if not filepath:
            self.filepath = None
        else:
            self.filepath = filepath
        self.textarea.setPlainText('')

    def open_file(self, filepath: str) -> None:
        """
        Open a file, unless there are unsaved changes.
        """
        if not os.path.isfile(filepath):
            self.error('The path is not a file')
            return
        for e in ('utf-8', 'latin1'):
            try:
                with open(filepath, encoding=e) as f:
                    text = f.read()
            except UnicodeDecodeError:
                continue
            else:
                self.textarea.setPlainText(text)
                self.filepath = filepath
                break
        else:
            self.error('Unable to open the file')
            return

    def save_file(self, filepath: str) -> None:
        if not filepath:
            if self.filepath is None:
                self.error('No active file')
                return
            filepath = self.filepath
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.log('TODO: saving to -> {}'.format(filepath))
            #     f.write(data)
        except IOError:
            self.error('Unable to save the file')
