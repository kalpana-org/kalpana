try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import SIGNAL, Qt, QDir, QEvent
    from PySide.QtGui import QMessageBox
except ImportError:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtCore import SIGNAL, Qt, QDir, QEvent
    from PyQt4.QtGui import QMessageBox
