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

from typing import Optional
import os.path
import subprocess
import sys

from PyQt5 import QtCore
from libsyntyche.cli import AutocompletionPattern, Command, ArgumentRules

from .common import autocomplete_file_path, KalpanaObject
from .textarea import TextArea


class FileHandler(QtCore.QObject, KalpanaObject):
    """Takes care of saving and opening files."""
    # file_opened(filepath, is new file)
    file_opened_signal = QtCore.pyqtSignal(str, bool)
    # file_saved(filepath, new save name)
    file_saved_signal = QtCore.pyqtSignal(str, bool)

    def __init__(self, textarea: TextArea) -> None:
        super().__init__()
        self.textarea = textarea
        self.filepath: Optional[str] = None
        self.kalpana_commands = [
                Command('new-file', 'Create a new file. Filename is optional.',
                        self.new_file, short_name='n'),
                Command('new-file-in-new-window',
                        'Create a new file. Filename is optional.',
                        self.new_file_in_new_window, short_name='N'),
                Command('open-file', 'Open a file', self.open_file,
                        args=ArgumentRules.REQUIRED, short_name='o'),
                Command('open-file-in-new-window',
                        'Open a file in a new window',
                        self.open_file_in_new_window,
                        args=ArgumentRules.REQUIRED, short_name='O'),
                Command('save-file', 'Save the file', self.save_file,
                        short_name='s'),
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

    def new_file(self, filepath: str, force: bool = False) -> None:
        """
        Clear the textarea and filepath unless there are unsaved changes.

        If filepath is not an empty string, that string is made the active
        filepath, which means you can then use save_file without a filepath
        to save.

        Note that nothing is written to the disk when new_file is run. An
        invalid filepath will only be detected when trying to save.
        """
        if self.textarea.document().isModified() and not force:
            self.confirm('There are unsaved changes. Discard them?',
                         self.force_new_file, filepath)
        elif os.path.exists(filepath):
            self.error('File already exists, open it instead')
        else:
            if filepath:
                self.filepath = filepath
                self.file_opened_signal.emit(filepath, True)
                self.log(f'New file: {filepath}')
            else:
                self.filepath = None
                self.file_opened_signal.emit('', True)
                self.log('New file')
            self.textarea.setPlainText('')
            # For some reason this signal isn't triggered on its own
            self.textarea.document().modificationChanged.emit(False)

    def new_file_in_new_window(self, filepath: str) -> None:
        """Open a new file in a new instance of Kalpana."""
        if os.path.exists(filepath):
            self.error('File already exists, open it instead')
        else:
            subprocess.Popen([sys.executable, sys.argv[0]] +
                             ([filepath] if filepath else []))

    def force_open_file(self, filepath: str) -> None:
        self.open_file(filepath, force=True)

    def open_file(self, filepath: str, force: bool = False) -> None:
        """
        Open a file, unless there are unsaved changes.

        This will only open files encoded in utf-8 or latin1.
        """
        if self.textarea.document().isModified() and not force:
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
                    self.textarea.setPlainText(text)
                    self.filepath = filepath
                    self.log(f'File opened: {filepath}')
                    self.file_opened_signal.emit(filepath, False)
                    return
            else:
                self.error(f'Unable to open the file: {filepath}')

    def open_file_in_new_window(self, filepath: str) -> None:
        """Open an existing file in a new instance of Kalpana."""
        if not filepath:
            self.error('No file specified')
        else:
            subprocess.Popen([sys.executable, sys.argv[0], filepath])

    def force_save_file(self, filepath: str) -> None:
        self.save_file(filepath, force=True)

    def save_file(self, filepath: str, force: bool = False) -> None:
        """
        Save the file to the disk.

        If filepath is specified, this works as "save as" works in most
        programs, otherwise it saves over the existing filepath without
        prompting.

        Note that this always saves in utf-8, no matter the original encoding.
        """
        if not filepath and self.filepath is None:
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
            try:
                with open(file_to_save, 'w', encoding='utf-8') as f:
                    f.write(self.textarea.toPlainText())
            except IOError:
                self.error(f'Unable to save the file: {file_to_save}')
            else:
                self.log(f'File saved: {file_to_save}')
                if file_to_save == self.filepath:
                    self.file_saved_signal.emit(file_to_save, False)
                else:
                    self.file_saved_signal.emit(file_to_save, True)
                self.filepath = file_to_save
                self.textarea.document().setModified(False)
