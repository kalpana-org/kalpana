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
import re

from PyQt4 import QtGui
from PyQt4.QtCore import pyqtSignal

from libsyntyche.terminal import GenericTerminalInputBox, GenericTerminalOutputBox, GenericTerminal


class Terminal(GenericTerminal):
    request_new_file = pyqtSignal(bool)
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
    spellcheck = pyqtSignal(str)

    def __init__(self, parent, get_filepath):
        super().__init__(parent, GenericTerminalInputBox, GenericTerminalOutputBox)

        self.get_filepath = get_filepath

        self.commands = {
            'o': (self.cmd_open, 'Open [file]'),
            'n': (self.cmd_new, 'Open new file'),
            's': (self.cmd_save, 'Save (as) [file]'),
            'q': (self.cmd_quit, 'Quit Kalpana'),
            '/': (self.search_and_replace, 'Search/replace'),
            '?': (self.cmd_help, 'List commands or help for [command]'),
            ':': (self.goto_line, 'Go to line'),
            'c': (self.count_words, 'Print wordcount'),
            '=': (self.manage_settings, 'Manage settings'),
            'p': (self.list_plugins, 'List active plugins'),
            'f': (self.print_filename, 'Print name of the active file'),
            '&': (self.spellcheck, 'Spellcheck (&? for help)')
        }

        self.hide()

    def update_commands(self, plugin_commands):
        self.commands.update(plugin_commands)

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

    def autocomplete(self):
        """
        Main autocomplete functions.
        Is called whenever tab is pressed.
        """
        text = self.input_term.text()
        rx = re.match(r'([os]!?)\s*(.*)', text)
        if not rx:
            return
        cmdprefix, ac_text = rx.groups()

        # Autocomplete with the working directory if the line is empty
        if not ac_text:
            wd = os.path.abspath(self.get_filepath())
            if not os.path.isdir(wd):
                wd = os.path.dirname(wd)
            self.prompt(cmdprefix + ' ' + wd + os.path.sep)
            return

        autocompleted_text = self.run_autocompletion(ac_text)
        self.prompt(cmdprefix + ' ' + autocompleted_text)


    def get_ac_suggestions(self, path):
        """
        Return a list of all possible paths that starts with the
        provided path.
        All directories are suffixed with a / or \ depending on os.
        """
        dirpath, namepart = os.path.split(path)
        if not os.path.isdir(dirpath):
            return []
        suggestions = [os.path.join(dirpath, p) for p in sorted(os.listdir(dirpath))
                       if p.lower().startswith(namepart.lower())]
        return [p + (os.path.sep*os.path.isdir(p)) for p in suggestions]



    # ==== Commands ============================== #

    def cmd_open(self, arg):
        fname = arg.lstrip('!').lstrip()
        self.request_open_file.emit(fname, arg.startswith('!'))

    def cmd_new(self, arg):
        self.request_new_file.emit(arg.startswith('!'))

    def cmd_save(self, arg):
        fname = arg.lstrip('!').lstrip()
        self.request_save_file.emit(fname, arg.startswith('!'))

    def cmd_quit(self, arg):
        self.request_quit.emit(arg.startswith('!'))

