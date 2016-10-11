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

import enchant
import os
from os.path import join
from typing import Any

from PyQt5 import QtCore

from kalpana.common import AutocompletionPattern, Command, KalpanaObject, SuggestionListAlias
from kalpana.textarea import TextArea


def get_spellcheck_languages(name: str, text: str) -> SuggestionListAlias:
    """Return a list with the tags of all available spellcheck languages."""
    return [(lang, None) for lang in sorted(enchant.list_languages())
            if lang.startswith(text)]


class Spellchecker(QtCore.QObject, KalpanaObject):

    rehighlight = QtCore.pyqtSignal()

    def __init__(self, config_dir: str, textarea: TextArea) -> None:
        super().__init__()
        self.kalpana_settings = ['spellcheck-active', 'spellcheck-language']
        self.kalpana_commands = [
                Command('toggle-spellcheck', '', self.toggle_spellcheck,
                        accept_args=False),
                Command('set-spellcheck-language', '', self.set_language),
                Command('suggest-spelling',
                        'Print a list of possible spellings for the argument '
                        'or the word under the cursor.',
                        self.suggest),
                Command('add-word', 'Add word to the spellcheck word list.',
                        self.add_word)
        ]
        self.kalpana_autocompletion_patterns = [
                AutocompletionPattern(name='set-spellcheck-language',
                                      prefix=r'set-spellcheck-language\s+',
                                      illegal_chars=' ',
                                      get_suggestion_list=get_spellcheck_languages),
        ]
        self.textarea = textarea
        self.language = 'en_US'
        self.pwl_path = join(config_dir, 'spellcheck-pwl')
        os.makedirs(self.pwl_path, exist_ok=True)
        pwl = join(self.pwl_path, self.language + '.pwl')
        self.language_dict = enchant.DictWithPWL(self.language, pwl=pwl)
        self.spellcheck_active = False

    def add_word(self, word: str) -> None:
        """
        Add a word to the spellcheck dictionary.

        This automatically saves the word to the wordlist file as well.
        """
        if not word:
            word = self.textarea.word_under_cursor()
        self.language_dict.add_to_pwl(word)
        self.rehighlight.emit()

    def suggest(self, word: str) -> None:
        """Print spelling suggestions for a certain word."""
        if not word:
            word = self.textarea.word_under_cursor()
        self.log('{}: {}'.format(word, ', '.join(self.language_dict.suggest(word)[:5])))

    def check_word(self, word: str) -> bool:
        """A callback for the highlighter to check a word's spelling."""
        return self.language_dict.check(word)

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'spellcheck-active':
            self.spellcheck_active = bool(new_value)
            self.rehighlight.emit()
        elif name == 'spellcheck-language':
            self.set_language(str(new_value))

    def set_language(self, language: str) -> None:
        if not language:
            self.error('No language specified')
            return
        try:
            pwl = join(self.pwl_path, language + '.pwl')
            self.language_dict = enchant.DictWithPWL(language, pwl=pwl)
        except enchant.errors.DictNotFoundError:
            self.error('Invalid language: {}'.format(language))
        else:
            self.language = language
            self.rehighlight.emit()

    def toggle_spellcheck(self) -> None:
        self.spellcheck_active = not self.spellcheck_active
        self.rehighlight.emit()
