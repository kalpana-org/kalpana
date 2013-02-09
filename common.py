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


import json
import os.path
import re
import sys


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.loads(f.read())

def write_json(path, data, sort_keys=True):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=sort_keys))


def local_path(path):
    return os.path.join(sys.path[0], path)


def read_stylesheet(path):
    if not os.path.isfile(path):
        print('No theme found at {}. You should fix this.'.format(path))
        return ''
    with open(path, encoding='utf-8') as f:
        data = f.read()

    re_values = re.compile(r'^(?P<key>\$\S+?)\s*:\s*(?P<value>\S+?);?$',
                           re.MULTILINE)

    stylesheet = '\n'.join([l for l in data.splitlines()
                            if not l.startswith('$')])

    for key, value in re_values.findall(data):
        stylesheet = stylesheet.replace(key, value)

    return stylesheet
