# Python import
import os
# PySide import
from PySide.QtCore import Qt, Signal
from PySide.QtGui import (QHBoxLayout, QLabel)
# Maya import
from maya import cmds
# Custom import
from mttConfig import MTTSettings
from mttCustomWidget import StatusCollapsibleLayout, StatusScrollArea
import mttFilterFileDialog
import mttCmd
import mttCmdUi


class MTTStatusLine(QHBoxLayout):
    """ Create custom toolbar with collapse Maya Status Line behavior """

    viewerToggled = Signal()
    filterSelectionToggled = Signal(bool)
    pinModeToggled = Signal(bool)
    externalVizToggled = Signal()

    def __init__(self, settings_menu, model, proxy):
        super(MTTStatusLine, self).__init__()

        self.settings_menu = settings_menu
        self.model = model
        self.proxy = proxy

        self.__create_ui()
        self.__init_ui()

    def __create_ui(self):
        # FILTERS
        scroll_area = StatusScrollArea()
        scroll_area.add_widget(self._create_filter_group())
        scroll_area.add_widget(self._create_visibility_group())
        scroll_area.add_widget(self._create_folder_group())
        scroll_area.add_widget(self._create_auto_group())
        scroll_area.add_widget(self._create_mtt_tools_group())
        scroll_area.add_widget(self._create_maya_tools_group())
        user_grp = self._create_user_group()
        if user_grp:
            scroll_area.add_widget(user_grp)
        self.addWidget(scroll_area)

        # STATS information
        self.stat_info = QLabel()
        self.stat_info.setAlignment(Qt.AlignCenter | Qt.AlignRight)
        self.stat_info.setText('0 File | 0/0 Node')
        self.stat_info.setToolTip(
            'number of files | number of nodes shown / total number of nodes')
        self.addWidget(self.stat_info)

        # SETTINGS button
        self.info_btn = mttCmdUi.create_status_button(
            ':/tb_config', 'Settings', None, False)
        self.info_btn.setMenu(self.settings_menu)
        self.addWidget(self.info_btn)

    def __init_ui(self):
        self.setContentsMargins(0, 0, 0, 0)
        self.setAlignment(Qt.AlignLeft)

        # FILTER GROUP
        self.selection_btn.setChecked(MTTSettings.value('onlySelectionState'))
        self.writable_btn.setChecked(MTTSettings.value('onlyWritableState'))
        self.reference_btn.setChecked(MTTSettings.value('showReferenceState'))
        self.wrong_name_btn.setChecked(MTTSettings.value('showWrongNameState'))
        self.filter_instances_btn.setChecked(
            MTTSettings.value('filterInstances'))

        self.filter_grp.set_current_state(MTTSettings.value('filterGroup'))

        # VISIBILITY GROUP
        self.wrong_name_visibility_btn.setChecked(
            MTTSettings.value('vizWrongNameState'))
        self.wrong_path_visibility_btn.setChecked(
            MTTSettings.value('vizWrongPathState'))
        self.external_visibility_btn.setChecked(
            MTTSettings.value('vizExternalState'))
        self.basename_visibility_btn.setChecked(
            MTTSettings.value('showBasenameState'))
        self.namespace_visibility_btn.setChecked(
            not MTTSettings.value('showNamespaceState'))

        self.visibility_grp.set_current_state(MTTSettings.value('visibilityGroup'))

        # FOLDER GROUP
        self.folder_grp.set_current_state(MTTSettings.value('folderGroup'))

        # AUTO GROUP
        self.auto_reload_btn.setChecked(MTTSettings.value('autoReload'))
        self.auto_select_btn.setChecked(MTTSettings.value('autoSelect'))
        self.auto_rename_btn.setChecked(MTTSettings.value('autoRename'))

        self.auto_grp.set_current_state(MTTSettings.value('autoGroup'))

        # MTT TOOLS
        self.viewer_btn.setChecked(MTTSettings.value('viewerState'))

        self.tool_grp.set_current_state(MTTSettings.value('toolGroup', 1))

        # MAYA TOOLS SHORTCUT
        self.maya_grp.set_current_state(MTTSettings.value('mayaGroup', 1))

    def _create_filter_group(self):
        # create toolbar buttons
        self.selection_btn = mttCmdUi.create_status_button(
            ':/tb_onlySelection',
            'Show textures applied to current selection',
            self.on_show_only_selection,
            True)
        self.writable_btn = mttCmdUi.create_status_button(
            ':/tb_onlyWritable',
            'Hide read-only textures',
            self.on_show_only_writable,
            True)
        self.reference_btn = mttCmdUi.create_status_button(
            ':/tb_onlyReference',
            'Hide references',
            self.on_show_reference,
            True)
        self.pin_btn = mttCmdUi.create_status_button(
            ':/tb_onlyPinned',
            'Pin textures',
            self.on_pin_nodes,
            True)
        self.wrong_name_btn = mttCmdUi.create_status_button(
            ':/tb_onlyWrongName',
            'Show Node name clashing with Texture name',
            self.on_show_wrong_name,
            True)
        self.filter_instances_btn = mttCmdUi.create_status_button(
            ':/tb_hideInstances',
            'Show only one instance per file',
            self.on_filter_instances,
            True)

        # sort toolbar buttons
        self.filter_grp = StatusCollapsibleLayout(
            section_name='Show/Hide the filter icons')
        self.filter_grp.add_button(self.pin_btn)
        self.filter_grp.add_button(self.selection_btn)
        self.filter_grp.add_button(self.reference_btn)
        self.filter_grp.add_button(self.writable_btn)
        self.filter_grp.add_button(self.wrong_name_btn)
        self.filter_grp.add_button(self.filter_instances_btn)

        return self.filter_grp

    def _create_visibility_group(self):
        # create toolbar buttons
        self.wrong_name_visibility_btn = mttCmdUi.create_status_button(
            ':/tb_vizWrongName',
            'Highlight Node name clashing with Texture name',
            self.on_wrong_name_visibility,
            True)

        self.external_visibility_btn = mttCmdUi.create_status_button(
            ':/tb_vizExternal',
            'Highlight Texture path that comes from outside current workspace',
            self.on_external_visibility,
            True)

        self.wrong_path_visibility_btn = mttCmdUi.create_status_button(
            ':/tb_vizWrongPath',
            'Highlight Texture path clashing with user defined path pattern',
            self.on_wrong_path_visibility,
            True)

        self.basename_visibility_btn = mttCmdUi.create_status_button(
            ':/tb_vizBasename',
            'Show files texture name only',
            self.on_basename_visibility,
            True)

        self.namespace_visibility_btn = mttCmdUi.create_status_button(
            ':/tb_vizNamespace',
            'Toggle namespace visibility',
            self.on_namespace_visibility,
            True)

        # sort toolbar buttons
        self.visibility_grp = StatusCollapsibleLayout(
            section_name='Show/Hide the visibility icons')
        self.visibility_grp.add_button(self.namespace_visibility_btn)
        self.visibility_grp.add_button(self.wrong_name_visibility_btn)
        self.visibility_grp.add_button(self.external_visibility_btn)
        self.visibility_grp.add_button(self.wrong_path_visibility_btn)
        self.visibility_grp.add_button(self.basename_visibility_btn)

        return self.visibility_grp

    def _create_folder_group(self):
        self.folder_grp = StatusCollapsibleLayout(
            section_name='Show/Hide the folder icons')

        # create toolbar buttons
        self.folder_grp.add_button(mttCmdUi.create_status_button(
            ':/tb_folderMap',
            'Open sourceimages folder',
            self.on_open_sourceimages_folder,
            False)
        )
        self.folder_grp.add_button(mttCmdUi.create_status_button(
            ':/tb_folderSrc',
            'Open source folder',
            self.on_open_source_folder,
            False)
        )

        return self.folder_grp

    def _create_auto_group(self):
        # create toolbar buttons
        self.auto_reload_btn = mttCmdUi.create_status_button(
            ':/tb_toolbar_autoReload',
            'Auto Reload Textures',
            self.on_auto_reload,
            True)

        self.auto_select_btn = mttCmdUi.create_status_button(
            ':/tb_toolbar_autoSelect',
            'Auto Select Textures Node',
            self.on_auto_select,
            True)

        self.auto_rename_btn = mttCmdUi.create_status_button(
            ':/tb_toolbar_autoRename',
            'Auto Rename Textures Node',
            self.on_auto_rename,
            True)

        # sort toolbar buttons
        self.auto_grp = StatusCollapsibleLayout(
            section_name='Show/Hide the auto actions icons')
        self.auto_grp.add_button(self.auto_reload_btn)
        self.auto_grp.add_button(self.auto_select_btn)
        self.auto_grp.add_button(self.auto_rename_btn)

        return self.auto_grp

    def _create_mtt_tools_group(self):
        # create toolbar buttons
        self.viewer_btn = mttCmdUi.create_status_button(
            ':/tb_Viewer',
            'Show/Hide Viewer',
            self.on_toggle_viewer,
            False)

        create_node_btn = mttCmdUi.create_status_button(
            ':/tb_toolCreateNode',
            'Create Node',
            self.on_create_node,
            False)

        # sort toolbar buttons
        self.tool_grp = StatusCollapsibleLayout(
            section_name='Show/Hide the tools icons')
        self.tool_grp.add_button(self.viewer_btn)
        self.tool_grp.add_button(create_node_btn)

        return self.tool_grp

    def _create_maya_tools_group(self):
        # sort toolbar buttons
        self.maya_grp = StatusCollapsibleLayout(
            section_name='Show/Hide the Maya tools icons')

        # create toolbar buttons
        self.maya_grp.add_button(mttCmdUi.create_status_button(
            ':/tb_Hypershade',
            'Hypershade',
            self.on_open_hypershade,
            False)
        )
        self.maya_grp.add_button(mttCmdUi.create_status_button(
            ':/tb_NodeEditor',
            'Node Editor',
            self.on_open_node_editor,
            False)
        )
        self.maya_grp.add_button(mttCmdUi.create_status_button(
            ':/tb_UVEditor',
            'UV Texture Editor',
            self.on_open_uv_editor,
            False)
        )

        return self.maya_grp

    def _create_user_group(self):
        if MTTSettings.CUSTOM_BUTTONS:
            self.custom_grp = StatusCollapsibleLayout(
                section_name='Show/Hide custom tools')

            for btnData in MTTSettings.CUSTOM_BUTTONS:
                self.custom_grp.add_button(mttCmdUi.create_status_button(
                    btnData[0],
                    btnData[1],
                    eval(btnData[2]),
                    False)
                )

            return self.custom_grp

    def _set_filter_value(self, key, value):
        self.model.layoutAboutToBeChanged.emit()

        MTTSettings.set_value(key, value)
        cmds.optionVar(stringValue=('filtered_instances', ''))

        self.model.layoutChanged.emit()
        self.update_node_file_count()

    def on_show_only_selection(self):
        """ Filter nodes from current selection """
        state = self.selection_btn.isChecked()
        MTTSettings.set_value('onlySelectionState', state)
        self.filterSelectionToggled.emit(state)

    def on_show_only_writable(self):
        """ Filter nodes with their file state """
        self._set_filter_value(
            'onlyWritableState', self.writable_btn.isChecked())

    def on_show_reference(self):
        """ Filter referenced nodes """
        self._set_filter_value(
            'showReferenceState', self.reference_btn.isChecked())

    def on_pin_nodes(self):
        """ Filter pinned nodes """
        self.pinModeToggled.emit(self.pin_btn.isChecked())

    def on_show_wrong_name(self):
        """ Filter node with the same name as texture """
        self._set_filter_value(
            'showWrongNameState', self.wrong_name_btn.isChecked())

    def on_wrong_name_visibility(self):
        """ Highlight node with the same name as texture """
        self._set_filter_value(
            'vizWrongNameState', self.wrong_name_visibility_btn.isChecked())

    def on_wrong_path_visibility(self):
        """ Highlight Texture path clashing with user defined path pattern """
        self._set_filter_value(
            'vizWrongPathState', self.wrong_path_visibility_btn.isChecked())

    def on_external_visibility(self):
        """ Highlight Texture path that comes from outside current workspace """
        state = self.external_visibility_btn.isChecked()
        self._set_filter_value('vizExternalState', state)
        if state:
            self.externalVizToggled.emit()

    def on_basename_visibility(self):
        """ Filter file path """
        self._set_filter_value(
            'showBasenameState', self.basename_visibility_btn.isChecked())

    def on_namespace_visibility(self):
        """ Filter namespace name """
        self._set_filter_value(
            'showNamespaceState', not self.namespace_visibility_btn.isChecked())

    def on_filter_instances(self):
        """ Show only one instance per file """
        self._set_filter_value(
            'filterInstances', self.filter_instances_btn.isChecked())

    def on_open_sourceimages_folder(self):
        """ Open sourceimages folder """
        folder_path = self.model.get_sourceimages_path()
        if os.path.isdir(folder_path):
            os.startfile(folder_path)
            # launchImageEditor can be an alternative
            # cmds.launchImageEditor(viewImageFile=directory)

    @staticmethod
    def on_open_source_folder():
        """ Open source folder """
        folder_path = mttCmd.get_texture_source_folder()
        if os.path.isdir(folder_path):
            os.startfile(folder_path)

    @staticmethod
    def on_auto_reload():
        state = MTTSettings.value('autoReload')
        MTTSettings.set_value('autoReload', not state)

    @staticmethod
    def on_auto_select():
        state = MTTSettings.value('autoSelect')
        MTTSettings.set_value('autoSelect', not state)

    @staticmethod
    def on_auto_rename():
        state = MTTSettings.value('autoRename')
        MTTSettings.set_value('autoRename', not state)

    def on_toggle_viewer(self):
        self.viewerToggled.emit()

    @staticmethod
    def on_create_node():
        mttFilterFileDialog.create_nodes()

    @staticmethod
    def on_open_hypershade():
        """ Open Maya Hypershade """
        cmds.HypershadeWindow()

    @staticmethod
    def on_open_node_editor():
        """ Open Maya Hypershade """
        cmds.NodeEditorWindow()

    @staticmethod
    def on_open_uv_editor():
        """ Open Maya UV Texture Editor """
        cmds.TextureViewWindow()

    def update_node_file_count(self):
        file_count = self.model.get_file_count()
        file_str = 'file{}'.format(['', 's'][file_count > 1])

        node_shown_count = self.proxy.rowCount()

        node_count = self.model.get_node_count()
        node_str = 'node' if node_count < 1 else 'nodes'

        self.stat_info.setText('%d %s | %d/%d %s' % (
            file_count, file_str, node_shown_count, node_count, node_str))

    def save_states(self):
        # buttons states
        MTTSettings.set_value('onlySelectionState', self.selection_btn.isChecked())
        MTTSettings.set_value('onlyWritableState', self.writable_btn.isChecked())
        MTTSettings.set_value('showReferenceState', self.reference_btn.isChecked())
        MTTSettings.set_value('showWrongNameState', self.wrong_name_btn.isChecked())
        MTTSettings.remove('pinnedNode')
        MTTSettings.set_value('vizWrongNameState', self.wrong_name_visibility_btn.isChecked())
        MTTSettings.set_value('showBasenameState', self.basename_visibility_btn.isChecked())
        MTTSettings.set_value('filterInstances', self.filter_instances_btn.isChecked())

        # groups states
        MTTSettings.set_value('filterGroup', self.filter_grp.current_state())
        MTTSettings.set_value('visibilityGroup', self.visibility_grp.current_state())
        MTTSettings.set_value('folderGroup', self.folder_grp.current_state())
        MTTSettings.set_value('autoGroup', self.auto_grp.current_state())
        MTTSettings.set_value('toolGroup', self.tool_grp.current_state())
        MTTSettings.set_value('mayaGroup', self.maya_grp.current_state())
