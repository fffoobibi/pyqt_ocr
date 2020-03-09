from sys import argv, exit
from PIL import Image, ImageQt
from fitz import open as pdf_open
from fitz import Matrix
from functools import wraps
from os.path import isfile, exists, isdir, abspath, join
from os import listdir
from math import sqrt

from PyQt5.QtWidgets import (QApplication, QWidget, QListWidgetItem, QGraphicsOpacityEffect,
                             QScrollBar, QVBoxLayout, QMessageBox, QLabel,
                             QListView)
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QSize, Qt, QPropertyAnimation, QRect, QCoreApplication
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QFont, QIcon
from pdfui import Ui_Form

from customwidgets import PreviewWidget

g_dpi = 0
g_width = 0
g_height = 0


def dpi(w_r, h_r, w, h):
    global g_dpi, g_width, g_height
    if g_dpi == 0:
        g_width = w
        g_height = h
        g_dpi = sqrt(w**2 + h**2) / sqrt((w_r / 10 * 0.394)**2 +
                                         (h_r / 10 * 0.394)**2)
    return g_dpi


class InitDpi(QWidget):
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_rect = desktop.screenGeometry()
        height = screen_rect.height()
        width = screen_rect.width()
        dpi(desktop.widthMM(), desktop.heightMM(), width, height)
        font = QFont("宋体")
        font.setPixelSize(
            11 *
            (g_dpi / 96))  # CurrentFontSize *（DevelopmentDPI / CurrentFontDPI）
        app.setFont(font)
        self.close()


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

    open_signal = pyqtSignal()
    display_signal = pyqtSignal()
    reload_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    ocr_signal = pyqtSignal(list, list)

    @staticmethod
    def slot(signal: str = '', desc=''):
        def outer(func):
            @wraps(func)
            def inner(self, *args, **kwargs):
                res = func(self, *args, **kwargs)
                return res

            return inner

        return outer

    def __init__(self):
        super().__init__()
        self.__previewZoom = None
        self.__previewSize = None
        self.__displayZoom = None
        self.__displaySize = None
        self.__pageSize = None
        self.__screenSize = None
        self.__engine = None
        self.__reload = False

        self.engined_counts = 0
        self.is_editing = False
        self.pixmaps = []
        self.pixmaps_points = []
        self.preview_pixmaps_points = []
        self.edited_pdfs = []

    def clear(self):
        if not self.__reload:
            self.__previewZoom = None
            self.__displayZoom = None
            self.__previewSize = None
            self.__pageSize = None
            self.__screenSize = None
            self.is_editing = False
        self.pixmaps.clear()
        self.pixmaps_points.clear()
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
                self.reload_signal.emit()  # 阻塞
                if parent_widget.reloaded == QMessageBox.Yes:
                    self.__reload = True
                    self.clear()
                    self.setEngine(path)
                    self.rendering()
                    self.display_signal.emit()
                    self.__reload = False
                    parent_widget.reloaded = -1
                elif parent_widget.reloaded == QMessageBox.No:
                    parent_widget.reloaded = -1
            else:
                self.clear()
                self.setEngine(path)
                self.rendering()
                self.display_signal.emit()

    def init(self):
        pass


class PdfWidget(Ui_Form, QWidget):

    engine_signal = pyqtSignal(str, bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.init()
        self.set_datas()
        print('init', QThread.currentThreadId())

    def _file(self):
        return self.lineEdit.text().strip('"').strip(' ')

    def set_datas(self):
        self.reloaded = -1
        self._flag = 0
        self.pdf_handle = PdfHandle()
        self.pdf_thread = QThread()
        self.pdf_handle.moveToThread(self.pdf_thread)
        self.radioButton.setText('22')
        self.radioButton.showMaximized()
        # self.radioButton.setChecked(True)
        self.radioButton.setFixedHeight(30)

        self.pdf_thread.finished.connect(self.pdf_handle.deleteLater)
        self.pdf_handle.destroyed.connect(self.pdf_thread.deleteLater)

        self.pdf_handle.open_signal.connect(
            lambda: self.pdf_handle.open(self._file(), self))

        self.pdf_handle.display_signal.connect(self.updateListWidget)
        self.pdf_handle.reload_signal.connect(self.reload)
        self.pdf_handle.clear_signal.connect(lambda: self.listWidget.clear())

        self.displayLabel.points.points_signal.connect(
            self.updateListWidgetItem)
        self.lineEdit_2.current_page.connect(self.jump)

    def jump(self, index):
        if self.pdf_handle.is_editing:
            if index > (self.pdf_handle.pageCount() - 1):
                index = self.pdf_handle.pageCount() - 1
                self.listWidget.setCurrentRow(index)
            else:
                self.listWidget.setCurrentRow(index)
            current = self.listWidget.currentItem()
            widget = self.listWidget.itemWidget(current)
            widget.preview_label.clicked.emit(index)

    def init(self):
        self.setStyleSheet(open('./sources/flatwhite.css').read())
        self.setWindowTitle('PDF')
        self.label_2.setText('of 0')
        self.lineEdit_2.setText('0')
        self.displayLabel.hide()

    @PdfHandle.slot(signal='reload_signal')
    def reload(self):
        replay = QMessageBox.question(self, 'PDF', '确认重新加载pdf么?',
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
        self.reloaded = replay

    @PdfHandle.slot(desc='run in pdf_thread')
    def updateListWidgetItem(self, points):
        self.displayLabel.points.clear()
        self.displayLabel.points.appends(points)

        index = int(self.lineEdit_2.text()) - 1
        p_width, p_height = self.pdf_handle.displaySize
        width, height = self.pdf_handle.previewSize
        process = []
        for point in points:
            tmp = []
            x1, y1, x2, y2 = point
            x3 = x1 / p_width * width
            y3 = y1 / p_height * height
            x4 = x2 / p_width * width
            y4 = y2 / p_height * height
            tmp.extend([x3, y3, x4, y4])
            process.append(tmp)

        self.pdf_handle.pixmaps_points[index] = points
        item = self.listWidget.item(index)
        preview_label = self.listWidget.itemWidget(item).preview_label
        preview_label.points.clear()
        preview_label.points.appends(process)
        preview_label.update()

    @PdfHandle.slot(desc='run in pdf_thread')
    def get_item_widget(self, pixmap, index):
        shadow_width = self.pdf_handle.screenSize[0] / 12 / 14
        widget = PreviewWidget(index, pixmap, shadow_width)
        widget.preview_label.clicked.connect(self.displayPdfPage)
        widget.preview_label.setFixedSize(*self.pdf_handle.previewSize)
        return widget

    @PdfHandle.slot(signal='display_signal')
    def updateListWidget(self):  # 槽函数
        shadow_width = self.pdf_handle.screenSize[0] / 12 / 14
        preview_width, preview_height = self.pdf_handle.previewSize
        preview_zoom = self.pdf_handle.previewZoom
        display_pixmap = self.pdf_handle.renderPixmap(
            0, self.pdf_handle.displayZoom)

        self.label_2.setText('of %s' % self.pdf_handle.pageCount())
        self.lineEdit_2.setText('1')

        self.listWidget.setFixedWidth(preview_width + shadow_width * 2 +
                                      10 * 2 + 20)
        self.displayLabel.setPixmap(display_pixmap)
        self.displayLabel.setEditPixmap(display_pixmap)
        self.displayLabel.setEdit(True)
        self.displayLabel.show()

        # 生成预览图
        self.listWidget.indexes = self.pdf_handle.pixmaps
        for index in self.pdf_handle.pixmaps:
            pix = self.pdf_handle.renderPixmap(index, preview_zoom)
            item = QListWidgetItem()
            widget = self.get_item_widget(pix, index)
            item.setSizeHint(
                QSize(preview_width + shadow_width * 2,
                      preview_height + shadow_width * 2))
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)
            QApplication.processEvents()

        self.listWidget.setCurrentRow(0)

    @PdfHandle.slot(desc='run in pdf_thread')
    def displayPdfPage(self, index):
        item = self.listWidget.currentItem()
        row = self.listWidget.currentRow()
        page = self.pdf_handle.renderPixmap(index=index,
                                            zoom=self.pdf_handle.displayZoom)
        self.displayLabel.points.clear()
        self.lineEdit_2.setText(str(row + 1))
        self.displayLabel.setPixmap(page)
        self.displayLabel.setEditPixmap(page)
        self.displayLabel.points.appends(self.pdf_handle.pixmaps_points[index])
        self.displayLabel.update()

    def openSlot(self):
        pass

    def confirmSlot(self):
        pdf_file = self._file()
        if exists(pdf_file):
            if pdf_file[-3:].lower() == 'pdf':
                self.pdf_thread.start()
                self.pdf_handle.open_signal.emit()
        else:
            QMessageBox.warning(self, '警告', '打开正确的pdf文件')

    def leftAnSlot(self):
        rect = self.listWidget.geometry()
        self.animL = QPropertyAnimation(self.listWidget,
                                        b'geometry')  
        self.animL.setDuration(200) 
        if self.pushButton_4.isChecked():
            self.animL.setStartValue(rect)  
            self.animL.setEndValue(QRect(-rect.width(), rect.y(), rect.width(),
                                     rect.height()))  
        else:
            self.animL.setStartValue(rect)  
            self.animL.setEndValue(QRect(0, rect.y(), rect.width(),
                                     rect.height()))  
        self.animL.start()
        if self.pushButton_4.isChecked():
            self.pushButton_4.setIcon(QIcon(":/image/img/indent-increase.svg"))
        else:
            self.pushButton_4.setIcon(QIcon(":/image/img/indent-decrease.svg"))

    def rightAnSlot(self):
        rect = self.textBrowser.geometry()
        self.anim = QPropertyAnimation(self.textBrowser,
                                       b'geometry')  # 设置动画的对象及其属性
        self.anim.setDuration(300)  # 设置动画间隔时间
        if self.pushButton_3.isChecked():
            self.anim.setStartValue(rect)  # 设置动画对象的起始属性
            self.anim.setEndValue(
                QRect(self.width(), rect.y(), rect.width(),
                      rect.height()))  # 设置动画对象的结束属性
        else:
            self.anim.setStartValue(rect)
            self.anim.setEndValue(
                QRect(0, rect.y(), rect.width(),
                      rect.height()))
            self.textBrowser.show()
        self.anim.start()  # 启动动画
        if self.pushButton_3.isChecked():
            self.pushButton_3.setIcon(QIcon(":/image/img/indent-decrease.svg"))
        else:
            self.pushButton_3.setIcon(QIcon(":/image/img/indent-increase.svg"))


def main():
    # QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
    app = QApplication(argv)
    # InitDpi(app=app)
    pdfwidget = PdfWidget()
    pdfwidget.showMaximized()
    exit(app.exec_())


if __name__ == "__main__":
    main()