from math import sqrt
from PIL import ImageQt
from configparser import ConfigParser
from os.path import exists, join, expanduser, isfile, abspath, isdir

from PyQt5.QtWidgets import (QLineEdit, QLabel, QMenu, QAction, QListWidget,
                             QPushButton, QApplication, QTextBrowser,
                             QListView, QListWidgetItem, QHBoxLayout, QWidget)

from PyQt5.QtGui import (QPainter, QCursor, QPen, QColor, QDrag, QIntValidator,
                         QIcon, QFont, QPixmap, QFont, QPainterPath, QDrag,
                         QDragEnterEvent)

from PyQt5.QtCore import QObject, Qt, pyqtSignal, QPoint, QMimeData, QRectF, QThread

from ruia_ocr import (BaiduOcrService, get_file_paths, BAIDU_ACCURATE_TYPE,
                      BAIDU_GENERAL_TYPE, BAIDU_HANDWRITING_TYPE)

from fitz import open as pdf_open
from supports import Account, User, Config
from handles import PdfHandle


class CTextBrowser(QTextBrowser):
    copy_latest = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    def contextMenu(self):
        menu = QMenu(self)
        a1 = menu.addAction('清空')
        a2 = menu.addAction('复制')
        a3 = menu.addAction('复制最近一个')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.clear()
            self.append(
                '<p><span style=" text-decoration: underline; color:#0000ff;">Ocr</span></p>'
            )
        elif action == a2:
            self.copy()
        elif action == a3:
            self.copy_latest.emit()


class DragListWidget(QListWidget):
    drag_item = None
    target_item = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMovement(QListView.Free)
        self.setSpacing(10)
        self.indexes = []
        self._start_press = None

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.drag_item = self.itemAt(QMouseEvent.pos())
            self._start_press = QMouseEvent.pos()
        super().mousePressEvent(QMouseEvent)

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
            if (QMouseEvent.pos() - self._start_press
                ).manhattanLength() < QApplication.startDragDistance():
                return
            if self.drag_item:
                drag = QDrag(self)
                data = QMimeData()
                widget = self.itemWidget(self.drag_item)
                if widget:
                    pixmap = widget.grab()
                    drag.setPixmap(pixmap)
                drag.setMimeData(data)
                drag.setHotSpot(QPoint(25, 25))
                action = drag.exec_(Qt.CopyAction | Qt.MoveAction
                                    | Qt.IgnoreAction)

                if action == Qt.MoveAction:
                    self.takeItem(self.row(self.drag_item))
                    self.takeItem(self.row(self.target_item))
                elif action == Qt.CopyAction:
                    pass
                else:
                    pass

    def _renderItemWidget(self, row, qsize, widget):
        item = QListWidgetItem()
        item.setSizeHint(qsize)
        if row == -1:
            self.addItem(item)
        else:
            self.insertItem(row, item)
        self.setItemWidget(item, widget)

    def dragEnterEvent(self, QDragEnterEvent: QDragEnterEvent):
        if self.drag_item:
            if QDragEnterEvent.source():
                QDragEnterEvent.setDropAction(Qt.MoveAction)
                QDragEnterEvent.accept()
        else:
            QDragEnterEvent.ignore()

    def dragMoveEvent(self, QDragMoveEvent):
        QDragMoveEvent.setDropAction(Qt.MoveAction)
        QDragMoveEvent.accept()

    def dropEvent(self, QDropEvent):
        self.target_item = self.itemAt(QDropEvent.pos())
        if self.target_item is None:
            QDropEvent.setDropAction(Qt.IgnoreAction)
        else:
            target_size = self.target_item.sizeHint()
            target_index = self.row(self.target_item)
            target_widget = self.itemWidget(self.target_item)
            drag_index = self.row(self.drag_item)
            drag_widget = self.itemWidget(self.drag_item)
            drag_label = drag_widget.preview_label
            drag_size = self.drag_item.sizeHint()
            if drag_index != target_index:
                if drag_widget:
                    self._renderItemWidget(target_index + 1, drag_size,
                                           drag_widget)
                    self._renderItemWidget(drag_index + 1, target_size,
                                           target_widget)
                else:
                    self.insertItem(target_index + 1, self.drag_item)
                    self.insertItem(drag_index + 1, self.target_item)

                self.setCurrentRow(target_index)
                QDropEvent.setDropAction(Qt.MoveAction)
                drag_label.clicked.emit(drag_label.index)
                QDropEvent.setDropAction(Qt.MoveAction)
            else:
                QDropEvent.setDropAction(Qt.IgnoreAction)
            # 记录交换的次序
            if drag_index != target_index:
                self.indexes[drag_index], self.indexes[
                    target_index] = self.indexes[target_index], self.indexes[
                        drag_index]
            QDropEvent.accept()


class DragLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def filterPolicy(self, event) -> bool:
        if event.mimeData().hasText():
            path = event.mimeData().text()[-4:]
            if path.lower() in ['.jpg', '.png', '.bmp', 'jpeg']:
                return True
        return False

    def dragEnterEvent(self, QDragEnterEvent):
        if self.filterPolicy(QDragEnterEvent):
            QDragEnterEvent.accept()
        else:
            QDragEnterEvent.ignore()

    def dropEvent(self, QDropEvent):
        self.setText(
            QDropEvent.mimeData().text()[8:])  # 如果之前设置ignore 为False 这里将不会生效


class PdfLineEdit(DragLineEdit):
    def __init__(self, *args, **kwargs):
        parent_widget = kwargs.pop('parent_widget', None)
        super().__init__(*args, **kwargs)
        self.parent_widget = parent_widget

    def filterPolicy(self, event):
        if event.mimeData().hasText():
            path = event.mimeData().text()[-4:]
            if path.lower() in ['.pdf', '.png', '.jpg', '.jpeg', '.bmp']:
                return True
            elif isdir(event.mimeData().text()[8:]) and exists(
                    event.mimeData().text()[8:]):
                return True
        return False

    def dropEvent(self, event):
        self.setText(event.mimeData().text()[8:])
        path = event.mimeData().text()[-4:]
        if path.lower() in ['.pdf', '.png', '.jpg', '.jpeg', '.bmp']:
            if path.lower() == '.pdf':
                self.parent_widget.comboBox.setCurrentIndex(0)
            else:
                self.parent_widget.comboBox.setCurrentIndex(1)
        else:
            self.parent_widget.comboBox.setCurrentIndex(2)
        self.parent_widget.startSlot()


class PageLineEdit(QLineEdit):

    current_page = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QIntValidator(0, 100000000))
        self.returnPressed.connect(self.emitPolicy)

    def emitPolicy(self):
        text = self.text()
        if text == '0':
            self.current_page.emit(0)
        else:
            self.current_page.emit(int(text) - 1)


class Validpoints(QObject):
    points_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.__data = []

    @classmethod
    def fromList(points):
        point = Validpoints()
        point.appends(points)
        return point

    @property
    def data(self) -> list:
        res = []
        for v in self.__data:
            if (v[:2] != v[2:]) and (0 not in v[-2:]):
                res.append(v)
        return res

    def append(self, v: '[x0,y0,x1,y1]') -> bool:
        if v[:2] != v[2:]:
            self.__data.append(v)
            return True
        return False

    def appends(self, points: 'List[List[int, int, int, int]]'):
        for point in points:
            self.append(point)

    def clear(self):
        self.__data.clear()

    def __iter__(self):
        for v in self.data:
            yield v

    def __getitem__(self, item):
        return self.__data[item]

    def __repr__(self):
        return f'Validpoints<{self.data}>'


class ImgLabel(QLabel):
    def __init__(self, *args, **kwargs):
        edit_pixmap = kwargs.pop('edit_pixmap', None)
        super().__init__(*args, **kwargs)
        self.__edit_pixmap = edit_pixmap
        self.edited = True
        self.points = Validpoints()
        self.menu = QMenu(self)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    def setEditPixmap(self, pixmap: bool):
        self.__edit_pixmap = pixmap

    def setEdit(self, flag):
        self.edited = flag

    def contextMenu(self, pos):
        menu = QMenu(self)
        a1 = menu.addAction('清除')
        a2 = menu.addAction('确认')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.points.clear()
            self.points.points_signal.emit([])
            self.update()
        elif action == a2:
            points = []
            for xycoords in self.points.data:
                x1, y1, x2, y2 = xycoords
                w, h = abs(x2 - x1), abs(y2 - y1)
                if (x2 - x1) > 0 and (y2 - y1) > 0:
                    points.append([x1, y1, x2, y2])  # 右下方滑动
                elif (x2 - x1) > 0 and (y2 - y1) < 0:
                    points.append([x1, y1 - h, x2, y2 + h])  # 右上方滑动
                elif (x2 - x1) < 0 and (y2 - y1) > 0:
                    points.append([x2, y2 - h, x1, y1 + h])  # 左下方滑动
                else:
                    points.append([x2, y2, x1, y1])  # 左上方滑动
            self.points.clear()
            self.points.appends(points)
            self.points.points_signal.emit(points)

    def mousePressEvent(self, QMouseEvent):
        if self.__edit_pixmap and self.edited:
            print(self, 'press')
            if QMouseEvent.button() == Qt.LeftButton:
                self.points.append([QMouseEvent.x(), QMouseEvent.y(), 0, 0])
        else:
            super().mousePressEvent(QMouseEvent)

    def mouseMoveEvent(self, QMouseEvent):
        if self.__edit_pixmap and self.edited:
            if (QMouseEvent.buttons()
                    & Qt.LeftButton) and self.rect().contains(
                        QMouseEvent.pos()):
                self.points[-1][-2:] = [QMouseEvent.x(), QMouseEvent.y()]
                self.update()
        else:
            super().mouseMoveEvent(QMouseEvent)

    def paintEvent(self, QPaintEvent):
        if self.__edit_pixmap and self.edited:
            self.setCursor(Qt.CrossCursor)
            font = self.font()
            font.setPointSize(15)
            painter = QPainter()
            painter.begin(self)
            painter.setFont(font)
            self.drawPolicy(painter)
            painter.end()
        else:
            self.setCursor(Qt.ArrowCursor)
            super().paintEvent(QPaintEvent)

    def drawPolicy(self, painter):
        painter.drawPixmap(self.rect(), self.pixmap())
        if self.points.data:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            for index, point in enumerate(self.points.data, 1):
                x1, y1, x2, y2 = point
                msg = str(index)
                w, h = abs(x2 - x1), abs(y2 - y1)
                if (x2 - x1) > 0 and (y2 - y1) > 0:
                    painter.drawRect(x1, y1, w, h)  # 右下方滑动
                    painter.drawText(x1, y1 - 4, msg)
                elif (x2 - x1) > 0 and (y2 - y1) < 0:
                    painter.drawRect(x1, y1 - h, w, h)  # 右上方滑动
                    painter.drawText(x1, y2 - 4, msg)

                elif (x2 - x1) < 0 and (y2 - y1) > 0:
                    painter.drawRect(x1 - w, y1, w, h)  # 左下方滑动
                    painter.drawText(x2, y1 - 4, msg)
                else:
                    painter.drawRect(x2, y1 - h, w, h)  # 左上方滑动
                    painter.drawText(x2, y2 - 4, msg)


class DisplayLabel(ImgLabel):
    def __init__(self, *args, **kwargs):
        pdfwidget = kwargs.pop('pdfwidget', None)
        super().__init__(*args, **kwargs)
        self.__pdfwidget = pdfwidget

    def mouseMoveEvent(self, QMouseEvent):
        if self.edited:  #???
            if (QMouseEvent.buttons()
                    & Qt.LeftButton) and self.rect().contains(
                        QMouseEvent.pos()):
                self.points[-1][-2:] = [QMouseEvent.x(), QMouseEvent.y()]
                self.points.points_signal.emit(self.points.data)
                self.update()
        else:
            super().mouseMoveEvent(QMouseEvent)

    def getPdfWidget(self):
        return self.__pdfwidget

    def filePolicy(self):
        menu = QMenu(self)
        a1 = menu.addAction('清除区域')
        a2 = menu.addAction('识别此页')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.points.clear()
            self.points.points_signal.emit([])
            self.update()
        elif action == a2:
            pdfwidget = self.getPdfWidget()
            activeuser = pdfwidget.account.active_user()
            activeuser.config.update_from_dict({
                'parseinfo': {
                    'workpath': pdfwidget._work_path(),
                    'basic': 0,
                    'handwriting': 0,
                    'accurate': 0
                }
            })
            pdfwidget.ocr_handle.ocr_signal.emit(activeuser)

    def pdfPolicy(self):
        menu = QMenu(self)
        a1 = menu.addAction('清除区域')
        a2 = menu.addAction('识别此页')
        a3 = menu.addAction('识别pdf')
        a4 = menu.addAction('导出pdf')
        action = menu.exec_(QCursor.pos())
        pdfwidget = self.getPdfWidget()
        activeuser = pdfwidget.account.active_user()
        if action == a1:
            self.points.clear()
            self.points.points_signal.emit([])
            self.update()
        elif action == a2:
            true_index = self.__pdfwidget.pdf_handle.fake_pixmaps_indexes[
                int(self.__pdfwidget.lineEdit_2.text()) - 1]

            activeuser.config.update_from_dict({
                'parseinfo': {
                    'workpath':
                    f'---此页---:{true_index}:{self.__pdfwidget.lineEdit_2.text()}',
                    'basic': 0,
                    'handwriting': 0,
                    'accurate': 0
                }
            })
            pdfwidget.ocr_handle.ocr_signal.emit(activeuser)
        elif action == a3:
            activeuser.config.update_from_dict({
                'parseinfo': {
                    'workpath': pdfwidget._work_path(),
                    'basic': 0,
                    'handwriting': 0,
                    'accurate': 0
                }
            })
            pdfwidget.ocr_handle.ocr_signal.emit(activeuser)
        elif action == a4:
            pdfwidget.pdf_handle.save_signal.emit(None)

    def dirPolicy(self):
        menu = QMenu(self)
        a1 = menu.addAction('清除区域')
        a2 = menu.addAction('识别此页')
        a3 = menu.addAction('识别全部')
        action = menu.exec_(QCursor.pos())
        pdfwidget = self.getPdfWidget()
        activeuser = pdfwidget.account.active_user()
        if action == a1:
            self.points.clear()
            self.points.points_signal.emit([])
            self.update()
        elif action == a2:
            true_index = self.__pdfwidget.pdf_handle.fake_pixmaps_indexes[
                int(self.__pdfwidget.lineEdit_2.text()) - 1]
            activeuser.config.update_from_dict({
                'parseinfo': {
                    'workpath':
                    f'---此页---:{true_index}:{self.__pdfwidget.lineEdit_2.text()}',
                    'basic': 0,
                    'handwriting': 0,
                    'accurate': 0
                }
            })
            pdfwidget.ocr_handle.ocr_signal.emit(activeuser)
        elif action == a3:
            activeuser.config.update_from_dict({
                'parseinfo': {
                    'workpath': pdfwidget._work_path(),
                    'basic': 0,
                    'handwriting': 0,
                    'accurate': 0
                }
            })
            pdfwidget.ocr_handle.ocr_signal.emit(activeuser)

    def contextMenu(self, pos):
        render_type = self.getPdfWidget().pdf_handle.getEngine().render_type
        if render_type == 'file':
            self.filePolicy()
        elif render_type == 'dir':
            self.dirPolicy()
        elif render_type == 'pdf':
            self.pdfPolicy()


class PreviewLabel(ImgLabel):

    clicked = pyqtSignal(int)
    reset_signal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        index = kwargs.pop('index', 0)
        super().__init__(*args, **kwargs)
        self.index = index
        self.dyindex = index
        self.edited = False
        self.setCursor(Qt.PointingHandCursor)

    def contextMenu(self, pos):
        menu = QMenu(self)
        a1 = menu.addAction('恢复排序')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.reset_signal.emit()

    def mouseReleaseEvent(self, QMouseEvent):
        super().mouseReleaseEvent(QMouseEvent)
        if QMouseEvent.button() == Qt.LeftButton:
            self.clicked.emit(self.index)

    def drawPolicy(self, painter):
        super().drawPolicy(painter)
        painter.setPen(QPen(QColor(60, 60, 60, 125), 4, Qt.SolidLine))
        painter.drawRect(QRectF(self.rect()))

    def paintEvent(self, QPaintEvent):
        self.setCursor(Qt.PointingHandCursor)
        painter = QPainter()
        painter.begin(self)
        self.drawPolicy(painter)
        painter.drawRect(QRectF(self.rect()))
        painter.end()


class PreviewWidget(QWidget):

    __slots__ = '__enter', 'selected', 'shadow', 'preview_label', 'layout'

    def __init__(self, index, pixmap, shadow=20):
        super().__init__()
        self.__enter = False
        self.selected = True
        self.shadow = shadow, shadow, shadow, shadow
        self.preview_label = PreviewLabel(index=index, edit_pixmap=pixmap)
        self.preview_label.setScaledContents(True)
        self.preview_label.setPixmap(pixmap)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(shadow, shadow, shadow, shadow)
        self.layout.addWidget(self.preview_label)
        self.setLayout(self.layout)

    def paintEvent(self, QPaintEvent):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self.drawPolicy(painter)
        painter.end()

    def drawPolicy(self, painter):
        if self.__enter:
            path1 = QPainterPath()
            path1.addRoundedRect(QRectF(self.rect()), 10, 10)
            # path1.addRect(QRectF(self.rect()))
            path2 = QPainterPath()
            path2.addRect(QRectF(self.preview_label.geometry()))
            painter.fillPath(path1 - path2, QColor(120, 120, 120, 80))
            painter.drawPath(path2)

    def enterEvent(self, QEnterEvent):
        super().enterEvent(QEnterEvent)
        self.__enter = True
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.__enter = False
        self.update()


class SideButton(QPushButton):
    def __init__(self, *args, **kwargs):
        attach = kwargs.pop('attach', None)
        super().__init__(*args, **kwargs)
        self.attach_object = attach or None
        self.setCheckable(True)

    def setAttach(self, qwidget):
        self.attach_object = qwidget

    def hidePolicy(self, me=False, attach_object=False):
        self.setHidden(me)
        if self.attach_object:
            self.attach_object.setHidden(attach_object)

    def iconPolicy(self,
                   checked_pix: QPixmap = None,
                   unchecked_pix: QPixmap = None):
        def __(flag):
            if flag:
                self.setIcon(QIcon(checked_pix))
            else:
                self.setIcon(QIcon(unchecked_pix))

        self.toggled.connect(__)
