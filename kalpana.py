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

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QEvent

from kalpana.textarea import TextArea
from kalpana.terminal import Terminal
from kalpana.controller import Controller
from kalpana.mainwindow import MainWindow


class Kalpana(QtGui.QApplication):

    def __init__(self, config_dir, silent_mode=False, file_to_open=None):
        super().__init__(['kalpana2'])
        self.mainwindow = MainWindow()
        self.textarea = TextArea(self.mainwindow)
        self.terminal = Terminal(self.mainwindow)
        self.mainwindow.set_terminal(self.terminal)
        self.mainwindow.add_stack_widgets([self.textarea])
        self.controller = Controller(self.mainwindow,
                                     self.textarea,
                                     self.terminal)
        # # Layout
        # layout.addWidget(self.textarea)
        # layout.addWidget(self.terminal)
        # # Misc
        # self.watch_terminal()
        # self.termkey = QtGui.QShortcut(QtGui.QKeySequence('Escape'), self, self.toggle_terminal)

        if file_to_open:
            self.controller.load_file(file_to_open)

    def toggle_terminal(self):
        pass


def main():
    import argparse
    import subprocess
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-directory')
    parser.add_argument('-s', '--silent-mode', action='store_true',
                        help="hide non-error messages in the OS's terminal")
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()
    if not args.files:
        app = Kalpana(args.config_directory, silent_mode=args.silent_mode)
    else:
        app = Kalpana(args.config_directory, file_to_open=args.files[0],
                      silent_mode=args.silent_mode)
        for f in args.files[1:]:
            if args.silent_mode:
                subprocess.Popen([sys.executable, sys.argv[0], '-s', f.encode('utf-8')])
            else:
                subprocess.Popen([sys.executable, sys.argv[0], f.encode('utf-8')])
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
