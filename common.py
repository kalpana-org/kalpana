try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import SIGNAL, Qt, QDir, QEvent
except ImportError:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtCore import SIGNAL, Qt, QDir, QEvent


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.loads(f.read())

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
