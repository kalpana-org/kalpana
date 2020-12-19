#!/usr/bin/env python3
# Copyright nycz 2011-2020

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

import logging
from pathlib import Path
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from .controller import Controller
from .mainwindow import MainWindow
from .settings import Settings


class Kalpana(QtWidgets.QApplication):

    def __init__(self, config_dir: Optional[str],
                 silent_mode: bool = False,
                 file_to_open: Optional[str] = None) -> None:
        super().__init__(['kalpana2'])
        self.settings = Settings(Path(config_dir) if config_dir else None)
        self.mainwindow = MainWindow()
        self.controller = Controller(self.mainwindow, self.settings)
        self.make_event_filter()
        self.settings.css_changed.connect(self.setStyleSheet)
        self.settings.reload_settings()
        self.settings.reload_stylesheet()
        if file_to_open:
            self.controller.filehandler.load_file_at_startup(file_to_open)
        self.controller.init_done()

    def make_event_filter(self) -> None:
        class MainWindowEventFilter(QtCore.QObject):
            def eventFilter(self_, obj: QtCore.QObject,
                            event: QtCore.QEvent) -> bool:
                if event.type() == QtCore.QEvent.Close:
                    self.settings.save_settings()
                return False
        self.close_filter = MainWindowEventFilter()
        self.mainwindow.installEventFilter(self.close_filter)


def main() -> None:
    import argparse
    import subprocess
    import sys
    logging.basicConfig(format='%(asctime)s - %(name)s - '
                               '%(levelname)s - %(msg)s')
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
                subprocess.Popen([sys.executable, sys.argv[0],
                                  '-s', f.encode('utf-8')])
            else:
                subprocess.Popen([sys.executable, sys.argv[0],
                                  f.encode('utf-8')])
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
