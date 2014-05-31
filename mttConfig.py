# Maya import
import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import maya.cmds as cmds

# Qt import
from PySide.QtGui import QMainWindow
from PySide.QtCore import QSettings
from shiboken import wrapInstance

# Python import
import os
import json


# -------------------------------------------------------------------------------------------------------------------- #
# Statics variables
# -------------------------------------------------------------------------------------------------------------------- #
WINDOW_DOCK_NAME = 'dbMayaTextureToolkitDock'
WINDOW_NAME = 'dbMayaTextureToolkitWin'
WINDOW_TITLE = 'db Maya Texture Toolkit %s' % cmds.optionVar(query='MTT_version')
VIEWER_DOCK_NAME = 'dbMayaTextureToolkitViewerDock'
VIEWER_NAME = 'dbMayaTextureToolkitViewer'
VIEWER_TITLE = 'MTT Viewer'
CREATE_NODE_TITLE = 'MTT Create Node'
TAG = 'MTT'

COLUMN_COUNT = 6
NODE_NAME, NODE_TYPE, NODE_REFERENCE, FILE_STATE, FILE_COUNT, NODE_FILE = range(COLUMN_COUNT)
VIEW_COLUMN_LABEL = {
    NODE_NAME: 'Node Name',
    NODE_TYPE: 'Type',
    NODE_REFERENCE: 'R',
    FILE_STATE: 'W',
    FILE_COUNT: '#',
    NODE_FILE: 'File'
}
VIEW_COLUMN_CONTEXT = {
    NODE_NAME: 'Node Name',
    NODE_TYPE: 'Type',
    NODE_REFERENCE: 'Reference',
    FILE_STATE: 'Writable',
    FILE_COUNT: '# Instance Count',
    NODE_FILE: 'File'
}
VIEW_COLUMN_SIZE = {
    NODE_NAME: 150,
    NODE_TYPE: 35,
    NODE_REFERENCE: 20,
    FILE_STATE: 20,
    FILE_COUNT: 20,
    NODE_FILE: 200
}
DB_COLUMN_LABEL = {
    NODE_NAME: 'Name',
    NODE_TYPE: 'Type',
    NODE_REFERENCE: 'IsRef',
    FILE_STATE: 'State',
    FILE_COUNT: 'InstanceCount',
    NODE_FILE: 'Attribute'
}

PROMPT_INSTANCE_ASK, PROMPT_INSTANCE_WAIT, PROMPT_INSTANCE_SESSION, PROMPT_INSTANCE_ALWAYS = range(4)
PROMPT_INSTANCE_WAIT_DURATION = 30
PROMPT_INSTANCE_STATE = {
    PROMPT_INSTANCE_ASK: 'Ask every time',
    PROMPT_INSTANCE_WAIT: 'Save choice for %ds' % PROMPT_INSTANCE_WAIT_DURATION,
    PROMPT_INSTANCE_SESSION: 'Save choice for this Maya session',
    PROMPT_INSTANCE_ALWAYS: 'Save choice permanently'
}

TOOLBAR_BUTTON_SIZE = 20
TOOLBAR_BUTTON_ICON_SIZE = 16

DEFAULT_VIZ_WRONG_NAME = False
DEFAULT_SHOW_WRONG_NAME = False
DEFAULT_SHOW_BASENAME = False
DEFAULT_SHOW_REAL_ATTRIBUTE = False
DEFAULT_SHOW_REFERENCE = False
DEFAULT_SHOW_HEADSUP = True
DEFAULT_SHOW_NAMESPACE = True
DEFAULT_FILTER_INSTANCES = False
DEFAULT_FORCE_RELATIVE_PATH = True
DEFAULT_BROWSER_FIRST_START = False
DEFAULT_AUTO_SELECT = False
DEFAULT_AUTO_RELOAD = False
DEFAULT_AUTO_RENAME = False
DEFAULT_ONLY_WRITABLE = False
DEFAULT_ONLY_SELECTION = False
DEFAULT_VIEWER = False
DEFAULT_VIEWER_IS_FLOATING = False
DEFAULT_VIEWER_AUTO_FIT = True
DEFAULT_VIEWER_AUTO_RESET = False
DEFAULT_VIEWER_AUTO_LOCK = False
DEFAULT_VIEWER_PREMULTIPLY = False
DEFAULT_VIEWER_RECOVERY = False
DEFAULT_SWITCH_EDIT = False
DEFAULT_FILTER_FOCUS = False
DEFAULT_FILTER_RE = False
DEFAULT_POWER_USER = False
DEFAULT_SUSPEND_CALLBACK = False


# -------------------------------------------------------------------------------------------------------------------- #
# Define utilities
# -------------------------------------------------------------------------------------------------------------------- #
def db_output(msg, add_tag=None, msg_type=None):
    """ Format output message '[TAG][add_tag] Message content'

    @param msg: message content
    @param add_tag: add extra tag to output
    @param msg_type: define message type. Accept : None, 'warning', 'error'
    """
    tag_str = '[%s]' % TAG

    if add_tag:
        if not isinstance(add_tag, list):
            add_tag = [add_tag]
        for tag in add_tag:
            tag_str += '[%s]' % tag.upper()

    if msg_type == 'warning':
        om.MGlobal.displayWarning('%s %s' % (tag_str, msg))
    elif msg_type == 'error':
        om.MGlobal.displayError('%s %s' % (tag_str, msg))
    else:
        # om.MGlobal.displayInfo('%s %s' % (tag_str, msg))
        print '%s %s\n' % (tag_str, msg),


def get_settings_bool_value(current_value):
    """ Return boolean type from QSettings value

    PySide QSettings return a unicode when value is query from a .ini file

    @return: current_value as boolean
    """
    if isinstance(current_value, unicode):
        return current_value == 'true'
    else:
        return current_value


def get_settings_int_value(current_value):
    """ Return integer type from QSettings value

    PySide QSettings return a unicode when value is query from a .ini file

    @return: current_value as integer
    """
    if isinstance(current_value, unicode):
        return int(current_value)
    else:
        return current_value


def convert_to_relative_path(file_path):
    """ Convert current texture file path to a relative path

    @return: relative path as a string
    """
    # get current sourceimages path
    if 'sourceImages' in cmds.workspace(fileRuleList=True):
        current_sourceimage_folder = cmds.workspace(fileRuleEntry="sourceImages")
    else:
        current_sourceimage_folder = 'sourceimages'
    workspace_path = cmds.workspace(query=True, rootDirectory=True)
    sourceimage_path = os.path.join(workspace_path, current_sourceimage_folder)

    # new path
    if current_sourceimage_folder in file_path:
        splits = file_path.replace('\\', '/').rsplit(current_sourceimage_folder, 1)
        file_path = os.path.join(sourceimage_path, splits[1][1:])

    # get relative path if file exists
    if os.path.isfile(file_path):
        relative_path = cmds.workspace(projectPath=file_path)
        return '/%s' % relative_path
    else:
        return file_path


def __get_maya_window():
    """ Get the maya main window as a QMainWindow instance

    @return: Maya main window address
    """
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(ptr), QMainWindow)


def __get_settings():
    """ Create QSettings object

    @return: QSettings object
    """
    return QSettings(QSettings.IniFormat, QSettings.UserScope, 'Bioeden', 'mtt')


def __get_JSON_settings():
    """ Read JSON file and create corresponding list

    @return: supported_type, unsupported_type, texture_source_folder, custom_buttons
    """
    # json file
    json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mtt.json')

    # create file with default value if doesn't exists
    if not os.path.isfile(json_file_path):
        default_file_content = '''{
    "supported_nodes":[
        {
            "node_type":"file",
            "node_nicename":"FILE",
            "node_attr":"fileTextureName"
        },
        {
            "node_type":"psdFileTex",
            "node_nicename":"PSD",
            "node_attr":"fileTextureName"
        },
        {
            "node_type":"mentalrayTexture",
            "node_nicename":"MRT",
            "node_attr":"fileTextureName"
        }
    ],
    "workspace_extend":{
        "texture_source_folder":"<WORKSPACE>/PSD/"
    },
    "custom_buttons":[
    ],
    "import_policy":"from dbMayaTextureToolkit.mttImportPolicy import exec_import_policy"
}'''
        f = open(json_file_path, 'w')
        f.write(default_file_content)
        f.close()

    # now read json file
    supported_type = list()
    unsupported_type = list()
    texture_source_folder = ''
    custom_buttons = list()
    import_policy = ''

    try:
        json_file = open(json_file_path, 'r')
        json_settings = json.load(json_file)
        json_file.close()

        maya_type = cmds.allNodeTypes()
        for entry in json_settings['supported_nodes']:
            if entry['node_type'] not in maya_type:
                db_output('Unsupported node type %s' % entry['node_type'], msg_type='warning')
                unsupported_type.append(entry['node_type'])
            else:
                supported_type.append((entry['node_type'], entry['node_nicename'], entry['node_attr']))

        texture_source_folder = json_settings['workspace_extend']['texture_source_folder']

        for customButtonData in json_settings['custom_buttons']:
            custom_buttons.append((customButtonData['icon'], customButtonData['tooltip'], customButtonData['cmd']))

        import_policy = json_settings['import_policy']

    except ValueError, e:
        db_output('Error when loading JSON file :\n%s' % e)

    return supported_type, unsupported_type, texture_source_folder, custom_buttons, import_policy


MAYA_MAIN_WINDOW = __get_maya_window()
SETTINGS = __get_settings()
SUPPORTED_TYPE, UNSUPPORTED_TYPE, TEXTURE_SOURCE_FOLDER, CUSTOM_BUTTONS, IMPORT_POLICY = __get_JSON_settings()