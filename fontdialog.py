try:
    from PySide import QtGui
    from PySide.QtCore import SIGNAL, Qt
except ImportError:
    from PyQt4 import QtGui
    from PyQt4.QtCore import SIGNAL, Qt

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
        fontlist_widget = QtGui.QListWidget(self)
        if show_fonts_in_dialoglist:
            for f in fontdb.families():
                w = QtGui.QListWidgetItem(f, fontlist_widget)
                font = w.font()
                font.setFamily(f)
                w.setFont(font)
        else:
            fontlist_widget.addItems(fontdb.families())
        # Start with the current fontfamily
        if self.main.themedict[self.fontfamily] in fontdb.families():
            fontlist_widget.setCurrentRow(fontdb.families().index(self.main.themedict[self.fontfamily]))
        else:
            fontlist_widget.setCurrentRow(0)

        # FONT SIZE LIST
        sizelist_widget = QtGui.QListWidget(self)
        fontsizes = [str(s) for s in fontdb.standardSizes()]
        sizelist_widget.addItems(fontsizes)
        fsize = self.main.themedict[self.fontsize].rstrip('pt')

        # Start with the current fontsize
        if fsize in fontsizes:
            sizelist_widget.setCurrentRow(fontsizes.index(fsize))
        else:
            sizelist_widget.setCurrentRow(0)

        # Layout
        lists_layout = QtGui.QGridLayout()
        lists_layout.addWidget(fontlist_widget, 0, 0)
        lists_layout.addWidget(sizelist_widget, 0, 1)
        lists_layout.setColumnStretch(0, 5)
        lists_layout.setColumnStretch(1, 1)

        self.connect(fontlist_widget, SIGNAL('currentItemChanged(QListWidgetItem *, QListWidgetItem *)'),
                     self.set_font)
        self.connect(sizelist_widget, SIGNAL('currentItemChanged(QListWidgetItem *, QListWidgetItem *)'),
                     self.set_size)
        self.connect(fontlist_widget, SIGNAL('itemActivated (QListWidgetItem *)'),
                     self.close)
        self.connect(sizelist_widget, SIGNAL('itemActivated (QListWidgetItem *)'),
                     self.close)

        def select_left_list():
            fontlist_widget.setFocus()
        def select_right_list():
            sizelist_widget.setFocus()

        QtGui.QShortcut(QtGui.QKeySequence('Left'), self, select_left_list)
        QtGui.QShortcut(QtGui.QKeySequence('Right'), self, select_right_list)
        QtGui.QShortcut(QtGui.QKeySequence('Escape'), self, self.close)

        self.setLayout(lists_layout)

        self.show()

    def closeEvent(self, event):
        self.main.font_dialog_open = False
        event.accept()

    def set_font(self, new, old):
        self.main.themedict[self.fontfamily] = new.text()
        self.main.updateTheme(self.main.themedict)

    def set_size(self, new, old):
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
