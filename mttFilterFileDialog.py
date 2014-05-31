# Maya import
import maya.cmds as cmds

# Qt import
from PySide.QtGui import *
from PySide.QtCore import *

# Python import
import os.path
from functools import partial

# custom import
from mttConfig import *


SOURCEIMAGES_TAG = '<sourceimages>'


class MTTFileList(QListView):
    """ Extend QListView for navigation """
    def __init__(self, parent=None):
        super(MTTFileList, self).__init__(parent)

        self.filter_line = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.filter_line.setFocus()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.validate_selection()
        elif event.key() == Qt.Key_Backspace:
            self.go_up_directory()
        else:
            super(MTTFileList, self).keyPressEvent(event)

    def validate_selection(self):
        pass

    def go_up_directory(self):
        pass


class MTTBookmarkList(QListWidget):
    """ Extend QListView for navigation """
    def __init__(self, parent=None):
        super(MTTBookmarkList, self).__init__(parent)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_bookmark()
        else:
            super(MTTBookmarkList, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        self.setSelection(QRect(), QItemSelectionModel.Clear)
        super(MTTBookmarkList, self).focusOutEvent(event)

    def delete_bookmark(self):
        pass


class MTTBookmarkItem(QListWidgetItem):
    def __init__(self, parent=None):
        super(MTTBookmarkItem, self).__init__(parent)

        self.root_path = None

    def add_raw_data(self, raw_data):
        name, path = raw_data.split('|')
        self.setText(name)
        self.root_path = path
        self.setToolTip(path)
        self.setStatusTip(path)


class MTTFilterFileDialog(QDialog):
    def __init__(self, define_path=None, define_type=None, parent=MAYA_MAIN_WINDOW, settings=SETTINGS):
        super(MTTFilterFileDialog, self).__init__(parent)

        self.supported_node_type = sorted([nodetype for (nodetype, nice, attr) in SUPPORTED_TYPE])

        self.defined_path = None
        if define_path:
            self.defined_path = define_path if os.path.isdir(define_path) or define_path == SOURCEIMAGES_TAG else None
        self.defined_type = define_type if define_type in self.supported_node_type else None

        self.settings = settings

        self.path_edit = None
        self.filter_reset_btn = None
        self.filter_line = None
        self.parent_folder_btn = None
        self.files_model = None
        self.files_list = None
        self.bookmark_list = None
        self.bookmark_list_selection_model = None
        self.types = None

        # move window to cursor position
        win_geo = self.settings.value('FilterFileDialog/windowGeometry', QRect(0, 0, 400, 300))
        self.setGeometry(win_geo)
        mouse_pos = QCursor.pos()
        mouse_pos.setX(mouse_pos.x() - (win_geo.width() * 0.5))
        self.move(mouse_pos)

        self.__create_ui()

        self.filter_line.setFocus()
        self.on_change_root_path(self.defined_path or SOURCEIMAGES_TAG)

    def __create_ui(self):
        """ Create main UI """
        self.setWindowTitle(CREATE_NODE_TITLE)

        # remove window decoration if path and type is set
        if self.defined_path and self.defined_type:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(1)
        main_layout.setContentsMargins(2, 2, 2, 2)

        # content layout
        content_layout = QVBoxLayout()
        self.files_model = QFileSystemModel()
        self.files_model.setNameFilterDisables(False)
        self.files_list = MTTFileList()
        self.files_list.validate_selection = self.do_validate_selection
        self.files_list.go_up_directory = self.on_go_up_parent
        self.files_list.setAlternatingRowColors(True)
        self.files_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.files_list.doubleClicked.connect(self.on_double_click)
        self.files_list.setModel(self.files_model)

        buttons_layout = QHBoxLayout()

        content_layout.addLayout(self.__create_filter_ui())
        content_layout.addWidget(self.files_list)
        content_layout.addLayout(buttons_layout)
        self.files_list.filter_line = self.filter_line

        if not self.defined_path:
            # path line
            path_layout = QHBoxLayout()
            # bookmark button
            bookmark_btn = QPushButton('')
            bookmark_btn.setFlat(True)
            bookmark_btn.setIcon(QIcon(':/addBookmark.png'))
            bookmark_btn.setToolTip('Bookmark this Folder')
            bookmark_btn.setStatusTip('Bookmark this Folder')
            bookmark_btn.clicked.connect(self.on_add_bookmark)
            # path line edit
            self.path_edit = QLineEdit()
            self.path_edit.editingFinished.connect(self.on_enter_path)
            # parent folder button
            self.parent_folder_btn = QPushButton('')
            self.parent_folder_btn.setFlat(True)
            self.parent_folder_btn.setIcon(QIcon(':/SP_FileDialogToParent.png'))
            self.parent_folder_btn.setToolTip('Parent Directory')
            self.parent_folder_btn.setStatusTip('Parent Directory')
            self.parent_folder_btn.clicked.connect(self.on_go_up_parent)
            # browse button
            browse_btn = QPushButton('')
            browse_btn.setFlat(True)
            browse_btn.setIcon(QIcon(':/navButtonBrowse.png'))
            browse_btn.setToolTip('Browse Directory')
            browse_btn.setStatusTip('Browse Directory')
            browse_btn.clicked.connect(self.on_browse)
            # parent widget and layout
            path_layout.addWidget(bookmark_btn)
            path_layout.addWidget(self.path_edit)
            path_layout.addWidget(self.parent_folder_btn)
            path_layout.addWidget(browse_btn)
            main_layout.addLayout(path_layout)

            # bookmark list
            bookmark_parent_layout = QHBoxLayout()
            bookmark_frame = QFrame()
            bookmark_frame.setFixedWidth(120)
            bookmark_layout = QVBoxLayout()
            bookmark_layout.setSpacing(1)
            bookmark_layout.setContentsMargins(2, 2, 2, 2)
            bookmark_frame.setLayout(bookmark_layout)
            bookmark_frame.setFrameStyle(QFrame.Sunken)
            bookmark_frame.setFrameShape(QFrame.StyledPanel)
            self.bookmark_list = MTTBookmarkList()
            self.bookmark_list.delete_bookmark = self.do_delete_bookmark
            self.bookmark_list.setAlternatingRowColors(True)
            self.bookmark_list.dragEnabled()
            self.bookmark_list.setAcceptDrops(True)
            self.bookmark_list.setDropIndicatorShown(True)
            self.bookmark_list.setDragDropMode(QListView.InternalMove)
            self.bookmark_list_selection_model = self.bookmark_list.selectionModel()
            self.bookmark_list_selection_model.selectionChanged.connect(self.on_select_bookmark)

            bookmark_layout.addWidget(self.bookmark_list)
            bookmark_parent_layout.addWidget(bookmark_frame)
            bookmark_parent_layout.addLayout(content_layout)
            main_layout.addLayout(bookmark_parent_layout)

            self.do_populate_bookmarks()

        else:
            main_layout.addLayout(content_layout)

        if not self.defined_type:
            # type layout
            self.types = QComboBox()
            self.types.addItems(self.supported_node_type)
            self.types.currentIndexChanged.connect(self.on_node_type_changed)
            if cmds.optionVar(exists='MTT_lastNodeType'):
                last = cmds.optionVar(query='MTT_lastNodeType')
                if last in self.supported_node_type:
                    self.types.setCurrentIndex(self.supported_node_type.index(last))
            buttons_layout.addWidget(self.types)

        if not self.defined_path or not self.defined_type:
            create_btn = QPushButton('C&reate')
            create_btn.clicked.connect(self.accept)
            cancel_btn = QPushButton('&Cancel')
            cancel_btn.clicked.connect(self.reject)

            buttons_layout.addStretch()
            buttons_layout.addWidget(create_btn)
            buttons_layout.addWidget(cancel_btn)

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

        self.filter_line = QLineEdit()
        self.filter_line.setPlaceholderText('Enter filter string here')
        self.filter_line.textChanged.connect(self.on_filter_change_text)

        completer = QCompleter(self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setModel(QStringListModel([], self))
        self.filter_line.setCompleter(completer)

        filter_layout.addWidget(self.filter_reset_btn)
        filter_layout.addWidget(self.filter_line)

        return filter_layout

    def on_filter_set_text(self, text):
        """ Set text in filter field """
        self.filter_line.setText(text)

    def on_filter_change_text(self, text):
        """ Apply filter string """
        if len(text):
            icon = QIcon(':/filtersOn.png')
            self.filter_reset_btn.setIcon(icon)
        else:
            icon = QIcon(':/filtersOff.png')
            self.filter_reset_btn.setIcon(icon)

        self.files_model.setNameFilters(['*%s*' % item.strip() for item in text.split(',') if item.strip()])

    def on_node_type_changed(self, index):
        cmds.optionVar(sv=['MTT_lastNodeType', self.supported_node_type[index]])

    def on_double_click(self, index):
        current_item = self.files_model.filePath(index)
        if os.path.isdir(current_item):
            self.on_change_root_path(current_item)
        elif os.path.isfile(current_item):
            self.accept()

    def on_change_root_path(self, current_path):
        if current_path == SOURCEIMAGES_TAG:
            current_path = os.path.join(cmds.workspace(query=True, rootDirectory=True), cmds.workspace(fileRuleEntry='sourceImages'))

        self.files_model.setRootPath(current_path)
        self.files_list.setRootIndex(self.files_model.index(current_path))
        if self.path_edit:
            self.path_edit.setText(current_path)

        if self.parent_folder_btn:
            current_dir = QDir(current_path)
            self.parent_folder_btn.setEnabled(current_dir.cdUp())

    def on_go_up_parent(self):
        current_path = QDir(self.files_model.rootPath())
        current_path.cdUp()
        self.on_change_root_path(current_path.absolutePath())

    def on_enter_path(self):
        new_path = self.path_edit.text()
        if os.path.isdir(new_path):
            self.on_change_root_path(new_path)
        else:
            self.path_edit.setText(self.files_model.rootPath())

    def on_browse(self):
        current_path = self.files_model.rootPath()
        file_dialog = QFileDialog(self, 'Select a Folder', current_path)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.ShowDirsOnly)
        if file_dialog.exec_():
            self.on_change_root_path(file_dialog.selectedFiles()[0])

    def on_select_bookmark(self, selected, deselected):
        current_item = selected.indexes()
        if current_item:
            self.on_change_root_path(self.bookmark_list.selectedItems()[0].root_path)

    def on_add_bookmark(self):
        current_path = self.files_model.rootPath()
        self.on_add_bookmark_item('%s|%s' % (os.path.basename(current_path), current_path))

    def on_add_bookmark_item(self, item):
        if item == '':
            return

        current_item = MTTBookmarkItem()
        current_item.add_raw_data(item)
        current_item.setSizeHint(QSize(40, 25))
        current_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        self.bookmark_list.addItem(current_item)

    def do_delete_bookmark(self):
        current_item = self.bookmark_list.selectedItems()
        if current_item:
            item_row = self.bookmark_list.row(current_item[0])
            self.bookmark_list.takeItem(item_row)
            del current_item[0]

    def do_save_bookmark(self):
        if not self.bookmark_list:
            return

        row_count = self.bookmark_list.count()
        ordered_list = list()

        for i in range(row_count):
            item = self.bookmark_list.item(i)
            name = item.text().replace(',', '_').replace('|', '_')
            path = item.root_path
            if name != 'sourceimages':
                ordered_list.append('%s|%s' % (name, path))

        self.settings.setValue('FilterFileDialog/bookmarks', ','.join(ordered_list))

    def do_populate_bookmarks(self):
        bookmarks = ['sourceimages|%s' % SOURCEIMAGES_TAG]
        bookmarks.extend(self.settings.value('FilterFileDialog/bookmarks', '').split(','))

        for bm in bookmarks:
            self.on_add_bookmark_item(bm)

    def do_validate_selection(self):
        selection = self.files_list.selectedIndexes()
        if len(selection) == 1:
            current_path = self.files_model.filePath(selection[0])
            if os.path.isdir(current_path):
                self.on_change_root_path(current_path)
                return
        self.accept()

    def get_selected_files(self):
        selected_items = list()
        for item_index in self.files_list.selectedIndexes():
            current_path = self.files_model.filePath(item_index)
            if os.path.isfile(current_path):
                selected_items.append(current_path)
        return selected_items

    def get_node_type(self):
        if self.types:
            node_type = self.types.currentText()
        else:
            node_type = self.defined_type
        return node_type

    def event(self, e):
        if e.type() == QEvent.Hide or e.type() == QEvent.Close:
            self.settings.setValue('FilterFileDialog/windowGeometry', self.geometry())
            self.do_save_bookmark()
        return super(MTTFilterFileDialog, self).event(e)

    def closeEvent(self, event):
        event.accept()


def create_nodes(define_path=None, define_type=None):
    dialog = MTTFilterFileDialog(define_path=define_path, define_type=define_type)
    if dialog.exec_():
        files = dialog.get_selected_files()
        node_type = dialog.get_node_type()
        node_attr = [attr for (nodetype, nice, attr) in SUPPORTED_TYPE if node_type == nodetype][0]

        current_selection = cmds.ls(selection=True)
        SETTINGS.setValue('suspendRenameCallbacks', True)

        nodes = list()
        for f in files:
            node_name = os.path.basename(f).rsplit('.')[0]
            node_name = node_name if not node_name[0].isdigit() else '_%s' % node_name
            new_node = cmds.shadingNode(node_type, name=node_name, asTexture=True)

            if get_settings_bool_value(SETTINGS.value('forceRelativePath', DEFAULT_FORCE_RELATIVE_PATH)):
                f = convert_to_relative_path(f)
            cmds.setAttr('%s.%s' % (new_node, node_attr), f, type='string')

            if IMPORT_POLICY:
                try:
                    exec IMPORT_POLICY
                    exec_import_policy(current_selection, node_name, os.path.basename(f))
                except:
                    db_output('Fail to run import policy.', msg_type='error')
            nodes.append(new_node)

        SETTINGS.setValue('suspendRenameCallbacks', False)
        SETTINGS.remove('suspendRenameCallbacks')
        if nodes:
            cmds.select(nodes, replace=True)

    dialog.deleteLater()
