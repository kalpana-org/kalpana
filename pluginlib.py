# Copyright nycz 2011-2013

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


NORTH, SOUTH, EAST, WEST, = list(range(4))

class GUIPlugin:
    hotkeys = {}
    commands = {}

    def __init__(self, callbacks, path):
        self.get_text, self.get_filepath, self.add_widget,\
            self.new_file, self.open_file, self.save_file,\
            self.quit = callbacks

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

    def get_theme(self):
        from os.path import isfile, join
        from common import read_stylesheet
        if not isfile(join(self.path, 'stylesheet.css')):
            return ''
        return read_stylesheet(join(self.path, 'stylesheet.css'))
