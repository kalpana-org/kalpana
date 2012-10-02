import os.path

from PySide import QtGui
from PySide.QtCore import Qt, SIGNAL

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

    class OutputBox(QtGui.QLineEdit):
        pass


    def __init__(self, main, *args):
        QtGui.QWidget.__init__(self, *args)
        self.textarea = main.textarea
        self.main = main
        self.sugindex = -1

        layout = QtGui.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        self.inputTerm = self.InputBox(self)
        self.outputTerm = self.OutputBox(self)
        self.inputTerm.setFont(QtGui.QFont('monospace'))
        self.outputTerm.setFont(QtGui.QFont('monospace'))
        self.outputTerm.setDisabled(True)
        self.outputTerm.setAlignment(Qt.AlignRight)

        # Colors
        p = self.outputTerm.palette()
        p.setColor(QtGui.QPalette.Text, Qt.black)
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