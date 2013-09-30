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

    def __init__(self, parent, get_filepath):
        super().__init__(parent, GenericTerminalInputBox, GenericTerminalOutputBox)

        self.get_filepath = get_filepath

        # Autocomplete
        self.ac_suggestions = []
        self.ac_index = 0
        self.input_term.tab_pressed.connect(self.autocomplete)
        self.input_term.reset_ac_suggestions.connect(self.reset_ac_suggestions)

        self.commands = {
            'o': (self.cmd_open, 'Open [file]'),
            'n': (self.cmd_new, 'Open new file'),
            's': (self.cmd_save, 'Save (as) [file]'),
            'q': (self.cmd_quit, 'Quit Kalpana'),
            '/': (self.search_and_replace, 'Search/replace'),
            '?': (self.cmd_help, 'List commands or help for [command]'),
            ':': (self.goto_line, 'Go to line'),
            'c': (self.count_words, 'Print wordcount'),
            '=': (self.manage_settings, 'Manage settings')
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

    def get_autocompletable_text(self):
        commands = ('o', 'o!', 's', 's!')
        text = self.input_term.text()
        for c in commands:
            if text.startswith(c + ' '):
                return text[:len(c)+1], text[len(c)+1:]
        return None, None


    def autocomplete(self):
        """
        Main autocomplete functions.
        Is called whenever tab is pressed.
        """
        cmdprefix, ac_text = self.get_autocompletable_text()
        if ac_text is None:
            return

        set_text = lambda p:self.input_term.setText(cmdprefix + p)

        # Autocomplete with the working directory if the line is empty
        if ac_text.strip() == '':
            wd = os.path.abspath(self.get_filepath())
            if not os.path.isdir(wd):
                wd = os.path.dirname(wd)
            set_text(wd + os.path.sep)
            return

        # Generate new suggestions if none exist
        if not self.ac_suggestions:
            self.ac_suggestions = self.get_ac_suggestions(ac_text)

        # If there's only one possibility, set it and move on
        if len(self.ac_suggestions) == 1:
            set_text(self.ac_suggestions[0])
            self.reset_ac_suggestions()
        # Otherwise start scrolling through 'em
        elif self.ac_suggestions:
            set_text(self.ac_suggestions[self.ac_index])
            self.ac_index += 1
            if self.ac_index == len(self.ac_suggestions):
                self.ac_index = 0

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
                       if p.startswith(namepart)]
        return [p + (os.path.sep*os.path.isdir(p)) for p in suggestions]

    def reset_ac_suggestions(self):
        """
        Reset the list of suggestions if another button than tab
        has been pressed.
        """
        self.ac_suggestions = []
        self.ac_index = 0


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

