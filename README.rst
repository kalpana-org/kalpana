Kalpana
=======

A clean and very minimalistic text editor/word processor specifically made
for writing longer texts with chapters.

*Kalpana* is also a feminine Hindu name meaning *imagination*, *fantasy*,
*creativity*. Can be written as  कल्पना (Hindi).


Kalpana 2 notes
---------------
This is a complete rewrite of the original Kalpana and is still under pretty
heavy development! Several features from the old version are still missing or
glitchy, so beware. See #81 for the status of the rewrite.

For the old version, use the ``legacy`` branch instead. Kalpana 2 uses a new
default config path so it should be fairly easy to have both active at the same
time.


Requirements
------------
* Linux (probably, other OSes have not been tested)
* Python >= 3.5
* PyQt >= 5.7
* PyEnchant >= 1.6.7 (don't forget the backends, eg. Hunspell or Aspell)
* PyYAML


Installation
------------
Clone the repo, then run this command (as root) in the repo's local directory::

  # pip install -e <local/path/to/gitrepo>

**Note that no dependencies will be installed!**

Run ``kalpana`` without any arguments to create a new file, or run it with
a file path as an argument to open the file. See ``kalpana --help``
for more info.


Usage
-----
Press Escape to open the terminal, then enter a command or press Tab to
autocomplete a command. Pressing Tab with an empty input field will show all
available commands.

Search and replace
~~~~~~~~~~~~~~~~~~
The search and replace functionality is a little... quirky, since it's more or
less exactly copied from Kalpana 1. The command ``search-and-replace`` takes
one argument which is a vim-like search and replace expression, albeit very
scaled down.

* Search: ``/<search>[/[FLAGS]]``
* Replace: ``/<search>/[<replace>]/[FLAGS]``
* Flags:
  * ``a``: Replace all matched search terms (only useful when replacing, obviously)
  * ``b``: Search/replace backwards
  * ``i``: Case-insensitive search
  * ``w``: Match only whole words

(Things inside square brackets are optional.)

Remember to escape any forward slashes with backslash (``\/``) inside the
search- or replace strings. Search terms are case-sensitive by default.

**Examples**::

  search-and-replace /stuff           (searches for "stuff")
  search-and-replace /foo/bar         (replaces the first "foo" with "bar")
  search-and-replace /fooz//a         (removes all "fooz")
  search-and-replace /test/boop/iw    (replaces first word "test" with "boop",
                                       case-insensitively)
  search-and-replace /nope/b          (searches for "nope", backwards)


Text formatting
---------------
Despite its minimalistic nature, Kalpana does have simple formatting available.
For example, if you surround a line or a part of a line with asterisks `*`, the
text will be shown as bold.

In later versions, this will be configurable, but as of this vesion, it is
still hardcoded. Right now, formats also don't work over multiple lines.
Customizing the existing formatting in the stylesheet is not yet implemented
either. (The few options that look relevant are for the chapter overview, not
the main textarea.)

Chapter formatting
~~~~~~~~~~~~~~~~~~
Chapter syntax will be formatted as well, such as chapter titles, descriptions,
and more. These lines are also used when generating the chapter overview.
See the Chapter section below for more info.

**Inline formats**::

  *word*                (bold)
  /foo bar/             (italic)


**Line formats** (have to be on their own lines)::

  * * *                 (horizontal line, whitespace is optional)
  CHAPTER foo bar       (chapter title)
  [[ description ]]     (chapter description, has to follow a chapter
                         title/time/tags line)
  🕑 a day earlier       (chapter time/date, has to follow a chapter
                         title/description/tags line)
  #something, #tag2     (chapter tags, has to follow a chapter
                         title/description/time line)
  << something >>       (chapter section, more or less a subheading)
  %% stuff              (generic metadata line)


Chapters
--------
*TODO: more documentation here*

There is a chapter overview but at the moment a lot of it is hardcoded.
Prefix your chapter titles with CHAPTER to let Kalpana recognize them as
chapter titles. Then use the ``toggle-chapter-overview`` command to see the
chapter overview.


Configuration
-------------
The default settings are located in
``<path/to/repo>/kalpana/data/default_settings.yaml``. If no other config is
located, these settings will be used.

If you want to change the default settings, create a ``settings.yaml`` file
in Kalpana's config directory (by default in ``~/.config/kalpana2``) with the
settings that you want to override.

You can of course also change most settings during runtime with their
corresponding commands. These changes will be saved (by default) in
``~/.config/kalpana2/file_settings.yaml`` together with the file that was open
at the time. This means that those changes will only be loaded again when you
open that same file.

Rule of thumb: *file-specific settings* (changed through Kalpana's terminal)
overules *global settings* (changed in ``settings.yaml``) which overrules
*default settings* (provided by the Kalpana repo itself).


Stylesheet
~~~~~~~~~~
The default Qt stylesheet is located in ``<path/to/repo>/kalpana/data/qt.css``.
If you want to override something there, create ``qt.css`` in Kalpana's
config directory and override whatever you want.

As mentioned before, formatting can not be styled yet.


Key bindings
~~~~~~~~~~~~
Most keys are bindable, and can be bound to any command. Use the
``key-bindings`` setting in the global config (``settings.yaml``) to
customize them::

  key-bindings:
    f5: reload-stylesheet
    f7: insert-text ✓
    f9: toggle-chapter-overview
    ctrl+pgup: go-to-prev-chapter
    ctrl+pgdown: go-to-next-chapter
    ctrl+f: ' search-and-replace /'
    f3: search-next

If a command is preceded by a space (and surrounded by citation marks so that
yaml doesn't ignore the whitespace), the text will be inserted into the
terminal's input field instead of run. Otherwise pressing the key will be
identical to writing its corresponding command into the terminal and pressing
enter.

**Note that the terminal key (default: Escape) is instead configurable in the
setting ``terminal-key``, and not in the ``key-bindings`` setting like the other
settings.**

Traditional text editing keys (arrow keys, Ctrl+C/V, tab, etc) are not
configurable.
