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
import subprocess
import sys
try:
    import enchant
except ImportError:
    enchant_present = False
else:
    enchant_present = True

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSignal

from libsyntyche.common import write_file
from libsyntyche.filehandling import FileHandler
from linewidget import LineTextWidget
from common import Configable, SettingsError


class TextArea(LineTextWidget, FileHandler, Configable):
    print_sig = pyqtSignal(str)
    error_sig = pyqtSignal(str)
    hide_terminal = pyqtSignal()
    prompt_sig = pyqtSignal(str)
    cursor_position_changed = pyqtSignal(int)
    wordcount_changed = pyqtSignal(int)
    modification_changed = pyqtSignal(bool)
    filename_changed = pyqtSignal(str)
    file_created = pyqtSignal()
    file_opened = pyqtSignal()
    file_saved = pyqtSignal()

    def __init__(self, parent, settingsmanager):
        super().__init__(parent)
        self.init_settings_functions(settingsmanager)
        # This function is actually in linewidget.py
        self.register_setting('Line Numbers', self.set_number_bar_visibility)
        self.register_setting('Vertical Scrollbar', self.set_vscrollbar_visibility)
        self.register_setting('max Page Width', self.set_maximum_width)
        self.register_setting('Show WordCount in titlebar', self.set_show_wordcount)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setTabStopWidth(30)
        self.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

        self.blockCountChanged.connect(self.new_line)
        def new_cursor_position():
            blocknumber = self.textCursor().blockNumber()
            self.cursor_position_changed.emit(blocknumber)
        self.cursorPositionChanged.connect(new_cursor_position)

        self.blocks = 0
        self.search_buffer = None
        self.highlighter = None
        self.file_path = ''
        self.show_wordcount = False

        # Scrollbar fadeout
        self.hidescrollbartimer = QtCore.QTimer(self)
        self.hidescrollbartimer.setInterval(1000)
        self.hidescrollbartimer.setSingleShot(True)
        self.hidescrollbartimer.timeout.connect(self.hide_scrollbar)
        self.verticalScrollBar().valueChanged.connect(self.scrollbar_moved)
        self.hidescrollbareffect = QtGui.QGraphicsOpacityEffect(self.verticalScrollBar())
        self.verticalScrollBar().setGraphicsEffect(self.hidescrollbareffect)
        a = QtCore.QPropertyAnimation(self.hidescrollbareffect, 'opacity')
        a.setEasingCurve(QtCore.QEasingCurve.InOutQuint)
        a.setDuration(500)
        a.setStartValue(1)
        a.setEndValue(0)
        self.hidescrollbaranim = a
        self.scrollbar_moved()

    def shake(self):
        a = QtCore.QPropertyAnimation(self, 'pos')
        a.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        a.setDuration(500)
        a.setKeyValueAt(0, self.pos())
        a.setKeyValueAt(0.2, self.pos() + QtCore.QPoint(40,0))
        a.setKeyValueAt(0.4, self.pos() - QtCore.QPoint(80,0))
        a.setKeyValueAt(0.6, self.pos() + QtCore.QPoint(40,0))
        a.setKeyValueAt(0.8, self.pos() - QtCore.QPoint(80,0))
        a.setKeyValueAt(1, self.pos())
        a.start(QtCore.QPropertyAnimation.DeleteWhenStopped)
        self.shakeanim = a

    def scrollbar_moved(self):
        self.hidescrollbaranim.stop()
        self.hidescrollbareffect.setOpacity(1)
        self.hidescrollbartimer.start()

    def hide_scrollbar(self):
        self.hidescrollbaranim.start()

    # Override
    def wheelEvent(self, event):
        # Can't call super().wheelEvent b/c it sends the event to the parent
        # when at the top or bottom of the page. Parent then sends it back
        # creating an infinite loop. Just ftr.
        steps = -event.delta()//120
        multiplier = 3 # To make it scroll as much as default
        if event.orientation() == QtCore.Qt.Horizontal:
            sb = self.horizontalScrollBar()
        elif event.orientation() == QtCore.Qt.Vertical:
            sb = self.verticalScrollBar()
        sb.setValue(sb.value() + sb.singleStep()*steps*multiplier)
        event.accept()

    def print_(self, arg):
        self.print_sig.emit(arg)

    # ==== Setting callbacks ========================================
    def set_vscrollbar_visibility(self, arg):
        policy = {'on': QtCore.Qt.ScrollBarAlwaysOn,
                  'auto': QtCore.Qt.ScrollBarAsNeeded,
                  'off': QtCore.Qt.ScrollBarAlwaysOff}
        if arg not in policy:
            raise SettingsError('Vertical scrollbar setting "{}" is not valid!'.format(arg))
        self.setVerticalScrollBarPolicy(policy[arg])

    def set_maximum_width(self, value):
        if value < 1:
            raise SettingsError('A negative page width is not possible!')
        self.setMaximumWidth(value)

    def set_show_wordcount(self, value):
        self.show_wordcount = value
        self.wordcount_changed.emit(self.get_wordcount())
    # ===============================================================

    def get_wordcount(self):
        return len(re.findall(r'\S+', self.document().toPlainText()))

    def print_wordcount(self):
        self.print_('Words: {}'.format(self.get_wordcount()))

    def print_filename(self, arg):
        """ Wrapper callback for the f command. """
        try:
            result = get_file_info(arg, self.file_path, self.is_modified)
        except KeyError as e:
            self.error(str(e))
        else:
            self.print_(result)

    def goto_line(self, raw_line_num):
        if type(raw_line_num) == str:
            if not raw_line_num.strip().isdigit():
                self.error('Invalid line number')
                return
            raw_line_num = int(raw_line_num.strip())
        line_num = min(raw_line_num, self.document().blockCount())
        block = self.document().findBlockByNumber(line_num - 1)
        new_cursor = QtGui.QTextCursor(block)
        self.setTextCursor(new_cursor)
        self.centerCursor()
        self.hide_terminal.emit()
        self.setFocus()


    def new_line(self, blocks):
        """ Generate auto-indentation if the option is enabled. """
        if self.get_setting('Auto-Indent') and blocks > self.blocks:
            cursor = self.textCursor()
            blocknum = cursor.blockNumber()
            prevblock = self.document().findBlockByNumber(blocknum-1)
            indent = re.match(r'[\t ]*', prevblock.text()).group(0)
            cursor.insertText(indent)
        self.blocks = blocks

    ## ==== Spellcheck ==================================================== ##

    class Highlighter(QtGui.QSyntaxHighlighter):
        def __init__(self, *args):
            super().__init__(*args)
            self.dict = None

        def highlightBlock(self, text):
            if not self.dict:
                return

            format = QtGui.QTextCharFormat()
            format.setUnderlineColor(QtCore.Qt.red)
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)

            for word in re.finditer(r'(?i)[\w\']+', text):
                if not self.dict.check(word.group().strip("'")):
                    self.setFormat(word.start(), word.end() - word.start(), format)

    def spellcheck(self, arg):
        def get_word():
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.WordUnderCursor)
            return cursor.selectedText()

        if not enchant_present:
            self.error('PyEnchant spell check dependency not installed!')
            return
        if self.highlighter is None:
            self.highlighter = self.Highlighter(self)
            self.set_spellcheck_language(self.get_setting('default spellcheck language'))
        if arg == '?':
            self.print_('&: toggle, &en_US: set language, &=: check word, &+: add word')
        elif arg == '=':
            word = get_word()
            if re.match(r'[\w\']+$', word):
                suggestions = ', '.join(self.highlighter.dict.suggest(word)[:3])
                self.print_('{}: {}'.format(word, suggestions))
        elif arg == '+':
            word = get_word()
            if re.match(r'[\w\']+$', word):
                self.prompt('&+' + word)
        elif arg.startswith('+'):
            self.highlighter.dict.add_to_pwl(arg[1:])
            lang = self.highlighter.dict.tag
            self.highlighter.rehighlight()
            self.print_('Added to {} dictionary: {}'.format(lang, arg[1:]))
        elif not arg:
            if self.highlighter.document() is None:
                self.highlighter.setDocument(self.document())
                lang = self.highlighter.dict.tag
                self.print_('Spell check is now on ({})'.format(lang))
            else:
                self.highlighter.setDocument(None)
                self.print_('Spell check is now off')
        else:
            self.set_spellcheck_language(arg)

    def set_spellcheck_language(self, lang):
        if lang in [x for x,y in enchant.list_dicts()]:
            pwlpath = self.get_path('spellcheck-pwl')
            pwl = os.path.join(pwlpath, lang+'.pwl')
            self.highlighter.dict = enchant.DictWithPWL(lang, pwl=pwl)
            self.highlighter.rehighlight()
            self.print_('Language set to {}'.format(lang))
        else:
            self.error('Language {} does not exist!'.format(lang))


    ## ==== Search & replace ================================================ ##

    def search_and_replace(self, arg):
        def generate_flags(flagstr):
            self.search_flags = QtGui.QTextDocument.FindFlags()
            if 'b' in flagstr:
                self.search_flags |= QtGui.QTextDocument.FindBackward
            if 'i' not in flagstr:
                self.search_flags |= QtGui.QTextDocument.FindCaseSensitively
            if 'w' in flagstr:
                self.search_flags |= QtGui.QTextDocument.FindWholeWords

        search_rx = re.compile(r'([^/]|\\/)+$')
        search_flags_rx = re.compile(r'([^/]|\\/)*?([^\\]/[biw]*)$')
        replace_rx = re.compile(r"""
            (?P<search>([^/]|\\/)*?[^\\])
            /
            (?P<replace>(([^/]|\\/)*[^\\])?)
            /
            (?P<flags>[abiw]*)
            $
        """, re.VERBOSE)

        if search_rx.match(arg):
            self.search_buffer = search_rx.match(arg).group(0)
            self.search_flags = QtGui.QTextDocument.FindCaseSensitively
            self.search_next()

        elif search_flags_rx.match(arg):
            self.search_buffer, flags = search_flags_rx.match(arg).group(0).rsplit('/', 1)
            generate_flags(flags)
            self.search_next()

        elif replace_rx.match(arg):
            match = replace_rx.match(arg)
            self.search_buffer = match.group('search')
            generate_flags(match.group('flags'))
            if 'a' in match.group('flags'):
                self.replace_all(match.group('replace'))
            else:
                self.replace_next(match.group('replace'))

        else:
            self.error('Malformed search/replace expression')

    def searching_backwards(self):
        return QtGui.QTextDocument.FindBackward & self.search_flags

    def search_next(self):
        if self.search_buffer is None:
            self.error('No previous searches')
            return
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer, self.search_flags)
        if not found:
            if not self.textCursor().atStart() \
                        or (self.searching_backwards() and not self.textCursor().atEnd()):
                if self.searching_backwards():
                    self.moveCursor(QtGui.QTextCursor.End)
                else:
                    self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer, self.search_flags)
                if not found:
                    self.setTextCursor(temp_cursor)
                    self.error('Text not found')
            else:
                self.setTextCursor(temp_cursor)
                self.error('Text not found')


    def replace_next(self, replace_buffer):
        temp_cursor = self.textCursor()
        found = self.find(self.search_buffer, self.search_flags)
        if not found:
            if not self.textCursor().atStart() \
                        or (self.searching_backwards() and not self.textCursor().atEnd()):
                if self.searching_backwards():
                    self.moveCursor(QtGui.QTextCursor.End)
                else:
                    self.moveCursor(QtGui.QTextCursor.Start)
                found = self.find(self.search_buffer, self.search_flags)
                if not found:
                    self.setTextCursor(temp_cursor)
        if found:
            t = self.textCursor()
            t.insertText(replace_buffer)
            l = len(replace_buffer)
            t.setPosition(t.position() - l)
            t.setPosition(t.position() + l, QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(t)
            self.print_('Replaced on line {}, pos {}'
                             ''.format(t.blockNumber(), t.positionInBlock()))
        else:
            self.error('Text not found')


    def replace_all(self, replace_buffer):
        temp_cursor = self.textCursor()
        times = 0
        self.moveCursor(QtGui.QTextCursor.Start)
        while True:
            found = self.find(self.search_buffer, self.search_flags)
            if found:
                self.textCursor().insertText(replace_buffer)
                times += 1
            else:
                break
        if times:
            self.print_('{0} instance{1} replaced'.format(times, 's'*(times>0)))
        else:
            self.error('Text not found')
        self.setTextCursor(temp_cursor)


    ## ==== File ops help functions ======================================= ##

    def set_filename(self, filename='', new=False):
        """ Set both the output file and the title to filename. """
        assert bool(filename) != new # Either a filename or new, not both/none
        self.file_path = '' if new else filename
        self.filename_changed.emit('New file' if new else filename)

    ## ==== Overloads from FileHandler ==================================== ##

    def error(self, text):
        self.error_sig.emit(text)

    def prompt(self, text):
        self.prompt_sig.emit(text)

    def is_modified(self):
        return self.document().isModified()

    def dirty_window_and_start_in_new_process(self):
        """ Return True if the file is empty and unsaved. """
        return self.get_setting('open in New Window') and (self.document().isModified() or self.file_path)

    def post_new(self):
        self.document().clear()
        self.document().setModified(False)
        self.blocks = 1
        self.set_filename(new=True)
        self.file_created.emit()

    def open_file(self, filename):
        """
        Main open file function
        """
        encodings = ('utf-8', 'latin1')
        for e in encodings:
            try:
                with open(filename, encoding=e) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                continue
            else:
                self.document().setPlainText(''.join(lines))
                self.document().setModified(False)
                self.blocks = self.blockCount()
                self.set_filename(filename)
                if self.show_wordcount:
                    self.wordcount_changed.emit(self.get_wordcount())
                self.moveCursor(QtGui.QTextCursor.Start)
                self.file_opened.emit()
                return True
        return False

    def write_file(self, filename):
        write_file(filename, self.document().toPlainText())

    def post_save(self, filename):
        if self.show_wordcount:
            self.wordcount_changed.emit(self.get_wordcount())
        self.set_filename(filename)
        self.document().setModified(False)
        self.file_saved.emit()


# ==== Loose functions ==========================================

def get_file_info(arg, file_path, is_modified):
    """ Parse the f command and return the requested information """
    if arg not in ('n','d','m','?',''):
        raise KeyError('Invalid argument')
    if arg == '?':
        return 'f=full path, fn=name, fd=directory, fm=modified'
    if file_path:
        if arg == 'n':
            return os.path.basename(file_path)
        elif arg == 'd':
            return os.path.dirname(file_path)
        elif arg == 'm':
            x = (not is_modified()) * 'not '
            return 'File is {}modified'.format(x)
        else:
            return file_path
    else:
        return 'File is not saved yet'
