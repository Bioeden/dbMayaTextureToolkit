# Qt import
from PySide.QtGui import QMessageBox

# custom import
from mttConfig import *
import mttView


def __check_editor_preferences():
    if not cmds.optionVar(exists='PhotoshopDir') and not cmds.optionVar(exists='EditImageDir'):
        pref_warning = QMessageBox()
        pref_warning.setWindowTitle(WINDOW_TITLE)
        pref_warning.setIcon(QMessageBox.Warning)
        pref_warning.setText(
            '<b>Applications for Editing Image Files</b> is not set in your preferences.<br>'
            'Maya need it to send image in the right Image Editor instead of file system association.')
        pref_warning.setInformativeText('Do you want to select an application ?')
        pref_warning.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        pref_warning.setDefaultButton(QMessageBox.Yes)
        pref_warning.setEscapeButton(QMessageBox.Cancel)
        ret = pref_warning.exec_()

        if ret == QMessageBox.Yes:
            app_path = cmds.fileDialog2(
                fileFilter='Image editor application (*.exe)',
                caption='Select image editor application',
                startingDirectory=os.path.expandvars('%ProgramFiles%'),
                fileMode=1)

            if app_path is not None:
                cmds.optionVar(sv=('PhotoshopDir', app_path[0]))
                cmds.optionVar(sv=('EditImageDir', app_path[0]))


def show_ui(toggle=True):
    """ INIT TOOL AND SHOW UI

    @param toggle: destroy and recreate window when is set to False
    """
    # delete UI if exists
    if cmds.control(WINDOW_NAME, exists=True):
        #winFullName = cmds.control(WINDOW_NAME, query=True, fullPathName=True)
        #mttWinPtr = omui.MQtUtil.findControl(winFullName)
        #mttWin = wrapInstance(long(mttWinPtr), QObject)
        #mttWin.close()
        cmds.deleteUI(WINDOW_NAME, window=True)

        if toggle:
            return

    __check_editor_preferences()

    dialog = mttView.MTTView(parent=MAYA_MAIN_WINDOW, settings=SETTINGS)
    dialog.show()