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

from collections import OrderedDict
import os.path
import sys
import subprocess

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSignal, Qt

from libsyntyche import common
from chaptersidebar import ChapterSidebar
from mainwindow import MainWindow
from overview import Overview
from pluginmanager import PluginManager
from settingsmanager import SettingsManager
from terminal import Terminal
from textarea import TextArea


class Kalpana(QtGui.QApplication):
    read_plugin_config = pyqtSignal()
    write_plugin_config = pyqtSignal()
    print_ = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, configdir, file_to_open=None, silentmode=False):
        super().__init__(['kalpana'])
        self.objects = create_objects(configdir)
        self.objects['mainwindow'].create_ui(self.objects['chaptersidebar'],
                                             self.objects['textarea'],
                                             self.objects['terminal'],
                                             self.objects['overview'])
        # Plugins
        self.pluginmanager = PluginManager(self.objects.copy(), silentmode)
        self.objects['terminal'].update_commands(self.pluginmanager.plugin_commands)
        # Signals
        connect_others_signals(*self.objects.values())
        self.connect_own_signals()
        # Hotkeys
        set_key_shortcuts(self.objects['mainwindow'], self.objects['textarea'],
                          self.objects['terminal'],
                          self.pluginmanager.get_compiled_hotkeys())
        self.init_hotkeys()
        # Load settings and get it oooon
        self.objects['settingsmanager'].load_settings()
        self.install_event_filter()
        # Try to open a file and die if it doesn't work, or make a new file
        if file_to_open:
            if os.path.exists(file_to_open):
                if not self.objects['textarea'].open_file(file_to_open):
                    print('Bad encoding! Use utf-8 or latin1.')
                    self.close()
            else:
                # If the path doesn't exist, open a new file with the name
                self.objects['textarea'].document().setModified(True)
                self.objects['textarea'].set_filename(file_to_open)
        else:
            self.objects['textarea'].set_filename(new=True)
            self.objects['textarea'].document().setModified(True)
        # FIN
        self.objects['overview'].set_data(self.objects['textarea'].toPlainText())

        self.objects['mainwindow'].show()

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
            self.objects['settingsmanager'].load_settings(refresh_only=True)
            #TODO: this is only temporary
            self.objects['overview'].refresh_stuff()
        self.event_filter.activation_event.connect(refresh_config)
        self.installEventFilter(self.event_filter)

    def connect_own_signals(self):
        self.objects['settingsmanager'].set_stylesheet.connect(self.setStyleSheet)
        self.objects['terminal'].list_plugins.connect(self.list_plugins)

    def list_plugins(self, _):
        plugins = self.pluginmanager.plugins
        self.objects['terminal'].print_(', '.join(name for name, p in plugins))

    # === Configurable hotkeys =========================================

    def init_hotkeys(self):
        l = (('terminal', self.objects['terminal'].toggle, self.set_terminal_hotkey),
             ('chapter sidebar', self.objects['chaptersidebar'].toggle, self.set_chaptersidebar_hotkey))
        self.hotkeys = {name: QtGui.QShortcut(QtGui.QKeySequence(''),
                                              self.objects['mainwindow'],
                                              callback)
                        for name, callback, _ in l}
        for n, _, callback in l:
            self.objects['settingsmanager'].register_setting(n + ' hotkey', callback)

    def set_terminal_hotkey(self, newkey):
        self.set_hotkey('terminal', newkey)

    def set_chaptersidebar_hotkey(self, newkey):
        self.set_hotkey('chapter sidebar', newkey)

    def set_hotkey(self, hotkey, newkey):
        self.hotkeys[hotkey].setKey(QtGui.QKeySequence(newkey))


## === Non-method functions ================================================ ##

def create_objects(configdir):
    smgr = SettingsManager(configdir)
    mw = MainWindow(smgr)
    txta = TextArea(mw, smgr)
    overview = Overview(mw, smgr)
    chsb = ChapterSidebar(smgr, txta.toPlainText, txta.textCursor)
    term = Terminal(mw, smgr, lambda: txta.file_path)
    # Ugly shit
    mw.set_is_modified_callback(txta.document().isModified)
    return OrderedDict((('chaptersidebar', chsb),
                        ('mainwindow', mw),
                        ('settingsmanager', smgr),
                        ('terminal', term),
                        ('textarea', txta),
                        ('overview', overview)))

def set_key_shortcuts(mainwindow, textarea, terminal, plugin_hotkeys):
    hotkeys = {
        'Ctrl+N': textarea.request_new_file,
        'Ctrl+O': lambda:terminal.prompt('o '),
        'Ctrl+S': textarea.request_save_file,
        'Ctrl+Shift+S': lambda:terminal.prompt('s '),
        'F3': textarea.search_next,
        'F9': mainwindow.switch_stack_focus,
    }
    hotkeys.update(plugin_hotkeys)
    for key, function in hotkeys.items():
        common.set_hotkey(key, mainwindow, function)

def connect_others_signals(chaptersidebar, mainwindow, settingsmanager, terminal, textarea, overview):
    connect = (
        # (SIGNAL, SLOT)
        (textarea.wordcount_changed, mainwindow.update_wordcount),
        (textarea.modificationChanged, mainwindow.update_file_modified),
        (textarea.filename_changed, mainwindow.update_filename),
        (textarea.cursor_position_changed, chaptersidebar.update_active_chapter),
        (chaptersidebar.goto_line, textarea.goto_line),

        # Print/error/prompt
        (settingsmanager.print_, terminal.print_),
        (settingsmanager.error, terminal.error),
        (textarea.print_sig, terminal.print_),
        (textarea.error_sig, terminal.error),
        (textarea.prompt_sig, terminal.prompt),
        (mainwindow.error, terminal.error),
        (chaptersidebar.error, terminal.error),

        (terminal.shake, textarea.shake),

        # File operations
        (terminal.request_new_file, textarea.request_new_file),
        (terminal.request_save_file, textarea.request_save_file),
        (terminal.request_open_file, textarea.request_open_file),
        (terminal.request_quit, mainwindow.quit),

        # Misc
        (textarea.hide_terminal, terminal.hide),
        (terminal.give_up_focus, textarea.setFocus),
        (terminal.goto_line, chaptersidebar.goto_line_or_chapter),
        (terminal.count_words, textarea.print_wordcount),
        (terminal.search_and_replace, textarea.search_and_replace),
        (terminal.manage_settings, settingsmanager.change_setting),
        (terminal.print_filename, textarea.print_filename),
        (terminal.spellcheck, textarea.spellcheck),
        (terminal.set_stylefile, settingsmanager.set_stylefile),
        (textarea.update_recent_files, terminal.update_recent_files),

        # Settings manager
        (settingsmanager.switch_focus_to_terminal, terminal.show)
    )
    for signal, slot in connect:
        signal.connect(slot)


def main():
    import argparse
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    parser = argparse.ArgumentParser()

    def valid_dir(dirname):
        if os.path.isdir(dirname):
            return dirname
        parser.error('Directory does not exist: {}'.format(dirname))

    parser.add_argument('-c', '--config-directory', type=valid_dir)
    parser.add_argument('-s', '--silent-mode', action='store_true',
                        help="hide non-error messages in the OS's terminal")
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()

    if not args.files:
        app = Kalpana(args.config_directory, silentmode=args.silent_mode)
    else:
        app = Kalpana(args.config_directory, file_to_open=args.files[0], silentmode=args.silent_mode)
        for f in args.files[1:]:
            if args.silent_mode:
                subprocess.Popen([sys.executable, sys.argv[0], '-s', f.encode('utf-8')])
            else:
                subprocess.Popen([sys.executable, sys.argv[0], f.encode('utf-8')])

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
