===================
 The plugin system
===================

Location and structure
----------------------

All plugins are located in the `plugins` subdirectory of Kalpana's config directory. This would be:

| *On Linux:* ``~/.config/kalpana/plugins/``
| *On Windows:* ``[Kalpana's working directory]/plugins/``

Every plugin consists (at least) of a directory containing a python plugin of the same name. They must match exactly, including case.

*Example:* ``~/.config/kalpana/plugins/myplugin/myplugin.py``

If a file with the name ``qtstylesheet.css`` is present, it will be merged with the main stylesheet and applied to the program. When loaded, the stylesheet may be format()ed using a values from the plugin's config. **Remember to escape all { and } if you use a theme config!** Otherwise Kalpana will most likely explode.

Apart from that, there can be as many other files in the plugin's directory as wanted.

The main module must define a class called ``UserPlugin``, as a subclass of ``pluginlib.GUIPlugin``.


Load order
----------

All plugins are loaded in a specific order dictated by ``loadorder.conf``. This file is generated automatically and is not meant to be edited. To edit the load order, use the command ``lo``.

The point of the load order is to manage conflicts between plugins. Plugins loaded after another plugin can override the previous plugin's edits, such as hotkeys, terminal commands and GUI widget placement.

Using ``lo`` you can also deactivate mods without having to remove them from the ``plugins`` directory.


Imports
-------
As of [we don't use version numbers no more], all Qt-imports should be made using PyQt4. PySide is no longer supported and therefore having the imports implementation agnostic and done in common is not neccessary.


common Reference
----------------
common includes some miscellaneous useful functions.

Functions
=========
read_json(path)
    * Return the content of the json-config file as a corresponding python object (usually a dict, tuple or list)

write_json(path, data)
    * Write the ``data`` to the specified ``path``.
    * ``data`` can be any python object (see the json library docs for more info) but most times you would want to use a dict, list or tuple. Lists' and tuples' order will be preserved.


pluginlib Reference
-------------------
For all references to Qt classes, see http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/classes.html

Constants
=========
NORTH, SOUTH, EAST, WEST
    * The sides to which a widget can be added in ``add_widget()``.

Fields
======
GUIPlugin.commands
    * A dict with terminal commands as key and a tuple with a function and a help-string as value. The function will be called when the command is entered in the terminal. The commands will **overwrite** vanilla commands and commands in earlier loaded plugins, if they are identical.
    * The command should be a short string (1-2 characters preferably).
    * *Example:* ``{'x': (self.explode, 'This will make everything explode')}``
    * The function must take one argument (the terminal argument) which will be a string (it may be an empty string).
    * *Example:* ``def explode(self, argument):``
    * The function may return a tuple with a string to be printed to the terminal and a bool indication an error (``True`` for error, ``False`` for no error). If nothing is return, nothing will be printed.
    * *Example:* ``("This is awesome", False)`` or ``("Oh shit everything blew up", True)``


GUIPlugin.hotkeys
    * A dict with keyboard shortcuts as key (see ``QKeySequence()``) and a function as value. The function will be called by Kalpana when the key (combination) is pressed. The key combinations will **overwrite** vanilla shortcuts and shortcuts in earlier loaded plugins, if they are identical.
    * *Example:* ``{'Ctrl+Shift+X': self.do_something_useful()}``

GUIPlugin.path
    * A string with the path to the plugin's directory. This is where config files should be stored.


"Events"
========
*These methods are called by Kalpana itself. You most likely do not want to call them manually. The scare quotes are there to remind you that they are regular functions and all you need to do is overload them. Nothing fancy.*

GUIPlugin.start(self)
    * Is called when the plugin has been initiated. This is the equivalent of a constructor. **Do not use __init__()!**

GUIPlugin.config_changed(self)
    * Is called when the (text in the) document is modified.

GUIPlugin.file_saved(self)
    * Is called when the file is saved.

GUIPlugin.read_config(self)
    * Is called when the config is (re)loaded.

GUIPlugin.write_config(self)
    * Is called when the config is saved.

GUIPlugin.theme_config(self)
    * Is called whenever the theme is reloaded.
    * Must return a dict with strings to be replaced with strings in the plugin's ``qtstylesheet.css``. See ``defaultcfg.json`` and ``qtstylesheet.css`` for real life examples.
    * Do not overload it if you do not wish to modify the stylesheet with the config.
    * *Example:* {"details_color": "#111", "term_fontfamily": "Monospace"}


Regular methods
===============
*These methods will never be called by Kalpana. You most likely do not want to overload them with your own versions.*

GUIPlugin.add_widget(widget, side)
    * Add a widget (must be a ``QtGui.QWidget``) to the specified side of Kalpana's main textarea. The sides are ``NORTH``, ``SOUTH``, ``EAST`` or ``WEST`` (see above).
    * All widgets are added to the right of *the widget added just before*. This means that the earlier a plugin is loaded, the farther to the left it will be, while still on the specified side of the textarea.

GUIPlugin.get_filepath()
    * Return the path of the file currently open in Kalpana.
    * If no file is open or saved, an empty string is returned.

GUIPlugin.get_text()
    * Return the text currently in the main textarea in Kalpana. This is a wrapper around ``QTextDocument.toPlainText()``.

GUIPlugin.new_file(force=False)
    * Try to open a new file.
    * If ``force`` is True, ignore unsaved changes and create a new file anyway.
    * Return True if it was successful, otherwise False

GUIPlugin.open_file(filename)
    * Try to open another file. ``filename`` is the file to be opened.
    * Return True if it was successful, otherwise False

GUIPlugin.save_file(filename="")
    * Try to save the currently open file.
    * If ``filename`` is not specified, save the file with the current filename.
    * Return True if it was successful, otherwise False

GUIPlugin.quit()
    * Try to close Kalpana. Will not work unless all changes to the current file is saved.
