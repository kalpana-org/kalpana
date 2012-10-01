#!/usr/bin/python
# -*- coding: utf-8 -*-
## KALPANA
##
## Gender: Feminine
##
## Usage: Indian
##
## Other Scripts: कल्पना (Hindi)
## Means "imagining, fantasy" in Sanskrit.
##
## v0.2 - added line numbers, taken from
## v0.3 - did sum shit, added dragndrop, made stuff better
## v0.4 - find(/replace)
## http://www.japh.de/blog/qtextedit-with-line-numbers/
## Original code in MIT license

version = 0.4

import ConfigParser
import codecs
import datetime
import os
import os.path
import platform
import re
import sys
import subprocess

from math import ceil

from PySide import QtCore, QtGui
from PySide.QtCore import SIGNAL, Qt
from PySide.QtGui import QMessageBox
try:
    from PySide.QtGui import QGtkStyle
except ImportError:
    gtkpresent = False
else:
    gtkpresent = True
    
    

class App(QtGui.QMainWindow):
    def __init__(self, file_=''):
        super(App, self).__init__()

        # Accept drag & drop events
        self.setAcceptDrops(True)

        # Find the path to the config file
        system = platform.system()
        if system == 'Linux':
            self.cfgpath = os.path.join(os.getenv('HOME'), '.kalpana')
        else:
            self.cfgpath = os.path.join(sys.path[0], 'kalpana.ini')

        # Generate confige if none exists
        if not os.path.exists(self.cfgpath):
            self.defaultConfig()

        # Window title stuff
        self.wt_wordcount = 0
        self.wt_modified = False
        self.wt_file = u''

        # Layout
        layout0widget = QtGui.QWidget(self)
        layout0 = QtGui.QVBoxLayout(layout0widget)
        layout0.setSpacing(0)
        layout0.setContentsMargins(0,0,0,0)
        layoutwidget = QtGui.QWidget(self)
        layout = QtGui.QHBoxLayout(layoutwidget)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        self.setCentralWidget(layout0widget)
        layout0.addWidget(layoutwidget)

        # Text area
        self.textarea = LineTextWidget(self)
        self.document = self.textarea.document()
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.textarea.setTabStopWidth(30)
        layout.addWidget(self.textarea)
        self.findtext = ''
        self.replace1text = ''
        self.replace2text = ''
        
        # Terminal
        self.terminal = Terminal(self, layoutwidget)
        layout0.addWidget(self.terminal)

        # Misc settings etc
        self.filename = u''
        self.autoindent = False
        self.blocks = 1
        self.textarea.setContextMenuPolicy(Qt.PreventContextMenu)
        self.generateMsgbox()
        self.open_in_new_window = False

        # Signals/slots
        self.connect(self.document, SIGNAL('modificationChanged(bool)'),
                     self.toggleModified)
        self.connect(self.document, SIGNAL('contentsChanged()'), 
                     self.updateWordCount)
        self.connect(self.textarea, SIGNAL('blockCountChanged(int)'), 
                     self.newLine)
        self.connect(self.textarea, SIGNAL('ctrlSpacePressed'), 
                     self.switchFocus)

        # Keyboard shortcuts
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+N'), self, self.new)
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+O'), self, self.open_)
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+S'), self, self.save)
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+Shift+S'), self, self.saveAs)
        QtGui.QShortcut(QtGui.QKeySequence('F3'), self, self.findNext)
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+P'), self, 
                        self.nanoToggleSidebar)
        QtGui.QShortcut(QtGui.QKeySequence('Ctrl+Return'), self, 
                        self.toggleTerminal)

        self.readConfig()

        # Nano stuff including empty sidebar
        self.myDay = 0 
        self.nanoMode = False
        self.nanoWidth = 20 
        self.nanowidget = QtGui.QPlainTextEdit(self)
        self.nanowidget.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        self.nanowidget.setReadOnly(True)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        font.setPointSize(10)
        self.nanowidget.setFont(font)
        # size is important
        charWidth = self.nanowidget.fontMetrics().averageCharWidth()
        self.nanowidget.setFixedWidth((self.nanoWidth + 1)*charWidth)
        self.nanowidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nanowidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # layout is layout
        layout.addWidget(self.nanowidget)
        self.nanowidget.setVisible(False)

        # Choose pythonw on windows if possible
        self.command = 'python'
        if system == 'Windows':
            try:
                subprocess.Popen(['pythonw'])
            except WindowsError:
                pass
            else:
                self.command = 'pythonw'
        # ...and python2 on Linux if possible
        elif system == 'Linux':
            # Or actually not, it takes the command from the first line
            # of itself (the file)
            with open(os.path.join(sys.path[0],
                                   os.path.basename(sys.argv[0]))) as f:
                l = f.readline()
            l = l.strip()[2:]
            if os.path.exists(l):
                self.command = l.strip()[2:]
##            try:
##                subprocess.Popen(['python2'])
##            except OSError:
##                pass
##            else:
##                self.command = 'python2'

        if file_:
            if not self.openFile(file_):
                self.close()            
            self.updateWindowTitle()
        else:
            self.setFileName('NEW')

        self.show()


## ==== Overrides ========================================================== ##
        
    def closeEvent(self, event):
        if self.saveIfModified() == 'continue':
            self.writeConfig()
            event.accept()
        else:
            event.ignore()


    def dragEnterEvent(self, event):
##        if event.mimeData().hasFormat('text/plain'):
        event.acceptProposedAction();

        
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        parsedurls = []
        for u in urls:
            u = u.path()
            if not os.path.isfile(u) and u.startswith('/'):
                u = u[1:]
            parsedurls.append(u)
            
        if parsedurls:
            self.open_(filename=parsedurls[0])
        for u in parsedurls[1:]:
            subprocess.Popen([self.command, sys.argv[0], u])
        event.acceptProposedAction();


## ==== Config ============================================================= ##
    """
    The config files' syntax is similar to standard INI's but the sections are
    treated as comments only and are therefore purely cosmetical. The rest is
    (as far as I know) identical.

    Order is not important but it IS saved between read/writes, contrary to
    how configparser does it.

    Also, leading/trailing whitspaces and around
    the = is ignored and removed on read, and added (only one on each side
    of the = ) on write.
    """

    def defaultConfig(self):
        """ Generate the default config file and save it. """
        defaultcfg = [
        '[Window]',
        'x = 20',
        'y = 20',
        'width = 800',
        'height = 480',
        'maximized = False',
        '',
        '[Settings]',
        'fontfamily = Times New Roman',
        'fontsize = 12',
        'lastdirectory = ',
        'vscrollbar = always',
        'linenumbers = False',
        'autoindent = False',
        ';Let Open/New do it in a new window instead of the current one.',
        'open_in_new_window = False',
        '',
        '[NaNo]',
        'endpoint = SLUTPUNKT',
        'goal = 50000',
        'days = 29',
        'idealChLen = 3600']
        
        defaultcfg = [x+'\n' for x in defaultcfg]
        
        with codecs.open(self.cfgpath, 'w', encoding='utf-8') as cfgfile:
            cfgfile.writelines(defaultcfg)


    def readConfig(self):
        """ Read the config and update the appropriate variables. """
        cfg = {}
        with codecs.open(self.cfgpath, encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if not l or l[0] in ('[', ';'):
                    continue
                key, value = l.split('=')
                cfg[key.strip()] = value.strip()

        # Window
        w = int(cfg['width'])
        h = int(cfg['height'])
##        self.resize(w,h)
        x = int(cfg['x'])
        y = int(cfg['y'])
##        self.move(x,y)
##        if cfg['maximized'].lower() == 'true':
##            self.showMaximized()
            
        # Settings
        fontfamily = cfg['fontfamily']
        fontsize = int(cfg['fontsize'])
        self.document.setDefaultFont(QtGui.QFont(fontfamily, fontsize))
        self.lastdir = unicode(cfg['lastdirectory'])
        vscrollbar = cfg['vscrollbar']
        if vscrollbar == 'always':
            self.sbAlwaysShow()
        elif vscrollbar == 'needed':
            self.sbNeededShow()
        elif vscrollbar == 'never':
            self.sbNeverShow()
        if cfg['linenumbers'].lower() == 'true':
            self.textarea.number_bar.showbar = True
        if cfg['autoindent'].lower() == 'true':
            self.autoindent = True
        if cfg['open_in_new_window'].lower() == 'true':
            self.open_in_new_window = True

        # NaNo
        self.endPoint = cfg['endpoint']
        self.goal = int(cfg['goal'])
        self.days = int(cfg['days'])
        self.idealChLen = int(cfg['idealChLen'])

    def writeConfig(self):
        """
        Read the config, update the info with appropriate variables (optional)
        and then overwrite the old file with the updated config.
        """
        vscrollbar = ('needed', 'never', 'always')
        sizepos = self.geometry()
        font = self.document.defaultFont()
        cfg = {'x': sizepos.left(),
               'y': sizepos.top(),
               'width': sizepos.width(),
               'height': sizepos.height(),
               'maximized': self.isMaximized(),
               'fontfamily': font.family(),
               'fontsize': font.pointSize(),
               'lastdirectory': self.lastdir,
               'vscrollbar': vscrollbar[self.textarea.
                                        verticalScrollBarPolicy()],
               'linenumbers': self.textarea.number_bar.showbar,
               'autoindent': self.autoindent,
               'open_in_new_window': self.open_in_new_window,
               'endpoint': self.endPoint,
               'goal': self.goal,
               'days': self.days,
               'idealChLen': self.idealChLen}
        output = []
        with codecs.open(self.cfgpath, encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if not l or l[0] in ('[', ';', '#'):
                    output.append(l+'\n')
                    continue
                key, value = l.split('=')
                key, value = key.strip(), value.strip()
                if key in cfg:
                    value = unicode(cfg[key])
                output.append(u'{0} = {1}\n'.format(key, value))

        with codecs.open(self.cfgpath, 'w', encoding='utf-8') as f:
            f.writelines(output)


## ==== Nano 3============================================================== ##
    # TODO Double-check word-counter's view on whitespace in [ ]
    # TODO Double-check what happens when NaNo mode is toggled several times
    # TODO Fix log files so they overwrite older dates with same wordcount

    def nanoToggleSidebar(self):
        """
        Ctrl Something does this.
        """
        if self.nanoMode:
            self.nanowidget.setPlainText(self.nanoGenerateStats())
            self.nanowidget.setVisible(abs(self.nanowidget.isVisible()-1))

    def nanoCountWordsChapters(self):
        """
        Count words per chapter, create current wordcount as chapter array and
        total wordcount. 
        Split chapter at text 'KAPITEL' or 'CHAPTER'.
        Should override updateWordCount.
        """
        # Join lines and remove comments.
        # Split into chapters at (newlines + chapter start)
        text = re.sub(r'\[.*?\]', '', self.document.toPlainText(), re.DOTALL)
        chapterText = re.split(r'\n{3}(?=KAPITEL|CHAPTER)', text)
        self.wordsPerChapter = []
        self.accWcount = 0
        for n,i in enumerate(chapterText):
            chLength = len(re.findall(r'\S+', i.split(self.endPoint)[0]))
            self.wordsPerChapter.append(chLength)
            self.accWcount += chLength
        # Very much stolen from updateWordCount()
        if not self.accWcount == self.wt_wordcount:
            self.wt_wordcount = self.accWcount
            self.updateWindowTitle()

    def nanoLogStats(self):
        """
        Check if there is a statistics file; if not, create one.
        Look for filename.log 
        This function is run during saving.

        Logfile part 1, written in stat1:
        STATISTICS FILE
        filename
        Date, time, myDay, total wordcount
        
        Logfile part 2, written in stat2:
        CHAPTER = WORDS
        Chapter number = wordcount
        
        BONUS HAMSTER:
        Read yesterday's last wordcount!
        """
        logfilename = self.filename + u'.log'
        thistime = datetime.datetime.today()
        logstring = u'{0}, {1} = {2}\n'
        stat1 = logstring.format(thistime.strftime(u'%Y-%m-%d %H:%M:%S'), 
                                 self.myDay, self.accWcount)
        stat2 = []
        for n,ch in enumerate(self.wordsPerChapter):
            stat2.append(u'{0} = {1}\n'.format(n, ch))
        if not os.path.isfile(logfilename):
            with codecs.open(logfilename, 'w', encoding='utf-8') as f:
                logHeader = u'STATISTICS FILE\n{0}\n\nDAY, MY DAY = WORDS\nCHAPTER = WORDS\n\n'.format(self.filename) 
                f.write(logHeader)
        with codecs.open(logfilename, 'r', encoding='utf-8') as lr:
            logLines = lr.readlines()
            h = logLines.index(u'DAY, MY DAY = WORDS\n')
            i = logLines.index(u'CHAPTER = WORDS\n')
            lines = sorted(logLines[h+1:i])
            for line in lines:
                dayWcount = line.split(u',')[1].strip()
                if int(dayWcount.split(' = ')[0]) < self.myDay:
                    self.myLastWcount = int(dayWcount.split(' = ')[1])
        with codecs.open(logfilename, 'w', encoding='utf-8') as l:
            newLines = logLines[:i] + [stat1] + [logLines[i]] + stat2
            l.writelines(newLines)

    def nanoExtractOldStats(self):
        """
        Read *_stats.txt files from prevStatsDir. Put them in array where row
        number corresponds to day, with year being in first row.
        Should be run at startup or when NaNo modes is turned on.
        """
        prevStatsDir = u'nano_prev_stats'
        self.oldStats = []
        statsFiles = []
        prevStatsDirPath = os.path.join(os.path.dirname(self.filename), 
                                        prevStatsDir) 
        try:
            # List of filenames without paths
            statsFiles = os.listdir(os.path.join(os.path.dirname(self.filename), 
                                    prevStatsDir))
        except OSError:
            pass
        else:
            for stFile in statsFiles:
                with codecs.open(os.path.join(prevStatsDirPath, stFile), 'r', 
                                 encoding='utf-8') as f:
                    statsByYearUnsplit = f.readlines()
                statsByYear = []
                for line in statsByYearUnsplit:
                    if len(line.split('\t'))>1:
                        line = line.split('\t')[1] 
                    statsByYear.append(line)
                self.oldStats.append(statsByYear)
        self.oldStats.sort()

    def nanoGenerateStats(self):
        """
        Pick config data and wordcounts and return the text for the statistics
        window as a string.
        """
        # Total width of stats window is hard-coded :(
        w = self.nanoWidth - 13
        # Building the array
        statsText = ['DAY {0}, {1:.2%}\n\n'.format(self.myDay, 
                     float(self.accWcount)/float(self.goal))]
        formStr = '{0:<{1}}{2:>5}{3:>7} \n'
        self.goalToday = int(ceil(float(self.goal)/float(self.days))*self.myDay)
        self.goalYesterday = int(ceil(float(self.goal)/float(self.days))
                                                        *(self.myDay - 1))
        writtenToday = self.accWcount - self.myLastWcount
        diffToDaygoal = writtenToday - (self.goalToday - self.goalYesterday)
        for n,ch in enumerate(self.wordsPerChapter):
            if not n:
                statsText.append(formStr.format(n, w, ch, ''))
            else:
                statsText.append(formStr.format(n, w, ch, ch - self.idealChLen))
        statsText.append(formStr.format('TOTAL', w, self.accWcount,
                         self.accWcount - self.goal))
        statsText.append(u'\n')
        statsText.append(formStr.format('GOAL', w, 
                         self.goalToday, self.accWcount - self.goalToday))
        statsText.append(formStr.format('TODAY', w, writtenToday, 
                                        diffToDaygoal))
        statsText.append('\nPREVIOUSLY\n')
        prevStr = '{0:<{1}}{2:>5}{3:>7} \n' 
        for year in self.oldStats:
            # year is [20XX, words, words, words]
            diff = self.accWcount - int(year[self.myDay].strip())
            try:
                statsText.append(prevStr.format(year[0].strip(), w, 
                                                year[self.myDay].strip(), diff))
            except IndexError:
                pass
        edStr = ''
        for line in statsText:
            edStr += line
        return edStr


## ==== Misc =============================================================== ##

    def generateMsgbox(self):
        """ Create a certain message box. (Should be obvious which.) """
        self.msgbox = QMessageBox(self)
        self.msgbox.setWindowTitle('Save changes?')
        self.msgbox.setText('The document has been modified.')
        self.msgbox.setInformativeText('Do you want to save your changes?')
        self.msgbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard |
                                  QMessageBox.Cancel)
        self.msgbox.setDefaultButton(QMessageBox.Save)
        self.msgbox.setIcon(QMessageBox.Warning)


    def toggleTerminal(self):
        self.terminal.setVisible(abs(self.terminal.isVisible()-1))
        if self.terminal.isVisible():
            self.switchFocus()


    def switchFocus(self):
        self.terminal.inputTerm.setFocus()


    def newLine(self, blocks):
        """ Generate auto-indentation if the option is enabled. """
        if blocks > self.blocks and self.autoindent:
            cursor = self.textarea.textCursor()
            blocknum = cursor.blockNumber()
            prevblock = self.document.findBlockByNumber(blocknum-1)
            indent = re.match(r'[\t ]*', prevblock.text()).group(0)
            cursor.insertText(indent)


    def newAndEmpty(self):
        """ Return True if the file is empty and unsaved. """
        if not self.document.isModified() and not self.filename:
            return True
        return False

    # ---- Vertical scrollbar -------------------------------------- #
    
    def sbAlwaysShow(self):
        """ Always show the vertical scrollbar. Convenience function. """
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
    def sbNeededShow(self):
        """
        Only show the vertical scrollbar when needed.
        Convenience function.
        """
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
    def sbNeverShow(self):
        """ Never show the vertical scrollbar. Convenience function. """
        self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    # -------------------------------------------------------------- #

    
    def findNext(self):
        tempCursor = self.textarea.textCursor()
        found = self.textarea.find(self.findtext)
        if not found:
            if not self.textarea.textCursor().atStart():
                self.textarea.moveCursor(QtGui.QTextCursor.Start)
                found = self.textarea.find(self.findtext)
                if not found:
                    self.textarea.setTextCursor(tempCursor)
                    self.terminal.error('[find] Text not found')

    
    def replaceNext(self):
        tempCursor = self.textarea.textCursor()
        found = self.textarea.find(self.replace1text)
        if not found:
            if not self.textarea.textCursor().atStart():
                self.textarea.moveCursor(QtGui.QTextCursor.Start)
                found = self.textarea.find(self.replace1text)
                if not found:
                    self.textarea.setTextCursor(tempCursor)
        if found:
            self.textarea.textCursor().insertText(self.replace2text)
            self.terminal.print_('found sumfin! {0}'.format(self.textarea.textCursor().hasSelection()))
        else:
            self.terminal.error('[replace] Text not found')
            
    
    def replaceAll(self):
        tempCursor = self.textarea.textCursor()
        times = 0
        while True:
            found = self.textarea.find(self.replace1text)
            if found:
                self.textarea.textCursor().insertText(self.replace2text)
                times += 1
            else:
                if self.textarea.textCursor().atStart():
                    break
                else:
                    self.textarea.moveCursor(QtGui.QTextCursor.Start)
                    continue
        if times:
            self.terminal.print_('{0} instances replaced'.format(times))
        else:
            self.textarea.setTextCursor(tempCursor)
            self.terminal.error('[replaceall] Text not found')
            

## ==== Window title ===================================== ##

    def updateWindowTitle(self):
        self.setWindowTitle(u'{0}{1} - {2}{0}'.format(u'*'*self.wt_modified,
                                                     self.wt_wordcount,
                                                     self.wt_file))
        

    def toggleModified(self, modified):
        """
        Toggle the asterisks in the title depending on if the file has been
        modified since last save/open or not.
        """
        self.wt_modified = modified
        self.updateWindowTitle()


    def updateWordCount(self):
        if self.nanoMode:
            self.nanoCountWordsChapters()
        else:
            wcount = len(re.findall(r'\S+', self.document.toPlainText()))
            if not wcount == self.wt_wordcount:
                self.wt_wordcount = wcount
                self.updateWindowTitle()


    def setFileName(self, filename):
        """ Set both the output file and the title to filename. """
        if filename == u'NEW':
            self.filename = u''
            self.wt_file = u'New file'
        else:
            self.filename = filename
            self.wt_file = os.path.basename(filename)
        self.updateWindowTitle()    
    


## ==== File operations: new/open/save ===================================== ##

    def saveIfModified(self):
        """
        Save the file if it has been modified.
        
        Return "abort" if it has been modified but has not been saved.
        Otherwise, return "continue" (signaling that the parent script can go on
        with whatever it was doing)
        """
        if self.document.isModified():
            answer = self.msgbox.exec_()
            if answer == QMessageBox.Save:
                if not self.save():
                    return 'abort'
            elif answer == QMessageBox.Cancel:
                return 'abort'
        return 'continue'
    

    def new(self):
        """ Create a new file. Save the old one if needed. """
        if self.open_in_new_window and not self.newAndEmpty():
            subprocess.Popen([self.command, sys.argv[0]])
        elif self.saveIfModified() == 'continue':
            self.document.clear()
            self.document.setModified(False)
            self.toggleModified(False)
            self.setFileName('NEW')
            self.blocks = 1


    def open_(self, filename=''):
        """
        Prompts the user for a filename and then call the openFile function
        to actually open and read the file. Save the old file if needed.
        Open a file. 
        If all encodings fail, the file will not be loaded.

        devnote: Does not use Qt's built-in file loading since it frakked up
        ansi/ascii files. This pure python method should work with utf-8
        and latin1/ansi/ascii/thatcrap files.

        NOTE that regardless of what encoding it used when loading the file, it
        will always be saved in utf-8.
        """
        
        if (self.open_in_new_window and not self.newAndEmpty())\
                        or self.saveIfModified() == 'continue':
            if not filename:
                filename = QtGui.QFileDialog.getOpenFileName(self,
                                                      dir=self.lastdir)[0]
        
        if filename:
            if self.open_in_new_window and not self.newAndEmpty():
                subprocess.Popen([self.command, sys.argv[0],
                                     filename.encode('utf-8')])
            else:
                self.lastdir = os.path.dirname(filename)
                self.openFile(filename)


    def openFile(self, filename):
        encodings = ('utf-8', 'latin1')
        import codecs
        readsuccess = False
        for e in encodings:
            try:
                with codecs.open(filename, encoding=e) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                continue
            else:
                readsuccess = True
                self.document.setPlainText(u''.join(lines))
                self.document.setModified(False)
                self.setFileName(filename)
                self.blocks = self.document.blockCount()
                self.textarea.moveCursor(QtGui.QTextCursor.Start)
                return True
        if not readsuccess:
            QMessageBox.critical(self, 'Kalpana - Encoding Error',
                                 'The file could not be decoded!\n' +
                                 filename, QMessageBox.Ok)
            return False
                

    def save(self):
        """
        Save the file. Prompt the user for a path if it is a new file, otherwise
        use the existing filename.
        Log NaNo statistics if NaNo mode is on.
        """
        if not self.filename:
            fname = QtGui.QFileDialog.getSaveFileName(self,
                                                    dir=self.lastdir)[0]
            if not fname:
                return False
            else:
                self.setFileName(fname)
                self.lastdir = os.path.dirname(fname)
        import codecs
        try:
            with codecs.open(self.filename, 'w', encoding='utf-8') as f:
                f.write(self.document.toPlainText())
        except IOError as e:
            print(e)
            pass
        else:
            if self.nanoMode:
                self.nanowidget.setPlainText(self.nanoGenerateStats())
                self.nanoLogStats()
            self.document.setModified(False)
            return True


    def saveAs(self):
        """
        Prompt the user for a path, regardless if it is a new file or not. Then
        save the file to that location, and continue editing that one (the new).
        """
        prevfile = self.filename
        self.filename = ''
        if not self.save():
            self.filename = prevfile


# =========================================================================== #
# ==== Terminal ============================================================= #

class Terminal(QtGui.QWidget):


    class InputBox(QtGui.QLineEdit):

        def __init__(self, *args):
            QtGui.QLineEdit.__init__(self, *args)

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Space and\
                        event.modifiers() == Qt.ControlModifier:
                self.emit(SIGNAL("ctrlSpacePressed"))
                return True
            return QtGui.QLineEdit.keyPressEvent(self, event)


    def __init__(self, main, *args):
        QtGui.QWidget.__init__(self, *args)
        self.textarea = main.textarea
        self.main = main
        self.sugindex = -1

        layout = QtGui.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        self.inputTerm = self.InputBox(self)
        self.outputTerm = QtGui.QLineEdit(self)
        self.inputTerm.setFont(QtGui.QFont('monospace'))
        self.outputTerm.setFont(QtGui.QFont('monospace'))
        self.outputTerm.setDisabled(True)
        self.outputTerm.setAlignment(Qt.AlignRight)

        # Colors
        p = self.outputTerm.palette()
        p.setColor(QtGui.QPalette.Text, QtGui.QPalette.Dark)
        p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Base, 
                Qt.lightGray)
        self.inputTerm.setPalette(p)
        self.outputTerm.setPalette(p)

        layout.addWidget(self.inputTerm)
        layout.addWidget(self.outputTerm)

#        self.connect(self.inputTerm, SIGNAL('textEdited(const QString&)'), 
#                     self.resetSuggestions)
        self.connect(self.inputTerm, SIGNAL('returnPressed()'), 
                     self.parseCommand)
        self.connect(self.inputTerm, SIGNAL('ctrlSpacePressed'), 
                     self.switchFocus)
#        self.connect(self.inputTerm, SIGNAL('shiftTabPressed'), 
#                     self.prevSuggestion)

    def switchFocus(self):
        self.main.textarea.setFocus()


    def setTextColor(self, color):
        if color == 'gray':
            color = Qt.darkGray
        else:
            color = QtGui.QPalette.Dark
        p = self.inputTerm.palette()
        p.setColor(QtGui.QPalette.Text, color)
        self.inputTerm.setPalette(p)

    ### UNUSED ###
    def autoComplete(self):
        if self.sugindex != -1:
            self.nextSuggestion()
        else:
            text = self.inputTerm.text()
            path, name = os.path.split(text)
            print(path, name)
            if path != os.path.expanduser(path):
                self.inputTerm.setText(os.path.join(os.path.expanduser(path),
                                                    name))
                return
            if text == '~':
                self.inputTerm.setText(os.path.expanduser(text))
                return
            if os.path.isdir(path):
                self.sugs = sorted([x for x in os.listdir(path) 
                            if x.startswith(name) and x != name]) + [name]
                self.sugs = [os.path.join(path,x) for x in self.sugs]
                #self.sugs = [x + os.path.isdir(x) * os.sep for x in self.sugs]
                self.sugindex = 0
                self.setText(self.sugs[self.sugindex], 
                             gray=os.path.isdir(self.sugs[self.sugindex]))

    ### UNUSED ###            
    def prevSuggestion(self):
        if self.sugindex == -1:
            return
        self.sugindex -= 1
        if self.sugindex == -1:
            self.sugindex = len(self.sugs)-1
        self.setText(self.sugs[self.sugindex], 
                     gray=os.path.isdir(self.sugs[self.sugindex]))

    ### UNUSED ###
    def nextSuggestion(self):
        self.sugindex += 1
        if self.sugindex == len(self.sugs):
            self.sugindex = 0
        self.setText(self.sugs[self.sugindex], 
                     gray=os.path.isdir(self.sugs[self.sugindex]))

    ### UNUSED ###
    def resetSuggestions(self):
        self.sugindex = -1


    def parseCommand(self):
        text = self.inputTerm.text()
        if not text.strip():
            return
        self.inputTerm.setText('')
        cmd = text.split(' ', 1)[0]
        # If the command exists, run the callback function (a bit cryptic maybe)
        if cmd in self.cmds:
            self.cmds[cmd][0](self, text[len(cmd)+1:])
        else:
            self.error('No such function')


    def setText(self, text, gray=False):
        self.inputTerm.setText(text)
        if gray:
            self.setTextColor('gray')
        elif self.inputTerm.palette().color(QtGui.QPalette.Text) == Qt.darkGray:
            self.setTextColor('black')


    def print_(self, text):
        self.outputTerm.setText(text)


    def error(self, text):
        self.outputTerm.setText('Error: ' + text)


    # ==== Commands ============================== #
    def cmdOpen(self, arg):
        f = arg.strip()
        if os.path.isfile(f):
            self.main.openFile(f)
        else:
            self.error('Non-existing file')

    def cmdNew(self, arg):
        pass

    def cmdSave(self, arg):
        pass

    def cmdFind(self, arg):
        if arg:
            self.main.findtext = arg
            self.main.findNext()
        else:
            if self.main.findtext:
                self.main.findNext()
            else:
                self.error("No previous searches")

    def cmdReplace(self, arg):
        if arg:
            args = arg.split(' ', 1)
            self.main.replace1text, self.main.replace2text = args
            self.main.replaceNext()
        else:
            if self.main.replace1text:
                self.main.replaceNext()
            else:
                self.error("No previous replaces")

    def cmdReplaceAll(self, arg):
        if arg:
            args = arg.split(' ', 1)
            self.main.replace1text, self.main.replace2text = args
            self.main.replaceAll()
        else:
            if self.main.replace1text:
                self.main.replaceAll()
            else:
                self.error("No previous replaces")

    def cmdListCommands(self, arg):
        self.print_(' '.join(sorted(self.cmds)))

    def cmdChangeFont(self, arg):
        font, ok = QtGui.QFontDialog.getFont(QtGui.QFont(self.main.document.
                                                         defaultFont()))
        if ok:
            self.main.document.setDefaultFont(font)

    def cmdAutoIndent(self, arg):
        self.main.autoindent = not self.main.autoindent

    def cmdLineNumbers(self, arg):
        self.textarea.number_bar.showbar = not self.textarea.number_bar.showbar
        self.textarea.number_bar.update()

    def cmdScrollbar(self, arg):
        arg = arg.strip()
        if arg == '0':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        elif arg == '1':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        elif arg == '2':
            self.textarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        else:
            self.error('Wrong argument')

    def cmdNewWindow(self, arg):
        arg = arg.strip()
        if arg == '0':
            self.main.open_in_new_window = False
        elif arg == '1':
            self.main.open_in_new_window = True
        else:
            self.error('Wrong argument')

    def cmdVersion(self, arg):
        self.print_('Kalpana {0}, made in 2011 by nycz'.format(version))

    def cmdWhereAmI(self, arg):
        self.print_(os.path.abspath(self.main.filename))

    def cmdHelp(self, arg):
        if arg in self.cmds:
            self.print_(self.cmds[arg][1])
        else:
            self.error('No such command')

    def cmdNanoToggle(self, arg):
        if arg.strip().isdigit():
            if int(arg.strip()) == 0:
                self.main.nanoMode = False
                self.print_('NaNo mode disabled')
            elif int(arg.strip()) in range(1,self.main.days + 1):
                self.main.myDay = int(arg.strip())
                self.main.nanoMode = True
                self.main.nanoCountWordsChapters()
                self.main.myLastWcount = self.main.accWcount
                self.main.nanoExtractOldStats()
                self.main.nanowidget.setPlainText(self.main.nanoGenerateStats())
                self.print_('NaNo mode initiated')
            else:
                self.error('Invalid date')
        else:
            self.error('Invalid argument')
       

    cmds = {'o': (cmdOpen, 'Open [file]'),
            'n': (cmdNew, 'Open new file'),
            's': (cmdSave, 'Save (as) [file]'),
            'f': (cmdFind, 'find (next) [string]'),
            'r': (cmdReplace, 'Replace (syntax help needed)'),
            'ra': (cmdReplaceAll, 'Replace all (syntax help needed)'),
            '?': (cmdListCommands, 'List all commands'),
            'cf': (cmdChangeFont, 'Change font'),
            'ai': (cmdAutoIndent, 'Toggle auto indent'),
            'ln': (cmdLineNumbers, 'Toggle line numbers'),
            'vs': (cmdScrollbar, 'Scrollbar [0,1,2] Off, Maybe, On'),
            'nw': (cmdNewWindow, 'Open in new window [0,1] No, Yes'),
            'v': (cmdVersion, 'Version info'),
            'wd': (cmdWhereAmI, 'Working directory'),
            'h': (cmdHelp, 'Help for [command]'),
            'nn': (cmdNanoToggle, 'Start NaNo mode at [day]')}
            


# =========================================================================== #
# ==== Line numbers ========================================================= #

class LineTextWidget(QtGui.QPlainTextEdit):
 
    def append(self,string):
        self.appendPlainText(string)
 
    class NumberBar(QtGui.QWidget): 
 
        def __init__(self, *args):
            QtGui.QWidget.__init__(self, *args)
            self.edit = None
            # This is used to update the width of the control.
            # It is the highest line that is currently visibile.
            self.highest_line = 0
            self.showbar = False
 
        def setTextEdit(self, edit):
            self.edit = edit
 
        def update(self, *args):
            if not self.showbar:
                width = 0
            else:
                width = QtGui.QFontMetrics(self.edit.document().defaultFont()).\
                                            width(str(self.highest_line)) + 10
            if self.width() != width:
                self.setFixedWidth(width)
                self.edit.setViewportMargins(width,0,0,0)
            QtGui.QWidget.update(self, *args)
 
        def paintEvent(self, event):
            contents_y = 0
            page_bottom = self.edit.viewport().height()
            font_metrics = QtGui.QFontMetrics(self.edit.document().
                                              defaultFont())
            current_block = self.edit.document().findBlock(self.edit.
                                                           textCursor().
                                                           position())
 
            painter = QtGui.QPainter(self)
 
            # Iterate over all text blocks in the document.
            block = self.edit.firstVisibleBlock()
            viewport_offset = self.edit.contentOffset()
            line_count = block.blockNumber()
            painter.setFont(self.edit.document().defaultFont())
            painter.setPen(QtGui.QColor('darkGray'))
            while block.isValid():
                line_count += 1
 
                # The top left position of the block in the document
                position = self.edit.blockBoundingGeometry(block).topLeft()\
                            + viewport_offset
                # Check if the position of the block is out side of the visible
                # area.
                if position.y() > page_bottom:
                    break
 
                # We want the line number for the selected line to be bold.
                bold = False
                if block == current_block:
                    bold = True
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
 
                # Draw the line number right justified at the y position of the
                # line. 3 is a magic padding number. drawText(x, y, text).
                painter.drawText(self.width() - font_metrics.
                                 width(str(line_count)) - 3,
                                 round(position.y() + font_metrics.
                                       ascent()*1.05), str(line_count))
 
                # Remove the bold style if it was set previously.
                if bold:
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)
 
                block = block.next()
 
            self.highest_line = line_count
            painter.end()
 
            QtGui.QWidget.paintEvent(self, event)
 
 
    def __init__(self, *args):
        QtGui.QPlainTextEdit.__init__(self, *args)
 
        self.number_bar = self.NumberBar(self)
        self.number_bar.setTextEdit(self)
 
        self.viewport().installEventFilter(self)
 
    def resizeEvent(self,e):
        self.number_bar.setFixedHeight(self.height())
        QtGui.QPlainTextEdit.resizeEvent(self,e)
 
    def setDefaultFont(self,font):
      self.document().setDefaultFont(font)
 
    def eventFilter(self, object, event):
        # Update the line numbers for all events on the text edit
        # and the viewport.
        # This is easier than connecting all necessary singals.
        if object is self.viewport():
            self.number_bar.update()
            return False
        return QtGui.QPlainTextEdit.eventFilter(object, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and\
                            event.modifiers() == Qt.ControlModifier:

            self.emit(SIGNAL("ctrlSpacePressed"))
            return True
        return QtGui.QPlainTextEdit.keyPressEvent(self, event)


def getValidFiles(): 
    output = []
    for f in sys.argv[1:]:
        try:
            f = unicode(f, 'utf-8')
        except UnicodeDecodeError:
            f = unicode(f, 'latin1')
        if os.path.isfile(os.path.abspath(f)):
            output.append(f)
        else:
            print('File not found:')
            print(f)
    return output
        
if __name__ == '__main__':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    files = getValidFiles()
    app = QtGui.QApplication(sys.argv)
##    app.setOverrideCursor(Qt.BlankCursor)
    if gtkpresent:
        app.setStyle(QGtkStyle())
    if not files:
        a = App()
    else:
        a = App(file_=files[0])
        for f in files[1:]:
            subprocess.Popen(['python', sys.argv[0], f.encode('utf-8')])
    sys.exit(app.exec_())
