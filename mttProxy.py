# Qt import
from PySide.QtCore import Qt
from PySide.QtGui import QSortFilterProxyModel

# Python import
import re

# custom import
from mttConfig import *


class MTTProxy(QSortFilterProxyModel):
    def __init__(self, parent=None, settings=None):
        super(MTTProxy, self).__init__(parent)
        self.settings = settings
        self.selected_texture_nodes = None

    def filterAcceptsRow(self, source_row, source_parent):
        nodes_str = self.settings.value('pinnedNode')
        if nodes_str:
            nodes = nodes_str.split(';')
            source_id = self.sourceModel().index(source_row, NODE_NAME, source_parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value not in nodes:
                return False

        result = super(MTTProxy, self).filterAcceptsRow(source_row, source_parent)

        if not result:
            return False

        if self.selected_texture_nodes is not None:
            source_id = self.sourceModel().index(source_row, NODE_NAME, source_parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value not in self.selected_texture_nodes:
                return False

        if get_settings_bool_value(self.settings.value('onlyWritableState', DEFAULT_ONLY_WRITABLE)):
            source_id = self.sourceModel().index(source_row, FILE_STATE, source_parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value != 1:
                return False

        if get_settings_bool_value(self.settings.value('showReferenceState', DEFAULT_SHOW_REFERENCE)):
            source_id = self.sourceModel().index(source_row, NODE_REFERENCE, source_parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value == 1:
                return False

        if get_settings_bool_value(self.settings.value('showWrongNameState', DEFAULT_SHOW_WRONG_NAME)):
            source_node_id = self.sourceModel().index(source_row, NODE_NAME, source_parent)
            source_file_id = self.sourceModel().index(source_row, NODE_FILE, source_parent)
            node_name = self.sourceModel().data(source_node_id, Qt.DisplayRole)
            file_name = os.path.splitext(os.path.basename(self.sourceModel().data(source_file_id, Qt.DisplayRole)))[0]
            if re.split('[0-9]*$', node_name.rsplit(':')[-1])[0] == re.split('[0-9]*$', file_name)[0]:
                return False

        if get_settings_bool_value(self.settings.value('filterInstances', DEFAULT_FILTER_INSTANCES)):
            source_file_id = self.sourceModel().index(source_row, NODE_FILE, source_parent)
            file_path = os.path.normpath(self.sourceModel().data(source_file_id, Qt.DisplayRole).lower())
            filterer_instances = cmds.optionVar(query='filtered_instances').split(';')
            if file_path not in filterer_instances:
                filterer_instances.append(file_path)
                cmds.optionVar(stringValue=('filtered_instances', ';'.join(filterer_instances)))
            else:
                return False

        return True

    def lessThan(self, left_id, right_id):
        left_var = left_id.data(Qt.DisplayRole)
        right_var = right_id.data(Qt.DisplayRole)

        return left_var < right_var

    def sort(self, column_id, sort_order):
        # ignore lessThan sort for performance purpose on large list
        self.sourceModel().sort(column_id, sort_order)