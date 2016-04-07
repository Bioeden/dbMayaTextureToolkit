# Qt import
from PySide.QtGui import (
    QMessageBox, QHBoxLayout, QWidget, QPushButton, QComboBox,
    QPixmap, QPainter, QCursor
)
from PySide.QtCore import Signal, Qt
# custom import
from mttConfig import TOOLBAR_BUTTON_SIZE


class RightPushButton(QPushButton):
    """ Push Button with Right click signal """

    rightClick = Signal()
    is_right_press = False

    def __init__(self, parent=None):
        super(RightPushButton, self).__init__(parent)
        self.is_right_press = False

    def mousePressEvent(self, event):
        QPushButton.mousePressEvent(self, event)

        if event.button() == Qt.RightButton:
            self.is_right_press = True
            self.setDown(True)

    def mouseMoveEvent(self, event):
        QPushButton.mouseMoveEvent(self, event)

        if event.buttons() & Qt.RightButton:
            if self.contentsRect().contains(event.pos()):
                self.setDown(True)
                self.is_right_press = True
            else:
                self.setDown(False)
                self.is_right_press = False

    def mouseReleaseEvent(self, event):
        QPushButton.mouseReleaseEvent(self, event)

        if event.button() == Qt.RightButton:
            if self.is_right_press:
                self.rightClick.emit()
                self.setDown(False)
                self.is_right_press = False


class StatusToolbarButton(QPushButton):
    """ Button with same Maya Status Line behavior """

    def __init__(self, pix_ico, parent=None):
        super(StatusToolbarButton, self).__init__(parent)

        self.icon = QPixmap(pix_ico)
        self.setFlat(True)
        self.setFixedSize(TOOLBAR_BUTTON_SIZE, TOOLBAR_BUTTON_SIZE)

    def paintEvent(self, event):
        QPushButton.paintEvent(self, event)

        if self.isChecked():
            compo_mode = QPainter.CompositionMode_Overlay
        elif self.contentsRect().contains(self.mapFromGlobal(QCursor.pos())):
            compo_mode = QPainter.CompositionMode_ColorDodge
        else:
            compo_mode = QPainter.CompositionMode_SourceOver

        painter = QPainter(self)
        painter.setCompositionMode(compo_mode)
        painter.drawPixmap(2, 2, self.icon)


class SeparatorButton(QPushButton):
    """ Separator button with Maya Status Line's style """

    def __init__(self, parent=None):
        super(SeparatorButton, self).__init__(parent)

        self.pix = (QPixmap(':/ShortCloseBar.png'),
                    QPixmap(':/ShortOpenBar.png'))

        self.is_collapsed = False
        self.icon = self.pix[1]
        self.setFlat(True)
        self.setFixedSize(10, 20)

    def paintEvent(self, event):
        QPushButton.paintEvent(self, event)

        if self.contentsRect().contains(self.mapFromGlobal(QCursor.pos())):
            compo_mode = QPainter.CompositionMode_ColorDodge
        else:
            compo_mode = QPainter.CompositionMode_SourceOver

        painter = QPainter(self)
        painter.setCompositionMode(compo_mode)
        painter.drawPixmap(2, 1, self.icon)

    def set_collapse(self, state):
        self.icon = self.pix[state]


class StatusCollapsibleLayout(QWidget):
    """ Collapsible layout with Maya Status Line's style """

    def __init__(self, parent=None, section_name=None):
        super(StatusCollapsibleLayout, self).__init__(parent)

        self.icon_buttons = []
        self.state = True

        self.toggle_btn = SeparatorButton()
        # self.toggle_btn.setIconSize(QSize(10, 17))
        if section_name is None:
            section_name = 'Show/Hide section'
        self.toggle_btn.setToolTip(section_name)
        self.toggle_btn.setFlat(True)
        self.toggle_btn.clicked.connect(self.toggle_layout)

        self.group_layout = QHBoxLayout()
        self.group_layout.setAlignment(Qt.AlignLeft)
        self.group_layout.setContentsMargins(0, 0, 0, 0)
        self.group_layout.setSpacing(0)
        self.group_layout.addWidget(self.toggle_btn)

        self.setLayout(self.group_layout)

    def add_button(self, button):
        """ Create a button and add it to the layout

        :param button: QPushButton
        """
        self.icon_buttons.append(button)
        self.group_layout.addWidget(button)

    def toggle_layout(self):
        """ Toggle collapse action for layout """
        self.state = not self.state

        for btn in self.icon_buttons:
            btn.setVisible(self.state)

        self.toggle_btn.set_collapse(self.state)

    def set_current_state(self, state):
        if isinstance(state, unicode):
            state = state == 'true'

        self.state = not state
        self.toggle_layout()

    def button_count(self):
        return len(self.icon_buttons)

    def button_list(self):
        return self.icon_buttons

    def current_state(self):
        return self.state


class MessageBoxWithCheckbox(QMessageBox):
    def __init__(self, parent=None):
        super(MessageBoxWithCheckbox, self).__init__(parent)

        self.instance_state_widget = QComboBox()
        self.layout().addWidget(self.instance_state_widget, 1, 1)

    def exec_(self, *args, **kwargs):
        return QMessageBox.exec_(self, *args, **kwargs), \
               self.instance_state_widget.currentIndex()
