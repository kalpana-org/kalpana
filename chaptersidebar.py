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

from operator import itemgetter
import re

from PyQt4 import QtCore, QtGui

from common import Configable, strip_metadata

class ChapterError(Exception):
    pass

class ChapterSidebar(QtGui.QListWidget, Configable):
    goto_line = QtCore.pyqtSignal(int)
    error = QtCore.pyqtSignal(str)

    def __init__(self, settingsmanager, get_text, get_text_cursor):
        super().__init__()
        self.init_settings_functions(settingsmanager)
        self.get_text = get_text
        self.get_text_cursor = get_text_cursor
        self.setDisabled(True)
        self.error_reasons = {
            'no chapters': 'No chapters detected!',
            'no settings': 'No chapter settings specified in the config!',
            'broken settings': 'Chapter settings are broken, fix them!'
        }
        self.current_error = None
        self.linenumbers = []
        self.pos = 1
        self.hide()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.update_list()
            if not self.current_error:
                self.show()
            else:
                self.error.emit(self.error_reasons[self.current_error])

    def update_list(self):
        self.clear()
        prologuename = self.get_setting('prologue chapter name')
        chapter_strings = self.get_setting('chapter strings')
        completeflags = self.get_setting('complete flags')
        completemarker = self.get_setting('complete marker')
        if not chapter_strings:
            self.current_error = 'no settings'
            return
        try:
            validate_chapter_strings(chapter_strings)
        except AssertionError:
            self.current_error = 'broken settings'
            return
        lines = self.get_text().splitlines()
        try:
            self.linenumbers, items = get_chapters_data(lines, prologuename, chapter_strings, completeflags, completemarker)
        except ChapterError as e:
            self.current_error = str(e)
        else:
            self.addItems([name for name, complete in items])
            self.mod_items_fonts(bold=True)
            self.setFixedWidth(self.sizeHintForColumn(0)+5)
            self.mod_items_fonts(bold=False)
            self.set_not_complete_items(complete for name, complete in items)
            self.update_active_chapter(self.get_text_cursor().blockNumber(), force=True)
            self.current_error = None

    def update_active_chapter(self, blocknumber, force=False):
        """
        Update the list to make the chapter the cursor is in bold.
        Triggered by moving the cursor (a signal from textarea.py).
        """
        if not force and (not self.count() or not self.isVisible()):
            return
        self.pos = blocknumber+1
        self.mod_items_fonts(bold=False)
        for n, ch in list(enumerate(self.linenumbers))[::-1]:
            if self.pos >= ch:
                i = self.item(n)
                i.setFont(mod_font(i, bold=True))
                break

    def goto_next_chapter(self):
        self.update_list()
        for n, linenum in enumerate(self.linenumbers):
            if n == len(self.linenumbers)-1:
                return
            if self.pos >= linenum and self.pos < self.linenumbers[n+1]:
                self.goto_line.emit(self.linenumbers[n+1])
                return

    def goto_prev_chapter(self):
        self.update_list()
        for n, linenum in enumerate(self.linenumbers):
            if n == len(self.linenumbers)-1 or (self.pos >= linenum and self.pos < self.linenumbers[n+1]):
                if n == 0:
                    return
                self.goto_line.emit(self.linenumbers[n-1])
                return


    def goto_line_or_chapter(self, arg):
        """ Scroll to the specified line or chapter. """
        if arg.isdigit():
            self.goto_line.emit(int(arg))
        elif re.match(r'c-?\d+', arg):
            self.update_list()
            if self.current_error:
                self.error.emit(self.error_reasons[self.current_error])
                return
            chapter = int(arg[1:].strip('-'))
            if chapter in range(1, len(self.linenumbers)):
                if arg[1] == '-':
                    chapter = -chapter
                self.goto_line.emit(self.linenumbers[chapter])
            else:
                self.error.emit('Invalid chapter number')
        else:
            self.error.emit('Invalid line or chapter number')

    def get_chapter_text(self, chapter, stripmetadata=True):
        self.update_list()
        if self.current_error:
            self.error.emit(self.error_reasons[self.current_error])
            return
        lines = self.get_text().splitlines()
        try:
            text = get_chapter_text(chapter, lines, self.linenumbers, stripmetadata)
        except ChapterError as e:
            self.error.emit(str(e))
        else:
            return text

    def mod_items_fonts(self, bold):
        for item_nr in range(self.count()):
            i = self.item(item_nr)
            i.setFont(mod_font(i, bold=bold))

    def set_not_complete_items(self, completelist):
        completetextalpha = self.get_setting('complete item alpha')
        incompletecolor = QtGui.QColor(self.get_style_setting('sidebar text color'))
        completecolor = QtGui.QColor(incompletecolor)
        completecolor.setAlphaF(completetextalpha)
        textcolors = [incompletecolor, completecolor]
        for item_nr, complete in zip(range(self.count()), completelist):
            i = self.item(item_nr)
            i.setFont(mod_font(i, italic=complete))
            i.setTextColor(textcolors[complete])


def mod_font(item, bold=None, italic=None):
    font = item.font()
    if bold is not None:
        font.setBold(bold)
    if italic is not None:
        font.setItalic(italic)
    return font

def get_chapter_text(chapter, lines, linenumbers, stripmetadata=True):
    """ Return the text inside the specified chapter. """
    if chapter not in range(len(linenumbers)):
        raise ChapterError('Invalid chapter number')
    ln = linenumbers + [len(lines)+1]
    chapterlines = lines[ln[chapter]:ln[chapter+1]-1]
    if stripmetadata:
        chapterlines = strip_metadata(chapterlines, impliedchapter=True)
    text = '\n'.join(chapterlines).strip('\n\t ')
    if not text:
        raise ChapterError('Chapter is only whitespace, ignoring')
    else:
        return text

def validate_chapter_strings(chapter_strings):
    """
    Make sure the chapter strings are as correct as possible.
    Return None on success and raise AssertionError on failure.
    """
    for item in chapter_strings:
        assert isinstance(item, list) and len(item) == 2
        rx_str, template = item
        assert isinstance(rx_str, str) and isinstance(template, str)
        assert rx_str.strip() and template.strip()
        try:
            rx = re.compile(rx_str)
        except re.error:
            raise AssertionError()
        try:
            template.format(**rx.groupindex)
        except KeyError:
            raise AssertionError()

def get_chapters_data(lines, prologuename, chapter_strings, completeflags, completemarker):
    """
    Return two lists:
        linenumbers - the numbers of the lines where each chapter begins
        items - a pair with string with name and wordcount to add to the
                sidebar widget and a bool set to true if the chapter is
                complete.
    """
    if not lines:
        raise ChapterError('no chapters')
    # Find lines that match the regexes
    # Match to every rawstring possible, but overwrite earlier if needed
    out = {}
    for rx_str, template in chapter_strings: # all combinations
        rx = re.compile(rx_str)
        for n, line in enumerate(lines, 1): # all lines
            # Remove potential complete flag from the end of the string
            if completeflags:
                complete = False
                for flag in completeflags:
                    if line.endswith(flag):
                        complete = True
                        line = line[:-len(flag)].lstrip()
                        break
            else:
                complete = True
            if rx.match(line):
                matchdict = rx.match(line).groupdict()
                # This happens if not all groups in the regex are matched
                if None in matchdict.values():
                    raise ChapterError('broken settings')
                out[n] = (template.format(**matchdict).strip(), complete)
    if not out:
        raise ChapterError('no chapters')
    out[0] = (prologuename, False)
    linenumbers, chapterlist = zip(*sorted(out.items(), key=itemgetter(0)))
    chapter_lengths = get_chapter_wordcounts(linenumbers, lines)
    items = [('{}\n   {} {}'.format(name, length, completemarker if complete else ''), complete)
             for (name, complete), length in zip(chapterlist, chapter_lengths)]
    return list(linenumbers), items

def get_chapter_wordcounts(real_chapter_lines, lines):
    """
    Return a list of the word count for each chapter.

    real_chapter_lines - a list of line numbers where a chapter starts,
                         including the prologue that starts on line 0.
    """
    chapter_lines = list(real_chapter_lines) + [len(lines)+1]
    return [len(re.findall(r'\S+', '\n'.join(lines[chapter_lines[i]:chapter_lines[i+1]-1])))
            for i in range(len(chapter_lines)-1)]
