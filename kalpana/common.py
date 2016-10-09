"""
Classes and functions needed in multiple different modules.

This is to avoid potential circular imports.
"""

from PyQt5.QtCore import pyqtSignal


class Loggable:
    """An interface to send messages display in the terminal."""

    error_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def error(self, text: str) -> None:
        """Show an error."""
        self.error_signal.emit(text)

    def log(self, text: str) -> None:
        """Print a text."""
        self.log_signal.emit(text)
