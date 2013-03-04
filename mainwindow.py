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
import sys
import subprocess

from PyQt4 import QtCore, QtGui

from libsyntyche import common


class MainWindow(QtGui.QFrame):
    error = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        self.force_quit_flag = False

        self.wordcount = 0
        self.filename = ''
        self.is_modified = False


    def set_is_modified_callback(self, callback):
        self.get_document_is_modified = callback


    def create_ui(self, textarea, terminal):
        # Layout
        vert_layout = QtGui.QVBoxLayout(self)
        common.kill_theming(vert_layout)

        horz_layout = QtGui.QHBoxLayout()
        common.kill_theming(horz_layout)
        vert_layout.addLayout(horz_layout)

        horz_layout.addWidget(textarea)
        vert_layout.addWidget(terminal)

        return vert_layout, horz_layout

    # Override
    def closeEvent(self, event):
        if not self.get_document_is_modified() or self.force_quit_flag:
            event.accept()
        else:
            self.error.emit('Unsaved changes! Force quit with q! or save first.')
            event.ignore()

    def quit(self, force):
        if force:
            self.force_quit_flag = True
            self.close()
        else:
            self.force_quit_flag = False
            self.close()

    # Override
    def dragEnterEvent(self, event):
        # if event.mimeData().hasFormat('text/plain'):
        event.acceptProposedAction()

    # Override
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        parsedurls = []
        for u in urls:
            u = u.path()
            if not os.path.isfile(u) and u.startswith('/'):
                u = u[1:]
            parsedurls.append(u)

        for u in parsedurls:
            subprocess.Popen([sys.executable, sys.argv[0], u])
        event.acceptProposedAction()

    def update_filename(self, filename):
        self.filename = 'New file' if filename == 'NEW' else filename
        self.update_title()

    def update_wordcount(self, wordcount):
        if wordcount != self.wordcount:
            self.wordcount = wordcount
            self.update_title()

    def update_file_modified(self, is_modified):
        self.is_modified = is_modified
        self.update_title()


    def update_title(self):
        title = '{0}{1} - {2}{0}'\
                ''.format('*'*self.is_modified, self.wordcount, self.filename)
        self.setWindowTitle(title)
