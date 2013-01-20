Kalpana
=======

A not so very user friendly text editor made probably not for you.


Technical shit
--------------
* Written in Python 3, will not work on Python 2 or earlier
* Requires either PySide or PyQt
* Probably wont work on Mac


Keyboard shortcuts not readily available anywhere else
------------------------------------------------------
* `Ctrl + Enter`: Toggles terminal
* `Alt + [Right/Left]`: Move the divider in the terminal


Font change dialog howto
------------------------
* `Enter`: Finish and return with the chosen font
* `Escape`: Exit without changing anything
* `Left/Right` or `Tab`: Jump between the font and size lists
* `Up/Down`: Why do I even write this


The usual shortcuts
-------------------
* `Ctrl + N`: New
* `Ctrl + O`: Open
* `Ctrl + S`: Save
* `Ctrl + Shift + S`: Save as
* `F3`: Find next (has to first search for something in the terminal)


Theme config
------------
Styling is done in the `theme` part of the config (`~/.config/kalpana/kalpana.conf` on Linux and `kalpana.json` in kalpana.py3's directory on Windows) with css-like values.

Four values are non-essential and can be left blank:

* `term_input_bgcolor` and `term_output_bgcolor` will be overloaded with `main_bgcolor`'s value if empty.
* `term_input_textcolor` and `term_output_textcolor` will be overloaded with `main_textcolor`'s value if empty.

All others should be specified but Kalpana will probably run without them anyway.


Plugins
-------
_Note: all names here are up for debate and/or pending change_

All plugins should consist of (at least) one python module in their own directory in the `config/plugins/` directory. The module and its parent directory must have the same name (case-sensitive).

Example: `~/.config/kalpana/plugins/myplugin/myplugin.py`

The module must contain a class called UserPlugin that subclasses `pluginlib.GUIPlugin`.

More info is available in `plugin_docs.rst`.
