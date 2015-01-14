# Maya import
import maya.OpenMaya as om
import maya.mel as mel
import maya.cmds as cmds
import __main__

# Qt import
from PySide.QtGui import *
from PySide.QtCore import *

# Python import
from functools import partial
from time import time
import stat
import webbrowser

# custom import
import mttResources
from mttConfig import *
from mttQuickFilterManager import MTTQuickFilterManager
from mttCustomWidget import RightPushButton, StatusToolbarButton, StatusCollapsibleLayout, MessageBoxWithCheckbox
import mttModel
import mttDelegate
import mttProxy
import mttViewer
import mttFilterFileDialog
import mttOverridePanels


def waitingcursor(func):
    def wrapper(self, *args, **kwargs):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        if args and kwargs:
            func(self, *args, **kwargs)
        elif kwargs:
            func(self, *kwargs)
        else:
            func(self)
        QApplication.restoreOverrideCursor()
    return wrapper


class MTTDockFrame(QFrame):
    """ Workaround to restore DockWidget size """
    def __init__(self, parent=None, w=256, h=256):
        super(MTTDockFrame, self).__init__(parent)
        self.custom_width = w
        self.custom_height = h

    def sizeHint(self, *args, **kwargs):
        return QSize(self.custom_width, self.custom_height)


class MTTDockWidget(QDockWidget):
    def __init__(self, settings, *args, **kwargs):
        super(MTTDockWidget, self).__init__(*args, **kwargs)

        self.settings = settings

    def closeEvent(self, *args, **kwargs):
        self.settings.setValue('viewerState', False)
        self.settings.setValue('Viewer/windowGeometry', self.saveGeometry())
        super(MTTDockWidget, self).closeEvent(*args, **kwargs)


#---------------------------------------------------------------------------------------------------------------------
# MAIN WINDOW
#---------------------------------------------------------------------------------------------------------------------
#noinspection PyUnresolvedReferences
class MTTView(QMainWindow):
    """ Maya Texture Manager Main UI """

    def __init__(self, parent=None, settings=SETTINGS):
        super(MTTView, self).__init__(parent)

        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle(WINDOW_TITLE)

        # Callbacks variables
        self.is_callbacks_created = False
        self.is_batching_change_attr = False
        self.scene_callbacks_ids = list()
        self.selection_callback_id = 0
        self.new_callback_id = 0
        self.open_callback_id = 0
        self.rename_node_callback_id = 0
        self.add_node_callback_id = 0
        self.remove_node_callback_id = 0
        self.attribute_callback_id = dict()

        # UI variables
        self.is_master_cmd = False
        self.viewer_dock = None
        self.image_editor_name = self.__get_image_editor_name
        self.header_menu = None
        self.filter_grp = None
        self.selection_btn = None
        self.writable_btn = None
        self.reference_btn = None
        self.pin_btn = None
        self.wrong_name_btn = None
        self.viewer_btn = None
        self.visibility_grp = None
        self.wrong_name_visibility_btn = None
        self.wrong_path_visibility_btn = None
        self.basename_visibility_btn = None
        self.namespace_visibility_btn = None
        self.filter_instances_btn = None
        self.folder_grp = None
        self.auto_grp = None
        self.tool_grp = None
        self.maya_grp = None
        self.custom_grp = None
        self.info_btn = None
        self.filter_reset_btn = None
        self.filter_line_edit = None
        self.filter_re_btn = None
        self.filter_combo = None
        self.table_view = None
        self.table_view_selection_model = None
        self.quick_action_layout = None
        self.quick_reload_btn = None
        self.quick_edit_btn = None
        self.instance_menu = None
        self.debug_menu = None
        self.support_info = None
        self.stat_info = None
        # theme found at http://www.colourlovers.com/ exclude Flashy Theme
        self.theme_data = {
            'Maya Theme': [None, None, None, None, None],
            'Flashy': ['#FF4F1E', '#F67C31', '#F7A128', '#F7DC2B', '#D1CE05'],
            'Dusty Velvet': ['#554D7D', '#9078A8', '#C0C0F0', '#9090C0', '#606090'],
            'Dark Spring Parakeet': ['#171717', '#292929', '#093E47', '#194D0A', '#615400'],
            'Yellow Tree Frog': ['#E73F3F', '#F76C27', '#E7E737', '#6D9DD1', '#7E45D3'],
            'Mod Mod Mod Mod': ['#949494', '#3A3A3A', '#3E5C5F', '#125358', '#002D31'],
            'Blue Jay Feather': ['#1F1F20', '#2B4C7E', '#567EBB', '#606D80', '#DCE0E6'],
            'Wonderous': ['#BE2525', '#BE5025', '#BE6825', '#BE8725', '#BEA025'],
            'Rococo Girl': ['#CCB24C', '#F7D683', '#FFFDC0', '#FFFFFD', '#457D97'],
            '6 Inch Heels': ['#1A2B2B', '#332222', '#4D1A1A', '#661111', '#800909'],
            '2 Kool For Skool': ['#020304', '#541F14', '#938172', '#CC9E61', '#626266'],
            'Retro Bath': ['#D8D6AF', '#C3B787', '#AB925C', '#DA902D', '#983727']
        }
        self.dock_side_data = dict()
        self.dock_side_data['Left'] = Qt.LeftDockWidgetArea
        self.dock_side_data['Top'] = Qt.TopDockWidgetArea
        self.dock_side_data['Right'] = Qt.RightDockWidgetArea
        self.dock_side_data['Bottom'] = Qt.BottomDockWidgetArea

        # Tools
        self.settings = settings
        self.settings.remove('suspendCallbacks')  # clean old pref
        cmds.optionVar(intValue=('suspendCallbacks', DEFAULT_SUSPEND_CALLBACK))
        cmds.optionVar(stringValue=('filtered_instances', ''))
        self.filewatcher = QFileSystemWatcher()
        self.model = mttModel.MTTModel(settings=settings, watcher=self.filewatcher)
        self.delegate = mttDelegate.MTTDelegate(settings=settings)
        self.proxy = mttProxy.MTTProxy(settings=settings)
        self.completion_model = QStringListModel(self.get_filter_completion_words(), self)
        self.quick_filter_words_init = get_settings_bool_value(self.settings.value('defaultQuickFilterWords', True))
        self.quick_filter_words = self.get_filter_quick_words()
        self.power_user = get_settings_bool_value(self.settings.value('powerUser', DEFAULT_POWER_USER))
        self.viewer_view = None

        self.supported_format_dict = dict([(nodeType, nodeAttrName) for nodeType, nice, nodeAttrName in SUPPORTED_TYPE])

        # create UI
        self.__create_ui()

        # restore geometry
        window_geo = self.settings.value('windowGeometry')
        if window_geo:
            self.restoreGeometry(window_geo)
        self.centralWidget().setGeometry(self.settings.value('centralGeometry', QRect(0, 0, 400, 200)))

        # manage focus to avoid hotkey capture when tool is called with shortcut key
        if get_settings_bool_value(self.settings.value('filterFocus', DEFAULT_FILTER_FOCUS)):
            self.filter_line_edit.setFocus()
        else:
            self.setFocus()

        # create callbacks
        self.__create_callbacks()

        # update node/file count
        self.__update_node_file_count_ui()

        # apply theme
        self.on_choose_theme(self.settings.value('theme', 'Default'))

    #-------------------------------------------------------------------------------------------------------------------
    # UI CREATION
    def __create_ui(self):
        """ Create main UI """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(1)
        main_layout.setContentsMargins(2, 2, 2, 2)

        main_layout.addLayout(self.__create_toolbar_ui())
        main_layout.addLayout(self.__create_filter_ui())
        main_layout.addWidget(self.__create_table_ui())
        main_layout.addLayout(self.__create_action_ui())

        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        if get_settings_bool_value(self.settings.value('viewerState', DEFAULT_VIEWER)):
            self.on_toolbar_viewer()

    @staticmethod
    def __create_toolbar_button(btn_icon, btn_text, btn_cmd, btn_checkable):
            new_button = StatusToolbarButton(btn_icon)
            new_button.setToolTip(btn_text)
            new_button.setStatusTip(btn_text)
            new_button.clicked.connect(btn_cmd)
            new_button.setCheckable(btn_checkable)
            return new_button

    def __create_toolbar_ui(self):
        """ Create custom toolbar with collapse Maya Status Line behavior """

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setAlignment(Qt.AlignLeft)

        # FILTER GROUP
        self.filter_grp = StatusCollapsibleLayout(section_name='Show/Hide the filter icons')

        self.selection_btn = self.__create_toolbar_button(
            ':/tb_onlySelection',
            'Show textures applied to current selection',
            self.on_toolbar_show_only_selection,
            True)
        self.writable_btn = self.__create_toolbar_button(
            ':/tb_onlyWritable',
            'Hide read-only textures',
            self.on_toolbar_show_only_writable,
            True)
        self.reference_btn = self.__create_toolbar_button(
            ':/tb_onlyReference',
            'Hide references',
            self.on_toolbar_show_reference,
            True)
        self.pin_btn = self.__create_toolbar_button(
            ':/tb_onlyPinned',
            'Pin textures',
            self.on_toolbar_pin_nodes,
            True)
        self.wrong_name_btn = self.__create_toolbar_button(
            ':/tb_onlyWrongName',
            'Show Node name clashing with Texture name',
            self.on_toolbar_show_wrong_name,
            True)
        self.filter_instances_btn = self.__create_toolbar_button(
            ':/tb_hideInstances',
            'Show only one instance per file',
            self.on_toolbar_filter_instances,
            True)

        self.selection_btn.setChecked(get_settings_bool_value(self.settings.value('onlySelectionState', DEFAULT_ONLY_SELECTION)))
        self.writable_btn.setChecked(get_settings_bool_value(self.settings.value('onlyWritableState', DEFAULT_ONLY_WRITABLE)))
        self.reference_btn.setChecked(get_settings_bool_value(self.settings.value('showReferenceState', DEFAULT_SHOW_REFERENCE)))
        self.wrong_name_btn.setChecked(get_settings_bool_value(self.settings.value('showWrongNameState', DEFAULT_SHOW_WRONG_NAME)))
        self.filter_instances_btn.setChecked(get_settings_bool_value(self.settings.value('filterInstances', DEFAULT_FILTER_INSTANCES)))

        # sort toolbar buttons
        self.filter_grp.add_button(self.pin_btn)
        self.filter_grp.add_button(self.selection_btn)
        self.filter_grp.add_button(self.reference_btn)
        self.filter_grp.add_button(self.writable_btn)
        self.filter_grp.add_button(self.wrong_name_btn)
        self.filter_grp.add_button(self.filter_instances_btn)

        self.filter_grp.set_current_state(self.settings.value('filterGroup', 1))
        toolbar_layout.addWidget(self.filter_grp)

        # VISIBILITY GROUP
        self.visibility_grp = StatusCollapsibleLayout(section_name='Show/Hide the visibility icons')

        self.wrong_name_visibility_btn = self.__create_toolbar_button(
            ':/tb_vizWrongName',
            'Highlight Node name clashing with Texture name',
            self.on_toolbar_wrong_name_visibility,
            True)

        self.wrong_path_visibility_btn = self.__create_toolbar_button(
            ':/tb_vizWrongPath',
            'Highlight Texture path clashing with user defined path pattern',
            self.on_toolbar_wrong_path_visibility,
            True)

        self.basename_visibility_btn = self.__create_toolbar_button(
            ':/tb_vizBasename',
            'Show files texture name only',
            self.on_toolbar_basename_visibility,
            True)

        self.namespace_visibility_btn = self.__create_toolbar_button(
            ':/tb_vizNamespace',
            'Toggle namespace visibility',
            self.on_toolbar_namespace_visibility,
            True)

        self.wrong_name_visibility_btn.setChecked(get_settings_bool_value(self.settings.value('vizWrongNameState', DEFAULT_VIZ_WRONG_NAME)))
        self.wrong_path_visibility_btn.setChecked(get_settings_bool_value(self.settings.value('vizWrongPathState', DEFAULT_VIZ_WRONG_NAME)))
        self.basename_visibility_btn.setChecked(get_settings_bool_value(self.settings.value('showBasenameState', DEFAULT_SHOW_BASENAME)))
        self.namespace_visibility_btn.setChecked(not get_settings_bool_value(self.settings.value('showNamespaceState', DEFAULT_SHOW_NAMESPACE)))

        self.visibility_grp.add_button(self.namespace_visibility_btn)
        self.visibility_grp.add_button(self.wrong_name_visibility_btn)
        self.visibility_grp.add_button(self.wrong_path_visibility_btn)
        self.visibility_grp.add_button(self.basename_visibility_btn)

        self.visibility_grp.set_current_state(self.settings.value('visibilityGroup', 1))
        toolbar_layout.addWidget(self.visibility_grp)

        # FOLDER GROUP
        self.folder_grp = StatusCollapsibleLayout(section_name='Show/Hide the folder icons')

        self.folder_grp.add_button(self.__create_toolbar_button(
            ':/tb_folderMap',
            'Open sourceimages folder',
            self.on_toolbar_open_sourceimages_folder,
            False)
        )
        self.folder_grp.add_button(self.__create_toolbar_button(
            ':/tb_folderSrc',
            'Open source folder',
            self.on_toolbar_open_source_folder,
            False)
        )

        self.folder_grp.set_current_state(self.settings.value('folderGroup', 1))
        toolbar_layout.addWidget(self.folder_grp)

        # AUTO GROUP
        self.auto_grp = StatusCollapsibleLayout(section_name='Show/Hide the auto actions icons')

        auto_reload_btn = self.__create_toolbar_button(
            ':/tb_toolbar_autoReload',
            'Auto Reload Textures',
            self.on_auto_reload,
            True)

        auto_select_btn = self.__create_toolbar_button(
            ':/tb_toolbar_autoSelect',
            'Auto Select Textures Node',
            self.on_auto_select,
            True)

        auto_rename_btn = self.__create_toolbar_button(
            ':/tb_toolbar_autoRename',
            'Auto Rename Textures Node',
            self.on_auto_rename,
            True)

        auto_reload_btn.setChecked(get_settings_bool_value(self.settings.value('autoReload', DEFAULT_AUTO_RELOAD)))
        auto_select_btn.setChecked(get_settings_bool_value(self.settings.value('autoSelect', DEFAULT_AUTO_SELECT)))
        auto_rename_btn.setChecked(get_settings_bool_value(self.settings.value('autoRename', DEFAULT_AUTO_RENAME)))

        self.auto_grp.add_button(auto_reload_btn)
        self.auto_grp.add_button(auto_select_btn)
        self.auto_grp.add_button(auto_rename_btn)

        self.auto_grp.set_current_state(self.settings.value('autoGroup', 1))
        toolbar_layout.addWidget(self.auto_grp)

        # MTT TOOLS
        self.tool_grp = StatusCollapsibleLayout(section_name='Show/Hide the tools icons')

        self.viewer_btn = self.__create_toolbar_button(
            ':/tb_Viewer',
            'Show/Hide Viewer',
            self.on_toolbar_viewer,
            False)

        create_node_btn = self.__create_toolbar_button(
            ':/tb_toolCreateNode',
            'Create Node',
            self.on_toolbar_create_node,
            False)

        self.viewer_btn.setChecked(get_settings_bool_value(self.settings.value('viewerState', DEFAULT_VIEWER)))

        self.tool_grp.add_button(self.viewer_btn)
        self.tool_grp.add_button(create_node_btn)

        self.tool_grp.set_current_state(self.settings.value('toolGroup', 1))
        toolbar_layout.addWidget(self.tool_grp)

        # MAYA TOOLS SHORTCUT
        self.maya_grp = StatusCollapsibleLayout(section_name='Show/Hide the Maya tools icons')

        self.maya_grp.add_button(self.__create_toolbar_button(
            ':/tb_Hypershade',
            'Hypershade',
            self.on_toolbar_hypershade,
            False)
        )
        self.maya_grp.add_button(self.__create_toolbar_button(
            ':/tb_NodeEditor',
            'Node Editor',
            self.on_toolbar_node_editor,
            False)
        )
        self.maya_grp.add_button(self.__create_toolbar_button(
            ':/tb_UVEditor',
            'UV Texture Editor',
            self.on_toolbar_uv_editor,
            False)
        )

        self.maya_grp.set_current_state(self.settings.value('mayaGroup', 1))
        toolbar_layout.addWidget(self.maya_grp)

        # USER DEFINE GROUP
        if CUSTOM_BUTTONS:
            self.custom_grp = StatusCollapsibleLayout(section_name='Show/Hide custom tools')
            for btnData in CUSTOM_BUTTONS:
                    self.custom_grp.add_button(self.__create_toolbar_button(
                        btnData[0],
                        btnData[1],
                        eval(btnData[2]),
                        False)
                    )
            toolbar_layout.addWidget(self.custom_grp)

        # SETTINGS MENU

        toolbar_layout.addStretch(2)
        self.stat_info = QLabel()
        self.stat_info.setAlignment(Qt.AlignCenter | Qt.AlignRight)
        self.stat_info.setText('0 File | 0/0 Node')
        self.stat_info.setToolTip('number of files | number of nodes shown / total number of nodes')
        toolbar_layout.addWidget(self.stat_info)

        self.info_btn = self.__create_toolbar_button(
            ':/tb_config',
            'Settings',
            self.fake_def,
            False)
        self.info_btn.setMenu(self.__create_settings_menu())
        toolbar_layout.addWidget(self.info_btn)

        return toolbar_layout

    def __create_filter_ui(self):
        """ Create filter widgets """
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(1)
        filter_layout.setContentsMargins(0, 0, 0, 0)

        self.filter_reset_btn = QPushButton()
        icon = QIcon(':/filtersOff.png')
        self.filter_reset_btn.setIcon(icon)
        self.filter_reset_btn.setIconSize(QSize(22, 22))
        self.filter_reset_btn.setFixedSize(24, 24)
        self.filter_reset_btn.setToolTip('Reset filter')
        self.filter_reset_btn.setFlat(True)
        self.filter_reset_btn.clicked.connect(partial(self.on_filter_set_text, ''))

        self.filter_line_edit = QLineEdit()
        self.filter_line_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filter_line_edit.customContextMenuRequested.connect(self.on_filter_quick_filter_menu)
        self.filter_line_edit.textChanged.connect(self.on_filter_text_changed)
        self.filter_line_edit.editingFinished.connect(self.on_filter_add_completion_item)

        completer = QCompleter(self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setModel(self.completion_model)
        self.filter_line_edit.setCompleter(completer)

        self.filter_re_btn = self.__create_toolbar_button(
            ':/fb_regularExpression',
            'Use regular expression',
            self.on_filter_toggle_re,
            True)
        self.filter_re_btn.setChecked(get_settings_bool_value(self.settings.value('filterRE', DEFAULT_FILTER_RE)))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Nodes', 'Files'])
        self.filter_combo.setCurrentIndex(get_settings_int_value(self.settings.value('filterType', 0)))
        self.filter_combo.currentIndexChanged.connect(self.on_filter_index_changed)

        filter_layout.addWidget(self.filter_reset_btn)
        filter_layout.addWidget(self.filter_line_edit)
        filter_layout.addWidget(self.filter_re_btn)
        filter_layout.addWidget(self.filter_combo)

        return filter_layout

    def __create_table_ui(self):
        """ Create QTableView widget """
        self.table_view = QTableView()

        self.table_view.setItemDelegate(self.delegate)
        self.model.set_table_view(self.table_view)
        self.proxy.setSourceModel(self.model)
        self.table_view.setModel(self.proxy)

        if not self.table_view.horizontalHeader().restoreState(self.settings.value('columnsSize')):
            # init some UI with default value when no user pref
            for columnId, sizeValue in VIEW_COLUMN_SIZE.items():
                self.table_view.setColumnWidth(columnId, sizeValue)

        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(17)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setMinimumSectionSize(10)
        self.table_view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_view.setSortingEnabled(True)
        #self.table_view.setMouseTracking(True)
        self.table_view_selection_model = self.table_view.selectionModel()
        self.table_view_selection_model.selectionChanged.connect(self.on_auto_select_node)

        # self.proxy.setDynamicSortFilter(True)
        self.on_filter_index_changed(self.settings.value('filterType', 0))

        # add context menu to show/hide columns
        self.table_view.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(self.on_column_header_context_menu)

        # add context menu
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.on_table_view_context_menu)

        return self.table_view

    def __create_action_ui(self):
        """ Create main button widget """
        self.quick_action_layout = QHBoxLayout()
        self.quick_action_layout.setSpacing(2)
        self.quick_action_layout.setContentsMargins(0, 0, 0, 0)

        self.quick_reload_btn = self.__create_quick_action_button(
                label=r'&Reload',
                tooltip="<p style='white-space:pre'>"
                                "<b>LMB</b> Reload selected files <i>R</i><br>"
                                "<b>RMB</b> Reload all files <i>Ctrl+Alt+R</i></p>",
                help_txt='Reload files (shortcut: R)',
                action=self.on_reload_files,
                right_action=self.on_reload_all_files)
        self.quick_action_layout.addWidget(self.quick_reload_btn)

        self.quick_action_layout.addWidget(
            self.__create_quick_action_button(
                label='&Select',
                tooltip="<p style='white-space:pre'>"
                                "<b>LMB</b> Select nodes <i>S</i><br>"
                                "<b>RMB</b> Open node in AE <i>Ctrl+Alt+S</i></p>",
                help_txt='Select nodes (shortcut: S)',
                action=self.on_select_nodes,
                right_action=self.on_open_node_in_attribute_editor)
        )
        self.quick_action_layout.addWidget(
                self.__create_quick_action_button(
                    label='Re&name',
                    tooltip="<p style='white-space:pre'>"
                                    "<b>LMB</b> Rename nodes with filename <i>N</i><br>"
                                    "<b>RMB</b> Rename all nodes with filename <i>Ctrl+Alt+N</i></p>",
                    help_txt='Rename nodes (shortcut: N)',
                    action=self.on_rename_nodes,
                    right_action=self.on_rename_all_nodes)
        )
        self.quick_action_layout.addWidget(
            self.__create_quick_action_button(
                label='&View',
                tooltip="<p style='white-space:pre'>"
                                "<b>LMB</b> Open files in Viewer <i>V</i><br>"
                                "<b>RMB</b> Open Viewer <i>Ctrl+Alt+V</i></p>",
                help_txt='View files in default viewer (shortcut: V)',
                action=self.on_view_files,
                right_action=self.on_toolbar_viewer)
        )
        self.quick_edit_btn = self.__create_quick_action_button(
            label='&Edit',
            tooltip='',
            help_txt='',
            action=self.on_quick_edit)
        self.quick_action_layout.addWidget(self.quick_edit_btn)
        self.on_set_source_edit_menu(get_settings_bool_value(self.settings.value('switchEdit', DEFAULT_SWITCH_EDIT)))

        return self.quick_action_layout

    @staticmethod
    def __create_quick_action_button(label='button', tooltip=None, help_txt=None, action=None, right_action=None):
        """ Create right click aware button """
        new_button = RightPushButton()
        new_button.setText(label)
        new_button.setToolTip(tooltip)
        if help_txt is None:
            help_txt = tooltip
        new_button.setStatusTip(help_txt)
        new_button.clicked.connect(action)
        if right_action is not None:
            new_button.rightClick.connect(right_action)

        return new_button

    def __create_settings_menu(self):
        """ Create settings context menu """
        settings_menu = QMenu(self)
        settings_menu.setTearOffEnabled(False)

        help_action = QAction('Help', self)
        help_action.setStatusTip('Opens the online Help page')
        help_action.triggered.connect(self.on_settings_help)
        settings_menu.addAction(help_action)

        settings_menu.addSeparator()

        header = QAction('SETTINGS', self)
        header.setEnabled(False)
        settings_menu.addAction(header)

        switch_edit_action = QAction('Switch Edit/Source', self)
        switch_edit_action.setStatusTip('Replace "Edit" button by "Source" button')
        switch_edit_action.setCheckable(True)
        switch_edit_action.setChecked(get_settings_bool_value(self.settings.value('switchEdit', DEFAULT_SWITCH_EDIT)))
        switch_edit_action.triggered.connect(self.on_switch_source_edit_menu)
        settings_menu.addAction(switch_edit_action)

        headsup_action = QAction('HeadsUp Message', self)
        headsup_action.setStatusTip('Show HeadsUp Message in viewport')
        headsup_action.setCheckable(True)
        headsup_action.setChecked(get_settings_bool_value(self.settings.value('showHeadsUp', DEFAULT_SHOW_HEADSUP)))
        headsup_action.triggered.connect(self.on_toggle_headsup)
        settings_menu.addAction(headsup_action)

        focus_filter_action = QAction('Focus Filter Field at Startup', self)
        focus_filter_action.setStatusTip('Focus filter field at startup')
        focus_filter_action.setCheckable(True)
        focus_filter_action.setChecked(get_settings_bool_value(self.settings.value('filterFocus', DEFAULT_FILTER_FOCUS)))
        focus_filter_action.triggered.connect(self.on_toggle_focus)
        settings_menu.addAction(focus_filter_action)

        force_relative_path_action = QAction('Force Relative Path', self)
        force_relative_path_action.setStatusTip('Set a relative path when selecting a new file')
        force_relative_path_action.setCheckable(True)
        force_relative_path_action.setChecked(get_settings_bool_value(self.settings.value('forceRelativePath', DEFAULT_FORCE_RELATIVE_PATH)))
        force_relative_path_action.triggered.connect(self.on_force_relative_path)
        settings_menu.addAction(force_relative_path_action)

        show_real_attr_value_action = QAction('Show Real Attribute Value', self)
        show_real_attr_value_action.setStatusTip('Show fullpath instead of filtering path as Attribute Editor')
        show_real_attr_value_action.setCheckable(True)
        show_real_attr_value_action.setChecked(get_settings_bool_value(self.settings.value('showRealAttributeValue', DEFAULT_SHOW_REAL_ATTRIBUTE)))
        show_real_attr_value_action.triggered.connect(self.on_show_real_attribute_value)
        settings_menu.addAction(show_real_attr_value_action)

        self.instance_menu = QMenu(self)
        self.instance_menu.setTitle('Prompt Instance Delay')
        self.instance_menu.aboutToShow.connect(self.on_show_prompt_instance_delay_menu)
        settings_menu.addMenu(self.instance_menu)

        theme_submenu = QMenu(self)
        theme_submenu.setTitle('Buttons Theme')
        theme_submenu.setTearOffEnabled(True)
        theme_submenu.setWindowTitle(TAG)
        theme_actions = QActionGroup(self)
        theme_actions.setExclusive(True)
        # create ordered theme list
        custom_order_theme = sorted(self.theme_data.iterkeys())
        custom_order_theme.remove('Maya Theme')
        custom_order_theme.insert(0, 'Maya Theme')
        default_item = True
        for themeName in custom_order_theme:
            current_theme_action = QAction(themeName, theme_actions)
            current_theme_action.setCheckable(True)
            current_theme_action.setChecked(self.settings.value('theme', 'Maya Theme') == themeName)
            current_theme_action.triggered.connect(partial(self.on_choose_theme, themeName))
            theme_submenu.addAction(current_theme_action)
            if default_item:
                theme_submenu.addSeparator()
                default_item = False
        settings_menu.addMenu(theme_submenu)

        settings_menu.addSeparator()

        header = QAction('FILTER OPTIONS', self)
        header.setEnabled(False)
        settings_menu.addAction(header)

        manage_quick_filter_action = QAction('Manage Quick Filters', self)
        manage_quick_filter_action.setStatusTip('Manage filters that popup with right clic in filter field')
        manage_quick_filter_action.triggered.connect(self.on_filter_manage_quick_filter)
        settings_menu.addAction(manage_quick_filter_action)

        clear_completion_cache_action = QAction('Clear Completion Cache', self)
        clear_completion_cache_action.setStatusTip('Erase auto completion cache of filter field')
        clear_completion_cache_action.triggered.connect(self.on_filter_clear_completion_cache)
        settings_menu.addAction(clear_completion_cache_action)

        settings_menu.addSeparator()

        header = QAction('MISC', self)
        header.setEnabled(False)
        settings_menu.addAction(header)

        override_panels_action = QAction('Add CreateNode Button to Editors', self)
        override_panels_action.setStatusTip('Add "Create Node" to HyperShade and Node Editor for the current session')
        override_panels_action.triggered.connect(self.on_override_panels)
        settings_menu.addAction(override_panels_action)

        export_to_csv = QAction('Export Texture List as CSV', self)
        export_to_csv.setStatusTip('Export current texture list into a csv file')
        export_to_csv.triggered.connect(self.on_export_as_csv)
        settings_menu.addAction(export_to_csv)

        settings_menu.addSeparator()

        header = QAction('DEBUG', self)
        header.setEnabled(False)
        settings_menu.addAction(header)

        self.debug_menu = QMenu(self)
        self.debug_menu.setTitle('Debug Menu')
        self.debug_menu.aboutToShow.connect(self.on_show_debug_menu)
        settings_menu.addMenu(self.debug_menu)

        settings_menu.addSeparator()

        about = QAction('About', self)
        about.triggered.connect(self.on_settings_about)
        settings_menu.addAction(about)

        return settings_menu

    def __update_node_file_count_ui(self):
        file_count = self.model.get_file_count()
        file_str = 'file' if file_count < 1 else 'files'

        node_shown_count = self.proxy.rowCount()

        node_count = self.model.get_node_count()
        node_str = 'node' if node_count < 1 else 'nodes'

        self.stat_info.setText('%d %s | %d/%d %s' % (file_count, file_str, node_shown_count, node_count, node_str))

    #-------------------------------------------------------------------------------------------------------------------
    # UI LOGIC
    def __layout_changed(self):
        cmds.optionVar(stringValue=('filtered_instances', ''))
        self.model.emit(SIGNAL("layoutChanged()"))
        self.__update_node_file_count_ui()

    @Slot()
    def on_toolbar_show_only_selection(self):
        """ Filter nodes from current selection """
        self.settings.setValue('onlySelectionState', self.selection_btn.isChecked())
        self.update_selection_change_callback_state(self.selection_btn.isChecked())

    @Slot()
    def on_toolbar_show_only_writable(self):
        """ Filter nodes with their file state """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('onlyWritableState', self.writable_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_show_reference(self):
        """ Filter referenced nodes """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('showReferenceState', self.reference_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_pin_nodes(self):
        """ Filter pinned nodes """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        nodes = ''
        if self.pin_btn.isChecked():
            nodes = ';'.join([node.data() for node in self.get_selected_table_nodes()])
        self.settings.setValue('pinnedNode', nodes)
        self.__layout_changed()

    @Slot()
    def on_toolbar_show_wrong_name(self):
        """ Filter node with the same name as texture """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('showWrongNameState', self.wrong_name_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_wrong_name_visibility(self):
        """ Highlight node with the same name as texture """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('vizWrongNameState', self.wrong_name_visibility_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_wrong_path_visibility(self):
        """ Highlight Texture path clashing with user defined path pattern """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('vizWrongPathState', self.wrong_path_visibility_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_basename_visibility(self):
        """ Filter file path """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('showBasenameState', self.basename_visibility_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_namespace_visibility(self):
        """ Filter namespace name """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('showNamespaceState', not self.namespace_visibility_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_filter_instances(self):
        """ Show only one instance per file """
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.settings.setValue('filterInstances', self.filter_instances_btn.isChecked())
        self.__layout_changed()

    @Slot()
    def on_toolbar_open_sourceimages_folder(self):
        """ Open sourceimages folder """
        folder_path = self.model.get_sourceimages_path()
        if os.path.isdir(folder_path):
            os.startfile(folder_path)
        # launchImageEditor can be an alternative
        # cmds.launchImageEditor(viewImageFile=directory)

    @Slot()
    def on_toolbar_open_source_folder(self):
        """ Open source folder """
        folder_path = self.get_texture_source_folder()
        if os.path.isdir(folder_path):
            os.startfile(folder_path)

    @Slot()
    def on_toolbar_viewer(self):
        """ Toggle Viewer """
        if self.viewer_dock is None:
            self.viewer_dock = MTTDockWidget(self.settings, VIEWER_TITLE, self)

            dock_size = self.settings.value('Viewer/dockGeometry', QRect(0, 0, 256, 256))
            dock_is_floating = get_settings_bool_value(self.settings.value('Viewer/isFloating', DEFAULT_VIEWER_IS_FLOATING))
            if dock_is_floating:
                self.viewer_dock.setVisible(False)

            self.viewer_view = mttViewer.MTTViewer(settings=self.settings)
            dock_frame = MTTDockFrame(self, dock_size.width(), dock_size.height())
            dock_frame_layout = QHBoxLayout()
            dock_frame_layout.setContentsMargins(0, 0, 0, 0)
            dock_frame_layout.addWidget(self.viewer_view)
            dock_frame.setLayout(dock_frame_layout)

            self.viewer_dock.setObjectName(VIEWER_DOCK_NAME)
            self.viewer_dock.setFloating(dock_is_floating)
            self.viewer_dock.setWidget(dock_frame)

            # self.viewer_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
            self.viewer_dock.topLevelChanged.connect(self.on_viewer_top_level_changed)
            if dock_is_floating:
                self.viewer_dock.setWindowFlags(Qt.Window)

            self.addDockWidget(self.dock_side_data[self.settings.value('Viewer/side', 'Right')], self.viewer_dock)

            self.viewer_dock.setGeometry(dock_size)
            self.viewer_dock.setVisible(True)

            self.table_view_selection_model.selectionChanged.connect(self.on_auto_show_texture)
            self.settings.setValue('viewerState', True)
            self.display_current_texture()
        else:
            state = not self.viewer_dock.isVisible()
            self.viewer_dock.setVisible(state)
            self.settings.setValue('viewerState', state)
            if state:
                self.table_view_selection_model.selectionChanged.connect(self.on_auto_show_texture)
                self.display_current_texture()
            else:
                self.table_view_selection_model.selectionChanged.disconnect(self.on_auto_show_texture)

    def on_viewer_top_level_changed(self, is_floating):
        if is_floating:
            self.viewer_dock.setWindowFlags(Qt.Window)
            self.viewer_dock.show()

    @Slot()
    def on_toolbar_create_node(self):
        mttFilterFileDialog.create_nodes()

    @staticmethod
    @Slot()
    def on_toolbar_hypershade():
        """ Open Maya Hypershade """
        cmds.HypershadeWindow()

    @staticmethod
    @Slot()
    def on_toolbar_node_editor():
        """ Open Maya Hypershade """
        cmds.NodeEditorWindow()

    @staticmethod
    @Slot()
    def on_toolbar_uv_editor():
        """ Open Maya UV Texture Editor """
        cmds.TextureViewWindow()

    @Slot(str)
    def on_filter_set_text(self, text):
        """ Set text in filter field """
        self.filter_line_edit.setText(text)

    @Slot(str)
    def on_filter_text_changed(self, text):
        """ Apply filter string """
        cmds.optionVar(stringValue=('filtered_instances', ''))
        if len(text):
            icon = QIcon(':/filtersOn.png')
            self.filter_reset_btn.setIcon(icon)
        else:
            icon = QIcon(':/filtersOff.png')
            self.filter_reset_btn.setIcon(icon)

        if self.filter_re_btn.isChecked():
            search = QRegExp(text, Qt.CaseInsensitive, QRegExp.RegExp)
        else:
            search = QRegExp(text, Qt.CaseInsensitive, QRegExp.Wildcard)
        self.proxy.setFilterRegExp(search)
        self.__update_node_file_count_ui()

    @Slot()
    def on_filter_manage_quick_filter(self):
        """ Open Quick Filter words manager and save its content """
        manager = MTTQuickFilterManager(self, self.settings)
        if manager.exec_():
            lists = manager.get_lists()
            # save list in settings
            self.settings.setValue('filterQuickWordsWildcard', ';;'.join(lists[0]))
            self.settings.setValue('filterQuickWordsRegExp', ';;'.join(lists[1]))
            # set current list
            self.quick_filter_words = lists[get_settings_bool_value(self.settings.value('filterRE', DEFAULT_FILTER_RE))]
        manager.deleteLater()

    @Slot(QPoint)
    def on_filter_quick_filter_menu(self, point):
        """ Create Quick Filter context menu """
        history_menu = QMenu(self)
        items = self.quick_filter_words

        if items:
            for item in items:
                item_action = QAction(item, self)
                item_action.triggered.connect(partial(self.on_filter_set_text, item))
                history_menu.addAction(item_action)
        else:
            empty = QAction('No Quick Filter', self)
            empty.setEnabled(False)
            history_menu.addAction(empty)

        history_menu.popup(self.filter_line_edit.mapToGlobal(point))

    @Slot()
    def on_filter_add_completion_item(self):
        """ Add new entry to completion cache """
        filter_text = self.filter_line_edit.text()
        if len(filter_text) < 2:
            return

        if get_settings_bool_value(self.settings.value('filterRE', DEFAULT_FILTER_RE)):
            setting_name = 'filterCompletionRegExp'
        else:
            setting_name = 'filterCompletionWildcard'

        items = self.get_filter_completion_words()

        if items:
            if filter_text not in items:
                items.append(filter_text)
                items.sort()
                self.completion_model.setStringList(items)
                self.settings.setValue(setting_name, ';;'.join(items))
        else:
            self.completion_model.setStringList([filter_text])
            self.settings.setValue(setting_name, filter_text)

    @Slot()
    def on_filter_clear_completion_cache(self):
        """ Clear filter auto completion cache """
        self.on_filter_set_text('')
        self.settings.remove('filterCompletionWildcard')
        self.settings.remove('filterCompletionRegExp')
        self.completion_model.setStringList([])

    @Slot()
    def on_filter_toggle_re(self):
        """ Toggle Regular Expression Filter """
        self.settings.setValue('filterRE', self.filter_re_btn.isChecked())
        filter_text = self.filter_line_edit.text()
        self.filter_line_edit.textChanged.disconnect(self.on_filter_text_changed(text=''))
        self.filter_line_edit.setText('')
        self.filter_line_edit.textChanged.connect(self.on_filter_text_changed)
        self.filter_line_edit.setText(filter_text)
        self.completion_model.setStringList(self.get_filter_completion_words())
        self.quick_filter_words = self.get_filter_quick_words()

    @Slot(int)
    def on_filter_index_changed(self, index):
        """ Change column filter """
        if index == 0:
            self.proxy.setFilterKeyColumn(NODE_NAME)
        elif index == 1:
            self.proxy.setFilterKeyColumn(NODE_FILE)

    @Slot(QPoint)
    def on_column_header_context_menu(self, point):
        """ Create context menu for header visibility """
        if self.header_menu is not None and self.header_menu.isTearOffMenuVisible():
            return

        self.header_menu = QMenu(self)
        self.header_menu.setTearOffEnabled(True)
        self.header_menu.setWindowTitle(TAG)

        is_last_item = self.table_view.horizontalHeader().hiddenSectionCount() == COLUMN_COUNT - 1
        for columnId in range(COLUMN_COUNT):
            state = get_settings_bool_value(self.settings.value('columnVisibility_%s' % columnId, True))
            current_action = QAction(VIEW_COLUMN_CONTEXT[columnId], self)
            current_action.setCheckable(True)
            current_action.setChecked(state)
            current_action.setEnabled(not (state & is_last_item))
            current_action.triggered.connect(partial(self.on_column_header_show_column, columnId))

            self.header_menu.addAction(current_action)

        self.header_menu.popup(self.table_view.horizontalHeader().mapToGlobal(point))

    @Slot(QPoint)
    def on_table_view_context_menu(self, point):
        """ Create table context menu """

        table_menu = QMenu(self)

        edit_image_action = QAction('Open Files in %s' % self.image_editor_name, self)
        edit_image_action.triggered.connect(self.on_edit_files)
        table_menu.addAction(edit_image_action)

        edit_source_image_action = QAction('Open Source Files in %s' % self.image_editor_name, self)
        edit_source_image_action.triggered.connect(self.on_edit_source_files)
        table_menu.addAction(edit_source_image_action)

        table_menu.addSeparator()

        open_file_folder_action = QAction('Open Folders', self)
        open_file_folder_action.triggered.connect(self.on_open_file_folder)
        table_menu.addAction(open_file_folder_action)

        table_menu.addSeparator()

        select_objects_action = QAction('Select Objects Using Texture Nodes', self)
        select_objects_action.triggered.connect(self.on_select_objects_with_shaders)
        table_menu.addAction(select_objects_action)

        select_objects_action = QAction('Select Objects Using Texture Files', self)
        select_objects_action.triggered.connect(self.on_select_objects_with_textures)
        table_menu.addAction(select_objects_action)

        table_menu.addSeparator()

        convert_to_relative_action = QAction('Convert to Relative Path', self)
        convert_to_relative_action.triggered.connect(self.on_convert_to_relative_path)
        table_menu.addAction(convert_to_relative_action)

        convert_to_absolute_action = QAction('Convert to Absolute Path', self)
        convert_to_absolute_action.triggered.connect(self.on_convert_to_absolute_path)
        table_menu.addAction(convert_to_absolute_action)

        custom_path_action = QAction('Convert to Custom Path', self)
        custom_path_action.triggered.connect(self.on_set_custom_path)
        table_menu.addAction(custom_path_action)

        table_menu.addSeparator()

        sourceimages_folder = os.path.basename(self.model.get_sourceimages_path())
        copy_to_workspace_action = QAction('Copy Files to "%s"' % sourceimages_folder, self)
        copy_to_workspace_action.triggered.connect(self.on_copy_files_to_workspace)
        table_menu.addAction(copy_to_workspace_action)

        table_menu.addSeparator()

        rename_with_node_name_action = QAction('Rename Files with Node Name', self)
        rename_with_node_name_action.triggered.connect(self.on_rename_file_with_node_name)
        table_menu.addAction(rename_with_node_name_action)

        rename_with_custom_name_action = QAction('Rename Files with Custom Name', self)
        rename_with_custom_name_action.triggered.connect(self.on_rename_file_with_custom_name)
        table_menu.addAction(rename_with_custom_name_action)

        if self.power_user:
            table_menu.addSeparator()
            toggle_readonly = QAction('Toggle Read-Only', self)
            toggle_readonly.triggered.connect(self.on_toggle_readonly)
            table_menu.addAction(toggle_readonly)

        offset = QPoint(0, self.table_view.horizontalHeader().height())
        table_menu.popup(self.table_view.mapToGlobal(point) + offset)

    @Slot(int)
    def on_column_header_show_column(self, column_id):
        """ Hide/Show table column """
        state = not get_settings_bool_value(self.settings.value('columnVisibility_%s' % column_id, True))
        self.table_view.setColumnHidden(column_id, not state)
        self.settings.setValue('columnVisibility_%s' % column_id, state)

    #@Slot(bool)
    @waitingcursor
    def on_reload_files(self, all_node=False):
        """ Reload selected files """
        nodes = self.get_all_table_nodes() if all_node else self.get_selected_table_nodes()
        if nodes:
            reloaded_files = list()
            self.model.is_reloading_file = True
            for node in [data.data() for data in nodes]:
                node_attr_name = self.supported_format_dict[cmds.nodeType(node)]
                node_attr_value = cmds.getAttr('%s.%s' % (node, node_attr_name))
                if node_attr_value not in reloaded_files:
                    reloaded_files.append(node_attr_value)
                    cmds.setAttr('%s.%s' % (node, node_attr_name), node_attr_value, type="string")
            self.model.is_reloading_file = False
            self.__output_message('%d node%s reloaded' % (len(nodes), ('s' if len(nodes) > 1 else '')), verbose=True)
        else:
            self.__output_message('Nothing selected... nothing to reload')

    @Slot()
    def on_reload_all_files(self):
        self.on_reload_files(all_node=True)

    #@Slot()
    @waitingcursor
    def on_select_nodes(self):
        nodes = self.get_selected_table_nodes()
        if nodes:
            cmds.select([data.data() for data in nodes], replace=True)
            self.__output_message('%d node%s selected' % (len(nodes), ('s' if len(nodes) > 1 else '')))
        else:
            self.__output_message('Nothing selected... nothing to select')

    @Slot()
    def on_open_node_in_attribute_editor(self):
        nodes = self.get_selected_table_nodes()
        mel.eval('showEditorExact("' + nodes[0].data() + '")')

    #@Slot(bool)
    @waitingcursor
    def on_rename_nodes(self, all_node=False):
        nodes = self.get_all_table_nodes() if all_node else self.get_selected_table_nodes()
        if nodes:
            rename_count = 0
            for nodeName in [mID.data() for mID in nodes]:
                wanted_name = self.model.get_node_file_basename(nodeName)
                if len(wanted_name):
                    new_name = self.model.rename_maya_node(nodeName, wanted_name)
                    if new_name != nodeName:
                        rename_count += 1
            self.__output_message(
                '%d/%d node%s renamed with filename' % (rename_count, len(nodes), ('s' if len(nodes) > 1 else '')),
                verbose=True
            )
        else:
            self.__output_message('Nothing selected... nothing to rename')

    @Slot()
    def on_rename_all_nodes(self):
        self.on_rename_nodes(all_node=True)

    @Slot()
    def on_view_files(self, edit=False):
        nodes = self.get_selected_table_nodes()
        if nodes:
            viewed_image = list()
            for node in nodes:
                # nodeName = node.data().toString().toLocal8Bit().data() -> original
                node_name = node.data()
                absolute_path = self.model.get_node_file_fullpath(node_name)
                if absolute_path not in viewed_image:
                    viewed_image.append(absolute_path)
                    if os.path.isfile(absolute_path):
                        if edit:
                            cmds.launchImageEditor(editImageFile=absolute_path)
                        else:
                            cmds.launchImageEditor(viewImageFile=absolute_path)
                    else:
                        filename = os.path.basename(absolute_path)
                        if filename != '.':
                            self.__output_message('File "%s" not found' % filename, verbose=True)
        else:
            self.__output_message('Nothing selected... nothing to show')

    @Slot()
    def on_edit_files(self):
        self.on_view_files(edit=True)

    @Slot()
    def on_quick_edit(self):
        if get_settings_bool_value(self.settings.value('switchEdit', DEFAULT_SWITCH_EDIT)):
            self.on_edit_source_files()
        else:
            self.on_edit_files()

    @Slot()
    def on_set_source_edit_menu(self, state):
        if state:
            self.quick_edit_btn.setText('Source')
            self.quick_edit_btn.setToolTip("<p style='white-space:pre'>Edit source files in %s <i>E</i></p>" % self.image_editor_name)
            self.quick_edit_btn.setStatusTip('Edit source files in %s (shortcut: E)' % self.image_editor_name)
        else:
            self.quick_edit_btn.setText('&Edit')
            self.quick_edit_btn.setToolTip("<p style='white-space:pre'>Edit files in %s <i>E</i></p>" % self.image_editor_name)
            self.quick_edit_btn.setStatusTip('Edit files in %s (shortcut: E)' % self.image_editor_name)

    @Slot()
    def on_switch_source_edit_menu(self):
        state = get_settings_bool_value(self.settings.value('switchEdit', DEFAULT_SWITCH_EDIT))
        self.settings.setValue('switchEdit', not state)
        self.on_set_source_edit_menu(not state)

    @Slot()
    def on_toggle_headsup(self):
        state = get_settings_bool_value(self.settings.value('showHeadsUp', DEFAULT_SHOW_HEADSUP))
        self.settings.setValue('showHeadsUp', not state)

    @Slot()
    def on_toggle_focus(self):
        state = get_settings_bool_value(self.settings.value('filterFocus', DEFAULT_FILTER_FOCUS))
        self.settings.setValue('filterFocus', not state)

    @Slot()
    def on_force_relative_path(self):
        state = get_settings_bool_value(self.settings.value('forceRelativePath', DEFAULT_FORCE_RELATIVE_PATH))
        self.settings.setValue('forceRelativePath', not state)

    @Slot()
    def on_show_real_attribute_value(self):
        self.model.emit(SIGNAL("layoutAboutToBeChanged()"))
        show_real_attribute_state = get_settings_bool_value(self.settings.value('showRealAttributeValue', DEFAULT_SHOW_REAL_ATTRIBUTE))
        self.settings.setValue('showRealAttributeValue', not show_real_attribute_state)
        self.__layout_changed()

    @Slot()
    def on_choose_instance_delay(self, delay_id, result=-1, prompt=True):
        if prompt:
            message_box = QMessageBox()
            message_box.setWindowTitle(WINDOW_TITLE)
            message_box.setIcon(QMessageBox.Question)
            message_box.setText('When textures path are modified,\ndo you want to apply changes to all instances ?')
            message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            message_box.setEscapeButton(QMessageBox.Cancel)
            message_box.setDefaultButton(QMessageBox.Yes)
            ret = message_box.exec_()

            if ret == QMessageBox.Yes:
                result = 1
            elif ret == QMessageBox.No:
                result = 0
            else:
                return

        __main__.mtt_prompt_session = delay_id == PROMPT_INSTANCE_SESSION
        cmds.optionVar(iv=['MTT_prompt_instance_state', delay_id])
        cmds.optionVar(fv=['MTT_prompt_instance_suspend', time()])
        cmds.optionVar(iv=['MTT_prompt_instance_value', result])

    @Slot()
    def on_choose_theme(self, theme_name):
        theme_name = theme_name if theme_name in self.theme_data else 'Maya Theme'
        self.settings.setValue('theme', theme_name)
        btn_default_bg_color = QApplication.palette().button().color().name()
        btn_default_text_color = QApplication.palette().buttonText().color().name()
        custom_buttons = self.findChildren(RightPushButton, QRegExp('.*'))
        for i in range(len(custom_buttons)):
            # select right color
            if theme_name == 'Maya Theme':
                current_bg_color = btn_default_bg_color
                current_text_color = btn_default_text_color
            else:
                current_bg_color = self.theme_data[theme_name][i]
                # get background luminance
                bg_color = QColor(current_bg_color)
                photometric_lum = (0.2126 * bg_color.red()) + (0.7152 * bg_color.green()) + (0.0722 * bg_color.blue())
                # perceivedLum = (0.299 * bgColor.red()) + (0.587 * bgColor.green()) + (0.114 * bgColor.blue())
                # print perceivedLum
                current_text_color = '#363636' if photometric_lum > 130 else '#C8C8C8'
            # set color
            custom_buttons[i].setStyleSheet(
                "RightPushButton {background-color: %s; color: %s};" %
                (current_bg_color, current_text_color)
            )

    # noinspection PyUnusedLocal
    @Slot()
    def on_auto_show_texture(self, selected, deselected):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        self.display_current_texture()
        # current_model_id = self.table_view.selectionModel().currentIndex()
        # current_node_name = (
        # 	current_model_id.data()
        # 	if current_model_id.column() == 0
        # 	else current_model_id.sibling(current_model_id.row(), NODE_NAME).data()
        # )
        # file_path = self.model.get_node_file_fullpath(current_node_name)
        # self.viewer_view.show_image(file_path)

    @Slot()
    def on_auto_reload(self):
        state = get_settings_bool_value(self.settings.value('autoReload', DEFAULT_AUTO_RELOAD))
        self.settings.setValue('autoReload', not state)

    @Slot()
    def on_auto_select(self):
        state = get_settings_bool_value(self.settings.value('autoSelect', DEFAULT_AUTO_SELECT))
        self.settings.setValue('autoSelect', not state)

    @Slot()
    def on_auto_select_node(self, selected, deselected):
        if get_settings_bool_value(self.settings.value('autoSelect', DEFAULT_AUTO_SELECT)):
            cmds.optionVar(intValue=('suspendCallbacks', True))
            nodes = list()
            for node in self.get_selected_table_nodes():
                nodes.append(node.data())
            if nodes:
                cmds.select(nodes, replace=True)
                cmds.optionVar(intValue=('suspendCallbacks', False))

    @Slot()
    def on_auto_rename(self):
        state = get_settings_bool_value(self.settings.value('autoRename', DEFAULT_AUTO_RENAME))
        self.settings.setValue('autoRename', not state)

    def on_auto_rename_node(self, node_name):
        wanted_name = self.model.get_node_file_basename(node_name)
        if len(wanted_name):
            self.model.rename_maya_node(node_name, wanted_name, deferred=True)

    @Slot()
    def on_edit_source_files(self):
        source_folder = self.get_texture_source_folder()
        nodes = self.get_selected_table_nodes()
        if nodes:
            psd_files = list()
            missing_files = list()
            for node in nodes:
                psd_found = False

                # get file path and filename
                node_name = node.data()
                absolute_path = self.model.get_node_file_fullpath(node_name)
                filename = os.path.basename(absolute_path)

                if filename != '.':
                    # split filename with underscore
                    file_without_ext = os.path.splitext(filename)[0]
                    file_token = file_without_ext.split('_')
                    file_token_len = len(file_token)

                    for n in xrange(file_token_len):
                        # remove token one by one starting at the end of the string
                        split_num = file_token_len - n
                        file_without_ext = '_'.join(file_token[:split_num])
                        psd_file = os.path.join(source_folder, file_without_ext + '.psd')

                        # if file doesn't exists try without another token
                        if not os.path.isfile(psd_file):
                            continue

                        # continue if psd file wasn't already opened
                        if psd_file not in psd_files:
                            psd_found = True
                            psd_files.append(psd_file)
                            if os.access(psd_file, os.W_OK):
                                cmds.launchImageEditor(editImageFile=psd_file)
                                self.__output_message('Opening "%s"' % psd_file, verbose=True)
                            else:
                                if self.__prompt_for_open_readonly_source_file(psd_file):
                                    cmds.launchImageEditor(editImageFile=psd_file)
                                    self.__output_message('Opening "%s"' % psd_file, verbose=True)
                                else:
                                    self.__output_message('Opening Aborted for "%s"' % psd_file, verbose=True)

                            # stop iterating tokens
                            break

                # if no psd file found, warn user
                if not psd_found and absolute_path not in missing_files:
                    missing_files.append(absolute_path)
                    self.__output_message('No PSD found for "%s"' % filename, verbose=True, msg_type='warning')
        else:
            self.__output_message('Nothing selected... nothing to show')

    @Slot()
    def on_open_file_folder(self):
        nodes = self.get_selected_table_nodes()
        if nodes:
            opened_folder = list()
            for node in nodes:
                node_name = node.data()
                folder_pat = os.path.dirname(self.model.get_node_file_fullpath(node_name))
                if folder_pat not in opened_folder:
                    opened_folder.append(folder_pat)
                    if os.path.isdir(folder_pat):
                        os.startfile(folder_pat)

    @Slot()
    def on_select_objects_with_shaders(self):
        nodes = self.get_selected_table_nodes()
        objects = list()

        if nodes:
            shading_groups = self.get_shading_group([node.data() for node in nodes])
            if shading_groups:
                objects = cmds.sets(shading_groups, query=True)

        if objects:
            cmds.select(objects, replace=True)
        else:
            cmds.select(clear=True)

    @Slot()
    def on_select_objects_with_textures(self):
        nodes = list()
        objects = list()

        tmp_nodes = self.get_selected_table_nodes()
        for tmpNode in tmp_nodes:
            node_name = tmpNode.data()
            if self.model.get_node_instance_count(node_name) > 1:
                for iNode in self.model.get_node_instances_model_id(node_name):
                    if iNode not in nodes:
                        nodes.append(iNode)
            else:
                nodes.append(tmpNode)

        if nodes:
            shading_groups = self.get_shading_group([node.data() for node in nodes])
            if shading_groups:
                objects = cmds.sets(shading_groups, query=True)

        if objects:
            cmds.select(objects, replace=True)
        else:
            cmds.select(clear=True)

    #@Slot()
    @waitingcursor
    def on_convert_to_relative_path(self):
        nodes = self.get_selected_table_nodes(is_instance_aware=True)
        self.model.suspend_force_sort = True
        self.is_batching_change_attr = True

        for node in nodes:
            node_name = node.data()
            if node_name:
                if not cmds.lockNode(node_name, query=True, lock=True)[0]:
                    node_attr_value = self.model.get_node_attribute(node_name)
                    relative_path = convert_to_relative_path(node_attr_value)
                    self.model.set_database_node_and_attribute(node_name, relative_path)

        self.model.suspend_force_sort = False
        self.is_batching_change_attr = False
        self.model.request_sort()

    #@Slot()
    @waitingcursor
    def on_convert_to_absolute_path(self):
        nodes = self.get_selected_table_nodes(is_instance_aware=True)
        self.model.suspend_force_sort = True
        self.is_batching_change_attr = True
        if nodes:
            for node in nodes:
                node_name = node.data()
                if node_name:
                    if not cmds.lockNode(node_name, query=True, lock=True)[0]:
                        node_attr_value = self.model.get_node_attribute(node_name)
                        absolute_path = self.model.get_node_file_fullpath(node_name)
                        if absolute_path != node_attr_value:
                            self.model.set_database_node_and_attribute(node_name, absolute_path)
        self.model.suspend_force_sort = False
        self.is_batching_change_attr = False
        self.model.request_sort()

    #@Slot()
    @waitingcursor
    def on_set_custom_path(self):
            QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
            custom_path = cmds.fileDialog2(
                caption='Select image directory',
                # startingDirectory=os.path.expandvars('%ProgramFiles%'),
                okCaption='Select',
                fileMode=3)
            QApplication.restoreOverrideCursor()

            if custom_path:
                nodes = self.get_selected_table_nodes(is_instance_aware=True)
                self.model.suspend_force_sort = True
                self.is_batching_change_attr = True
                if nodes:
                    for node in nodes:
                        node_name = node.data()
                        if node_name:
                            if not cmds.lockNode(node_name, query=True, lock=True)[0]:
                                node_attr_name = self.supported_format_dict[cmds.nodeType(node_name)]
                                node_attr_value = self.model.get_node_attribute(node_name)
                                new_path = os.path.normpath(os.path.join(custom_path[0], os.path.basename(node_attr_value)))
                                new_path = new_path.replace('\\', '/')
                                cmds.setAttr('%s.%s' % (node_name, node_attr_name), new_path, type="string")
                self.model.suspend_force_sort = False
                self.is_batching_change_attr = False
                self.model.request_sort()

    #@Slot()
    @waitingcursor
    def on_copy_files_to_workspace(self):
        self.model.suspend_force_sort = True
        self.is_batching_change_attr = True
        nodes = self.get_selected_table_nodes(is_instance_aware=True)
        if nodes:
            file_history = dict()
            sourceimages_path = self.model.get_sourceimages_path()
            for node in nodes:
                node_name = node.data()
                if not node_name:
                    continue
                if not cmds.lockNode(node_name, query=True, lock=True)[0]:
                    file_fullpath = self.model.get_node_file_fullpath(node_name)

                    node_attr_name = self.supported_format_dict[cmds.nodeType(node_name)]
                    if file_fullpath not in file_history.iterkeys():

                        if not os.path.isfile(file_fullpath) or os.path.commonprefix([sourceimages_path, file_fullpath]) == sourceimages_path:
                            continue

                        destination_path = (os.path.join(sourceimages_path, os.path.basename(file_fullpath))).replace('\\', '/')

                        if destination_path == file_fullpath.replace('\\', '/'):
                            file_history[file_fullpath] = None
                            continue
                        else:
                            file_history[file_fullpath] = destination_path

                        if os.path.isfile(destination_path):
                            is_readonly = self.model.get_file_state(destination_path) < 1
                            if not self.__prompt_for_override_file(os.path.basename(destination_path), is_readonly):
                                continue
                            if is_readonly:
                                os.chmod(destination_path, stat.S_IWRITE)

                        if cmds.sysFile(file_fullpath, copy=destination_path):
                            self.__output_message('%s copied.' % os.path.basename(destination_path), verbose=True)
                            os.chmod(destination_path, stat.S_IWRITE)
                            cmds.setAttr('%s.%s' % (node_name, node_attr_name), destination_path, type="string")
                        else:
                            self.__output_message('%s copy failed.' % os.path.basename(destination_path), msg_type='warning', verbose=True)
                    else:
                        if file_history[file_fullpath]:
                            cmds.setAttr('%s.%s' % (node_name, node_attr_name), file_history[file_fullpath], type="string")

        self.model.suspend_force_sort = False
        self.is_batching_change_attr = False
        self.model.request_sort()

    def on_rename_file(self, custom_name=False):
        self.model.suspend_force_sort = True
        self.is_batching_change_attr = True
        nodes = self.get_selected_table_nodes(is_instance_aware=True)
        if nodes:
            file_history = dict()

            for node in nodes:
                node_name = node.data()
                if node_name:
                    if cmds.lockNode(node_name, query=True, lock=True)[0]:
                        continue
                    file_fullpath = self.model.get_node_file_fullpath(node_name)
                    node_attr_name = self.supported_format_dict[cmds.nodeType(node_name)]

                    if file_fullpath not in file_history.iterkeys():
                        if file_fullpath == '.' or not os.path.isfile(file_fullpath):
                            continue

                        file_path = os.path.dirname(file_fullpath)
                        filename, file_ext = os.path.splitext(os.path.basename(file_fullpath))

                        if custom_name:
                            new_path, ok = QInputDialog.getText(
                                self,
                                WINDOW_TITLE,
                                'Enter new name for "%s" :' % filename,
                                QLineEdit.Normal,
                                filename)

                            filename = new_path
                            new_path = os.path.join(file_path, '%s%s' % (new_path, file_ext))
                        else:
                            new_path = os.path.join(file_path, '%s%s' % (node_name.replace(':', '_'), file_ext))

                        if node_name == filename and not custom_name:
                            file_history[file_fullpath] = None
                            continue
                        else:
                            file_history[file_fullpath] = new_path

                        if self.model.get_file_state(file_fullpath) == 1:
                            if cmds.sysFile(file_fullpath, rename=new_path):
                                cmds.setAttr('%s.%s' % (node_name, node_attr_name), new_path, type="string")
                            else:
                                self.__output_message('%s rename failed.' % filename, msg_type='warning', verbose=True)
                        else:
                            self.__output_message('%s rename aborted (read-only).' % filename, msg_type='warning', verbose=True)
                    else:
                        if file_history[file_fullpath]:
                            cmds.setAttr('%s.%s' % (node_name, node_attr_name), file_history[file_fullpath], type="string")

            self.model.suspend_force_sort = False
            self.is_batching_change_attr = False
            self.model.request_sort()

    #@Slot()
    @waitingcursor
    def on_rename_file_with_node_name(self):
        if self.__prompt_for_rename_without_undo():
            undo_state = cmds.undoInfo(query=True, state=True)
            try:
                cmds.undoInfo(stateWithoutFlush=False)
                self.on_rename_file(custom_name=False)
            finally:
                cmds.undoInfo(stateWithoutFlush=undo_state)

    #@Slot()
    @waitingcursor
    def on_rename_file_with_custom_name(self):
        if self.__prompt_for_rename_without_undo():
            undo_state = cmds.undoInfo(query=True, state=True)
            try:
                cmds.undoInfo(stateWithoutFlush=False)
                self.on_rename_file(custom_name=True)
            finally:
                cmds.undoInfo(stateWithoutFlush=undo_state)

    #@Slot()
    @waitingcursor
    def on_toggle_readonly(self):
        nodes = self.get_selected_table_nodes()
        if nodes:
            toggled_files = list()

            for node in nodes:
                node_name = node.data()
                file_fullpath = self.model.get_node_file_fullpath(node_name)

                if not os.path.isfile(file_fullpath) or file_fullpath in toggled_files:
                    continue

                is_readonly = self.model.get_file_state(file_fullpath) < 1
                os.chmod(file_fullpath, (stat.S_IWRITE if is_readonly else stat.S_IREAD))
                toggled_files.append(file_fullpath)

    @staticmethod
    @Slot()
    def on_settings_help():
        help_wiki = 'https://github.com/Bioeden/dbMayaTextureToolkit/wiki'
        webbrowser.open(help_wiki)


    @Slot()
    def on_show_prompt_instance_delay_menu(self):
        prompt_instance_state = cmds.optionVar(query='MTT_prompt_instance_state')

        if prompt_instance_state == PROMPT_INSTANCE_WAIT:
            elapsed_time = time() - cmds.optionVar(query='MTT_prompt_instance_suspend')
            if elapsed_time > PROMPT_INSTANCE_WAIT_DURATION:
                prompt_instance_state = PROMPT_INSTANCE_ASK
                cmds.optionVar(iv=['MTT_prompt_instance_state', prompt_instance_state])
            else:
                self.__output_message('Remaining %.2fs' % (PROMPT_INSTANCE_WAIT_DURATION - elapsed_time))
        elif prompt_instance_state == PROMPT_INSTANCE_SESSION:
            if not 'mtt_prompt_session' in __main__.__dict__:
                prompt_instance_state = PROMPT_INSTANCE_ASK
                cmds.optionVar(iv=['MTT_prompt_instance_state', prompt_instance_state])

        self.instance_menu.clear()

        prompt_delay = QActionGroup(self)
        prompt_delay.setExclusive(True)
        for i in range(len(PROMPT_INSTANCE_STATE.keys())):
            current_delay_action = QAction(PROMPT_INSTANCE_STATE[i], prompt_delay)
            current_delay_action.setCheckable(True)
            current_delay_action.setChecked(prompt_instance_state == i)
            current_delay_action.triggered.connect(partial(self.on_choose_instance_delay, i, prompt=i != 0))
            self.instance_menu.addAction(current_delay_action)

    @Slot()
    def on_show_debug_menu(self):
        self.debug_menu.clear()

        if self.is_master_cmd or self.power_user:
            power_user_mode = QAction('Power User Mode', self)
            power_user_mode.setCheckable(True)
            power_user_mode.setChecked(get_settings_bool_value(self.settings.value('powerUser', DEFAULT_POWER_USER)))
            power_user_mode.triggered.connect(self.__on_toggle_power_user)
            self.debug_menu.addAction(power_user_mode)
            self.is_master_cmd = False

            self.debug_menu.addSeparator()

        open_pref_folder_action = QAction('Open Preferences Folder', self)
        open_pref_folder_action.setStatusTip('Open MTT preference folder')
        open_pref_folder_action.triggered.connect(self.on_open_preference_folder)
        self.debug_menu.addAction(open_pref_folder_action)

        self.debug_menu.addSeparator()

        database_dump_csv = QAction('Dump Database as CSV', self)
        database_dump_csv.triggered.connect(self.model.database_dump_csv)
        self.debug_menu.addAction(database_dump_csv)

        database_dump_sql = QAction('Dump Database as SQL', self)
        database_dump_sql.triggered.connect(self.model.database_dump_sql)
        self.debug_menu.addAction(database_dump_sql)

        self.debug_menu.addSeparator()

        self.support_info = QMenu(self)
        self.support_info.setTitle('Supported Node Type')
        self.support_info.aboutToShow.connect(self.on_show_supported_type)
        self.debug_menu.addMenu(self.support_info)

    @Slot()
    def on_show_supported_type(self):
        node_types = sorted([nodetype for (nodetype, nice, attr) in SUPPORTED_TYPE] + UNSUPPORTED_TYPE)
        self.support_info.clear()

        for nodetype in node_types:
            current = QAction(nodetype, self)
            current.setEnabled(False)
            current.setCheckable(True)
            current.setChecked(nodetype not in UNSUPPORTED_TYPE)
            self.support_info.addAction(current)

    @Slot()
    def __on_toggle_power_user(self):
        state = get_settings_bool_value(self.settings.value('powerUser', DEFAULT_POWER_USER))
        self.settings.setValue('powerUser', not state)
        self.power_user = not state

    @Slot()
    def on_export_as_csv(self):
        """ Export texture listing in csv file """
        file_content = self.model.get_database_content_as_csv()

        # check if current scene is empty
        if not file_content:
            db_output('Nothing to save. Operation aborted.', msg_type='warning')
            return

        # clean output
        convert_nicename = dict(zip([n for t, n, a in SUPPORTED_TYPE], [t for t, n, a in SUPPORTED_TYPE]))
        for i, row in enumerate(file_content):
            node_type = convert_nicename[row[1]]
            ref_str = 'True' if row[2] == 1 else ''
            missing_str = 'True' if row[3] == -1 else ''
            file_content[i] = (row[0], node_type, ref_str, missing_str, row[4], row[5])

        # query file to write
        scene_name = os.path.basename(cmds.file(query=True, sceneName=True))
        file_path = os.path.join(cmds.workspace(query=True, rootDirectory=True), scene_name)
        csv_path = cmds.fileDialog2(
            fileFilter='Texture List (*.csv)',
            caption='Save Texture List',
            startingDirectory=file_path,
            fileMode=0)

        # fill file
        if csv_path is not None:
            import csv
            file_path = csv_path[0]
            scene_name = cmds.file(query=True, sceneName=True) or 'Scene UNTITLED'
            with open(file_path, "w") as csv_file:
                csv_file_writer = csv.writer(csv_file, delimiter=';')
                csv_file_writer.writerow([scene_name])
                csv_file_writer.writerow(['NODE NAME', 'NODE TYPE', 'IS REF', 'MISSING', 'INSTANCE COUNT', 'FILE PATH'])
                csv_file_writer.writerows(file_content)
                csv_file.close()
                db_output('CSV file saved to %s' % file_path)
                cmds.launchImageEditor(viewImageFile=os.path.dirname(file_path))

    @Slot()
    def on_open_preference_folder(self):
        """ Open preference folder """
        folder_path = os.path.dirname(self.settings.fileName())
        cmds.launchImageEditor(viewImageFile=folder_path)

    @Slot()
    def on_override_panels(self):
        """ Override HyperShade and NodeEditor creation callback"""
        override_info_box = QMessageBox()
        override_info_box.setWindowTitle(WINDOW_TITLE)
        override_info_box.setIcon(QMessageBox.Information)
        override_info_box.setText(
            'Buttons will be added to HyperShade toolbar and Node Editor toolbar.<br/>'
            'Changes will exists during this session.'
        )
        override_info_box.setInformativeText('<i>Read Help to set this settings permanent</i>')
        override_info_box.setStandardButtons(QMessageBox.Ok)
        override_info_box.setDefaultButton(QMessageBox.Ok)
        override_info_box.exec_()

        mttOverridePanels.override_panels()

    @Slot()
    def on_settings_about(self):
        from __init__ import __version__, __author__
        special_list = [u'Stordeur Beno\xeet', u'Jumel Fran\xe7ois', 'Lorber Jonathan', 'Cretinon Norbert', 'Hoff Gilles']
        QMessageBox.about(
            self,
            WINDOW_TITLE,
            '<b>Maya Texture Toolkit v%s</b>'
            u'<p>%s - \xa9 2014'
            '</p>'
            '<p>Special thanks to :<br/>'
            '%s'
            '</p>' % (__version__, __author__, '<br/>'.join([u'<i>\xa0\xa0%s %s</i>' % (name.partition(' ')[2], name.partition(' ')[0]) for name in sorted(special_list)]))
        )

    #-------------------------------------------------------------------------------------------------------------------
    # TOOLS METHODS
    def __output_message(self, message, msg_type=None, verbose=False):
        db_output(message, msg_type=msg_type)

        if get_settings_bool_value(self.settings.value('showHeadsUp', DEFAULT_SHOW_HEADSUP)) and not verbose:
            cmds.headsUpMessage(message)

    @staticmethod
    def __prompt_for_override_file(filename, is_readonly):
        msg = '<b>%s</b> already exists' % filename
        if is_readonly:
            msg += ' and is a read-only file'
        msg += '.'

        message_box = QMessageBox()
        message_box.setWindowTitle(WINDOW_TITLE)
        message_box.setIcon(QMessageBox.Question)
        message_box.setText(msg)
        message_box.setInformativeText('Do you want to <b>override</b> file ?')
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.Yes)
        message_box.setEscapeButton(QMessageBox.Cancel)
        ret = message_box.exec_()

        if ret == QMessageBox.Yes:
            return True
        elif ret == QMessageBox.No:
            return False

    @staticmethod
    def __prompt_for_open_readonly_source_file(filename):
        msg = '<b>%s</b> is a read-only file.' % os.path.basename(filename)

        message_box = QMessageBox()
        message_box.setWindowTitle(WINDOW_TITLE)
        message_box.setIcon(QMessageBox.Question)
        message_box.setText(msg)
        message_box.setInformativeText('Do you want to <b>open</b> this file anyway?')
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.Yes)
        message_box.setEscapeButton(QMessageBox.Cancel)
        ret = message_box.exec_()

        if ret == QMessageBox.Yes:
            return True
        elif ret == QMessageBox.No:
            return False

    @staticmethod
    def __prompt_for_rename_without_undo():
        message_box = QMessageBox()
        message_box.setWindowTitle(WINDOW_TITLE)
        message_box.setIcon(QMessageBox.Question)
        message_box.setText('This operation can\'t be undo.')
        message_box.setInformativeText('Do you want to <b>continue</b> anyway ?')
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.Yes)
        message_box.setEscapeButton(QMessageBox.Cancel)
        ret = message_box.exec_()

        if ret == QMessageBox.Yes:
            return True
        elif ret == QMessageBox.No:
            return False

    def __prompt_for_instance_propagation(self, show_cancel_button=True):
        prompt_instance_state = cmds.optionVar(query='MTT_prompt_instance_state')
        if prompt_instance_state:
            if prompt_instance_state == PROMPT_INSTANCE_WAIT:
                current_time = time()
                if current_time - cmds.optionVar(query='MTT_prompt_instance_suspend') < PROMPT_INSTANCE_WAIT_DURATION:
                    return cmds.optionVar(query='MTT_prompt_instance_value')
            elif prompt_instance_state == PROMPT_INSTANCE_SESSION:
                if 'mtt_prompt_session' in __main__.__dict__ and __main__.mtt_prompt_session:
                    return cmds.optionVar(query='MTT_prompt_instance_value')
            elif prompt_instance_state == PROMPT_INSTANCE_ALWAYS:
                return cmds.optionVar(query='MTT_prompt_instance_value')

        QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
        message_box = MessageBoxWithCheckbox()
        message_box.setWindowTitle(WINDOW_TITLE)
        message_box.setIcon(QMessageBox.Question)
        message_box.setText('-- Nodes with the same texture found. --\n\nDo you want to change all instances ?')
        message_box.instance_state_widget.addItems(PROMPT_INSTANCE_STATE.values())
        if show_cancel_button:
            message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            message_box.setEscapeButton(QMessageBox.Cancel)
        else:
            message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            message_box.setEscapeButton(QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.Yes)
        ret, suspend = message_box.exec_()

        result = -1
        if ret == QMessageBox.Yes:
            result = 1
        elif ret == QMessageBox.No:
            result = 0

        self.on_choose_instance_delay(suspend, result, False)

        QApplication.restoreOverrideCursor()

        return result

    @property
    def __get_image_editor_name(self):
        if cmds.optionVar(exists='EditImageDir'):
            app_name = os.path.splitext(os.path.basename(cmds.optionVar(query='EditImageDir')))[0]
            self.image_editor_name = app_name
            return app_name

        return 'Image Editor'

    def keyPressEvent(self, event):
        """ Capture keyPress to prevent Maya Shortcut """
        if event.isAutoRepeat():
            return

        if self.viewer_dock:
            if self.viewer_dock.isVisible():
                self.viewer_view.is_mtt_sender = True
                if self.viewer_view.keyPressEvent(event):
                    self.viewer_view.is_mtt_sender = False
                    return
                self.viewer_view.is_mtt_sender = False

        if event.modifiers() == Qt.ControlModifier:
            self.is_master_cmd = True

        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.filter_line_edit.setFocus()
        elif event.key() == Qt.Key_R and event.modifiers() == Qt.NoModifier:
            self.on_reload_files()
        elif event.key() == Qt.Key_R and event.modifiers() == Qt.ControlModifier | Qt.AltModifier:
            self.on_reload_all_files()
        elif event.key() == Qt.Key_S and event.modifiers() == Qt.NoModifier:
            self.on_select_nodes()
        elif event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier | Qt.AltModifier:
            self.on_open_node_in_attribute_editor()
        elif event.key() == Qt.Key_N and event.modifiers() == Qt.NoModifier:
            self.on_rename_nodes()
        elif event.key() == Qt.Key_N and event.modifiers() == Qt.ControlModifier | Qt.AltModifier:
            self.on_rename_all_nodes()
        elif event.key() == Qt.Key_V and event.modifiers() == Qt.NoModifier:
            self.on_view_files()
        elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier | Qt.AltModifier:
            self.on_toolbar_viewer()
        elif event.key() == Qt.Key_E and event.modifiers() == Qt.NoModifier:
            self.on_quick_edit()
        elif event.key() in [Qt.Key_Left, Qt.Key_Up, Qt.Key_Right, Qt.Key_Down]:
            return
        else:
            super(MTTView, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        if self.viewer_dock:
            if self.viewer_dock.isVisible():
                self.viewer_view.keyReleaseEvent(event)

        self.is_master_cmd = False
        return super(MTTView, self).keyReleaseEvent(event)

    def get_shading_group(self, nodes):
        """ Return ShadingEngine node attach to nodes """
        shading_groups = list()
        shading_nodes = cmds.listHistory(nodes, future=True, pruneDagObjects=True)
        if shading_nodes:
            for futureNode in shading_nodes[:]:
                asset_name = cmds.container(query=True, findContainer=[futureNode])
                if asset_name:
                    self.callback_selection_changed_recursive(shading_nodes, asset_name, True)
            shading_groups = cmds.ls(list(set(shading_nodes)), exactType='shadingEngine')

        return shading_groups

    def get_texture_source_folder(self):
        """ Return texture source folder """
        key = '<WORKSPACE>'
        texture_source_folder = TEXTURE_SOURCE_FOLDER
        if key in TEXTURE_SOURCE_FOLDER:
            texture_source_folder = TEXTURE_SOURCE_FOLDER.replace(key, cmds.workspace(query=True, rootDirectory=True))

        texture_source_folder = os.path.normpath(texture_source_folder)

        if not os.path.isdir(texture_source_folder):
            # if default folder not found, try in sourceimages folder
            if key in TEXTURE_SOURCE_FOLDER:
                texture_source_folder = TEXTURE_SOURCE_FOLDER.replace(key, self.model.get_sourceimages_path())
                texture_source_folder = os.path.normpath(texture_source_folder)
                if not os.path.isdir(texture_source_folder):
                    # if another location doesn't exists, return workspace root
                    texture_source_folder = cmds.workspace(query=True, rootDirectory=True)
                    self.__output_message('You should change "textureSourceFolder" folder in mtt.json file', msg_type='warning')

        return os.path.normpath(texture_source_folder)

    def get_selected_table_nodes(self, is_instance_aware=False):
        nodes = list()
        nodes_name = list()
        is_already_prompted = False
        collect_instance = False

        for index in self.table_view.selectionModel().selectedRows(NODE_NAME):
            node_name = index.data()

            if node_name not in nodes_name:
                nodes_name.append(node_name)
                nodes.append(index)

            if is_instance_aware:
                if self.model.get_node_instance_count(node_name) > 1:
                    if collect_instance:
                        result = 1
                    else:
                        if not is_already_prompted:
                            result = self.__prompt_for_instance_propagation()
                        is_already_prompted = True
                    if result == -1:
                        return []
                    elif result == 1:
                        collect_instance = True
                        for instanceIndex in self.model.get_node_instances_model_id(node_name):
                            instance_index_name = instanceIndex.data()
                            if instance_index_name not in nodes_name:
                                nodes_name.append(instance_index_name)
                                nodes.append(instanceIndex)

        return nodes

    def get_all_table_nodes(self):
        nodes = []
        for rowId in xrange(self.proxy.rowCount()):
            midx = self.proxy.index(rowId, 0, QModelIndex())
            node = midx.data()
            if cmds.objExists(node):
                nodes.append(midx)

        return nodes

    def get_filter_completion_words(self):
        if get_settings_bool_value(self.settings.value('filterRE', DEFAULT_FILTER_RE)):
            item_str = self.settings.value('filterCompletionRegExp', '')
        else:
            item_str = self.settings.value('filterCompletionWildcard', '')

        if item_str:
            return item_str.split(';;')
        else:
            return []

    def get_filter_quick_words(self):
        if self.quick_filter_words_init:
            self.quick_filter_words_init = False
            self.settings.setValue('defaultQuickFilterWords', False)
            self.settings.setValue('filterQuickWordsRegExp', r'_DIF$;;_NOR$;;_SPE$;;HEAD;;BODY;;^HEAD\w*DIF$;;^HEAD.*NOR')
            self.settings.setValue('filterQuickWordsWildcard', '_DIF;;_NOR;;_SPE;;HEAD;;BODY;;HEAD*_DIF;;HEAD*_NOR')

        if get_settings_bool_value(self.settings.value('filterRE', DEFAULT_FILTER_RE)):
            item_str = self.settings.value('filterQuickWordsRegExp', '')
        else:
            item_str = self.settings.value('filterQuickWordsWildcard', '')

        if item_str:
            return item_str.split(';;')
        else:
            return []

    def display_current_texture(self):
        """ Display in viewer the first selected row """
        if not self.viewer_dock:
            return

        if self.viewer_dock.isVisible():
            current_model_id = self.table_view.selectionModel().currentIndex()
            if current_model_id:
                current_node_name = (
                    current_model_id.data()
                    if current_model_id.column() == 0
                    else current_model_id.sibling(current_model_id.row(), NODE_NAME).data()
                )
                if current_node_name:
                    file_path = self.model.get_node_file_fullpath(current_node_name)
                    self.viewer_view.show_image(file_path)

    def callback_open_scene(self, clientData=None):
        cmds.optionVar(intValue=('suspendCallbacks', True))

    def callback_rename_node(self, node, old_name, clientData=None):
        if cmds.optionVar(query='suspendCallbacks') \
                or not old_name \
                or self.settings.value('suspendRenameCallbacks', False):
            return
        new_node = om.MFnDependencyNode(node)
        if new_node.typeName() in self.supported_format_dict.iterkeys():
            new_node_name = new_node.name()
            if new_node_name != old_name:
                self.model.rename_database_node(old_name, new_node_name)
                if self.proxy.selected_texture_nodes is not None:
                    self.proxy.selected_texture_nodes.remove(old_name)
                    self.proxy.selected_texture_nodes.add(new_node_name)
                self.model.request_sort()
                self.attribute_callback_id[new_node_name] = self.attribute_callback_id.pop(old_name)

    def callback_add_node(self, node, clientData=None):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        new_node_name = om.MFnDependencyNode(node).name()
        if cmds.nodeType(new_node_name) in self.supported_format_dict.iterkeys():
            self.model.database_add_new_node(new_node_name)
            self.model.request_sort()
            self.create_attribute_calllback(new_node_name)
            self.__update_node_file_count_ui()

    def callback_remove_node(self, node, clientData=None):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        node_name = om.MFnDependencyNode(node).name()
        if cmds.nodeType(node_name) in self.supported_format_dict.iterkeys():
            self.model.database_remove_node(node_name)
            self.model.request_sort()
            self.remove_attribute_callback(node_name)
            self.__update_node_file_count_ui()

    def callback_attribute_changed(self, node_msg, plug, otherPlug, clientData=None):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        node, attr = plug.name().split('.')
        if node_msg & om.MNodeMessage.kAttributeSet:
            if attr == self.supported_format_dict[cmds.nodeType(node)]:
                new_path = cmds.getAttr(plug.name())
                extra_nodes = list()
                if not self.is_batching_change_attr and not self.model.is_reloading_file:
                    if self.model.get_node_instance_count(node) > 1:
                        if self.__prompt_for_instance_propagation(show_cancel_button=False) == 1:
                            instance_nodes = self.model.get_node_instances_model_id(node)
                            for instanceNode in instance_nodes:
                                extra_node = instanceNode.data()
                                if extra_node != node:
                                    extra_nodes.append(extra_node)

                if self.model.change_node_attribute(node, new_path):
                    is_auto_rename_activated = get_settings_bool_value(self.settings.value('autoRename', DEFAULT_AUTO_RENAME))
                    if is_auto_rename_activated:
                        self.on_auto_rename_node(node)

                    for extra_node in extra_nodes:
                        cmds.optionVar(intValue=('suspendCallbacks', True))
                        node_attr_name = self.supported_format_dict[cmds.nodeType(extra_node)]
                        cmds.setAttr('%s.%s' % (extra_node, node_attr_name), new_path, type="string")
                        if self.model.change_node_attribute(extra_node, new_path):
                            if is_auto_rename_activated:
                                self.on_auto_rename_node(extra_node)
                    cmds.optionVar(intValue=('suspendCallbacks', False))

                    self.model.request_sort()
                    self.__update_node_file_count_ui()

    def callback_selection_changed_recursive(self, shading_nodes, asset_node, do_future):
        shading_nodes.extend(cmds.container(asset_node, query=True, nodeList=True))

        if do_future:
            new_nodes_list = [nodeAttr.split('.')[0] for nodeAttr in cmds.container(asset_node, query=True, connectionList=True)]
        else:
            new_nodes_list = cmds.listHistory(asset_node)

        for node in new_nodes_list[:]:
            if node not in shading_nodes:
                asset_name = cmds.container(query=True, findContainer=[node])
                if asset_name:
                    self.callback_selection_changed_recursive(shading_nodes, asset_name, do_future)

        shading_nodes.extend(new_nodes_list)
        shading_nodes.extend(cmds.listHistory(new_nodes_list, future=do_future))

    def callback_selection_changed(self, clientData=None):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        current_selection = cmds.ls(selection=True, objectsOnly=True)
        current_shading_group = list()
        supported_format = self.supported_format_dict.keys()

        if current_selection:
            # create SG list
            shading_nodes = cmds.listHistory(current_selection, future=True, pruneDagObjects=True)
            if shading_nodes is not None:
                for futureNode in shading_nodes[:]:
                    asset_name = cmds.container(query=True, findContainer=[futureNode])
                    if asset_name:
                        self.callback_selection_changed_recursive(shading_nodes, asset_name, True)
                current_shading_group = cmds.ls(list(set(shading_nodes)), exactType='shadingEngine')

            if current_shading_group:
                nodes = list()
                # parse SG
                for SG in current_shading_group:
                    shading_nodes = cmds.listHistory(SG, pruneDagObjects=True)
                    if shading_nodes is not None:
                        for nodeName in shading_nodes[:]:
                            asset_name = cmds.container(query=True, findContainer=[nodeName])
                            if asset_name:
                                self.callback_selection_changed_recursive(shading_nodes, asset_name, False)
                                #shadingNodes.extend(cmds.container(assetName, query=True, nodeList=True))
                                #shadingNodes.extend(cmds.listHistory(assetName))

                    nodes.extend(cmds.ls(list(set(shading_nodes)), exactType=supported_format))

                self.proxy.selected_texture_nodes = set(nodes)
                self.model.request_sort()
                self.__update_node_file_count_ui()
                return
            else:
                self.proxy.selected_texture_nodes = None
                self.model.request_sort()
        # if no selection
        else:
            self.proxy.selected_texture_nodes = None
            self.model.request_sort()

        self.__update_node_file_count_ui()

    def reset_mtt(self, clientData=None):
        cmds.optionVar(stringValue=('filtered_instances', ''))
        self.pin_btn.setChecked(False)
        self.settings.remove('pinnedNode')
        self.clear_all_attribute_callbacks()
        self.model.filewatch_remove_all()
        self.model.database_reset()
        cmds.optionVar(intValue=('suspendCallbacks', DEFAULT_SUSPEND_CALLBACK))
        self.apply_attribute_change_callback()
        self.__update_node_file_count_ui()

    @Slot()
    def fake_def(self):
        pass

    #-------------------------------------------------------------------------------------------------------------------
    # MANAGE CALLBACKS
    def apply_attribute_change_callback(self):
        nodes = self.model.get_all_nodes_name()
        for nodeName in nodes:
            self.create_attribute_calllback(nodeName[0])

    def create_attribute_calllback(self, node_name):
        # get MObject of node_name
        sel = om.MSelectionList()
        sel.add(node_name)
        m_node = om.MObject()
        sel.getDependNode(0, m_node)
        # create callbacks for this node
        self.attribute_callback_id[node_name] = om.MNodeMessage.addAttributeChangedCallback(m_node, self.callback_attribute_changed)

    def remove_attribute_callback(self, node_name):
        om.MNodeMessage.removeCallback(self.attribute_callback_id[node_name])
        self.attribute_callback_id.pop(node_name)

    def clear_all_attribute_callbacks(self):
        for aCBId in self.attribute_callback_id.itervalues():
            om.MNodeMessage.removeCallback(aCBId)
        self.attribute_callback_id.clear()

    def update_selection_change_callback_state(self, state):
        if state:
            self.selection_callback_id = om.MEventMessage.addEventCallback('SelectionChanged', self.callback_selection_changed)
            self.callback_selection_changed()
        else:
            if self.selection_callback_id is not 0:
                om.MSceneMessage.removeCallback(self.selection_callback_id)
                self.selection_callback_id = 0
                self.proxy.selected_texture_nodes = None
                self.model.request_sort()
        self.__update_node_file_count_ui()

    def __create_callbacks(self):
        """ Create callbacks """
        self.is_callbacks_created = True
        self.new_callback_id = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterNew, self.reset_mtt)

        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeOpen, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, self.reset_mtt))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeImport, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterImport, self.reset_mtt))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeImport, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterImport, self.reset_mtt))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeRemoveReference, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterRemoveReference, self.reset_mtt))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeImportReference, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterImportReference, self.reset_mtt))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeUnloadReference, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterUnloadReference, self.reset_mtt))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeLoadReference, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterLoadReference, self.reset_mtt))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeCreateReference, self.callback_open_scene))
        self.scene_callbacks_ids.append(om.MSceneMessage.addCallback(om.MSceneMessage.kAfterCreateReference, self.reset_mtt))

        self.rename_node_callback_id = om.MNodeMessage.addNameChangedCallback(om.MObject(), self.callback_rename_node)
        self.add_node_callback_id = om.MDGMessage.addNodeAddedCallback(self.callback_add_node)
        self.remove_node_callback_id = om.MDGMessage.addNodeRemovedCallback(self.callback_remove_node)

        self.apply_attribute_change_callback()
        self.update_selection_change_callback_state(get_settings_bool_value(self.settings.value('onlySelectionState', DEFAULT_ONLY_SELECTION)))

    def __remove_callbacks(self):
        """ Remove callbacks """
        if not self.is_callbacks_created:
            return
        om.MSceneMessage.removeCallback(self.new_callback_id)
        for callbackID in self.scene_callbacks_ids:
            om.MSceneMessage.removeCallback(callbackID)
        om.MSceneMessage.removeCallback(self.rename_node_callback_id)
        om.MSceneMessage.removeCallback(self.add_node_callback_id)
        om.MSceneMessage.removeCallback(self.remove_node_callback_id)
        self.clear_all_attribute_callbacks()
        self.update_selection_change_callback_state(False)

    def __remove_filewatch(self):
        self.model.filewatch_remove_all()

    #-------------------------------------------------------------------------------------------------------------------
    # CLEAN EXIT
    def __save_dock_settings(self):
        if not self.viewer_dock:
            return

        is_floating = self.viewer_dock.isFloating()
        dock_geometry = self.viewer_dock.geometry()
        central_geometry = self.centralWidget().geometry()

        if not is_floating:
            delta_x = central_geometry.x() - dock_geometry.x()
            delta_y = central_geometry.y() - dock_geometry.y()
            if delta_x > 0 and delta_y == 0:
                self.settings.setValue('Viewer/side', 'Left')
            elif delta_x == 0 and delta_y > 0:
                self.settings.setValue('Viewer/side', 'Top')
            elif delta_x < 0 and delta_y == 0:
                self.settings.setValue('Viewer/side', 'Right')
            elif delta_x == 0 and delta_y < 0:
                self.settings.setValue('Viewer/side', 'Bottom')

        self.settings.setValue('Viewer/isFloating', is_floating)
        self.settings.setValue('Viewer/dockGeometry', dock_geometry)

    def __save_settings(self):
        """ Save settings to QSettings """
        if self.table_view is None:
            return

        self.settings.setValue('windowGeometry', self.saveGeometry())
        self.settings.setValue('centralGeometry', self.centralWidget().geometry())
        self.settings.setValue('columnsSize', self.table_view.horizontalHeader().saveState())

        self.settings.setValue('filterRE', self.filter_re_btn.isChecked())
        self.settings.setValue('filterType', self.filter_combo.currentIndex())

        self.settings.setValue('onlySelectionState', self.selection_btn.isChecked())
        self.settings.setValue('onlyWritableState', self.writable_btn.isChecked())
        self.settings.setValue('showReferenceState', self.reference_btn.isChecked())
        self.settings.setValue('showWrongNameState', self.wrong_name_btn.isChecked())
        self.settings.remove('pinnedNode')
        self.settings.setValue('vizWrongNameState', self.wrong_name_visibility_btn.isChecked())
        self.settings.setValue('showBasenameState', self.basename_visibility_btn.isChecked())
        self.settings.setValue('filterInstances', self.filter_instances_btn.isChecked())

        self.settings.setValue('filterGroup', self.filter_grp.current_state())
        self.settings.setValue('visibilityGroup', self.visibility_grp.current_state())
        self.settings.setValue('folderGroup', self.folder_grp.current_state())
        self.settings.setValue('autoGroup', self.auto_grp.current_state())
        self.settings.setValue('toolGroup', self.tool_grp.current_state())
        self.settings.setValue('mayaGroup', self.maya_grp.current_state())

        # remove temp variable
        self.settings.remove('browserFirstStart')

    def closeEvent(self, event):
        """ closeEvent override to save preferences and close callbacks """
        if self.table_view is not None:
            # prevent crash when file path editor is open
            self.table_view.setFocus()

            # save user pref
            self.__save_settings()
            self.__save_dock_settings()

            # remove callbacks
            self.__remove_callbacks()

            # remove file watch
            self.__remove_filewatch()

            # delete memory database
            self.model.database_close()

        # clean widget
        self.deleteLater()

        event.accept()
