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
import sys
import subprocess

from PyQt4 import QtCore, QtGui

from libsyntyche import common
from common import Configable


class MainWindow(QtGui.QFrame, Configable):
    error = QtCore.pyqtSignal(str)

    def __init__(self, settingsmanager):
        super().__init__()
        self.init_settings_functions(settingsmanager)
        self.register_setting('Show WordCount in titlebar', self.set_show_wordcount)

        self.setAcceptDrops(True)

        self.force_quit_flag = False

        self.wordcount = 0
        self.filename = ''
        self.is_modified = False
        self.show_wordcount = False

        self.textarea = None

    # Ugly as fuck, but eh...
    def set_is_modified_callback(self, callback):
        self.get_document_is_modified = callback

    # ==== Setting callbacks ================================
    def set_show_wordcount(self, value):
        self.show_wordcount = value
        self.update_title()
    # =======================================================

    def create_ui(self, chaptersidebar, textarea, terminal, overview):
        self.textarea = textarea
        self.outer_v_layout = QtGui.QVBoxLayout(self)
        common.kill_theming(self.outer_v_layout)

        self.stack = QtGui.QStackedWidget()
        self.stack.setMaximumWidth(1000)
        #self.outer_v_layout.addLayout(self.stack)
        self.stack.addWidget(textarea)
        self.stack.addWidget(overview)
        self.stack.setCurrentIndex(0)

        self.inner_h_layout = QtGui.QHBoxLayout()
        self.outer_v_layout.addLayout(self.inner_h_layout)
        common.kill_theming(self.inner_h_layout)
        #self.inner_h_layout.setStyleSheet('text-align: center;')

        self.inner_h_layout.addStretch()
        self.inner_h_layout.addWidget(self.stack, stretch=1)
        self.inner_h_layout.addStretch()
        self.inner_h_layout.addWidget(chaptersidebar)
        self.outer_v_layout.addWidget(terminal)

        #common.kill_theming(self.outer_v_layout)

        #self.inner_h_layout = QtGui.QHBoxLayout()
        #common.kill_theming(self.inner_h_layout)
        #self.stack.addLayout(self.inner_h_layout)
        #self.outer_v_layout.addLayout(self.stack)
        ##self.outer_v_layout.addLayout(self.inner_h_layout)
        #self.inner_h_layout.addStretch()
        ##self.inner_h_layout.addWidget(self.stack, stretch=1)
        #self.inner_h_layout.addWidget(textarea, stretch=1)
        #self.inner_h_layout.addStretch()
        #self.inner_h_layout.addWidget(chaptersidebar)
        #self.outer_v_layout.addWidget(terminal)


    def switch_stack_focus(self):
        self.stack.setCurrentIndex(abs(self.stack.currentIndex()-1))
        self.stack.currentWidget().setFocus()
        if self.stack.currentWidget() != self.textarea:
            self.stack.currentWidget().set_data(self.textarea.toPlainText())


    # Override
    def closeEvent(self, event):
        if not self.get_document_is_modified() or self.force_quit_flag:
            event.accept()
        else:
            self.error.emit('Unsaved changes! Force quit with q! or save first.')
            event.ignore()

    def quit(self, force):
        self.force_quit_flag = force
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

    # Override
    def wheelEvent(self, event):
        self.stack.currentWidget().wheelEvent(event)

    def update_filename(self, filename):
        self.filename = filename
        self.update_title()

    def update_wordcount(self, wordcount):
        if wordcount != self.wordcount:
            self.wordcount = wordcount
            self.update_title()

    def update_file_modified(self, is_modified):
        self.is_modified = is_modified
        self.update_title()


    def update_title(self):
        wc = ''
        if self.show_wordcount:
            wc = '{} - '.format(self.wordcount)
        title = '{0}{1}{2}{0}'\
                ''.format('*'*self.is_modified, wc, self.filename)
        self.setWindowTitle(title)
