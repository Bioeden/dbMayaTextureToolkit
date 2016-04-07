# Qt import
from PySide.QtGui import QApplication, QCursor
from PySide.QtCore import Qt


def wait_cursor(func):
    def wrapper(*args, **kwargs):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        exception = None

        try:
            rtn = func(*args, **kwargs)
        except Exception as e:
            exception = e
            rtn = None
        finally:
            QApplication.restoreOverrideCursor()

        if exception:
            raise exception

        return rtn
    return wrapper
