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


class MainWindow(QtGui.QFrame):
    read_plugin_config = pyqtSignal()
    write_plugin_config = pyqtSignal()

    def __init__(self, file_=''):
        super().__init__()
        # Accept drag & drop events
        self.setAcceptDrops(True)

        # Window title stuff
        self.wt_wordcount = 0
        self.wt_file = ''

        # Misc settings etc
        self.search_buffer = None
        self.replace_buffer = None
        self.filepath = ''
        self.blocks = 1
        self.font_dialog_open = False
        self.force_quit_flag = False

        # UI
        vert_layout, horz_layout, self.textarea, self.terminal\
            = self.create_ui()
        self.document = self.textarea.document()

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
        self.settings = {}
        self.load_settings(self.config_file_path)

        if file_:
            if not self.open_file(file_):
                self.close()
            self.update_window_title(self.document.isModified())
        else:
            self.set_file_name('NEW')

        self.show()


    def create_ui(self):
        # Layout
        vert_layout = QtGui.QVBoxLayout(self)
        common.kill_theming(vert_layout)

        horz_layout = QtGui.QHBoxLayout()
        common.kill_theming(horz_layout)
        vert_layout.addLayout(horz_layout)

        # Text area
        textarea = TextArea(self)
        horz_layout.addWidget(textarea)

        # Terminal
        terminal = Terminal(self, textarea)
        terminal.setVisible(False)
        vert_layout.addWidget(terminal)

        return vert_layout, horz_layout, textarea, terminal

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

    def connect_signals(self):
        self.document.modificationChanged.connect(self.update_window_title)
        self.document.contentsChanged.connect(self.contents_changed)
        self.document.blockCountChanged.connect(self.new_line)

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

## ==== Overrides ========================================================== ##

    def closeEvent(self, event):
        if not self.document.isModified() or self.force_quit_flag:
            event.accept()
        else:
            self.error('Unsaved changes! Force quit with q! or save first.')
            event.ignore()

    def quit(self, force):
        if force:
            self.force_quit_flag = True
            self.close()
        else:
            self.force_quit_flag = False
            self.close()

    def dragEnterEvent(self, event):
##        if event.mimeData().hasFormat('text/plain'):
        event.acceptProposedAction();

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
        event.acceptProposedAction();


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


    def new_line(self, blocks):
        """ Generate auto-indentation if the option is enabled. """
        if blocks > self.blocks and self.settings['autoindent']:
            cursor = self.textarea.textCursor()
            blocknum = cursor.blockNumber()
            prevblock = self.document.findBlockByNumber(blocknum-1)
            indent = re.match(r'[\t ]*', prevblock.text()).group(0)
            cursor.insertText(indent)


    def new_and_empty(self):
        """ Return True if the file is empty and unsaved. """
        return not self.document.isModified() and not self.filepath


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



## ==== File operations: new/open/save ===================================== ##

    def request_new_file(self, force=False):
        success = self.new_file(force)
        if not success:
            self.error('Unsaved changes! Force new with n! or save first.')

    def request_open_file(self, filename, force=False):
        if not os.path.isfile(filename):
            self.error('File not found!')
            return
        if self.settings['open_in_new_window'] and not self.new_and_empty():
            subprocess.Popen([sys.executable, sys.argv[0], filename])
        elif not self.document.isModified() or force:
            success = self.open_file(filename)
            if not success:
                self.error('File could not be decoded!')
        else:
            self.error('Unsaved changes! Force open with o! or save first.')

    def request_save_file(self, filename='', force=False):
        if not filename:
            if self.filepath:
                result = self.save_file()
                if not result:
                    self.error('File not saved! IOError!')
            else:
                self.error('No filename', defaultcmd='s ')
        else:
            if os.path.isfile(filename) and not force:
                self.error('File already exists, use s! to overwrite')
            # Make sure the parent directory actually exists
            elif os.path.isdir(os.path.dirname(filename)):
                result = self.save_file(filename)
                if not result:
                    self.error('File not saved! IOError!')
            else:
                self.error('Invalid path')


    def new_file(self, force=False):
        """
        Main new file function
        """
        if self.settings['open_in_new_window'] and not self.new_and_empty():
            subprocess.Popen([sys.executable, sys.argv[0]])
            return True
        elif not self.document.isModified() or force:
            self.document.clear()
            self.document.setModified(False)
            self.set_file_name('NEW')
            self.blocks = 1
            return True
        else:
            return False

    def open_file(self, filename):
        """
        Main open file function
        """
        encodings = ('utf-8', 'latin1')
        for e in encodings:
            try:
                with open(filename, encoding=e) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                continue
            else:
                self.document.setPlainText(''.join(lines))
                self.document.setModified(False)
                self.set_file_name(filename)
                self.blocks = self.document.blockCount()
                self.textarea.moveCursor(QtGui.QTextCursor.Start)
                return True
        return False


    def save_file(self, filename=''):
        """
        Main save file function

        Save the file with the specified filename.
        If no filename is provided, save the file with the existing filename,
        (aka don't save as, just save normally)
        """
        if filename:
            savefname = filename
        else:
            savefname = self.filepath

        assert savefname.strip() != ''

        try:
            with open(savefname, 'w', encoding='utf-8') as f:
                f.write(self.document.toPlainText())
        except IOError as e:
            print(e)
            return False
        else:
            self.set_file_name(savefname)
            self.document.setModified(False)
            for p in self.plugins:
                p.file_saved()
            return True


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
    app = QtGui.QApplication(sys.argv)

    if not files:
        a = MainWindow()
    else:
        a = MainWindow(file_=files[0])
        for f in files[1:]:
            subprocess.Popen([sys.executable, sys.argv[0], f.encode('utf-8')])

    class AppEventFilter(QtCore.QObject):
        def eventFilter(self, object, event):
            if event.type() == QtCore.QEvent.ApplicationActivate:
                a.refresh_config()
            return False

    event_filter = AppEventFilter()
    app.installEventFilter(event_filter)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
