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

from libsyntyche import common
import configlib
from textarea import TextArea
from loadorderdialog import LoadOrderDialog
from terminal import Terminal


class Kalpana(QtGui.QApplication):
    def __init__(self, argv, file_to_open=None):
        super().__init__(argv)
        self.settings = {}

        self.mainwindow = MainWindow()
        self.textarea = TextArea(self.mainwindow, lambda key: self.settings[key])
        self.terminal = Terminal(self.mainwindow, textarea)

        # UI
        vert_layout, horz_layout = self.mainwindow.create_ui(self.textarea, 
                                                             self.terminal)

        # Paths
        self.config_file_path, self.config_dir,\
        self.theme_path, self.loadorder_path\
            = configlib.get_paths()

        # Plugins
        self.plugins, plugin_commands = self.init_plugins(self.config_dir,
                                                    vert_layout, horz_layout)
        self.terminal.update_commands(plugin_commands)

        self.connect_signals()
        self.create_key_shortcuts(self.plugins)
        self.load_settings(self.config_file_path)

        if file_to_open:
            if not self.textarea.open_file(file_to_open):
                self.close()
            self.update_window_title(self.document.isModified())
        else:
            self.textarea.set_file_name('NEW')

        self.mainwindow.show()

        # class AppEventFilter(QtCore.QObject):
        #     def eventFilter(self, object, event):
        #         if event.type() == QtCore.QEvent.ApplicationActivate:
        #             a.refresh_config()
        #         return False

        # event_filter = AppEventFilter()
        # self..installEventFilter(event_filter)



    def init_plugins(self, config_dir, vert_layout, horz_layout):
        # Plugins
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

        plugins = []

        callbacks = [
            self.document.toPlainText,   # get_text()
            lambda:self.filepath,        # get_filepath()
            add_widget,                  # add_widget()
            self.new_file,               # new_file()
            self.open_file,              # open_file()
            self.save_file,              # save_file()
            self.close,                  # quit()
        ]
        for name, path, module in configlib.get_plugins(config_dir):
            try:
                plugin_constructor = module.UserPlugin
            except AttributeError:
                print('"{0}" is not a valid plugin and was not loaded.'\
                      .format(name))
            else:
                plugins.append(plugin_constructor(callbacks, path))

        plugin_commands = {}
        for p in plugins:
            self.read_plugin_config.connect(p.read_config)
            self.write_plugin_config.connect(p.write_config)
            self.document.contentsChanged.connect(p.contents_changed)
            plugin_commands.update(p.commands)

        return plugins, plugin_commands


    def connect_signals(self):
        # Text area
        self.textarea.print_.connect(self.print_)
        self.textarea.error.connect(self.error)

        # Terminal file operations
        self.terminal.request_new_file.connect(self.request_new_file)
        self.terminal.request_save_file.connect(self.request_save_file)
        self.terminal.request_open_file.connect(self.request_open_file)
        self.terminal.request_quit.connect(self.quit)

        # Terminal settings
        self.terminal.manage_settings.connect(self.manage_settings)

        # Terminal misc
        def open_loadorder_dialog():
            LoadOrderDialog(self, self.loadorder_path).exec_()
        self.terminal.give_up_focus.connect(self.textarea.setFocus)
        self.terminal.open_loadorder_dialog.connect(open_loadorder_dialog)
        self.terminal.reload_theme.connect(self.set_theme)
        self.terminal.goto_line.connect(self.textarea.goto_line)
        self.terminal.search_and_replace.connect(self.textarea.search_and_replace)


    def create_key_shortcuts(self, plugins):
        hotkeys = {
            'Ctrl+N': self.request_new_file,
            'Ctrl+O': lambda:self.prompt_term(defaultcmd='o '),
            'Ctrl+S': self.request_save_file,
            'Ctrl+Shift+S': lambda:self.prompt_term(defaultcmd='s '),
            'F3': self.textarea.search_next,
            'Ctrl+Return': self.toggle_terminal
        }
        for p in plugins:
            hotkeys.update(p.hotkeys)
        for key, function in hotkeys.items():
            common.set_hotkey(key, self, function)


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
            self.switch_focus_to_term()

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
            self.print_('Settings: {}'.format(', '.join(sorted(self.setting_names))))
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
            self.error('No such setting: {}'.format(acronym))
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
            self.print_('{} = {} ({})'.format(name, value,
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
            self.error('Wrong value {} for setting: {}'\
                            .format(new_value, key))
            return False
        self.settings[key] = new_value
        if not quiet:
            self.print_('{} now set to: {}'.format(key, new_value))

        # Setting specific settings... yyyeah.
        if key == 'linenumbers':
            self.textarea.number_bar.showbar = new_value
            self.textarea.number_bar.update()
        elif key == 'vscrollbar':
            policy = {'on': Qt.ScrollBarAlwaysOn,
                  'auto': Qt.ScrollBarAsNeeded,
                  'off':Qt.ScrollBarAlwaysOff}
            self.textarea.setVerticalScrollBarPolicy(policy[new_value])
        elif key == 'cmd_separator':
            self.terminal.set_command_separator(new_value)
        return True




class MainWindow(QtGui.QFrame):
    read_plugin_config = pyqtSignal()
    write_plugin_config = pyqtSignal()

    def __init__(self, file_=''):
        super().__init__()

        # Window title stuff
        self.wt_wordcount = 0
        self.wt_file = ''

        # Misc settings etc
        self.blocks = 1
        self.font_dialog_open = False

        self.document = self.textarea.document()





## ==== Overrides ========================================================== ##

    


## ==== Config ============================================================= ##

    def save_settings(self):
        configlib.write_config(self.config_file_path, self.settings)
        self.write_plugin_config.emit()

    def set_theme(self):
        stylesheet = common.read_stylesheet(self.theme_path)
        plugin_themes = [p.get_theme() for p in self.plugins]
        stylesheet = '\n'.join([stylesheet] + [p for p in plugin_themes if p])
        self.setStyleSheet(stylesheet)

    def refresh_config(self):
        self.load_settings(self.config_file_path)


## ==== Misc =============================================================== ##

    def error(self, errortext, defaultcmd=''):
        """ Show error in terminal """
        self.terminal.error(errortext)
        self.prompt_term(defaultcmd)

    def print_(self, text):
        self.terminal.print_(text)
        self.terminal.setVisible(True)

    def prompt_term(self, defaultcmd=''):
        if defaultcmd:
            self.terminal.input_term.setText(defaultcmd)
        self.terminal.setVisible(True)
        self.switch_focus_to_term()


    def toggle_terminal(self):
        """ Toggle terminal visibility and focus jointly """
        self.terminal.setVisible(abs(self.terminal.isVisible()-1))
        if self.terminal.isVisible():
            self.switch_focus_to_term()
        else:
            self.textarea.setFocus()


    def switch_focus_to_term(self):
        self.terminal.input_term.setFocus()



## ==== Window title ===================================== ##

    def contents_changed(self):
        """
        Update wordcount and stuff
        """
        wcount = len(re.findall(r'\S+', self.document.toPlainText()))
        if not wcount == self.wt_wordcount:
            self.wt_wordcount = wcount
            self.update_window_title(self.document.isModified())


    def update_window_title(self, modified):
        self.setWindowTitle('{0}{1} - {2}{0}'.format('*'*modified,
                                                     self.wt_wordcount,
                                                     self.wt_file))


    def set_file_name(self, filename):
        """ Set both the output file and the title to filename. """
        if filename == 'NEW':
            self.filepath = ''
            self.wt_file = 'New file'
        else:
            self.filepath = filename
            self.wt_file = os.path.basename(filename)
        self.update_window_title(self.document.isModified())





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
