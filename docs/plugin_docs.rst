===================
 The plugin system
===================

Location and structure
----------------------

All plugins are located in the `plugins` subdirectory of Kalpana's config directory.

Every plugin consists (at least) of a directory containing a python plugin of the same name. They must match exactly, including case.

*Example:* ``~/.config/kalpana/plugins/myplugin/myplugin.py``

The main module must define a class called ``UserPlugin``, as a subclass of ``pluginlib.GUIPlugin``.


Load order
----------

All plugins are loaded in a specific order dictated by ``loadorder.conf``. Every line is treated as the name of one plugin. The first line is loaded first, the second line second, etc. Lines beginning with '#' are ignored.

The point of the load order is to manage conflicts between plugins. Plugins loaded after another plugin can override the previous plugin's edits, such as hotkeys, terminal commands and GUI widget placement.


Imports
-------
As of [we don't use version numbers no more], all Qt-imports must be made using PyQt4. PySide is no longer supported and therefore having the imports implementation agnostic and done in common is not neccessary.


libsyntyche.common Reference
----------------------------
common includes some miscellaneous useful functions. Import it with `import libsyntyche.common` or `from libsyntyche import common` or any other way that is supported by standard Python modules. (Just like PyQt.QtGui and so on)

See https://github.com/nycz/libsyntyche for more info.


pluginlib Reference
-------------------
For all references to Qt classes, see http://pyqt.sourceforge.net/Docs/PyQt4/classes.html

**Do not forget the to call the super-class' constructor in your UserPlugin! Eg.:** ``super().__init__(objects, get_path)``


Fields
======
GUIPlugin.commands
    * A dict with terminal commands as key and a tuple with a function and a help-string as value. The function will be called when the command is entered in the terminal. The commands will **overwrite** vanilla commands and commands in earlier loaded plugins, if they are identical.
    * The command should be a short string (1-2 characters preferably).
    * *Example:* ``{'x': (self.explode, 'This will make everything explode')}``
    * The function must take one argument (the terminal argument) which will be a string (it may be an empty string).
    * *Example:* ``def explode(self, argument):``
    * The return value does nothing.


GUIPlugin.hotkeys
    * A dict with keyboard shortcuts as key (see ``QKeySequence()``) and a function as value. The function will be called by Kalpana when the key (combination) is pressed. The key combinations will **overwrite** vanilla shortcuts and shortcuts in earlier loaded plugins, if they are identical.
    * *Example:* ``{'Ctrl+Shift+X': self.do_something_useful()}``


"Events"
========
GUIPlugin.__init__(self, objects, get_path)
    * objects is a dict:
        * 'mainwindow': mainwindow,
        * 'textarea': textarea,
        * 'terminal': terminal,
        * 'settings manager': settings_manager
    * get_path is a function that returns a string with the path to the plugin's directory. This is where config files should be stored.

GUIPlugin.read_config(self)
    * Is called when the config is (re)loaded.

GUIPlugin.write_config(self)
    * Is called when the config is saved.


Regular methods
===============
*These methods will never be called by Kalpana. You most likely do not want to overload them with your own versions.*

GUIPlugin.print_(self, text)
    * text will be shown in the terminal

GUIPlugin.error(self, text)
    * text will be shown as an error in the terminal
