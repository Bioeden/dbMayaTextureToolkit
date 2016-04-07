# Python import
import json
import os
# PySide import
from PySide.QtCore import QSettings
# Maya import
from maya import cmds


WINDOW_DOCK_NAME = 'dbMayaTextureToolkitDock'
WINDOW_TITLE = 'Maya Texture Toolkit v{:.02f}'.format(
    cmds.optionVar(query='MTT_version'))
WINDOW_NAME = 'dbMayaTextureToolkitWin'
# TODO : create a custom icon
WINDOW_ICON = ':/dimTexture.png'
VIEWER_DOCK_NAME = 'dbMayaTextureToolkitViewerDock'
VIEWER_NAME = 'dbMayaTextureToolkitViewer'
VIEWER_TITLE = 'MTT Viewer'
CREATE_NODE_TITLE = 'MTT Create Node'
TAG = 'MTT'

COLUMN_COUNT = 6
NODE_NAME, NODE_TYPE, NODE_REFERENCE, FILE_STATE, FILE_COUNT, NODE_FILE = range(
    COLUMN_COUNT)
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

(PROMPT_INSTANCE_ASK, PROMPT_INSTANCE_WAIT, PROMPT_INSTANCE_SESSION,
    PROMPT_INSTANCE_ALWAYS) = range(4)
PROMPT_INSTANCE_WAIT_DURATION = 30
PROMPT_INSTANCE_STATE = {
    PROMPT_INSTANCE_ASK: 'Ask every time',
    PROMPT_INSTANCE_WAIT: 'Save choice for %ds' % PROMPT_INSTANCE_WAIT_DURATION,
    PROMPT_INSTANCE_SESSION: 'Save choice for this Maya session',
    PROMPT_INSTANCE_ALWAYS: 'Save choice permanently'
}

TOOLBAR_BUTTON_SIZE = 20
TOOLBAR_BUTTON_ICON_SIZE = 16

DEFAULT_VALUES = {
    'vizWrongNameState': False,
    'vizWrongPathState': False,
    'showWrongNameState': False,
    'showBasenameState': False,
    'showRealAttributeValue': False,
    'showReferenceState': False,
    'showHeadsUp': True,
    'showNamespaceState': True,
    'filterInstances': False,
    'forceRelativePath': False,
    'browserFirstStart': False,
    'autoSelect': False,
    'autoReload': False,
    'autoRename': False,
    'onlyWritableState': False,
    'onlySelectionState': False,
    'viewerState': False,
    'Viewer/isFloating': False,
    'Viewer/autoFit': True,
    'Viewer/autoReset': False,
    'Viewer/autoLock': False,
    'Viewer/premultiply': False,
    'Viewer/recoverMode': False,
    'switchEdit': False,
    'filterFocus': False,
    'filterRE': False,
    'filterType': 0,
    'powerUser': False,
    'suspendCallbacks': False,
    'suspendRenameCallbacks': False,
    'defaultQuickFilterWords': True,
    'FilterFileDialog/bookmarks': '',
    'filterQuickWordsWildcard': '',
    'filterQuickWordsRegExp': '',
    'filterGroup': True,
    'visibilityGroup': True,
    'folderGroup': True,
    'autoGroup': True,
    'toolGroup': True,
    'mayaGroup': True,
}
BOOL_VALUES_KEYS = (
    'vizWrongNameState', 'vizWrongPathState',
    'showWrongNameState', 'showBasenameState',
    'showRealAttributeValue', 'showReferenceState', 'showHeadsUp',
    'showNamespaceState', 'filterInstances', 'forceRelativePath',
    'browserFirstStart',
    'autoSelect', 'autoReload', 'autoRename',
    'onlyWritableState', 'onlySelectionState', 'viewerState',
    'Viewer/isFloating', 'Viewer/autoFit', 'Viewer/autoReset',
    'Viewer/autoLock', 'Viewer/premultiply', 'Viewer/recoverMode',
    'switchEdit', 'filterFocus', 'filterRE',
    'powerUser',
    'suspendCallbacks', 'suspendRenameCallbacks',
    'defaultQuickFilterWords',
    'filterGroup', 'visibilityGroup', 'folderGroup', 'autoGroup', 'toolGroup',
    'mayaGroup',
    'columnVisibility_0', 'columnVisibility_1', 'columnVisibility_2',
    'columnVisibility_3', 'columnVisibility_4', 'columnVisibility_5',
)
INT_VALUES_KEYS = (
    'filterType',
)

# theme found at http://www.colourlovers.com/ exclude Flashy Theme
THEMES = {
    'Maya Theme': (None, None, None, None, None),
    'Flashy': ('#FF4F1E', '#F67C31', '#F7A128', '#F7DC2B', '#D1CE05'),
    'Dusty Velvet': ('#554D7D', '#9078A8', '#C0C0F0', '#9090C0', '#606090'),
    'Dark Spring Parakeet': ['#171717', '#292929', '#093E47', '#194D0A', '#615400'],
    'Yellow Tree Frog': ('#E73F3F', '#F76C27', '#E7E737', '#6D9DD1', '#7E45D3'),
    'Mod Mod Mod Mod': ('#949494', '#3A3A3A', '#3E5C5F', '#125358', '#002D31'),
    'Blue Jay Feather': ('#1F1F20', '#2B4C7E', '#567EBB', '#606D80', '#DCE0E6'),
    'Wonderous': ('#BE2525', '#BE5025', '#BE6825', '#BE8725', '#BEA025'),
    'Rococo Girl': ('#CCB24C', '#F7D683', '#FFFDC0', '#FFFFFD', '#457D97'),
    '6 Inch Heels': ('#1A2B2B', '#332222', '#4D1A1A', '#661111', '#800909'),
    '2 Kool For Skool': ('#020304', '#541F14', '#938172', '#CC9E61', '#626266'),
    'Retro Bath': ('#D8D6AF', '#C3B787', '#AB925C', '#DA902D', '#983727')
}

DEFAULT_JSON_CONTENT = '''{
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
  "import_policy":"from dbMayaTextureToolkit.mttImportPolicy import exec_import_policy",
  "path_pattern":"E:\\CG_Projects\\Demo_MTT",
  "VCS": {
    "checkout": "from dbMayaTextureToolkit.mttSourceControlTemplate import checkout",
    "submit": "from dbMayaTextureToolkit.mttSourceControlTemplate import submit",
    "revert": "from dbMayaTextureToolkit.mttSourceControlTemplate import revert"
  }
}'''


class MTTSettings(object):

    _SETTINGS = None
    SUPPORTED_TYPE = []
    UNSUPPORTED_TYPE = []
    TEXTURE_SOURCE_FOLDER = ''
    CUSTOM_BUTTONS = []
    IMPORT_POLICY = ''
    PATH_PATTERN = '.*'
    VCS = {}

    def __init__(self):
        # init settings only once
        if not MTTSettings._SETTINGS:
            MTTSettings._SETTINGS = QSettings(
                QSettings.IniFormat, QSettings.UserScope,
                'Bioeden', 'mtt')

            MTTSettings.__load_json_settings()

    @classmethod
    def __load_json_settings(cls):
        """ Read JSON file and create corresponding list

        @return: supported_type, unsupported_type, texture_source_folder and
                 custom_buttons
        """
        # json file
        json_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'mtt.json')

        # create file with default value if doesn't exists
        if not os.path.isfile(json_file_path):
            with open(json_file_path, 'w') as f:
                f.write(DEFAULT_JSON_CONTENT)

        # now read json file
        with open(json_file_path, 'r') as json_file:
            json_settings = json.load(json_file)

        # get supported node types
        maya_type = set(cmds.allNodeTypes())
        for entry in json_settings.get('supported_nodes', []):
            entry_type = entry.get('node_type', '')
            if entry_type not in maya_type:
                cmds.warning('Unsupported node type %s' % entry_type)
                MTTSettings.UNSUPPORTED_TYPE.append(entry_type)
            else:
                MTTSettings.SUPPORTED_TYPE.append((
                    entry_type,
                    entry.get('node_nicename', entry_type),
                    entry.get('node_attr', 'fileTextureName')))

        # get workspace extend
        ws_extend = json_settings.get('workspace_extend', {})
        # get texture source folder
        MTTSettings.TEXTURE_SOURCE_FOLDER = ws_extend.get(
            'texture_source_folder', '<WORKSPACE>/PSD/')

        # get custom buttons
        for customButtonData in json_settings.get('custom_buttons', []):
            MTTSettings.CUSTOM_BUTTONS.append((
                customButtonData.get('icon', ':/menuIconImages.png'),
                customButtonData.get('tooltip', ''),
                customButtonData.get('cmd', '')
            ))

        # get import policy
        MTTSettings.IMPORT_POLICY = json_settings.get('import_policy', '')

        # get path pattern
        if 'path_pattern' in json_settings:
            # convert string to raw string
            MTTSettings.PATH_PATTERN = ('%r' % json_settings['path_pattern'])[2:-1]

        # get VCS commands
        if 'VCS' in json_settings:
            MTTSettings.VCS = json_settings['VCS']

    @classmethod
    def _get_as_bool(cls, value):
        return value == 'true' if isinstance(value, unicode) else value

    @classmethod
    def _get_as_int(cls, value):
        return int(value) if isinstance(value, unicode) else value

    @classmethod
    def value(cls, key, default_value=None):
        default_value = DEFAULT_VALUES.get(key, default_value)
        value = cls._SETTINGS.value(key, default_value)

        if key in BOOL_VALUES_KEYS:
            return cls._get_as_bool(value)
        elif key in INT_VALUES_KEYS:
            return cls._get_as_int(value)
        else:
            return value

    @classmethod
    def set_value(cls, key, value):
        cls._SETTINGS.setValue(key, value)

    @classmethod
    def remove(cls, key):
        cls._SETTINGS.remove(key)

    @classmethod
    def filename(cls):
        return cls._SETTINGS.fileName()
