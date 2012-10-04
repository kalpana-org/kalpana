Kalpana
=======

A not so very user friendly text editor made probably not for you.


Keyboard shortcuts not readily available anywhere else
------------------------------------------------------
* `Ctrl + Enter`: Toggles terminal
* `Ctrl + P`: Toggles NaNo sidebar
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
Styling is done in the `theme` part of the config (`.kalpana` on Linux and `kalpana.json` in kalpana.py3's directory on Windows) with css-like values.

Six values are non-essential and can be left blank:

* `term_input_bgcolor`, `term_output_bgcolor` and `nano_bgcolor` will be overloaded with `main_bgcolor`'s value if empty.
* `term_input_textcolor`, `term_output_textcolor` and `nano_textcolor` will be overloaded with `main_textcolor`'s value if empty.

All others should be specified but Kalpana will probably run without them anyway.