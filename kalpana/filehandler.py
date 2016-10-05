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

from PyQt5 import QtCore, QtGui

class FileError(Exception):
    pass


class FileHandler(QtCore.QObject):

    def __init__(self):
        super().__init__()
        self.filepath = None

    def open_file(self, filepath: str) -> str:
        if not os.path.isfile(filepath):
            raise FileError('the path is not a file')
        for e in ('utf-8', 'latin1'):
            try:
                with open(filepath, encoding=e) as f:
                    text = f.read()
            except UnicodeDecodeError:
                continue
            else:
                return text
        raise FileError('unknown encoding')

    def save_file(self, data: str, filepath: str = None) -> None:
        if filepath is None:
            filepath = self.filepath
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
