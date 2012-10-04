from PySide import QtGui
from PySide.QtCore import SIGNAL, Qt

class FontDialog(QtGui.QDialog):
    def __init__(self, parent, show_fonts_in_dialoglist, fontfamily, fontsize):
        QtGui.QDialog.__init__(self, parent)

        self.main = parent
        self.fontfamily = fontfamily
        self.fontsize = fontsize

        self.setWindowTitle('Choose font')
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        fontdb = QtGui.QFontDatabase()            

        # FONT FAMILY LIST
        fontlistwidget = QtGui.QListWidget(self)
        if show_fonts_in_dialoglist:
            for f in fontdb.families():
                w = QtGui.QListWidgetItem(f, fontlistwidget)
                font = w.font()
                font.setFamily(f)
                w.setFont(font)
        else:
            fontlistwidget.addItems(fontdb.families())
        # Start with the current fontfamily
        if self.main.themedict[self.fontfamily] in fontdb.families():
            fontlistwidget.setCurrentRow(fontdb.families().index(self.main.themedict[self.fontfamily]))
        else:
            fontlistwidget.setCurrentRow(0)

        # FONT SIZE LIST
        sizelistwidget = QtGui.QListWidget(self)
        fontsizes = [str(s) for s in fontdb.standardSizes()]
        sizelistwidget.addItems(fontsizes)
        fsize = self.main.themedict[self.fontsize].rstrip('pt')

        # Start with the current fontsize
        if fsize in fontsizes:
            sizelistwidget.setCurrentRow(fontsizes.index(fsize))
        else:
            sizelistwidget.setCurrentRow(0)

        # Layout
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
                     self.close)
        self.connect(sizelistwidget, SIGNAL('itemActivated (QListWidgetItem *)'),
                     self.close)

        def selectLeftList():
            fontlistwidget.setFocus()
        def selectRightList():
            sizelistwidget.setFocus()

        QtGui.QShortcut(QtGui.QKeySequence('Left'), self, selectLeftList)
        QtGui.QShortcut(QtGui.QKeySequence('Right'), self, selectRightList)
        QtGui.QShortcut(QtGui.QKeySequence('Escape'), self, self.close)

        self.setLayout(listslayout)

        self.show()

    def closeEvent(self, event):
        self.main.fontdialogopen = False
        event.accept()

    def setFont(self, new, old):
        self.main.themedict[self.fontfamily] = new.text()
        self.main.updateTheme(self.main.themedict)

    def setSize(self, new, old):
        self.main.themedict[self.fontsize] = new.text() + 'pt'
        self.main.updateTheme(self.main.themedict)


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
