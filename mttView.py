# Python import
from functools import partial
from time import time
import os
import stat
# PySide import
from PySide.QtGui import *
from PySide.QtCore import (
    Qt, QSize, QRegExp, QPoint, QRect, QModelIndex, QFileSystemWatcher)
# Maya import
import __main__
from maya import mel, cmds, OpenMaya as om
from maya.OpenMaya import MSceneMessage as sceneMsg
# Custom import
import mttResources
import mttViewer
import mttModel
import mttDelegate
import mttProxy
import mttCmdUi
from mttConfig import (
    MTTSettings,
    WINDOW_NAME, WINDOW_TITLE, WINDOW_ICON, VIEWER_TITLE, VIEWER_DOCK_NAME,
    DEFAULT_VALUES, VIEW_COLUMN_SIZE, VIEW_COLUMN_CONTEXT,
    TAG, NODE_NAME, NODE_FILE, COLUMN_COUNT, PROMPT_INSTANCE_SESSION, THEMES,
    PROMPT_INSTANCE_WAIT_DURATION, PROMPT_INSTANCE_STATE, PROMPT_INSTANCE_ALWAYS,
    PROMPT_INSTANCE_WAIT
)
from mttCmd import (
    convert_to_relative_path, get_source_file,
    check_editor_preferences, mtt_log, set_attr
)
from mttCmdUi import get_maya_window
from mttCustomWidget import RightPushButton, MessageBoxWithCheckbox
from mttDecorators import wait_cursor
from mttSettingsMenu import MTTSettingsMenu
from mttViewStatusLine import MTTStatusLine
# avoid inspection error
from mttSourceControlTemplate import checkout, submit, revert


class MTTDockFrame(QFrame):
    """ Workaround to restore DockWidget size """
    def __init__(self, parent=None, w=256, h=256):
        super(MTTDockFrame, self).__init__(parent)
        self.custom_width = w
        self.custom_height = h

    def sizeHint(self, *args, **kwargs):
        return QSize(self.custom_width, self.custom_height)


class MTTDockWidget(QDockWidget):
    def __init__(self, title):
        super(MTTDockWidget, self).__init__()

        self.setWindowTitle(title)

    def closeEvent(self, event):
        MTTSettings.set_value('viewerState', False)
        MTTSettings.set_value('Viewer/windowGeometry', self.saveGeometry())
        super(MTTDockWidget, self).closeEvent(event)


# ------------------------------------------------------------------------------
# MAIN WINDOW
# ------------------------------------------------------------------------------
class MTTView(QMainWindow):
    """ Maya Texture Manager Main UI """

    def __init__(self, parent=None):
        super(MTTView, self).__init__(parent)

        mttResources.qInitResources()

        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle(WINDOW_TITLE)

        # Callbacks variables
        self.is_callbacks_created = False
        self.is_batching_change_attr = False
        self.scene_callbacks_ids = []
        self.selection_callback_id = 0
        self.new_callback_id = 0
        self.open_callback_id = 0
        self.rename_node_callback_id = 0
        self.add_node_callback_id = 0
        self.remove_node_callback_id = 0
        self.attribute_callback_id = dict()

        # UI variables
        self.viewer_dock = None
        self.viewer_view = None
        self.image_editor_name = self.__get_image_editor_name()
        self.header_menu = None
        self.filter_reset_btn = None
        self.filter_line_edit = None
        self.filter_re_btn = None
        self.filter_combo = None
        self.table_view = None
        self.table_view_selection_model = None
        self.quick_action_layout = None
        self.quick_reload_btn = None
        self.quick_edit_btn = None
        self.dock_side_data = dict()
        self.dock_side_data['Left'] = Qt.LeftDockWidgetArea
        self.dock_side_data['Top'] = Qt.TopDockWidgetArea
        self.dock_side_data['Right'] = Qt.RightDockWidgetArea
        self.dock_side_data['Bottom'] = Qt.BottomDockWidgetArea
        self.supported_format_dict = dict(
            [(nodeType, nodeAttrName)
             for nodeType, nice, nodeAttrName in MTTSettings.SUPPORTED_TYPE])

        # clean old pref
        suspend_callback_value = DEFAULT_VALUES['suspendCallbacks']
        MTTSettings.remove('suspendCallbacks')
        cmds.optionVar(intValue=('suspendCallbacks', suspend_callback_value))
        cmds.optionVar(stringValue=('filtered_instances', ''))

        # main UI variables
        self.file_watcher = QFileSystemWatcher()
        self.model = mttModel.MTTModel(watcher=self.file_watcher)
        self.delegate = mttDelegate.MTTDelegate()
        self.proxy = mttProxy.MTTProxy()

        # user completion
        self.completion_model = QStringListModel(
            self.get_filter_completion_words(), self)
        self.quick_filter_words_init = MTTSettings.value(
            'defaultQuickFilterWords')
        self.quick_filter_words = self.get_filter_quick_words()

        # create UI
        self.__create_ui()
        self.__init_ui()

        # create callbacks
        self.__create_callbacks()

    # -------------------------------------------------------------------------
    # UI CREATION
    def __create_ui(self):
        """ Create main UI """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(1)
        main_layout.setContentsMargins(2, 2, 2, 2)

        self.settings_menu = MTTSettingsMenu(self)

        self.status_line_ui = MTTStatusLine(
            self.settings_menu, self.model, self.proxy)
        self.status_line_ui.viewerToggled.connect(self.on_toggle_viewer)
        self.status_line_ui.pinModeToggled.connect(self.on_pin_toggle)
        self.status_line_ui.externalVizToggled.connect(self._update_workspace)
        self.status_line_ui.filterSelectionToggled.connect(
            self.update_selection_change_callback_state)

        main_layout.addLayout(self.status_line_ui)
        main_layout.addLayout(self.__create_filter_ui())
        main_layout.addWidget(self.__create_table_ui())
        main_layout.addLayout(self.__create_action_ui())

        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        if MTTSettings.value('viewerState'):
            self.on_toggle_viewer()

    def __init_ui(self):
        # restore geometry
        self.restoreGeometry(MTTSettings.value('windowGeometry'))
        self.centralWidget().setGeometry(
            MTTSettings.value('centralGeometry', QRect(0, 0, 400, 200))
        )

        # update delegate workspace
        self._update_workspace()

        # restore table header width
        if not self.table_view.horizontalHeader().restoreState(
                MTTSettings.value('columnsSize')):
            # init some UI with default value when no user pref
            for columnId, sizeValue in VIEW_COLUMN_SIZE.iteritems():
                self.table_view.setColumnWidth(columnId, sizeValue)

        # manage focus to avoid hotkey capture
        # when tool is called with shortcut key
        if MTTSettings.value('filterFocus'):
            self.filter_line_edit.setFocus()
        else:
            self.setFocus()

        # update node/file count
        self.__update_node_file_count_ui()

        # apply theme
        self.on_choose_theme(MTTSettings.value('theme', 'Default'))
        self.setWindowIcon(QIcon(WINDOW_ICON))

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
        self.filter_reset_btn.clicked.connect(
            partial(self.on_filter_set_text, ''))

        self.filter_line_edit = QLineEdit()
        self.filter_line_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filter_line_edit.customContextMenuRequested.connect(
            self.on_filter_quick_filter_menu)
        self.filter_line_edit.textChanged.connect(self.on_filter_text_changed)
        self.filter_line_edit.editingFinished.connect(
            self.on_filter_add_completion_item)

        completer = QCompleter(self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setModel(self.completion_model)
        self.filter_line_edit.setCompleter(completer)

        self.filter_re_btn = mttCmdUi.create_status_button(
            ':/fb_regularExpression',
            'Use regular expression',
            self.on_filter_toggle_re,
            True)
        self.filter_re_btn.setChecked(MTTSettings.value('filterRE'))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Nodes', 'Files'])
        self.filter_combo.setCurrentIndex(MTTSettings.value('filterType'))
        self.filter_combo.currentIndexChanged.connect(
            self.on_filter_index_changed)

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

        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(17)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setMinimumSectionSize(10)
        self.table_view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_view.setSortingEnabled(True)

        # self.proxy.setDynamicSortFilter(True)
        self.on_filter_index_changed(MTTSettings.value('filterType'))

        # add context menu to show/hide columns
        self.table_view.horizontalHeader().setContextMenuPolicy(
            Qt.CustomContextMenu)
        self.table_view.horizontalHeader().customContextMenuRequested.connect(
            self.on_column_header_context_menu)

        # add context menu
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(
            self.on_table_view_context_menu)

        self.table_view.setModel(self.proxy)
        self.table_view_selection_model = self.table_view.selectionModel()
        self.table_view_selection_model.selectionChanged.connect(
            self.on_auto_select_cb)

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
                            "<b>RMB</b> Rename all nodes with filename "
                            "<i>Ctrl+Alt+N</i></p>",
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
                right_action=self.on_toggle_viewer)
        )
        self.quick_edit_btn = self.__create_quick_action_button(
            label='&Edit',
            tooltip='',
            help_txt='',
            action=self.on_quick_edit)
        self.quick_action_layout.addWidget(self.quick_edit_btn)
        self.on_set_source_edit_menu(MTTSettings.value('switchEdit'))

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

    def __update_node_file_count_ui(self):
        self.status_line_ui.update_node_file_count()

    # --------------------------------------------------------------------------
    # UI LOGIC
    def _layout_changed(self):
        cmds.optionVar(stringValue=('filtered_instances', ''))
        self.model.layoutChanged.emit()
        self.__update_node_file_count_ui()

    def _update_workspace(self):
        workspace_root = os.path.normpath(cmds.workspace(q=True, rd=True))
        self.delegate.ws_path = workspace_root

    def on_pin_toggle(self, state):
        self.model.layoutAboutToBeChanged.emit()

        nodes = '' if not state else ';'.join(
            [node.data() for node in self.get_selected_table_nodes()])

        MTTSettings.set_value('pinnedNode', nodes)

        self._layout_changed()

    def on_filter_set_text(self, text=''):
        """ Set text in filter field """
        self.filter_line_edit.setText(text)

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

    def on_filter_add_completion_item(self):
        """ Add new entry to completion cache """
        filter_text = self.filter_line_edit.text()
        if len(filter_text) < 2:
            return

        if MTTSettings.value('filterRE'):
            setting_name = 'filterCompletionRegExp'
        else:
            setting_name = 'filterCompletionWildcard'

        items = self.get_filter_completion_words()

        if items:
            if filter_text not in items:
                items.append(filter_text)
                items.sort()
                self.completion_model.setStringList(items)
                MTTSettings.set_value(setting_name, ';;'.join(items))
        else:
            self.completion_model.setStringList([filter_text])
            MTTSettings.set_value(setting_name, filter_text)

    def on_filter_toggle_re(self):
        """ Toggle Regular Expression Filter """
        MTTSettings.set_value('filterRE', self.filter_re_btn.isChecked())
        filter_text = self.filter_line_edit.text()
        self.filter_line_edit.textChanged.disconnect(self.on_filter_text_changed(text=''))
        self.filter_line_edit.setText('')
        self.filter_line_edit.textChanged.connect(self.on_filter_text_changed)
        self.filter_line_edit.setText(filter_text)
        self.completion_model.setStringList(self.get_filter_completion_words())
        self.quick_filter_words = self.get_filter_quick_words()

    def on_filter_index_changed(self, index):
        """ Change column filter """
        if index == 0:
            self.proxy.setFilterKeyColumn(NODE_NAME)
        elif index == 1:
            self.proxy.setFilterKeyColumn(NODE_FILE)

    def on_column_header_context_menu(self, point):
        """ Create context menu for header visibility """
        if self.header_menu is not None and self.header_menu.isTearOffMenuVisible():
            return

        self.header_menu = QMenu(self)
        self.header_menu.setTearOffEnabled(True)
        self.header_menu.setWindowTitle(TAG)

        is_last_item = self.table_view.horizontalHeader().hiddenSectionCount() == COLUMN_COUNT - 1
        for columnId in range(COLUMN_COUNT):
            state = MTTSettings.value('columnVisibility_%s' % columnId, True)
            current_action = QAction(VIEW_COLUMN_CONTEXT[columnId], self)
            current_action.setCheckable(True)
            current_action.setChecked(state)
            current_action.setEnabled(not (state & is_last_item))
            current_action.triggered.connect(partial(self.on_column_header_show_column, columnId))

            self.header_menu.addAction(current_action)

        self.header_menu.popup(self.table_view.horizontalHeader().mapToGlobal(point))

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

        if MTTSettings.VCS:
            table_menu.addSeparator()

            if 'checkout' in MTTSettings.VCS:
                check_out_action = QAction('Checkout', self)
                check_out_action.triggered.connect(self.on_checkout)
                table_menu.addAction(check_out_action)

            if 'submit' in MTTSettings.VCS:
                check_in_action = QAction('submit', self)
                check_in_action.triggered.connect(self.on_submit)
                table_menu.addAction(check_in_action)

            if 'revert' in MTTSettings.VCS:
                revert_action = QAction('Revert', self)
                revert_action.triggered.connect(self.on_revert)
                table_menu.addAction(revert_action)

        if MTTSettings.value('powerUser'):
            table_menu.addSeparator()
            toggle_readonly = QAction('Toggle Read-Only', self)
            toggle_readonly.triggered.connect(self.on_toggle_readonly)
            table_menu.addAction(toggle_readonly)

        offset = QPoint(0, self.table_view.horizontalHeader().height())
        table_menu.popup(self.table_view.mapToGlobal(point) + offset)

    def on_column_header_show_column(self, column_id):
        """ Hide/Show table column """
        state = not MTTSettings.value('columnVisibility_%s' % column_id, True)
        self.table_view.setColumnHidden(column_id, not state)
        MTTSettings.set_value('columnVisibility_%s' % column_id, state)

    @wait_cursor
    def on_reload_files(self, all_node=False):
        """ Reload selected files """
        nodes = self.get_all_table_nodes() if all_node else self.get_selected_table_nodes()
        if nodes:
            reloaded_files = []
            reloaded_files_count = 0
            self.model.is_reloading_file = True
            for node in [data.data() for data in nodes]:
                node_attr_name = self.supported_format_dict[cmds.nodeType(node)]
                node_attr_value = cmds.getAttr('%s.%s' % (node, node_attr_name))
                if node_attr_value not in reloaded_files:
                    reloaded_files.append(node_attr_value)
                    if set_attr(node, node_attr_name, node_attr_value, attr_type="string"):
                        reloaded_files_count += 1
            self.model.is_reloading_file = False
            mtt_log('%d/%d texture%s reloaded' % (
                reloaded_files_count, len(nodes),
                ('s' if reloaded_files_count > 1 else '')))
        else:
            mtt_log('Nothing selected... nothing to reload')

    def on_reload_all_files(self):
        self.on_reload_files(all_node=True)

    @wait_cursor
    def on_select_nodes(self):
        nodes = self.get_selected_table_nodes()
        if nodes:
            cmds.select([data.data() for data in nodes], replace=True)
            mtt_log('%d node%s selected' % (len(nodes), ('s' if len(nodes) > 1 else '')))
        else:
            mtt_log('Nothing selected... nothing to select')

    def on_open_node_in_attribute_editor(self):
        nodes = self.get_selected_table_nodes()
        mel.eval('showEditorExact("' + nodes[0].data() + '")')

    @wait_cursor
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
            mtt_log(
                '%d/%d node%s renamed with filename' % (rename_count, len(nodes), ('s' if len(nodes) > 1 else '')),
                verbose=False
            )
        else:
            mtt_log('Nothing selected... nothing to rename')

    def on_rename_all_nodes(self):
        self.on_rename_nodes(all_node=True)

    def on_view_files(self, edit=False):
        nodes = self.get_selected_table_nodes()
        if nodes:
            viewed_image = []
            for node in nodes:
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
                            mtt_log('File "%s" not found' % filename, verbose=False)
        else:
            mtt_log('Nothing selected... nothing to show')

    def on_edit_files(self):
        self.on_view_files(edit=True)

    def on_quick_edit(self):
        if MTTSettings.value('switchEdit'):
            self.on_edit_source_files()
        else:
            self.on_edit_files()

    def on_set_source_edit_menu(self, state):
        if state:
            self.quick_edit_btn.setText('Source')
            self.quick_edit_btn.setToolTip("<p style='white-space:pre'>Edit source files in %s <i>E</i></p>" % self.image_editor_name)
            self.quick_edit_btn.setStatusTip('Edit source files in %s (shortcut: E)' % self.image_editor_name)
        else:
            self.quick_edit_btn.setText('&Edit')
            self.quick_edit_btn.setToolTip("<p style='white-space:pre'>Edit files in %s <i>E</i></p>" % self.image_editor_name)
            self.quick_edit_btn.setStatusTip('Edit files in %s (shortcut: E)' % self.image_editor_name)

    def on_toggle_viewer(self):
        """ Toggle Viewer """
        self.table_view_selection_model = self.table_view.selectionModel()

        if self.viewer_dock is None:
            # init value
            MTTSettings.set_value('viewerState', True)

            # get default values
            default_size = QRect(0, 0, 256, 256)
            dock_size = MTTSettings.value('Viewer/dockGeometry', default_size)
            dock_is_floating = MTTSettings.value('Viewer/isFloating')

            # create widgets
            self.viewer_dock = MTTDockWidget(VIEWER_TITLE)
            self.viewer_view = mttViewer.MTTViewer()
            dock_frame = MTTDockFrame(
                self, dock_size.width(), dock_size.height())

            # layout widgets
            dock_frame_layout = QHBoxLayout()
            dock_frame_layout.setContentsMargins(0, 0, 0, 0)
            dock_frame_layout.addWidget(self.viewer_view)
            dock_frame.setLayout(dock_frame_layout)
            self.viewer_dock.setObjectName(VIEWER_DOCK_NAME)
            self.viewer_dock.setWidget(dock_frame)

            self.addDockWidget(
                self.dock_side_data[MTTSettings.value('Viewer/side', 'Right')],
                self.viewer_dock
            )

            # init callback
            self.viewer_dock.topLevelChanged.connect(
                self.on_viewer_top_level_changed)
            self.table_view_selection_model.selectionChanged.connect(
                self.on_auto_show_texture)

            # update
            self.viewer_dock.setFloating(dock_is_floating)
            self.viewer_dock.setGeometry(dock_size)
            self.viewer_dock.setVisible(True)
            self.display_current_texture()
        else:
            state = not self.viewer_dock.isVisible()
            self.viewer_dock.setVisible(state)
            MTTSettings.set_value('viewerState', state)
            if state:
                self.table_view_selection_model.selectionChanged.connect(self.on_auto_show_texture)
                self.display_current_texture()
            else:
                self.table_view_selection_model.selectionChanged.disconnect(self.on_auto_show_texture)

    def on_viewer_top_level_changed(self, is_floating):
        if is_floating:
            self.viewer_dock.setWindowFlags(Qt.Window)
            self.viewer_dock.show()

    @staticmethod
    def on_choose_instance_delay(delay_id, result=-1, prompt=True):
        msg = ('When textures path are modified,\n'
               'do you want to apply changes to all instances ?')

        if prompt:
            message_box = QMessageBox()
            message_box.setWindowTitle(WINDOW_TITLE)
            message_box.setIcon(QMessageBox.Question)
            message_box.setText(msg)
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

    def on_choose_theme(self, theme_name):
        theme_name = theme_name if theme_name in THEMES else 'Maya Theme'
        MTTSettings.set_value('theme', theme_name)
        btn_default_bg_color = QApplication.palette().button().color().name()
        btn_default_text_color = QApplication.palette().buttonText().color().name()
        custom_buttons = self.findChildren(RightPushButton, QRegExp('.*'))
        for i in range(len(custom_buttons)):
            # select right color
            if theme_name == 'Maya Theme':
                current_bg_color = btn_default_bg_color
                current_text_color = btn_default_text_color
            else:
                current_bg_color = THEMES[theme_name][i]
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

    def on_auto_select_cb(self, selected, deselected):
        if MTTSettings.value('autoSelect'):
            cmds.optionVar(intValue=('suspendCallbacks', True))
            nodes = []
            for node in self.get_selected_table_nodes():
                nodes.append(node.data())
            if nodes:
                cmds.select(nodes, replace=True)
                cmds.optionVar(intValue=('suspendCallbacks', False))

    def on_rename_node(self, node_name):
        wanted_name = self.model.get_node_file_basename(node_name)
        if wanted_name:
            self.model.rename_maya_node(node_name, wanted_name, deferred=True)

    def on_edit_source_files(self):
        source_files = set()
        user_choice_files = set()
        missing_files = set()

        self._update_workspace()
        nodes = self.get_selected_table_nodes()
        if not nodes:
            mtt_log('Nothing selected... nothing to show')
            return

        # parse all selected nodes
        for node in nodes:
            node_name = node.data()
            absolute_path = self.model.get_node_file_fullpath(node_name)

            # avoid extra processing/request for already scanned files
            if absolute_path in source_files:
                continue

            # get source file for current node
            source_file = get_source_file(absolute_path)

            # store files without source file
            if not source_file:
                missing_files.add(absolute_path)
                continue

            is_external = not source_file.startswith(self.delegate.ws_path)
            is_writable = os.access(source_file, os.W_OK)

            # finally sort writable and internal source files from others
            if is_writable and not is_external:
                source_files.add(source_file)
            else:
                user_choice_files.add((source_file, is_writable, is_external))

        # open writable source files from current workspace
        for source in source_files:
            cmds.launchImageEditor(editImageFile=source)
            mtt_log('Opening "%s"' % source, verbose=False)

        # open non writable source files if user want it
        for source, is_writable, is_external in user_choice_files:
            if self.__prompt_to_open_file(source, is_writable, is_external):
                cmds.launchImageEditor(editImageFile=source)
                mtt_log('Opening "%s"' % source, verbose=False)
            else:
                mtt_log('Opening Aborted for "%s"' % source, verbose=False)

        # log missing source files
        for source in missing_files:
            mtt_log('No PSD found for "%s"' % source,
                    verbose=False, msg_type='warning')

    def on_open_file_folder(self):
        nodes = self.get_selected_table_nodes()
        if nodes:
            opened_folder = []
            for node in nodes:
                node_name = node.data()
                folder_pat = os.path.dirname(self.model.get_node_file_fullpath(node_name))
                if folder_pat not in opened_folder:
                    opened_folder.append(folder_pat)
                    if os.path.isdir(folder_pat):
                        os.startfile(folder_pat)

    def on_select_objects_with_shaders(self):
        nodes = self.get_selected_table_nodes()
        objects = []

        if nodes:
            shading_groups = self.get_shading_group([node.data() for node in nodes])
            if shading_groups:
                objects = cmds.sets(shading_groups, query=True)

        if objects:
            cmds.select(objects, replace=True)
        else:
            cmds.select(clear=True)

    def on_select_objects_with_textures(self):
        nodes = []
        objects = []

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

    @wait_cursor
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

    @wait_cursor
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

    @wait_cursor
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
                                set_attr(node_name, node_attr_name, new_path, type="string")
                self.model.suspend_force_sort = False
                self.is_batching_change_attr = False
                self.model.request_sort()

    @wait_cursor
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
                            mtt_log('%s copied.' % os.path.basename(destination_path), verbose=False)
                            os.chmod(destination_path, stat.S_IWRITE)
                            set_attr(node_name, node_attr_name, destination_path, attr_type="string")
                        else:
                            mtt_log('%s copy failed.' % os.path.basename(destination_path), msg_type='warning', verbose=False)
                    else:
                        if file_history[file_fullpath]:
                            set_attr(node_name, node_attr_name, file_history[file_fullpath], attr_type="string")

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
                                set_attr(node_name, node_attr_name, new_path, attr_type="string")
                            else:
                                mtt_log('%s rename failed.' % filename, msg_type='warning', verbose=False)
                        else:
                            mtt_log('%s rename aborted (read-only).' % filename, msg_type='warning', verbose=False)
                    else:
                        if file_history[file_fullpath]:
                            set_attr(node_name, node_attr_name, file_history[file_fullpath], attr_type="string")

            self.model.suspend_force_sort = False
            self.is_batching_change_attr = False
            self.model.request_sort()

    @wait_cursor
    def on_rename_file_with_node_name(self):
        if self.__prompt_for_rename_without_undo():
            undo_state = cmds.undoInfo(query=True, state=True)
            try:
                cmds.undoInfo(stateWithoutFlush=False)
                self.on_rename_file(custom_name=False)
            finally:
                cmds.undoInfo(stateWithoutFlush=undo_state)

    @wait_cursor
    def on_rename_file_with_custom_name(self):
        if self.__prompt_for_rename_without_undo():
            undo_state = cmds.undoInfo(query=True, state=True)
            try:
                cmds.undoInfo(stateWithoutFlush=False)
                self.on_rename_file(custom_name=True)
            finally:
                cmds.undoInfo(stateWithoutFlush=undo_state)

    def on_checkout(self, files=None):
        if not files:
            nodes = self.get_selected_table_nodes()
            files = [self.model.get_node_file_fullpath(n.data()) for n in nodes]

        exec MTTSettings.VCS['checkout']
        checkout(set(files))

    def on_submit(self):
        nodes = self.get_selected_table_nodes()
        files = [self.model.get_node_file_fullpath(n.data()) for n in nodes]

        exec MTTSettings.VCS['submit']
        submit(set(files))

    def on_revert(self):
        nodes = self.get_selected_table_nodes()
        files = [self.model.get_node_file_fullpath(n.data()) for n in nodes]

        exec MTTSettings.VCS['revert']
        revert(set(files))

    @wait_cursor
    def on_toggle_readonly(self):
        nodes = self.get_selected_table_nodes()
        if nodes:
            toggled_files = []

            for node in nodes:
                node_name = node.data()
                file_fullpath = self.model.get_node_file_fullpath(node_name)

                if not os.path.isfile(file_fullpath) or file_fullpath in toggled_files:
                    continue

                is_readonly = self.model.get_file_state(file_fullpath) < 1
                os.chmod(file_fullpath, (stat.S_IWRITE if is_readonly else stat.S_IREAD))
                toggled_files.append(file_fullpath)

    # --------------------------------------------------------------------------
    # TOOLS METHODS
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

    def __prompt_to_open_file(self, filename, is_writable, is_external):
        checkout_btn = None
        msg = ''

        # add non writable comment
        if not is_writable:
            msg += '<b>%s</b> is a read-only file.' % os.path.basename(filename)
            msg += '<br/>'

        # add external comment
        if is_external:
            msg += '<br/>This file is not in the current workspace :'
            msg += '<br/>{}'.format(filename)

        message_box = QMessageBox()
        message_box.setWindowTitle(WINDOW_TITLE)
        message_box.setIcon(QMessageBox.Question)
        message_box.setText(msg)
        message_box.setInformativeText('Do you want to <b>open</b> this file anyway?')

        # create buttons
        yes_btn = message_box.addButton('Yes', QMessageBox.YesRole)
        if not is_external and 'checkout' in MTTSettings.VCS:
            checkout_btn = message_box.addButton(
                'Yes && Checkout', QMessageBox.AcceptRole)
        no_btn = message_box.addButton('No', QMessageBox.DestructiveRole)

        # set default buttons
        message_box.setDefaultButton(yes_btn)
        message_box.setEscapeButton(no_btn)

        # show dialog
        message_box.exec_()
        pressed_btn = message_box.clickedButton()

        # result
        if pressed_btn == yes_btn:
            return True
        elif pressed_btn == no_btn:
            return False
        elif pressed_btn == checkout_btn:
            self.on_checkout([filename])
            return True

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

    def __get_image_editor_name(self):
        if cmds.optionVar(exists='EditImageDir'):
            app_path = cmds.optionVar(query='EditImageDir')
            app_name = os.path.splitext(os.path.basename(app_path))[0]
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
            self.on_toggle_viewer()
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

        return super(MTTView, self).keyReleaseEvent(event)

    def get_shading_group(self, nodes):
        """ Return ShadingEngine node attach to nodes """
        shading_groups = []
        shading_nodes = cmds.listHistory(nodes, future=True, pruneDagObjects=True)
        if shading_nodes:
            for futureNode in shading_nodes[:]:
                asset_name = cmds.container(query=True, findContainer=[futureNode])
                if asset_name:
                    self.callback_selection_changed_recursive(shading_nodes, asset_name, True)
            shading_groups = cmds.ls(list(set(shading_nodes)), exactType='shadingEngine')

        return shading_groups

    def get_selected_table_nodes(self, is_instance_aware=False):
        nodes = []
        nodes_name = []
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

    @staticmethod
    def get_filter_completion_words():
        if MTTSettings.value('filterRE'):
            item_str = MTTSettings.value('filterCompletionRegExp')
        else:
            item_str = MTTSettings.value('filterCompletionWildcard')

        return item_str.split(';;') if item_str else []

    def get_filter_quick_words(self):
        if self.quick_filter_words_init:
            self.quick_filter_words_init = False
            MTTSettings.set_value('defaultQuickFilterWords', False)
            MTTSettings.set_value('filterQuickWordsRegExp', r'_DIF$;;_NOR$;;_SPE$;;HEAD;;BODY;;^HEAD\w*DIF$;;^HEAD.*NOR')
            MTTSettings.set_value('filterQuickWordsWildcard', '_DIF;;_NOR;;_SPE;;HEAD;;BODY;;HEAD*_DIF;;HEAD*_NOR')

        if MTTSettings.value('filterRE'):
            item_str = MTTSettings.value('filterQuickWordsRegExp')
        else:
            item_str = MTTSettings.value('filterQuickWordsWildcard')

        return item_str.split(';;') if item_str else []

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

    @staticmethod
    def callback_open_scene(clientData=None):
        cmds.optionVar(intValue=('suspendCallbacks', True))

    def callback_rename_node(self, node, old_name, clientData=None):
        if cmds.optionVar(query='suspendCallbacks') \
                or not old_name \
                or MTTSettings.value('suspendRenameCallbacks'):
            return
        dep_node = om.MFnDependencyNode(node)
        if dep_node.typeName() in self.supported_format_dict:
            new_name = dep_node.name()
            if new_name != old_name:
                self.model.rename_database_node(old_name, new_name)
                if self.proxy.selected_texture_nodes is not None:
                    if old_name in self.proxy.selected_texture_nodes:
                        self.proxy.selected_texture_nodes.remove(old_name)
                    self.proxy.selected_texture_nodes.add(new_name)
                self.model.request_sort()
                self.attribute_callback_id[new_name] = self.attribute_callback_id.pop(old_name)

    def callback_add_node(self, node, clientData=None):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        new_node_name = om.MFnDependencyNode(node).name()
        if cmds.nodeType(new_node_name) in self.supported_format_dict.iterkeys():
            self.model.database_add_new_node(new_node_name)
            self.model.request_sort()
            self.create_attribute_callback(new_node_name)
            self.__update_node_file_count_ui()

    def callback_remove_node(self, node, clientData=None):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        dep_node = om.MFnDependencyNode(node)
        if dep_node.typeName() in self.supported_format_dict:
            self.model.database_remove_node(dep_node.name())
            self.model.request_sort()
            self.remove_attribute_callback(dep_node.name())
            self.__update_node_file_count_ui()

    def callback_attribute_changed(self, node_msg, plug, otherPlug, clientData=None):
        if cmds.optionVar(query='suspendCallbacks'):
            return
        node, attr = plug.name().split('.')
        if node_msg & om.MNodeMessage.kAttributeSet:
            if attr == self.supported_format_dict[cmds.nodeType(node)]:
                new_path = cmds.getAttr(plug.name())
                extra_nodes = []
                if not self.is_batching_change_attr and not self.model.is_reloading_file:
                    if self.model.get_node_instance_count(node) > 1:
                        if self.__prompt_for_instance_propagation(show_cancel_button=False) == 1:
                            instance_nodes = self.model.get_node_instances_model_id(node)
                            for instanceNode in instance_nodes:
                                extra_node = instanceNode.data()
                                if extra_node != node:
                                    extra_nodes.append(extra_node)

                if self.model.change_node_attribute(node, new_path):
                    is_auto_rename_activated = MTTSettings.value('autoRename')
                    if is_auto_rename_activated:
                        self.on_rename_node(node)

                    for extra_node in extra_nodes:
                        cmds.optionVar(intValue=('suspendCallbacks', True))
                        node_attr_name = self.supported_format_dict[cmds.nodeType(extra_node)]
                        set_attr(extra_node, node_attr_name, new_path, attr_type="string")
                        if self.model.change_node_attribute(extra_node, new_path):
                            if is_auto_rename_activated:
                                self.on_rename_node(extra_node)
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
        current_shading_group = []
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
                nodes = []
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
        self.status_line_ui.pin_btn.setChecked(False)
        MTTSettings.remove('pinnedNode')
        self._update_workspace()
        self.clear_all_attribute_callbacks()
        self.model.file_watch_remove_all()
        self.model.database_reset()
        suspend_callback_value = DEFAULT_VALUES['suspendCallbacks']
        cmds.optionVar(intValue=('suspendCallbacks', suspend_callback_value))
        self.apply_attribute_change_callback()
        self.__update_node_file_count_ui()

    # --------------------------------------------------------------------------
    # MANAGE CALLBACKS
    def apply_attribute_change_callback(self):
        nodes = self.model.get_all_nodes_name()
        for nodeName in nodes:
            self.create_attribute_callback(nodeName[0])

    def create_attribute_callback(self, node_name):
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
                sceneMsg.removeCallback(self.selection_callback_id)
                self.selection_callback_id = 0
                self.proxy.selected_texture_nodes = None
                self.model.request_sort()
        self.__update_node_file_count_ui()

    def __create_callbacks(self):
        """ Create callbacks """
        def add_callback(cb_type, func):
            self.scene_callbacks_ids.append(
                sceneMsg.addCallback(cb_type, func)
            )

        self.is_callbacks_created = True
        self.new_callback_id = sceneMsg.addCallback(sceneMsg.kAfterNew, self.reset_mtt)

        add_callback(sceneMsg.kBeforeOpen, self.callback_open_scene)
        add_callback(sceneMsg.kAfterOpen, self.reset_mtt)
        add_callback(sceneMsg.kBeforeImport, self.callback_open_scene)
        add_callback(sceneMsg.kAfterImport, self.reset_mtt)
        add_callback(sceneMsg.kBeforeImport, self.callback_open_scene)
        add_callback(sceneMsg.kAfterImport, self.reset_mtt)
        add_callback(sceneMsg.kBeforeRemoveReference, self.callback_open_scene)
        add_callback(sceneMsg.kAfterRemoveReference, self.reset_mtt)
        add_callback(sceneMsg.kBeforeImportReference, self.callback_open_scene)
        add_callback(sceneMsg.kAfterImportReference, self.reset_mtt)
        add_callback(sceneMsg.kBeforeUnloadReference, self.callback_open_scene)
        add_callback(sceneMsg.kAfterUnloadReference, self.reset_mtt)
        add_callback(sceneMsg.kBeforeLoadReference, self.callback_open_scene)
        add_callback(sceneMsg.kAfterLoadReference, self.reset_mtt)
        add_callback(sceneMsg.kBeforeCreateReference, self.callback_open_scene)
        add_callback(sceneMsg.kAfterCreateReference, self.reset_mtt)

        self.rename_node_callback_id = om.MNodeMessage.addNameChangedCallback(om.MObject(), self.callback_rename_node)
        self.add_node_callback_id = om.MDGMessage.addNodeAddedCallback(self.callback_add_node)
        self.remove_node_callback_id = om.MDGMessage.addNodeRemovedCallback(self.callback_remove_node)

        self.apply_attribute_change_callback()
        self.update_selection_change_callback_state(MTTSettings.value('onlySelectionState'))

    def __remove_callbacks(self):
        """ Remove callbacks """
        if not self.is_callbacks_created:
            return

        sceneMsg.removeCallback(self.new_callback_id)
        for callbackID in self.scene_callbacks_ids:
            sceneMsg.removeCallback(callbackID)
        sceneMsg.removeCallback(self.rename_node_callback_id)
        sceneMsg.removeCallback(self.add_node_callback_id)
        sceneMsg.removeCallback(self.remove_node_callback_id)
        self.clear_all_attribute_callbacks()
        self.update_selection_change_callback_state(False)

    def __remove_filewatch(self):
        self.model.file_watch_remove_all()

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
                MTTSettings.set_value('Viewer/side', 'Left')
            elif delta_x == 0 and delta_y > 0:
                MTTSettings.set_value('Viewer/side', 'Top')
            elif delta_x < 0 and delta_y == 0:
                MTTSettings.set_value('Viewer/side', 'Right')
            elif delta_x == 0 and delta_y < 0:
                MTTSettings.set_value('Viewer/side', 'Bottom')

        MTTSettings.set_value('Viewer/isFloating', is_floating)
        MTTSettings.set_value('Viewer/dockGeometry', dock_geometry)

    def __save_settings(self):
        """ Save settings to QSettings """
        if self.table_view is None:
            return

        MTTSettings.set_value('windowGeometry', self.saveGeometry())
        MTTSettings.set_value('centralGeometry', self.centralWidget().geometry())
        MTTSettings.set_value('columnsSize', self.table_view.horizontalHeader().saveState())

        MTTSettings.set_value('filterRE', self.filter_re_btn.isChecked())
        MTTSettings.set_value('filterType', self.filter_combo.currentIndex())

        self.status_line_ui.save_states()

        # remove temp variable
        MTTSettings.remove('browserFirstStart')

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


def show_ui(toggle=True):
    """ INIT TOOL AND SHOW UI

    @param toggle: destroy and recreate window when is set to False
    """
    # delete UI if exists
    if cmds.control(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME, window=True)

        if toggle:
            return

    check_editor_preferences()

    dialog = MTTView(parent=get_maya_window())
    dialog.show()
