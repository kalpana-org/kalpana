
import enchant
from typing import Any, List, Tuple

from PyQt5 import QtCore

from kalpana.autocompletion import AutocompletionPattern
from kalpana.common import Command, KalpanaObject
from kalpana.textarea import TextArea


def get_spellcheck_languages(name: str, text: str) -> List[Tuple[str, int]]:
    return [(lang, None) for lang in sorted(enchant.list_languages())
            if lang.startswith(text)]


class Spellchecker(QtCore.QObject, KalpanaObject):

    def __init__(self, textarea: TextArea) -> None:
        super().__init__()
        self.kalpana_settings = ['spellcheck-active', 'spellcheck-language']
        self.kalpana_commands = [
                Command('toggle-spellcheck', '', self.toggle_spellcheck,
                        accept_args=False),
                Command('set-spellcheck-language', '', self.set_language),
                Command('suggest-spelling',
                        'Print a list of possible spellings for the argument or the word under the cursor.',
                        self.suggest),
        ]
        self.kalpana_autocompletion_patterns = [
                AutocompletionPattern(name='set-spellcheck-language',
                                      prefix=r'set-spellcheck-language\s+',
                                      illegal_chars=' ',
                                      get_suggestion_list=get_spellcheck_languages),
        ]
        self.textarea = textarea
        self.language = 'en_US'
        self.language_dict = enchant.Dict(self.language)
        self.highlighter = self.textarea.highlighter
        self.highlighter.spellcheck_word = self.check_word
        self.spellcheck_active = False

    def check_word(self, word: str) -> bool:
        return self.language_dict.check(word)

    def suggest(self, word: str) -> None:
        if not word:
            word = self.textarea.word_under_cursor()
        self.log('{}: {}'.format(word, ', '.join(self.language_dict.suggest(word))))

    def setting_changed(self, name: str, new_value: Any) -> None:
        if name == 'spellcheck-active':
            self.highlighter.spellcheck_active = bool(new_value)
            self.highlighter.rehighlight()
        elif name == 'spellcheck-language':
            self.set_language(str(new_value))
            # self.rehighlight()

    def set_language(self, language: str) -> None:
        try:
            self.language_dict = enchant.Dict(language)
        except enchant.errors.DictNotFoundError:
            self.error('invalid language: {}'.format(language))
        else:
            self.language = language
            self.highlighter.rehighlight()

    def toggle_spellcheck(self) -> None:
        self.highlighter.spellcheck_active = not self.highlighter.spellcheck_active
        self.highlighter.rehighlight()
