# Qt import
from PySide.QtGui import *
from PySide.QtCore import *

# custom import
from mttConfig import *


class RightPushButton(QPushButton):
    """
    Push Button with Right click signal
    """
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
    """
    Button with same Maya Status Line behavior
    """
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
    """
    Separator button Maya Status Line's style
    """
    def __init__(self, parent=None):
        super(SeparatorButton, self).__init__(parent)

        self.is_collapsed = False
        self.icon = QPixmap(':/ShortOpenBar.png')
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

    def setCollapse(self, state):
        self.icon = (QPixmap(':/ShortOpenBar.png') if state else QPixmap(':/ShortCloseBar.png'))


class StatusCollapsibleLayout(QWidget):
    """
    Collapsible layout Maya Status Line's style
    """
    def __init__(self, parent=None, section_name=None):
        super(StatusCollapsibleLayout, self).__init__(parent)

        self.__iconButtons = []
        self.__currentState = 1

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

    def add_button(self, button=None):
        """ Create a button and add it to the layout """
        if button is not None:
            self.__iconButtons.append(button)
            self.group_layout.addWidget(button)

    def toggle_layout(self):
        """ Toggle collapse action for layout """
        if self.__currentState:
            self.__currentState = 0
            for btn in self.__iconButtons:
                btn.hide()
        else:
            self.__currentState = 1
            for btn in self.__iconButtons:
                btn.show()
        self.toggle_btn.setCollapse(self.__currentState)

    def set_current_state(self, state):
        if isinstance(state, unicode):
            state = int(state)
        self.__currentState = [1, 0][state]
        self.toggle_layout()

    def button_count(self):
        return len(self.__iconButtons)

    def button_list(self):
        return self.__iconButtons

    def current_state(self):
        return self.__currentState


class MessageBoxWithCheckbox(QMessageBox):
    def __init__(self, parent=None):
        super(MessageBoxWithCheckbox, self).__init__(parent)

        self.instance_state_widget = QComboBox()
        current_layout = self.layout()
        current_layout.addWidget(self.instance_state_widget, 1, 1)

    def exec_(self, *args, **kwargs):
        return QMessageBox.exec_(self, *args, **kwargs), self.instance_state_widget.currentIndex()