from PySide import QtGui
from PySide.QtCore import SIGNAL, Qt

class FontDialog(QtGui.QDialog):
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)

        self.setWindowTitle('Choose font')

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        fontdb = QtGui.QFontDatabase()

        fontlistwidget = QtGui.QListWidget(self)
        fontlistwidget.addItems(fontdb.families())
        fontlistwidget.setCurrentRow(0)

        sizelistwidget = QtGui.QListWidget(self)
        sizelistwidget.addItems([str(s) for s in fontdb.standardSizes()])
        sizelistwidget.setCurrentRow(0)

        listslayout = QtGui.QGridLayout()
        listslayout.addWidget(fontlistwidget, 0, 0)
        listslayout.addWidget(sizelistwidget, 0, 1)
        listslayout.setColumnStretch(0, 5)
        listslayout.setColumnStretch(1, 1)

        self.connect(fontlistwidget, SIGNAL('currentItemChanged(QListWidgetItem *, QListWidgetItem *)'),
                     self.setFont)
        self.connect(sizelistwidget, SIGNAL('currentItemChanged(QListWidgetItem *, QListWidgetItem *)'),
                     self.setSize)
        self.connect(fontlistwidget, SIGNAL('itemActivated (QListWidgetItem *)'),
                     self.accept)
        self.connect(sizelistwidget, SIGNAL('itemActivated (QListWidgetItem *)'),
                     self.accept)

        def selectLeftList():
            fontlistwidget.setFocus()
        def selectRightList():
            sizelistwidget.setFocus()

        QtGui.QShortcut(QtGui.QKeySequence('Left'), self, selectLeftList)
        QtGui.QShortcut(QtGui.QKeySequence('Right'), self, selectRightList)

        class FontExampleLabel(QtGui.QLabel):
            pass
        self.fontlabel = FontExampleLabel('Räksmörgås?!', self)
        self.fontlabel.setAlignment(Qt.AlignCenter)

        listslayout.addWidget(self.fontlabel, 1, 0, 1, 2)
        listslayout.setRowStretch(0, 5)
        listslayout.setRowStretch(1, 1)

        self.setLayout(listslayout)

        self.chosenfont = fontdb.families()[0]
        self.chosensize = fontdb.standardSizes()[0]

    def setFont(self, new, old):
        self.chosenfont = new.text()
        self.updateFont()

    def setSize(self, new, old):
        self.chosensize = int(new.text())
        self.updateFont()

    def updateFont(self):
        self.fontlabel.setFont(QtGui.QFont(self.chosenfont, self.chosensize))

    def fontInfo(self):
        return {'name': self.chosenfont, 'size': self.chosensize}



def getFontInfo(parent):
    window = FontDialog(parent)
    if window.exec_():
        return window.fontInfo()
    else:
        return None



if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)

    with open('fontdialog.css', encoding='utf8') as f:
        stylesheet = f.read()

    app.setStyleSheet(stylesheet)

    # getFontInfo(None)

    a = FontDialog()
    x = a.exec_()
    print(x)
    print(a.fontInfo())
    # fontdb = QtGui.QFontDatabase()
    # print(fontdb.families())
