"""Qt import shim.

FreeCAD 1.x ships PySide6. Older builds and some distro packages expose the
same classes through FreeCAD's own ``PySide`` alias module.
"""

try:
    from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets  # noqa: F401
    QT_API = "PySide6"
except ImportError:  # pragma: no cover - fallback for older FreeCAD
    from PySide import QtCore, QtGui, QtNetwork, QtWidgets  # noqa: F401
    QT_API = "PySide"

Signal = QtCore.Signal
Qt = QtCore.Qt
