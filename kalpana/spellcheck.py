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

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import enchant
from PyQt5 import QtCore
from libsyntyche.cli import AutocompletionPattern, Command, ArgumentRules

from kalpana.common import command_callback, KalpanaObject


def get_spellcheck_languages(name: str, text: str) -> List[str]:
    """Return a list with the tags of all available spellcheck languages."""
    return [lang for lang in sorted(enchant.list_languages())
            if lang.startswith(text)]


def _get_word_if_missing(word_command: Callable[['Spellchecker', str], None]
                         ) -> Callable[['Spellchecker', str], None]:
    def wrapper(self: 'Spellchecker', word: str) -> None:
        if not word:
            new_word = self.word_under_cursor()
            if new_word is None:
                self.error('No word under the cursor')
                return
            word = new_word
        return word_command(self, word)
    return wrapper


class Spellchecker(QtCore.QObject, KalpanaObject):

    rehighlight = QtCore.pyqtSignal()
    rehighlight_word = QtCore.pyqtSignal(str)

    def __init__(self, config_dir: Path,
                 word_under_cursor: Callable[[], Optional[str]]) -> None:
        super().__init__()
        self.word_cache: Dict[str, bool] = {}
        self.word_under_cursor = word_under_cursor
        self.kalpana_settings = ['spellcheck-active', 'spellcheck-language']
        self.kalpana_commands = [
                Command('toggle-spellcheck', 'Toggle the spellcheck.',
                        self.toggle_spellcheck,
                        args=ArgumentRules.NONE,
                        short_name='&',
                        category='spellcheck'),
                Command('set-spellcheck-language',
                        'Set the spellcheck language',
                        self.set_language,
                        short_name='l',
                        category='spellcheck',
                        arg_help=((' en-US',
                                   'Set the language to English.'),)),
                Command('suggest-spelling',
                        'Suggest spelling corrections for a word.',
                        self.suggest,
                        short_name='@',
                        category='spellcheck',
                        arg_help=(('', 'Suggest spelling corrections for '
                                   'the word under the cursor.'),
                                  ('foo', 'Suggest spelling corrections for '
                                   'the word "foo".'))),
                Command('add-word', 'Add word to the spellcheck word list.',
                        self.add_word,
                        short_name='+',
                        category='spellcheck',
                        arg_help=(('', 'Add the word under the cursor to the '
                                   'dictionary.'),
                                  ('foo', 'Add the word "foo" to the '
                                   'dictionary.')))
        ]
        self.kalpana_autocompletion_patterns = [
                AutocompletionPattern('set-spellcheck-language',
                                      get_spellcheck_languages,
                                      prefix=r'l\s*',
                                      illegal_chars=' ')
        ]
        self.language = 'en_US'
        self.pwl_path = config_dir / 'spellcheck-pwl'
        self.pwl_path.mkdir(exist_ok=True, parents=True)
        pwl = self.pwl_path / (self.language + '.pwl')
        self.language_dict = enchant.DictWithPWL(self.language, pwl=str(pwl))
        self.spellcheck_active = False

    @command_callback
    @_get_word_if_missing
    def add_word(self, word: str) -> None:
        """
        Add a word to the spellcheck dictionary.

        This automatically saves the word to the wordlist file as well.
        """
        self.language_dict.add_to_pwl(word)
        self.word_cache[word] = True
        self.rehighlight_word.emit(word)
        self.log(f'Added "{word}" to dictionary')

    @command_callback
    @_get_word_if_missing
    def suggest(self, word: str) -> None:
        """Print spelling suggestions for a certain word."""
        suggestions = ', '.join(self.language_dict.suggest(word)[:5])
        self.log(f'{word}: {suggestions}')

    def check_word(self, word: str) -> bool:
        """A callback for the highlighter to check a word's spelling."""
        if word in self.word_cache:
            return self.word_cache[word]
        result = self.language_dict.check(word)
        self.word_cache[word] = result
        return result

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'spellcheck-active':
            self.spellcheck_active = bool(new_value)
            self.rehighlight.emit()
        elif name == 'spellcheck-language':
            self._change_language(str(new_value))

    @command_callback
    def set_language(self, language: str) -> None:
        """Set the language. (callback for the terminal command)"""
        self._change_language(language)
        self.change_setting('spellcheck-language', self.language)

    def _change_language(self, language: str) -> None:
        if not language:
            self.error('No language specified')
            return
        try:
            pwl = self.pwl_path / (language + '.pwl')
            self.language_dict = enchant.DictWithPWL(language, pwl=str(pwl))
        except enchant.errors.DictNotFoundError:
            self.error(f'Invalid language: {language}')
        else:
            self.language = language
            self.rehighlight.emit()

    @command_callback
    def toggle_spellcheck(self) -> None:
        self.spellcheck_active = not self.spellcheck_active
        if self.spellcheck_active:
            self.log('Spellcheck activated')
        else:
            self.log('Spellcheck deactivated')
        self.change_setting('spellcheck-active', self.spellcheck_active)
        self.rehighlight.emit()
