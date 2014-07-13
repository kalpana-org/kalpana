Kalpana
=======

A not so very user friendly text editor made probably not for you.

*Kalpana* is also a feminine Hindu name meaning *imagination*, *fantasy*, *creativity*. Can be written as  कल्पना (Hindi).


Technical shit
--------------
* Written in Python 3, will not work on Python 2 or earlier
* Requires PyQt
* Requires libsyntyche *(https://github.com/nycz/libsyntyche)*
* Optionally requires PyEnchant and language dictionaries for Enchant's backends (eg. Hunspell, Aspell) for the spell check to work
* Probably won't work on Mac


Shortcuts
-------------------
* `Ctrl + N` – New
* `Ctrl + O` – Open
* `Ctrl + S` – Save
* `Ctrl + Shift + S` – Save as
* `F3` – Find next (has to first search for something in the terminal)
* `Escape` – Toggle terminal *(default)*


Commands
--------
* `&` – See *Spell check*
* `/` – See *Search and replace*
* `:<line>` – Go to `<line>`
* `=<option> [<value>]` – Show `<option>`'s value or set it to `<value>`
* `?[<command>]` – List all commands or show help for `<command>`
* `c` – Print wordcount
* `f[ndm]` – Print file info, n for name, d for directory, m for modified or nothing for full path
* `n[!]` – Create new file, use `!` to ignore unsaved changes
* `o[!] <filename>` – Open `<filename>`, use `!` to ignore unsaved changes
* `p` – List all active plugins
* `q[!]` – Quit, use `!` to ignore unsaved changes
* `s[!] [<filename>]` – Save the opened file, or save to `<filename>`. Use `!` to ignore existing file


Tab completion
--------------
For commands `o` and `s`, you can use tab to autocomplete filepaths in the terminal. Pressing tab without a filepath inserts the current working directory (where kalpana was started from)


Spell check
-----------
The spell checking uses PyEnchant and requires language dictionaries to be installed for it to work properly. Kalpana will run without either, but the spell check will not.

The *default* language is set in the config, but changing it will only change which language is set when Kalpana starts. To change during run-time, use the appropriate command below.

Custom words can be added to the so-called *personal word list* to stop them from being flagged by the spell check. The lists are unique for each language code and are saved in files in the `spellcheck-pwl` directory in the config directory.

* `&` – Toggle spell check on/off
* `&<languagecode>` – Set the language (eg. `en_US`)
* `&=` – Show word suggestions for the word the cursor is in
* `&+[<word>] – Add a word to the personal word list, omit `<word>` to automatically insert the word the cursor currently is in


Search and replace
------------------
Kalpana uses a vim-like syntax, meaning that you will have to escape forward-slash `/` with backslash like `\/` if you want to search for it. Search terms are case-sensitive search by default.

* `/<search>[/[FLAGS]]`
* `/<search>/[<replace>]/[FLAGS]`
* Flags:
    * `a`: Replace all matched search terms
    * `b`: Search/replace backwards
    * `i`: Case-insensitive search
    * `w`: Match only whole words


Config
------
The config directory is in `~/.config/kalpana` on Linux and the local directory (where `kalpana.py` is) on Windows. This directory contains (among other things, in the case of Windows) `kalpana.conf`, `loadorder.conf`, `stylesheet.css` and the `plugin` directory.

The main config file (`kalpana.conf`) is automagically created from the default config (not simply copied) if it doesn't exist. It is not meant to be edited by hand but have fun if you're wild and crazy. Any setting keys that don't match settings in the default config are removed and any illegal options are reverted to default. Basically, don't fuck with da config, yo.

The config is reloaded everytime Kalpana is activated, which means that if you change something in one instance of Kalpana, as soon as you change to another one it gets that change as well.

###Options###
* `ai` – Use auto-indentation. *Allowed values: true/false*
* `dl` – Default language for spell checking. *Allowed values: language codes for existing PyEnchant-compatible language dictionaries (eg. en_US)*
* `ln` – Show line numbers. *Allowed values: true/false*
* `nw` – Open files in a new windows. *Allowed values: true/false*
* `sit` – Set focus on the terminal on startup. *Allowed values: true/false*
* `tk` – Terminal toggling hotkey. *Allowed values: http://pyqt.sourceforge.net/Docs/PyQt4/qkeysequence.html*
* `ato` – Animate the terminal output, typing out each character one by one. *Allowed values: true/false*
* `tai` – The interval of each character being typed out in the output part of the terminal, in milliseconds. *Allowed values: a positive integer*
* `vs` – Show the vertical scrollbar. *Allowed values: `on`/`off`/`auto`, auto means it only appears when needed*
* `pw` – Set the maximum width of the page (the space you actually write text). *Allowed values: a positive integer*
* `swc` – Toggle the automatically updating wordcount in the titlebar. If this is disabled, wordcount can still be shown using the `c` command. Note that on slower computers and/or large files, enabling this option may slow down Kalpana. *Allowed values: true/false*

Boolean values (true/false) can be represented as `y`, `1` or `true` and `n`, `0` or `false` respectively (case-insensitive).


Theme config
------------
The theme is specified in `stylesheet.css` in the config directory. If the file doesn't exist, Kalpana will copy and use `themes/default.css` instead.

The syntax used is libsyntyche's modified version of Qt's stylesheets:
https://github.com/nycz/libsyntyche


Plugins
-------
See `docs/plugin_docs.rst`.
