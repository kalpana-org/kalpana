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


Search and replace
------------------
Kalpana uses a vim-like syntax, meaning that you will have to escape forward-slash `/` with backslash like `\/` if you want to search for it. Search terms are case-sensitive search by default.

* `/<search>[/[FLAGS]]`
* `/<search>/[<replace>]/[FLAGS]`
* Flags:
    * `a` – Replace all matched search terms
    * `b` – Search/replace backwards
    * `i` — Case-insensitive search
    * `w` – Match only whole words


Shortcuts
-------------------
* `Ctrl + N`: New
* `Ctrl + O`: Open
* `Ctrl + S`: Save
* `Ctrl + Shift + S`: Save as
* `F3`: Find next (has to first search for something in the terminal)
* `Escape`: Toggle terminal *(default)*

*__NOTE:__ The terminal toggle key is configurable. Valid settings are explained here:
http://pyqt.sourceforge.net/Docs/PyQt4/qkeysequence.html*


Config
------
The config directory is in `~/.config/kalpana` on Linux and the local directory (where `kalpana.py` is) on Windows. This directory contains (among other things, in the case of Windows) `kalpana.conf`, `loadorder.conf`, `stylesheet.css` and the `plugin` directory.

The main config file (`kalpana.conf`) is automagically created from the default config (not simply copied) if it doesn't exist. It is not meant to be edited by hand but have fun if you're wild and crazy. Any setting keys that don't match settings in the default config are removed and any illegal options are reverted to default. Basically, don't fuck with da config, yo.

The config is reloaded everytime Kalpana is activated, which means that if you change something in one instance of Kalpana, as soon as you change to another one it gets that change as well.


Theme config
------------
The theme is specified in `stylesheet.css` in the config directory. If the file doesn't exist, Kalpana will copy and use `themes/default.css` instead.

The syntax used is libsyntyche's modified version of Qt's stylesheets:
https://github.com/nycz/libsyntyche


Plugins
-------
See `docs/plugin_docs.rst`.
