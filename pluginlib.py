NORTH, SOUTH, EAST, WEST, = list(range(4))

hotkeys = {}
commands = {}

class GUIPlugin:

    def __init__(self, get_text, add_widget):
        self.get_text = get_text

    def read_config(self):
        pass

    def write_config(self):
        pass

    def contents_changed(self):
        pass
