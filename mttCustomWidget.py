# Qt import
from PySide.QtGui import (
    QApplication, QMessageBox, QHBoxLayout, QWidget, QPushButton, QComboBox,
    QScrollArea, QPixmap, QPainter, QCursor, QPen
)
from PySide.QtCore import Signal, Qt
# Maya import
from maya import cmds
# custom import
from mttConfig import TOOLBAR_BUTTON_SIZE, TOOLBAR_SEPARATOR_WIDTH


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
        self.setFixedSize(TOOLBAR_SEPARATOR_WIDTH, 20)

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

    toggled = Signal(int)

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

    def _delta_length(self):
        if self.state:
            return self.max_length() - TOOLBAR_SEPARATOR_WIDTH
        else:
            return TOOLBAR_SEPARATOR_WIDTH - self.max_length()

    def add_button(self, button):
        """ Create a button and add it to the layout

        :param button: QPushButton
        """
        self.icon_buttons.append(button)
        self.group_layout.addWidget(button)

    def toggle_layout(self, init=False):
        """ Toggle collapse action for layout """
        if not init:
            self.state = not self.state

        for btn in self.icon_buttons:
            btn.setVisible(self.state)

        self.toggle_btn.set_collapse(self.state)
        if init:
            self.toggled.emit(0 if self.state else self._delta_length())
        else:
            self.toggled.emit(self._delta_length())

    def set_current_state(self, state):
        self.state = state == 'true' if isinstance(state, unicode) else state
        self.toggle_layout(init=True)

    def button_count(self):
        return len(self.icon_buttons)

    def button_list(self):
        return self.icon_buttons

    def current_state(self):
        return self.state

    def max_length(self):
        count = self.button_count()
        # separator button width + button count * button size + spacing
        return TOOLBAR_SEPARATOR_WIDTH + count * TOOLBAR_BUTTON_SIZE + count


class StatusScrollArea(QScrollArea):
    def __init__(self):
        super(StatusScrollArea, self).__init__()

        self._width = 0
        self._group_count = 0

        self._pan_pos = None

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

    def _update_width(self, expand_value):
        self._width += expand_value
        self.container.setFixedWidth(self._width + self._group_count)

    def mousePressEvent(self, event):
        if event.button() == Qt.MidButton:
            QApplication.setOverrideCursor(QCursor(Qt.SizeHorCursor))
            self._pan_pos = event.globalPos()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MidButton:
            QApplication.restoreOverrideCursor()
            self._pan_pos = None
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self._pan_pos:
            h_bar = self.horizontalScrollBar()
            h_bar_pos = h_bar.sliderPosition()
            cursor_pos = event.globalPos()
            cursor_delta = (cursor_pos - self._pan_pos).x()

            h_bar.setValue(h_bar_pos - cursor_delta)
            self._pan_pos = cursor_pos
            event.accept()
        else:
            event.ignore()

    def wheelEvent(self, event):
        if event.orientation() == Qt.Vertical:
            num_degrees = event.delta() / 8
            h_bar = self.horizontalScrollBar()
            h_bar_pos = h_bar.sliderPosition()

            h_bar.setValue(h_bar_pos - num_degrees)
        else:
            super(StatusScrollArea, self).wheelEvent(event)

    def resizeEvent(self, event):
        max_scroll = max(0, self.container.width() - event.size().width())
        self.horizontalScrollBar().setMaximum(max_scroll)

    def add_widget(self, widget):
        # add widget to layout
        self.container_layout.addWidget(widget)

        # connect widget for future update when user interact with it
        widget.toggled.connect(self._update_width)

        # expand widget layout
        self._width += widget.max_length()
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
