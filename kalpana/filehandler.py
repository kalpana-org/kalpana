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

from kalpana.textarea import TextArea


class FileHandler(QtCore.QObject):

    def __init__(self, textarea: TextArea) -> None:
        super().__init__()
        self.textarea = textarea
        self.filepath = None  # type: str

    def new_file(self, filepath: str) -> None:
        if self.textarea.document().isModified():
            print('file is modified!')
            return
        if not filepath:
            self.filepath = None
        else:
            self.filepath = filepath
        self.textarea.setPlainText('')

    def open_file(self, filepath: str) -> None:
        if not os.path.isfile(filepath):
            print('the path is not a file')
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
            print('can\'t open the file')
            return

    def save_file(self, filepath: str) -> None:
        if not filepath:
            if self.filepath is None:
                print('no filename set')
                return
            filepath = self.filepath
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                print('TODO: saving to -> {}'.format(filepath))
            #     f.write(data)
        except IOError:
            print('could not save the file')
