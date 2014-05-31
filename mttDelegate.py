# Maya import
from maya.cmds import workspace, showWindow

# Qt import
from PySide.QtCore import *
from PySide.QtGui import *

# Python import
import re
import os.path

# custom import
from mttConfig import *


class MTTDelegate(QStyledItemDelegate):
    """ MTT Delegate, provide editors and look & feel	"""

    def __init__(self, settings=None):
        super(MTTDelegate, self).__init__()
        self.settings = settings

    def paint(self, painter, option, index):
        """ Change data appearance """
        # if index.row() % 2 == 0

        if index.column() == NODE_REFERENCE:
            # NODE_REFERENCE -------------------------------------------------------------------------------------------------

            # backup painter
            painter.save()

            # paint background
            palette = QApplication.palette()
            if option.state & QStyle.State_Selected:
                bg_color = palette.highlight().color()
            else:
                bg_color = Qt.transparent
            painter.fillRect(option.rect, bg_color)

            # paint
            value = float(index.model().data(index))
            if value == 0.0:
                painter.setPen((Qt.black if option.state & QStyle.State_Selected else Qt.darkGray))
                painter.setBrush(Qt.NoBrush)
                mid_size = 3.0
            else:
                painter.setPen(Qt.darkCyan)
                painter.setBrush(Qt.cyan)
                mid_size = 4.0

            h_center = round(option.rect.x() + (option.rect.width() * .5))
            v_center = round(option.rect.y() + (option.rect.height() * .5))
            losange = QPolygonF()
            losange.append(QPointF(h_center, v_center - mid_size))
            losange.append(QPointF(h_center - mid_size, v_center))
            losange.append(QPointF(h_center, v_center + mid_size))
            losange.append(QPointF(h_center + mid_size, v_center))

            painter.drawPolygon(losange)

            # restore painter
            painter.restore()
        elif index.column() == FILE_STATE:
            # FILE_STATE -----------------------------------------------------------------------------------------------------

            # backup painter
            painter.save()

            # paint background
            palette = QApplication.palette()
            bg_color = (palette.highlight().color() if option.state & QStyle.State_Selected else Qt.transparent)
            painter.fillRect(option.rect, bg_color)

            # paint circle
            value = index.model().data(index)

            pen_color = [
                Qt.darkRed,
                (Qt.black if option.state & QStyle.State_Selected else Qt.gray),
                Qt.darkGreen][value + 1]
            brush_color = [Qt.red, Qt.NoBrush, Qt.green][value + 1]

            painter.setPen(pen_color)
            painter.setBrush(brush_color)

            h_center = round(option.rect.x() + (option.rect.width() * .5))
            v_center = round(option.rect.y() + (option.rect.height() * .5))
            center = QPointF(h_center, v_center)

            painter.drawEllipse(center, 3.0, 3.0)

            # restore painter
            painter.restore()
        elif index.column() == NODE_NAME:
            # NODE_NAME ------------------------------------------------------------------------------------------------------
            text = index.model().data(index, Qt.DisplayRole)
            palette = QApplication.palette()
            bg_color = (palette.highlight().color() if option.state & QStyle.State_Selected else Qt.transparent)
            txt_color = (palette.highlightedText().color() if option.state & QStyle.State_Selected else palette.text().color())

            if get_settings_bool_value(self.settings.value('vizWrongNameState', DEFAULT_VIZ_WRONG_NAME)) \
                and not get_settings_bool_value(self.settings.value('showWrongNameState', DEFAULT_SHOW_WRONG_NAME)):
                file_name = os.path.splitext(os.path.basename(index.model().data(index.sibling(index.row(), NODE_FILE), Qt.DisplayRole)))[0]
                if not re.split('[0-9]*$', text.rsplit(':')[-1])[0] == re.split('[0-9]*$', file_name)[0]:
                    bg_color = QBrush((Qt.red if option.state & QStyle.State_Selected else Qt.darkRed), Qt.Dense4Pattern)

            if not get_settings_bool_value(self.settings.value('showNamespaceState', DEFAULT_SHOW_NAMESPACE)):
                splits = text.split(':')
                text = splits[len(splits) > 1]

            painter.save()
            painter.fillRect(option.rect, bg_color)
            painter.setPen(txt_color)
            QApplication.style().drawItemText(painter, option.rect, Qt.AlignLeft | Qt.AlignVCenter, palette, True, text)
            painter.restore()
        elif index.column() == NODE_FILE:
            # NODE_FILE ------------------------------------------------------------------------------------------------------
            text = index.model().data(index, Qt.DisplayRole)
            if get_settings_bool_value(self.settings.value('showBasenameState', DEFAULT_SHOW_BASENAME)):
                text = os.path.basename(text)
            elif not get_settings_bool_value(self.settings.value('showRealAttributeValue', DEFAULT_SHOW_REAL_ATTRIBUTE)):
                if not text.startswith('\\'):
                    text = os.path.normpath(workspace(projectPath=text))
            palette = QApplication.palette()
            bg_color = (palette.highlight().color() if option.state & QStyle.State_Selected else Qt.transparent)
            txt_color = (palette.highlightedText().color() if option.state & QStyle.State_Selected else palette.text().color())

            painter.save()
            painter.fillRect(option.rect, bg_color)
            painter.setPen(txt_color)
            QApplication.style().drawItemText(painter, option.rect, Qt.AlignLeft | Qt.AlignVCenter, palette, True, text)
            painter.restore()
        else:
            QStyledItemDelegate.paint(self, painter, option, index)

    def editorEvent(self, event, model, option, index):
        """ prevent rename when pressing on keys """
        if isinstance(event, QKeyEvent):
            return event.key() != Qt.Key_F2

        return False

    def createEditor(self, parent, option, index):
        """ Create editors """
        if index.column() == NODE_NAME:
            rename_editor = QLineEdit(parent)
            rename_editor.setValidator(QRegExpValidator(QRegExp(r'[a-zA-Z_]+[a-zA-Z0-9_:]*'), self))
            return rename_editor
        elif index.column() == NODE_FILE:
            #filename_editor = QLineEdit(parent)
            filename_editor = PathEditor(parent, index, self.settings)
            filename_editor.editingFinished.connect(self.commit_and_close_editor)
            return filename_editor
        else:
            return QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        """ Fill editors with the right data """
        text = index.model().data(index, Qt.DisplayRole)
        if index.column() in (NODE_NAME, NODE_FILE):
            if index.column() == NODE_FILE and not get_settings_bool_value(self.settings.value('showRealAttributeValue', DEFAULT_SHOW_REAL_ATTRIBUTE)):
                if not text.startswith('\\'):
                    text = workspace(projectPath=text)
            editor.setText(text)

    def setModelData(self, editor, model, index):
        """ Send modification to model """
        if index.column() in (NODE_NAME, NODE_FILE):
            index_str = index.model().data(index, Qt.DisplayRole)
            if index_str != editor.text():
                if index.column() == NODE_FILE and not get_settings_bool_value(self.settings.value('showRealAttributeValue', DEFAULT_SHOW_REAL_ATTRIBUTE)):
                    if not index_str.startswith('\\'):
                        index_str = workspace(projectPath=index_str)
                    if index_str == editor.text():
                        return
                model.setData(index, editor.text())
        else:
            QStyledItemDelegate.setModelData(self, editor, model, index)

    def commit_and_close_editor(self):
        editor = self.sender()

        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)


class PathEditor(QWidget):
    """ Custom widget with LineEdit and a Button to browse file """

    editingFinished = Signal()

    def __init__(self, parent=None, index=None, settings=None):
        super(PathEditor, self).__init__(parent)

        self.parent = parent
        self.index = index
        self.settings = settings
        self.open_dialog_visible = False

        self.setFocusPolicy(Qt.StrongFocus)

        editor_layout = QHBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.line_edit = LineEditor(self)
        editor_layout.addWidget(self.line_edit)

        self.button = QPushButton('')
        self.button.setIcon(QIcon(':/editor_folder'))
        self.button.setFixedSize(18, 17)
        self.button.setToolTip('Select a texture')
        self.button.setStatusTip('Select a texture')
        self.button.clicked.connect(self.selectFile)
        editor_layout.addWidget(self.button)

        self.setFocusProxy(self.line_edit)
        self.setLayout(editor_layout)

    def setText(self, text):
        """ Set line edit text """
        self.line_edit.setText(text)

    def text(self):
        """ return line edit text """
        return self.line_edit.text()

    def selectFile(self):
        """ Maya Open Dialog to select file texture """
        self.open_dialog_visible = True

        if get_settings_bool_value(self.settings.value('browserFirstStart', DEFAULT_BROWSER_FIRST_START)):
            image_dir = cmds.optionVar(query='MTT_browserStartFolder')
        else:
            image_dir = cmds.workspace(query=True, rootDirectory=True) + cmds.workspace(fileRuleEntry='sourceImages')
            self.settings.setValue('browserFirstStart', True)

        file_path = cmds.fileDialog2(fileMode=1, startingDirectory=image_dir, caption='Select a texture', okCaption='Select')

        if file_path:
            new_path = file_path[0]
            cmds.optionVar(sv=['MTT_browserStartFolder', os.path.dirname(new_path)])
            if get_settings_bool_value(self.settings.value('forceRelativePath', DEFAULT_FORCE_RELATIVE_PATH)):
                new_path = convert_to_relative_path(new_path)
                # relative_path = workspace(projectPath=new_path)
                # if relative_path != new_path:
                #     new_path = '/%s' % relative_path
            self.line_edit.setText(new_path)
        self.open_dialog_visible = False
        self.close()
        self.editingFinished.emit()
        showWindow(WINDOW_NAME)


class LineEditor(QLineEdit):
    """ Custom LineEdit to manage focus """
    def __init__(self, parent=None):
        super(LineEditor, self).__init__(parent)
        self.parent = parent

    def focusOutEvent(self, event):
        """ focusOutEvent override """
        super(LineEditor, self).focusOutEvent(event)
        if self.parent.open_dialog_visible:
            self.parent.close()
        elif event.reason() == Qt.MouseFocusReason:
            self.parent.editingFinished.emit()
