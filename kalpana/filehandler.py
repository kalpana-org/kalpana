# Copyright nycz 2011-2020

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
import subprocess
import sys
from typing import Callable, Optional

from libsyntyche.cli import ArgumentRules, AutocompletionPattern, Command
from libsyntyche.widgets import mk_signal1, mk_signal2
from PyQt5 import QtCore

from .common import KalpanaObject, autocomplete_file_path, command_callback


class FileHandler(QtCore.QObject, KalpanaObject):
    """Takes care of saving and opening files."""
    # file_opened(filepath, is new file)
    file_opened_signal = mk_signal2(str, bool)
    # file_saved(filepath, new save name)
    file_saved_signal = mk_signal2(str, bool)
    set_text = mk_signal1(str)

    def __init__(self, get_text: Callable[[], str],
                 is_modified: Callable[[], bool]) -> None:
        super().__init__()
        self.is_modified = is_modified
        self.get_text = get_text
        self.filepath: Optional[str] = None
        self.kalpana_commands = [
                Command('new-file', 'Create a new file.',
                        self.new_file,
                        short_name='n',
                        category='file',
                        arg_help=(('', 'Create a new unnamed file.'),
                                  (' path/to/file', 'Create a new file with '
                                   'the specified path and name. It will not '
                                   'be created on disk until you save it, '
                                   'but you can\'t use a file that already '
                                   'exists.'))),
                Command('new-file-in-new-window',
                        'Create a new file in a new window',
                        self.new_file_in_new_window,
                        short_name='N',
                        category='file',
                        arg_help=(('', 'Create a new unnamed file.'),
                                  (' path/to/file', 'Create a new file with '
                                   'the specified path and name. It will not '
                                   'be created on disk until you save it, '
                                   'but you can\'t use a file that already '
                                   'exists.'))),
                Command('open-file', 'Open a file', self.open_file,
                        args=ArgumentRules.REQUIRED,
                        short_name='o',
                        category='file',
                        arg_help=((' path/to/file',
                                   'Open the specified file.'),)),
                Command('open-file-in-new-window',
                        'Open a file in a new window',
                        self.open_file_in_new_window,
                        args=ArgumentRules.REQUIRED,
                        short_name='O',
                        category='file',
                        arg_help=((' path/to/file', 'Open the specified file '
                                   'in a new window.'),)),
                Command('save-file', 'Save the file', self.save_file,
                        short_name='s',
                        category='file',
                        arg_help=(('', 'Save the file. (Can\'t be a new and '
                                   'unnamed file.)'),
                                  (' path/to/file', 'Save the file to the '
                                   'specified path.'))),
        ]
        self.kalpana_autocompletion_patterns = [
                AutocompletionPattern('new-file',
                                      autocomplete_file_path,
                                      prefix=r'n\s*'),
                AutocompletionPattern('new-file-in-new-window',
                                      autocomplete_file_path,
                                      prefix=r'N\s*'),
                AutocompletionPattern('open-file',
                                      autocomplete_file_path,
                                      prefix=r'o\s*'),
                AutocompletionPattern('open-file-in-new-window',
                                      autocomplete_file_path,
                                      prefix=r'O\s*'),
                AutocompletionPattern('save-file',
                                      autocomplete_file_path,
                                      prefix=r's\s*'),
        ]

    def load_file_at_startup(self, filepath: str) -> None:
        """
        Initialize the filepath and textarea when the application starts.

        This is a convenience method so you can create a new file with a
        file name from the operating system's terminal or the
        open_file_in_new_window command easily.
        """
        if os.path.exists(filepath):
            self.open_file(filepath)
        else:
            self.new_file(filepath)

    def force_new_file(self, filepath: str) -> None:
        self.new_file(filepath, force=True)

    @command_callback
    def new_file(self, filepath: Optional[str], force: bool = False) -> None:
        """
        Clear the textarea and filepath unless there are unsaved changes.

        If filepath is not an empty string, that string is made the active
        filepath, which means you can then use save_file without a filepath
        to save.

        Note that nothing is written to the disk when new_file is run. An
        invalid filepath will only be detected when trying to save.
        """
        if self.is_modified() and not force:
            self.confirm('There are unsaved changes. Discard them?',
                         self.force_new_file, filepath or '')
        elif filepath and os.path.exists(filepath):
            self.error('File already exists, open it instead')
        else:
            self.set_text.emit('')
            if filepath:
                self.filepath = filepath
                self.file_opened_signal.emit(filepath, True)
                self.log(f'New file: {filepath}')
            else:
                self.filepath = None
                self.file_opened_signal.emit('', True)
                self.log('New file')

    @command_callback
    def new_file_in_new_window(self, filepath: Optional[str]) -> None:
        """Open a new file in a new instance of Kalpana."""
        if filepath and os.path.exists(filepath):
            self.error('File already exists, open it instead')
        else:
            subprocess.Popen([sys.executable, sys.argv[0]] +
                             ([filepath] if filepath else []))

    def force_open_file(self, filepath: str) -> None:
        self.open_file(filepath, force=True)

    @command_callback
    def open_file(self, filepath: str, force: bool = False) -> None:
        """
        Open a file, unless there are unsaved changes.

        This will only open files encoded in utf-8 or latin1.
        """
        if self.is_modified() and not force:
            self.confirm('There are unsaved changes. Discard them?',
                         self.force_open_file, filepath)
        elif not os.path.isfile(filepath):
            self.error('The path is not a file')
        else:
            encodings = ['utf-8', 'latin1']
            for e in encodings:
                try:
                    with open(filepath, encoding=e) as f:
                        text = f.read()
                except UnicodeDecodeError:
                    continue
                else:
                    self.set_text.emit(text)
                    self.filepath = filepath
                    self.log(f'File opened: {filepath}')
                    self.file_opened_signal.emit(filepath, False)
                    return
            else:
                self.error(f'Unable to open the file: {filepath}')

    @command_callback
    def open_file_in_new_window(self, filepath: str) -> None:
        """Open an existing file in a new instance of Kalpana."""
        if not filepath:
            self.error('No file specified')
        else:
            subprocess.Popen([sys.executable, sys.argv[0], filepath])

    def force_save_file(self, filepath: str) -> None:
        self.save_file(filepath, force=True)

    @command_callback
    def save_file(self, filepath: Optional[str], force: bool = False) -> None:
        """
        Save the file to the disk.

        If filepath is specified, this works as "save as" works in most
        programs, otherwise it saves over the existing filepath without
        prompting.

        Note that this always saves in utf-8, no matter the original encoding.
        """
        if not filepath and not self.filepath:
            self.error('No active file')
        elif filepath and filepath != self.filepath \
                and os.path.exists(filepath) and not force:
            self.confirm('File already exists. Overwrite?',
                         self.force_save_file, filepath)
        else:
            if self.filepath is None:
                file_to_save = filepath
            elif filepath:
                file_to_save = filepath
            else:
                file_to_save = self.filepath
            # When we get here, either filepath or self.filepath has
            # a valid value (see the first part of this if statement)
            assert file_to_save is not None
            try:
                with open(file_to_save, 'w', encoding='utf-8') as f:
                    f.write(self.get_text())
            except IOError:
                self.error(f'Unable to save the file: {file_to_save}')
            else:
                self.log(f'File saved: {file_to_save}')
                self.file_saved_signal.emit(file_to_save, file_to_save != self.filepath)
                self.filepath = file_to_save
