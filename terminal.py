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

from common import set_key_shortcut
import fontdialog


class Terminal(QtGui.QSplitter):

    class InputBox(QtGui.QLineEdit):
        tab_pressed = pyqtSignal()
        update_completion_prefix = pyqtSignal()
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
                self.update_completion_prefix.emit()
            elif event.key() == Qt.Key_Up:
                self.history_up.emit()
            elif event.key() == Qt.Key_Down:
                self.history_down.emit()
            else:
                return super().keyPressEvent(event)

    # This needs to be here for the stylesheet
    class OutputBox(QtGui.QLineEdit):
        pass

    open_loadorder_dialog = pyqtSignal()

    def __init__(self, main):
        super().__init__(parent=main)
        self.textarea = main.textarea
        self.main = main
        self.sugindex = -1

        self.history = []

        # Splitter settings
        self.setHandleWidth(2)

        # I/O fields creation
        self.input_term = self.InputBox(self)
        self.output_term = self.OutputBox(self)
        self.output_term.setDisabled(True)
        self.output_term.setAlignment(Qt.AlignRight)

        self.addWidget(self.input_term)
        self.addWidget(self.output_term)

        # Autocomplete
        self.completer = QtGui.QCompleter(self)
        fsmodel = QtGui.QFileSystemModel(self.completer)
        fsmodel.setRootPath(QDir.homePath())
        self.completer.setModel(fsmodel)
        self.completer.setCompletionMode(QtGui.QCompleter.InlineCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitive)

        # Signals/slots
        self.input_term.tab_pressed.connect(self.autocomplete)
        self.input_term.update_completion_prefix.connect(self.update_completion_prefix)
        self.input_term.returnPressed.connect(self.parse_command)

        set_key_shortcut('Alt+Left', self, self.move_splitter_left)
        set_key_shortcut('Alt+Right', self, self.move_splitter_right)

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


    # ==== Autocomplete ========================== #

    def get_autocompletable_text(self):
        cmds = ('o', 'o!', 's', 's!')
        text = self.input_term.text()
        for c in cmds:
            if text.startswith(c + ' '):
                return text[:len(c)+1], text[len(c)+1:]
        return None, None


    def autocomplete(self):
        cmdprefix, ac_text = self.get_autocompletable_text()
        if ac_text is None:
            return

        separator = QDir.separator()

        # Autocomplete with the working directory if the line is empty
        if ac_text.strip() == '':
            wd = os.path.abspath(self.main.filepath)
            if not os.path.isdir(wd):
                wd = os.path.dirname(wd)
            self.completer.setCompletionPrefix(wd + separator)
            self.input_term.setText(cmdprefix + wd + separator)
            return

        isdir = os.path.isdir(self.completer.currentCompletion())
        if ac_text == self.completer.currentCompletion() + separator*isdir:
            if not self.completer.setCurrentRow(self.completer.currentRow() + 1):
                self.completer.setCurrentRow(0)

        prefix = self.completer.completionPrefix()
        suggestion = self.completer.currentCompletion()
        newisdir = os.path.isdir(self.completer.currentCompletion())
        self.input_term.setText(cmdprefix + prefix + suggestion[len(prefix):] + separator*newisdir)


    def update_completion_prefix(self):
        cmdprefix, ac_text = self.get_autocompletable_text()
        if not ac_text:
            return
        self.completer.setCompletionPrefix(ac_text)


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
        pass
        # if self.history_position > 0:
        #     self.history_position -= 1:
        #     self.input_term.setText(self.history[self.history_position])

    def history_down(self):
        # if self.history_position < len(self.history)-1:
        #     self.history_position += 1:
        #     self.input_term.setText(self.history[self.history_position])
        # elif self.history_position == len(self.history)-1 and self.input_term.text():
        #     self.history_position += 1:
        pass


    # ==== Misc ================================= #

    def switchFocus(self):
        self.main.textarea.setFocus()


    def parse_command(self):
        text = self.input_term.text()
        if not text.strip():
            return
        self.history.append(text)
        self.history_position = len(self.history)
        self.input_term.setText('')
        self.output_term.setText('')
        cmd = text.split(' ', 1)[0]
        # If the command exists, run the callback function (a bit cryptic maybe)
        if cmd in self.cmds:
            self.cmds[cmd][0](self, text[len(cmd)+1:])
        # Convenience for help and search: ?cf = ? cf, /lol = / lol
        elif text[0] in ('?', '/'):
            self.cmds[text[0]][0](self, text[1:])
        else:
            self.error('No such function (? for help)')


    def print_(self, text):
        self.output_term.setText(str(text))


    def error(self, text):
        self.output_term.setText('Error: ' + text)


    # ==== Commands ============================== #
    def cmd_open(self, arg, force=False):
        f = arg.strip()
        if os.path.isfile(f):
            self.main.open_t(f, force)
        else:
            self.error('Non-existing file')

    def cmd_force_open(self, arg):
        self.cmd_open(arg, force=True)


    def cmd_new(self, arg):
        success = self.main.new_file()
        if not success:
            self.error('Unsaved changes! Force new with n! or save first.')

    def cmd_force_new(self, arg):
        self.main.new_file(force=True)


    def cmd_save(self, arg, force=False):
        f = arg.strip()
        if not f:
            if self.main.filepath:
                result = self.main.save_file()
                if not result:
                    self.error('File not saved! IOError!')
            else:
                self.error('No filename')
        else:
            if os.path.isfile(f) and not force:
                self.error('File already exists, use s! to overwrite')
            # Make sure the parent directory actually exists
            elif os.path.isdir(os.path.dirname(f)):
                result = self.main.save_file(f)
                if not result:
                    self.error('File not saved! IOError!')
            else:
                self.error('Invalid path')

    def cmd_overwrite_save(self, arg):
        self.cmd_save(arg, force=True)


    def cmd_quit(self, arg):
        self.main.close()

    def cmd_force_quit(self, arg):
        self.main.force_quit = True
        self.main.close()


    def cmd_find(self, arg):
        if arg:
            self.main.findtext = arg
        self.main.find_next()

    def set_replace_texts(self, arg):
        """ Try to set the find/replace texts to the args, return False if it fails """
        try:
            self.main.replace1text, self.main.replace2text = arg.split(' ', 1)
        except ValueError:
            self.error('Not enough arguments')
            return False
        return True

    def cmd_replace(self, arg):
        if arg and not self.set_replace_texts(arg):
            return
        self.main.replace_next()

    def cmd_replace_all(self, arg):
        if arg and not self.set_replace_texts(arg):
            return
        self.main.replace_all()


    def cmd_change_font(self, arg):
        if self.main.font_dialog_open:
            self.error('Font dialog already open')
            return
        if arg not in ('main', 'term'):
            self.error('Wrong argument [main/term]')
            return
        if arg == 'term':
            self.print_('Räksmörgås?!')
        self.main.font_dialog_open = True
        fwin = fontdialog.FontDialog(self.main, self.main.show_fonts_in_dialoglist,
                                     arg + '_fontfamily', arg + '_fontsize')

    def cmd_autoindent(self, arg):
        self.main.autoindent = not self.main.autoindent
        self.print_('Now ' + str(self.main.autoindent).lower())

    def cmd_line_numbers(self, arg):
        self.textarea.number_bar.showbar = not self.textarea.number_bar.showbar
        self.textarea.number_bar.update()
        self.print_('Now ' + str(self.textarea.number_bar.showbar).lower())

    def cmd_scrollbar(self, arg):
        arg = arg.strip().lower()
        if not arg:
            self.print_(('Off','Maybe','On')[self.textarea.verticalScrollBarPolicy()])
        elif arg == 'off':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        elif arg == 'maybe':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        elif arg == 'on':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        else:
            self.error('Wrong argument [off/maybe/on]')

    def cmd_new_window(self, arg):
        arg = arg.strip()
        if not arg:
            self.print_(self.main.open_in_new_window)
        elif arg == 'y':
            self.main.open_in_new_window = True
        elif arg == 'n':
            self.main.open_in_new_window = False
        else:
            self.error('Wrong argument [y/n]')

    def cmd_help(self, arg):
        if not arg:
            self.print_(' '.join(sorted(self.cmds)))
        elif arg in self.cmds:
            self.print_(self.cmds[arg][1])
        else:
            self.error('No such command')

    def cmd_reload_theme(self, arg):
        self.main.set_theme()

    def cmd_load_order(self, arg):
        self.open_loadorder_dialog.emit()


    cmds = {
        'o': (cmd_open, 'Open [file]'),
        'o!': (cmd_force_open, 'Open [file] and discard the old'),
        'n': (cmd_new, 'Open new file'),
        'n!': (cmd_force_new, 'Open new file and discard the old'),
        's': (cmd_save, 'Save (as) [file]'),
        's!': (cmd_overwrite_save, 'Save (as) [file] and overwrite'),
        'q': (cmd_quit, 'Quit Kalpana'),
        'q!': (cmd_force_quit, 'Quit Kalpana without saving'),
        '/': (cmd_find, 'find (next) [string]'),
        'r': (cmd_replace, 'Replace (syntax help needed)'),
        'ra': (cmd_replace_all, 'Replace all (syntax help needed)'),
        '?': (cmd_help, 'List commands or help for [command]'),
        'cf': (cmd_change_font, 'Change font [main/term]'),
        'ai': (cmd_autoindent, 'Toggle auto indent'),
        'ln': (cmd_line_numbers, 'Toggle line numbers'),
        'vs': (cmd_scrollbar, 'Scrollbar [off/maybe/on]'),
        'nw': (cmd_new_window, 'Open in new window [y/n]'),
        'rt': (cmd_reload_theme, 'Reload theme from config'),
        'lo': (cmd_load_order, 'Change the plugin load order')
    }
