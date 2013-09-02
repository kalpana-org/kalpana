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


class GUIPlugin:
    hotkeys = {}
    commands = {}

    def __init__(self, objects, get_path):
        self.objects = objects
        self.get_path = get_path

    def read_config(self):
        pass

    def write_config(self):
        pass

    # def get_theme(self):
    #     from os.path import isfile, join
    #     from libsyntyche.common import read_stylesheet
    #     if not isfile(join(self.path, 'stylesheet.css')):
    #         return ''
    #     return read_stylesheet(join(self.path, 'stylesheet.css'))
