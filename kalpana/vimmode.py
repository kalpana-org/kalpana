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

from typing import Callable, Iterable, List, Optional, Tuple

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor

from libsyntyche.widgets import mk_signal0, mk_signal1


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
        QTC = QTextCursor
        doc = self.document

        def move(motion: QTextCursor.MoveOperation, count: int = 1) -> None:
            tc = self.get_cursor()
            tc.movePosition(motion, n=count)
            self.set_cursor(tc)

        def is_sentence_sep(text: str) -> bool:
            return text.isspace() or text in '"\''

        def next_sentence(tc: QTextCursor, move_mode: QTextCursor.MoveMode) -> None:
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

        def prev_sentence(tc: QTextCursor, move_mode: QTextCursor.MoveMode) -> None:
            if tc.atStart():
                return
            if tc.atBlockStart():
                tc.movePosition(QTC.Left, move_mode)
                if tc.atBlockStart():
                    return
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

        def to_char(op: str, count: int, key: str,
                    move_mode: QTextCursor.MoveMode = QTC.MoveAnchor
                    ) -> Optional[QTextCursor]:
            if len(key) != 1 and key not in {SPACE}:
                return None
            if key == SPACE:
                key = ' '
            tc = self.get_cursor()
            pos = tc.positionInBlock()
            text = tc.block().text()
            if op in {'f', 't'}:
                for _ in range(count):
                    pos = text.find(key, pos + 1)
                    if pos == -1:
                        break
                else:
                    if op == 't':
                        pos -= 1
            elif op in {'F', 'T'}:
                for _ in range(count):
                    pos = text.rfind(key, 0, pos)
                    if pos == -1:
                        break
                else:
                    if op == 'T':
                        pos += 1
            if pos >= 0:
                tc.setPosition(tc.block().position() + pos, move_mode)
                return tc
            return None

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

        def do_motion(key: str, move_mode: QTextCursor.MoveMode) -> QTextCursor:
            tc = self.get_cursor()
            move_actions = {
                '0': QTC.StartOfBlock,
                '^': QTC.StartOfLine,
                '$': QTC.EndOfBlock,
                'G': QTC.End,
            }
            if key in move_actions:
                tc.movePosition(move_actions[key], move_mode)
            elif key == 'H':
                tc.setPosition(next(iter(self.get_visible_blocks()))[1].position(), move_mode)
            elif key in {'M', 'L'}:
                height = self.get_height()
                for rect, block in self.get_visible_blocks():
                    if (key == 'M' and rect.top() < height / 2 and rect.bottom() > height / 2) \
                            or (key == 'L' and rect.bottom() >= height):
                        tc.setPosition(block.position(), move_mode)
                        break
            else:
                # TODO: warn
                pass
            return tc

        def do_count_motion(key: str, count: int, move_mode: QTextCursor.MoveMode) -> QTextCursor:
            tc = self.get_cursor()
            move_actions = {
                'b': QTC.PreviousWord,
                'w': QTC.NextWord,
                SPACE: QTC.Right,
                BACKSPACE: QTC.Left,
                'h': QTC.Up,
                'k': QTC.Down,
                RIGHT: QTC.Right,
                LEFT: QTC.Left,
                UP: QTC.Up,
                DOWN: QTC.Down,
            }
            if key in move_actions:
                tc.movePosition(move_actions[key], move_mode, count)
            elif key == 'gg':
                count = min(count - 1, doc.blockCount() - 1)
                tc.setPosition(doc.findBlockByNumber(count).position(), move_mode)
            elif key == 'e':
                if count == 1:
                    pos = self.get_cursor().position()
                    tc.movePosition(QTC.EndOfWord, move_mode)
                    if pos == tc.position():
                        tc.movePosition(QTC.NextWord, move_mode)
                        tc.movePosition(QTC.EndOfWord, move_mode)
                else:
                    tc.movePosition(QTC.NextWord, move_mode, count)
                    tc.movePosition(QTC.EndOfWord, move_mode)
            elif key == '(':
                for _ in range(int(self.counts[0] or '1')):
                    prev_sentence(tc, move_mode)
            elif key == ')':
                for _ in range(int(self.counts[0] or '1')):
                    next_sentence(tc, move_mode)
            elif key in {'{', '}'}:
                block = tc.block().next() if key == '}' else tc.block().previous()
                pos = -1
                while block.isValid():
                    if block.text().strip():
                        pos = block.position()
                        count -= 1
                        if count == 0:
                            tc.setPosition(pos, move_mode)
                            break
                    block = block.next() if key == '}' else block.previous()
            else:
                # TODO: warn
                pass
            return tc

        def do_operation(tc: QTextCursor, op: str) -> None:
            if op in {'c', 'd'}:
                clipboard = QtGui.QGuiApplication.clipboard()
                clipboard.setText(tc.selectedText())
                tc.removeSelectedText()
                if op == 'c':
                    self.activate_insert_mode()
            elif op in {'gu', 'gU'}:
                new_text = (tc.selectedText().lower() if op == 'gu'
                            else tc.selectedText().upper())
                tc.removeSelectedText()
                tc.insertText(new_text)
            elif op == 'y':
                clipboard = QtGui.QGuiApplication.clipboard()
                clipboard.setText(tc.selectedText())
            else:
                # TODO: warn
                pass

        SPACE = '<space>'
        BACKSPACE = '<backspace>'
        ESCAPE = '<escape>'
        LEFT = '<left>'
        RIGHT = '<right>'
        UP = '<up>'
        DOWN = '<down>'
        text_obj_sel_mod = 'i a'.split()
        text_obj_sel_target = 'w s p " \' / * ( ) [ ] < > { }'.split()
        commands = [ESCAPE] + ': / n N zz zt zb a A i I o O D C * ? <c-f> <c-b>'.split()
        count_commands = 'u gc gC <c-r> <c-tab> <cs-tab> x ~ s J p P'.split()
        motions = '0 ^ $ G H M L'.split()
        count_motions = 'gg w b e h k ( ) { }'.split()
        count_motions.extend([SPACE, BACKSPACE, LEFT, RIGHT, UP, DOWN])
        to_char_motions = 'f F t T'.split()
        motion_operators = 'y c d gu gU'.split()
        partial_keys = 'g z'.split()

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
            if mods == Qt.NoModifier \
                    and event.key() in {Qt.Key_Space, Qt.Key_Backspace, Qt.Key_Escape,
                                        Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down}:
                if event.key() == Qt.Key_Space:
                    key = SPACE
                elif event.key() == Qt.Key_Backspace:
                    key = BACKSPACE
                elif event.key() == Qt.Key_Escape:
                    key = ESCAPE
                elif event.key() == Qt.Key_Left:
                    key = LEFT
                elif event.key() == Qt.Key_Right:
                    key = RIGHT
                elif event.key() == Qt.Key_Up:
                    key = UP
                elif event.key() == Qt.Key_Down:
                    key = DOWN
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
                count = int(self.counts[0] or '1') * int(self.counts[1] or '1')
                tc = to_char(motion, count, key, QTC.KeepAnchor)
                if tc is not None and tc.hasSelection():
                    tc.beginEditBlock()
                    do_operation(tc, op)
                    tc.endEditBlock()
                self.clear()
            # == Run operation on text object ==
            elif self.ops[1] in text_obj_sel_mod:
                if key in text_obj_sel_target:
                    # Select the text
                    op, mod = self.ops
                    tc = self.get_cursor()
                    tc.beginEditBlock()
                    pairs = {
                        '"': ('"', '"'),
                        '\'': ('\'', '\''),
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
                    # Paragraph
                    if key == 'p':
                        tc.movePosition(QTC.StartOfBlock)
                        tc.movePosition(QTC.EndOfBlock, QTC.KeepAnchor)
                        if mod == 'a':
                            tc.movePosition(QTC.NextBlock, QTC.KeepAnchor)
                            block = tc.block()
                            while block.isValid():
                                if not block.text().strip():
                                    tc.movePosition(QTC.NextBlock,
                                                    QTC.KeepAnchor)
                                else:
                                    break
                                block = block.next()
                    # Sentence
                    elif key == 's':
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
                            if mod == 'a':
                                while end_pos < len(text) and text[end_pos].isspace():
                                    end_pos += 1
                            tc.setPosition(tc.block().position() + end_pos,
                                           QTC.KeepAnchor)
                    # Word
                    elif key == 'w':
                        tc.movePosition(QTC.StartOfWord)
                        tc.movePosition(QTC.EndOfWord, QTC.KeepAnchor)
                        if mod == 'a':
                            tc.movePosition(QTC.NextWord, QTC.KeepAnchor)
                    # Character pairs
                    elif key in pairs:
                        start, end = pairs[key]
                        select_between(tc, start, end, mod == 'i')
                    else:
                        # TODO: warn
                        pass
                    # Do the thing
                    do_operation(tc, op)
                    tc.endEditBlock()
                self.clear()
            else:
                # TODO: warn
                self.clear()
        elif len(self.ops) == 1:
            # == Go to character ==
            if self.ops[0] in to_char_motions:
                tc = to_char(self.ops[0], int(self.counts[0] or '1'), key)
                if tc:
                    self.set_cursor(tc)
                self.clear()
            # == In operation ==
            elif self.ops[0] in motion_operators:
                if key.isdigit():
                    self.counts[-1] += key
                elif key in partial_keys:
                    self.partial_key = key
                elif key in to_char_motions + text_obj_sel_mod:
                    self.ops.append(key)
                # Run operation on <count> lines
                elif key == self.ops[0]:
                    count = int(self.counts[0] or '1') * int(self.counts[1] or '1')
                    tc = self.get_cursor()
                    tc.beginEditBlock()
                    tc.movePosition(QTC.StartOfBlock)
                    tc.movePosition(QTC.NextBlock, QTC.KeepAnchor, n=count)
                    do_operation(tc, key)
                    tc.endEditBlock()
                    self.clear()
                # Run operation on motion
                elif key in motions:
                    tc = do_motion(key, QTC.KeepAnchor)
                    tc.beginEditBlock()
                    do_operation(tc, self.ops[0])
                    tc.endEditBlock()
                    self.clear()
                # Run operation on <count> motions
                elif key in count_motions:
                    count = int(self.counts[0] or '1') * int(self.counts[1] or '1')
                    tc = do_count_motion(key, count, QTC.KeepAnchor)
                    tc.beginEditBlock()
                    do_operation(tc, self.ops[0])
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
                if key in {':', ESCAPE}:
                    self.show_terminal.emit('')
                elif key == '/':
                    self.show_terminal.emit('/')
                elif key in {'n', 'N'}:
                    reverse = key == 'N'
                    self.search_next.emit(reverse)
                elif key == 'zz':
                    self.center_cursor.emit()
                elif key == 'zt':
                    self.align_cursor_to_edge.emit(True)
                elif key == 'zb':
                    self.align_cursor_to_edge.emit(False)
                elif key == '<c-b>':
                    tc = self.get_cursor()
                    tc.setPosition(next(iter(self.get_visible_blocks()))[1].position())
                    self.set_cursor(tc)
                    self.align_cursor_to_edge.emit(False)
                elif key == '<c-f>':
                    tc = self.get_cursor()
                    for _, block in self.get_visible_blocks():
                        pass
                    tc.setPosition(block.position())
                    self.set_cursor(tc)
                    self.align_cursor_to_edge.emit(True)
                elif key in {'D', 'C'}:
                    tc = self.get_cursor()
                    if not tc.atBlockEnd():
                        tc.movePosition(QTC.EndOfBlock, QTC.KeepAnchor)
                        tc.deleteChar()
                    if key == 'C':
                        self.activate_insert_mode()
                elif key in {'A', 'a', 'I', 'i'}:
                    if key == 'A':
                        move(QTC.EndOfBlock)
                    elif key == 'I':
                        move(QTC.StartOfBlock)
                    elif key == 'a':
                        move(QTC.NextCharacter)
                    self.activate_insert_mode()
                elif key == 'O':
                    tc = self.get_cursor()
                    tc.movePosition(QTC.StartOfBlock)
                    tc.insertBlock()
                    tc.movePosition(QTC.PreviousBlock)
                    self.set_cursor(tc)
                    self.activate_insert_mode()
                elif key == 'o':
                    tc = self.get_cursor()
                    tc.movePosition(QTC.EndOfBlock)
                    tc.insertBlock()
                    self.set_cursor(tc)
                    self.activate_insert_mode()
                elif key == '*':
                    pass
                elif key == '?':
                    pass
                else:
                    # TODO: warn
                    pass
                self.clear()
            # == Run simple motion ==
            elif key in motions:
                tc = do_motion(key, QTC.MoveAnchor)
                self.set_cursor(tc)
                self.clear()
            # == Run <count> commands ==
            elif key in count_commands:
                count = int(self.counts[0] or '1')
                if key in {'u', '<c-r>'}:
                    for _ in range(count):
                        if key == 'u':
                            if not doc.isUndoAvailable():
                                break
                            doc.undo()
                        else:
                            if not doc.isRedoAvailable():
                                break
                            doc.redo()
                elif key in {'gc', 'gC'}:
                    self.go_to_chapter.emit(count * (-1 if key == 'gC' else 1))
                elif key in {'<c-tab>', '<cs-tab>'}:
                    self.change_chapter.emit(count * (-1 if key == '<cs-tab>' else 1))
                elif key in {'s', 'x', '~'}:
                    tc = self.get_cursor()
                    tc.beginEditBlock()
                    tc.movePosition(QTC.NextCharacter, QTC.KeepAnchor, n=count)
                    if key == '~':
                        text = tc.selectedText()
                    tc.removeSelectedText()
                    if key == 's':
                        self.activate_insert_mode()
                    elif key == '~':
                        tc.insertText(text.swapcase())
                    tc.endEditBlock()
                elif key == 'J':
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
                elif key in {'p', 'P'}:
                    clipboard = QtGui.QGuiApplication.clipboard()
                    tc = self.get_cursor()
                    text = clipboard.text()
                    # \u2029 is paragraph separator
                    if '\n' in text or '\u2029' in text:
                        if key == 'p':
                            tc.movePosition(QTC.NextBlock)
                        else:
                            tc.movePosition(QTC.StartOfBlock)
                    else:
                        if key == 'p':
                            tc.movePosition(QTC.Right)
                    tc.insertText(text)
                    self.set_cursor(tc)
                else:
                    # TODO: warn
                    pass
                self.clear()
            # == Run <count> motions ==
            elif key in count_motions:
                count = int(self.counts[0] or '1')
                tc = do_count_motion(key, count, QTC.MoveAnchor)
                self.set_cursor(tc)
                self.clear()
            # == Start an operation ==
            elif key in motion_operators:
                self.ops.append(key)
                self.counts.append('')
            else:
                self.clear()
        else:
            # TODO: warn
            self.clear()
        return None
