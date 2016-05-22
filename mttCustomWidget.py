# Qt import
from PySide.QtGui import (
    QApplication, QMessageBox, QHBoxLayout, QWidget, QPushButton, QComboBox,
    QScrollArea, QPixmap, QPainter, QCursor, QPen
)
from PySide.QtCore import Signal, Qt
# Maya import
from maya import cmds
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
        self.new_ui = float(cmds.about(version=True)) >= 2016

        palette = QApplication.palette()
        self.highlight = palette.highlight().color()

    def paintEvent(self, event):
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        is_hover = self.contentsRect().contains(mouse_pos)

        if not self.new_ui:
            QPushButton.paintEvent(self, event)

        painter = QPainter(self)
        if self.new_ui and self.isChecked():
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(Qt.NoPen))
            painter.setBrush(self.highlight)
            painter.drawRoundedRect(event.rect(), 2, 2)

        painter.drawPixmap(2, 2, self.icon)

        if is_hover:
            painter.setCompositionMode(QPainter.CompositionMode_Screen)
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
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        is_hover = self.contentsRect().contains(mouse_pos)

        QPushButton.paintEvent(self, event)

        painter = QPainter(self)
        painter.drawPixmap(2, 1, self.icon)
        if is_hover:
            painter.setCompositionMode(QPainter.CompositionMode_Screen)
            painter.drawPixmap(2, 1, self.icon)

    def set_collapse(self, state):
        self.icon = self.pix[state]


class StatusCollapsibleLayout(QWidget):
    """ Collapsible layout with Maya Status Line's style """

    toggled = Signal(bool)

    def __init__(self, parent=None, section_name=None):
        super(StatusCollapsibleLayout, self).__init__(parent)

        self.icon_buttons = []
        self.state = True

        self.toggle_btn = SeparatorButton()
        if section_name is None:
            section_name = 'Show/Hide section'
        self.toggle_btn.setToolTip(section_name)
        self.toggle_btn.setFlat(True)
        self.toggle_btn.clicked.connect(self.toggle_layout)

        self.group_layout = QHBoxLayout()
        self.group_layout.setAlignment(Qt.AlignLeft)
        self.group_layout.setContentsMargins(0, 0, 0, 0)
        self.group_layout.setSpacing(1)
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
        self.toggled.emit(self.state)

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

    def length(self):
        count = self.button_count()
        # count * button size + spacing
        return count * TOOLBAR_BUTTON_SIZE + count


class StatusScrollArea(QScrollArea):
    def __init__(self):
        super(StatusScrollArea, self).__init__()

        self._width = 0
        self._group_count = 0

        self.__create_ui()
        self.__init_ui()

    def __create_ui(self):
        self.container = QWidget()
        self.container_layout = QHBoxLayout()

        self.container.setLayout(self.container_layout)
        self.setWidget(self.container)

    def __init_ui(self):
        self.container.setFixedHeight(TOOLBAR_BUTTON_SIZE)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(1)
        self.container_layout.setAlignment(Qt.AlignLeft)

        self.setFixedHeight(TOOLBAR_BUTTON_SIZE)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFrameShape(self.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _update_width(self, expand):
        self._width += self.sender().length() * [-1, 1][expand]
        self.container.setFixedWidth(self._width + self._group_count)

    def add_widget(self, widget):
        # add widget to layout
        self.container_layout.addWidget(widget)

        # connect widget for future update when user interact with it
        widget.toggled.connect(self._update_width)

        # expand widget layout
        self._width += widget.length()
        self._group_count += 1
        self.container.setFixedWidth(self._width)


class MessageBoxWithCheckbox(QMessageBox):
    def __init__(self, parent=None):
        super(MessageBoxWithCheckbox, self).__init__(parent)

        self.instance_state_widget = QComboBox()
        self.layout().addWidget(self.instance_state_widget, 1, 1)

    def exec_(self, *args, **kwargs):
        return QMessageBox.exec_(self, *args, **kwargs), \
               self.instance_state_widget.currentIndex()
