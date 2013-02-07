NORTH, SOUTH, EAST, WEST, = list(range(4))

class GUIPlugin:
    hotkeys = {}
    commands = {}

    def __init__(self, callbacks, path):
        from os.path import isfile, join

        self.get_text, self.get_filename, self.add_widget,\
            self.new_file, self.open_file, self.save_file,\
            self.quit = callbacks

        self.path = path

        self.has_stylesheet = isfile(join(path, 'qtstylesheet.css'))
        if self.has_stylesheet:
            with open(join(path, 'qtstylesheet.css'), encoding='utf8') as f:
                self.stylesheet = f.read()
        self.start()

    def start(self):
        pass

    def read_config(self):
        pass

    def write_config(self):
        pass

    def contents_changed(self):
        pass

    def file_saved(self):
        pass

    def theme_config(self):
        pass
