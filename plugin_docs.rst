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
    * The function may return a tuple with a string to be printed to the terminal and a bool indication an error (``True`` for error, ``False`` for no error). If nothing is return, nothing will be printed.
    * *Example:* ``("This is awesome", False)`` or ``("Oh shit everything blew up", True)``


GUIPlugin.hotkeys
    * A dict with keyboard shortcuts as key (see ``QKeySequence()``) and a function as value. The function will be called by Kalpana when the key (combination) is pressed. The key combinations will **overwrite** vanilla shortcuts and shortcuts in earlier loaded plugins, if they are identical.

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

GUIPlugin.get_filename()
    * Return the name of the file current open in Kalpana.
    * If no file is open or saved, an empty string is returned.

GUIPlugin.get_text()
    * Return the text currently in the main textarea in Kalpana. This is a wrapper around ``QTextDocument.toPlainText()``.
