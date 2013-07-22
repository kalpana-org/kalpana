#!/usr/bin/env python3
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
from PyQt4.QtCore import pyqtSignal, Qt

from libsyntyche import common
from mainwindow import MainWindow
from pluginmanager import PluginManager
from settingsmanager import SettingsManager
from terminal import Terminal
from textarea import TextArea


class Kalpana(QtGui.QApplication):
    read_plugin_config = pyqtSignal()
    write_plugin_config = pyqtSignal()

    print_ = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, argv, file_to_open=None):
        super().__init__(argv)

        # Create the objects
        self.mainwindow, self.textarea, self.terminal, self.settings_manager \
            = create_objects()

        # UI
        vert_layout, horz_layout \
            = self.mainwindow.create_ui(self.textarea, self.terminal)

        # Plugins
        self.plugin_manager \
            = PluginManager(vert_layout,horz_layout,
                            self.textarea, self.mainwindow,
                            self.settings_manager)
        self.terminal.update_commands(self.plugin_manager.plugin_commands)

        # Signals
        connect_others_signals(self.mainwindow, self.textarea, self.terminal,
                               self.settings_manager)
        self.connect_own_signals()

        # Hotkeys
        set_key_shortcuts(self.mainwindow, self.textarea, self.terminal,
                          self.plugin_manager.get_compiled_hotkeys())

        self.settings_manager.load_settings()
        self.install_event_filter()

        if file_to_open:
            if not self.textarea.open_file(file_to_open):
                self.close()
        else:
            self.textarea.set_file_name(new=True)

        self.mainwindow.show()


    def install_event_filter(self):
        # Event filter
        class AppEventFilter(QtCore.QObject):
            activation_event = pyqtSignal()
            def eventFilter(self, object, event):
                if event.type() == QtCore.QEvent.ApplicationActivate:
                    self.activation_event.emit()
                return False

        self.event_filter = AppEventFilter()
        def refresh_config():
            self.settings_manager.load_settings(refresh_only=True)
        self.event_filter.activation_event.connect(refresh_config)
        self.installEventFilter(self.event_filter)


    def connect_own_signals(self):
        self.settings_manager.set_stylesheet.connect(self.setStyleSheet)


## === Non-method functions ================================================ ##

def create_objects():
    settings_manager = SettingsManager()
    mainwindow = MainWindow()
    textarea = TextArea(mainwindow, settings_manager.get_setting)
    terminal = Terminal(mainwindow, lambda: textarea.file_path)
    mainwindow.set_is_modified_callback(textarea.document().isModified)
    return mainwindow, textarea, terminal, settings_manager

def set_key_shortcuts(mainwindow, textarea, terminal, plugin_hotkeys):
    hotkeys = {
        'Ctrl+N': textarea.request_new_file,
        'Ctrl+O': lambda:terminal.prompt_command('o'),
        'Ctrl+S': textarea.request_save_file,
        'Ctrl+Shift+S': lambda:terminal.prompt_command('s'),
        'F3': textarea.search_next,
        'Ctrl+Return': terminal.show
    }
    hotkeys.update(plugin_hotkeys)
    for key, function in hotkeys.items():
        common.set_hotkey(key, mainwindow, function)


def connect_others_signals(mainwindow, textarea, terminal, settings_manager):
    """
    "spider" as in "spider in the net"
    """
    connect = (
        # (SIGNAL, SLOT)
        (textarea.wordcount_changed, mainwindow.update_wordcount),
        (textarea.modification_changed, mainwindow.update_file_modified),
        (textarea.filename_changed, mainwindow.update_filename),

        # Print/error/prompt
        (settings_manager.print_, terminal.print_),
        (settings_manager.error, terminal.error),
        (textarea.print_, terminal.print_),
        (textarea.error, terminal.error),
        (textarea.prompt_command, terminal.prompt_command),
        (mainwindow.error, terminal.error),

        # File operations
        (terminal.request_new_file, textarea.request_new_file),
        (terminal.request_save_file, textarea.request_save_file),
        (terminal.request_open_file, textarea.request_open_file),
        (terminal.request_quit, mainwindow.quit),

        # Misc
        (textarea.hide_terminal, terminal.hide),
        (terminal.give_up_focus, textarea.setFocus),
        (terminal.goto_line, textarea.goto_line),
        (terminal.search_and_replace, textarea.search_and_replace),
        (terminal.manage_settings, settings_manager.manage_settings),
        (terminal.reload_theme, settings_manager.set_theme),

        # Settings manager
        (settings_manager.set_number_bar_visibility,
            textarea.set_number_bar_visibility),
        (settings_manager.set_vscrollbar_visibility,
            textarea.setVerticalScrollBarPolicy),
        (settings_manager.set_terminal_command_separator,
            terminal.set_command_separator),
        (settings_manager.switch_focus_to_terminal,
            terminal.show)
    )
    for signal, slot in connect:
        signal.connect(slot)


def get_valid_files():
    output = []
    for f in sys.argv[1:]:
        # try:
        #     f = unicode(f, 'utf-8')
        # except UnicodeDecodeError:
        #     f = unicode(f, 'latin1')
        if os.path.isfile(os.path.abspath(f)):
            output.append(f)
        else:
            print('File not found:')
            print(f)
    return output

def main():
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    files = get_valid_files()

    if not files:
        app = Kalpana(sys.argv)
    else:
        app = Kalpana(sys.argv, files[0])
        for f in files[1:]:
            subprocess.Popen([sys.executable, sys.argv[0], f.encode('utf-8')])

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
