# Copyright nycz, cefyr 2011-2012

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


# [Kalpana]
# Gender: Feminine
# Usage: Indian
# Other Scripts: कल्पना (Hindi)
# Means "imagining, fantasy" in Sanskrit.

# v0.2 - added line numbers, taken from
# v0.3 - did sum shit, added dragndrop, made stuff better
# v0.4 - find(/replace)
# v0.5 - moved to git, converted to py3k, refactored, GPL'd


version = 0.5

import datetime, json, os, os.path, platform, re, sys, subprocess

from math import ceil

from terminal import Terminal
from linewidget import LineTextWidget

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
            self.cfgpath = os.path.join(sys.path[0], 'kalpana.json')

        # Generate confige if none exists
        if not os.path.exists(self.cfgpath):
            self.defaultConfig()

        # Window title stuff
        self.wt_wordcount = 0
        self.wt_modified = False
        self.wt_file = ''

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
        self.terminal = Terminal(self, version, layoutwidget)
        layout0.addWidget(self.terminal)
        self.terminal.setVisible(False)

        # Misc settings etc
        self.filename = ''
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
        class NaNoSidebar(QtGui.QPlainTextEdit):
            # For the stylesheet
            pass 
        self.myDay = 0 
        self.nanoMode = False
        self.nanoWidth = 20 
        self.nanowidget = NaNoSidebar(self)
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
        defaultcfg = {
            'window': {
                'x': 20,
                'y': 20,
                'width': 800,
                'height': 480,
                'maximized': False,
            },
            'settings': {
                'fontfamily': 'Times New Roman',
                'fontsize': 12,
                'lastdirectory': 'self.lastdir',
                'vscrollbar': 'always',
                'linenumbers': False,
                'autoindent': False,
                'open_in_new_window': False,
            },   
            'nano': {
                'endpoint': 'SLUTPUNKT',
                'goal': 50000,
                'days': 29,
                'idealChLen': 3600,
            },
        }
        
        jsondump = json.dumps(defaultcfg, ensure_ascii=False, indent=4, sort_keys=True)
        with open(self.cfgpath, 'w', encoding='utf-8') as cfgfile:
            cfgfile.write(jsondump)


    def readConfig(self):
        """ Read the config and update the appropriate variables. """
        with open(self.cfgpath, encoding='utf-8') as f:
            cfg = json.loads(f.read())

        # Settings
        fontfamily = cfg['settings']['fontfamily']
        fontsize = cfg['settings']['fontsize']
        self.document.setDefaultFont(QtGui.QFont(fontfamily, fontsize))
        self.lastdir = cfg['settings']['lastdirectory']
        vscrollbar = cfg['settings']['vscrollbar']
        if vscrollbar == 'always':
            self.sbAlwaysShow()
        elif vscrollbar == 'needed':
            self.sbNeededShow()
        elif vscrollbar == 'never':
            self.sbNeverShow()
        self.textarea.number_bar.showbar = cfg['settings']['linenumbers']
        self.autoindent = cfg['settings']['autoindent']
        self.open_in_new_window = cfg['settings']['open_in_new_window']

        # NaNo
        self.endPoint = cfg['nano']['endpoint']
        self.goal = cfg['nano']['goal']
        self.days = cfg['nano']['days']
        self.idealChLen = cfg['nano']['idealChLen']

    def writeConfig(self):
        """
        Read the config, update the info with appropriate variables (optional)
        and then overwrite the old file with the updated config.
        """
        vscrollbar = ('needed', 'never', 'always')
        sizepos = self.geometry()
        font = self.document.defaultFont()
        cfg = {
            'window': {
                'x': sizepos.left(),
                'y': sizepos.top(),
                'width': sizepos.width(),
                'height': sizepos.height(),
                'maximized': self.isMaximized(),
            },
            'settings': {
                'fontfamily': font.family(),
                'fontsize': font.pointSize(),
                'lastdirectory': self.lastdir,
                'vscrollbar': vscrollbar[self.textarea.
                                    verticalScrollBarPolicy()],
                'linenumbers': self.textarea.number_bar.showbar,
                'autoindent': self.autoindent,
                'open_in_new_window': self.open_in_new_window,
            },   
            'nano': {
                'endpoint': self.endPoint,
                'goal': self.goal,
                'days': self.days,
                'idealChLen': self.idealChLen
            }
        }

        outjson = json.dumps(cfg, ensure_ascii=False, indent=4, sort_keys=True)
        with open(self.cfgpath, 'w', encoding='utf-8') as f:
            f.write(outjson)



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
        logfilename = self.filename + '.log'
        thistime = datetime.datetime.today()
        logstring = '{0}, {1} = {2}\n'
        stat1 = logstring.format(thistime.strftime('%Y-%m-%d %H:%M:%S'), 
                                 self.myDay, self.accWcount)
        stat2 = []
        for n,ch in enumerate(self.wordsPerChapter):
            stat2.append('{0} = {1}\n'.format(n, ch))
        if not os.path.isfile(logfilename):
            with open(logfilename, 'w', encoding='utf-8') as f:
                logHeader = 'STATISTICS FILE\n{0}\n\nDAY, MY DAY = WORDS\nCHAPTER = WORDS\n\n'.format(self.filename) 
                f.write(logHeader)
        with open(logfilename, 'r', encoding='utf-8') as lr:
            logLines = lr.readlines()
            h = logLines.index('DAY, MY DAY = WORDS\n')
            i = logLines.index('CHAPTER = WORDS\n')
            lines = sorted(logLines[h+1:i])
            for line in lines:
                dayWcount = line.split(',')[1].strip()
                if int(dayWcount.split(' = ')[0]) < self.myDay:
                    self.myLastWcount = int(dayWcount.split(' = ')[1])
        with open(logfilename, 'w', encoding='utf-8') as l:
            newLines = logLines[:i] + [stat1] + [logLines[i]] + stat2
            l.writelines(newLines)

    def nanoExtractOldStats(self):
        """
        Read *_stats.txt files from prevStatsDir. Put them in array where row
        number corresponds to day, with year being in first row.
        Should be run at startup or when NaNo modes is turned on.
        """
        prevStatsDir = 'nano_prev_stats'
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
                with open(os.path.join(prevStatsDirPath, stFile), 'r', 
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
        statsText.append('\n')
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

        return ''.join(statsText)


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
        return not self.document.isModified() and not self.filename

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
        self.setWindowTitle('{0}{1} - {2}{0}'.format('*'*self.wt_modified,
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
        if filename == 'NEW':
            self.filename = ''
            self.wt_file = 'New file'
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
                subprocess.Popen([self.command, sys.argv[0], filename])
            else:
                self.lastdir = os.path.dirname(filename)
                self.openFile(filename)


    def openFile(self, filename):
        encodings = ('utf-8', 'latin1')
        readsuccess = False
        for e in encodings:
            try:
                with open(filename, encoding=e) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                continue
            else:
                readsuccess = True
                self.document.setPlainText(''.join(lines))
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
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
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


def getValidFiles(): 
    output = []
    for f in sys.argv[1:]:
        # try:
        #     f = unicode(f, 'utf-8')
        # except UnicodeDecodeError:
        #     f = unicode(f, 'latin1')
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
    # if gtkpresent:
    #     app.setStyle(QGtkStyle())

    with open('qtstylesheet.css', encoding='utf8') as f:
        stylesheet = f.read()
    app.setStyleSheet(stylesheet)

    if not files:
        a = App()
    else:
        a = App(file_=files[0])
        for f in files[1:]:
            subprocess.Popen(['python', sys.argv[0], f.encode('utf-8')])
    sys.exit(app.exec_())
