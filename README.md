Kalpana
=======

A not so very user friendly text editor made probably not for you.

*Kalpana* is also a feminine Hindu name meaning *imagination*, *fantasy*, *creativity*. Can be written as  कल्पना (Hindi).


Technical shit
--------------
* Written in Python 3, will not work on Python 2 or earlier
* Requires PyQt
* Requires libsyntyche *(https://github.com/nycz/libsyntyche)*
* Probably won't work on Mac


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

Also, http://qt-project.org/doc/qt-4.8/stylesheet-reference.html is documentation on how Qt's stylesheets work.


Plugins
-------
_Note: all names here are up for debate and/or pending change_

All plugins should consist of (at least) one python module in their own directory in the `config/plugins/` directory. The module and its parent directory must have the same name (case-sensitive).

Example: `~/.config/kalpana/plugins/myplugin/myplugin.py`

The module must contain a class called UserPlugin that subclasses `pluginlib.GUIPlugin`.

All plugins are loaded in a specific order dictated by `loadorder.conf`. This file is generated automatically and is not meant to be edited. To edit the load order, use the command `lo`. Plugins loaded after another plugin can override the previous plugin's edits, such as hotkeys, terminal commands and GUI widget placement.

More info is available in `plugin_docs.rst`.
