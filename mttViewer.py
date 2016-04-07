# Python import
import os
import math
import ctypes
from functools import partial
# Qt import
from PySide.QtCore import *
from PySide.QtGui import *
# Maya import
from maya import cmds
from maya import OpenMaya as om
# custom import
from mttConfig import MTTSettings, VIEWER_NAME, VIEWER_TITLE, WINDOW_ICON
from mttCmd import mtt_log
from mttCmdUi import get_maya_window
from mttCustomWidget import StatusToolbarButton


class MTTPopup(QFrame):
    def __init__(self, parent=None):
        super(MTTPopup, self).__init__(parent)

        # init variables
        self.current_image = None
        self.compared_image = None
        self.is_compare_mode = False

        # UI variables
        self.current_pixel = None
        self.current_red = None
        self.current_green = None
        self.current_blue = None
        self.current_alpha = None

        self.compared_pixel = None
        self.compared_red = None
        self.compared_green = None
        self.compared_blue = None
        self.compared_alpha = None

        self.__create_ui()

    def __create_ui(self):
        p = QPalette()
        p.setColor(QPalette.Background, QColor(60, 60, 60))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setPalette(p)
        self.setFrameStyle(QFrame.Raised)
        self.setFrameShape(QFrame.StyledPanel)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)

        current_layout = QVBoxLayout()
        compare_layout = QVBoxLayout()

        self.current_pixel = QLabel()
        self.current_pixel.setFixedSize(QSize(35, 16))
        current_layout.addWidget(self.current_pixel)
        self.current_red = QLabel()
        self.current_red.setStyleSheet("color:#FF0000")
        current_layout.addWidget(self.current_red)
        self.current_green = QLabel()
        self.current_green.setStyleSheet("color:#00FF00")
        current_layout.addWidget(self.current_green)
        self.current_blue = QLabel()
        self.current_blue.setStyleSheet("color:#0000FF")
        current_layout.addWidget(self.current_blue)
        self.current_alpha = QLabel()
        current_layout.addWidget(self.current_alpha)

        self.compared_pixel = QLabel()
        self.compared_pixel.setFixedSize(QSize(35, 16))
        compare_layout.addWidget(self.compared_pixel)
        self.compared_red = QLabel()
        self.compared_red.setStyleSheet("color:#FF0000")
        compare_layout.addWidget(self.compared_red)
        self.compared_green = QLabel()
        self.compared_green.setStyleSheet("color:#00FF00")
        compare_layout.addWidget(self.compared_green)
        self.compared_blue = QLabel()
        self.compared_blue.setStyleSheet("color:#0000FF")
        compare_layout.addWidget(self.compared_blue)
        self.compared_alpha = QLabel()
        compare_layout.addWidget(self.compared_alpha)

        main_layout.addLayout(current_layout)
        main_layout.addLayout(compare_layout)

        self.setLayout(main_layout)

    def new_pos(self, image_pos, cursor_pos):
        self.compared_red.setVisible(self.is_compare_mode)
        self.compared_green.setVisible(self.is_compare_mode)
        self.compared_blue.setVisible(self.is_compare_mode)
        self.compared_alpha.setVisible(self.is_compare_mode)
        self.compared_pixel.setVisible(self.is_compare_mode)

        self.setFixedWidth(50 * (int(self.is_compare_mode) + 1))

        raw_image = self.current_image.toImage()
        current_color = raw_image.pixel(int(image_pos.x()), int(image_pos.y()))
        self.current_red.setText('R=%d' % qRed(current_color))
        self.current_green.setText('G=%d' % qGreen(current_color))
        self.current_blue.setText('B=%d' % qBlue(current_color))
        self.current_alpha.setText('A=%d' % qAlpha(current_color))
        self.current_pixel.setStyleSheet('background-color: %s;' % QColor(current_color).name())

        if self.is_compare_mode:
            raw_comp_image = self.compared_image.toImage()
            if raw_comp_image.rect().contains(QPoint(int(image_pos.x()), int(image_pos.y()))):
                comp_color = raw_comp_image.pixel(int(image_pos.x()), int(image_pos.y()))
            else:
                comp_color = qRgba(0, 0, 0, 0)
            self.compared_red.setText('-> %d' % qRed(comp_color))
            self.compared_green.setText('-> %d' % qGreen(comp_color))
            self.compared_blue.setText('-> %d' % qBlue(comp_color))
            self.compared_alpha.setText('-> %d' % qAlpha(comp_color))
            self.compared_pixel.setStyleSheet('background-color: %s;' % QColor(comp_color).name())

        self.move(QPoint(cursor_pos + QPoint(16, 16)))


class MTTItem(QGraphicsPixmapItem):
    def __init__(self, *args, **kwargs):
        super(MTTItem, self).__init__(*args, **kwargs)

        self.draw_style = 'RGB'

        self.texture_width = self.pixmap().width()
        self.texture_height = self.pixmap().height()
        self.comp_split_pos = -1
        self.compare_texture = QPixmap(8, 8)

    def draw_splitted_image(self, p):
        if self.comp_split_pos >= 0:
            p.setClipRect(QRectF(0, 0, self.comp_split_pos, self.texture_height))
            p.drawPixmap(0, 0, self.pixmap())
            clip_rect = QRectF(self.comp_split_pos, 0, self.texture_width, self.texture_height)
            p.setClipRect(clip_rect.intersect(self.shape().boundingRect()))
            p.drawPixmap(0, 0, self.compare_texture.width(), self.compare_texture.height(), self.compare_texture)
            p.setClipping(False)
        else:
            p.drawPixmap(0, 0, self.pixmap())

    def draw_rgb_channel(self, p, color):
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(QRect(0, 0, self.texture_width, self.texture_height), QColor(0, 0, 0))
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        self.draw_splitted_image(p)
        p.setCompositionMode(QPainter.CompositionMode_Multiply)
        p.fillRect(QRect(0, 0, self.texture_width, self.texture_height), color)

    def draw_alpha_channel(self, p):
        self.draw_splitted_image(p)
        p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        p.fillRect(QRect(0, 0, self.texture_width, self.texture_height), QColor(255, 255, 255))

    def draw_rgba_image(self, p):
        p.setCompositionMode(QPainter.CompositionMode_Xor)
        self.draw_splitted_image(p)
        p.setCompositionMode(QPainter.CompositionMode_DestinationOver)
        self.draw_splitted_image(p)

    def custom_paint(self, p):
        if self.draw_style == 'RGB':
            self.draw_splitted_image(p)
        elif self.draw_style == 'RGBA':
            self.draw_rgba_image(p)
        elif self.draw_style == 'R':
            self.draw_rgb_channel(p, QColor(255, 0, 0))
        elif self.draw_style == 'G':
            self.draw_rgb_channel(p, QColor(0, 255, 0))
        elif self.draw_style == 'B':
            self.draw_rgb_channel(p, QColor(0, 0, 255))
        elif self.draw_style == 'A':
            self.draw_alpha_channel(p)

    def get_current_pixmap(self):
        pix = QPixmap(QSize(self.texture_width, self.texture_height))

        p = QPainter(pix)
        toggle_style = False
        if self.draw_style == 'RGBA':
            toggle_style = True
            self.draw_style = 'RGB'
        self.custom_paint(p)
        if toggle_style:
            self.draw_style = 'RGBA'
        p.end()

        return pix

    def paint(self, p, option, widget):
        self.custom_paint(p)


class MTTGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super(MTTGraphicsView, self).__init__(parent)

        # init some variables
        self.supported_image_ext = QImageReader.supportedImageFormats()
        self.scene = QGraphicsScene()
        self.default_texture = QPixmap(':/viewer_empty')

        # create background pattern
        self.alpha_background = QPixmap(32, 32)
        self.alpha_background.fill(Qt.white)
        tile_painter = QPainter(self.alpha_background)
        tile_color = QColor(220, 220, 220, 255)
        tile_painter.fillRect(0, 0, 16, 16, tile_color)
        tile_painter.fillRect(16, 16, 16, 16, tile_color)
        tile_painter.end()
        self.image_buffer = None

        self.current_texture = self.default_texture
        self.compare_texture = self.default_texture
        self.popup_info = MTTPopup(parent=self)
        self.popup_info.current_image = self.default_texture
        self.popup_info.compared_image = self.default_texture
        self.current_item = None
        self.current_style = 'RGB'

        self.is_default_texture = True
        self.is_loading_fail = False
        self.is_popup_info = False
        self.show_tile = False
        self.navigation_mode = False
        self.compare_mode = False
        self.last_pos = QPoint(0, 0)
        self.compare_split_pos = -1
        self.is_comparing = False

        self.__init_ui()

    def __init_ui(self):
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setScene(self.scene)

        # TODO : found a way to linearized color when showing R or G or B

    def __add_texture_item(self, default_texture_state):
        # clear the scene
        if self.scene.items():
            self.scene.removeItem(self.scene.items()[0])
            self.scene.setSceneRect(0, 0, self.current_texture.width(), self.current_texture.height())

        self.current_item = MTTItem(self.current_texture)
        self.current_item.texture = self.popup_info.current_image = self.current_texture
        self.current_item.compare_texture = self.popup_info.compared_image = self.compare_texture
        if self.compare_mode:
            self.current_item.comp_split_pos = self.compare_split_pos
        self.scene.addItem(self.current_item)

        # show image
        self.centerOn(self.current_texture.width() * 0.5, self.current_texture.height() * 0.5)
        self.centerOn(self.current_texture.width(), self.current_texture.height())
        self.is_default_texture = default_texture_state
        if not default_texture_state:
            if MTTSettings.value('Viewer/autoFit'):
                self.fit_texture()
            elif MTTSettings.value('Viewer/autoReset'):
                self.reset_texture_transform()
            self.setBackgroundBrush(QBrush(self.alpha_background))
            self.change_draw_style(self.current_style)

    def reset_image(self):
        self.current_texture = self.default_texture
        self.__add_texture_item(True)
        self.reset_texture_transform()
        self.setBackgroundBrush(QBrush(Qt.NoBrush))
        self.update_status()

    def change_draw_style(self, style):
        self.current_style = style
        self.current_item.draw_style = style
        if self.show_tile:
            self.setBackgroundBrush(QBrush(self.current_item.get_current_pixmap()))
        self.current_item.update()

    def update_status(self):
        pass

    def show_texture(self, texture_path):
        # create pointers
        width_util = om.MScriptUtil()
        width_util.createFromInt(0)
        width_ptr = width_util.asUintPtr()

        height_util = om.MScriptUtil()
        height_util.createFromInt(0)
        height_ptr = height_util.asUintPtr()

        # create Maya native MImage
        maya_texture = om.MImage()
        maya_texture.readFromFile(texture_path)
        maya_texture.verticalFlip()
        maya_texture.getSize(width_ptr, height_ptr)

        # get texture info
        width_value = width_util.getUint(width_ptr)
        height_value = height_util.getUint(height_ptr)
        texture_size = width_value * height_value * 4

        # convert to Qt format
        image_format = QImage.Format_ARGB32_Premultiplied \
            if MTTSettings.value('Viewer/premultiply') \
            else QImage.Format_RGB32

        show_default = False
        qt_image = None

        try:
            self.image_buffer = ctypes.c_ubyte * texture_size
            self.image_buffer = self.image_buffer.from_address(long(maya_texture.pixels()))
            qt_image = QImage(self.image_buffer, width_value, height_value, image_format).rgbSwapped()

            self.is_loading_fail = False
            mtt_log('%s loaded' % os.path.basename(texture_path), add_tag='VIEWER')
        except Exception as e:
            mtt_log('%s\n%s' % (type(e), e), add_tag='VIEWER', msg_type='error')
            mtt_log('Fail to load %s' % os.path.basename(texture_path), add_tag='VIEWER', msg_type='error')
            self.is_loading_fail = True
            if MTTSettings.value('Viewer/recoverMode'):
                try:
                    import time

                    start = time.clock()
                    qt_image = QImage(width_value, height_value, QImage.Format_ARGB32)
                    pixel_ptr = maya_texture.pixels()
                    for y in xrange(height_value):
                        for x in xrange(1, width_value):
                            i = (y * width_value) + x
                            i = 4 * (i - 1)
                            r = om.MScriptUtil.getUcharArrayItem(pixel_ptr, i)
                            g = om.MScriptUtil.getUcharArrayItem(pixel_ptr, i + 1)
                            b = om.MScriptUtil.getUcharArrayItem(pixel_ptr, i + 2)
                            a = om.MScriptUtil.getUcharArrayItem(pixel_ptr, i + 3)
                            qt_image.setPixel(x, y, QColor(r, g, b, a).rgba())
                    end = time.clock()
                    mtt_log('Image read in %.3fs' % (end - start))
                except Exception as e:
                    mtt_log(e, add_tag='VIEWER', msg_type='error')
                    show_default = True
            else:
                show_default = True
        except RuntimeError as e:
            mtt_log('%s\n%s' % (type(e), e), add_tag='VIEWER', msg_type='error')
            mtt_log('Fail to load %s' % os.path.basename(texture_path), add_tag='VIEWER', msg_type='error')
            self.is_loading_fail = True
            show_default = True

        if show_default:
            self.reset_image()
            return

        self.current_texture = QPixmap.fromImage(qt_image)

        # display texture in QGraphicsView
        self.__add_texture_item(False)
        self.update_status()

    def toggle_tile(self):
        if self.is_default_texture:
            self.setBackgroundBrush(QBrush(Qt.NoBrush))
        else:
            if self.show_tile:
                self.setBackgroundBrush(QBrush(self.alpha_background))
                self.show_tile = False
            else:
                self.setBackgroundBrush(QBrush(self.current_item.get_current_pixmap()))
                self.show_tile = True

    def toggle_compare(self):
        if self.is_default_texture:
            return False

        self.compare_mode = not self.compare_mode
        self.popup_info.is_compare_mode = self.compare_mode
        if self.compare_mode:
            self.current_item.compare_texture = self.compare_texture = self.current_item.pixmap()
            self.current_item.comp_split_pos = self.compare_split_pos = math.floor(self.current_item.texture_width * 0.5)
            self.popup_info.compared_image = self.compare_texture
        else:
            self.current_item.comp_split_pos = self.compare_split_pos = -1

        self.current_item.update()

        return True

    def toggle_color_info(self):
        self.is_popup_info = not self.is_popup_info
        self.setMouseTracking(self.is_popup_info)

    def fit_texture(self):
        if self.is_default_texture:
            return

        self.fitInView(self.current_item, Qt.KeepAspectRatio)
        self.update_status()

    def reset_texture_transform(self):
        self.resetMatrix()
        self.update_status()

    def update_split_pos(self, event):
        mouse_texture_pos = self.mapToScene(event.pos())
        self.compare_split_pos = self.current_item.comp_split_pos = max(0, min(mouse_texture_pos.x(), self.current_item.boundingRect().width()))
        self.current_item.update()

    def drawBackground(self, p, rect):
        if self.show_tile:
            p.save()
            # store current transform
            current_transform = p.transform()

            # draw background tile
            p.resetTransform()
            p.drawTiledPixmap(self.viewport().rect(), self.alpha_background)

            # restore transform
            p.setTransform(current_transform)

            # create texture tiling coord
            viewport_scene_pos = self.mapFromScene(self.current_item.pos())
            viewport_texture_size = self.transform().mapRect(self.current_item.shape().boundingRect())
            tile_x_pos = (viewport_scene_pos.x() % viewport_texture_size.width()) - viewport_texture_size.width()
            tile_y_pos = (viewport_scene_pos.y() % viewport_texture_size.height()) - viewport_texture_size.height()

            new_start_pos = self.mapToScene(tile_x_pos, tile_y_pos)
            new_size = QPoint(tile_x_pos, tile_y_pos) + self.viewport().rect().bottomRight() + QPoint(
                viewport_texture_size.width(), viewport_texture_size.height())
            new_rect = self.transform().inverted()[0].mapRect(
                QRectF(QPointF(tile_x_pos, tile_y_pos), QPointF(new_size.x(), new_size.y()))
            )

            # draw tiling
            self.current_item.setVisible(False)
            if self.current_item.draw_style == 'RGBA':
                p.setCompositionMode(QPainter.CompositionMode_Xor)
                p.drawTiledPixmap(
                    QRect(math.floor(new_start_pos.x()), math.floor(new_start_pos.y()), new_rect.width(), new_rect.height()),
                    self.backgroundBrush().texture()
                )
                p.setCompositionMode(QPainter.CompositionMode_DestinationOver)
            p.drawTiledPixmap(
                QRect(math.floor(new_start_pos.x()), math.floor(new_start_pos.y()), new_rect.width(), new_rect.height()),
                self.backgroundBrush().texture()
            )
            p.restore()
        else:
            self.current_item.setVisible(True)
            p.save()
            p.resetTransform()
            p.drawTiledPixmap(self.viewport().rect(), self.backgroundBrush().texture())
            p.restore()

    def show_popup(self):
        if self.is_popup_info and not self.navigation_mode:
            QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))

    def hide_popup(self):
        if self.is_popup_info and not self.navigation_mode:
            QApplication.restoreOverrideCursor()
            self.popup_info.hide()

    def enterEvent(self, event):
        self.show_popup()
        QGraphicsView.enterEvent(self, event)

    def leaveEvent(self, event):
        self.hide_popup()
        QGraphicsView.leaveEvent(self, event)

    def mousePressEvent(self, event):
        if self.is_default_texture:
            return

        if event.button() == Qt.RightButton and self.navigation_mode:
            self.last_pos = event.globalPos()
        elif event.button() == Qt.MidButton and self.navigation_mode:
            self.last_pos = event.globalPos()
            event2 = QMouseEvent(QEvent.MouseButtonPress, event.pos(), Qt.LeftButton, Qt.LeftButton, Qt.AltModifier)
            QGraphicsView.mousePressEvent(self, event2)
        elif event.button() == Qt.LeftButton and self.compare_mode and not self.navigation_mode:
            self.is_comparing = True
            self.update_split_pos(event)
        else:
            QGraphicsView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.is_default_texture:
            return

        # popup behavior
        if self.is_popup_info and not self.navigation_mode:
            cursor_view_pos = self.mapToScene(event.pos())
            if self.current_item.boundingRect().contains(cursor_view_pos):
                self.popup_info.new_pos(cursor_view_pos, event.globalPos())
                self.popup_info.show()
            else:
                if not self.is_popup_info:
                    QApplication.restoreOverrideCursor()
                self.popup_info.hide()

        # zoom behavior
        if event.buttons() == Qt.RightButton and self.navigation_mode:
            delta_pos = QPointF(event.globalPos() - self.last_pos)
            delta = (delta_pos.x() + delta_pos.y()) * 0.5

            self.last_pos = event.globalPos()

            # scaleFactor = math.pow(1.05, 1 if (delta > 0) else -1)
            # if not self.zoomFeature(delta, scaleFactor=1.02):

            if not self.zoom_feature(1, scale_factor=1.0 + delta * .01):
                return
            if self.current_item:
                self.update_status()

        # pan behavior
        elif event.buttons() == Qt.MidButton and self.navigation_mode:
            event2 = QMouseEvent(QEvent.MouseMove, event.pos(), Qt.NoButton, Qt.LeftButton, Qt.AltModifier)
            QGraphicsView.mouseMoveEvent(self, event2)
            self.scene.update()

        # comparison behavior
        elif self.is_comparing and not self.navigation_mode:
            self.update_split_pos(event)

        # update background when panning
        elif event.buttons() == Qt.LeftButton and self.navigation_mode:
            QGraphicsView.mouseMoveEvent(self, event)
            self.scene.update()

        else:
            QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.buttons() != Qt.MidButton:
            event2 = QMouseEvent(
                QEvent.MouseButtonRelease,
                event.pos(),
                Qt.LeftButton,
                Qt.MidButton | Qt.RightButton,
                Qt.AltModifier
            )
            QGraphicsView.mouseReleaseEvent(self, event2)
        else:
            QGraphicsView.mouseReleaseEvent(self, event)

        if self.is_default_texture:
            return

        self.is_comparing = False

    def wheelEvent(self, event):
        if self.is_default_texture:
            return

        if not self.zoom_feature(event.delta()):
            return

        if self.current_item:
            self.update_status()

    def zoom_feature(self, delta, scale_factor=1.15):
        # m11() Returns the horizontal scaling factor.
        # m22() Returns the vertical scaling factor.

        min_zoom = 0.1
        max_zoom = 50

        if delta > 0:
            if self.transform().m11() > max_zoom and scale_factor > 1:
                return False
            self.scale(scale_factor, scale_factor)
        else:
            if self.transform().m11() < min_zoom:
                return False
            self.scale(1.0 / scale_factor, 1.0 / scale_factor)

        return True


class MTTViewer(QMainWindow):
    def __init__(self, parent=get_maya_window()):
        super(MTTViewer, self).__init__(parent)

        if cmds.control(VIEWER_NAME, exists=True):
            cmds.deleteUI(VIEWER_NAME, window=True)

        self.parent = parent
        self.setObjectName(VIEWER_NAME)
        self.setWindowTitle(VIEWER_TITLE)
        self.setWindowIcon(QIcon(WINDOW_ICON))

        self.texture_path = None
        self.texture_compare_path = None
        self.is_mtt_sender = False

        # UI variables
        self.viewer_statusbar = None
        self.graphics_view = None
        self.channel_btn = dict()
        self.fit_btn = None
        self.reset_zoom_btn = None
        self.toggle_tile_btn = None
        self.toggle_compare_btn = None
        self.toggle_picker_btn = None
        self.settings_btn = None

        # create UI
        self.__create_ui()
        # self.setMouseTracking(True)

        # restore geometry
        self.restoreGeometry(MTTSettings.value('Viewer/windowGeometry'))

    @staticmethod
    def __create_toolbar_button(btn_icon, btn_text, btn_cmd, btn_checkable):
        new_button = StatusToolbarButton(btn_icon)
        new_button.setToolTip(btn_text)
        new_button.setStatusTip(btn_text)
        new_button.clicked.connect(btn_cmd)
        new_button.setCheckable(btn_checkable)
        return new_button

    def __create_toolbar_ui(self):
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setAlignment(Qt.AlignLeft)

        self.channel_btn['RGB'] = self.__create_toolbar_button(
            ':/viewer_RGB',
            'Display RGB Channel (shortcut: 1)',
            partial(self.show_channel, 'RGB'),
            True)

        self.channel_btn['RGBA'] = self.__create_toolbar_button(
            ':/viewer_RGBA',
            'Display RGBA Channel (shortcut: 2)',
            partial(self.show_channel, 'RGBA'),
            True)

        self.channel_btn['R'] = self.__create_toolbar_button(
            ':/viewer_R',
            'Display Red Channel (shortcut: 3)',
            partial(self.show_channel, 'R'),
            True)

        self.channel_btn['G'] = self.__create_toolbar_button(
            ':/viewer_G',
            'Display Green Channel (shortcut: 4)',
            partial(self.show_channel, 'G'),
            True)

        self.channel_btn['B'] = self.__create_toolbar_button(
            ':/viewer_B',
            'Display Blue Channel (shortcut: 5)',
            partial(self.show_channel, 'B'),
            True)

        self.channel_btn['A'] = self.__create_toolbar_button(
            ':/viewer_A',
            'Display Alpha Channel (shortcut: 6)',
            partial(self.show_channel, 'A'),
            True)

        self.fit_btn = self.__create_toolbar_button(
            ':/viewer_fit',
            'Fit Image  (shortcut: F)',
            self.graphics_view.fit_texture,
            False)

        self.reset_zoom_btn = self.__create_toolbar_button(
            ':/viewer_resetZoom',
            'Reset Zoom  (shortcut: A)',
            self.graphics_view.reset_texture_transform,
            False)

        self.toggle_tile_btn = self.__create_toolbar_button(
            ':/viewer_tile',
            'Toggle Tile (shortcut: T)',
            self.graphics_view.toggle_tile,
            True)

        self.toggle_compare_btn = self.__create_toolbar_button(
            ':/viewer_compare',
            'Toggle Compare (shortcut: C)',
            self.toggle_compare,
            True)

        self.toggle_picker_btn = self.__create_toolbar_button(
            ':/viewer_picker',
            'Toggle Color Information  (shortcut: I)',
            self.graphics_view.toggle_color_info,
            True)

        toolbar_layout.addWidget(self.channel_btn['RGB'])
        toolbar_layout.addWidget(self.channel_btn['RGBA'])
        toolbar_layout.addWidget(self.channel_btn['R'])
        toolbar_layout.addWidget(self.channel_btn['G'])
        toolbar_layout.addWidget(self.channel_btn['B'])
        toolbar_layout.addWidget(self.channel_btn['A'])
        toolbar_layout.addWidget(self.fit_btn)
        toolbar_layout.addWidget(self.reset_zoom_btn)
        toolbar_layout.addWidget(self.toggle_tile_btn)
        toolbar_layout.addWidget(self.toggle_compare_btn)
        toolbar_layout.addWidget(self.toggle_picker_btn)

        toolbar_layout.addStretch(2)

        self.settings_btn = self.__create_toolbar_button(
            ':/tb_config',
            'Settings',
            self.fake_def,
            False)
        self.settings_btn.setMenu(self.__create_settings_menu())
        toolbar_layout.addWidget(self.settings_btn)

        return toolbar_layout

    def __create_ui(self):
        """ Create main UI """
        main_layout = QVBoxLayout(self)

        main_layout.setSpacing(1)
        main_layout.setContentsMargins(2, 2, 2, 2)

        self.viewer_statusbar = self.statusBar()
        self.graphics_view = MTTGraphicsView()
        self.graphics_view.update_status = self.update_status
        self.graphics_view.reset_image()

        main_layout.addLayout(self.__create_toolbar_ui())
        self.channel_btn['RGB'].setChecked(True)
        main_layout.addWidget(self.graphics_view)

        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

    def __create_settings_menu(self):
        """ Create settings context menu """
        settings_menu = QMenu(self)
        settings_menu.setTearOffEnabled(False)

        premultiply_menu = QAction('Premultiply Alpha', self)
        premultiply_menu.setCheckable(True)
        premultiply_menu.setChecked(MTTSettings.value('Viewer/premultiply'))
        premultiply_menu.triggered.connect(self.toggle_premultiply)
        settings_menu.addAction(premultiply_menu)

        recover_action = QAction('Recovery Mode', self)
        recover_action.setToolTip('Reconstruct image iterating over all pixels when loading fail (Very SLOW)')
        recover_action.setStatusTip('Reconstruct image iterating over all pixels when loading fail (Very SLOW)')
        recover_action.setCheckable(True)
        recover_action.setChecked(MTTSettings.value('Viewer/recoverMode'))
        recover_action.triggered.connect(self.toggle_recover_mode)
        settings_menu.addAction(recover_action)

        settings_menu.addSeparator()

        header = QAction('LOADING ACTION', self)
        header.setEnabled(False)
        settings_menu.addAction(header)

        zoom_group = QActionGroup(settings_menu)

        fit_action = QAction('Fit Image', zoom_group)
        fit_action.setCheckable(True)
        fit_action.setChecked(MTTSettings.value('Viewer/autoFit'))
        fit_action.triggered.connect(self.auto_fit)
        settings_menu.addAction(fit_action)

        lock_action = QAction('Lock Zoom', zoom_group)
        lock_action.setCheckable(True)
        lock_action.setChecked(MTTSettings.value('Viewer/autoLock'))
        lock_action.triggered.connect(self.auto_lock_zoom)
        settings_menu.addAction(lock_action)

        reset_action = QAction('Reset Zoom', zoom_group)
        reset_action.setCheckable(True)
        reset_action.setChecked(MTTSettings.value('Viewer/autoReset'))
        reset_action.triggered.connect(self.auto_reset_zoom)
        settings_menu.addAction(reset_action)

        return settings_menu

    def show_channel(self, channel_type):
        for btnType in self.channel_btn.iterkeys():
            self.channel_btn[btnType].setChecked(btnType == channel_type)
        if not self.graphics_view.is_default_texture:
            self.graphics_view.change_draw_style(channel_type)

    def toggle_premultiply(self):
        state = not MTTSettings.value('Viewer/premultiply')
        MTTSettings.set_value('Viewer/premultiply', state)
        if self.texture_path:
            self.show_image(self.texture_path)

    @staticmethod
    def toggle_recover_mode():
        state = not MTTSettings.value('Viewer/recoverMode')
        MTTSettings.set_value('Viewer/recoverMode', state)

    @staticmethod
    def auto_fit():
        MTTSettings.set_value('Viewer/autoFit', True)
        MTTSettings.set_value('Viewer/autoLock', False)
        MTTSettings.set_value('Viewer/autoReset', False)

    @staticmethod
    def auto_lock_zoom():
        MTTSettings.set_value('Viewer/autoFit', False)
        MTTSettings.set_value('Viewer/autoLock', True)
        MTTSettings.set_value('Viewer/autoReset', False)

    @staticmethod
    def auto_reset_zoom():
        MTTSettings.set_value('Viewer/autoFit', False)
        MTTSettings.set_value('Viewer/autoLock', False)
        MTTSettings.set_value('Viewer/autoReset', True)

    def show_image(self, texture_path):
        if os.path.isfile(texture_path):
            self.texture_path = texture_path
            self.graphics_view.is_loading_fail = False
            self.update_status(is_loading=True)
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            self.graphics_view.show_texture(texture_path)
            QApplication.restoreOverrideCursor()
        else:
            self.texture_path = None
            mtt_log('File not found.', add_tag='VIEWER', msg_type='warning')
            self.graphics_view.is_loading_fail = True
            self.graphics_view.reset_image()

    def toggle_compare(self):
        if self.graphics_view.toggle_compare():
            self.texture_compare_path = self.texture_path if self.toggle_compare_btn.isChecked() else None
        self.update_status()

    def update_status(self, is_loading=False):
        current_color = QApplication.palette().Window

        if is_loading:
            current_color = QColor(Qt.darkGreen).name()
            msg = 'Loading texture. Please wait...'
        elif self.graphics_view.is_default_texture:
            msg = 'No Texture Found.'
        else:
            self.graphics_view.viewport().repaint()
            current_zoom = self.graphics_view.transform().m11() * 100
            texture_width = self.graphics_view.current_item.pixmap().width()
            texture_height = self.graphics_view.current_item.pixmap().height()
            texture_name = os.path.basename(self.texture_path)
            msg = '%.d%% | %dx%d | %s' % (current_zoom, texture_width, texture_height, texture_name)
            if self.texture_compare_path:
                msg += ' compared to %s' % os.path.basename(self.texture_compare_path)

        if self.graphics_view.is_loading_fail and not self.graphics_view.is_default_texture:
            msg = 'Failed to load image ! '
            if MTTSettings.value('Viewer/recoverMode'):
                msg += '::: IMAGE RECONSTRUCTED :::'
                current_color = QColor(Qt.darkRed).name()

        self.viewer_statusbar = self.statusBar()
        self.viewer_statusbar.showMessage(msg)
        self.viewer_statusbar.setStyleSheet("background-color: %s" % current_color)

    def fake_def(self):
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier | Qt.AltModifier and not self.is_mtt_sender:
            MTTSettings.set_value('viewerState', False)
            # get main tool window and disconnect signal
            main_window = self.parentWidget().parentWidget().parentWidget()
            main_window.table_view_selection_model.selectionChanged.disconnect(main_window.on_auto_show_texture)
            # get current QDockWidget parent to hide tool
            self.parentWidget().parentWidget().setVisible(False)
            # set focus to tableView otherwise filter field will be selected
            main_window.table_view.setFocus()

        if self.graphics_view.is_default_texture or event.isAutoRepeat():
            return False if self.is_mtt_sender else None

        if event.key() == Qt.Key_Alt:
            self.graphics_view.navigation_mode = True
            self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
        elif event.key() == Qt.Key_A:
            self.graphics_view.reset_texture_transform()
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_F:
            self.graphics_view.fit_texture()
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_T:
            state = self.toggle_tile_btn.isChecked()
            self.toggle_tile_btn.setChecked(not state)
            self.graphics_view.toggle_tile()
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_C:
            state = self.toggle_compare_btn.isChecked()
            self.toggle_compare_btn.setChecked(not state)
            self.toggle_compare()
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_I:
            state = self.toggle_picker_btn.isChecked()
            if not state:
                self.toggle_picker_btn.setChecked(True)
                self.graphics_view.toggle_color_info()
                self.graphics_view.show_popup()
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_1:
            self.show_channel('RGB')
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_2:
            self.show_channel('RGBA')
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_3:
            self.show_channel('R')
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_4:
            self.show_channel('G')
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_5:
            self.show_channel('B')
            return True if self.is_mtt_sender else None
        elif event.key() == Qt.Key_6:
            self.show_channel('A')
            return True if self.is_mtt_sender else None

        return False if self.is_mtt_sender else None

    def keyReleaseEvent(self, event):
        if self.graphics_view.is_default_texture or event.isAutoRepeat():
            return

        if event.key() == Qt.Key_Alt:
            self.graphics_view.navigation_mode = False
            self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        elif event.key() == Qt.Key_I:
            state = self.toggle_picker_btn.isChecked()
            if state:
                self.toggle_picker_btn.setChecked(False)
                self.graphics_view.hide_popup()
                self.graphics_view.toggle_color_info()
