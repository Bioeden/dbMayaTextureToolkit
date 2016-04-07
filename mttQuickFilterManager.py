# Qt import
from PySide.QtGui import *
from PySide.QtCore import *

# custom import
from mttCmdUi import get_maya_window
from mttConfig import MTTSettings, WINDOW_TITLE, WINDOW_ICON


class MTTQuickFilterManager(QDialog):
    def __init__(self, parent=get_maya_window()):
        super(MTTQuickFilterManager, self).__init__(parent)

        # create UI
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(4, 4, 4, 4)

        list_layout = QHBoxLayout(self)
        self.quick_filter_wildcard_ui = _QuickFilterUI('Wildcard')
        list_layout.addLayout(self.quick_filter_wildcard_ui)

        self.quick_filter_regex_ui = _QuickFilterUI('RegularExpression')
        list_layout.addLayout(self.quick_filter_regex_ui)

        main_layout.addLayout(list_layout)

        main_layout.addSpacing(2)

        buttons_layout = QHBoxLayout(self)
        save_button = QPushButton('&Save')
        save_button.clicked.connect(self.accept)
        buttons_layout.addWidget(save_button)

        cancel_button = QPushButton('&Cancel')
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        main_layout.addLayout(buttons_layout)

        # populate lists
        items_str = MTTSettings.value('filterQuickWordsWildcard')
        if items_str:
            self.quick_filter_wildcard_ui.populate(
                quick_filter_words=items_str.split(';;'))

        items_str = MTTSettings.value('filterQuickWordsRegExp')
        if items_str:
            self.quick_filter_regex_ui.populate(
                quick_filter_words=items_str.split(';;'))

        # adjust UI
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon(WINDOW_ICON))
        self.setModal(True)
        self.resize(300, 200)

    def get_lists(self):
        return (
            self.quick_filter_wildcard_ui.get_list_content(),
            self.quick_filter_regex_ui.get_list_content())


class _QuickFilterUI(QVBoxLayout):
    def __init__(self, title, parent=None):
        super(_QuickFilterUI, self).__init__(parent)

        button_size = 24

        label_title = QLabel('<b>%s</b>' % title)
        label_title.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)
        label_title.setFrameStyle(QFrame.Panel | QFrame.Raised)
        label_title.setMinimumHeight(20)
        self.addWidget(label_title)

        self.quick_filter_list = QListView()
        self.quick_filter_list.setMinimumWidth(40)
        self.quick_filter_list.dragEnabled()
        self.quick_filter_list.setAcceptDrops(True)
        self.quick_filter_list.setDropIndicatorShown(True)
        self.quick_filter_list.setDragDropMode(QListView.InternalMove)
        self.quick_filter_model = QStandardItemModel(self.quick_filter_list)
        self.quick_filter_list.setModel(self.quick_filter_model)

        self.addWidget(self.quick_filter_list)

        buttons_layout = QHBoxLayout()

        add_button = QPushButton('+')
        add_button.setMinimumWidth(button_size)
        add_button.clicked.connect(self.addItem)
        buttons_layout.addWidget(add_button)

        del_button = QPushButton('-')
        del_button.setMinimumWidth(button_size)
        del_button.clicked.connect(self.removeItem)
        buttons_layout.addWidget(del_button)

        self.addLayout(buttons_layout)

    def addItem(self, item_name=''):
        if not item_name:
            item_name = 'new item'
        item = QStandardItem(item_name)
        item.setDropEnabled(False)
        self.quick_filter_model.appendRow(item)

    def removeItem(self):
        sel = self.quick_filter_list.selectedIndexes()
        if sel:
            self.quick_filter_model.removeRow(sel[0].row())

    def populate(self, quick_filter_words=None):
        for word in quick_filter_words or []:
            self.addItem(item_name=word)

    def get_list_content(self):
        row_count = self.quick_filter_model.rowCount()
        items = []
        for idx in range(row_count):
            item = self.quick_filter_model.index(idx, 0).data()
            if item:
                items.append(item)
        return items
