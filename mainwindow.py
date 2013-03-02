


class MainWindow(QtGui.QFrame):

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        self.force_quit_flag = False


    def create_ui(self, textarea, terminal):
        # Layout
        vert_layout = QtGui.QVBoxLayout(self)
        common.kill_theming(vert_layout)

        horz_layout = QtGui.QHBoxLayout()
        common.kill_theming(horz_layout)
        vert_layout.addLayout(horz_layout)

        horz_layout.addWidget(textarea)
        vert_layout.addWidget(terminal)

        return vert_layout, horz_layout

    # Override
    def closeEvent(self, event):
        if not self.document.isModified() or self.force_quit_flag:
            event.accept()
        else:
            self.error('Unsaved changes! Force quit with q! or save first.')
            event.ignore()

    def quit(self, force):
        if force:
            self.force_quit_flag = True
            self.close()
        else:
            self.force_quit_flag = False
            self.close()

    # Override
    def dragEnterEvent(self, event):
        # if event.mimeData().hasFormat('text/plain'):
        event.acceptProposedAction()

    # Override
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        parsedurls = []
        for u in urls:
            u = u.path()
            if not os.path.isfile(u) and u.startswith('/'):
                u = u[1:]
            parsedurls.append(u)

        for u in parsedurls:
            subprocess.Popen([sys.executable, sys.argv[0], u])
        event.acceptProposedAction()

    def update_wordcount(self, wordcount):
        


    def update_title(self, wordcount, filename, is_modified):
        title = '{0}{1} - {2}{0}'.format('*' * is_modified,
                                         self.wt_wordcount,
                                         self.wt_file)
        self.setWindowTitle(title)