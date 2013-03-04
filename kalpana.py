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
from os.path import join
import re
import sys
import subprocess

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSignal, Qt

import configlib
from libsyntyche import common
from loadorderdialog import LoadOrderDialog
from mainwindow import MainWindow
from terminal import Terminal
from textarea import TextArea


class Kalpana(QtGui.QApplication):
    read_plugin_config = pyqtSignal()
    write_plugin_config = pyqtSignal()

    print_ = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, argv, file_to_open=None):
        super().__init__(argv)

        # Event filter
        class AppEventFilter(QtCore.QObject):
            activation_event = pyqtSignal()
            def eventFilter(self, object, event):
                if event.type() == QtCore.QEvent.ApplicationActivate:
                    self.activation_event.emit()
                return False

        self.event_filter = AppEventFilter()
        def refresh_config():
            self.load_settings(self.config_file_path)
        self.event_filter.activation_event.connect(refresh_config)
        self.installEventFilter(self.event_filter)

        # Gotta create the settings here (see create_objects)
        self.settings = {}

        # Paths
        self.config_file_path, self.config_dir, \
        self.theme_path, self.loadorder_path \
            = configlib.get_paths()

        # Create the objects
        self.mainwindow, self.textarea, self.terminal \
            = create_objects(self.settings)

        # UI
        vert_layout, horz_layout \
            = self.mainwindow.create_ui(self.textarea, self.terminal)

        # Plugins
        self.plugins, plugin_commands \
            = init_plugins(self.config_dir, vert_layout, horz_layout,
                           self.textarea, self.mainwindow,
                           self.read_plugin_config, self.write_plugin_config)
        self.terminal.update_commands(plugin_commands)

        connect_others_signals(self.mainwindow, self.textarea, self.terminal)
        self.connect_own_signals()
        set_key_shortcuts(self.mainwindow, self.textarea, self.terminal,
                                  self.plugins)
        self.load_settings(self.config_file_path)

        if file_to_open:
            if not self.textarea.open_file(file_to_open):
                self.close()
        else:
            self.textarea.set_file_name('NEW')

        self.mainwindow.show()


    def connect_own_signals(self):
        self.print_.connect(self.terminal.print_)
        self.error.connect(self.terminal.error)
        def open_loadorder_dialog():
            LoadOrderDialog(self, self.loadorder_path).exec_()
        self.terminal.open_loadorder_dialog.connect(open_loadorder_dialog)
        self.terminal.reload_theme.connect(self.set_theme)
        self.terminal.manage_settings.connect(self.manage_settings)


# ===================== SETTINGS =========================================== #

    def load_settings(self, config_file_path, refresh_only=False):
        """
        Load settings from the main config file.
        """
        default_config_path = common.local_path('defaultcfg.json')
        settings_dict = configlib.read_config(config_file_path, default_config_path)

        loaded_settings = settings_dict['settings']
        self.allowed_setting_values = settings_dict['legal_values']
        self.setting_names = settings_dict['acronyms']

        if loaded_settings['start_in_term'] and not refresh_only:
            self.terminal.setVisible(True)
            self.terminal.input_term.setFocus()

        for key, value in loaded_settings.items():
            self.set_setting(key, value, quiet=True)

        # Make sure any potential corrected errors are saved
        self.save_settings()

        self.read_plugin_config.emit()
        self.set_theme()


    def manage_settings(self, argument):
        """
        Called from terminal.
        Allowed value for argument:
            <setting acronym> [<new value>]

        If new value is not specified, print current and allowed values
        for the specified setting.
        Otherwise set the setting to the new value.

        Print relevant error if value is not allowed, acronym does not exist,
        or the structure of argument does not follow above specification.
        """
        if not argument.strip():
            self.print_.emit('Settings: {}'\
                             .format(', '.join(sorted(self.setting_names))))
            return

        arg_rx = re.compile(r"""
            (?P<setting>\S+)
            (
                \ +
                (?P<value>.+?)
            )?
            \s*
            $
        """, re.VERBOSE)
        parsed_arg = arg_rx.match(argument)
        acronym = parsed_arg.group('setting')
        if acronym not in self.setting_names:
            self.error.emit('No such setting: {}'.format(acronym))
            return
        name = self.setting_names[acronym]

        # Set new value if there is one
        if parsed_arg.group('value'):
            new_value = parsed_arg.group('value')
            success = self.set_setting(name, new_value)
            if success:
                self.save_settings()
        # Otherwise just print the current value
        else:
            value = self.settings[name]
            self.print_.emit('{} = {} ({})'.format(name, value,
                ', '.join([str(x) for x in self.allowed_setting_values[name]])))


    def set_setting(self, key, new_value, quiet=False):
        """
        Set the value of a setting the the specified new value.

        key is the name of the setting.
        new_value is the new value.
        quiet means only errors will be printed.
        """
        # TODO: this needs to be better
        if isinstance(new_value, str):
            if new_value.lower() in ('n', 'false'):
                new_value = False
            elif new_value.lower() in ('y', 'true'):
                new_value = True

        if len(self.allowed_setting_values[key]) > 1 \
                and new_value not in self.allowed_setting_values[key]:
            self.error.emit('Wrong value {} for setting: {}'\
                            .format(new_value, key))
            return False
        self.settings[key] = new_value
        if not quiet:
            self.print_.emit('{} now set to: {}'.format(key, new_value))

        # Setting specific settings... yyyeah.
        if key == 'linenumbers':
            self.textarea.set_number_bar_visibility(new_value)
        elif key == 'vscrollbar':
            policy = {'on': Qt.ScrollBarAlwaysOn,
                  'auto': Qt.ScrollBarAsNeeded,
                  'off':Qt.ScrollBarAlwaysOff}
            self.textarea.setVerticalScrollBarPolicy(policy[new_value])
        elif key == 'cmd_separator':
            self.terminal.set_command_separator(new_value)
        return True

## ==== Config ============================================================ ##

    def save_settings(self):
        configlib.write_config(self.config_file_path, self.settings)
        self.write_plugin_config.emit()

    def set_theme(self):
        stylesheet = common.read_stylesheet(self.theme_path)
        plugin_themes = [p.get_theme() for p in self.plugins]
        stylesheet = '\n'.join([stylesheet] + [p for p in plugin_themes if p])
        self.setStyleSheet(stylesheet)


## === Non-method functions ================================================ ##

def create_objects(settings):
    mainwindow = MainWindow()
    textarea = TextArea(mainwindow,
                        lambda key: settings[key])
    terminal = Terminal(mainwindow,
                        lambda: textarea.file_path)
    mainwindow.set_is_modified_callback(\
            textarea.document().isModified)
    return mainwindow, textarea, terminal


def set_key_shortcuts(mainwindow, textarea, terminal, plugins):
    hotkeys = {
        'Ctrl+N': textarea.request_new_file,
        'Ctrl+O': lambda:terminal.prompt_command('o'),
        'Ctrl+S': textarea.request_save_file,
        'Ctrl+Shift+S': lambda:terminal.prompt_command('s'),
        'F3': textarea.search_next,
        'Ctrl+Return': terminal.toggle
    }
    for p in plugins:
        hotkeys.update(p.hotkeys)
    for key, function in hotkeys.items():
        common.set_hotkey(key, mainwindow, function)


def connect_spider_signals(mainwindow, textarea, terminal):
    """
    "spider" as in "spider in the net"
    """
    connect = (
        # (SIGNAL, SLOT)
        (textarea.wordcount_changed, mainwindow.update_wordcount),
        (textarea.modification_changed, mainwindow.update_file_modified),
        (textarea.filename_changed, mainwindow.update_filename),

        # Print/error/prompt
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
    )
    for signal, slot in connect:
        signal.connect(slot)


def init_plugins(config_dir, vert_layout, horz_layout,
                 textarea, mainwindow,
                 read_plugin_config, write_plugin_config):
    def add_widget(widget, side):
        from pluginlib import NORTH, SOUTH, EAST, WEST
        if side in (NORTH, SOUTH):
            layout = vert_layout
        elif side in (WEST, EAST):
            layout = horz_layout
        if side in (NORTH, WEST):
            layout.insertWidget(0, widget)
        elif side in (SOUTH, EAST):
            layout.addWidget(widget)

    callbacks = [
        textarea.document().toPlainText,   # get_text()
        lambda:textarea.file_path,         # get_filepath()
        add_widget,                             # add_widget()
        textarea.new_file,                 # new_file()
        textarea.open_file,                # open_file()
        textarea.save_file,                # save_file()
        mainwindow.close,                  # quit()
    ]

    plugins = []
    plugin_commands = {}
    for name, path, module in configlib.get_plugins(config_dir):
        try:
            plugin_constructor = module.UserPlugin
        except AttributeError:
            print('"{0}" is not a valid plugin and was not loaded.'\
                  .format(name))
        else:
            p = plugin_constructor(callbacks, path)
            plugins.append(p)
            read_plugin_config.connect(p.read_config)
            write_plugin_config.connect(p.write_config)
            textarea.file_saved.connect(p.file_saved)
            textarea.document().contentsChanged.connect(p.contents_changed)
            plugin_commands.update(p.commands)

    return plugins, plugin_commands



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
