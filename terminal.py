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
from PyQt4.QtCore import pyqtSignal, Qt, QDir, QEvent

from libsyntyche.common import set_hotkey
import fontdialog


class Terminal(QtGui.QSplitter):

    class TerminalInputBox(QtGui.QLineEdit):
        tab_pressed = pyqtSignal()
        reset_ac_suggestions = pyqtSignal()
        reset_history_travel = pyqtSignal()
        history_up = pyqtSignal()
        history_down = pyqtSignal()
        # This has to be here, keyPressEvent does not capture tab press
        def event(self, event):
            if event.type() == QEvent.KeyPress and\
                        event.key() == Qt.Key_Tab and\
                        event.modifiers() == Qt.NoModifier:
                self.tab_pressed.emit()
                return True
            return super().event(event)

        def keyPressEvent(self, event):
            if event.text() or event.key() in (Qt.Key_Left, Qt.Key_Right):
                QtGui.QLineEdit.keyPressEvent(self, event)
                self.reset_ac_suggestions.emit()
                self.reset_history_travel.emit()
            elif event.key() == Qt.Key_Up:
                self.history_up.emit()
            elif event.key() == Qt.Key_Down:
                self.history_down.emit()
            else:
                return super().keyPressEvent(event)

    # This needs to be here for the stylesheet
    class TerminalOutputBox(QtGui.QLineEdit):
        pass

    request_new_file = pyqtSignal(bool)
    request_open_file = pyqtSignal(str, bool)
    request_save_file = pyqtSignal(str, bool)
    request_quit = pyqtSignal(bool)

    manage_settings = pyqtSignal(str)

    search_and_replace = pyqtSignal(str)
    give_up_focus = pyqtSignal()
    open_loadorder_dialog = pyqtSignal()
    reload_theme = pyqtSignal()
    goto_line = pyqtSignal(str)

    def __init__(self, parent, get_filepath):
        super().__init__(parent)

        self.get_filepath = get_filepath

        self.command_separator = ' '

        # Splitter settings
        self.setHandleWidth(2)
        set_hotkey('Alt+Left', self, self.move_splitter_left)
        set_hotkey('Alt+Right', self, self.move_splitter_right)

        # I/O fields creation
        self.input_term = self.TerminalInputBox(self)
        self.output_term = self.TerminalOutputBox(self)
        self.output_term.setDisabled(True)
        self.output_term.setAlignment(Qt.AlignRight)

        self.addWidget(self.input_term)
        self.addWidget(self.output_term)

        self.input_term.returnPressed.connect(self.parse_command)
        # Autocomplete
        self.ac_suggestions = []
        self.ac_index = 0
        self.input_term.tab_pressed.connect(self.autocomplete)
        self.input_term.reset_ac_suggestions.connect(self.reset_ac_suggestions)

        # History
        self.history = ['']
        self.history_index = 0
        self.input_term.reset_history_travel.connect(self.reset_history_travel)
        self.input_term.history_up.connect(self.history_up)
        self.input_term.history_down.connect(self.history_down)


    def update_commands(self, plugin_commands):
        # Plugins
        def run_plugin_command(function, arg):
            result = function(arg)
            if result:
                text, error = result
                if error:
                    self.error(text)
                else:
                    self.print_(text)

        for key, value in plugin_commands.items():
            function, help = value
            run_function = lambda _,arg: run_plugin_command(function, arg)
            plugin_commands[key] = (run_function, help)

        self.cmds.update(plugin_commands)

    def set_command_separator(self, separator):
        self.command_separator = separator


    def print_(self, text):
        self.output_term.setText(str(text))
        self.show()


    def error(self, text):
        self.output_term.setText('Error: ' + text)
        self.show()

    def prompt_command(self, cmd):
        self.input_term.setText(cmd + ' ')
        self.input_term.setFocus()
        self.show()

    # ==== Autocomplete ========================== #

    def get_autocompletable_text(self):
        cmds = ('o', 'o!', 's', 's!')
        text = self.input_term.text()
        for c in cmds:
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


    # ==== Splitter ============================== #

    def move_splitter(self, dir):
        s1, s2 = self.sizes()
        jump = int((s1 + s2) * 0.1)
        if dir == 'left':
            new_s1 = max(0, s1 - jump)
        else:
            new_s1 = min(s1 + s2, s1 + jump)
        new_s2 = s1 + s2 - new_s1
        self.setSizes((new_s1, new_s2))

    def move_splitter_left(self):
        self.move_splitter('left')

    def move_splitter_right(self):
        self.move_splitter('right')


    # ==== History =============================== #

    def history_up(self):
        if self.history_index < len(self.history)-1:
            self.history_index += 1
        self.input_term.setText(self.history[self.history_index])

    def history_down(self):
        if self.history_index > 0:
            self.history_index -= 1
        self.input_term.setText(self.history[self.history_index])

    def add_history(self, text):
        self.history[0] = text
        self.history.insert(0, '')

    def reset_history_travel(self):
        self.history_index = 0
        self.history[self.history_index] = self.input_term.text()


    # ==== Misc ================================= #

    def parse_command(self):
        text = self.input_term.text()
        if not text.strip():
            return
        self.add_history(text)
        self.input_term.setText('')
        self.output_term.setText('')

        run_cmd = lambda c,space: self.cmds[c][0](self,
                                                  text[len(c)+space:].strip())

        if self.command_separator in text:
            cmd = text.split(self.command_separator, 1)[0]
            if cmd in self.cmds:
                run_cmd(cmd, 1)
            else:
                self.error('No such command (? for help)')
        else:
            possible_cmds = [cmd for cmd in self.cmds if text.startswith(cmd)]
            if not possible_cmds:
                self.error('No such command (? for help)')
            elif len(possible_cmds) == 1:
                # If only one command matches, run it
                run_cmd(possible_cmds[0], 0)
            else:
                self.error('Ambiguous command, could mean: ' +\
                           ', '.join(possible_cmds))


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


    def cmd_search_and_replace(self, arg):
        self.search_and_replace.emit(arg)


    def cmd_change_font(self, arg):
        self.error('Font dialog deactivated until further notice')
        # if self.main.font_dialog_open:
        #     self.error('Font dialog already open')
        #     return
        # if arg not in ('main', 'term'):
        #     self.error('Wrong argument [main/term]')
        #     return
        # if arg == 'term':
        #     self.print_('Räksmörgås?!')
        # self.main.font_dialog_open = True
        # fwin = fontdialog.FontDialog(self.main, self.main.show_fonts_in_dialoglist,
        #                              arg + '_fontfamily', arg + '_fontsize')

    def cmd_help(self, arg):
        if not arg:
            self.print_(' '.join(sorted(self.cmds)))
        elif arg in self.cmds:
            self.print_(self.cmds[arg][1])
        else:
            self.error('No such command')

    def cmd_reload_theme(self, arg):
        self.reload_theme.emit()

    def cmd_load_order(self, arg):
        self.open_loadorder_dialog.emit()


    def cmd_set(self, arg):
        self.manage_settings.emit(arg)

    def cmd_goto_line(self, arg):
        self.goto_line.emit(arg)


    cmds = {
        'o': (cmd_open, 'Open [file]'),
        'n': (cmd_new, 'Open new file'),
        's': (cmd_save, 'Save (as) [file]'),
        'q': (cmd_quit, 'Quit Kalpana'),
        '/': (cmd_search_and_replace, 'Search/replace'),
        '?': (cmd_help, 'List commands or help for [command]'),
        'cf': (cmd_change_font, 'Change font [main/term]'),
        'rt': (cmd_reload_theme, 'Reload theme from config'),
        'lo': (cmd_load_order, 'Change the plugin load order'),
        ':': (cmd_goto_line, 'Go to line'),
        '=': (cmd_set, 'Manage settings')
    }
