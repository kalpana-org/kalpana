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

from typing import cast, Callable, Dict, List, Optional, Tuple
from mypy_extensions import TypedDict
import re

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal
from libsyntyche.cli import AutocompletionPattern, Command, ArgumentRules

from kalpana.chapters import ChapterIndex
from kalpana.chapteroverview import ChapterOverview
from kalpana.common import KalpanaObject
from kalpana.filehandler import FileHandler
from kalpana.mainwindow import MainWindow
from kalpana.terminal import Terminal
from kalpana.textarea import TextArea, Highlighter
from kalpana.settings import Settings
from kalpana.spellcheck import Spellchecker


class Controller:
    def __init__(self, mainwindow: MainWindow, textarea: TextArea,
                 terminal: Terminal, settings: Settings,
                 chapter_overview: ChapterOverview) -> None:
        self.mainwindow = mainwindow
        self.textarea = textarea
        self.terminal = terminal
        self.settings = settings
        self.chapter_overview = chapter_overview
        self.filehandler = FileHandler(self.textarea)
        self.chapter_index = ChapterIndex()
        self.spellchecker = Spellchecker(self.settings.config_dir,
                                         self.textarea)
        self.highlighter = Highlighter(self.textarea, self.chapter_index,
                                       self.spellchecker)
        self.set_keybindings()
        self.connect_objects()
        self.register_own_commands()

    def update_style(self) -> None:
        pass

    def register_own_commands(self) -> None:
        commands = [
                Command('go-to-chapter', 'Jump to a specified chapter',
                        self.go_to_chapter, short_name='.'),
                Command('go-to-next-chapter', 'Jump to next chapter',
                        self.go_to_next_chapter,
                        args=ArgumentRules.NONE, short_name='>'),
                Command('go-to-prev-chapter', '', self.go_to_prev_chapter,
                        args=ArgumentRules.NONE, short_name='<'),
                Command('word-count-total', '', self.count_total_words,
                        args=ArgumentRules.NONE, short_name='C'),
                Command('word-count-chapter', '', self.count_chapter_words,
                        short_name='c'),
                Command('reload-settings', '', self.settings.reload_settings,
                        args=ArgumentRules.NONE),
                Command('reload-stylesheet', '',
                        self.settings.reload_stylesheet,
                        args=ArgumentRules.NONE),
                Command('show-info',
                        'Show information about the open file or the session.',
                        self.show_info, short_name='i'),
                Command('export-chapter', '',
                        self.export_chapter,
                        args=ArgumentRules.REQUIRED, short_name='e'),
                Command('toggle-chapter-overview', '',
                        self.toggle_chapter_overview,
                        args=ArgumentRules.NONE, short_name='9'),
        ]
        self.terminal.register_commands(commands)
        autocompletion_patterns = [
                AutocompletionPattern('show-info',
                                      self.get_show_info_suggestions,
                                      prefix=r'i\s*',
                                      illegal_chars=' '),
        ]
        self.terminal.register_autocompletion_patterns(autocompletion_patterns)

    def set_keybindings(self) -> None:
        class EventFilter(QtCore.QObject):
            def eventFilter(self_, obj: QtCore.QObject,
                            event: QtCore.QEvent) -> bool:
                if event.type() == QtCore.QEvent.KeyPress:
                    key_event = cast(QtGui.QKeyEvent, event)
                    actual_key = (key_event.key()
                                  | int(cast(int, key_event.modifiers())))
                    if actual_key in self.settings.key_bindings:
                        command_string = self.settings.key_bindings[actual_key]
                        self.terminal.exec_command(command_string)
                        return True
                    elif actual_key == self.settings.terminal_key:
                        self.toggle_terminal()
                        return True
                return False
        self.key_binding_event_filter = EventFilter()
        self.mainwindow.installEventFilter(self.key_binding_event_filter)

    def connect_objects(self) -> None:
        objects: List[KalpanaObject] = [
            self.textarea, self.filehandler, self.spellchecker,
            self.chapter_index, self.settings, self.terminal,
            self.mainwindow, self.highlighter
        ]
        for obj in objects:
            if obj != self.terminal:
                obj.log_signal.connect(self.terminal.print_)
                obj.error_signal.connect(self.terminal.error)
                obj.confirm_signal.connect(self.terminal.confirm_command)
                self.terminal.register_commands(obj.kalpana_commands)
                self.terminal.register_autocompletion_patterns(
                        obj.kalpana_autocompletion_patterns)
            if obj != self.settings:
                obj.change_setting_signal.connect(self.settings.change_setting)
                self.settings.register_settings(obj.kalpana_settings, obj)
            if obj != self.filehandler:
                self.filehandler.file_saved_signal.connect(obj.file_saved)
                self.filehandler.file_opened_signal.connect(obj.file_opened)
        misc_signals: List[Tuple[pyqtSignal, Callable]] = [
            (self.spellchecker.rehighlight, self.highlighter.rehighlight),
            (self.textarea.document().contentsChange,
             self.update_chapter_index),
            (self.textarea.modificationChanged,
             self.mainwindow.modification_changed),
            (self.terminal.error_triggered, self.mainwindow.shake_screen),
        ]
        for signal, slot in misc_signals:
            signal.connect(slot)

    def toggle_terminal(self) -> None:
        if self.terminal.input_field.hasFocus():
            # if self.terminal.completer_popup.isVisible():
            #    self.terminal.completer_popup.visible = False
            # else:
            self.terminal.hide()
            self.mainwindow.setFocus()
        else:
            self.terminal.input_field.setFocus()

    def update_chapter_index(self, pos: int, removed: int, added: int) -> None:
        new_index = self.chapter_index.update_line_index(
            self.textarea.document(), self.textarea.textCursor(),
            pos, removed, added)
        if new_index:
            self.chapter_overview.load_chapter_data(
                self.chapter_index.chapters)

    def set_text_block_formats(self) -> None:
        def make_format(alpha: float = 1, bold: bool = False,
                        size: Optional[float] = None) -> QtGui.QTextCharFormat:
            char_format = QtGui.QTextCharFormat()
            if bold:
                char_format.setFontWeight(QtGui.QFont.Bold)
            if size:
                char_format.setFontPointSize(size)
            if alpha < 1:
                col = self.textarea.palette().windowText().color()
                col.setAlphaF(alpha)
                char_format.setForeground(QtGui.QBrush(col))
            return char_format

        def set_line_format(line_number: int,
                            format_: QtGui.QTextCharFormat) -> None:
            block = QtGui.QTextCursor(
                self.textarea.document().findBlockByNumber(line_number))
            block.select(QtGui.QTextCursor.BlockUnderCursor)
            block.setCharFormat(format_)
        chapter_format = make_format(bold=True, size=16)
        metadata_format = make_format(alpha=0.3)
        section_format = make_format(alpha=0.5, bold=True)
        chapter_data = self.chapter_index.chapters
        pos = 0
        self.textarea.setUndoRedoEnabled(False)
        for chapter in chapter_data:
            if chapter.title:
                set_line_format(pos, chapter_format)
                pos += 1
            for line_num in range(1, chapter.metadata_line_count):
                set_line_format(pos, metadata_format)
                pos += 1
            for section in chapter.sections:
                if section.desc:
                    set_line_format(pos, section_format)
                pos += section.line_count
        self.textarea.setUndoRedoEnabled(True)

    # =========== COMMANDS ================================

    def toggle_chapter_overview(self) -> None:
        if self.mainwindow.active_stack_widget == self.textarea:
            if not self.chapter_overview.empty:
                self.mainwindow.active_stack_widget = self.chapter_overview
            else:
                self.terminal.error('No chapters to show')
        elif self.mainwindow.active_stack_widget == self.chapter_overview:
            self.mainwindow.active_stack_widget = self.textarea

    def show_info(self, arg: str) -> None:
        if arg == 'file':
            if self.filehandler.filepath is None:
                self.terminal.print_('No filename set')
            else:
                self.terminal.print_(self.filehandler.filepath)
        elif arg == 'modified':
            self.terminal.print_(
                'Modified' if self.textarea.document().isModified()
                else 'Not modified')
        elif arg == 'spellcheck':
            active = ('Active' if self.spellchecker.spellcheck_active
                      else 'Inactive')
            language = self.spellchecker.language
            self.terminal.print_(f'{active}, language: {language}')
        else:
            self.terminal.error('Invalid argument')

    def get_show_info_suggestions(self, name: str, text: str
                                  ) -> List[str]:
        return [item for item in ['file', 'spellcheck', 'modified']
                if item.startswith(text)]

    def go_to_chapter(self, arg: str) -> None:
        """
        Go to the chapter specified in arg.

        arg - The argument string entered in the terminal. Negative values
            means going from the end, where -1 is the last chapter
            and -2 is the second to last.
        """
        if not self.chapter_index.chapters:
            self.terminal.error('No chapters detected!')
        elif not re.match(r'-?\d+$', arg):
            self.terminal.error('Argument has to be a number!')
        else:
            chapter = int(arg)
            total_chapters = len(self.chapter_index.chapters)
            if chapter not in range(-total_chapters, total_chapters):
                self.terminal.error('Invalid chapter!')
            else:
                if chapter < 0:
                    chapter += total_chapters
                line = self.chapter_index.get_chapter_line(chapter)
                self.textarea.center_on_line(line)

    def go_to_next_chapter(self) -> None:
        self.go_to_chapter_incremental(1)

    def go_to_prev_chapter(self) -> None:
        self.go_to_chapter_incremental(-1)

    def go_to_chapter_incremental(self, diff: int) -> None:
        """
        Move to a chapter a number of chapters from the current.

        diff - How many chapters to move, negative to move backwards.
        """
        current_line = self.textarea.textCursor().blockNumber()
        current_chapter = self.chapter_index.which_chapter(current_line)
        target_chapter = max(0, min(len(self.chapter_index.chapters) - 1,
                                    current_chapter+diff))
        if current_chapter != target_chapter:
            line = self.chapter_index.get_chapter_line(target_chapter)
            current_chapter_line = self.chapter_index.get_chapter_line(
                current_chapter)
            # Go to the top of the current chapter if going up and not there
            if diff == -1 and current_line != current_chapter_line:
                line = current_chapter_line
            self.textarea.center_on_line(line)

    def count_total_words(self) -> None:
        words = len(self.textarea.toPlainText().split())
        self.terminal.print_(f'Total words: {words}')

    def count_chapter_words(self, arg: str) -> None:
        if not self.chapter_index.chapters:
            self.terminal.error('No chapters detected!')
        elif not arg:
            self.terminal.error('No chapter specified!')
        elif not arg.isdecimal():
            self.terminal.error('Argument has to be a number!')
        elif int(arg) >= len(self.chapter_index.chapters):
            self.terminal.error('Invalid chapter!')
        else:
            words = self.chapter_index.chapters[int(arg)].word_count
            self.terminal.print_(f'Words in chapter {arg}: {words}')

    def export_chapter(self, arg: str) -> None:
        # TODO: unify the whole chapter arg thingy
        args = arg.split(None, 1)
        if not len(args) == 2:
            self.terminal.error('Specify both chapter and format!')
        elif not self.chapter_index.chapters:
            self.terminal.error('No chapters detected!')
        elif not args[0]:
            self.terminal.error('No chapter specified!')
        elif not args[0].isdecimal():
            self.terminal.error('Argument has to be a number!')
        elif int(args[0]) >= len(self.chapter_index.chapters):
            self.terminal.error('Invalid chapter!')
        else:
            chapter = self.chapter_index.chapters[int(args[0])]
            start = (self.chapter_index.get_chapter_line(int(args[0]))
                     + chapter.metadata_line_count)
            end = start + chapter.line_count - chapter.metadata_line_count
            lines = self.textarea.toPlainText().split('\n')[start:end]
            # Get rid of irrelevant stuff
            text = '\n'.join(t for t in lines if not t.startswith('<<')
                             and not t.startswith('%%'))
            # settings = self.settings.settings
            # italic_marker = settings['italic-marker']
            # bold_marker = settings['bold-marker']
            # hr_marker = settings['horizontal-ruler-marker']
            ExportFormat = TypedDict('ExportFormat',
                                     {'pattern': str, 'repl': str,
                                      'selection_pattern': str}, total=False)
            export_formats: Dict[str, List[ExportFormat]] \
                = self.settings.settings['export_formats']
            # TODO: unify this with highlighter in textarea.py
            # for marker in (italic_marker, bold_marker):
                # for chunk in re.finditer(r'(?:\W|^)({0}[^{0}]*{0})(?:\W|$)'
                                         # .format(re.escape(marker)), text):
            fmt = args[1]
            if fmt not in export_formats:
                self.terminal.error('Export format not recognized!')
                return
            for x in export_formats[fmt]:
                if 'selection_pattern' in x:
                    text = replace_in_selection(text, x['pattern'], x['repl'],
                                                x['selection_pattern'])
                else:
                    text = re.sub(x['pattern'], x['repl'], text)
            text = text.strip('\n\t ')
            clipboard = QtGui.QGuiApplication.clipboard()
            clipboard.setText(text)


def replace_in_selection(text: str, rx: str, rep: str, selrx: str) -> str:
    chunks = []
    selections = re.finditer(selrx, text)
    for sel in selections:
        x = re.sub(rx, rep, sel.group(0))
        chunks.append((sel.start(), sel.end(), x))
    # Do this backwards to avoid messing up the positions of the chunks
    for start, end, payload in chunks[::-1]:
        text = text[:start] + payload + text[end:]
    return text
