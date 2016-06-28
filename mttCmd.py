# Python import
import os
# Qt import
from PySide.QtGui import QMessageBox
# Maya import
from maya import cmds
# custom import
from mttConfig import WINDOW_TITLE, MTTSettings, WS_KEY


def mtt_log(msg, add_tag=None, msg_type=None, verbose=True):
    """ Format output message '[TAG][add_tag] Message content'

    :param msg: (string) message content
    :param add_tag: (string or list) add extra tag to output
    :param msg_type: define message type. Accept : None, 'warning', 'error'
    :param verbose: (bool) enable headsUpMessage output
    """
    # define tags
    tag_str = '[MTT]'

    # append custom tags
    if add_tag:
        if not isinstance(add_tag, list):
            add_tag = [add_tag]

        for tag in add_tag:
            tag_str += '[%s]' % tag.upper()

    # output message the right way
    if msg_type == 'warning':
        cmds.warning('%s %s' % (tag_str, msg))
    elif msg_type == 'error':
        cmds.error('%s %s' % (tag_str, msg))
    else:
        print '%s %s\n' % (tag_str, msg),

    if verbose and MTTSettings.value('showHeadsUp'):
        cmds.headsUpMessage(msg)


def get_attr(node, attr, default_value=None):
    if cmds.attributeQuery(attr, node=node, exists=True):
        return cmds.getAttr('{}.{}'.format(node, attr))
    else:
        return default_value


def set_attr(node, attr, value, attr_type=None):
    attr_name = '{}.{}'.format(node, attr)
    state = cmds.getAttr(attr_name, lock=True)

    try:
        # set attr fail on referenced node
        cmds.setAttr(attr_name, lock=False)
        if attr_type:
            cmds.setAttr(attr_name, value, type=attr_type, lock=state)
        else:
            cmds.setAttr(attr_name, value, lock=state)
        return True

    except RuntimeError:
        mtt_log('setAttr command failed on {}'.format(attr_name), verbose=False)
        return False


def get_texture_source_folder(alt_path=None):
    """ Return texture source folder

    :param alt_path:
    """
    texture_source_folder = MTTSettings.TEXTURE_SOURCE_FOLDER
    if WS_KEY in MTTSettings.TEXTURE_SOURCE_FOLDER:
        ws = cmds.workspace(query=True, rootDirectory=True)
        texture_source_folder = MTTSettings.TEXTURE_SOURCE_FOLDER.replace(WS_KEY, ws)

    texture_source_folder = os.path.normpath(texture_source_folder)

    if not os.path.isdir(texture_source_folder):
        # if default folder not found, try in sourceimages folder
        if WS_KEY in MTTSettings.TEXTURE_SOURCE_FOLDER and alt_path:
            texture_source_folder = MTTSettings.TEXTURE_SOURCE_FOLDER.replace(WS_KEY, alt_path)
            texture_source_folder = os.path.normpath(texture_source_folder)
            if not os.path.isdir(texture_source_folder):
                # if another location doesn't exists, return workspace root
                texture_source_folder = cmds.workspace(q=1, rootDirectory=True)
                msg = (
                    'You should change "textureSourceFolder" folder '
                    'in mtt.json file')
                mtt_log(msg, msg_type='warning', verbose=False)

    return os.path.normpath(texture_source_folder)


def is_source_file_in_path(path, file_names, result):
    # exclude non existing folder
    if not os.path.isdir(path):
        return False

    # try each possibilities
    for file_name in file_names:
        file_path = os.path.join(path, file_name)
        if os.path.isfile(file_path):
            result.append(file_path)
            return True

    return False


def get_source_image_folder():
    # get current sourceimages path
    if 'sourceImages' in cmds.workspace(fileRuleList=True):
        return cmds.workspace(fileRuleEntry="sourceImages")
    else:
        return 'sourceimages'


def get_filename_variant(file_name, ext='psd'):
    """ Return a list of file name variant split by underscore

    FILE_NAME_DIF will give this variant :
    - FILE_NAME_DIF.ext
    - FILE_NAME.ext
    - FILE.ext
    """
    # split file with underscore
    tokens = file_name.split('_')
    # init values
    last_name = tokens[0]
    file_names = ['.'.join([last_name, ext])]
    # build variant sequence
    for token in tokens[1:]:
        last_name = '_'.join([last_name, token])
        _file_name = '.'.join([last_name, ext])
        file_names.append(_file_name)

    return list(reversed(file_names))


def get_source_file(file_path):
    """ Return source file of file_path

    Folder scanned for source file (in order):
    - file path folder
    - file path source folder using pattern
    - workspace sourceimage folder
    - workspace source folder using pattern

    :param file_path: (string) file path
    :return path to the source file
    """
    source_pattern = MTTSettings.TEXTURE_SOURCE_FOLDER
    ws = cmds.workspace(query=True, rootDirectory=True)

    path, full_file_name = os.path.split(file_path)
    file_name, file_ext = os.path.splitext(full_file_name)
    file_names = get_filename_variant(file_name)

    # using a mutable variable to get result
    result = []

    # scan PATTERN if absolute path
    if WS_KEY not in source_pattern:
        if is_source_file_in_path(source_pattern, file_names, result):
            return result[0]

    # scan FILE PATH FOLDER
    scan_path = os.path.normpath(path)
    if is_source_file_in_path(scan_path, file_names, result):
        return result[0]

    # scan FILE PATH SOURCE FOLDER USING PATTERN
    scan_path = os.path.normpath(
        os.path.join(path, source_pattern.replace(WS_KEY, '..')))
    if is_source_file_in_path(scan_path, file_names, result):
        return result[0]

    # scan WORKSPACE SOURCEIMAGE FOLDER
    scan_path = os.path.normpath(os.path.join(ws, get_source_image_folder()))
    if is_source_file_in_path(scan_path, file_names, result):
        return result[0]

    # scan WORKSPACE SOURCE FOLDER USING PATTERN
    scan_path = os.path.normpath(source_pattern.replace(WS_KEY, ws))
    if is_source_file_in_path(scan_path, file_names, result):
        return result[0]

    return None


def convert_to_relative_path(file_path):
    """ Convert current texture file path to a relative path

    :param file_path: (string) file path
    :return: relative path as a string
    """
    # get current sourceimages path
    cur_sourceimages_dir = get_source_image_folder()
    workspace_path = cmds.workspace(query=True, rootDirectory=True)
    sourceimages_path = os.path.join(workspace_path, cur_sourceimages_dir)

    # new path
    if cur_sourceimages_dir in file_path:
        splits = file_path.replace('\\', '/').rsplit(cur_sourceimages_dir, 1)
        file_path = os.path.join(sourceimages_path, splits[1][1:])

    # get relative path if file exists
    if os.path.isfile(file_path):
        relative_path = cmds.workspace(projectPath=file_path)
        return '/%s' % relative_path
    else:
        return file_path


def check_editor_preferences():
    # get preference values of external app path
    photo_dir = cmds.optionVar(exists='PhotoshopDir')
    image_dir = cmds.optionVar(exists='EditImageDir')

    # if there is no external app, request for an app path
    if not photo_dir and not image_dir:
        pref_warn = QMessageBox()
        pref_warn.setWindowTitle(WINDOW_TITLE)
        pref_warn.setIcon(QMessageBox.Warning)
        pref_warn.setText(
            '<b>Applications for Editing Image Files</b> '
            'is not set in your preferences.<br>'
            'Maya needs it to send image in the right Image Editor '
            'instead of file system association.')
        pref_warn.setInformativeText('Do you want to select an application ?')
        pref_warn.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        pref_warn.setDefaultButton(QMessageBox.Yes)
        pref_warn.setEscapeButton(QMessageBox.Cancel)
        ret = pref_warn.exec_()

        if ret == QMessageBox.Yes:
            app_path = cmds.fileDialog2(
                fileFilter='Image editor application (*.exe)',
                caption='Select image editor application',
                startingDirectory=os.path.expandvars('%ProgramFiles%'),
                fileMode=1)

            if app_path is not None:
                cmds.optionVar(sv=('PhotoshopDir', app_path[0]))
                cmds.optionVar(sv=('EditImageDir', app_path[0]))

