# Python import
import re
import os
# PySide import
from PySide.QtCore import Qt
from PySide.QtGui import QSortFilterProxyModel
# Maya import
from maya import cmds
# custom import
from mttConfig import (
    MTTSettings, NODE_NAME, NODE_REFERENCE, FILE_STATE, NODE_FILE)


class MTTProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(MTTProxy, self).__init__(parent)
        self.selected_texture_nodes = None

    def filterAcceptsRow(self, row, parent):
        nodes_str = MTTSettings.value('pinnedNode')
        if nodes_str:
            nodes = nodes_str.split(';')
            source_id = self.sourceModel().index(row, NODE_NAME, parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value not in nodes:
                return False

        result = super(MTTProxy, self).filterAcceptsRow(row, parent)

        if not result:
            return False

        if self.selected_texture_nodes is not None:
            source_id = self.sourceModel().index(row, NODE_NAME, parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value not in self.selected_texture_nodes:
                return False

        if MTTSettings.value('onlyWritableState'):
            source_id = self.sourceModel().index(row, FILE_STATE, parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value != 1:
                return False

        if MTTSettings.value('showReferenceState'):
            source_id = self.sourceModel().index(row, NODE_REFERENCE, parent)
            value = self.sourceModel().data(source_id, Qt.DisplayRole)
            if value == 1:
                return False

        if MTTSettings.value('showWrongNameState'):
            source_node_id = self.sourceModel().index(row, NODE_NAME, parent)
            source_file_id = self.sourceModel().index(row, NODE_FILE, parent)
            node_name = self.sourceModel().data(source_node_id, Qt.DisplayRole)
            file_path = self.sourceModel().data(source_file_id, Qt.DisplayRole)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            node_split = re.split('[0-9]*$', node_name.rsplit(':')[-1])[0]
            file_split = re.split('[0-9]*$', file_name)[0]
            if node_split == file_split:
                return False

        if MTTSettings.value('filterInstances'):
            source_file_id = self.sourceModel().index(row, NODE_FILE, parent)
            file_path = self.sourceModel().data(source_file_id, Qt.DisplayRole)
            norm_path = os.path.normpath(file_path.lower())
            instances = cmds.optionVar(query='filtered_instances').split(';')
            if norm_path not in instances:
                instances.append(norm_path)
                cmds.optionVar(stringValue=(
                    'filtered_instances', ';'.join(instances)))
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
