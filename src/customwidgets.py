from dataclasses import dataclass, field
from typing import List
from math import sqrt
from PIL import ImageQt, Image
from os.path import exists, join, expanduser, isfile, abspath, isdir

from PyQt5.QtWidgets import (QLineEdit, QLabel, QMenu, QAction, QListWidget,
                             QPushButton, QApplication, QTextBrowser, QDialog,
                             QListView, QListWidgetItem, QHBoxLayout, QWidget)
from PyQt5.QtGui import (QPainter, QCursor, QPen, QColor, QDrag, QIntValidator, 
                         QIcon, QFont, QPixmap, QFont, QPainterPath, QDrag,
                         QTransform, QDragEnterEvent, QDropEvent, QMouseEvent, QDragMoveEvent)
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QPoint, QMimeData, QRectF, QThread, QTime, QSize

from ruia_ocr import (BaiduOcrService, get_file_paths, BAIDU_ACCURATE_TYPE,
                      BAIDU_GENERAL_TYPE, BAIDU_HANDWRITING_TYPE)

from fitz import open as pdf_open
from supports import *

from advancedui import Ui_Dialog


class AdvancedDialog(QDialog, Ui_Dialog):

    radio_signal = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)
        super().__init__(*args, **kwargs)
        self.setWindowIcon(QIcon(':/image/img/cogs.svg'))
        self.setupUi(self)
        self.account = account or Account()
        self.comboBox_2.currentIndexChanged.connect(self.switch_user)
        self.comboBox_2.currentTextChanged.connect(self.switch_user_policy)

    @slot(signal='currentTextChanged', sender='comboBox_2')
    def switch_user_policy(self, text):
        texts = [
            self.comboBox_2.itemText(index)
            for index in range(self.comboBox_2.count())
        ]
        if text not in texts:
            self.login_lineEdit_id.setText('')
            self.login_lineEdit_key.setText('')
            self.login_lineEdit_secret.setText('')
        else:
            user = self.account.info[text]
            self.login_lineEdit_id.setText(user['id'])
            self.login_lineEdit_key.setText(user['key'])
            self.login_lineEdit_secret.setText(user['secret'])

    @slot(signal='currentIndexChanged', sender='comboBox_2')
    def switch_user(self, index):
        if not self.auto:
            alias = self.comboBox_2.currentText()
            active_user = self.account.get_user(alias)
            self.account.set_active_user(alias)
            self.login_lineEdit_id.setText(active_user.id)
            self.login_lineEdit_key.setText(active_user.key)
            self.login_lineEdit_secret.setText(active_user.secret)
            self.update_config(active_user.config)
            self.auto = False

    def update_account(self, from_user: User):
        self.auto = True
        alias = self.account.active_alias()
        self.comboBox_2.clear()
        self.comboBox_2.addItems(self.account.alias())
        self.comboBox_2.setCurrentText(alias)
        self.auto = False

        self.login_lineEdit_id.setText(from_user.id)
        self.login_lineEdit_key.setText(from_user.key)
        self.login_lineEdit_secret.setText(from_user.secret)

    def update_config(self, from_config: Config):
        if from_config.get('out', 'format') == 'txt':
            self.out_lineEdit_title.setEnabled(False)
            self.out_comboBox.setCurrentIndex(0)
        else:
            self.out_lineEdit_title.setEnabled(True)
            self.out_comboBox.setCurrentIndex(1)
        self.out_lineEdit_dir.setText(from_config.get('out', 'directory'))

        self.comboBox.setCurrentIndex(
            from_config.get('recognition', 'type', parse=int))

        self.reg_timeEdit.setTime(
            QTime(0, 0, from_config.get('recognition', 'delay', int)))

        self.reg_comboBox.setEditText(from_config.get('recognition', 'number'))
        self.adv_lineEdit.setText(from_config.get('advanced', 'region'))

    @slot(signal='clicked', sender='reset_button')
    def set_resetSlot(self, value: int):
        self.update_config(DEFAULT_CONFIG)
        self.update()

    @slot(signal='clicked', sender='ok_button')
    def set_applySlot(self, clicked):
        user = self.account.active_user()
        user.id = self.login_lineEdit_id.text()
        user.key = self.login_lineEdit_key.text()
        user.secret = self.login_lineEdit_secret.text()
        user.alias = self.comboBox_2.lineEdit().text()
        user.config.update_from_dict({
            'recognition': {
                'delay': self.reg_timeEdit.text()[:-1],
                'number': int(self.reg_timeEdit.text()[:-1]),
                'type': self.comboBox.currentIndex()
            },
            'out': {
                'format':
                'txt' if self.out_comboBox.currentText().startswith('文本') else
                'xlsx',
                'directory':
                self.out_lineEdit_dir.text(),
                'title':
                'none'
            },
            'advanced': {
                'region': self.adv_lineEdit.text(),
                'text1': 'none',
                'clean': 'false'
            }
        })
        self.account.set_active_user(user.alias)
        user.sync(self.account)
        self.radio_signal.emit(user.config.get('recognition', 'type', int))
        self.close()

    def out_buttonSlot(self):
        pass

    def out_fmtSlot(self, index: int):
        user = self.account.active_user()
        if index == 0:
            if user.config.get('out', 'format') == 'txt':
                self.out_lineEdit_title.setEnabled(False)
        else:
            if user.config.get('out', 'format') == 'xlsx':
                self.out_lineEdit_title.setEnabled(True)

    def reg_buttonSlot(self):
        pass

    def adv_buttonAddSlot(self):
        pass

    def adv_buttonHelpSlot(self):
        pass


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
    MARGINES = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMovement(QListView.Free)
        self.setSpacing(self.MARGINES)
        self._start_press = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_item = self.itemAt(event.pos())
            self._start_press = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton:
            if (event.pos() - self._start_press).manhattanLength() < QApplication.startDragDistance():
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

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.drag_item:
            if event.source():
                event.setDropAction(Qt.MoveAction)
                event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        event.setDropAction(Qt.MoveAction)
        event.accept()

    def _renderItemWidget(self, row: int, qsize: QSize, widget: QWidget):
        item = QListWidgetItem()
        item.setSizeHint(qsize)
        if row == -1:
            self.addItem(item)
        else:
            self.insertItem(row, item)
        self.setItemWidget(item, widget)

    def addItemWidget(self, itemsize: QSize, widget: QWidget) -> NoReturn:
        item = QListWidgetItem()
        item.setSizeHint(itemsize)
        self.addItem(item)
        self.setItemWidget(item, widget)

    def getItemWidget(self, index: int) -> QWidget:
        item = self.item(index)
        return self.itemWidget(item)

    def insertItemWidget(self, index: int, itemsize: QSize, widget: QWidget) -> NoReturn:
        item = QListWidgetItem()
        item.setSizeHint(itemsize)
        self.insertItem(index, item)
        self.setItemWidget(item, widget)

    def takeItemWidget(self, index: int) -> NoReturn:
        item = self.item(index)
        self.removeItemWidget(item)
        self.takeItem(index)


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

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.filterPolicy(event):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        self.setText(
            event.mimeData().text()[8:])  # 如果之前设置ignore 为False 这里将不会生效


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
    def fromList(points: RectCoords):
        point = Validpoints()
        point.appends(points)
        return point

    @classmethod
    def adjustCoords(cls, points: RectCoords) -> RectCoords:
        xycoords = []
        for coord in points:
            x1, y1, x2, y2 = coord
            w, h = abs(x2 - x1), abs(y2 - y1)
            if (x2 - x1) > 0 and (y2 - y1) > 0:
                xycoords.append([x1, y1, x2, y2])  # 右下方滑动
            elif (x2 - x1) > 0 and (y2 - y1) < 0:
                xycoords.append([x1, y1 - h, x2, y2 + h])  # 右上方滑动
            elif (x2 - x1) < 0 and (y2 - y1) > 0:
                xycoords.append([x2, y2 - h, x1, y1 + h])  # 左下方滑动
            else:
                xycoords.append([x2, y2, x1, y1])  # 左上方滑动
        return xycoords

    @property
    def data(self) -> RectCoords:
        res = []
        for v in self.__data:
            if (v[:2] != v[2:]) and (0 not in v[-2:]):
                res.append(v)
        return res

    def append(self, v: RectCoord) -> bool:
        if v[:2] != v[2:]:
            self.__data.append(v)
            return True
        return False

    def appends(self, points: RectCoords):
        for point in points:
            self.append(point)

    def clear(self):
        self.__data.clear()

    def __iter__(self):
        for v in self.data:
            yield v

    def __getitem__(self, item) -> RectCoord:
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

    def setEditPixmap(self, flag: bool):
        self.__edit_pixmap = flag

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
        painter.drawPixmap(0, 0, self.pixmap())
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

    select_rotate_index_sig = pyqtSignal(bool, int, int)
    restore_rotate_sig = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        parent_widget = kwargs.pop('parent_widget', None)
        super().__init__(*args, **kwargs)
        self.__pdfwidget = parent_widget
        self._rotate_angle = 0
        self.index = -1
        self.fake_index = -1
        self.is_editing = False
        self.is_select = True
        self.restore_rotate_sig.connect(self._restore_angle)

    def _restore_angle(self, rotate):
        self._rotate_angle = rotate

    def initFirst(self, pixmap: QPixmap) -> NoReturn:
        self.setPixmap(pixmap)
        self.setEditPixmap(True)
        self.setEdit(True)
        self.index = 0
        self.fake_index = 0
        self.show()

    def mouseMoveEvent(self, QMouseEvent):
        if self.edited:  # ???
            if (QMouseEvent.buttons()
                    & Qt.LeftButton) and self.rect().contains(
                        QMouseEvent.pos()):
                try:
                    self.points[-1][-2:] = [QMouseEvent.x(), QMouseEvent.y()]
                    self.points.points_signal.emit(self.points.data)
                    self.is_editing = True
                    self.update()
                except IndexError:
                    ...
        else:
            super().mouseMoveEvent(QMouseEvent)
            self.is_editing = False

    def getPdfWidget(self) -> QWidget:
        return self.__pdfwidget

    def rotate(self, angle: int = 90) -> NoReturn:
        self._rotate_angle += angle

        transform = QTransform()
        transform.rotate(angle)
        pix = self.pixmap().transformed(transform, Qt.SmoothTransformation)
        self.setPixmap(pix)
        # 更新previewlabel中的信息
        self.select_rotate_index_sig.emit(
            self.is_select, self._rotate_angle, self.fake_index)

    def clearXYCoords(self) -> NoReturn:
        self.points.clear()

    def extendsPoints(self, points) -> NoReturn:
        self.points.appends(points)

    def drawPolicy(self, painter):
        painter.drawPixmap(0, 0, self.pixmap())
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

    def filePolicy(self):
        menu = QMenu(self)
        a1 = menu.addAction('清除区域')
        a2 = menu.addAction('识别此页')
        a3 = menu.addAction('复制结果')
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
        elif action == a3:
            pdfwidget.textBrowser.copy_latest.emit()

    def pdfPolicy(self):
        menu = QMenu(self)
        a1 = menu.addAction('清除区域')
        a2 = menu.addAction('识别此页')
        a3 = menu.addAction('识别pdf')
        a4 = menu.addAction('导出pdf')
        a5 = menu.addAction('复制结果')
        action = menu.exec_(QCursor.pos())
        pdfwidget = self.getPdfWidget()
        activeuser = Account().active_user()
        if action == a1:
            self.points.clear()
            self.points.points_signal.emit([])
            self.update()
        elif action == a2:
            activeuser.config.update_from_dict({
                'parseinfo': {
                    'workpath': '---此页---:',
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
        elif action == a5:
            pdfwidget.textBrowser.copy_latest.emit()

    def dirPolicy(self):
        menu = QMenu(self)
        a1 = menu.addAction('清除区域')
        a2 = menu.addAction('识别此页')
        a3 = menu.addAction('识别全部')
        a4 = menu.addAction('复制结果')
        action = menu.exec_(QCursor.pos())
        pdfwidget = self.getPdfWidget()
        activeuser = pdfwidget.account.active_user()
        if action == a1:
            self.points.clear()
            self.points.points_signal.emit([])
            self.update()
        elif action == a2:
            activeuser.config.update_from_dict({
                'parseinfo': {
                    'workpath': '---此页---:',
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
            pdfwidget.textBrowser.copy_latest.emit()

    def contextMenu(self, pos):
        render_type = self.getPdfWidget().pdf_handle.getEngine().render_type
        if render_type == 'file':
            self.filePolicy()
        elif render_type == 'dir':
            self.dirPolicy()
        elif render_type == 'pdf':
            self.pdfPolicy()


@dataclass
class PageState(object):
    page_index: int = -1
    fake_page_index: int = -1
    rotate: int = 0
    select_state: bool = False
    rect_coords: list = field(default_factory=list)
    dis_coords: list = field(default_factory=list)

    def __repr__(self):
        return f'PageState<{self.page_index},{self.fake_page_index},{self.rotate},{self.select_state}...>'


class PreviewLabel(ImgLabel):

    reset_signal = pyqtSignal()
    clicked = pyqtSignal(PageState)
    select_rotate_index_sig = pyqtSignal(bool, int, int)  # 更新previewlabel信息

    def __init__(self, *args, **kwargs):
        index = kwargs.pop('index', 0)
        super().__init__(*args, **kwargs)
        self.index = index
        self.edited = False
        self.page_state = PageState(page_index=index,
                                    fake_page_index=index,
                                    select_state=True)
        self.setCursor(Qt.PointingHandCursor)
        self.select_rotate_index_sig.connect(self._update_page_state)

    def _update_page_state(self, flag, angle, index):
        if index == self.page_state.fake_page_index:
            self.page_state.select_state = flag
            self.page_state.rotate = angle

    def contextMenu(self, pos):
        menu = QMenu(self)
        a1 = menu.addAction('恢复排序')
        action = menu.exec_(QCursor.pos())
        if action == a1:
            self.reset_signal.emit()

    def mouseReleaseEvent(self, QMouseEvent):
        super().mouseReleaseEvent(QMouseEvent)
        if QMouseEvent.button() == Qt.LeftButton:
            self.clicked.emit(self.page_state)

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

    SHADOW = 20

    __slots__ = '__enter', 'selected', 'shadow', 'preview_label', 'layout'

    def __init__(self, index, pixmap, shadow=None):
        super().__init__()
        self.__enter = False
        self.selected = True
        self.shadow = (shadow, ) * 4 if shadow else (self.SHADOW, ) * 4
        self.preview_label = PreviewLabel(index=index, edit_pixmap=pixmap)
        self.preview_label.setScaledContents(True)
        self.preview_label.setPixmap(pixmap)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(*self.shadow)
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


class PreViewListWidget(DragListWidget):

    def dropEvent(self, event: QDropEvent):
        self.target_item = self.itemAt(event.pos())
        if self.target_item is None:
            event.setDropAction(Qt.IgnoreAction)
        else:
            target_size = self.target_item.sizeHint()
            target_index = self.row(self.target_item)
            target_widget = self.itemWidget(self.target_item)
            target_label = target_widget.preview_label

            drag_size = self.drag_item.sizeHint()
            drag_index = self.row(self.drag_item)
            drag_widget = self.itemWidget(self.drag_item)
            drag_label = drag_widget.preview_label

            if drag_index != target_index:
                # 交换次序
                target_label.page_state.fake_page_index, drag_label.page_state.fake_page_index = drag_label.page_state.fake_page_index, target_label.page_state.fake_page_index

                if drag_widget:
                    self._renderItemWidget(target_index + 1, drag_size,
                                           drag_widget)
                    self._renderItemWidget(drag_index + 1, target_size,
                                           target_widget)
                else:
                    self.insertItem(target_index + 1, self.drag_item)
                    self.insertItem(drag_index + 1, self.target_item)

                self.setCurrentRow(target_index)
                event.setDropAction(Qt.MoveAction)
                drag_label.clicked.emit(drag_label.page_state)
            else:
                event.setDropAction(Qt.IgnoreAction)
            event.accept()

    def updateItemPreview(self, index: int, itemsize: QSize, pixmap: QPixmap, clear=True) -> NoReturn:
        item = self.item(index)
        widget = self.getItemWidget(index)
        shadow_width = widget.shadow[0]
        item.setSizeHint(itemsize + QSize(shadow_width * 2, shadow_width * 2))
        preview_label = widget.preview_label
        preview_label.setPixmap(pixmap)
        preview_label.setFixedSize(pixmap.size())
        preview_label.points.clear() if clear else None

    def getPreviewLabel(self, index: int) -> PreviewLabel:
        widget = self.getItemWidget(index)
        return widget.preview_label

    def getPreviewLabelPageStates(self) -> List[PageState]:
        pages = []
        for index in range(self.count()):
            pages.append(self.getPreviewLabel(index).page_state)
        return pages


class SideButton(QPushButton):

    def __init__(self, *args, **kwargs):
        attachs = kwargs.pop('attachs', None)
        super().__init__(*args, **kwargs)
        self.attach_objects = attachs or None
        self.setCheckable(True)

    def setAttach(self, *args, qwidgets: list = None):
        if qwidgets is None:
            self.attach_objects = list(args)
        else:
            self.attach_objects = qwidgets

    def hidePolicy(self, me=False, attach_object=False):
        self.setHidden(me)
        if self.attach_objects is not None:
            if isinstance(attach_object, list):
                for widget, flag in zip(self.attach_objects, attach_object):
                    widget.setHidden(flag)
            else:
                self.attach_objects[0].setHidden(attach_object)

    def iconPolicy(self, checked_pix: str = None, unchecked_pix: str = None):
        def __(flag):
            if flag:
                self.setIcon(QIcon(checked_pix))
                if isinstance(self.attach_objects, list):
                    self.hidePolicy(False, [True] * len(self.attach_objects))
                else:
                    self.hidePolicy(False, True)
            else:
                self.setIcon(QIcon(unchecked_pix))
                if isinstance(self.attach_objects, list):
                    self.hidePolicy(False, [False] * len(self.attach_objects))
                else:
                    self.hidePolicy(False, False)

        self.toggled.connect(__)
