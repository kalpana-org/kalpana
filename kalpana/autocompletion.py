from typing import Callable, Dict, List, Tuple, Union
import re

SuggestionListAlias = List[Tuple[str, int]]
SuggestionCallback = Callable[[str, str], SuggestionListAlias]
AutocompletionPattern = Dict[str, Union[str, bool, SuggestionCallback]]

class SuggestionList():

    def __init__(self, list_widget, input_widget) -> None:
        self.list_widget = list_widget
        self.input_widget = input_widget
        self.suggestions = []  # type: SuggestionListAlias
        self.last_raw_text = ''
        # self.history = []
        self._selection = 0
        self.autocompletion_patterns = []  # type: List[AutocompletionPattern]
        self.active_pattern = None  # type: str
        self.completable_span = (0, 0)

    @property
    def selection(self) -> int:
        """Get the position of the selected item in the list of suggestions."""
        return self._selection

    @selection.setter
    def selection(self, pos: int) -> None:
        self._selection = max(0, min(pos, len(self.suggestions)-1))
        self.list_widget.set_selection(self._selection)

    def up_pressed(self) -> None:
        """Should be called whenever the up key is pressed."""
        if self.list_widget.visible:
            self.selection -= 1
        else:
            # show history
            pass

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
        if not self.list_widget.visible or not self.input_widget.text:
            return
        self._autocomplete()
        # cmd, arg = split_input(self.text)
        # self.command_frequency[cmd] += 1
        # if self.last_autocompletion and self.last_autocompletion != cmd:
        #     self.run_history[self.last_autocompletion][cmd] += 1
        # self.last_autocompletion = None
        # self.run_command(cmd, arg)
        # # TODO: add to history
        # self.text = ''

    def update(self) -> None:
        if self.input_widget.text:
            self._update_suggestions(self.input_widget.text)
        else:
            self.list_widget.visible = False

    def _autocomplete(self) -> None:
        if not self.suggestions:
            return
        start, end = self.completable_span
        self.last_raw_text = self.input_widget.text[start:end]
        new_fragment = self.suggestions[self.selection][0]
        self.input_widget.text = self.input_widget.text[:start] + new_fragment + self.input_widget.text[end:]
        self.input_widget.cursor_position = start + len(new_fragment)

    def _update_suggestions(self, text: str) -> None:
        suggestions, span = _generate_suggestions(self.autocompletion_patterns,
                                                  text,
                                                  self.input_widget.cursor_position)
        self.completable_span = span
        if suggestions != self.suggestions:
            self.suggestions = suggestions
            self.selection = len(suggestions) - 1
        self.list_widget.set_suggestions(suggestions, self.selection, '')

    def add_autocompletion_pattern(self, name: str = '', prefix: str = '',
                                   start: str = r'^', end: str = r'$',
                                   illegal_chars: str = '',
                                   remember_raw_text: bool = False,
                                   get_suggestion_list: SuggestionCallback = None) -> None:
        """
        Add an autocompletion pattern to autocompleter.

        Note that the prefix will be removed from the string the start and end
        regexes are matched against.

        Args:
            name: The pattern's identifier. Should be unique.
            prefix: A regex that matches the start of the input string but
                which will not be considered for autocompletion.
            start: A regex that matches the start of the autocompleted text.
            end: A regex that matches the end of the autocompleted text.
            illegal_chars: A string with all character that the autocompleted
                text may not include.
            remember_raw_text: True if the original string should be saved when
                autocompleting. Useful when you want to remember what a certain
                string has been most often autocompleted to (eg. when
                autocompleting commands).
            get_suggestion_list: A function taking (name, text) as arguments,
                where name is the name of the pattern and text is the string
                that is being autocompleted.
        """
        if get_suggestion_list is None:
            raise ValueError('AC pattern {} must have a suggestion list function!'.format(name))
        self.autocompletion_patterns.append({
                'name': name,
                'prefix': prefix,
                'start': start,
                'end': end,
                'illegal_chars': illegal_chars,
                'remember_raw_text': remember_raw_text,
                'get_suggestions': get_suggestion_list
        })


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


def _generate_suggestions(autocompletion_patterns: List[Dict],
                          rawtext: str,
                          rawpos: int) -> Tuple[SuggestionListAlias, Tuple[int, int]]:
    for ac in autocompletion_patterns:
        prefix = re.match(ac['prefix'], rawtext)
        if prefix is None:
            continue
        prefix_length = len(prefix.group(0))
        # Dont match anything if the cursor is in the prefix
        if rawpos < prefix_length:
            continue
        pos = rawpos - prefix_length
        text = rawtext[prefix_length:]
        start_matches = [x for x in re.finditer(ac['start'], text)
                         if x.end() <= pos]
        end_matches = [x for x in re.finditer(ac['end'], text)
                       if x.start() >= pos]
        if not start_matches or not end_matches:
            continue
        start = start_matches[-1].end()
        end = end_matches[0].start()
        matchtext = text[start:end]
        if _contains_illegal_chars(matchtext, ac['illegal_chars']):
            continue
        normalized_span = (start+prefix_length, end+prefix_length)
        return ac['get_suggestions'](ac['name'], matchtext), normalized_span
    return [], (0, len(rawtext))
