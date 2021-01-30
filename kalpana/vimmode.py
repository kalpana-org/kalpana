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

import logging
from functools import reduce
from operator import mul
from typing import (Any, Callable, Dict, Iterable, List, Optional, Set, Tuple,
                    TypeVar)

from libsyntyche.widgets import mk_signal0, mk_signal1
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor

QTC = QTextCursor

F = TypeVar('F', bound=Callable[..., Any])


KEYS = {
    Qt.Key_Left: '<left>',
    Qt.Key_Right: '<right>',
    Qt.Key_Up: '<up>',
    Qt.Key_Down: '<down>',
    Qt.Key_Escape: '<escape>',
    Qt.Key_Space: '<space>',
    Qt.Key_Backspace: '<backspace>',
    Qt.Key_Tab: '<tab>',
}

partial_keys: Set[str] = set()
commands: Dict[str, Callable[['VimMode'], None]] = {}
count_commands: Dict[str, Callable[['VimMode', int], None]] = {}
motions: Dict[str, Callable[['VimMode', QTC.MoveMode], QTextCursor]] = {}
count_motions: Dict[str, Callable[['VimMode', int, QTC.MoveMode], QTextCursor]] = {}
to_char_motions: Dict[str, Callable[['VimMode', int, str, QTC.MoveMode],
                                    Optional[QTextCursor]]] = {}
text_object_select_full = 'a'
text_object_select_inside = 'i'
text_object_modifiers = {
    text_object_select_full: 'Select the text object and following whitespace',
    text_object_select_inside: 'Select the text object',
}
operators: Dict[str, Callable[['VimMode', QTextCursor], None]] = {}

text_object_wrappers = {
    '"': ('"', '"'),
    "'": ("'", "'"),
    '(': ('(', ')'),
    ')': ('(', ')'),
    '[': ('[', ']'),
    ']': ('[', ']'),
    '{': ('{', '}'),
    '}': ('{', '}'),
    '<': ('<', '>'),
    '>': ('<', '>'),
    '/': ('/', '/'),
    '*': ('*', '*'),
}
text_objects: Dict[str, Callable[['VimMode', QTC, bool], QTextCursor]] = {}


def command(keys: Set[str], help_text: str) -> Callable[[F], F]:
    def decorator_command(func: F) -> F:
        for key in keys:
            if key in commands:
                logging.warn(f'key {key} is bound to multiple commands')
            if len(key) == 2:
                partial_keys.add(key[0])
            commands[key] = func
        return func
    return decorator_command


def count_command(keys: Set[str], help_text: str) -> Callable[[F], F]:
    def decorator_command(func: F) -> F:
        for key in keys:
            if key in count_commands:
                logging.warn(f'key {key} is bound to multiple count commands')
            if len(key) == 2:
                partial_keys.add(key[0])
            count_commands[key] = func
        return func
    return decorator_command


def motion(keys: Set[str], help_text: str
           ) -> Callable[[Callable[['VimMode', QTC, QTC.MoveMode], None]],
                         Callable[['VimMode', QTC.MoveMode], QTC]]:
    def decorator_command(func: Callable[['VimMode', QTC, QTC.MoveMode], None]
                          ) -> Callable[['VimMode', QTC.MoveMode], QTC]:
        def wrapper(self: 'VimMode', move_mode: QTC.MoveMode) -> QTC:
            tc = self.get_cursor()
            func(self, tc, move_mode)
            return tc
        for key in keys:
            if key in motions:
                logging.warn(f'key {key} is bound to multiple motions')
            if len(key) == 2:
                partial_keys.add(key[0])
            motions[key] = wrapper
        return wrapper
    return decorator_command


def count_motion(keys: Set[str], help_text: str
                 ) -> Callable[[Callable[['VimMode', int, QTC, QTC.MoveMode], None]],
                               Callable[['VimMode', int, QTC.MoveMode], QTC]]:
    def decorator_command(func: Callable[['VimMode', int, QTC, QTC.MoveMode], None]
                          ) -> Callable[['VimMode', int, QTC.MoveMode], QTC]:
        def wrapper(self: 'VimMode', count: int, move_mode: QTC.MoveMode) -> QTC:
            tc = self.get_cursor()
            func(self, count, tc, move_mode)
            return tc
        for key in keys:
            if key in count_motions:
                logging.warn(f'key {key} is bound to multiple count motions')
            if len(key) == 2:
                partial_keys.add(key[0])
            count_motions[key] = wrapper
        return wrapper
    return decorator_command


def to_char_motion(keys: Set[str], help_text: str) -> Callable[[F], F]:
    def decorator_command(func: F) -> F:
        for key in keys:
            if key in to_char_motions:
                logging.warn(f'key {key} is bound to multiple to-char motions')
            if len(key) == 2:
                partial_keys.add(key[0])
            to_char_motions[key] = func
        return func
    return decorator_command


def text_object(keys: Set[str], help_text: str) -> Callable[[F], F]:
    def decorator_command(func: F) -> F:
        for key in keys:
            if key in text_objects:
                logging.warn(f'key {key} is bound to multiple text objects')
            text_objects[key] = func
        return func
    return decorator_command


def operator(keys: Set[str], help_text: str) -> Callable[[F], F]:
    def decorator_command(func: F) -> F:
        for key in keys:
            if key in operators:
                logging.warn(f'key {key} is bound to multiple operators')
            operators[key] = func
        return func
    return decorator_command


def is_sentence_sep(text: str) -> bool:
    return text.isspace() or text in '"\''


class VimMode(QtCore.QObject):
    align_cursor_to_edge = mk_signal1(bool)
    center_cursor = mk_signal0()
    change_chapter = mk_signal1(int)
    go_to_chapter = mk_signal1(int)
    search_next = mk_signal1(bool)
    show_terminal = mk_signal1(str)

    def __init__(self, doc: QtGui.QTextDocument,
                 get_height: Callable[[], int],
                 get_cursor: Callable[[], QTextCursor],
                 set_cursor: Callable[[QTextCursor], None],
                 get_visible_blocks: Callable[[], Iterable[Tuple[QtCore.QRectF,
                                                                 QtGui.QTextBlock]]],
                 activate_insert_mode: Callable[[], None]) -> None:
        super().__init__()
        self.ops: List[str] = []
        self.counts: List[str] = ['']
        self.partial_key = ''
        self.document = doc
        self.get_height = get_height
        self.get_cursor = get_cursor
        self.set_cursor = set_cursor
        self.get_visible_blocks = get_visible_blocks
        self.activate_insert_mode = activate_insert_mode

    def clear(self) -> None:
        self.ops = []
        self.counts = ['']
        self.partial_key = ''

    @property
    def count(self) -> int:
        return reduce(mul, (int(c or '1') for c in self.counts))

    # COMMANDS

    @command({':', KEYS[Qt.Key_Escape]}, 'Switch to the terminal')
    def _show_terminal(self) -> None:
        self.show_terminal.emit('')

    @command({'/'}, 'Start a search string')
    def _start_search(self) -> None:
        self.show_terminal.emit('/')

    @command({'n'}, 'Search next')
    def _search_next(self) -> None:
        self.search_next.emit(False)

    @command({'N'}, 'Search next (reverse)')
    def _search_next_reverse(self) -> None:
        self.search_next.emit(True)

    @command({'zz'}, 'Scroll to put the current line in the middle of the screen')
    def _center_cursor(self) -> None:
        self.center_cursor.emit()

    @command({'zt'}, 'Scroll to put the current line at the top of the screen')
    def _scroll_cursor_top(self) -> None:
        self.align_cursor_to_edge.emit(True)

    @command({'zb'}, 'Scroll to put the current line at the bottom of the screen')
    def _scroll_cursor_bottom(self) -> None:
        self.align_cursor_to_edge.emit(False)

    @command({'<c-b>'}, 'Scroll up one screen height')
    def _scroll_screen_up(self) -> None:
        tc = self.get_cursor()
        tc.setPosition(next(iter(self.get_visible_blocks()))[1].position())
        self.set_cursor(tc)
        self.align_cursor_to_edge.emit(False)

    @command({'<c-f>'}, 'Scroll down one screen height')
    def _scroll_screen_down(self) -> None:
        tc = self.get_cursor()
        for _, block in self.get_visible_blocks():
            pass
        tc.setPosition(block.position())
        self.set_cursor(tc)
        self.align_cursor_to_edge.emit(True)

    @command({'D'}, 'Delete to the end of the block')
    def _delete_to_eob(self) -> None:
        tc = self.get_cursor()
        if not tc.atBlockEnd():
            tc.movePosition(QTC.EndOfBlock, QTC.KeepAnchor)
            tc.deleteChar()

    @command({'C'}, 'Delete to the end of the block and switch to insert mode')
    def _change_to_eob(self) -> None:
        self._delete_to_eob()
        self.activate_insert_mode()

    def _append_insert_generic(self, motion: QTC.MoveOperation,
                               insert_block: bool = False,
                               motion2: QTC.MoveOperation = QTC.NoMove) -> None:
        tc = self.get_cursor()
        tc.movePosition(motion)
        if insert_block:
            tc.insertBlock()
        tc.movePosition(motion2)
        self.set_cursor(tc)
        self.activate_insert_mode()

    @command({'A'}, 'Switch to insert mode at the end of the block')
    def _append_at_eob(self) -> None:
        self._append_insert_generic(QTC.EndOfBlock)

    @command({'a'}, 'Switch to insert mode after the current character')
    def _append(self) -> None:
        self._append_insert_generic(QTC.NextCharacter)

    @command({'I'}, 'Switch to insert mode at the start of the block')
    def _insert_at_sob(self) -> None:
        self._append_insert_generic(QTC.StartOfBlock)

    @command({'i'}, 'Switch to insert mode')
    def _insert(self) -> None:
        self.activate_insert_mode()

    @command({'O'}, 'Add a new block after the current and switch to insert mode there')
    def _append_block(self) -> None:
        self._append_insert_generic(QTC.StartOfBlock, True, QTC.PreviousBlock)

    @command({'o'}, 'Insert a new block before the current and switch to insert mode there')
    def _insert_block(self) -> None:
        self._append_insert_generic(QTC.EndOfBlock, True)

    def _paste_generic(self, motion1: QTC.MoveOperation,
                       motion2: QTC.MoveOperation) -> None:
        clipboard = QtGui.QGuiApplication.clipboard()
        tc = self.get_cursor()
        text = clipboard.text()
        # \u2029 is paragraph separator
        if '\n' in text or '\u2029' in text:
            tc.movePosition(motion1)
        else:
            tc.movePosition(motion2)
        tc.insertText(text)
        self.set_cursor(tc)

    @count_command({'p'}, 'Paste <count> times after the current character/block')
    def _paste(self) -> None:
        self._paste_generic(QTC.NextBlock, QTC.Right)

    @count_command({'P'}, 'Paste <count> times before the current character/block')
    def _paste_before(self) -> None:
        self._paste_generic(QTC.StartOfBlock, QTC.NoMove)

    # COUNT COMMANDS

    @count_command({'u', '<c-z>'}, 'Undo <count> actions')
    def _undo(self, count: int) -> None:
        for _ in range(count):
            if not self.document.isUndoAvailable():
                break
            self.document.undo()

    @count_command({'<c-r>', '<c-y>'}, 'Redo <count> actions')
    def _redo(self, count: int) -> None:
        for _ in range(count):
            if not self.document.isRedoAvailable():
                break
            self.document.redo()

    @count_command({'gc'}, 'Go to chapter <count>')
    def _go_to_chapter(self, count: int) -> None:
        self.go_to_chapter.emit(count)

    @count_command({'gC'}, 'Go to chapter <count>, counting from the end')
    def _go_to_chapter_reverse(self, count: int) -> None:
        self.go_to_chapter.emit(-count)

    @count_command({'<c-tab>'}, 'Go <count> chapters forward')
    def _change_chapter(self, count: int) -> None:
        self.change_chapter.emit(count)

    @count_command({'<cs-tab>'}, 'Go <count> chapters backward')
    def _change_chapter_reverse(self, count: int) -> None:
        self.change_chapter.emit(-count)

    @count_command({'x'}, 'Delete <count> characters')
    def _delete(self, count: int) -> None:
        tc = self.get_cursor()
        tc.beginEditBlock()
        tc.movePosition(QTC.NextCharacter, QTC.KeepAnchor, n=count)
        tc.removeSelectedText()
        tc.endEditBlock()

    @count_command({'s'}, 'Delete <count> characters and switch to insert mode')
    def _delete_and_insert(self, count: int) -> None:
        self._delete(count)
        self.activate_insert_mode()

    @count_command({'~'}, 'Swap the case of <count> characters')
    def _swap_case(self, count: int) -> None:
        tc = self.get_cursor()
        tc.beginEditBlock()
        tc.movePosition(QTC.NextCharacter, QTC.KeepAnchor, n=count)
        text = tc.selectedText()
        tc.removeSelectedText()
        tc.insertText(text.swapcase())
        tc.endEditBlock()

    @count_command({'J'}, 'Join the next <count> blocks with this')
    def _join_lines(self, count: int) -> None:
        tc = self.get_cursor()
        tc.beginEditBlock()
        for _ in range(count):
            next_block = tc.block().next()
            if not next_block.isValid():
                break
            add_space = bool(next_block.text().strip())
            tc.movePosition(QTC.EndOfBlock)
            tc.deleteChar()
            if add_space:
                tc.insertText(' ')
        tc.endEditBlock()

    # MOTIONS

    @motion({'0'}, 'Go to the start of the block')
    def _go_to_sob(self, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.StartOfBlock, move_mode)

    @motion({'^'}, 'Go to the start of the line')
    def _go_to_sol(self, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.StartOfLine, move_mode)

    @motion({'$'}, 'Go to the end of the block')
    def _go_to_eob(self, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.EndOfBlock, move_mode)

    @motion({'G'}, 'Go to the end of the document')
    def _go_to_end(self, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.End, move_mode)

    @motion({'H'}, 'Go to the top of the screen')
    def _go_to_screen_top(self, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.setPosition(next(iter(self.get_visible_blocks()))[1].position(), move_mode)

    @motion({'M'}, 'Go to the middle of the screen')
    def _go_to_screen_mid(self, tc: QTC, move_mode: QTC.MoveMode) -> None:
        height = self.get_height()
        for rect, block in self.get_visible_blocks():
            if rect.top() < height / 2 and rect.bottom() > height / 2:
                tc.setPosition(block.position(), move_mode)
                break

    @motion({'L'}, 'Go to the bottom of the screen')
    def _go_to_screen_bottom(self, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.setPosition(list(self.get_visible_blocks())[-1][1].position(), move_mode)

    # COUNT MOTIONS

    @count_motion({'b'}, 'Go to the start of <count> words left')
    def _word_backwards(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.PreviousWord, move_mode, count)

    @count_motion({'w'}, 'Go to the start of <count> words right')
    def _word_forwards(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.NextWord, move_mode, count)

    @count_motion({'e'}, 'Go to the end of <count> words right')
    def _word_end_forwards(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        if count == 1:
            pos = self.get_cursor().position()
            tc.movePosition(QTC.EndOfWord, move_mode)
            if pos == tc.position():
                tc.movePosition(QTC.NextWord, move_mode)
                tc.movePosition(QTC.EndOfWord, move_mode)
        else:
            tc.movePosition(QTC.NextWord, move_mode, count)
            tc.movePosition(QTC.EndOfWord, move_mode)

    @count_motion({'gg'}, 'Go to block <count>')
    def _go_to_block(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        count = min(count - 1, self.document.blockCount() - 1)
        tc.setPosition(self.document.findBlockByNumber(count).position(), move_mode)

    @count_motion({KEYS[Qt.Key_Backspace], KEYS[Qt.Key_Left]}, 'Go <count> characters left')
    def _go_left(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.Left, move_mode, count)

    @count_motion({KEYS[Qt.Key_Space], KEYS[Qt.Key_Right]}, 'Go <count> characters right')
    def _go_right(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.Right, move_mode, count)

    @count_motion({'h', KEYS[Qt.Key_Up]}, 'Go <count> lines up')
    def _go_up(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.Up, move_mode, count)

    @count_motion({'k', KEYS[Qt.Key_Down]}, 'Go <count> lines down')
    def _go_down(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        tc.movePosition(QTC.Down, move_mode, count)

    @count_motion({'('}, 'Go <count> sentences left')
    def _prev_sentence(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        for _ in range(count):
            if tc.atStart():
                return
            if tc.atBlockStart():
                tc.movePosition(QTC.Left, move_mode)
                if tc.atBlockStart():
                    continue
            pos = tc.positionInBlock() - 1
            text = tc.block().text()
            while 0 <= pos < len(text) and is_sentence_sep(text[pos]):
                pos -= 1
            start_pos = max(text.rfind('.', 0, pos),
                            text.rfind('?', 0, pos),
                            text.rfind('!', 0, pos))
            if start_pos != -1:
                start_pos += 1
                while start_pos < len(text) and is_sentence_sep(text[start_pos]):
                    start_pos += 1
                tc.setPosition(tc.block().position() + start_pos, move_mode)
            elif pos == 0:
                tc.movePosition(QTC.PreviousBlock, move_mode)
            else:
                tc.movePosition(QTC.StartOfBlock, move_mode)

    @count_motion({')'}, 'Go <count> sentences right')
    def _next_sentence(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        for _ in range(count):
            pos = tc.positionInBlock()
            text = tc.block().text()
            end_poses = [text.find('.', pos),
                         text.find('?', pos),
                         text.find('!', pos)]
            end_pos = -1
            if max(end_poses) != -1:
                end_pos = min(p for p in end_poses if p != -1) + 1
                while end_pos < len(text) and is_sentence_sep(text[end_pos]):
                    end_pos += 1
                if end_pos == len(text):
                    tc.movePosition(QTC.NextBlock, move_mode)
                else:
                    tc.setPosition(tc.block().position() + end_pos, move_mode)
            else:
                block = tc.block().next()
                while block.isValid():
                    if block.text().strip():
                        tc.setPosition(block.position(), move_mode)
                        break
                    block = block.next()

    def _prev_next_block(self, count: int, tc: QTC, move_mode: QTC.MoveMode,
                         forward: bool) -> None:
        block = tc.block().next() if forward else tc.block().previous()
        pos = -1
        while block.isValid():
            if block.text().strip():
                pos = block.position()
                count -= 1
                if count == 0:
                    tc.setPosition(pos, move_mode)
                    break
            block = block.next() if forward else block.previous()

    @count_motion({'{'}, 'Go <count> blocks up')
    def _prev_block(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        self._prev_next_block(count, tc, move_mode, False)

    @count_motion({'}'}, 'Go <count> blocks down')
    def _next_block(self, count: int, tc: QTC, move_mode: QTC.MoveMode) -> None:
        self._prev_next_block(count, tc, move_mode, True)

    # TO-CHAR MOTIONS

    def _to_char_generic(self, forward: bool, greedy: bool, count: int, key: str,
                         move_mode: QTextCursor.MoveMode
                         ) -> Optional[QTextCursor]:
        if len(key) != 1 and key not in {KEYS[Qt.Key_Space]}:
            return None
        if key == KEYS[Qt.Key_Space]:
            key = ' '
        tc = self.get_cursor()
        pos = tc.positionInBlock()
        text = tc.block().text()
        if forward:
            for _ in range(count):
                pos = text.find(key, pos + 1)
                if pos == -1:
                    break
            else:
                if not greedy:
                    pos -= 1
        else:
            for _ in range(count):
                pos = text.rfind(key, 0, pos)
                if pos == -1:
                    break
            else:
                if not greedy:
                    pos += 1
        if pos >= 0:
            tc.setPosition(tc.block().position() + pos, move_mode)
            return tc
        return None

    @to_char_motion({'f'}, 'Go to the <count>th <char> to the right')
    def _to_char_right_greedy(self, count: int, key: str, move_mode: QTC.MoveMode
                              ) -> Optional[QTextCursor]:
        return self._to_char_generic(True, True, count, key, move_mode)

    @to_char_motion({'F'}, 'Go to the <count>th <char> to the left')
    def _to_char_left_greedy(self, count: int, key: str, move_mode: QTC.MoveMode
                             ) -> Optional[QTextCursor]:
        return self._to_char_generic(False, True, count, key, move_mode)

    @to_char_motion({'t'}, 'Go to one char before the <count>th <char> to the right')
    def _to_char_right(self, count: int, key: str, move_mode: QTC.MoveMode
                       ) -> Optional[QTextCursor]:
        return self._to_char_generic(True, False, count, key, move_mode)

    @to_char_motion({'T'}, 'Go to one char before the <count>th <char> to the left')
    def _to_char_left(self, count: int, key: str, move_mode: QTC.MoveMode
                      ) -> Optional[QTextCursor]:
        return self._to_char_generic(False, False, count, key, move_mode)

    # TEXT OBJECT SELECTIONS

    @text_object({'p'}, 'Select a paragraph')
    def _text_obj_paragraph(self, tc: QTC, select_full: bool) -> None:
        tc.movePosition(QTC.StartOfBlock)
        tc.movePosition(QTC.EndOfBlock, QTC.KeepAnchor)
        if select_full:
            tc.movePosition(QTC.NextBlock, QTC.KeepAnchor)
            block = tc.block()
            while block.isValid():
                if not block.text().strip():
                    tc.movePosition(QTC.NextBlock,
                                    QTC.KeepAnchor)
                else:
                    break
                block = block.next()

    @text_object({'s'}, 'Select a sentence')
    def _text_obj_sentence(self, tc: QTC, select_full: bool) -> None:
        pos = tc.positionInBlock()
        text = tc.block().text()
        start_pos = max(text.rfind('.', 0, pos),
                        text.rfind('?', 0, pos),
                        text.rfind('!', 0, pos))
        end_poses = [text.find('.', pos),
                     text.find('?', pos),
                     text.find('!', pos)]
        if max(end_poses) != -1:
            end_pos = min(p for p in end_poses if p != -1)
        else:
            end_pos = -1
        if start_pos == -1:
            tc.movePosition(QTC.StartOfBlock)
        else:
            start_pos += 1
            while start_pos < len(text) and text[start_pos].isspace():
                start_pos += 1
            tc.setPosition(tc.block().position() + start_pos)
        if end_pos == -1:
            tc.movePosition(QTC.EndOfBlock, QTC.KeepAnchor)
        else:
            end_pos += 1
            if select_full:
                while end_pos < len(text) and text[end_pos].isspace():
                    end_pos += 1
            tc.setPosition(tc.block().position() + end_pos,
                           QTC.KeepAnchor)

    @text_object({'w'}, 'Select a word')
    def _text_obj_word(self, tc: QTC, select_full: bool) -> None:
        tc.movePosition(QTC.StartOfWord)
        tc.movePosition(QTC.EndOfWord, QTC.KeepAnchor)
        if select_full:
            tc.movePosition(QTC.NextWord, QTC.KeepAnchor)

    # OPERATORS

    @operator({'d'}, 'Delete a chunk of text')
    def _delete_op(self, tc: QTC) -> None:
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(tc.selectedText())
        tc.removeSelectedText()

    @operator({'c'}, 'Delete a chunk of text and switch to insert mode')
    def _change_op(self, tc: QTC) -> None:
        self._delete_op(tc)
        self.activate_insert_mode()

    @operator({'gu'}, 'Switch a chunk of text to lower case characters')
    def _lower_case_op(self, tc: QTC) -> None:
        new_text = tc.selectedText().lower()
        tc.removeSelectedText()
        tc.insertText(new_text)

    @operator({'gU'}, 'Switch a chunk of text to upper case characters')
    def _upper_case_op(self, tc: QTC) -> None:
        new_text = tc.selectedText().upper()
        tc.removeSelectedText()
        tc.insertText(new_text)

    @operator({'y'}, 'Copy a chunk of text')
    def _yank_op(self, tc: QTC) -> None:
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(tc.selectedText())

    # OTHER

    def key_pressed(self, event: QtGui.QKeyEvent) -> None:
        """
        # Syntax Rules
        H, zz
        [partial-key] <action>

        9w, 3gg
        [count=1] [partial-key] <action>

        12Fj
        [count=1] <action> <target-char>

        dw, gU4w, gU4gg
        [count=1] [partial-key] <action> [count=1] [partial-key] <action>

        dfJ, gu5Fw
        [count=1] [partial-key] <action> [count=1] <action> <target-char>

        gUiw, das
        [partial-key] <action> <modifier> <target-obj>
        """

        def select_between(tc: QTextCursor, start_char: str, end_char: str,
                           select_inside: bool = True) -> None:
            pos = tc.positionInBlock()
            text = tc.block().text()
            start_pos = text.rfind(start_char, 0, pos)
            if start_pos == -1:
                return
            end_pos = text.find(end_char, pos)
            if end_pos == -1:
                return
            if select_inside:
                start_pos += len(start_char)
            else:
                end_pos += len(end_char)
                while end_pos < len(text) and text[end_pos].isspace():
                    end_pos += 1
            tc.setPosition(tc.block().position() + start_pos)
            tc.setPosition(tc.block().position() + end_pos, QTC.KeepAnchor)

        # Encode key
        if event.key() in {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt,
                           Qt.Key_AltGr, Qt.Key_Meta}:
            return
        mods = int(event.modifiers())
        if mods & int(Qt.AltModifier):
            self.clear()
            return
        if mods & int(Qt.ControlModifier):
            if (mods & ~int(Qt.ControlModifier)
                    & ~int(Qt.ShiftModifier)) == 0 \
                    and event.key() not in {Qt.Key_Control, Qt.Key_Shift}:
                if event.key() == Qt.Key_Tab:
                    key = '<c-tab>'
                elif event.key() == Qt.Key_Backtab:
                    key = '<cs-tab>'
                else:
                    key = f'<c-{chr(event.nativeVirtualKey())}>'
        else:

            if mods == Qt.NoModifier and event.key() in KEYS:
                key = KEYS[Qt.Key(event.key())]
            elif event.text():
                key = event.text()
            else:
                self.clear()
                return None

        if self.partial_key:
            key = self.partial_key + key
            self.partial_key = ''

        if len(self.ops) == 2:
            # == Run operation up to character ==
            if self.ops[1] in to_char_motions:
                op, motion = self.ops
                tc = to_char_motions[motion](self, self.count, key, QTC.KeepAnchor)
                if tc is not None and tc.hasSelection():
                    tc.beginEditBlock()
                    operators[op](self, tc)
                    tc.endEditBlock()
                self.clear()
            # == Run operation on text object ==
            elif self.ops[1] in text_object_modifiers:
                if key in text_objects or key in text_object_wrappers:
                    # Select the text
                    op, mod = self.ops
                    select_full = mod == text_object_select_full
                    tc = self.get_cursor()
                    tc.beginEditBlock()
                    # Paragraph
                    if key in text_objects:
                        text_objects[key](self, tc, select_full)
                    # Character pairs
                    elif key in text_object_wrappers:
                        start, end = text_object_wrappers[key]
                        select_between(tc, start, end, select_full)
                    else:
                        # TODO: warn
                        pass
                    # Do the thing
                    operators[op](self, tc)
                    tc.endEditBlock()
                self.clear()
            else:
                # TODO: warn
                self.clear()
        elif len(self.ops) == 1:
            # == Go to character ==
            if self.ops[0] in to_char_motions:
                tc = to_char_motions[self.ops[0]](self, self.count, key, QTC.MoveAnchor)
                if tc:
                    self.set_cursor(tc)
                self.clear()
            # == In operation ==
            elif self.ops[0] in operators:
                if key.isdigit():
                    self.counts[-1] += key
                elif key in partial_keys:
                    self.partial_key = key
                elif key in to_char_motions or key in text_object_modifiers:
                    self.ops.append(key)
                # Run operation on <count> lines
                elif key == self.ops[0]:
                    tc = self.get_cursor()
                    tc.beginEditBlock()
                    tc.movePosition(QTC.StartOfBlock)
                    tc.movePosition(QTC.NextBlock, QTC.KeepAnchor, n=self.count)
                    operators[key](self, tc)
                    tc.endEditBlock()
                    self.clear()
                # Run operation on motion
                elif key in motions:
                    tc = motions[key](self, QTC.KeepAnchor)
                    tc.beginEditBlock()
                    operators[self.ops[0]](self, tc)
                    tc.endEditBlock()
                    self.clear()
                # Run operation on <count> motions
                elif key in count_motions:
                    tc = count_motions[key](self, self.count, QTC.KeepAnchor)
                    tc.beginEditBlock()
                    operators[self.ops[0]](self, tc)
                    tc.endEditBlock()
                    self.clear()
                # Invalid key
                else:
                    self.clear()
        elif not self.ops:
            if key.isdigit() and (key != '0' or self.counts[-1]):
                self.counts[-1] += key
            elif key in partial_keys:
                self.partial_key = key
            elif key in to_char_motions:
                self.ops.append(key)
            # == Run simple command ==
            elif key in commands:
                commands[key](self)
                self.clear()
            # == Run simple motion ==
            elif key in motions:
                tc = motions[key](self, QTC.MoveAnchor)
                self.set_cursor(tc)
                self.clear()
            # == Run <count> commands ==
            elif key in count_commands:
                count_commands[key](self, self.count)
                self.clear()
            # == Run <count> motions ==
            elif key in count_motions:
                tc = count_motions[key](self, self.count, QTC.MoveAnchor)
                self.set_cursor(tc)
                self.clear()
            # == Start an operation ==
            elif key in operators:
                self.ops.append(key)
                self.counts.append('')
            else:
                self.clear()
        else:
            # TODO: warn
            self.clear()
        return None
