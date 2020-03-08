from configparser import ConfigParser
from os.path import exists, join, expanduser, isfile, abspath, isdir

from PyQt5.QtWidgets import (QLineEdit, QLabel, QMenu, QAction, QListWidget,
                             QListWidgetItem, QHBoxLayout, QWidget)
from PyQt5.QtGui import (QPainter, QCursor, QPen, QColor, QDrag, QIntValidator, QPixmap, 
                         QFont, QPainterPath)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QPoint, QMimeData, QRectF

from ruia_ocr import (BaiduOcrService, get_file_paths, BAIDU_ACCURATE_TYPE,
                      BAIDU_GENERAL_TYPE, BAIDU_HANDWRITING_TYPE)
from supports import Account, User, Config


class DragListWidget(QListWidget):
    drag_item = None
    target_item = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSpacing(10)
        self.indexes = []

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.drag_item = self.itemAt(QMouseEvent.pos())
        super().mousePressEvent(QMouseEvent)

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() & Qt.LeftButton:
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

    def dragEnterEvent(self, QDragEnterEvent):
        QDragEnterEvent.setDropAction(Qt.MoveAction)
        QDragEnterEvent.accept()

    def dragMoveEvent(self, QDragMoveEvent):
        QDragMoveEvent.setDropAction(Qt.MoveAction)
        QDragMoveEvent.accept()

    def dropEvent(self, QDropEvent):
        self.target_item = self.itemAt(QDropEvent.pos())
        target_index = self.row(self.target_item)
        target_widget = self.itemWidget(self.target_item)
        drag_index = self.row(self.drag_item)
        drag_widget = self.itemWidget(self.drag_item)
        drag_label = drag_widget.preview_label
        drag_size = self.drag_item.sizeHint()
        if self.target_item is None:
            QDropEvent.setDropAction(Qt.IgnoreAction)
        else:
            if drag_index != target_index:
                if drag_widget:
                    self._renderItemWidget(target_index + 1, drag_size,
                                           drag_widget)
                    self._renderItemWidget(drag_index + 1, drag_size,
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
    def filterPolicy(self, event):
        if event.mimeData().hasText():
            path = event.mimeData().text()[-3:]
            if path.lower() == 'pdf':
                return True
        return False


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

    def setEditPixmap(self, pixmap):
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
        painter.drawPixmap(self.rect(), self.__edit_pixmap)
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
    def contextMenu(self, pos):
        menu = QMenu(self)
        a1 = menu.addAction('清除')
        a2 = menu.addAction('确认')
        a3 = menu.addAction('识别此页')
        a4 = menu.addAction('识别此PDF')
        a5 = menu.addAction('导出此PDF')
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

        elif action == a3:
            pass
        elif action == a4:
            pass
        elif action == a5:
            pass


class PreviewLabel(ImgLabel):

    clicked = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        index = kwargs.pop('index', 0)
        super().__init__(*args, **kwargs)
        self.index = index
        self.dyindex = index
        self.edited = False
        self.setCursor(Qt.PointingHandCursor)

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
    def __init__(self, index, pixmap, shadow=20):
        super().__init__()
        self.__enter = False
        self.selected = False
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
        if self.__enter or self.selected:
            path1 = QPainterPath()
            path1.addRect(QRectF(self.rect()))
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


class EngineError(Exception):
    ...


class Engine(object):
    def __init__(self, path):

        if isfile(path) and (path[-3:].lower() == 'pdf'):
            self.render = pdf_open(path)
            self.isPdf = True

        elif exists(path) and isdir(path):
            self.render = path
            self.isPdf = False
        else:
            raise EngineError('渲染异常')
        self.__pagesView = None
        self.target = path

    def pagesView(self) -> list:
        if self.__pagesView is None:
            if self.isPdf:
                self.__pagesView = [
                    'Page_%s' % page
                    for page in range(1, self.render.pageCount + 1)
                ]
            else:
                self.__pagesView = [
                    abspath(join(self.target, file))
                    for file in listdir(self.target)
                ]
        return self.__pagesView

    def pageCount(self):
        if self.isPdf:
            return self.render.pageCount
        return len(listdir(self.target))

    def getPixmap(self, index, zoom=(1, 1)) -> QPixmap:
        if self.isPdf:
            x, y = zoom
            pdf_pixmap = self.render[index].getPixmap(Matrix(x, y))
            fmt = QImage.Format_RGBA8888 if pdf_pixmap.alpha else QImage.Format_RGB888
            pixmap = QPixmap.fromImage(
                QImage(pdf_pixmap.samples, pdf_pixmap.width, pdf_pixmap.height,
                       pdf_pixmap.stride, fmt))
            return pixmap
        else:
            return QPixmap(self.pagesView()[index])

    def __getitem__(self, index) -> QPixmap:
        return self.getPixmap(index)

    def __repr__(self):
        return f'Engine<{self.target}>'


class PdfHandle(QObject):

    display_signal = pyqtSignal()
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    ocr_signal = pyqtSignal(list, list)

    def __init__(self):
        super().__init__()
        self.__previewZoom = None
        self.__previewSize = None
        self.__displayZoom = None
        self.__displaySize = None
        self.__pageSize = None
        self.__screenSize = None
        self.__engine = None

        self.engined_counts = 0
        self.is_editing = False
        self.pixmaps = []
        self.pixmaps_points = []
        self.preview_pixmaps_points = []
        self.edited_pdfs = []

    def clear(self):
        self.__previewZoom = None
        self.__displayZoom = None
        self.__previewSize = None
        self.__pageSize = None
        self.__screenSize = None
        self.is_editing = False
        self.pixmaps.clear()
        self.pixmaps_points.clear()
        # self.preview_pixmaps_points.clear()
        self.edited_pdfs.clear()
        self.clear_signal.emit()

    def setEngine(self, path):
        self.__engine = Engine(path)

    @property
    def screenSize(self) -> tuple:
        if self.__screenSize is None:
            desktop = QApplication.desktop()
            self.__screenSize = desktop.width(), desktop.height()
        return self.__screenSize

    @property
    def pageSize(self) -> tuple:
        if self.__pageSize is None:
            pix = self.__engine.getPixmap(index=0, zoom=(1, 1))
            self.__pageSize = pix.width(), pix.height()
        return self.__pageSize

    @property
    def previewSize(self) -> tuple:
        if self.__previewSize is None:
            p_width, p_height = self.pageSize
            d_width, d_height = self.screenSize
            zoom_width = d_width / 12
            zoom_height = p_height / p_width * zoom_width
            self.__previewSize = round(zoom_width, 0), round(zoom_height, 0)
        return self.__previewSize

    @property
    def previewZoom(self) -> tuple:
        if self.__previewZoom is None:
            p_width, p_height = self.pageSize
            width, height = self.previewSize
            self.__previewZoom = width / p_width, width / p_width
        return self.__previewZoom

    @property
    def displayZoom(self) -> tuple:
        if self.__displayZoom is None:
            p_width, p_height = self.pageSize
            d_width, d_height = self.screenSize
            if (p_width, p_height) > (d_width, d_height):
                scaled_x = max(p_width / d_width, p_height / d_height) - 0.1
                self.__displayZoom = scaled_x, scaled_x
            else:
                self.__displayZoom = d_height * 0.8 / p_height, d_height * 0.8 / p_height

        return self.__displayZoom

    @displayZoom.setter
    def displayZoom(self, zoom: tuple):
        self.__displayZoom = zoom

    @property
    def displaySize(self):
        if self.__displaySize is None:
            display_zoom = self.displayZoom[0]
            p_width, p_height = self.pageSize
            width, height = round(p_width * display_zoom,
                                  0), round(p_height * display_zoom, 0)
            self.__displaySize = width, height
        return self.__displaySize

    def pageCount(self):
        return self.__engine.pageCount()

    def renderPixmap(self, index, zoom=(1, 1)) -> QPixmap:
        pixmap = self.__engine.getPixmap(index, zoom)
        return pixmap

    def rendering(self):
        self.is_editing = True
        render_indexes = []
        for index in range(self.pageCount()):
            render_indexes.append(index)

        self.pixmaps = render_indexes
        self.pixmaps_points = [[[]] for points in range(len(self.pixmaps))]

    def open(self, path, parent_widget):
        self.engined_counts += 1
        self.edited_pdfs.append(path)

        try:
            if self.engined_counts == 1:
                flag = False
            else:
                flag = self.__engine.target == self.edited_pdfs[-1]
        except IndexError:
            flag = False
        finally:
            if flag:
                self.reload_signal.emit()
                while True:
                    if parent_widget.reloaded == QMessageBox.Yes:
                        self.clear()
                        self.setEngine(path)
                        self.rendering()
                        self.display_signal.emit()
                        parent_widget.reloaded = -1
                        break
                    elif parent_widget.reloaded == QMessageBox.No:
                        parent_widget.reloaded = -1
                        break
            else:
                self.clear()
                self.setEngine(path)
                self.rendering()
                self.display_signal.emit()
            parent_widget.displayLabel.show()
            self.thread().quit()

    def init(self):
        pass


class ResultsHandle():
    def __init__(self, platform='b'):
        self.platform = platform

    def process(self, results: dict):
        if 'words_result' in results.keys():
            res = []
            for dic in results.get('words_result'):
                res.append(dic.get('words'))
            return results, True
        else:
            return results, False


class OcrHandle(QObject):

    ocr_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.use_pdf_handle = False
        self.result_handle =  ResultsHandle()

    def ocr(self, user: User):
        platform = user.platform
        if platform == 'b':
            self.baidu(user)
        else:
            pass

    def baidu(self, user:User):
        config: Config = user.config
        if user.legal:
            starts = config.get('parseinfo', 'workpath')
            service = config.get('recognition', 'type')
            number = config.get('recognition', 'number')
            delay = int(config.get('recognition', 'delay')) * 1000

            _region = config.get('advanced', 'region')
            region = None if _region == 'none' else _region
            if not self.use_pdf_handle:
                if service == '0':
                    service_type = BAIDU_GENERAL_TYPE
                elif service== '1':
                    service_type = BAIDU_ACCURATE_TYPE
                else:
                    service_type = BAIDU_HANDWRITING_TYPE
                ocr_service = BaiduOcrService(user.id, user.key, user.secret, service_type, seq='\n')

                self.signal.emit(
                    f'<p style="font-weight:bold;color:purple">[{info_time()}] {basename(path)}:</p>')

                json = ocr_service.request(region=region, image_path=starts)
                res, flag = self.result_handle.process(json)
                if flag:
                    self.signal.emit('<p>%s</p>' % '\n'.join(res))
                else:
                    self.signal.emit(str(json))
                self.thread().msleep(delay)