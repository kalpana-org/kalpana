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
import re

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSignal, QEvent, Qt

from libsyntyche.terminal import GenericTerminalInputBox, GenericTerminalOutputBox, GenericTerminal
from libsyntyche.common import read_file
from common import Configable


class Terminal(GenericTerminal, Configable):
    request_new_file = pyqtSignal(bool, str)
    request_open_file = pyqtSignal(str, bool)
    request_save_file = pyqtSignal(str, bool)
    request_quit = pyqtSignal(bool)

    manage_settings = pyqtSignal(str)
    search_and_replace = pyqtSignal(str)
    give_up_focus = pyqtSignal()
    count_words = pyqtSignal(str)
    goto_line = pyqtSignal(str)
    list_plugins = pyqtSignal(str)
    print_filename = pyqtSignal(str)
    set_stylefile = pyqtSignal(str)
    spellcheck = pyqtSignal(str)

    shake = pyqtSignal()

    def __init__(self, parent, settingsmanager, get_filepath):
        super().__init__(parent, GenericTerminalInputBox, GenericTerminalOutputBox)
        self.init_settings_functions(settingsmanager)
        self.register_setting('Terminal Animation Interval', self.set_terminal_animation_interval)
        self.register_setting('Animate Terminal Output', self.set_terminal_animation)
        self.get_configpath = lambda: settingsmanager.paths['config_dir']
        self.get_filepath = get_filepath

        self.recent_files = []
        self.recent_files_index = 0
        self.update_recent_files()

        self.commands = {
            'o': (self.cmd_open, 'Open [file]'),
            'n': (self.cmd_new, 'Open new file'),
            's': (self.cmd_save, 'Save (as) [file]'),
            'q': (self.cmd_quit, 'Quit Kalpana'),
            '/': (self.search_and_replace, 'Search/replace', {'keep whitespace': True}),
            '?': (self.cmd_help, 'List commands or help for [command]'),
            ':': (self.goto_line, 'Go to line'),
            'c': (self.count_words, 'Print wordcount'),
            '=': (self.manage_settings, 'Manage settings'),
            'p': (self.list_plugins, 'List active plugins'),
            'f': (self.print_filename, 'Print name of the active file'),
            'g': (self.set_stylefile, 'Set style for the interface'),
            '&': (self.spellcheck, 'Spellcheck (&? for help)')
        }

        self.hide()

    def event(self, ev):
        if ev.type() == QEvent.KeyPress:
            if ev.key() == Qt.Key_Backtab and ev.modifiers() == Qt.ShiftModifier | Qt.ControlModifier:
                self.iterate_recent_files()
                return True
            elif ev.key() == Qt.Key_Tab and ev.modifiers() == Qt.ControlModifier:
                self.iterate_recent_files(reverse=True)
                return True
        return super().event(ev)

    def update_commands(self, plugin_commands):
        self.commands.update(plugin_commands)

    # ==== Setting callbacks ========================================
    def set_terminal_animation(self, animate):
        self.output_term.animate = animate

    def set_terminal_animation_interval(self, interval):
        if interval < 1:
            self.error('Too low animation interval')
            return
        self.output_term.set_timer_interval(interval)
    # ===============================================================

    def error(self, arg):
        super().error(arg)
        self.shake.emit()

    def show(self):
        super().show()
        self.input_term.setFocus()

    def toggle(self):
        if self.input_term.hasFocus():
            self.give_up_focus.emit()
            self.hide()
        else:
            self.show()

    # ==== Autocomplete ========================== #

    def autocomplete(self, reverse):
        """
        Main autocomplete functions.
        Is called whenever tab is pressed.
        """
        text = self.input_term.text()
        rx = re.match(r'([nos]!?|g)\s*(.*)', text)
        if not rx:
            return
        cmdprefix, ac_text = rx.groups()

        if not ac_text:
            if cmdprefix[0] in 'nos':
                # Autocomplete with the working directory if the line is empty
                wd = os.path.abspath(self.get_filepath())
                if not os.path.isdir(wd):
                    wd = os.path.dirname(wd)
                self.prompt(cmdprefix + ' ' + wd + os.path.sep)
                return

        autocompleted_text = self.run_autocompletion(ac_text, reverse)
        self.prompt(cmdprefix + ' ' + autocompleted_text)


    def get_ac_suggestions(self, prefix):
        """
        Return a list of all possible paths that starts with the
        provided string.
        All directories are suffixed with a / or \ depending on os.
        """
        cmd = self.input_term.text()[0]
        if cmd == 'g':
            suggestions = [x[6:-5] for x in sorted(os.listdir(self.get_configpath()))
                           if re.fullmatch(r'style-.+?\.conf', x)\
                           and x.startswith('style-' + prefix)]
            return suggestions
        else:
            dirpath, namepart = os.path.split(prefix)
            if not os.path.isdir(dirpath):
                return []
            suggestions = [os.path.join(dirpath, p) for p in sorted(os.listdir(dirpath))
                           if p.lower().startswith(namepart.lower())]
            return [p + (os.path.sep*os.path.isdir(p)) for p in suggestions]


    def update_recent_files(self):
        listfname = self.get_path('recentfiles')
        if not os.path.exists(listfname):
            return
        self.recent_files = read_file(listfname).splitlines()
        self.recent_files_index = 0


    def iterate_recent_files(self, reverse=False):
        if not self.recent_files:
            return
        text = self.input_term.text()
        rx = re.match(r'([nos]!?)\s*(.*)', text)
        if not rx:
            return
        cmdprefix, fname = rx.groups(1)
        if fname == self.recent_files[self.recent_files_index]:
            self.recent_files_index += -1 if reverse else 1
            self.recent_files_index %= len(self.recent_files)
        newtext = '{} {}'.format(cmdprefix, self.recent_files[self.recent_files_index])
        self.input_term.setText(newtext)


    # ==== Commands ============================== #

    def cmd_open(self, arg):
        fname = arg.lstrip('!').lstrip()
        self.request_open_file.emit(fname, arg.startswith('!'))

    def cmd_new(self, arg):
        fname = arg.lstrip('!').lstrip()
        self.request_new_file.emit(arg.startswith('!'), fname)

    def cmd_save(self, arg):
        fname = arg.lstrip('!').lstrip()
        self.request_save_file.emit(fname, arg.startswith('!'))

    def cmd_quit(self, arg):
        self.request_quit.emit(arg.startswith('!'))

