from operator import itemgetter
import re

from PyQt4 import QtCore, QtGui

from common import Configable

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
            self.linenumbers, items = get_chapters_data(lines, prologuename, chapter_strings)
        except ChapterError as e:
            self.current_error = str(e)
        else:
            self.addItems(items)
            self.mod_items_fonts(bold=True)
            self.setFixedWidth(self.sizeHintForColumn(0)+5)
            self.mod_items_fonts(bold=False)
            self.update_active_chapter(self.get_text_cursor().blockNumber(), force=True)
            self.current_error = None

    def update_active_chapter(self, blocknumber, force=False):
        """
        Update the list to make the chapter the cursor is in bold.
        Triggered by moving the cursor (a signal from textarea.py).
        """
        if not force and (not self.count() or not self.isVisible()):
            return
        pos = blocknumber+1
        self.mod_items_fonts(bold=False)
        for n, ch in list(enumerate(self.linenumbers))[::-1]:
            if pos >= ch:
                i = self.item(n)
                i.setFont(mod_font(i, True))
                break

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

    def get_chapter_text(self, chapter):
        self.update_list()
        if self.current_error:
            self.error.emit(self.error_reasons[self.current_error])
            return
        lines = self.get_text().splitlines()
        try:
            text = get_chapter_text(chapter, lines, self.linenumbers)
        except ChapterError as e:
            self.error.emit(str(e))
        else:
            return text

    def mod_items_fonts(self, bold):
        for item_nr in range(self.count()):
            i = self.item(item_nr)
            i.setFont(mod_font(i, bold))


def mod_font(item, bold):
    font = item.font()
    font.setBold(bold)
    return font

def get_chapter_text(chapter, lines, linenumbers):
    """ Return the text inside the specified chapter. """
    if chapter not in range(len(linenumbers)):
        raise ChapterError('Invalid chapter number')
    ln = linenumbers + [len(lines)+1]
    text = '\n'.join(lines[ln[chapter]:ln[chapter+1]-1]).strip('\n\t ')
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

def get_chapters_data(lines, prologuename, chapter_strings):
    """
    Return two lists:
        linenumbers - the numbers of the lines where each chapter begins
        items - string with name and wordcount to add to the sidebar widget.
    """
    if not lines:
        raise ChapterError('no chapters')
    # Find lines that match the regexes
    # Match to every rawstring possible, but overwrite earlier if needed
    out = {}
    for rx_str, template in chapter_strings: # all combinations
        rx = re.compile(rx_str)
        for n, line in enumerate(lines, 1): # all lines
            if rx.match(line):
                matchdict = rx.match(line).groupdict()
                # This happens if not all groups in the regex are matched
                if None in matchdict.values():
                    raise ChapterError('broken settings')
                out[n] = template.format(**matchdict).strip()
    if not out:
        raise ChapterError('no chapters')
    out[0] = prologuename
    linenumbers, chapterlist = zip(*sorted(out.items(), key=itemgetter(0)))
    chapter_lengths = get_chapter_wordcounts(linenumbers, lines)
    items = ['{}\n   {}'.format(x,y)
             for x,y in zip(chapterlist, chapter_lengths)]
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
