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

from typing import Callable, Dict, List, Optional, Tuple
import re

from kalpana.common import AutocompletionPattern, SuggestionListAlias


class ListWidget:
    @property
    def visible(self) -> bool: ...

    @visible.setter
    def visible(self, visible: bool) -> None: ...

    @property
    def selection(self) -> int: ...

    @selection.setter
    def selection(self, selection: int) -> None: ...

    def set_suggestions(self, suggestions: SuggestionListAlias,
                        selection: int, text_fragment: str) -> None: ...

    def set_help_text(self, help_text: str) -> None: ...


class InputWidget:
    @property
    def text(self) -> str:
        raise NotImplementedError

    @text.setter
    def text(self, text: str) -> None: ...

    @property
    def cursor_position(self) -> int: ...

    @cursor_position.setter
    def cursor_position(self, cursor_position: int) -> None: ...





class SuggestionList():

    def __init__(self, list_widget: ListWidget, input_widget: InputWidget,
                 run_command: Callable[[str, Optional[str]], None]) -> None:
        self.list_widget = list_widget
        self.input_widget = input_widget
        self.run_command = run_command
        self.command_help_texts = {}  # type: Dict[str, str]
        self.suggestions = []  # type: SuggestionListAlias
        self.unautocompleted_cmd = None  # type: Optional[str]
        self.history = []  # type: SuggestionListAlias
        self.history_active = False
        self._selection = 0
        self.autocompletion_patterns = []  # type: List[AutocompletionPattern]
        self.active_pattern = ''  # type: str
        self.completable_span = (0, 0)

    @property
    def selection(self) -> int:
        """Get the position of the selected item in the list of suggestions."""
        return self._selection

    @selection.setter
    def selection(self, pos: int) -> None:
        self._selection = max(0, min(pos, len(self.suggestions)-1))
        if not self.history and self.active_pattern == 'command':
            cmd = self.suggestions[self.selection][0]
            self.list_widget.set_help_text(self.command_help_texts.get(cmd, ''))
        else:
            self.list_widget.set_help_text('')
        self.list_widget.selection = self._selection

    def up_pressed(self) -> None:
        """Should be called whenever the up key is pressed."""
        if self.list_widget.visible:
            self.selection -= 1
        else:
            if self.history:
                self.suggestions = self.history
                self.selection = len(self.suggestions) - 1
                self.history_active = True
                self.list_widget.set_suggestions(self.suggestions, self.selection, '')

    def down_pressed(self) -> None:
        """Should be called whenever the down key is pressed."""
        if self.list_widget.visible:
            self.selection += 1

    def tab_pressed(self) -> None:
        """Should be called whenever the tab key is pressed."""
        if self.list_widget.visible:
            self._autocomplete()
        else:
            self._update_suggestions(self.input_widget.text)

    def return_pressed(self) -> None:
        """Should be called whenever the return key is pressed."""
        if self.history_active:
            self.input_widget.text = self.suggestions[self.selection][0]
            self.history_active = False
            self.list_widget.visible = False
            return
        text = self.input_widget.text.strip()
        if not text:
            return
        self.run_command(text, self.unautocompleted_cmd)
        self.unautocompleted_cmd = None
        self.input_widget.text = ''

    def update(self) -> None:
        if self.input_widget.text:
            self._update_suggestions(self.input_widget.text)
        else:
            self.list_widget.visible = False

    def _autocomplete(self) -> None:
        if not self.suggestions:
            return
        if self.history_active:
            self.input_widget.text = self.suggestions[self.selection][0]
            self.history_active = False
            self.list_widget.visible = False
            return
        start, end = self.completable_span
        if self.active_pattern == 'command':
            self.unautocompleted_cmd = self.input_widget.text[start:end]
        new_fragment = self.suggestions[self.selection][0]
        self.input_widget.text = self.input_widget.text[:start] + new_fragment + self.input_widget.text[end:]
        self.input_widget.cursor_position = start + len(new_fragment)

    def _update_suggestions(self, text: str) -> None:
        suggestions, span, pattern_name =\
                        _generate_suggestions(self.autocompletion_patterns,
                                              text, self.input_widget.cursor_position)
        self.completable_span = span
        self.active_pattern = pattern_name
        if suggestions != self.suggestions:
            self.suggestions = suggestions
            self.selection = len(suggestions) - 1
        self.list_widget.set_suggestions(suggestions, self.selection, '')

    def add_autocompletion_pattern(self, pattern: AutocompletionPattern) -> None:
        self.autocompletion_patterns.append(pattern)


def _contains_illegal_chars(text: str, illegal_chars: str) -> bool:
    """
    Check if a string includes any illegal characters.

    Args:
        text: The string to be checked.
        illegal_chars: A string with the characters text may not include.
    """
    for char in illegal_chars:
        if char in text:
            return True
    return False


def _generate_suggestions(autocompletion_patterns: List[AutocompletionPattern],
                          rawtext: str, rawpos: int)\
                          -> Tuple[SuggestionListAlias, Tuple[int, int], str]:
    for ac in autocompletion_patterns:
        prefix = re.match(ac.prefix, rawtext)
        if prefix is None:
            continue
        prefix_length = len(prefix.group(0))
        # Dont match anything if the cursor is in the prefix
        if rawpos < prefix_length:
            continue
        pos = rawpos - prefix_length
        text = rawtext[prefix_length:]
        start_matches = [x for x in re.finditer(ac.start, text)
                         if x.end() <= pos]
        end_matches = [x for x in re.finditer(ac.end, text)
                       if x.start() >= pos]
        if not start_matches or not end_matches:
            continue
        start = start_matches[-1].end()
        end = end_matches[0].start()
        matchtext = text[start:end]
        if _contains_illegal_chars(matchtext, ac.illegal_chars):
            continue
        normalized_span = (start+prefix_length, end+prefix_length)
        return ac.get_suggestion_list(ac.name, matchtext), normalized_span, ac.name
    return [], (0, len(rawtext)), ''
