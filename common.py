# Copyright nycz 2011-2016

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

class Configable():
    def init_settings_functions(self, settingsmanager):
        self.get_setting = settingsmanager.get_setting
        self.get_path = settingsmanager.get_path
        self.get_style_setting = settingsmanager.get_style_setting
        self.register_setting = lambda settingname, callback: \
                        settingsmanager.register_setting(settingname, callback)

class SettingsError(Exception):
    pass



keywordpatterns = {
    'chapter': r'(?:>> )?CHAPTER\s+(?P<num>\d+)(\s+-\s+(?P<name>.+?))?',
    'section': r'<<\s*(?P<payload>.+?)\s*>>',
    'description': r'\[\[\s*(?P<desc>.+?)\s*(\]\])?',
    'tags': r'#[^,]+(,\s*#[^,]+)*,?\s*',
    'time': r'🕑\s+(?P<time>.+)',
    'meta': r'%%.+',
}


def strip_metadata(lines, impliedchapter=False):
    """
    Take a list of strings and return a list with only the strings that
    aren't metadata (chapter, section, tags, etc)

    impliedchapter is whether to assume the lines was prepended
    by a chapter line.
    """
    import re
    def match(name, line):
        return re.fullmatch(keywordpatterns[name], line)
    out = []
    if impliedchapter:
        itemsleft = ['description', 'tags', 'time']
        eatlines = True
    else:
        itemsleft = []
        eatlines = False
    for line in lines:
        if eatlines:
            for name in itemsleft:
                if match(name, line):
                    itemsleft.remove(name)
                    break
            else:
                # No match was found
                eatlines = False
        if not eatlines:
            if match('chapter', line):
                itemsleft = ['description', 'tags', 'time']
                eatlines = True
            elif match('section', line) or match('meta', line):
                continue
            else:
                out.append(line)
    return out
