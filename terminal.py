# Copyright nycz 2011-2012

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
import fontdialog

from PySide import QtGui
from PySide.QtCore import Qt, SIGNAL, QDir, QEvent


class Terminal(QtGui.QSplitter):

    class InputBox(QtGui.QLineEdit):
        def __init__(self, *args):
            QtGui.QLineEdit.__init__(self, *args)

        def event(self, event):
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab and\
                        event.modifiers() == Qt.NoModifier:
                self.emit(SIGNAL('tabPressed()'))
                return True
            return QtGui.QLineEdit.event(self, event)

        def keyPressEvent(self, event):
            if event.text() or event.key() in (Qt.Key_Left, Qt.Key_Right):
                QtGui.QLineEdit.keyPressEvent(self, event)
                self.emit(SIGNAL('updateCompletionPrefix()'))
                return True
            return QtGui.QLineEdit.keyPressEvent(self, event)
  
    # This needs to be here for the stylesheet 
    class OutputBox(QtGui.QLineEdit):
        pass


    def __init__(self, main, version, *args):
        QtGui.QSplitter.__init__(self, *args)
        self.textarea = main.textarea
        self.main = main
        self.sugindex = -1
        self.version = version

        # Splitter settings
        self.setHandleWidth(2)

        # I/O fields creation
        self.inputTerm = self.InputBox(self)
        self.outputTerm = self.OutputBox(self)
        self.outputTerm.setDisabled(True)
        self.outputTerm.setAlignment(Qt.AlignRight)

        self.addWidget(self.inputTerm)
        self.addWidget(self.outputTerm)

        # Autocomplete
        self.completer = QtGui.QCompleter(self)
        fsmodel = QtGui.QFileSystemModel(self.completer)
        fsmodel.setRootPath(QDir.homePath())
        self.completer.setModel(fsmodel)
        self.completer.setCompletionMode(QtGui.QCompleter.InlineCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitive)
        
        self.connect(self.inputTerm, SIGNAL('tabPressed()'),
                     self.autocomplete)
        self.connect(self.inputTerm, SIGNAL('updateCompletionPrefix()'),
                     self.updateCompletionPrefix)

        self.connect(self.inputTerm, SIGNAL('returnPressed()'), 
                     self.parseCommand)
        QtGui.QShortcut(QtGui.QKeySequence('Alt+Left'), self,
                        self.moveSplitterLeft)
        QtGui.QShortcut(QtGui.QKeySequence('Alt+Right'), self,
                        self.moveSplitterRight)
    

    # ==== Autocomplete ========================== #

    def getAutocompletableText(self):
        cmds = ('o', 's')
        text = self.inputTerm.text()
        for c in cmds:
            if text.startswith(c + ' '):
                return text[:2], text[2:]
        return None, None


    def autocomplete(self):
        cmdprefix, ac_text = self.getAutocompletableText()
        if ac_text is None:
            return
    
        separator = QDir.separator()

        # Autocomplete with the working directory if the line is empty
        if ac_text.strip() == '':
            wd = os.path.abspath(self.main.filename)
            self.completer.setCompletionPrefix(wd + separator)
            self.inputTerm.setText(cmdprefix + wd + separator)
            return

        isdir = os.path.isdir(self.completer.currentCompletion())
        if ac_text == self.completer.currentCompletion() + separator*isdir:
            if not self.completer.setCurrentRow(self.completer.currentRow() + 1):
                self.completer.setCurrentRow(0)

        prefix = self.completer.completionPrefix()
        suggestion = self.completer.currentCompletion()
        newisdir = os.path.isdir(self.completer.currentCompletion())
        self.inputTerm.setText(cmdprefix + prefix + suggestion[len(prefix):] + separator*newisdir)


    def updateCompletionPrefix(self):
        cmdprefix, ac_text = self.getAutocompletableText()
        if not ac_text:
            return
        self.completer.setCompletionPrefix(ac_text)


    # ==== Splitter ============================== #

    def moveSplitter(self, dir):
        s1, s2 = self.sizes()
        jump = int((s1 + s2) * 0.1)
        if dir == 'left':
            new_s1 = max(0, s1 - jump)
        else:
            new_s1 = min(s1 + s2, s1 + jump)
        new_s2 = s1 + s2 - new_s1
        self.setSizes((new_s1, new_s2))

    def moveSplitterLeft(self):
        self.moveSplitter('left')

    def moveSplitterRight(self):
        self.moveSplitter('right')


    # ==== Misc ================================= #

    def switchFocus(self):
        self.main.textarea.setFocus()


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
            self.error('No such function (? for help)')


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

    def setReplaceTexts(self, arg):
        """ Try to set the find/replace texts to the args, return False if it fails """
        try:
            self.main.replace1text, self.main.replace2text = arg.split(' ', 1)
        except ValueError:
            self.error('Not enough arguments')
            return False
        return True

    def cmdReplace(self, arg):
        if arg and not self.setReplaceTexts(arg):
            return
        self.main.replaceNext()

    def cmdReplaceAll(self, arg):
        if arg and not self.setReplaceTexts(arg):
            return
        self.main.replaceAll()

    def cmdListCommands(self, arg):
        self.print_(' '.join(sorted(self.cmds)))

    def cmdChangeFont(self, arg):
        if arg not in ('main', 'term', 'nano'):
            self.error('Argument should be main, term or nano')
            return
        font = fontdialog.getFontInfo(self.main)
        if font:
            self.main.themedict[arg + '_fontfamily'] = font['name']
            self.main.themedict[arg + '_fontsize'] = '{}pt'.format(font['size'])
            self.main.updateTheme(self.main.themedict)

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
        self.print_('Kalpana {0}'.format(self.version))

    def cmdWhereAmI(self, arg):
        self.print_(os.path.abspath(self.main.filename))

    def cmdHelp(self, arg):
        if not arg:
            self.print_(' '.join(sorted(self.cmds)))
        elif arg in self.cmds:
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

    def cmdReloadTheme(self, arg):
        self.main.reloadTheme()

    def cmdQuit(self, arg):
        self.main.close()
       
    def cmdForceQuit(self, arg):
        self.main.forcequit = True
        self.main.close()

    cmds = {'o': (cmdOpen, 'Open [file]'),
            'n': (cmdNew, 'Open new file'),
            's': (cmdSave, 'Save (as) [file]'),
            '/': (cmdFind, 'find (next) [string]'),
            'r': (cmdReplace, 'Replace (syntax help needed)'),
            'ra': (cmdReplaceAll, 'Replace all (syntax help needed)'),
            '?': (cmdHelp, 'List commands or help for [command]'),
            'cf': (cmdChangeFont, 'Change font'),
            'ai': (cmdAutoIndent, 'Toggle auto indent'),
            'ln': (cmdLineNumbers, 'Toggle line numbers'),
            'vs': (cmdScrollbar, 'Scrollbar [0,1,2] Off, Maybe, On'),
            'nw': (cmdNewWindow, 'Open in new window [0,1] No, Yes'),
            'v': (cmdVersion, 'Version info'),
            'wd': (cmdWhereAmI, 'Working directory'),
            'nn': (cmdNanoToggle, 'Start NaNo mode at [day]'),
            'rt': (cmdReloadTheme, 'Reload theme from config'),
            'q': (cmdQuit, 'Quit Kalpana'),
            'q!': (cmdForceQuit, 'Quit Kalpana without saving')}