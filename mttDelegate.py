# Python import
import re
import os.path
# Qt import
from PySide.QtCore import Qt, QRegExp, Signal, QPointF
from PySide.QtGui import (
    QApplication, QKeyEvent, QRegExpValidator, QWidget,
    QStyledItemDelegate, QAbstractItemDelegate,
    QHBoxLayout, QLineEdit, QPushButton,
    QStyle, QIcon, QBrush, QPolygonF
)
# Maya import
from maya import cmds
# custom import
from mttConfig import (
    WINDOW_NAME, MTTSettings, NODE_REFERENCE, FILE_STATE, NODE_NAME, NODE_FILE,
)
from mttCmd import convert_to_relative_path


class MTTDelegate(QStyledItemDelegate):
    """ MTT Delegate, provide editors and look & feel """

    def __init__(self):
        super(MTTDelegate, self).__init__()

    def paint(self, painter, option, index):
        # NODE_REFERENCE ---------------------------------------------------
        if index.column() == NODE_REFERENCE:

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
                painter.setPen(
                    Qt.black
                    if option.state & QStyle.State_Selected
                    else Qt.darkGray
                )
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

        # FILE_STATE -------------------------------------------------------
        elif index.column() == FILE_STATE:

            # backup painter
            painter.save()

            # paint background
            palette = QApplication.palette()
            bg_color = palette.highlight().color() \
                if option.state & QStyle.State_Selected \
                else Qt.transparent
            painter.fillRect(option.rect, bg_color)

            # paint circle
            value = index.model().data(index)

            pen_color = [
                Qt.darkRed,
                Qt.black if option.state & QStyle.State_Selected else Qt.gray,
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

        # NODE_NAME --------------------------------------------------------
        elif index.column() == NODE_NAME:
            text = index.model().data(index, Qt.DisplayRole)
            palette = QApplication.palette()
            bg_color = palette.highlight().color() \
                if option.state & QStyle.State_Selected \
                else Qt.transparent
            txt_color = palette.highlightedText().color() \
                if option.state & QStyle.State_Selected \
                else palette.text().color()

            if MTTSettings.value('vizWrongNameState') \
                    and not MTTSettings.value('showWrongNameState'):
                file_name = os.path.splitext(os.path.basename(
                    index.model().data(
                        index.sibling(index.row(), NODE_FILE),
                        Qt.DisplayRole
                    )
                ))[0]
                if not re.split('[0-9]*$', text.rsplit(':')[-1])[0] == \
                        re.split('[0-9]*$', file_name)[0]:
                    bg_color = QBrush(
                        Qt.red
                        if option.state & QStyle.State_Selected
                        else Qt.darkRed,
                        Qt.Dense4Pattern
                    )

            if not MTTSettings.value('showNamespaceState'):
                splits = text.split(':')
                text = splits[len(splits) > 1]

            painter.save()
            painter.fillRect(option.rect, bg_color)
            painter.setPen(txt_color)
            rect = option.rect
            rect.setX(4)
            QApplication.style().drawItemText(
                painter, rect, Qt.AlignLeft | Qt.AlignVCenter,
                palette, True, text
            )
            painter.restore()

        # NODE_FILE ------------------------------------------------------------
        elif index.column() == NODE_FILE:
            palette = QApplication.palette()
            bg_color = palette.highlight().color() \
                if option.state & QStyle.State_Selected \
                else Qt.transparent
            txt_color = palette.highlightedText().color() \
                if option.state & QStyle.State_Selected \
                else palette.text().color()

            text = index.model().data(index, Qt.DisplayRole)
            if MTTSettings.value('vizWrongPathState'):
                if not re.match(MTTSettings.PATH_PATTERN, text):
                    bg_color = QBrush(
                        Qt.red
                        if option.state & QStyle.State_Selected
                        else Qt.darkRed,
                        Qt.Dense4Pattern)

            if MTTSettings.value('showBasenameState'):
                text = os.path.basename(text)
            elif not MTTSettings.value('showRealAttributeValue'):
                if not text.startswith('\\'):
                    text = os.path.normpath(cmds.workspace(projectPath=text))

            painter.save()
            painter.fillRect(option.rect, bg_color)
            painter.setPen(txt_color)
            QApplication.style().drawItemText(
                painter, option.rect, Qt.AlignLeft | Qt.AlignVCenter,
                palette, True, text)
            painter.restore()
        else:
            QStyledItemDelegate.paint(self, painter, option, index)

    def editorEvent(self, event, model, option, index):
        # avoid rename when pressing on keys
        if isinstance(event, QKeyEvent):
            return event.key() != Qt.Key_F2

        return False

    def createEditor(self, parent, option, index):
        if index.column() == NODE_NAME:
            rename_editor = QLineEdit(parent)
            rename_editor.setValidator(
                QRegExpValidator(QRegExp(r'[a-zA-Z_]+[a-zA-Z0-9_:]*'), self))
            return rename_editor
        elif index.column() == NODE_FILE:
            # filename_editor = QLineEdit(parent)
            filename_editor = PathEditor(parent, index)
            filename_editor.editingFinished.connect(
                self.commit_and_close_editor)
            return filename_editor
        else:
            return QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        # fill editors with the right data
        text = index.model().data(index, Qt.DisplayRole)
        if index.column() in (NODE_NAME, NODE_FILE):
            if index.column() == NODE_FILE \
                    and not MTTSettings.value('showRealAttributeValue'):
                if not text.startswith('\\'):
                    text = cmds.workspace(projectPath=text)
            editor.setText(text)

    def setModelData(self, editor, model, index):
        # send modification to model
        if index.column() in (NODE_NAME, NODE_FILE):
            index_str = index.model().data(index, Qt.DisplayRole)
            if index_str != editor.text():
                if index.column() == NODE_FILE \
                        and not MTTSettings.value('showRealAttributeValue'):
                    if not index_str.startswith('\\'):
                        index_str = cmds.workspace(projectPath=index_str)
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

    def __init__(self, parent=None, index=None):
        super(PathEditor, self).__init__(parent)

        self.parent = parent
        self.index = index
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
        self.button.clicked.connect(self.select_file)
        editor_layout.addWidget(self.button)

        self.setFocusProxy(self.line_edit)
        self.setLayout(editor_layout)

    def setText(self, text):
        """ Set line edit text

        :param text: (string) text...
        """
        self.line_edit.setText(text)

    def text(self):
        """ return line edit text """
        return self.line_edit.text()

    def select_file(self):
        """ Maya Open Dialog to select file texture """
        self.open_dialog_visible = True

        if MTTSettings.value('browserFirstStart'):
            image_dir = cmds.optionVar(query='MTT_browserStartFolder')
        else:
            image_dir = cmds.workspace(query=True,
                                       rootDirectory=True) + cmds.workspace(
                fileRuleEntry='sourceImages')
            MTTSettings.set_value('browserFirstStart', True)

        file_path = cmds.fileDialog2(fileMode=1, startingDirectory=image_dir,
                                     caption='Select a texture',
                                     okCaption='Select')

        if file_path:
            new_path = file_path[0]
            cmds.optionVar(
                sv=['MTT_browserStartFolder', os.path.dirname(new_path)])
            if MTTSettings.value('forceRelativePath'):
                new_path = convert_to_relative_path(new_path)
                # relative_path = workspace(projectPath=new_path)
                # if relative_path != new_path:
                #     new_path = '/%s' % relative_path
            self.line_edit.setText(new_path)
        self.open_dialog_visible = False
        self.close()
        self.editingFinished.emit()
        cmds.showWindow(WINDOW_NAME)


class LineEditor(QLineEdit):
    """ Custom LineEdit to manage focus """

    def __init__(self, parent=None):
        super(LineEditor, self).__init__(parent)
        self.parent = parent

    def focusOutEvent(self, event):
        super(LineEditor, self).focusOutEvent(event)
        if self.parent.open_dialog_visible:
            self.parent.close()
        elif event.reason() == Qt.MouseFocusReason:
            self.parent.editingFinished.emit()
