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

from datetime import datetime
from typing import cast, Dict, Iterable

from PyQt5 import QtCore, QtWidgets
from libsyntyche import cli, terminal

from kalpana.common import command_callback, KalpanaObject, Signal0
from kalpana.settings import CommandHistory


class MessageTrayItem(QtWidgets.QLabel):
    def __init__(self, text: str, name: str,
                 parent: QtWidgets.QWidget) -> None:
        super().__init__(text, parent)
        self.parent = parent
        self.setObjectName(name)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Preferred)
        # Fade out animation
        effect = QtWidgets.QGraphicsOpacityEffect(self)
        effect.setOpacity(1)
        self.setGraphicsEffect(effect)
        a1 = QtCore.QPropertyAnimation(effect, b'opacity')
        a1.setEasingCurve(QtCore.QEasingCurve.InOutQuint)
        a1.setDuration(500)
        a1.setStartValue(1)
        a1.setEndValue(0)
        cast(Signal0, a1.finished).connect(self.deleteLater)
        self.fade_animation = a1
        # Move animation
        a2 = QtCore.QPropertyAnimation(self, b'pos')
        a2.setEasingCurve(QtCore.QEasingCurve.InQuint)
        a2.setDuration(300)
        self.move_animation = a2

    def kill(self) -> None:
        self.fade_animation.start()
        self.move_animation.setStartValue(self.pos())
        self.move_animation.setEndValue(self.pos() - QtCore.QPoint(0, 50))
        self.move_animation.start()


class MessageTray(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        # TODO: put this in settings
        self.seconds_alive = 5
        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch()
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def add_message(self, timestamp: datetime, msgtype: terminal.MessageType,
                    text: str) -> None:
        if msgtype == terminal.MessageType.INPUT:
            return
        classes = {
            terminal.MessageType.ERROR: 'terminal_error',
            terminal.MessageType.PRINT: 'terminal_print',
        }
        # if msgtype == terminal.MessageType.ERROR:
            # text = f'Error: {text}'
        lbl = MessageTrayItem(text, classes[msgtype], self)
        self.layout().addWidget(lbl)
        QtCore.QTimer.singleShot(1000 * self.seconds_alive, lbl.kill)


class FocusWrapper(QtWidgets.QLineEdit):
    def setText(self, text: str) -> None:
        super().setText(text)
        self.parentWidget().show()


class Terminal(terminal.Terminal, KalpanaObject):
    def __init__(self, parent: QtWidgets.QFrame,
                 command_history: CommandHistory) -> None:
        super().__init__(parent, short_mode=True)
        self.add_command(cli.Command(
                'toggle-log',
                ('Show or hide the log of all input '
                 'and output in the terminal.'),
                self.toggle_log,
                args=cli.ArgumentRules.NONE, short_name='t'),
        )
        self.help_command = 'h'
        self.add_command(cli.Command(
                'toggle-help',
                'Show or hide the help view.',
                self.toggle_extended_help,
                args=cli.ArgumentRules.OPTIONAL, short_name=self.help_command,
                arg_help=(('', 'Toggle extended help view.'),
                          ('X', 'Show help for command X, which should be '
                           'one from the list below.'))
        ))
        self.help_view = HelpView(self, self.cli.commands, self.help_command)
        # Default to show help about itself
        self.help_view.show_help(self.help_command)
        cast(QtWidgets.QBoxLayout,
             self.layout()).insertWidget(0, self.help_view)
        self.output_field.hide()

    def register_commands(self, commands: Iterable[cli.Command]) -> None:
        for command in commands:
            self.add_command(command)

    def register_autocompletion_patterns(
                self, patterns: Iterable[cli.AutocompletionPattern]) -> None:
        for pattern in patterns:
            self.add_autocompletion_pattern(pattern)

    @command_callback
    def toggle_extended_help(self, arg: str) -> None:
        if not arg and self.help_view.isVisible():
            self.help_view.hide()
        else:
            success = self.help_view.show_help(arg or self.help_command)
            if success:
                self.help_view.show()
            else:
                self.error('Unknown command')
                self.help_view.hide()

    @command_callback
    def toggle_log(self) -> None:
        self.log_history.toggle_visibility()


class HelpView(QtWidgets.QLabel):
    def __init__(self, parent: QtWidgets.QWidget,
                 commands: Dict[str, cli.Command],
                 help_command: str) -> None:
        super().__init__(parent)
        self.commands = commands
        self.help_command = help_command
        self.set_help_text()
        self.setWordWrap(True)
        self.hide()

    def set_help_text(self) -> None:
        def escape(s: str) -> str:
            return s.replace('<', '&lt;').replace('>', '&gt;')
        # TODO: make this into labels and widgets instead maybe?
        main_template = ('<h2 style="margin:0">{command}: {desc}</h2>'
                         '<hr><table>{rows}</table>')
        row_template = ('<tr><td><b>{command}{arg}</b></td>'
                        '<td style="padding-left:10px">{subdesc}</td></tr>')

        def gen_arg_help(cmd: cli.Command) -> Iterable[str]:
            err_template = ('<tr><td colspan="2"><b><i>ERROR: {}'
                            '</i></b></td></tr>')
            if not cmd.arg_help and cmd.args == cli.ArgumentRules.NONE:
                return ["<tr><td>This command doesn't take any arguments."
                        "</td></tr>"]
            elif not cmd.arg_help:
                return [err_template.format('missing help for args')]
            else:
                out = [row_template.format(command=escape(cmd.short_name),
                                           arg=escape(arg),
                                           subdesc=escape(subdesc))
                       for arg, subdesc in cmd.arg_help]
                if cmd.args == cli.ArgumentRules.NONE:
                    out.append(err_template.format(
                        'command takes no arguments but there are still '
                        'help lines!'))
                return out

        self.help_html = {
            id_: main_template.format(
                command=escape(id_),
                desc=cmd.help_text,
                rows=''.join(gen_arg_help(cmd))
            )
            for id_, cmd in self.commands.items()
            if cmd.short_name
        }
        command_template = ('<div style="margin-left:5px">'
                            '<h3>List of {} commands</h3>'
                            '<table style="margin-top:2px">{}</table></div>')
        categories = {cmd.category for cmd in self.commands.values()}
        for group in sorted(categories):
            command_rows = (
                row_template.format(command=escape(cmd), arg='',
                                    subdesc=meta.help_text)
                for cmd, meta in self.commands.items()
                if meta.category == group and cmd
            )
            self.help_html[self.help_command] += command_template.format(
                group or 'misc',
                ''.join(command_rows))

    def show_help(self, arg: str) -> bool:
        self.set_help_text()
        if arg not in self.help_html:
            return False
        self.setText(self.help_html[arg])
        return True
