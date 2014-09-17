from operator import itemgetter
import re

from PyQt4 import QtCore, QtGui

from common import Configable

class ChapterSidebar(QtGui.QListWidget, Configable):
    goto_line = QtCore.pyqtSignal(int)
    error = QtCore.pyqtSignal(str)

    def __init__(self, settingsmanager, get_text):
        super().__init__()
        self.init_settings_functions(settingsmanager)
        self.get_text = get_text
        self.setDisabled(True)
        self.chapters_detected = False
        self.hide()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.update_list()
            if self.chapters_detected:
                self.show()
            else:
                self.error.emit('No chapters detected')

    def update_list(self):
        self.clear()
        prefix = self.get_setting('prologue chapter name')
        trigger = self.get_setting('chapter trigger string')
        chapter_strings = self.get_setting('chapter strings')
        text = self.get_text().splitlines()
        result = update_list_data(text, trigger, prefix, chapter_strings)
        if result is None:
            self.chapters_detected = False
            return
        self.linenumbers, items = result
        self.addItems(items)
        self.mod_items_fonts(bold=True)
        self.setFixedWidth(self.sizeHintForColumn(0)+5)
        self.mod_items_fonts(bold=False)
        self.item(0).setFont(mod_font(self.item(0), bold=True))
        self.chapters_detected = True

    def update_active_chapter(self, blocknumber):
        """
        Update the list to make the chapter the cursor is in bold.
        Triggered by moving the cursor (a signal from textarea.py).
        """
        if not self.count() or not self.isVisible():
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
        elif re.match(r'c\d+', arg):
            self.update_list()
            if not self.chapters_detected:
                self.error.emit('No chapters detected')
                return
            chapter = int(arg[1:])
            if chapter in range(len(self.linenumbers)):
                self.goto_line.emit(self.linenumbers[chapter])
            else:
                self.error.emit('Invalid chapter number')
        else:
            self.error.emit('Invalid line or chapter number')

    def get_chapter_text(self, chapter):
        self.update_list()
        if not self.chapters_detected:
            self.error.emit('No chapters detected')
            return
        lines = self.get_text().splitlines()
        if chapter not in range(len(self.linenumbers)):
            self.error.emit('Invalid chapter number')
            return
        ln = self.linenumbers + [len(lines)+1]
        text = '\n'.join(lines[ln[chapter]:ln[chapter+1]-1]).strip('\n\t ')
        if not text:
            self.error.emit('Chapter is only whitespace, ignoring')
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

def update_list_data(text, trigger, prefix, chapter_strings):
    if not text:
        return
    # Find all remotely possible lines (linenumber, text)
    rough_list = [(n,t) for n,t in enumerate(text, 1) if t.startswith(trigger)]
    if not rough_list:
        return
    # Find only those that match the regexes
    # Match to every rawstring possible, but overwrite earlier if needed
    out = {}
    for rx_str, template in chapter_strings: # all combinations
        rx = re.compile(rx_str)
        for x in rough_list: # all lines
            if rx.match(x[1]):
                out[x[0]] = template.format(**rx.match(x[1]).groupdict()).strip()
    if not out:
        return
    linenumbers, chapterlist = zip(*sorted(out.items(), key=itemgetter(0)))
    chapter_lengths = get_chapter_wordcounts(linenumbers, text)
    items = ['{}\n   {}'.format(x,y) for x,y in zip(chapterlist, chapter_lengths)]
    if linenumbers[0] > 1:
        wc = len(re.findall(r'\S+', '\n'.join(text[:linenumbers[0]-1])))
        linenumbers = [0] + list(linenumbers)
        items.insert(0, prefix + '\n   ' + str(wc))
    return linenumbers, items

def get_chapter_wordcounts(real_chapter_lines, text):
    """ Return a list of the word count for each chapter. """
    chapter_lines = list(real_chapter_lines) + [len(text)]
    return [len(re.findall(r'\S+', '\n'.join(text[chapter_lines[i]:chapter_lines[i+1]-1])))
            for i in range(len(chapter_lines)-1)]
