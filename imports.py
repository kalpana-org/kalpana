try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import SIGNAL, Qt, QDir, QEvent
except ImportError:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtCore import SIGNAL, Qt, QDir, QEvent
