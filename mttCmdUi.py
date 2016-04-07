# PySide import
from shiboken import wrapInstance
from PySide.QtGui import QMainWindow
# Maya import
from maya import OpenMayaUI
# Custom import
from mttCustomWidget import StatusToolbarButton


def get_maya_window():
    """ Get the maya main window as a QMainWindow instance

    :return: Maya main window address
    """
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(long(ptr), QMainWindow)


def create_status_button(ico, txt, cmd, is_checkable):
        btn = StatusToolbarButton(ico)
        btn.setToolTip(txt)
        btn.setStatusTip(txt)
        if cmd:
            btn.clicked.connect(cmd)
        btn.setCheckable(is_checkable)
        return btn
