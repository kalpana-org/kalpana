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

from libsyntyche.common import read_file, write_file
from libsyntyche.filehandling import FileHandler
from libsyntyche.texteditor import SearchAndReplaceable
from linewidget import LineTextWidget
from common import Configable, SettingsError, keywordpatterns


class TextArea(LineTextWidget, FileHandler, Configable, SearchAndReplaceable):
    print_sig = pyqtSignal(str)
    error_sig = pyqtSignal(str)
    hide_terminal = pyqtSignal()
    prompt_sig = pyqtSignal(str)
    cursor_position_changed = pyqtSignal(int)
    wordcount_changed = pyqtSignal(int)
    modification_changed = pyqtSignal(bool)
    update_recent_files = pyqtSignal()
    filename_changed = pyqtSignal(str)
    file_created = pyqtSignal()
    file_opened = pyqtSignal()
    file_saved = pyqtSignal()

    def __init__(self, parent, settingsmanager):
        super().__init__(parent)
        self.init_settings_functions(settingsmanager)
        self.initialize_search_and_replace(self.error, self.print_)
        # This function is actually in linewidget.py
        self.register_setting('Line Numbers', self.set_number_bar_visibility)
        self.register_setting('Vertical Scrollbar', self.set_vscrollbar_visibility)
        self.register_setting('max Page Width', self.set_maximum_width)
        self.register_setting('Show WordCount in titlebar', self.set_show_wordcount)
        self.register_setting('Miscellaneous Animations', self.set_animations_active)
        self.register_setting('Show Formatting', self.set_formatting_active)

        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setTabStopWidth(30)
        self.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

        self.blockCountChanged.connect(self.new_line)
        def new_cursor_position():
            if self.highlighter:
                block = self.textCursor().block()
                self.highlighter.cursor_position_changed(block)
            blocknumber = self.textCursor().blockNumber()
            self.cursor_position_changed.emit(blocknumber)
        self.cursorPositionChanged.connect(new_cursor_position)

        self.blocks = 0
        self.highlighter = self.Highlighter(self, self.document(), self.get_style_setting)
        self.file_path = ''
        self.show_wordcount = False
        self.animations_active = False

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
        if not self.animations_active:
            return
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
        if not self.animations_active:
            return
        self.hidescrollbaranim.stop()
        self.hidescrollbareffect.setOpacity(1)
        self.hidescrollbartimer.start()

    def hide_scrollbar(self):
        if not self.animations_active:
            return
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

    def paintEvent(self, ev):
        super().paintEvent(ev)
        pagebottom = self.viewport().height()
        block = self.firstVisibleBlock()
        linenum = block.blockNumber()
        viewport_offset = self.contentOffset()
        painter = QtGui.QPainter(self.viewport())
        fg = QtGui.QColor(self.get_style_setting('document text color'))
        fg.setAlphaF(0.4)
        bg = QtGui.QColor(self.get_style_setting('document background'))
        painter.setPen(QtGui.QPen(QtGui.QBrush(fg), 2))
        hrmargin = 0.3
        while block.isValid():
            linenum += 1
            rect = self.blockBoundingGeometry(block).translated(viewport_offset)
            if rect.y() > pagebottom:
                break
            if block in self.highlighter.hrblocks and block != self.textCursor().block():
                painter.fillRect(rect, bg)
                x1 = rect.x() + rect.width()*hrmargin
                x2 = rect.x() + rect.width()*(1-hrmargin)
                y = rect.y() + rect.height()*0.5
                painter.drawLine(x1,y, x2,y)
            block = block.next()
        painter.end()

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

    def set_animations_active(self, value):
        if not value:
            self.hidescrollbaranim.stop()
            self.hidescrollbartimer.stop()
            self.hidescrollbareffect.setOpacity(1)
        elif value and not self.animations_active:
            self.hidescrollbartimer.start()
        self.animations_active = value

    def set_formatting_active(self, value):
        self.highlighter.formatting_active = value
        self.highlighter.rehighlight()
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


    def add_to_recent_files(self, filename):
        listfname = self.get_path('recentfiles')
        length = self.get_setting('recent file list length')
        # This fixes both symlinks and relative paths
        realfname = os.path.realpath(filename)
        recentfiles = [realfname]
        if os.path.exists(listfname):
            oldrecentfiles = read_file(listfname).splitlines()
            recentfiles += [x for x in oldrecentfiles if x != realfname][:length-1]
        write_file(listfname, '\n'.join(recentfiles))
        self.update_recent_files.emit()


    ## ==== Spellcheck ==================================================== ##

    class Highlighter(QtGui.QSyntaxHighlighter):
        def __init__(self, parent, document, get_style_setting):
            super().__init__(document)
            self.dict = None
            self.get_style_setting = get_style_setting
            self.spellcheck_active = False
            self.formatting_active = False
            self.activeblock = None
            self.lastblock = None
            self.parent = parent
            self.hrblocks = []

        def cursor_position_changed(self, block):
            self.lastblock = self.activeblock
            self.activeblock = block
            for b in [self.lastblock, self.activeblock]:
                if not b:
                    continue
                self.rehighlightBlock(b)
                if b in self.hrblocks:
                    self.document().markContentsDirty(b.position(), b.length())

        def previousBlockState(self):
            return max(0, super().previousBlockState())

        def highlightBlock(self, text):
            def set_line_format(charformat):
                l = sum(2 if ord(x)>65535 else 1 for x in text)
                self.setFormat(0, l, charformat)
            # block states
            defaultstate = -1
            chapterstate = 0b00001
            sectionstate = 0b00010
            linesfound = {
                'description': 0b00100,
                'tags': 0b01000,
                'time': 0b10000,
            }
            boldstate = 0b100000
            italicstate = 0b1000000
            try:
                fgname = self.get_style_setting('document text color')
            except:
                fgname = '#000'
            fg = QtGui.QColor(fgname)
            # hide the metadata lines a bit
            charformat = QtGui.QTextCharFormat()
            if self.formatting_active:
                if re.fullmatch(keywordpatterns['chapter'], text):
                    self.setCurrentBlockState(chapterstate)
                    charformat.setFontWeight(QtGui.QFont.Bold)
                    set_line_format(charformat)
                    return
                if re.fullmatch(keywordpatterns['section'], text):
                    #self.setCurrentBlockState(sectionstate)
                    if not self.activeblock or self.currentBlock() != self.activeblock:
                        fg.setAlphaF(0.5)
                        charformat.setForeground(QtGui.QBrush(fg))
                    charformat.setFontWeight(QtGui.QFont.Bold)
                    set_line_format(charformat)
                    return
                if re.fullmatch(keywordpatterns['meta'], text):
                    if not self.activeblock or self.currentBlock() != self.activeblock:
                        fg.setAlphaF(0.1)
                        charformat.setForeground(QtGui.QBrush(fg))
                        charformat.setFontItalic(True)
                    set_line_format(charformat)
                    return
                state = self.previousBlockState()
                fg.setAlphaF(0.3)
                if state & chapterstate:
                    for line in linesfound.keys():
                        if re.fullmatch(keywordpatterns[line], text) \
                                    and not linesfound[line] & state:
                            self.setCurrentBlockState(state | linesfound[line])
                            if not self.activeblock or self.currentBlock() != self.activeblock:
                                charformat.setForeground(QtGui.QBrush(fg))
                                set_line_format(charformat)
                            return
                # Bold text
            #    f = QtGui.QTextCharFormat()
            #    f.setFontWeight(QtGui.QFont.Bold)
            #    for chunk in re.finditer(r'\*.+?\*', text):
            #        self.setFormat(chunk.start(), chunk.end() - chunk.start(), f)
            #    # TODO
            #    todoformat = QtGui.QTextCharFormat()
            #    todoformat.setFontWeight(QtGui.QFont.Bold)
            #    todoformat.setForeground(QtCore.Qt.red)
            #    for todo in re.finditer(r'(?i)#todo:?', text):
            #        self.setFormat(todo.start(), todo.end() - todo.start(), todoformat)
            #if self.spellcheck_active:
            #    charformat.setUnderlineColor(QtCore.Qt.red)
            #    charformat.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            #    for word in re.finditer(r'(?i)[\w\']+', text):
            #        if not self.dict.check(word.group().strip("'")):
            #            self.setFormat(word.start(), word.end() - word.start(), charformat)
            #    charformat.setUnderlineColor(QtCore.Qt.blue)
            if re.fullmatch(r'(\s*\*\s*){3}', text):
                f = QtGui.QTextCharFormat()
                fg.setAlphaF(0.3)
                f.setForeground(fg)
                f.setFontPointSize(40)
                if self.currentBlock() not in self.hrblocks:
                    self.hrblocks.append(self.currentBlock())
                set_line_format(f)
                self.setCurrentBlockState(self.previousBlockState())
                return
            else:
                if self.currentBlock() in self.hrblocks:
                    self.hrblocks.remove(self.currentBlock())
            laststate = self.previousBlockState()
            bold = laststate & boldstate
            italic = laststate & italicstate
            fg.setAlphaF(0.5)
            for chunk in re.finditer(r'([^\s*/]+|//|/|\*\*|\*)', text):
                f = QtGui.QTextCharFormat()
                if self.formatting_active:
                    if chunk.group() == '*':
                        bold = not bold
                        f.setForeground(fg)
                        self.setFormat(chunk.start(), 1, f)
                        continue
                    if chunk.group() == '/':
                        italic = not italic
                        f.setForeground(fg)
                        self.setFormat(chunk.start(), 1, f)
                        continue
                    if bold:
                        f.setFontWeight(QtGui.QFont.Bold)
                    if italic:
                        f.setFontItalic(True)
                    if bold or italic:
                        self.setFormat(chunk.start(), chunk.end()-chunk.start(), f)
                    todo = re.search(r'(?i)#todo:?', chunk.group())
                    if todo:
                        f.setForeground(QtCore.Qt.red)
                        f.setFontWeight(QtGui.QFont.Bold)
                        self.setFormat(chunk.start()+todo.start(), todo.end()-todo.start(), f)
                if self.spellcheck_active:
                    f.setUnderlineColor(QtCore.Qt.red)
                    f.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
                    word = re.search(r'[\w\']+', chunk.group())
                    if word and not self.dict.check(word.group().strip("'")):
                        self.setFormat(chunk.start()+word.start(), word.end()-word.start(), f)

            currentstate = self.currentBlockState()
            if bold:
                currentstate |= boldstate
            else:
                currentstate &= ~boldstate
            if italic:
                currentstate |= italicstate
            else:
                currentstate &= ~italicstate
            self.setCurrentBlockState(currentstate)


    def spellcheck(self, arg):
        def get_word():
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.WordUnderCursor)
            return cursor.selectedText()

        if not enchant_present:
            self.error('PyEnchant spell check dependency not installed!')
            return
        if self.highlighter.dict is None:
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
            self.highlighter.spellcheck_active = not self.highlighter.spellcheck_active
            if self.highlighter.spellcheck_active:
                lang = self.highlighter.dict.tag
                self.print_('Spell check is now on ({})'.format(lang))
            else:
                self.print_('Spell check is now off')
        else:
            self.set_spellcheck_language(arg)

    def set_spellcheck_language(self, lang):
        if lang in [x for x,y in enchant.list_dicts()]:
            pwlpath = self.get_path('spellcheck-pwl')
            pwl = os.path.join(pwlpath, lang+'.pwl')
            self.highlighter.dict = enchant.DictWithPWL(lang, pwl=pwl)
            if self.highlighter.spellcheck_active:
                self.highlighter.rehighlight()
            self.print_('Language set to {}'.format(lang))
        else:
            self.error('Language {} does not exist!'.format(lang))


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

    def post_new(self, filename=''):
        self.document().clear()
        # Not sure if this is needed but explicit is better than implicit
        self.document().setModified(True)
        self.blocks = 1
        if not filename:
            self.set_filename(new=True)
        else:
            self.set_filename(filename)
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
                self.add_to_recent_files(filename)
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
        self.add_to_recent_files(filename)
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
