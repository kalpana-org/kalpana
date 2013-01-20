NORTH, SOUTH, EAST, WEST, = list(range(4))

class GUIPlugin:
    hotkeys = {}
    commands = {}

    def __init__(self, get_text, get_filename, add_widget, path):
        self.get_text = get_text
        self.get_filename = get_filename
        self.add_widget = add_widget
        self.path = path
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
