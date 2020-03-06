from PyQt5.QtWidgets import (QLineEdit, QLabel, QMenu, QAction, QListWidget,
                             QListView, QListWidgetItem, QScrollBar,
                             QHBoxLayout, QWidget)
from PyQt5.QtGui import (QPainter, QCursor, QPen, QColor, QDrag, QIntValidator,
                         QPainterPath)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QPoint, QMimeData, QRectF


class DragListWidget(QListWidget):

    drag_item = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.setMovement(QListView.Free)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSpacing(10)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_item = self.itemAt(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() and Qt.LeftButton:
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
                    if widget:
                        self.removeItemWidget(self.drag_item)
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

    def dragEnterEvent(self, event):
        event.setDropAction(Qt.MoveAction)
        event.accept()

    def dragMoveEvent(self, event):
        event.setDropAction(Qt.MoveAction)
        event.accept()

    def dropEvent(self, event):
        target_item = self.itemAt(event.pos())
        target_index = self.row(target_item)
        drag_index = self.row(self.drag_item)
        drag_widget = self.itemWidget(self.drag_item)
        drag_size = self.drag_item.sizeHint()
        if target_item is None:
            event.setDropAction(Qt.IgnoreAction)
        else:
            if drag_index < target_index:
                if drag_widget:
                    self._renderItemWidget(target_index + 1, drag_size,
                                           drag_widget)
                else:
                    self.insertItem(target_index + 1, self.drag_item)
                event.setDropAction(Qt.MoveAction)
                self.setCurrentRow(target_index + 1)
            elif drag_index > target_index:
                if drag_widget:
                    self._renderItemWidget(target_index, drag_size,
                                           drag_widget)
                else:
                    self.insertItem(target_index, self.drag_item)

                self.setCurrentRow(target_index)
                event.setDropAction(Qt.MoveAction)
            else:
                event.setDropAction(Qt.IgnoreAction)
            event.accept()


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

    def dragEnterEvent(self, event):
        if self.filterPolicy(event):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.setText(
            event.mimeData().text()[8:])  # 如果之前设置ignore 为False 这里将不会生效


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
        self.setValidator(QIntValidator(0, 10000))
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
            if v[:2] != v[2:]:
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
    action1_signal = pyqtSignal(dict)
    action2_signal = pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        draw_pixmap = kwargs.pop('draw_pixmap', None)
        super().__init__(*args, **kwargs)
        self.__flag = None
        self.edited = True
        self.draw_pixmap = draw_pixmap
        self.points = Validpoints()
        self.metedata = {}
        self.menu = QMenu(self)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    def setEditPixmap(self, pixmap):
        self.draw_pixmap = pixmap

    def setEdited(self, flag):
        self.edited = flag

    def contextMenu(self, pos):
        menu = QMenu(self)
        a1 = menu.addAction('清除')
        a2 = menu.addAction('确认')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.points.clear()
            self.action1_signal.emit(self.metedata)
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
            self.action2_signal.emit(self.metedata)
            self.points.points_signal.emit(points)

    def mousePressEvent(self, QMouseEvent):
        if self.draw_pixmap and self.edited:
            if QMouseEvent.button() == Qt.LeftButton:
                self.__flag = True
                self.points.append([QMouseEvent.x(), QMouseEvent.y(), 0, 0])
        else:
            super().mousePressEvent(QMouseEvent)

    def mouseReleaseEvent(self, QMouseEvent):
        if self.draw_pixmap and self.edited:
            if QMouseEvent.button() == Qt.LeftButton:
                self.__flag = False
        else:
            super().mouseReleaseEvent(QMouseEvent)

    def mouseMoveEvent(self, QMouseEvent):
        if self.draw_pixmap and self.edited:
            if self.__flag:
                self.points[-1][-2:] = [QMouseEvent.x(), QMouseEvent.y()]
                self.update()
        else:
            super().mouseMoveEvent(QMouseEvent)

    def paintEvent(self, QPaintEvent):
        if self.draw_pixmap and self.edited:
            self.setCursor(Qt.CrossCursor)
            painter = QPainter()
            painter.begin(self)
            self.drawPolicy(painter)
            painter.end()
        else:
            self.setCursor(Qt.ArrowCursor)
            super().paintEvent(QPaintEvent)

    def drawPolicy(self, painter):
        painter.drawPixmap(self.rect(), self.draw_pixmap)
        if self.points.data:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            for point in self.points:
                x1, y1, x2, y2 = point
                w, h = abs(x2 - x1), abs(y2 - y1)
                if (x2 - x1) > 0 and (y2 - y1) > 0:
                    painter.drawRect(x1, y1, w, h)  # 右下方滑动
                elif (x2 - x1) > 0 and (y2 - y1) < 0:
                    painter.drawRect(x1, y1 - h, w, h)  # 右上方滑动
                elif (x2 - x1) < 0 and (y2 - y1) > 0:
                    painter.drawRect(x1 - w, y1, w, h)  # 左下方滑动
                else:
                    painter.drawRect(x2, y1 - h, w, h)  # 左上方滑动


# DisplayLabel = ImgLabel

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
            self.action1_signal.emit(self.metedata)
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
            self.action2_signal.emit(self.metedata)
            self.points.points_signal.emit(points)

        elif action == a3:
            pass
        elif action == a4:
            pass
        elif action == a5:
            pass
    

class PreviewLabel(DisplayLabel):

    clicked = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        index = kwargs.pop('index', 0)
        super().__init__(*args, **kwargs)
        self.index = index
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)

    def drawPolicy(self, painter):
        super().drawPolicy(painter)
        painter.setPen(QPen(QColor(60,60,60,125), 4, Qt.SolidLine))
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
        self.shadow = shadow, shadow,shadow, shadow
        self.preview_label = PreviewLabel(index=index)
        self.preview_label.setScaledContents(True)
        self.preview_label.setEdited(False)
        self.preview_label.setPixmap(pixmap)
        self.preview_label.setEditPixmap(pixmap)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(*self.shadow)
        self.layout.addWidget(self.preview_label)
        self.setLayout(self.layout)

    def paintEvent(self, event):
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

    def enterEvent(self, event):
        super().enterEvent(event)
        self.__enter = True
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.__enter = False
        self.update()