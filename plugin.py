NORTH = 0
SOUTH = 1
EAST = 2
WEST = 3

hotkeys = {}
commands = {}

class GUIPlugin:

    def __init__(self, layout, get_text, add_widget):
        self.get_text = get_text

    def read_config(self):
        pass

    def write_config(self):
        pass

    def contents_changed(self):
        pass
