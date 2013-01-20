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

Apart from that, there can be as many other files in the plugin's directory as wanted.

The main module must define a class called ``UserPlugin``, as a subclass of ``pluginlib.GUIPlugin``.


pluginlib Reference
-------------------
For all references to Qt classes, see http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/classes.html

.. _Python: http://www.python.org/

Constants
=========
NORTH, SOUTH, EAST, WEST
    The sides to which a widget can be added in ``add_widget()``.


"Events"
========
*These methods are called by Kalpana itself. You most likely do not want to call them manually. The scare quotes are there to remind you that they are regular functions and all you need to do is overload them. Nothing fancy.*

GUIPlugin.start(self)
    Is called when the plugin has been initiated. This is the equivalent of a constructor. **Do not use __init__()!**

GUIPlugin.read_config(self, path)
    Is called when the config is (re)loaded. `path` is the path to the plugin's *directory*. The plugin must find and read its config file itself, if it has one.

GUIPlugin.write_config(self, path)
    Is called when the config is saved. `path` is the path to the plugin's *directory*. The plugin must find and write its config file itself, if it has one.


Regular methods
===============
*These methods will never be called by Kalpana. You most likely do not want to overload them with your own versions.*

GUIPlugin.add_widget(widget, side)
    Add a widget (must be a ``QtGui.QWidget``) to the specified side of Kalpana's main textarea. The sides are ``NORTH``, ``SOUTH``, ``EAST`` or ``WEST`` (see above).
    All widgets are added to the right of *the widget added just before*. This means that the earlier a plugin is loaded, the farther to the left it will be, while still on the specified side of the textarea.

GUIPlugin.get_text()
    Return the text currently in the main textarea in Kalpana. This is a wrapper around ``QTextDocument.toPlainText()``.
